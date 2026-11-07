IF OBJECT_ID('dbo.stg_steam_games_rejected', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.stg_steam_games_rejected (
        run_id char(32) NOT NULL,
        source_file nvarchar(2048) NOT NULL,
        source_record_no bigint NOT NULL,
        line_start bigint NOT NULL,
        line_end bigint NOT NULL,
        chunk_id int NULL,
        rejected_stage varchar(16) NOT NULL,
        reason_code varchar(32) NOT NULL,
        reason_detail nvarchar(4000) NOT NULL,
        raw_appid nvarchar(max) NULL,
        raw_record nvarchar(max) NOT NULL,
        rejected_at datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT pk_steam_games_rejected
            PRIMARY KEY (run_id, source_record_no, rejected_stage, reason_code)
    );
END;
