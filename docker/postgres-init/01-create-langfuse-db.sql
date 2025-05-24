-- Create langfuse database if it doesn't exist
SELECT 'CREATE DATABASE langfuse'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE langfuse TO postgres;
GRANT ALL PRIVILEGES ON DATABASE policiytracker TO postgres;