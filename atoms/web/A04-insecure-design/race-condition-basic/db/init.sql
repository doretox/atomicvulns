-- Seeded into a fresh Postgres on first init: the official image runs any .sql in
-- /docker-entrypoint-initdb.d/ before it starts accepting TCP connections, so once
-- the TCP server is up (the healthcheck) the seed is already done. One fake account
-- with a fake balance -- lab data only (CLAUDE.md §8).
CREATE TABLE accounts (
    id      INT PRIMARY KEY,
    balance INT NOT NULL
);

INSERT INTO accounts (id, balance) VALUES (1, 100);
