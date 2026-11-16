CREATE TABLE IF NOT EXISTS accounts (
    id           VARCHAR(36) PRIMARY KEY,
    user_id      VARCHAR(36) NOT NULL REFERENCES users (id),
    sheba_number VARCHAR(26) NOT NULL UNIQUE,
    status       VARCHAR(10) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'BLOCKED'))
)