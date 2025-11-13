-- Те же структуры таблиц, что и в auto-init, на случай ручного применения.

CREATE TABLE IF NOT EXISTS managers (
    tg_id BIGINT PRIMARY KEY,
    name TEXT,
    role TEXT CHECK (role IN ('manager','admin','owner')) NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name TEXT,
    contact TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    login TEXT NOT NULL,
    password TEXT NOT NULL,
    proxy TEXT,
    supplier_id INT REFERENCES suppliers(id),
    buy_price NUMERIC(10,2) NOT NULL,
    status TEXT CHECK (status IN ('free','issued','blocked_at_receipt','error_on_login','dead','disabled')) DEFAULT 'free',
    manager_tg_id BIGINT REFERENCES managers(tg_id),
    issue_datetime TIMESTAMP,
    receipt_state TEXT,
    lifetime_minutes INT,
    end_datetime TIMESTAMP
);

CREATE TABLE IF NOT EXISTS history (
    id SERIAL PRIMARY KEY,
    datetime TIMESTAMP DEFAULT NOW(),
    resource_id INT REFERENCES resources(id),
    manager_tg_id BIGINT REFERENCES managers(tg_id),
    type TEXT,
    supplier_id INT,
    price NUMERIC(10,2),
    action TEXT,
    receipt_state TEXT,
    lifetime_minutes INT
);
