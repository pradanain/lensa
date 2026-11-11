#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cd /srv/stacks/lensa
exec 9>.deploy.lock
flock -n 9 || { echo 'Another LENSA deployment is running.' >&2; exit 1; }
compose=(docker compose --project-name lensa --file compose.yml --env-file .env)
test -f compose.yml && test -f .env
test -f /storage/data/lensa/census/se2026.sqlite
test -f /storage/data/lensa/state/portal.sqlite
test -d /storage/data/lensa/backups
docker network inspect cloudflared-net >/dev/null
if [[ -n "${1:-}" ]]; then
  [[ "$1" =~ ^ghcr\.io/pradanain/lensa:(sha-[0-9a-f]{40}|latest)$ || "$1" =~ ^ghcr\.io/pradanain/lensa@sha256:[0-9a-f]{64}$ ]] || { echo 'Invalid LENSA image reference.' >&2; exit 1; }
  export LENSA_IMAGE="$1"
fi
if [[ -f /srv/stacks/lensa/.docker/config.json ]]; then
  export DOCKER_CONFIG=/srv/stacks/lensa/.docker
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
"${compose[@]}" pull lensa
image=$("${compose[@]}" config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["lensa"]["image"])')
# SQLite backup API is safe with the running app's WAL. The census mount is never written.
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
    LENSA_IMAGE="$rollback_image" "${compose[@]}" up -d --no-deps lensa || echo 'Rollback also failed; inspect only the LENSA stack.' >&2
  fi
}
trap 'rollback' ERR
"${compose[@]}" up -d --no-deps lensa
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
