ARG APP=vpsl
FROM node:22.14.0 AS dev
ARG APP
ENV APP=${APP}
WORKDIR /app
COPY . .
RUN npm ci
EXPOSE 5173
CMD ["sh", "-c", "npm run dev -w @sisoc/${APP} -- --host 0.0.0.0"]

FROM dev AS build
ARG VITE_SENTRY_DSN
ARG VITE_SENTRY_ENVIRONMENT
ARG VITE_RELEASE_SHA
RUN npm run build -w @sisoc/${APP}

FROM nginxinc/nginx-unprivileged:1.27-alpine AS prod
ARG APP
COPY --from=build /app/apps/${APP}/dist /usr/share/nginx/html/v2/${APP}
COPY nginx.conf.template /tmp/default.conf.template
RUN sed "s/@APP@/${APP}/g" /tmp/default.conf.template > /etc/nginx/conf.d/default.conf
EXPOSE 8080
