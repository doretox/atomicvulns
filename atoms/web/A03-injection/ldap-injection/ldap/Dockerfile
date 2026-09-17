# OpenLDAP directory for the lab, built from Debian's slapd. The seed (LDIF) and
# the ACL are baked into the image at build time: the data lives in the image,
# with no bind mount (SELinux on the maintainer's host blocks bind mounts into
# containers). The directory is reachable only on the compose's internal network.
FROM debian:12-slim@sha256:abd67ffcfa541b485a3dff59865ab629aa048a6c613e639d36e7456b0b229241
ENV DEBIAN_FRONTEND=noninteractive

# Preseed slapd so the package configures a directory non-interactively:
# base dc=example,dc=com, rootdn cn=admin, MDB backend. Dummy admin password.
RUN set -eux; \
    echo "slapd slapd/no_configuration boolean false" | debconf-set-selections; \
    echo "slapd slapd/domain string example.com"      | debconf-set-selections; \
    echo "slapd shared/organization string Example"   | debconf-set-selections; \
    echo "slapd slapd/password1 password changeme"     | debconf-set-selections; \
    echo "slapd slapd/password2 password changeme"     | debconf-set-selections; \
    echo "slapd slapd/backend string MDB"              | debconf-set-selections; \
    apt-get update; \
    apt-get install -y --no-install-recommends slapd ldap-utils; \
    rm -rf /var/lib/apt/lists/*

COPY acl.ldif seed.ldif /seed/

# Start slapd on the local socket only, apply the ACL (as the config root over
# EXTERNAL) and the data (as cn=admin), then stop it -- the result is baked into
# the image. See acl.ldif for the userPassword ACL and seed.ldif for the entries.
RUN set -eux; \
    mkdir -p /run/slapd; chown openldap:openldap /run/slapd; \
    slapd -h "ldapi:///" -u openldap -g openldap; \
    for i in $(seq 1 30); do ldapsearch -Y EXTERNAL -H ldapi:/// -b cn=config -s base >/dev/null 2>&1 && break; sleep 0.3; done; \
    ldapmodify -Y EXTERNAL -H ldapi:/// -f /seed/acl.ldif; \
    ldapadd -x -H ldapi:/// -D "cn=admin,dc=example,dc=com" -w changeme -f /seed/seed.ldif; \
    PID="$(cat /run/slapd/slapd.pid)"; kill "$PID"; \
    for i in $(seq 1 20); do kill -0 "$PID" 2>/dev/null || break; sleep 0.3; done; \
    chown -R openldap:openldap /var/lib/ldap /etc/ldap/slapd.d

EXPOSE 389
# Foreground slapd on TCP for the apps on the internal network. No host port is
# published (see docker-compose.yml) -- the directory never touches the host.
CMD ["slapd", "-h", "ldap://0.0.0.0:389/", "-u", "openldap", "-g", "openldap", "-d", "0"]
