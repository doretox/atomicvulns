FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Override default host (127.0.0.1) so other containers on the Docker network can reach Flask.
# This service is never published to the host (no ports: in docker-compose.yml).
ENV HOST=0.0.0.0
EXPOSE 80
CMD ["python", "-u", "app.py"]
