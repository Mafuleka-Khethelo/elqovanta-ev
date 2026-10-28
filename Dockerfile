FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13.9-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend \
    SERVE_FRONTEND=true INITIALIZE_DATABASE=true \
    ARTIFACT_PATH=/app/ev_charger_bundle.joblib \
    ENVIRONMENT_MANIFEST_PATH=/app/model_environment.json \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
WORKDIR /app
COPY backend/requirements.lock.txt /app/backend/requirements.lock.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.lock.txt
RUN useradd --create-home --uid 10001 elqovanta
COPY --chown=10001:10001 backend/ /app/backend/
COPY --chown=10001:10001 scripts/ /app/scripts/
COPY --chown=10001:10001 ev_charger_bundle.joblib model_environment.json /app/
RUN python -c "import hashlib; assert hashlib.file_digest(open('/app/ev_charger_bundle.joblib','rb'),'sha256').hexdigest() == 'b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626', 'Saved model checksum changed'"
COPY --from=frontend --chown=10001:10001 /build/frontend/dist /app/frontend/dist
USER 10001
EXPOSE 8000
CMD ["python", "-m", "app.serve"]
