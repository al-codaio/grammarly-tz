-- Create TensorZero database and tables
CREATE DATABASE IF NOT EXISTS tensorzero;

USE tensorzero;

-- Migration tracking table (must exist first)
CREATE TABLE IF NOT EXISTS TensorZeroMigration (
    migration_id String,
    migration_name String,
    gateway_version String,
    gateway_git_sha String,
    config_hash String,
    execution_time_ms UInt64,
    applied_at DateTime DEFAULT now()
) ENGINE = MergeTree() ORDER BY applied_at;

-- Dynamic In-Context Learning Example table (needed for DICL)
CREATE TABLE IF NOT EXISTS DynamicInContextLearningExample (
    id UUID,
    function_name LowCardinality(String),
    variant_name LowCardinality(String),
    namespace String,
    input String,
    output String,
    embedding Array(Float32),
    timestamp DateTime MATERIALIZED UUIDv7ToDateTime(id)
) ENGINE = MergeTree() ORDER BY (function_name, variant_name, namespace);