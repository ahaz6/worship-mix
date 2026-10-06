FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/ /app/
COPY presets/ /presets/
RUN pip install --no-cache-dir -e .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
