-- rfmseg 初始表结构（PostgreSQL 16）
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(120) NOT NULL UNIQUE,
    display_name  VARCHAR(80) NOT NULL,
    role          VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS members (
    id          SERIAL PRIMARY KEY,
    member_no   VARCHAR(24) NOT NULL UNIQUE,
    name        VARCHAR(60) NOT NULL,
    phone       VARCHAR(24) NOT NULL,
    store_code  VARCHAR(12) NOT NULL,
    store_name  VARCHAR(60) NOT NULL,
    joined_at   DATE NOT NULL,
    consent     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS order_facts (
    id              SERIAL PRIMARY KEY,
    order_no        VARCHAR(24) NOT NULL UNIQUE,
    member_id       INTEGER NOT NULL REFERENCES members(id),
    store_code      VARCHAR(12) NOT NULL,
    amount          NUMERIC(10,2) NOT NULL,
    ordered_at      TIMESTAMP NOT NULL,
    coupon_issued   BOOLEAN NOT NULL DEFAULT FALSE,
    coupon_redeemed BOOLEAN NOT NULL DEFAULT FALSE,
    coupon_discount NUMERIC(8,2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS segment_runs (
    id            SERIAL PRIMARY KEY,
    run_no        VARCHAR(32) NOT NULL UNIQUE,
    name          VARCHAR(80) NOT NULL,
    status        VARCHAR(16) NOT NULL DEFAULT 'queued',
    k_requested   VARCHAR(8) NOT NULL DEFAULT 'auto',
    as_of         DATE NOT NULL,
    random_state  INTEGER NOT NULL DEFAULT 5741,
    selected_k    INTEGER,
    silhouette    NUMERIC(6,4),
    inertia       NUMERIC(14,4),
    member_count  INTEGER,
    result        JSONB,
    error_message TEXT,
    duration_ms   INTEGER,
    created_by    INTEGER REFERENCES users(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS strategies (
    id            SERIAL PRIMARY KEY,
    strategy_no   VARCHAR(32) NOT NULL UNIQUE,
    name          VARCHAR(90) NOT NULL,
    status        VARCHAR(16) NOT NULL DEFAULT 'draft',
    run_id        INTEGER NOT NULL REFERENCES segment_runs(id),
    total_budget  NUMERIC(10,2) NOT NULL,
    allocations   JSONB,
    totals        JSONB,
    tiers_used    JSONB,
    touch_log     JSONB,
    created_by    INTEGER REFERENCES users(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at  TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id           SERIAL PRIMARY KEY,
    actor_id     INTEGER REFERENCES users(id),
    actor_email  VARCHAR(120),
    action       VARCHAR(60) NOT NULL,
    entity_type  VARCHAR(40) NOT NULL,
    entity_id    INTEGER,
    before_json  JSONB,
    after_json   JSONB,
    ip           VARCHAR(64),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_members_store ON members(store_code);
CREATE INDEX IF NOT EXISTS idx_orders_member ON order_facts(member_id);
CREATE INDEX IF NOT EXISTS idx_orders_time ON order_facts(ordered_at);
CREATE INDEX IF NOT EXISTS idx_runs_status ON segment_runs(status);
CREATE INDEX IF NOT EXISTS idx_strategies_run ON strategies(run_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
