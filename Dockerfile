FROM node:20-bookworm-slim AS frontend-build

WORKDIR /workspace/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS backend-runtime

WORKDIR /app
COPY backend /app/backend
RUN --mount=type=cache,target=/root/.cache/uv-deploy \
    uv venv --clear /app/backend/.venv \
    && UV_CACHE_DIR=/root/.cache/uv-deploy \
       UV_LINK_MODE=copy \
       UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
       UV_HTTP_TIMEOUT=300 \
       UV_HTTP_RETRIES=5 \
       uv pip install --python /app/backend/.venv/bin/python -e /app/backend

COPY --from=frontend-build /workspace/frontend/dist /app/frontend/dist

ENV PATH="/app/backend/.venv/bin:${PATH}" \
    PYTHONPATH="/app/backend/src" \
    PYTHONDONTWRITEBYTECODE="1"

RUN mkdir -p /data/uploads
EXPOSE 8000

CMD ["uvicorn", "outfit_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM caddy:2-alpine AS frontend-runtime

COPY --from=frontend-build /workspace/frontend/dist /srv
