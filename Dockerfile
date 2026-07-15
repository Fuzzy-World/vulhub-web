FROM python:3.11-slim

LABEL org.opencontainers.image.title="Vulhub-Web"
LABEL org.opencontainers.image.description="Web-based Vulnerability Lab Management Platform"
LABEL org.opencontainers.image.url="https://github.com/Fuzzy-World/vulhub-web"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data
RUN mkdir -p /vulhub

EXPOSE 8088

VOLUME ["/vulhub", "/var/run/docker.sock"]

CMD ["python", "run.py"]
