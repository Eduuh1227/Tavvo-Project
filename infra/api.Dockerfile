FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY apps/api/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock \
    && groupadd --system tavvo && useradd --system --gid tavvo --home /app tavvo
COPY apps/api /app/apps/api
COPY scripts /app/scripts
COPY infra /app/infra
USER tavvo
EXPOSE 8000
CMD ["gunicorn", "--chdir", "apps/api", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--error-logfile", "-"]
