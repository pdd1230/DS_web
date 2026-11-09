-- ★★ github에 프로젝트를 올릴때 여기 있는 정보는 올리지 마세요.  db 정보는 반드시 제거하고 올립니다.  (계정 비번은 반드시 설정하세요)
-- MySQL 관리자 계정으로 한 번 실행하세요. 실행 전에 비밀번호를 변경하세요.
-- 새 데이터베이스를 사용하며, 기존 프로젝트의 데이터베이스는 변경하지 않습니다.

CREATE DATABASE IF NOT EXISTS deepsight_web CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'deepsight'@'127.0.0.1' IDENTIFIED BY 'change me';

GRANT ALL PRIVILEGES ON deepsight_web.* TO 'deepsight'@'127.0.0.1';

-- 기존 계정을 사용하려면 config.ps1에 해당 계정 정보를 설정하세요.
-- Spring Boot가 처음 정상적으로 시작될 때 Flyway가 애플리케이션 테이블을 생성합니다.
