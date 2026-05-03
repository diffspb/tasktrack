# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Keycloak settings are baked into the JS bundle at build time
ARG VITE_KEYCLOAK_URL=https://auth.busypage.ru
ARG VITE_KEYCLOAK_REALM=home
ARG VITE_KEYCLOAK_CLIENT_ID=tasktrack
ENV VITE_AUTH_STUB=false \
    VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL \
    VITE_KEYCLOAK_REALM=$VITE_KEYCLOAK_REALM \
    VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID

COPY frontend/ .
RUN npm run build

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS backend-builder
WORKDIR /app
RUN python -m venv /venv
COPY backend/pyproject.toml .
COPY backend/app/ ./app/
RUN /venv/bin/pip install --no-cache-dir .

# Stage 3: Final image
FROM python:3.12-slim
WORKDIR /app

COPY --from=backend-builder /venv /venv
COPY --from=backend-builder /app/app ./app
COPY --from=frontend-builder /frontend/dist ./frontend/dist

ENV PATH="/venv/bin:$PATH" \
    PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
