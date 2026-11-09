#!/usr/bin/env bash
# Deploy por pull: se a branch acompanhada recebeu commits novos, atualiza o
# clone e reconstrói o contêiner. Roda pelo timer hivebr-deploy.timer.
#
# Configuração (variáveis de ambiente, ver hivebr-deploy.service):
#   HIVEBR_DIR     clone do repositório no servidor   (padrão /docker/hivebr)
#   HIVEBR_BRANCH  branch acompanhada                 (padrão feature/browser-simulator)
#   HIVEBR_BIND    endereço:porta publicado           (padrão do docker-compose.yml)
#
# Se o build falhar, o contêiner atual continua no ar e o mesmo commit só é
# tentado de novo quando houver outro commit (ou com --force).
set -euo pipefail

DIR="${HIVEBR_DIR:-/docker/hivebr}"
BRANCH="${HIVEBR_BRANCH:-feature/browser-simulator}"
STATE="$DIR/.deploy-state"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

log() { printf '%s hivebr-deploy: %s\n' "$(date -Is)" "$*"; }

exec 9>"/run/hivebr-deploy.lock"
flock -n 9 || { log "outro deploy em andamento, saindo"; exit 0; }

cd "$DIR"
git fetch --quiet origin "$BRANCH"
REMOTE="$(git rev-parse FETCH_HEAD)"
LAST="$(cat "$STATE" 2>/dev/null || true)"

if [ "$FORCE" -eq 0 ] && [ "$REMOTE" = "$LAST" ]; then
  exit 0   # nada novo (ou já tentado e falhou): silencioso
fi

log "atualizando ${LAST:0:7} -> ${REMOTE:0:7} ($BRANCH)"
git checkout --quiet -B "$BRANCH" FETCH_HEAD
git reset --quiet --hard FETCH_HEAD

# Registra antes do build: um commit com build quebrado não entra em loop.
echo "$REMOTE" > "$STATE"

if ! docker compose -f web/docker-compose.yml up -d --build; then
  log "FALHA no build/up de ${REMOTE:0:7}; contêiner anterior mantido"
  exit 1
fi

for _ in $(seq 1 30); do
  status="$(docker inspect -f '{{.State.Health.Status}}' hivebr-web-1 2>/dev/null || echo none)"
  [ "$status" = "healthy" ] && { log "ok: ${REMOTE:0:7} no ar (healthy)"; docker image prune -f >/dev/null; exit 0; }
  sleep 2
done
log "AVISO: ${REMOTE:0:7} subiu mas não ficou healthy (status=$status)"
exit 1
