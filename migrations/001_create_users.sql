CREATE TABLE IF NOT EXISTS users (
    id            VARCHAR(36)  PRIMARY KEY,
    national_code VARCHAR(10)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    birth_date    DATE         NOT NULL,
    status        VARCHAR(10)  NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'BLOCKED')),
    phone_number  VARCHAR(11)  NOT NULL,
    address       VARCHAR(255) NOT NULL,
    postal_code   VARCHAR(10)  NOT NULL
)
