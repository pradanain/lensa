#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
trap 'echo "LENSA deployment stopped at line $LINENO. No other stack was changed." >&2' ERR
cd /srv/stacks/lensa
exec 9>.deploy.lock
flock -n 9 || { echo 'Another LENSA deployment is running.' >&2; exit 1; }
compose=(docker compose --project-name lensa --file compose.yml --env-file .env)
test -f compose.yml || { echo 'Missing compose.yml' >&2; exit 1; }
test -f .env || { echo 'Missing .env' >&2; exit 1; }
test -f /storage/data/lensa/census/se2026.sqlite || { echo 'Missing census database' >&2; exit 1; }
# State files are intentionally inaccessible to the SSH user (directory mode 700,
# owner 10001). The backup container below checks/reads them as the correct UID.
test -d /storage/data/lensa/backups || { echo 'Missing backups directory' >&2; exit 1; }
docker network inspect cloudflared-net >/dev/null
if [[ -n "${1:-}" ]]; then
  [[ "$1" =~ ^ghcr\.io/pradanain/lensa:(sha-[0-9a-f]{40}|latest)$ || "$1" =~ ^ghcr\.io/pradanain/lensa@sha256:[0-9a-f]{64}$ ]] || { echo 'Invalid LENSA image reference.' >&2; exit 1; }
  export LENSA_IMAGE="$1"
fi
registry_config=${LENSA_REGISTRY_CONFIG:-}
if [[ -z "$registry_config" ]]; then
  registry_config=/srv/stacks/lensa/.docker-anonymous
  mkdir -p "$registry_config"
  chmod 700 "$registry_config"
  printf '{}\n' > "$registry_config/config.json"
fi
"${compose[@]}" config --quiet
"${compose[@]}" config --format json | python3 -c 'import json,subprocess,sys; d=json.load(sys.stdin); a=d["services"]["lensa"]["environment"]["FORWARDED_ALLOW_IPS"]; n=json.loads(subprocess.check_output(["docker","network","inspect","cloudflared-net"]))[0]; assert a in [v["Subnet"] for v in n["IPAM"]["Config"]], "TRUSTED_PROXY_SUBNET_MISMATCH"'
available=$(df --output=avail -B1 /storage/data/lensa | tail -1 | tr -d ' ')
(( available > 2147483648 )) || { echo 'At least 2 GiB free storage is required.' >&2; exit 1; }
stamp=$(date -u +%Y%m%dT%H%M%SZ)
old_id=$("${compose[@]}" ps --quiet lensa)
rollback_image=""
if [[ -n "$old_id" ]]; then
  old_image=$(docker inspect --format '{{.Image}}' "$old_id")
  rollback_image="ghcr.io/pradanain/lensa:rollback-$stamp"
  docker image tag "$old_image" "$rollback_image"
fi
image=$("${compose[@]}" config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["lensa"]["image"])')
echo 'Pulling LENSA image with isolated registry configuration...'
docker --config "$registry_config" pull "$image"
# SQLite backup API is safe with the running app's WAL. The census mount is never written.
echo 'Checking private state and creating consistent backups as UID 10001...'
docker run --rm --network none --user 10001:10001 --read-only --cap-drop ALL --security-opt no-new-privileges \
  --mount type=bind,src=/storage/data/lensa/state,dst=/state,readonly \
  --mount type=bind,src=/storage/data/lensa/backups,dst=/backup \
  --entrypoint python "$image" -c 'import sqlite3,sys; a=sqlite3.connect("file:/state/portal.sqlite?mode=ro",uri=True); b=sqlite3.connect("/backup/portal-"+sys.argv[1]+".sqlite"); a.backup(b); assert b.execute("PRAGMA quick_check").fetchone()[0]=="ok"; b.close(); a.close()' "$stamp"
tar -cz compose.yml .env deploy.sh | docker run --rm -i --network none --user 10001:10001 --read-only --cap-drop ALL \
  --mount type=bind,src=/storage/data/lensa/backups,dst=/backup \
  --entrypoint python "$image" -c 'import os,shutil,sys; p="/backup/config-"+sys.argv[1]+".tar.gz"; f=open(p,"xb"); shutil.copyfileobj(sys.stdin.buffer,f); f.close(); os.chmod(p,0o600)' "$stamp"
rollback() {
  if [[ -n "$rollback_image" ]]; then
    echo 'LENSA health failed; restoring previous image. Database backup retained.' >&2
    LENSA_IMAGE="$rollback_image" "${compose[@]}" up -d --no-deps --pull never lensa || echo 'Rollback also failed; inspect only the LENSA stack.' >&2
  fi
}
trap 'rollback' ERR
echo 'Starting only the LENSA service...'
"${compose[@]}" up -d --no-deps --pull never lensa
healthy=false
for _ in $(seq 1 120); do
  cid=$("${compose[@]}" ps --quiet lensa)
  state=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$cid")
  if [[ "$state" == healthy ]]; then healthy=true; break; fi
  if [[ "$state" == unhealthy ]]; then break; fi
  sleep 2
done
[[ "$healthy" == true ]] || { rollback; exit 1; }
trap - ERR
printf '%s\n' "$image" > /srv/stacks/lensa/.last-successful-image
printf '%s\n' "$rollback_image" > /srv/stacks/lensa/.rollback-image
"${compose[@]}" ps
echo 'LENSA container healthy. Verify public HTTPS, assets and authorization before declaring deployment complete.'
