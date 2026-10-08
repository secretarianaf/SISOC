"""Transición y rollback de rutas, sin Git, Docker ni servidores reales."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[4]
WRAPPER = REPO_ROOT / "src/scripts/operacion/deploy_verified.sh"
BASH = (
    str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe")
    if os.name == "nt"
    else shutil.which("bash")
)
pytestmark = pytest.mark.skipif(
    not BASH or not Path(BASH).is_file(), reason="Requiere Bash"
)
PREVIOUS = "a" * 40
EXPECTED = "b" * 40


def _script(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("#!/usr/bin/env bash\nset -eu\n" + content).encode("utf-8"))
    path.chmod(0o755)


@pytest.mark.parametrize("rollback_legacy", [False, True])
@pytest.mark.parametrize("fail_health", [False, True])
def test_wrapper_transicion_y_rollback(tmp_path, rollback_legacy, fail_health):
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    registry = checkout / "src/backends/config/backends.json"
    registry.parent.mkdir(parents=True)
    registry.write_text("{}", encoding="utf-8")
    compose = checkout / "docker/compose/docker-compose.deploy.yml"
    compose.parent.mkdir(parents=True)
    compose.write_text("", encoding="utf-8")
    (checkout / ".head").write_text(PREVIOUS, encoding="utf-8")
    new_scripts = checkout / "src/scripts"
    old_scripts = checkout / "scripts" if rollback_legacy else new_scripts
    refresh = 'printf "refresh:%s\\n" "$*" >> "$MOCK_LOG"\n'
    # El deploy_refresh.sh nuevo admite --diff-base; el de main lo rechaza.
    _script(checkout / "pending_refresh.sh", "# --diff-base\n" + refresh)
    _script(
        old_scripts / "operacion/deploy_refresh.sh",
        (
            '[[ " $* " != *" $MOCK_FLAG_NUEVO "* ]] || exit 3\n'
            if rollback_legacy
            else "# --diff-base\n"
        )
        + refresh,
    )
    _script(old_scripts / "infra/healthcheck_hml.sh", "exit 0\n")
    new_scripts.joinpath("operacion").mkdir(parents=True, exist_ok=True)
    _script(new_scripts / "infra/healthcheck_hml.sh", "exit 0\n")
    if not rollback_legacy:
        (new_scripts / "operacion/deploy_refresh.sh").unlink()

    fake_bin = tmp_path / "bin"
    _script(
        fake_bin / "git",
        """[[ "$1" == "-C" ]]
repo="$2"
shift 2
case "$1" in
  branch) echo homologacion ;;
  diff|fetch) exit 0 ;;
  rev-parse)
    if [[ "$2" == HEAD ]]; then cat "$repo/.head"; else echo "$MOCK_EXPECTED"; fi ;;
  merge)
    printf 'merge:%s\\n' "$3" >> "$MOCK_LOG"
    cp "$repo/pending_refresh.sh" "$repo/src/scripts/operacion/deploy_refresh.sh"
    echo "$MOCK_EXPECTED" > "$repo/.head" ;;
  reset)
    printf 'reset:%s\\n' "$3" >> "$MOCK_LOG"
    if [[ "$MOCK_LEGACY" == 1 ]]; then
      mv "$repo/src/scripts/operacion/deploy_refresh.sh" "$repo/removed_refresh.sh"
      mv "$repo/src/scripts/infra/healthcheck_hml.sh" "$repo/removed_health.sh"
      rm -r "$repo/docker" "$repo/src/backends"
    fi
    echo "$MOCK_PREVIOUS" > "$repo/.head" ;;
  *) exit 2 ;;
esac
""",
    )
    _script(
        fake_bin / "docker",
        """printf 'docker:%s\\n' "$*" >> "$MOCK_LOG"
if [[ "$MOCK_FAIL" == 1 && "$SISOC_RELEASE_SHA" == "$MOCK_EXPECTED" && "$*" == *"migrate --check"* ]]; then
  exit 1
fi
exit 0
""",
    )
    _script(fake_bin / "python3", '[[ -f "$3" ]]\necho backend_demo\n')
    _script(fake_bin / "sleep", "exit 0\n")
    log = tmp_path / "calls.log"
    env = os.environ.copy()
    env.update(
        SISOC_ROOT_DIR=checkout.as_posix(),
        MOCK_LOG=log.as_posix(),
        MOCK_EXPECTED=EXPECTED,
        MOCK_PREVIOUS=PREVIOUS,
        MOCK_FAIL=str(int(fail_health)),
        MOCK_LEGACY=str(int(rollback_legacy)),
        MOCK_FLAG_NUEVO="--diff-base",
        MOCK_BIN=fake_bin.as_posix(),
        PATH=str(fake_bin) + os.pathsep + env["PATH"],
    )
    env.pop("GITHUB_STEP_SUMMARY", None)
    result = subprocess.run(
        [
            BASH,
            "-c",
            'if command -v cygpath >/dev/null; then MOCK_BIN=$(cygpath -u "$MOCK_BIN"); fi; '
            'export PATH="$MOCK_BIN:$PATH"; '
            '[[ "$(command -v git)" == "$MOCK_BIN/git" ]] || exit 99; '
            'exec bash "$@"',
            "_",
            WRAPPER.as_posix(),
            "--environment",
            "homologacion",
            "--expected-revision",
            EXPECTED,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert log.is_file(), result.stdout + result.stderr
    calls = log.read_text(encoding="utf-8")
    assert calls.startswith(f"merge:{EXPECTED}\nrefresh:"), result.stderr
    assert "--skip-pull" in calls
    if fail_health:
        assert result.returncode != 0
        assert f"reset:{PREVIOUS}" in calls
        assert f"--expected-revision {PREVIOUS}" in calls
        assert "Rollback verificado" in result.stdout, result.stderr
        rollback = calls.split(f"reset:{PREVIOUS}\n", 1)[1]
        if rollback_legacy:
            # main: refresh completo, compose de la raíz y migrate en django.
            assert "--diff-base" not in rollback
            assert f"-f {checkout.as_posix()}/docker-compose.deploy.yml" in rollback
            assert "exec -T django python manage.py migrate --check" in rollback
            assert "migrator" not in rollback
        else:
            assert f"--diff-base {EXPECTED}" in rollback
            assert "docker/compose/docker-compose.deploy.yml" in rollback
    else:
        assert result.returncode == 0, result.stderr
        assert "reset:" not in calls
    assert (checkout / ".head").read_text(encoding="utf-8").strip() == (
        PREVIOUS if fail_health else EXPECTED
    )
