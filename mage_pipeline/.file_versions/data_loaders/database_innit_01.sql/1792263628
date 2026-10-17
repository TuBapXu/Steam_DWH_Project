-- Bảng Watermark (điều khiển CDC - LSET)
IF OBJECT_ID('dbo.etl_watermark', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.etl_watermark (
        table_name VARCHAR(100) PRIMARY KEY,
        lset DATETIME
    );

    INSERT INTO dbo.etl_watermark (table_name, lset)
    VALUES ('stg_steam_games', '1900-01-01');
END;

-- Bảng Audit Log (nhật ký hệ thống)
IF OBJECT_ID('dbo.etl_audit_log', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.etl_audit_log (
        log_id INT IDENTITY(1,1) PRIMARY KEY,
        pipeline_name VARCHAR(100),
        run_date DATETIME,
        status VARCHAR(50),
        records_processed INT,
        error_message NVARCHAR(MAX)
    );
END;