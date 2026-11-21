FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Download the embedding model at build time so the first request is fast
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as D; D()(['warm up'])"
COPY app ./app
RUN useradd -m appuser && chown -R appuser /app
USER appuser
ENV ENV=production
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
