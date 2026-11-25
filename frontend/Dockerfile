# Build the static bundle, then serve it from nginx.
#
# The previous version ran `npm run dev` — the Vite development server — as the
# container's process. That is not a deployment: it serves unminified modules,
# exposes the dev server's file access, and has no cache or SPA behaviour. This
# builds `dist/` and serves it the way a browser expects.

FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

# Drop privileges: run nginx as the unprivileged `nginx` user that already
# exists in the nginx:alpine image (no base-image change, no new packages).
# The image defaults assume root, so the paths nginx must write at runtime
# (pid file under /run, cache, logs) plus the served bundle and config are
# handed to that user first; COPY/probe behaviour is otherwise unchanged.
# Port 80 stays the listen port: a default Docker runtime grants
# CAP_NET_BIND_SERVICE, so binding it unprivileged works there. Under a
# hardened runtime that drops that capability, remap the listen port instead
# of running as root again.
RUN chown -R nginx:nginx /usr/share/nginx/html /etc/nginx/conf.d /var/cache/nginx /var/log/nginx \
    && mkdir -p /run \
    && chown nginx:nginx /run
USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
