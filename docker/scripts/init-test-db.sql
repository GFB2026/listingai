-- Auto-create the test database if it doesn't exist.
-- Mounted into /docker-entrypoint-initdb.d/ by docker-compose.test.yml.
SELECT 'CREATE DATABASE listingai_test OWNER listingai'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'listingai_test')\gexec
