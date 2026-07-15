FROM python:3.11-slim

LABEL org.opencontainers.image.title="Vulhub-Web"
LABEL org.opencontainers.image.description="Web-based Vulnerability Lab Management Platform"
LABEL org.opencontainers.image.url="https://github.com/your-org/vulhub-web"

RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

EXPOSE 8088

CMD ["python", "run.py"]
