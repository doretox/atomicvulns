# Pinned LTS base by tag AND digest (Node 22 "Jod" LTS).
FROM node:22-bookworm-slim@sha256:f32b81066cde10a75dbac96646099533316d94bac4150c55da1636e1f0ffdc46
WORKDIR /app
COPY package.json .
# No `npm install`: zero runtime dependencies (http + JSON are stdlib).
COPY app.js .
# Override default host (127.0.0.1) so Docker's port forwarding can reach Node.
# Host-side exposure is still restricted to 127.0.0.1 by docker-compose.yml.
ENV HOST=0.0.0.0
EXPOSE 5000
CMD ["node", "app.js"]
