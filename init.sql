CREATE TABLE IF NOT EXISTS recordings (
  id SERIAL PRIMARY KEY,
  filename TEXT UNIQUE,
  agent_id TEXT,
  extension TEXT,
  caller_id TEXT,
  called_id TEXT,
  start_time TIMESTAMP,
  duration TEXT,
  direction TEXT,
  local_path TEXT,
  s3_path TEXT,
  uploaded BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);