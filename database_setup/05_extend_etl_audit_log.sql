-- =========================================================================
-- Mở rộng dbo.etl_audit_log: mỗi bước của một lượt ETL vẫn là 1 dòng,
-- các dòng cùng lượt chạy có chung run_id. Chỉ thêm cột cho phép NULL,
-- giữ nguyên 6 cột và dữ liệu cũ. Chạy lại nhiều lần an toàn.
-- =========================================================================
USE steam_games_DWH;
GO

IF COL_LENGTH('dbo.etl_audit_log', 'run_id') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD run_id char(32) NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'step') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD step varchar(20) NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'trigger_name') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD trigger_name nvarchar(100) NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'run_mode') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD run_mode varchar(20) NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'started_at') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD started_at datetime2 NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'finished_at') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD finished_at datetime2 NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'duration_sec') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD duration_sec int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'inserted') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD inserted int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'updated') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD updated int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'unchanged') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD unchanged int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'rejected') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD rejected int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'dbt_tests') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD dbt_tests int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'checks_failed') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD checks_failed int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'metrics_json') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD metrics_json nvarchar(max) NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'end_time') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD end_time datetime2 NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'duration_seconds') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD duration_seconds int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'dbt_tests_passed') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD dbt_tests_passed int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'dbt_tests_failed') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD dbt_tests_failed int NULL;
IF COL_LENGTH('dbo.etl_audit_log', 'ai_explanation') IS NULL
    ALTER TABLE dbo.etl_audit_log ADD ai_explanation nvarchar(max) NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes
               WHERE name = 'ix_etl_audit_log_run' AND object_id = OBJECT_ID('dbo.etl_audit_log'))
    CREATE NONCLUSTERED INDEX ix_etl_audit_log_run ON dbo.etl_audit_log (run_id, log_id);
GO
