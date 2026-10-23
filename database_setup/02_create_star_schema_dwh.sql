-- =========================================================================
-- Đồ án: Data Warehouse - Tập dữ liệu Steam Games
-- Mô tả: DDL khởi tạo cấu trúc Star Schema (Fact & 4 Dimension) vật lý trên SQL Server
-- Giai đoạn: 3.3 Data Warehouse (Star Schema)
-- =========================================================================

USE steam_games_DWH;
GO

-- 1. TẠO SCHEMA DWH (Phân tách rõ ràng với Staging dbo)
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'dwh')
BEGIN
    EXEC('CREATE SCHEMA dwh');
    PRINT '=> Thanh cong: Da tao schema dwh.';
END
ELSE
BEGIN
    PRINT '=> Bo qua: Schema dwh da ton tai.';
END
GO

-- =========================================================================
-- 2. XÓA BẢNG CŨ THEO THỨ TỰ AN TOÀN (Drop Fact trước, Dim sau để tránh lỗi FK)
-- =========================================================================
IF OBJECT_ID('dwh.Fact_Game_Snapshot', 'U') IS NOT NULL 
BEGIN
    DROP TABLE dwh.Fact_Game_Snapshot;
    PRINT '=> Da xoa bang cu dwh.Fact_Game_Snapshot.';
END

IF OBJECT_ID('dwh.Dim_Date', 'U') IS NOT NULL 
BEGIN
    DROP TABLE dwh.Dim_Date;
    PRINT '=> Da xoa bang cu dwh.Dim_Date.';
END

IF OBJECT_ID('dwh.Dim_Game', 'U') IS NOT NULL 
BEGIN
    DROP TABLE dwh.Dim_Game;
    PRINT '=> Da xoa bang cu dwh.Dim_Game.';
END

IF OBJECT_ID('dwh.Dim_Platform', 'U') IS NOT NULL 
BEGIN
    DROP TABLE dwh.Dim_Platform;
    PRINT '=> Da xoa bang cu dwh.Dim_Platform.';
END

IF OBJECT_ID('dwh.Dim_Publisher', 'U') IS NOT NULL 
BEGIN
    DROP TABLE dwh.Dim_Publisher;
    PRINT '=> Da xoa bang cu dwh.Dim_Publisher.';
END
GO

-- =========================================================================
-- 3. TẠO CÁC BẢNG DIMENSION
-- =========================================================================

-- Dim 1: Dim_Date (Chiều Thời gian - Phục vụ phân tích Seasonality & Trend)
CREATE TABLE dwh.Dim_Date (
    date_key            INT PRIMARY KEY,              -- Surrogate Key: YYYYMMDD (vd: 20201210)
    full_date           DATE NOT NULL,                -- Business Key
    month               TINYINT NOT NULL,             -- 1 -> 12
    quarter             TINYINT NOT NULL,             -- 1 -> 4
    year                SMALLINT NOT NULL,            -- vd: 2020
    season              NVARCHAR(20) NOT NULL,        -- Xuân, Hạ, Thu, Đông
    is_holiday          BIT NOT NULL DEFAULT 0        -- 1: Ngày lễ, 0: Ngày thường
);
PRINT '=> Thanh cong: Da tao bang dwh.Dim_Date.';

-- Dim 2: Dim_Game (Chiều Sản phẩm - Denormalized theo báo cáo)
CREATE TABLE dwh.Dim_Game (
    game_key            INT IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key tự tăng
    appid_nk            BIGINT NOT NULL UNIQUE,        -- Business Key (AppID từ Steam)
    game_name           NVARCHAR(500) NOT NULL,
    required_age        INT NULL,
    genres              NVARCHAR(MAX) NULL,            -- Lưu chuỗi nguyên bản (phi chuẩn hóa)
    categories          NVARCHAR(MAX) NULL,            -- Lưu chuỗi nguyên bản (phi chuẩn hóa)
    supported_languages NVARCHAR(MAX) NULL
);
PRINT '=> Thanh cong: Da tao bang dwh.Dim_Game.';

