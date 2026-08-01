#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${BASE:-/opt/ivrm/compose/minecraft-main}"
CONTAINER="${CONTAINER:-mc-main}"
OUT="${OUT:-/tmp/ivrm-velocity-prerequisites-$(date +%Y%m%d-%H%M%S).txt}"

{
  echo "===== timestamp ====="
  date --iso-8601=seconds

  echo
  echo "===== container state ====="
  docker inspect "${CONTAINER}" \
    --format 'Status={{.State.Status}} Health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} RestartCount={{.RestartCount}} OOMKilled={{.State.OOMKilled}}'

  echo
  echo "===== published ports ====="
  docker port "${CONTAINER}" || true

  echo
  echo "===== mounts ====="
  docker inspect "${CONTAINER}" \
    --format '{{range .Mounts}}{{println .Type .Source "->" .Destination}}{{end}}'

  echo
  echo "===== networks ====="
  docker inspect "${CONTAINER}" \
    --format '{{range $name, $network := .NetworkSettings.Networks}}{{println $name $network.IPAddress}}{{end}}'

  echo
  echo "===== selected environment ====="
  docker inspect "${CONTAINER}" \
    --format '{{range .Config.Env}}{{println .}}{{end}}' |
    grep -E '^(TYPE|VERSION|NEOFORGE_VERSION|SERVER_PORT|ONLINE_MODE|ENFORCE_SECURE_PROFILE|ENABLE_RCON|RCON_PORT|MEMORY|INIT_MEMORY|MAX_MEMORY|OPS|WHITELIST|ENABLE_WHITELIST)=' || true

  echo
  echo "===== server.properties ====="
  grep -E '^(server-port|server-ip|online-mode|white-list|enforce-secure-profile|prevent-proxy-connections|motd|simulation-distance|view-distance)=' \
    "${BASE}/data/server.properties" || true

  echo
  echo "===== compose files ====="
  find "${BASE}" -maxdepth 2 -type f \
    \( -iname 'compose.yml' -o -iname 'compose.yaml' -o -iname 'docker-compose.yml' -o -iname 'docker-compose.yaml' -o -iname '.env' \) \
    -print

  echo
  echo "===== compose service summary ====="
  if docker compose -f "${BASE}/compose.yml" config >/dev/null 2>&1; then
    docker compose -f "${BASE}/compose.yml" config --services
    docker compose -f "${BASE}/compose.yml" config 2>/dev/null |
      grep -nE '(^services:|^[[:space:]]{2}[A-Za-z0-9_.-]+:|image:|container_name:|ports:|25565|networks:|restart:)' || true
  elif docker compose -f "${BASE}/docker-compose.yml" config >/dev/null 2>&1; then
    docker compose -f "${BASE}/docker-compose.yml" config --services
    docker compose -f "${BASE}/docker-compose.yml" config 2>/dev/null |
      grep -nE '(^services:|^[[:space:]]{2}[A-Za-z0-9_.-]+:|image:|container_name:|ports:|25565|networks:|restart:)' || true
  else
    echo "compose config unavailable at expected paths"
  fi

  echo
  echo "===== listening sockets ====="
  sudo ss -lntup 2>/dev/null |
    grep -E '(:25565|:25566|:25567|:25575|:24454)' || true

  echo
  echo "===== host resources ====="
  free -h
  nproc
  df -h "${BASE}" || true

  echo
  echo "===== container resources ====="
  docker stats --no-stream "${CONTAINER}" || true

  echo
  echo "===== recent startup markers ====="
  docker logs --since 30m "${CONTAINER}" 2>&1 |
    grep -E 'Done \(|RCON running|Starting remote control|IVRM Permission Control|PermissionAPI|FatalStartupException|ModLoadingException' |
    tail -100 || true
} | tee "${OUT}"

echo
echo "Report=${OUT}"
