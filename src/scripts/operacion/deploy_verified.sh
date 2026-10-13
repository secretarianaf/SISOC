#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="${SISOC_ROOT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)}"
EXPECTED_REVISION=""
DEPLOY_ENVIRONMENT=""
ROLLBACK_REVISION=""
SKIP_PULL=0

fail() {
  printf '[deploy-verified] ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      DEPLOY_ENVIRONMENT="${2:-}"
      shift 2
      ;;
    --expected-revision)
      EXPECTED_REVISION="${2:-}"
      shift 2
      ;;
    --rollback-revision)
      ROLLBACK_REVISION="${2:-}"
      shift 2
      ;;
    --skip-pull)
      SKIP_PULL=1
      shift
      ;;
    *)
      fail "Argumento desconocido: $1"
      ;;
  esac
done

[[ "$EXPECTED_REVISION" =~ ^[0-9a-f]{40}$ ]] \
  || fail "--expected-revision debe ser un SHA completo."
if [[ -n "$ROLLBACK_REVISION" && ! "$ROLLBACK_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  fail "--rollback-revision debe ser un SHA completo."
fi

case "$DEPLOY_ENVIRONMENT" in
  qa)
    EXPECTED_BRANCH=development
    COMPOSE_FILES=(-f "$ROOT_DIR/docker/compose/docker-compose.deploy.yml")
    HEALTH_SCRIPT="$ROOT_DIR/src/scripts/infra/healthcheck_qa.sh"
    ;;
  homologacion)
    EXPECTED_BRANCH=homologacion
    COMPOSE_FILES=(-f "$ROOT_DIR/docker/compose/docker-compose.deploy.yml" -f "$ROOT_DIR/docker/compose/docker-compose.produccion.yml")
    HEALTH_SCRIPT="$ROOT_DIR/src/scripts/infra/healthcheck_hml.sh"
    ;;
  production)
    EXPECTED_BRANCH=main
    COMPOSE_FILES=(-f "$ROOT_DIR/docker/compose/docker-compose.deploy.yml" -f "$ROOT_DIR/docker/compose/docker-compose.produccion.yml")
    HEALTH_SCRIPT="$ROOT_DIR/src/scripts/infra/healthcheck_prod.sh"
    ;;
  *)
    fail "--environment debe ser qa, homologacion o production."
    ;;
esac

COMPOSE=(docker compose "${COMPOSE_FILES[@]}" --project-directory "$ROOT_DIR")
[[ -d "$ROOT_DIR/.git" ]] || fail "SISOC_ROOT_DIR no apunta a un checkout Git."
[[ "$(git -C "$ROOT_DIR" branch --show-current)" == "$EXPECTED_BRANCH" ]] \
  || fail "El checkout no esta en $EXPECTED_BRANCH."
git -C "$ROOT_DIR" diff --quiet || fail "El checkout tiene cambios tracked."
git -C "$ROOT_DIR" diff --cached --quiet || fail "El checkout tiene cambios staged."

git -C "$ROOT_DIR" fetch origin --no-tags "$EXPECTED_BRANCH:refs/remotes/origin/$EXPECTED_BRANCH"
remote_revision="$(git -C "$ROOT_DIR" rev-parse "origin/$EXPECTED_BRANCH")"
[[ "$remote_revision" == "$EXPECTED_REVISION" ]] \
  || fail "La branch avanzo a $remote_revision; no se despliega $EXPECTED_REVISION."

previous_revision="${ROLLBACK_REVISION:-$(git -C "$ROOT_DIR" rev-parse HEAD)}"
deployment_started=0

wait_for() {
  local description="$1"
  local attempts="$2"
  local output attempt
  shift 2
  output="$(mktemp)"
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if "$@" >"$output" 2>&1; then
      cat "$output"
      rm -f "$output"
      return 0
    fi
    if ((attempt < attempts)); then
      echo "[deploy-verified] Esperando $description ($attempt/$attempts)..."
      sleep 2
    fi
  done
  cat "$output"
  rm -f "$output"
  return 1
}

