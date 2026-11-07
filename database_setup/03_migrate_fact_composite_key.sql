-- Run on an existing Steam DWH before building the updated dbt models.
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @lock_result int;
    EXEC @lock_result = sys.sp_getapplock
        @Resource = 'steam_staging_writer', @LockMode = 'Exclusive',
        @LockOwner = 'Transaction', @LockTimeout = 0;
    IF @lock_result < 0 THROW 50001, 'Another load is using staging.', 1;

    IF NOT EXISTS (SELECT 1 FROM dwh.dim_date WHERE date_key = 0)
        INSERT dwh.dim_date (date_key, full_date, month, quarter, year, season, is_holiday)
        VALUES (0, '00010101', 1, 1, 1, N'Unknown', 0);

    IF NOT EXISTS (SELECT 1 FROM dwh.dim_publisher WHERE publisher_key = 0)
        INSERT dwh.dim_publisher (publisher_key, publisher_name, developer_name, publisher_tier)
        VALUES (0, N'Unknown Publisher', NULL, N'Unknown');

    IF EXISTS (SELECT 1 FROM dwh.fact_game_snapshot WHERE date_key IS NULL)
    UPDATE f SET date_key = CASE WHEN c.release_date IS NULL THEN 0 ELSE d.date_key END
    FROM dwh.fact_game_snapshot f
    JOIN dwh.dim_game g ON g.game_key = f.game_key
    JOIN dbt_staging.stg_steam_games_cleaned c ON c.game_id = g.appid_nk
    LEFT JOIN dwh.dim_date d ON d.full_date = c.release_date AND d.date_key <> 0
    WHERE f.date_key IS NULL;

    IF EXISTS (SELECT 1 FROM dwh.fact_game_snapshot WHERE publisher_key IS NULL)
    UPDATE f SET publisher_key = CASE WHEN p.name IS NULL THEN 0 ELSE d.publisher_key END
    FROM dwh.fact_game_snapshot f
    JOIN dwh.dim_game g ON g.game_key = f.game_key
    JOIN dbt_staging.stg_steam_games_cleaned c ON c.game_id = g.appid_nk
    CROSS APPLY (VALUES (NULLIF(LTRIM(RTRIM(LEFT(c.publishers,
        CHARINDEX(N',', c.publishers + N',') - 1))), N''))) p(name)
    LEFT JOIN dwh.dim_publisher d ON d.publisher_name = p.name AND d.publisher_key <> 0
    WHERE f.publisher_key IS NULL;

    IF EXISTS (SELECT 1 FROM dwh.fact_game_snapshot WHERE date_key IS NULL OR publisher_key IS NULL)
        THROW 50002, 'Some facts could not be matched to date or publisher.', 1;

    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints
                   WHERE parent_object_id = OBJECT_ID('dwh.fact_game_snapshot')
                     AND name = 'uq_fact_game_snapshot_game')
    BEGIN
        DROP INDEX IF EXISTS ix_fact_date_key ON dwh.fact_game_snapshot;
        DROP INDEX IF EXISTS ix_fact_publisher_key ON dwh.fact_game_snapshot;
        ALTER TABLE dwh.fact_game_snapshot DROP CONSTRAINT fk_fact_date, fk_fact_publisher;
        ALTER TABLE dwh.fact_game_snapshot DROP CONSTRAINT pk_fact_game_snapshot;
        ALTER TABLE dwh.fact_game_snapshot ALTER COLUMN date_key INT NOT NULL;
        ALTER TABLE dwh.fact_game_snapshot ALTER COLUMN publisher_key INT NOT NULL;
        ALTER TABLE dwh.fact_game_snapshot ADD CONSTRAINT pk_fact_game_snapshot
            PRIMARY KEY (game_key, date_key, platform_key, publisher_key);
        ALTER TABLE dwh.fact_game_snapshot ADD CONSTRAINT uq_fact_game_snapshot_game UNIQUE (game_key);
        ALTER TABLE dwh.fact_game_snapshot ADD CONSTRAINT fk_fact_date
            FOREIGN KEY (date_key) REFERENCES dwh.dim_date(date_key);
        ALTER TABLE dwh.fact_game_snapshot ADD CONSTRAINT fk_fact_publisher
            FOREIGN KEY (publisher_key) REFERENCES dwh.dim_publisher(publisher_key);
        CREATE INDEX ix_fact_date_key ON dwh.fact_game_snapshot (date_key);
        CREATE INDEX ix_fact_publisher_key ON dwh.fact_game_snapshot (publisher_key);
    END;
    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;
