-- Plans the seller offers, customer orders awaiting approval, and who did what in the admin console.
CREATE TABLE plans (
  id TEXT PRIMARY KEY, name TEXT NOT NULL,
  days INTEGER NOT NULL CHECK(days BETWEEN 1 AND 3650),
  device_limit INTEGER NOT NULL CHECK(device_limit BETWEEN 1 AND 10),
  price INTEGER NOT NULL CHECK(price BETWEEN 0 AND 1000000000),
  active INTEGER NOT NULL DEFAULT 1, created INTEGER NOT NULL
);
-- An order keeps the plan as sold (name, term, devices, price) even if the plan changes later.
CREATE TABLE orders (
  id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL REFERENCES users(id), identity TEXT NOT NULL,
  plan_id TEXT NOT NULL, plan_name TEXT NOT NULL,
  days INTEGER NOT NULL, device_limit INTEGER NOT NULL, price INTEGER NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'cancelled')),
  created INTEGER NOT NULL, decided INTEGER, decided_by TEXT, reason TEXT,
  license_id TEXT REFERENCES licenses(id)
);
CREATE INDEX orders_status ON orders(status, created);
CREATE INDEX orders_user ON orders(user_id, created);
CREATE INDEX orders_decided ON orders(decided);
CREATE INDEX users_created ON users(created);
ALTER TABLE audit ADD COLUMN actor TEXT;
ALTER TABLE audit ADD COLUMN detail TEXT;
