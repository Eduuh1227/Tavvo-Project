FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/admin ./apps/admin
COPY apps/public-reference ./apps/public-reference
COPY packages ./packages
RUN npm ci --include=dev && npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NEXT_TELEMETRY_DISABLED=1 NODE_ENV=production API_INTERNAL_URL=http://127.0.0.1:8000
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends nginx supervisor libatomic1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --home /app tavvo
COPY apps/api/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend /app/node_modules ./node_modules
COPY --from=frontend /app/apps/public-reference ./apps/public-reference
COPY --from=frontend /app/packages/api-client ./packages/api-client
COPY --from=frontend /app/apps/admin/dist ./apps/admin/dist
COPY apps/api ./apps/api
COPY infra/render-nginx.conf /etc/tavvo/nginx.conf
COPY infra/render-supervisor.conf /etc/tavvo/supervisor.conf
RUN mkdir -p /app/apps/public-reference/.next/cache && chown tavvo /app/apps/public-reference/.next/cache
USER tavvo
EXPOSE 10000
CMD ["supervisord", "-c", "/etc/tavvo/supervisor.conf"]
