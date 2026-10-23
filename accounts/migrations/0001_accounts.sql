PRAGMA foreign_keys = ON;
CREATE TABLE users (id TEXT PRIMARY KEY, identity TEXT NOT NULL UNIQUE, created INTEGER NOT NULL);
CREATE TABLE otp (
  id TEXT PRIMARY KEY, identity TEXT NOT NULL, digest TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0, expires INTEGER NOT NULL,
  created INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX otp_identity ON otp(identity, created);
CREATE TABLE limits (bucket TEXT PRIMARY KEY, hits INTEGER NOT NULL, expires INTEGER NOT NULL);
CREATE TABLE sessions (digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires INTEGER NOT NULL);
CREATE TABLE licenses (
  id TEXT PRIMARY KEY, identity TEXT NOT NULL, key_digest TEXT UNIQUE,
  owner_id TEXT REFERENCES users(id), days INTEGER NOT NULL CHECK(days BETWEEN 1 AND 3650),
  device_limit INTEGER NOT NULL CHECK(device_limit BETWEEN 1 AND 10),
  created INTEGER NOT NULL, expires INTEGER,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX licenses_identity ON licenses(identity);
CREATE TABLE devices (
  id TEXT NOT NULL, license_id TEXT NOT NULL REFERENCES licenses(id),
  name TEXT NOT NULL, created INTEGER NOT NULL, last_seen INTEGER NOT NULL,
  PRIMARY KEY(license_id, id)
);
-- Enforce device capacity in the database, including simultaneous activations.
CREATE TRIGGER device_capacity BEFORE INSERT ON devices
WHEN NOT EXISTS (SELECT 1 FROM devices WHERE license_id=NEW.license_id AND id=NEW.id)
AND (SELECT count(*) FROM devices WHERE license_id=NEW.license_id) >=
    (SELECT device_limit FROM licenses WHERE id=NEW.license_id)
BEGIN SELECT RAISE(ABORT, 'device_limit'); END;
CREATE TABLE audit (id INTEGER PRIMARY KEY, action TEXT NOT NULL, license_id TEXT NOT NULL, created INTEGER NOT NULL);
