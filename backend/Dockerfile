FROM python:3.11-slim

# Runtime lib for OR-Tools. All Python deps ship manylinux wheels, so no compiler in the image (smaller, faster cold starts).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications first for layer caching
COPY requirements.txt pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Set default environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    AGENT_RUNTIME=local

EXPOSE 8080

# Cloud Run injects $PORT (default 8080)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
