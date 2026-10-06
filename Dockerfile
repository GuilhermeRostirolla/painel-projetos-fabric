FROM python:3.12-slim

WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY simulador/ simulador/
COPY api/ api/

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.app:criar_app --factory --host 0.0.0.0 --port ${PORT}"]
