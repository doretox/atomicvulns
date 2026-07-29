FROM mongo:7.0
# Bake the seed into the image so it runs on first init, with no bind mount.
# (Bind-mounting the seed is the usual approach, but SELinux on the host blocks
# bind mounts into containers, so the seed is COPYed into a thin image instead.)
COPY mongo-init.js /docker-entrypoint-initdb.d/
