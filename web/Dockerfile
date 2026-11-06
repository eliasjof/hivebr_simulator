# syntax=docker/dockerfile:1
# Contexto de build: a raiz do repositório (docker compose -f web/docker-compose.yml).
# O build do web/ lê src/hivebr, config/ e examples/ fora de web/, por isso o contexto é a raiz.

# ---- build: gera web/dist/ (inclui o zip do Python via scripts/bundle-python.mjs) ----
FROM node:24-alpine AS build

WORKDIR /app

# Dependências primeiro, para o cache da camada npm ci.
COPY web/package.json web/package-lock.json /app/web/
WORKDIR /app/web
RUN npm ci --no-audit --no-fund

# Fontes do pacote Python e do bundle (o bundle lê ../src, ../config, ../examples).
COPY src/hivebr /app/src/hivebr
COPY config /app/config
COPY examples /app/examples

# Fontes do site.
COPY web/index.html web/vite.config.js /app/web/
COPY web/scripts /app/web/scripts
COPY web/python /app/web/python
COPY web/templates /app/web/templates
COPY web/src /app/web/src
COPY web/public /app/web/public

RUN npm run build

# ---- final: nginx sem root servindo apenas web/dist ----
FROM nginxinc/nginx-unprivileged:1.29-alpine AS final

COPY web/docker/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/web/dist /usr/share/nginx/html

USER 101
EXPOSE 8080