show_diagnostics() {
  echo "::group::Diagnostico de $DEPLOY_ENVIRONMENT"
  "${COMPOSE[@]}" ps || true
  "${COMPOSE[@]}" logs --tail 200 django || true
  echo "::endgroup::"
}

backend_services() {
  python3 -c 'import json,sys; print(" ".join(s["service"] for s in json.load(open(sys.argv[1])).values()))' \
    "$ROOT_DIR/src/backends/config/backends.json"
}

verify_stack() {
  # Migraciones de la composición completa (core + backends): las aplica y las
  # verifica el migrador, que tiene todo el grafo.
  if ! wait_for "migraciones de $DEPLOY_ENVIRONMENT" 30 \
    "${COMPOSE[@]}" --profile migrate run --rm -T migrator python manage.py migrate --check; then
    return 1
  fi
  local service
  for service in $(backend_services); do
    if ! wait_for "salud de $service en $DEPLOY_ENVIRONMENT" 30 \
      "${COMPOSE[@]}" exec -T "$service" python -c "from urllib.request import urlopen, Request; r = urlopen(Request('http://127.0.0.1:8000/health/', headers={'X-Forwarded-Proto': 'https'}), timeout=2); exit(0 if r.status == 200 else 1)"; then
      return 1
    fi
  done
  wait_for "healthcheck de $DEPLOY_ENVIRONMENT" 30 bash "$HEALTH_SCRIPT"
}

# Una revisión previa a la modularización (#2628) no tiene migrador ni
# backends: se verifica como lo hacía su propio deploy_verified.sh.
verify_legacy_stack() {
  if ! wait_for "migraciones de $DEPLOY_ENVIRONMENT" 30 \
    "${COMPOSE[@]}" exec -T django python manage.py migrate --check; then
    return 1
  fi
  wait_for "healthcheck de $DEPLOY_ENVIRONMENT" 30 bash "$HEALTH_SCRIPT"
}

