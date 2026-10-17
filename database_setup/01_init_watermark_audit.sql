-- =========================================================================
-- Đồ án: Data Warehouse - Tập dữ liệu Steam Games
-- Mô tả: Khởi tạo Database, bảng Watermark và Audit Log chuẩn DBA
-- =========================================================================

-- 1. CHUYỂN VỀ MASTER ĐỂ TẠO DATABASE AN TOÀN
USE master;
GO

-- Kiểm tra ràng buộc: Nếu chưa có DB thì mới tạo
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'steam_games_DWH')
BEGIN
    CREATE DATABASE steam_games_DWH;
    PRINT '=> Thanh cong: Da tao Database steam_games_DWH.';
END
ELSE
BEGIN
    PRINT '=> Bo qua: Database steam_games_DWH da ton tai.';
END
GO

-- 2. CHUYỂN NGỮ CẢNH VÀO DATABASE CỦA ĐỒ ÁN
USE steam_games_DWH;
GO

-- 3. KIỂM TRA VÀ TẠO BẢNG WATERMARK (ĐIỀU KHIỂN CDC - LSET)
IF OBJECT_ID('etl_watermark', 'U') IS NULL 
BEGIN
    CREATE TABLE etl_watermark (
        table_name VARCHAR(100) PRIMARY KEY,
        lset DATETIME
    );
    
    -- Khởi tạo mốc sơ khai ngay sau khi tạo bảng
    INSERT INTO etl_watermark (table_name, lset) 
    VALUES ('stg_steam_games', '2010-01-01');
    
    PRINT '=> Thanh cong: Da tao bang etl_watermark.';
END
ELSE
BEGIN
    PRINT '=> Bo qua: Bang etl_watermark da ton tai.';
END
GO

-- 4. KIỂM TRA VÀ TẠO BẢNG AUDIT LOG (NHẬT KÝ HỆ THỐNG)
IF OBJECT_ID('etl_audit_log', 'U') IS NULL 
BEGIN
    CREATE TABLE etl_audit_log (
        log_id INT IDENTITY(1,1) PRIMARY KEY,
        pipeline_name VARCHAR(100),
        run_date DATETIME,
        status VARCHAR(50),
        records_processed INT,
        error_message NVARCHAR(MAX)
    );
    
    PRINT '=> Thanh cong: Da tao bang etl_audit_log.';
END
ELSE
BEGIN
    PRINT '=> Bo qua: Bang etl_audit_log da ton tai.';
END
GO

-- 5. Tạo Staging table
USE steam_games_DWH;

IF OBJECT_ID('dbo.stg_steam_games', 'U') IS NOT NULL
    DROP TABLE dbo.stg_steam_games;

CREATE TABLE dbo.stg_steam_games (
    appid                       BIGINT          NOT NULL PRIMARY KEY,
    name                        NVARCHAR(1000)  NULL,
    release_date                DATE            NULL,
    estimated_owners            NVARCHAR(50)    NULL,
    peak_ccu                    INT             NULL,
    required_age                INT             NULL,
    price                       DECIMAL(10,2)   NULL,
    discount                    INT             NULL,
    dlc_count                   INT             NULL,
    about_the_game              NVARCHAR(MAX)   NULL,
    supported_languages         NVARCHAR(MAX)   NULL,
    full_audio_languages        NVARCHAR(MAX)   NULL,
    reviews                     NVARCHAR(MAX)   NULL,
    header_image                NVARCHAR(1000)  NULL,
    website                     NVARCHAR(1000)  NULL,
    support_url                 NVARCHAR(1000)  NULL,
    support_email               NVARCHAR(500)   NULL,
    windows                     BIT             NULL,
    mac                         BIT             NULL,
    linux                       BIT             NULL,
    metacritic_score            INT             NULL,
    metacritic_url              NVARCHAR(1000)  NULL,
    user_score                  INT             NULL,
    positive                    INT             NULL,
    negative                    INT             NULL,
    score_rank                  NVARCHAR(50)    NULL,
    achievements                INT             NULL,
    recommendations             INT             NULL,
    notes                       NVARCHAR(MAX)   NULL,
    average_playtime_forever    INT             NULL,
    average_playtime_two_weeks  INT             NULL,
    median_playtime_forever     INT             NULL,
    median_playtime_two_weeks   INT             NULL,
    developers                  NVARCHAR(MAX)   NULL,
    publishers                  NVARCHAR(MAX)   NULL,
    categories                  NVARCHAR(MAX)   NULL,
    genres                      NVARCHAR(MAX)   NULL,
    tags                        NVARCHAR(MAX)   NULL,
    screenshots                 NVARCHAR(MAX)   NULL,
    movies                      NVARCHAR(MAX)   NULL,
    _loaded_at                  DATETIME        NULL,
    _run_mode                   VARCHAR(20)     NULL
);
