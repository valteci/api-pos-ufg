#!/bin/sh

# Gera o documento servido pelo Nginx sem gravar a credencial no repositório.
set -eu

caminho_modelo="${CAMINHO_MODELO_FRONTEND:-/opt/frontend/index.html.template}"
caminho_saida="${CAMINHO_INDEX_FRONTEND:-/usr/share/nginx/html/index.html}"
token_codificado="$(printf '%s' "${AUTH_TOKEN:?AUTH_TOKEN deve ser configurado}" | base64 | tr -d '\n')"

sed "s|__AUTH_TOKEN_BASE64__|${token_codificado}|g" "${caminho_modelo}" > "${caminho_saida}"
