-- infra/postgres/init.sql
-- Creates schemas for all services

CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS course;
CREATE SCHEMA IF NOT EXISTS enrollment;
CREATE SCHEMA IF NOT EXISTS progress;
CREATE SCHEMA IF NOT EXISTS publishing;
CREATE SCHEMA IF NOT EXISTS notification;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Shared schema for outbox
CREATE SCHEMA IF NOT EXISTS shared;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
