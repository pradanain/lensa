"""Exercise the Bash health/rollback lifecycle without Docker or private data."""

from pathlib import Path
import shutil
import shlex
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
SCRIPT = (ROOT / "app/deploy/deploy.sh").read_text(encoding="utf-8")


@pytest.mark.skipif(not BASH, reason="Bash unavailable")
@pytest.mark.parametrize(
    "scenario,success",
    [("healthy", True), ("slow", True), ("unhealthy", False),
     ("exited", False), ("missing", False), ("timeout", False), ("up_error", False)],
)
def test_health_lifecycle_reports_failure_before_single_rollback(scenario, success):
    lifecycle = SCRIPT.split("diagnose_failure() {", 1)[1].split(
        '\ntrap - ERR\nprintf', 1
    )[0]
    harness = r'''
set -Eeuo pipefail
compose=(compose_mock)
rollback_image=synthetic-previous
health_timeout=600
SECONDS=0
compose_mock() {
  case "$1" in
    up)
      if [[ "${LENSA_IMAGE:-}" == synthetic-previous ]]; then
        echo ROLLBACK >&2
      elif [[ "$scenario" == up_error ]]; then
        return 1
      fi ;;
    ps)
      [[ "$*" == *--all* ]] || return 2
      echo synthetic-container ;;
  esac
}
docker() {
  if [[ "$1" == logs ]]; then
    echo 'RuntimeError: PRODUCTION_ADMIN_NOT_PROVISIONED private-synthetic-value'
    return
  fi
  case "$3" in
    '{{.State.Status}}')
      if [[ "$scenario" == exited ]]; then echo exited; else echo running; fi ;;
    '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}')
      case "$scenario" in
        slow) if (( SECONDS >= 300 )); then echo healthy; else echo starting; fi ;;
        timeout) echo starting ;;
        *) echo "$scenario" ;;
      esac ;;
    status=*) echo 'STATE_DIAGNOSTIC exit=1 oom_killed=false' ;;
    *) echo 'PROBE_DIAGNOSTIC exit=1' ;;
  esac
}
sleep() { SECONDS=$((SECONDS + 150)); }
'''
    interpreter = shlex.quote(sys.executable.replace("\\", "/"))
    harness += '\npython3() { ' + interpreter + ' "$@"; }\n'
    result = subprocess.run(
        [BASH, "-c", harness + '\nscenario="' + scenario + '"\ndiagnose_failure() {' + lifecycle],
        text=True, capture_output=True, timeout=15,
    )
    assert (result.returncode == 0) == success, result.stderr
    if success:
        assert "ROLLBACK" not in result.stderr
    else:
        assert result.stderr.count("ROLLBACK") == 1
        assert result.stderr.index("STATE_DIAGNOSTIC") < result.stderr.index("ROLLBACK")
        assert "PROBE_DIAGNOSTIC" in result.stderr
        assert "startup_error=PRODUCTION_ADMIN_NOT_PROVISIONED" in result.stderr
        assert "private-synthetic-value" not in result.stderr
