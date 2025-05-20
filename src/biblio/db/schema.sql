CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id BIGINT NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    codice_fiscale VARCHAR(16) UNIQUE NOT NULL,
    priority INTEGER DEFAULT 2,
    name TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (codice_fiscale, username, first_name, last_name, email)
);

CREATE TABLE IF NOT EXISTS reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    selected_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,     
    display_date TEXT,
    selected_duration INTEGER NOT NULL,
    booking_code VARCHAR,
    retries INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    instant BOOLEAN DEFAULT FALSE,
    status_change BOOLEAN DEFAULT FALSE,
    notified BOOLEAN DEFAULT FALSE
);