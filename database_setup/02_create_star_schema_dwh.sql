-- =========================================================================
-- Đồ án: Data Warehouse - Tập dữ liệu Steam Games
-- Mô tả: DDL khởi tạo Star Schema (dwh) — chạy MỘT LẦN trước khi ETL
-- Nguyên tắc: Idempotent (chạy lại an toàn), KHÔNG DROP bảng đã có dữ liệu
--             Surrogate key do dbt quản lý (ROW_NUMBER), không dùng IDENTITY
-- =========================================================================

USE steam_games_DWH;
GO

-- =========================================================================
-- 1. TẠO SCHEMA DWH (Tách biệt với Staging dbo)
-- =========================================================================
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'dwh')
BEGIN
    EXEC('CREATE SCHEMA dwh');
    PRINT '=> Thanh cong: Da tao schema dwh.';
END
ELSE
    PRINT '=> Bo qua: Schema dwh da ton tai.';
GO

-- =========================================================================
-- 2. DIMENSION TABLES
-- =========================================================================

-- Dim 1: Dim_Date — Chiều thời gian (calendar 2010–2024)
IF OBJECT_ID('dwh.dim_date', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.dim_date (
        date_key    INT           NOT NULL,   -- Surrogate key: YYYYMMDD, do dbt cung cấp
        full_date   DATE          NOT NULL,   -- Business key
        month       TINYINT       NOT NULL,   -- 1–12
        quarter     TINYINT       NOT NULL,   -- 1–4
        year        SMALLINT      NOT NULL,   -- 2010–2024
        season      NVARCHAR(20)  NOT NULL,   -- Xuan / Ha / Thu / Dong
        is_holiday  BIT           NOT NULL CONSTRAINT df_dim_date_holiday DEFAULT 0,

        CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
    );
    PRINT '=> Thanh cong: Da tao bang dwh.dim_date.';
END
ELSE
    PRINT '=> Bo qua: Bang dwh.dim_date da ton tai.';
GO

-- Dim 2: Dim_Game — Chiều sản phẩm (game)
IF OBJECT_ID('dwh.dim_game', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.dim_game (
        game_key            INT            NOT NULL,   -- Surrogate key, do dbt cung cấp
        appid_nk            BIGINT         NOT NULL,   -- Business key (AppID Steam)
        game_name           NVARCHAR(500)  NOT NULL,
        required_age        INT            NULL,
        genres              NVARCHAR(MAX)  NULL,       -- Chuỗi CSV nguyên bản
        categories          NVARCHAR(MAX)  NULL,       -- Chuỗi CSV nguyên bản
        supported_languages NVARCHAR(MAX)  NULL,

        CONSTRAINT pk_dim_game       PRIMARY KEY (game_key),
        CONSTRAINT uq_dim_game_appid UNIQUE      (appid_nk)
    );
    PRINT '=> Thanh cong: Da tao bang dwh.dim_game.';
END
ELSE
    PRINT '=> Bo qua: Bang dwh.dim_game da ton tai.';
GO

-- Dim 3: Dim_Platform — Chiều nền tảng (8 tổ hợp Win/Mac/Linux)
IF OBJECT_ID('dwh.dim_platform', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.dim_platform (
        platform_key    INT           NOT NULL,   -- Surrogate key, do dbt cung cấp
        platform_combo  NVARCHAR(50)  NOT NULL,   -- Windows Only / Win & Mac / Cross-platform ...
        is_windows      BIT           NOT NULL CONSTRAINT df_dim_platform_win DEFAULT 0,
        is_mac          BIT           NOT NULL CONSTRAINT df_dim_platform_mac DEFAULT 0,
        is_linux        BIT           NOT NULL CONSTRAINT df_dim_platform_linux DEFAULT 0,

        CONSTRAINT pk_dim_platform PRIMARY KEY (platform_key)
    );
    PRINT '=> Thanh cong: Da tao bang dwh.dim_platform.';
END
ELSE
    PRINT '=> Bo qua: Bang dwh.dim_platform da ton tai.';
GO

-- Dim 4: Dim_Publisher — Chiều nhà phát hành & studio phát triển
IF OBJECT_ID('dwh.dim_publisher', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.dim_publisher (
        publisher_key   INT            NOT NULL,   -- Surrogate key, do dbt cung cấp
        publisher_name  NVARCHAR(500)  NOT NULL,   -- Business key
        developer_name  NVARCHAR(500)  NULL,
        publisher_tier  NVARCHAR(50)   NULL,       -- AAA / Indie

        CONSTRAINT pk_dim_publisher PRIMARY KEY (publisher_key)
    );
    PRINT '=> Thanh cong: Da tao bang dwh.dim_publisher.';
END
ELSE
    PRINT '=> Bo qua: Bang dwh.dim_publisher da ton tai.';
GO

-- =========================================================================
-- 3. FACT TABLE — Periodic Snapshot
-- Grain: 1 dòng = 1 tựa game duy nhất tại thời điểm nạp vào DWH
-- FK phải tạo SAU khi đã có đủ 4 bảng Dimension ở trên
-- =========================================================================
IF OBJECT_ID('dwh.fact_game_snapshot', 'U') IS NULL
BEGIN
    CREATE TABLE dwh.fact_game_snapshot (
        -- Khóa chính (đồng thời là FK → dim_game)
        game_key            INT             NOT NULL,

        -- Khóa ngoại tham chiếu Dimension
        date_key            INT             NULL,     -- NULL nếu ngoài 2010–2024
        platform_key        INT             NOT NULL,
        publisher_key       INT             NULL,     -- NULL nếu publisher trống

        -- Measures
        price               DECIMAL(10, 2)  NULL,    -- Non-additive
        discount            INT             NULL,    -- Non-additive
        peak_ccu            INT             NULL,    -- Semi-additive
        positive_reviews    INT             NULL,    -- Additive
        negative_reviews    INT             NULL,    -- Additive
        metacritic_score    INT             NULL,    -- Non-additive
        user_score          DECIMAL(10, 2)  NULL,    -- Non-additive
        average_playtime    INT             NULL,    -- Non-additive (phút)

        -- Constraints
        CONSTRAINT pk_fact_game_snapshot  PRIMARY KEY (game_key),
        CONSTRAINT fk_fact_game           FOREIGN KEY (game_key)       REFERENCES dwh.dim_game(game_key),
        CONSTRAINT fk_fact_date           FOREIGN KEY (date_key)       REFERENCES dwh.dim_date(date_key),
        CONSTRAINT fk_fact_platform       FOREIGN KEY (platform_key)   REFERENCES dwh.dim_platform(platform_key),
        CONSTRAINT fk_fact_publisher      FOREIGN KEY (publisher_key)  REFERENCES dwh.dim_publisher(publisher_key)
    );
    PRINT '=> Thanh cong: Da tao bang dwh.fact_game_snapshot.';
END
ELSE
    PRINT '=> Bo qua: Bang dwh.fact_game_snapshot da ton tai.';
GO

-- =========================================================================
-- 4. NONCLUSTERED INDEX — Tối ưu JOIN cho Power BI / báo cáo
-- =========================================================================
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_fact_date_key'
               AND object_id = OBJECT_ID('dwh.fact_game_snapshot'))
    CREATE NONCLUSTERED INDEX ix_fact_date_key
        ON dwh.fact_game_snapshot (date_key);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_fact_platform_key'
               AND object_id = OBJECT_ID('dwh.fact_game_snapshot'))
    CREATE NONCLUSTERED INDEX ix_fact_platform_key
        ON dwh.fact_game_snapshot (platform_key);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_fact_publisher_key'
               AND object_id = OBJECT_ID('dwh.fact_game_snapshot'))
    CREATE NONCLUSTERED INDEX ix_fact_publisher_key
        ON dwh.fact_game_snapshot (publisher_key);
GO

PRINT '=========================================================================';
PRINT '=> HOAN THANH: Toan bo cau truc Star Schema (dwh) da duoc khoi tao!';
PRINT '   Buoc tiep theo: Chay dbt run de nap du lieu tu Staging vao DWH.';
PRINT '=========================================================================';
