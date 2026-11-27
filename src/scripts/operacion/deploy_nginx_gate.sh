#!/usr/bin/env bash
set -Eeuo pipefail
# Runs unprivileged; only the fixed, preinstalled root-owned command uses sudo.
[[ $# -eq 2 && "$2" =~ ^[0-9a-f]{40}$ ]] || { echo '[nginx] ERROR: entorno o revision invalida' >&2; exit 1; }
env_name="$1"
revision="$2"
root="${SISOC_ROOT_DIR:?}"
case "$env_name" in
  qa) site='docs/operacion/nginx/sisoc-qa.conf'; pwa='docs/operacion/nginx/sisoc-qa-pwas.conf'; command='/usr/local/sbin/sisoc-nginx-qa' ;;
  production) site='docs/operacion/nginx/sisoc-produccion.conf'; pwa='docs/operacion/nginx/sisoc-pwas.conf'; command='/usr/local/sbin/sisoc-nginx-production' ;;
  homologacion) site='docs/operacion/nginx/sisoc-homologacion.conf'; pwa='docs/operacion/nginx/sisoc-homologacion-pwas.conf'; command='/usr/local/sbin/sisoc-nginx-homologacion' ;;
  *) echo '[nginx] ERROR: entorno desconocido' >&2; exit 1 ;;
esac
anchor_dir='/var/lib/sisoc-nginx'
anchor="$anchor_dir/$env_name.activated"
anchor_present=0
if [[ -e "$anchor_dir" || -L "$anchor_dir" ]]; then
  [[ -d "$anchor_dir" && ! -L "$anchor_dir" && -r "$anchor_dir" && -x "$anchor_dir" ]] || { echo '[nginx] ERROR: estado durable inaccesible' >&2; exit 1; }
  read -r owner permissions < <(stat -c '%u %a' "$anchor_dir")
  [[ "$owner" == 0 && "$permissions" =~ ^[0-7]{3,4}$ ]] || exit 1
  (( (8#$permissions & 8#022) == 0 )) || { echo '[nginx] ERROR: estado durable modificable' >&2; exit 1; }
  if [[ -e "$anchor" || -L "$anchor" ]]; then
    [[ -f "$anchor" && ! -L "$anchor" ]] || { echo '[nginx] ERROR: activacion durable invalida' >&2; exit 1; }
    read -r owner permissions < <(stat -c '%u %a' "$anchor")
    [[ "$owner" == 0 && "$permissions" =~ ^[0-7]{3,4}$ ]] || exit 1
    (( (8#$permissions & 8#022) == 0 )) || { echo '[nginx] ERROR: activacion durable modificable' >&2; exit 1; }
    anchor_present=1
  fi
fi
state='/etc/sisoc-nginx'
if [[ ! -e "$state" && ! -L "$state" ]]; then
  (( anchor_present == 0 )) || { echo '[nginx] ERROR: estado de entorno activado ausente' >&2; exit 1; }
  echo "::warning::Nginx $env_name NO GESTIONADO: no se verifico la configuracion."
  exit 0
fi
[[ -d "$state" && ! -L "$state" ]] || { echo '[nginx] ERROR: directorio de estado invalido' >&2; exit 1; }
[[ -r "$state" && -x "$state" ]] || { echo '[nginx] ERROR: estado no accesible; no se puede verificar onboarding' >&2; exit 1; }
read -r owner permissions < <(stat -c '%u %a' "$state")
[[ "$owner" == 0 && "$permissions" =~ ^[0-7]{3,4}$ ]] || exit 1
(( (8#$permissions & 8#022) == 0 )) || { echo '[nginx] ERROR: directorio de estado modificable' >&2; exit 1; }
flag="$state/$env_name.enabled"
if [[ ! -e "$flag" && ! -L "$flag" ]]; then
  (( anchor_present == 0 )) || { echo '[nginx] ERROR: indicador de entorno activado ausente' >&2; exit 1; }
  echo "::warning::Nginx $env_name NO GESTIONADO: falta onboarding; no se verifico la configuracion."
  exit 0
fi
[[ -f "$flag" && ! -L "$flag" ]] || { echo '[nginx] ERROR: indicador de activacion invalido' >&2; exit 1; }
(( anchor_present == 1 )) || { echo '[nginx] ERROR: activacion durable ausente' >&2; exit 1; }
read -r owner permissions < <(stat -c '%u %a' "$flag")
[[ "$owner" == 0 && "$permissions" =~ ^[0-7]{3,4}$ ]] || exit 1
(( (8#$permissions & 8#022) == 0 )) || { echo '[nginx] ERROR: indicador modificable' >&2; exit 1; }
[[ -n "$site" && -n "$command" ]] || { echo '[nginx] ERROR: configuracion de entorno no soportada' >&2; exit 1; }
# The operator accepts this trust model; Docker access can bypass the helper.
if [[ -S /var/run/docker.sock && -w /var/run/docker.sock ]]; then
  echo '::warning::[nginx] runner con acceso Docker: no existe aislamiento frente a un runner comprometido.' >&2
fi
# Each command is installed root-owned outside the checkout and accepts no args.
[[ -f "$command" && ! -L "$command" ]] || { echo '[nginx] ERROR: helper no instalado' >&2; exit 1; }
for protected in /usr /usr/local /usr/local/sbin "$command"; do
  [[ ! -L "$protected" ]] || { echo '[nginx] ERROR: helper o directorio es enlace' >&2; exit 1; }
  read -r owner permissions < <(stat -c '%u %a' "$protected")
  [[ "$owner" == 0 && "$permissions" =~ ^[0-7]{3,4}$ ]] || exit 1
  (( (8#$permissions & 8#022) == 0 )) || { echo '[nginx] ERROR: helper o directorio modificable' >&2; exit 1; }
done

/usr/bin/python3 - "$root" "$revision" "$site" "$pwa" <<'PY' | /usr/bin/sudo -n "$command"
import base64, json, subprocess, sys
root, revision, site, pwa = sys.argv[1:]
def blob(path):
    return subprocess.check_output(['/usr/bin/git', '-C', root, 'show', revision + ':' + path])
print(json.dumps({'site': base64.b64encode(blob(site)).decode('ascii'), 'pwa': base64.b64encode(blob(pwa)).decode('ascii')}))
PY
