# syntax=docker/dockerfile:1
#
# Imagen compartida por todas las apps de src/frontends/. El modulo se elige con
# `ARG APP`, asi que agregar una app no agrega un Dockerfile.
#
#   docker build --build-arg APP=celiaquia --target prod -f docker/frontends/Dockerfile .
ARG APP=vpsl

# --- Desarrollo: Vite con hot reload -----------------------------------------
# El navegador entra por Django (/v2/<modulo>/), pero el websocket de HMR
# conecta directo al puerto de Vite, porque Django no reenvia websockets.
FROM node:22.14.0 AS dev
ARG APP
ENV APP=${APP}
WORKDIR /app/src/frontends
COPY src/frontends/ .
COPY src/scripts/frontends/ ../scripts/frontends/
RUN npm ci
EXPOSE 5173
CMD ["sh", "-c", "npm run dev -w @sisoc/${APP} -- --host 0.0.0.0"]

# --- Build de produccion ------------------------------------------------------
FROM dev AS build
ARG VITE_SENTRY_DSN
ARG VITE_SENTRY_ENVIRONMENT
ARG VITE_RELEASE_SHA
ARG APP_ROUTE
RUN npm run build -w @sisoc/${APP} \
    && mkdir -p "/tmp/frontend/${APP_ROUTE:-${APP}}" \
    && cp -a "apps/${APP}/dist/." "/tmp/frontend/${APP_ROUTE:-${APP}}/"

# --- Export del build ----------------------------------------------------------
# Solo el `dist` (index.html + assets/). Lo consumen los runtimes con
# `COPY --from=<este stage>` para las entradas web_preview_* (SISOC_REACT_BUILD_DIR).
FROM scratch AS export
ARG APP
COPY --from=build /app/src/frontends/apps/${APP}/dist /

# --- Produccion: estatico servido por nginx sin privilegios -------------------
# El `dist` se copia bajo /v2/<app>/ porque es el `base` con el que Vite genero
# las rutas de los assets con hash; servirlo desde la raiz los rompe.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS prod
ARG APP
ARG APP_ROUTE
COPY --from=build /tmp/frontend/ /usr/share/nginx/html/v2/
COPY docker/frontends/nginx.conf.template /tmp/default.conf.template
RUN sed "s/@APP@/${APP_ROUTE:-${APP}}/g" /tmp/default.conf.template > /etc/nginx/conf.d/default.conf
# Puerto interno: solo lo alcanza Django por la red de compose.
EXPOSE 8080