-- Dim 3: Dim_Platform (Chiều Nền tảng)
CREATE TABLE dwh.Dim_Platform (
    platform_key        INT IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key tự tăng
    platform_combo      NVARCHAR(50) NOT NULL,         -- "Windows Only", "Win & Mac", "Cross-platform"
    is_windows          BIT NOT NULL DEFAULT 0,
    is_mac              BIT NOT NULL DEFAULT 0,
    is_linux            BIT NOT NULL DEFAULT 0
);
PRINT '=> Thanh cong: Da tao bang dwh.Dim_Platform.';

-- Dim 4: Dim_Publisher (Chiều Nhà phát hành & Phát triển)
CREATE TABLE dwh.Dim_Publisher (
    publisher_key       INT IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key tự tăng
    publisher_name      NVARCHAR(500) NOT NULL,        -- Business Key
    developer_name      NVARCHAR(500) NULL,
    publisher_tier      NVARCHAR(50) NULL              -- Phân khúc: AAA, Indie (xử lý logic dbt)
);
PRINT '=> Thanh cong: Da tao bang dwh.Dim_Publisher.';
GO

-- =========================================================================
-- 4. TẠO BẢNG FACT 
-- Loại bảng: Periodic Snapshot Fact Table
-- Grain: Một dòng tương ứng 1 tựa game duy nhất tại thời điểm lấy mẫu (Snapshot)
-- =========================================================================
CREATE TABLE dwh.Fact_Game_Snapshot (
    snapshot_id         BIGINT IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key của bản ghi snapshot
    
    -- Khóa ngoại tham chiếu 4 Dimension
    date_key            INT NULL,
    game_key            INT NOT NULL,
    platform_key        INT NOT NULL,
    publisher_key       INT NULL,
    
    -- Measures (Các chỉ số đo lường phục vụ BI)
    price               DECIMAL(10,2) NULL,            -- Non-additive: Giá bán lẻ của game
    discount            INT NULL,                      -- Non-additive: Mức giảm giá (%)
    peak_ccu            INT NULL,                      -- Semi-additive: Lượng người chơi cùng lúc cao nhất
    positive_reviews    INT NULL,                      -- Additive: Số lượt đánh giá tích cực
    negative_reviews    INT NULL,                      -- Additive: Số lượt đánh giá tiêu cực
    metacritic_score    INT NULL,                      -- Non-additive: Điểm đánh giá từ chuyên gia
    user_score          DECIMAL(4,2) NULL,             -- Non-additive: Điểm số từ người dùng
    average_playtime    INT NULL,                      -- Non-additive: Thời gian chơi trung bình (phút)
    
    -- Ràng buộc toàn vẹn khóa ngoại (Foreign Keys)
    CONSTRAINT fk_fact_date FOREIGN KEY (date_key) REFERENCES dwh.Dim_Date(date_key),
    CONSTRAINT fk_fact_game FOREIGN KEY (game_key) REFERENCES dwh.Dim_Game(game_key),
    CONSTRAINT fk_fact_platform FOREIGN KEY (platform_key) REFERENCES dwh.Dim_Platform(platform_key),
    CONSTRAINT fk_fact_publisher FOREIGN KEY (publisher_key) REFERENCES dwh.Dim_Publisher(publisher_key)
);
PRINT '=> Thanh cong: Da tao bang dwh.Fact_Game_Snapshot.';
GO

-- =========================================================================
-- 5. TẠO NONCLUSTERED INDEX TỐI ƯU TRUY VẤN (Tối ưu cho Power BI và JOIN)
-- =========================================================================
CREATE NONCLUSTERED INDEX ix_fact_date_key ON dwh.Fact_Game_Snapshot(date_key);
CREATE NONCLUSTERED INDEX ix_fact_game_key ON dwh.Fact_Game_Snapshot(game_key);
CREATE NONCLUSTERED INDEX ix_fact_platform_key ON dwh.Fact_Game_Snapshot(platform_key);
CREATE NONCLUSTERED INDEX ix_fact_publisher_key ON dwh.Fact_Game_Snapshot(publisher_key);
GO

PRINT '=========================================================================';
PRINT '=> HOAN THANH: Toan bo cau truc Star Schema (dwh) da duoc tao thanh cong!';
PRINT '=========================================================================';
