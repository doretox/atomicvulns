FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Plant a DUMMY app secret for the out-of-band channel to carry in the exfil URL. Obviously fake,
# lab-only (see CLAUDE.md security rules). Written with NO trailing newline (printf, no \n): a
# newline in the file content would break the constructed exfil URI, so the secret is a single
# line of URL-safe characters. Planted in BOTH images so a fixed-side no-leak is the PARSER, not a
# missing file.
RUN printf 'FLAG-xxe30-9f1c2a-EXAMPLE-not-a-real-secret' > /app/secret.txt
# Override default host (127.0.0.1) so Docker's port forwarding can reach Flask.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["python", "-u", "app.py"]
