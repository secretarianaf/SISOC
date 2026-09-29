# syntax=docker/dockerfile:1
#
# Imagen compartida por todas las apps de frontends/. El modulo se elige con
# `ARG APP`, asi que agregar una app no agrega un Dockerfile.
#
#   docker build --build-arg APP=celiaquia --target prod -f frontends/Dockerfile frontends/

ARG APP=celiaquia

FROM node:22.14.0-alpine AS deps
WORKDIR /front
# El lockfile es unico para todo el front v2: se instala el workspace completo.
COPY package.json package-lock.json .npmrc ./
COPY packages/ui/package.json packages/ui/
COPY packages/api/package.json packages/api/
COPY apps/celiaquia/package.json apps/celiaquia/
RUN npm ci

FROM deps AS source
COPY . .

# --- Desarrollo: Vite con hot reload -----------------------------------------
# El navegador entra por Django (/v2/<modulo>/), pero el websocket de HMR
# conecta directo al puerto de Vite, porque Django no reenvia websockets.
FROM source AS dev
ARG APP
ENV APP=${APP}
EXPOSE 5173
CMD ["sh", "-c", "npm run dev --workspace @sisoc/${APP} -- --host 0.0.0.0"]

# --- Build de produccion ------------------------------------------------------
FROM source AS build
ARG APP
RUN npm run build --workspace @sisoc/${APP}

# --- Produccion: estatico servido por nginx sin privilegios -------------------
FROM nginxinc/nginx-unprivileged:1.27-alpine AS prod
ARG APP
COPY --from=build /front/apps/${APP}/dist /usr/share/nginx/html
# Puerto interno: solo lo alcanza Django por la red de compose.
EXPOSE 8080