# Compose de la revisión restaurada: antes de #2639 vivían en la raíz.
use_rollback_compose() {
  [[ -f "$ROOT_DIR/docker/compose/docker-compose.deploy.yml" ]] && return 0
  local index
  local legacy_files=()
  for ((index = 1; index < ${#COMPOSE_FILES[@]}; index += 2)); do
    legacy_files+=(-f "$ROOT_DIR/$(basename "${COMPOSE_FILES[$index]}")")
  done
  COMPOSE_FILES=("${legacy_files[@]}")
  COMPOSE=(docker compose "${COMPOSE_FILES[@]}" --project-directory "$ROOT_DIR")
}

# Cada deploy deja imágenes sisoc/* con el SHA en el tag y llenan el disco.
# Después de un deploy verificado se borran las que ya no sirven: se conservan
# las que usa algún contenedor (también detenido) y las de la revisión
# desplegada y la anterior. Si el rollback necesita otra, la reconstruye.
cleanup_old_images() {
  local in_use image image_id
  in_use="$(docker ps -aq | xargs -r docker inspect --format '{{.Image}}' | sort -u)" \
    || return 1
  while read -r image image_id; do
    [[ -n "$image" ]] || continue
    case "$image" in
      *:"$EXPECTED_REVISION" | *:"$previous_revision") continue ;;
    esac
    grep -qxF "$image_id" <<<"$in_use" && continue
    docker image rm "$image" >/dev/null \
      || echo "::warning::No se pudo borrar la imagen $image."
  done < <(docker image ls --no-trunc --filter 'reference=sisoc/*' \
    --format '{{.Repository}}:{{.Tag}} {{.ID}}')
  docker builder prune -f --filter until=72h >/dev/null
}

rollback_on_exit() {
  local failed_status=$?
  trap - EXIT
  if [[ "$failed_status" -eq 0 || "$deployment_started" -eq 0 ]]; then
    exit "$failed_status"
  fi

  show_diagnostics
  echo "::warning::El deploy fallo; restaurando automaticamente $previous_revision."
  if ! git -C "$ROOT_DIR" reset --hard "$previous_revision"; then
    echo "::error::No se pudo restaurar el checkout anterior."
    exit "$failed_status"
  fi
  # Una revisión previa a #2639 conserva scripts/ en la raíz.
  local rollback_scripts="$ROOT_DIR/src/scripts"
  [[ -f "$rollback_scripts/operacion/deploy_refresh.sh" ]] || rollback_scripts="$ROOT_DIR/scripts"
  HEALTH_SCRIPT="$rollback_scripts/infra/$(basename "$HEALTH_SCRIPT")"
  use_rollback_compose
  local refresh="$rollback_scripts/operacion/deploy_refresh.sh"
  local refresh_args=(--yes --skip-pull --expected-revision "$previous_revision" --without-mobile)
  # Diff desde la revision fallida: se recrean los mismos servicios que toco.
  # Un deploy_refresh.sh previo al deploy selectivo no conoce --diff-base y
  # siempre recrea el stack completo.
  if grep -q -- "--diff-base" "$refresh"; then
    refresh_args+=(--diff-base "$EXPECTED_REVISION")
  fi
  if ! SISOC_ROOT_DIR="$ROOT_DIR" bash "$refresh" "${refresh_args[@]}"; then
    echo "::error::No se pudo reconstruir el stack de la revision anterior."
    exit "$failed_status"
  fi
  # El rollback verifica con las imágenes de la revisión anterior.
  export SISOC_RELEASE_SHA="$previous_revision"
  local verify=verify_stack
  [[ -f "$ROOT_DIR/src/backends/config/backends.json" ]] || verify=verify_legacy_stack
  if ! "$verify"; then
    show_diagnostics
    echo "::error::La revision anterior fue recreada, pero no supero la verificacion."
    exit "$failed_status"
  fi
  echo "::warning::Rollback verificado en $previous_revision. Las migraciones de base de datos no se revierten automaticamente: ver docs/operacion/rollback_release_modularizacion.md."
  exit "$failed_status"
}
trap rollback_on_exit EXIT

echo "Commit previo al deploy para rollback: $previous_revision"
deployment_started=1
# Actualizar antes de resolver las rutas nuevas: HML/PRD pueden seguir en una
# revisión con scripts/ en la raíz. La revisión previa ya quedó guardada.
if [[ "$SKIP_PULL" -eq 0 ]]; then
  git -C "$ROOT_DIR" merge --ff-only "$EXPECTED_REVISION"
fi
# Tag de las imágenes con código que construye deploy_refresh.sh: verify_stack
# usa las mismas (el migrador, entre ellas).
export SISOC_RELEASE_SHA="$EXPECTED_REVISION"
deploy_args=(--yes --skip-pull --expected-revision "$EXPECTED_REVISION" --without-mobile --diff-base "$previous_revision")
SISOC_ROOT_DIR="$ROOT_DIR" bash "$ROOT_DIR/src/scripts/operacion/deploy_refresh.sh" "${deploy_args[@]}"
verify_stack
deployed_revision="$(git -C "$ROOT_DIR" rev-parse HEAD)"
[[ "$deployed_revision" == "$EXPECTED_REVISION" ]] \
  || fail "El checkout final no coincide con la revision esperada."
deployment_started=0

# El deploy ya quedó verificado: un error de limpieza solo avisa.
image_cleanup="OK"
if ! cleanup_old_images; then
  image_cleanup="con errores"
  echo "::warning::La limpieza de imagenes viejas no termino; el deploy quedo verificado."
fi

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "### Deploy $DEPLOY_ENVIRONMENT verificado"
    echo "- Revision desplegada: \`$deployed_revision\`"
    echo "- Migraciones: \`migrate --check\` OK"
    echo "- Health: \`$(basename "$HEALTH_SCRIPT")\` OK"
    echo "- Rollback automatico: revision previa \`$previous_revision\`"
    echo "- Limpieza de imagenes viejas: $image_cleanup"
  } >> "$GITHUB_STEP_SUMMARY"
fi

trap - EXIT
