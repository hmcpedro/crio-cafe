CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO users (
    name,
    email,
    phone,
    password_hash,
    is_admin,
    is_active
)
VALUES (
    'Administrador',
    'admin@admin.com',
    '11999999999',
    crypt('admin', gen_salt('bf')),
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING; 