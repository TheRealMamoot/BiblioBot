CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id BIGINT NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    codice_fiscale VARCHAR(16) NOT NULL,
    priority INTEGER DEFAULT 2,
    name TEXT,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (codice_fiscale, email, name) 
);

CREATE TABLE IF NOT EXISTS reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    inserted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    selected_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,     
    display_date TEXT,
    selected_duration INTEGER NOT NULL,
    booking_code VARCHAR,
    retries INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    instant BOOLEAN DEFAULT FALSE,
    status_change BOOLEAN DEFAULT FALSE,
    notified BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    slot TEXT NOT NULL,
    available INTEGER NOT NULL
);