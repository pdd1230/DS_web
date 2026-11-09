-- Run once as a MySQL administrator. Replace the password before executing.
-- Uses a new database; does not change existing project databases.
CREATE DATABASE IF NOT EXISTS deepsight_web CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'deepsight'@'127.0.0.1' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON deepsight_web.* TO 'deepsight'@'127.0.0.1';
-- If using an existing account, set config.ps1 to that account instead.
-- Flyway creates the application tables on first successful Spring startup.
