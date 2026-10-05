# syntax=docker/dockerfile:1
#
# Imagen compartida por todas las apps de frontends/. El modulo se elige con
# `ARG APP`, asi que agregar una app no agrega un Dockerfile.
#
#   docker build --build-arg APP=celiaquia --target prod -f frontends/Dockerfile frontends/
ARG APP=vpsl

# --- Desarrollo: Vite con hot reload -----------------------------------------
# El navegador entra por Django (/v2/<modulo>/), pero el websocket de HMR
# conecta directo al puerto de Vite, porque Django no reenvia websockets.
FROM node:22.14.0 AS dev
ARG APP
ENV APP=${APP}
WORKDIR /app
COPY . .
RUN npm ci
EXPOSE 5173
CMD ["sh", "-c", "npm run dev -w @sisoc/${APP} -- --host 0.0.0.0"]

# --- Build de produccion ------------------------------------------------------
FROM dev AS build
ARG VITE_SENTRY_DSN
ARG VITE_SENTRY_ENVIRONMENT
ARG VITE_RELEASE_SHA
RUN npm run build -w @sisoc/${APP}

# --- Produccion: estatico servido por nginx sin privilegios -------------------
# El `dist` se copia bajo /v2/<app>/ porque es el `base` con el que Vite genero
# las rutas de los assets con hash; servirlo desde la raiz los rompe.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS prod
ARG APP
COPY --from=build /app/apps/${APP}/dist /usr/share/nginx/html/v2/${APP}
COPY nginx.conf.template /tmp/default.conf.template
RUN sed "s/@APP@/${APP}/g" /tmp/default.conf.template > /etc/nginx/conf.d/default.conf
# Puerto interno: solo lo alcanza Django por la red de compose.
EXPOSE 8080
