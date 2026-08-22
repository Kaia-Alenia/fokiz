-- schema.sql — Fokiz SQLite schema with immutability triggers.
-- Copyright (C) Alenia Studios — GNU GPL v3

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    nickname TEXT NOT NULL,
    timezone TEXT NOT NULL,
    max_active_slots INTEGER NOT NULL DEFAULT 3,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    total_days INTEGER NOT NULL CHECK (total_days >= 1),
    total_phases INTEGER NOT NULL CHECK (total_phases BETWEEN 1 AND 8),
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK(status IN ('ACTIVE', 'COMPLETED', 'SURRENDERED')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deadline DATETIME NOT NULL,
    completed_at DATETIME,
    surrender_reason TEXT,
    integrity_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    phase_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    instructions TEXT NOT NULL,
    target_deadline DATETIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(status IN ('PENDING', 'COMPLETED')),
    completed_at DATETIME,
    completion_log TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT,
    UNIQUE(task_id, phase_number)
);

CREATE TABLE IF NOT EXISTS notification_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    urgency_level TEXT NOT NULL
        CHECK(urgency_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    message_sent TEXT NOT NULL,
    dispatched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS integrity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    task_id INTEGER,
    detail TEXT,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- Immutability triggers — tasks
-- ---------------------------------------------------------------------------

CREATE TRIGGER IF NOT EXISTS abort_task_contract_update
BEFORE UPDATE OF title, objective, deadline, created_at, total_days,
total_phases ON tasks
BEGIN
    SELECT RAISE(ABORT,
        'Fokiz: immutable task contract field');
END;

CREATE TRIGGER IF NOT EXISTS abort_task_delete
BEFORE DELETE ON tasks
BEGIN
    SELECT RAISE(ABORT,
        'Fokiz: immutable task deletion');
END;

-- ---------------------------------------------------------------------------
-- Immutability triggers — task_phases
-- ---------------------------------------------------------------------------

CREATE TRIGGER IF NOT EXISTS abort_phase_contract_update
BEFORE UPDATE OF task_id, phase_number, title, instructions, target_deadline
ON task_phases
BEGIN
    SELECT RAISE(ABORT,
        'Fokiz: immutable phase contract field');
END;

CREATE TRIGGER IF NOT EXISTS abort_phase_delete
BEFORE DELETE ON task_phases
BEGIN
    SELECT RAISE(ABORT,
        'Fokiz: immutable phase deletion');
END;

-- ---------------------------------------------------------------------------
-- State transition guard — tasks
-- Valid: ACTIVE -> COMPLETED | SURRENDERED
-- Invalid: any reverse or COMPLETED <-> SURRENDERED
-- ---------------------------------------------------------------------------

CREATE TRIGGER IF NOT EXISTS guard_task_status_transition
BEFORE UPDATE OF status ON tasks
BEGIN
    SELECT RAISE(ABORT, 'Fokiz: invalid task state transition')
    WHERE NOT (
        -- ACTIVE -> COMPLETED
        (OLD.status = 'ACTIVE' AND NEW.status = 'COMPLETED')
        OR
        -- ACTIVE -> SURRENDERED
        (OLD.status = 'ACTIVE' AND NEW.status = 'SURRENDERED')
        OR
        -- Same value (no change — allowed, no-op)
        (OLD.status = NEW.status)
    );
END;

-- ---------------------------------------------------------------------------
-- State transition guard — task_phases
-- Valid: PENDING -> COMPLETED only
-- ---------------------------------------------------------------------------

CREATE TRIGGER IF NOT EXISTS guard_phase_status_transition
BEFORE UPDATE OF status ON task_phases
BEGIN
    SELECT RAISE(ABORT, 'Fokiz: invalid phase state transition')
    WHERE NOT (
        (OLD.status = 'PENDING' AND NEW.status = 'COMPLETED')
        OR
        (OLD.status = NEW.status)
    );
END;
