// Seeded into a fresh MongoDB on first init: the official image runs any .js in
// /docker-entrypoint-initdb.d/ before it starts accepting network connections.
// Two fake users. Plaintext passwords are a lab simplification -- hashing is
// orthogonal to the NoSQL injection fix (see DIFF.md, note 3).
db = db.getSiblingDB("labdb");
db.users.insertMany([
  { username: "admin", password: "s3cr3t-admin-pw" },
  { username: "alice", password: "alice-pw" }
]);
