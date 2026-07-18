FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY keys ./keys
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
