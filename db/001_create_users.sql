CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    national_id   CHAR(10) NOT NULL UNIQUE
                  CHECK (national_id ~ '^[0-9]{10}$'),
    full_name     VARCHAR(150) NOT NULL,
    birth_date    DATE NOT NULL,
    status        VARCHAR(10) NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'blocked', 'disabled')),
    phone_number  VARCHAR(11) NOT NULL UNIQUE
                  CHECK (phone_number ~ '^09[0-9]{9}$'),
    address       TEXT NOT NULL,
    postal_code   CHAR(10) NOT NULL
                  CHECK (postal_code ~ '^[0-9]{10}$'),
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);