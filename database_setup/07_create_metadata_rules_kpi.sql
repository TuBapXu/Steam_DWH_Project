-- =========================================================================
-- Metadata-driven Validation Rules & KPI Definitions (khong gan cung trong code)
-- Cho phep them/go/bat/tat rule va doi dinh nghia cach tinh KPI qua SQL / UI
-- ma khong phai sua code Python hay SQL dbt model.
-- Script idempotent: chay lai an toan, giu nguyen cau hinh nguoi dung da sua.
-- =========================================================================
USE steam_games_DWH;
GO

IF OBJECT_ID('dbo.etl_validation_rules', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.etl_validation_rules (
        rule_id        INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        rule_code      VARCHAR(64)       NOT NULL UNIQUE,
        rule_name      NVARCHAR(200)     NOT NULL,
        target_column  VARCHAR(64)       NOT NULL,
        rule_type      VARCHAR(32)       NOT NULL, -- REQUIRED | NUMERIC | MIN_VALUE | MAX_VALUE | RANGE | DATE | REGEX
        params_json    NVARCHAR(1000)    NULL,
        on_fail_action VARCHAR(16)       NOT NULL, -- REJECT_ROW | NULLIFY
        is_active      BIT               NOT NULL CONSTRAINT df_etl_rules_active DEFAULT 1,
        sort_order     INT               NOT NULL CONSTRAINT df_etl_rules_sort DEFAULT 100,
        description    NVARCHAR(500)     NULL,
        updated_at     DATETIME2         NOT NULL CONSTRAINT df_etl_rules_updated DEFAULT SYSUTCDATETIME()
    );
END;
GO

-- Seed cac rule mac dinh (chi chen neu chua co de bao toan trang thai bat/tat khi demo)
IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'REQUIRE_APPID')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('REQUIRE_APPID', N'Bat buoc co AppID', 'AppID', 'REQUIRED', NULL, 'REJECT_ROW', 1, 10,
            N'Loai bo ban ghi thieu khoa chinh AppID vao bang rejected');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'VALID_APPID_NUMERIC')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('VALID_APPID_NUMERIC', N'AppID phai la gia tri so hop le', 'AppID', 'NUMERIC', '{"allow_null": true}', 'REJECT_ROW', 1, 20,
            N'Loai bo AppID khong phai so');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'REJECT_NON_POSITIVE_APPID')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('REJECT_NON_POSITIVE_APPID', N'Chan AppID nho hon hoac bang 0', 'AppID', 'MIN_VALUE', '{"min": 1}', 'REJECT_ROW', 0, 25,
            N'Khi bat: loai bo AppID <= 0 ngay o tang staging');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'PRICE_NON_NEGATIVE')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('PRICE_NON_NEGATIVE', N'Gia game khong am (chuyen NULL neu < 0)', 'Price', 'MIN_VALUE', '{"min": 0}', 'NULLIFY', 1, 30,
            N'Giu dong nhung dua Price < 0 ve NULL o staging/dbt');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'DISCOUNT_RANGE')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('DISCOUNT_RANGE', N'Phan tram giam gia nam trong [0, 100]', 'Discount', 'RANGE', '{"min": 0, "max": 100}', 'NULLIFY', 1, 40,
            N'Dua Discount ngoai [0, 100] ve NULL');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'METACRITIC_RANGE')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('METACRITIC_RANGE', N'Diem Metacritic nam trong [1, 100]', 'Metacritic score', 'RANGE', '{"min": 1, "max": 100}', 'NULLIFY', 1, 50,
            N'Dua Metacritic ngoai [1, 100] ve NULL');

-- Cac rule mo rong san sang bat/tat trong demo (mac dinh is_active = 0)
IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'REJECT_NEGATIVE_PRICE')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('REJECT_NEGATIVE_PRICE', N'Chan dong co Price am (< 0)', 'Price', 'MIN_VALUE', '{"min": 0}', 'REJECT_ROW', 0, 60,
            N'Khi bat: dong co Price < 0 bi tu choi va ghi vao stg_steam_games_rejected');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'REQUIRE_GAME_NAME')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('REQUIRE_GAME_NAME', N'Bat buoc co ten game hop le', 'Name', 'REQUIRED', '{"disallow_placeholders": ["nan", "none", "null", "n/a"]}', 'REJECT_ROW', 0, 70,
            N'Khi bat: dong thieu Name bi tu choi thay vi gan Unknown game');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'REJECT_INVALID_DISCOUNT')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('REJECT_INVALID_DISCOUNT', N'Chan dong co Discount ngoai [0, 100]', 'Discount', 'RANGE', '{"min": 0, "max": 100}', 'REJECT_ROW', 0, 80,
            N'Khi bat: dong co Discount < 0 hoac > 100 bi tu choi vao rejected');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_validation_rules WHERE rule_code = 'REJECT_BAD_RELEASE_DATE')
    INSERT INTO dbo.etl_validation_rules (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order, description)
    VALUES ('REJECT_BAD_RELEASE_DATE', N'Bat buoc Release date dung dinh dang ngay', 'Release date', 'DATE', NULL, 'REJECT_ROW', 0, 90,
            N'Khi bat: dong thieu hoac sai dinh dang Release date bi tu choi vao rejected');
GO

IF OBJECT_ID('dbo.etl_kpi_definitions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.etl_kpi_definitions (
        kpi_code     VARCHAR(64)    NOT NULL PRIMARY KEY,
        kpi_name     NVARCHAR(200)  NOT NULL,
        target_model VARCHAR(64)    NOT NULL,
        formula_mode VARCHAR(32)    NOT NULL, -- THRESHOLD | FORMULA_VARIANT
        kpi_value    NVARCHAR(256)  NOT NULL,
        params_json  NVARCHAR(1000) NULL,
        description  NVARCHAR(500)  NULL,
        version_no   INT            NOT NULL CONSTRAINT df_etl_kpi_ver DEFAULT 1,
        updated_at   DATETIME2      NOT NULL CONSTRAINT df_etl_kpi_updated DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.etl_kpi_definitions WHERE kpi_code = 'PUBLISHER_AAA_MIN_GAMES')
    INSERT INTO dbo.etl_kpi_definitions (kpi_code, kpi_name, target_model, formula_mode, kpi_value, params_json, description)
    VALUES ('PUBLISHER_AAA_MIN_GAMES', N'Nguong phan tang nha phat hanh AAA', 'dim_publisher', 'THRESHOLD', '10',
            '{"min_games": 10}', N'So tua game toi thieu trong DWH de Publisher dat hang AAA (mac dinh >= 10)');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_kpi_definitions WHERE kpi_code = 'FREE_GAME_RULE')
    INSERT INTO dbo.etl_kpi_definitions (kpi_code, kpi_name, target_model, formula_mode, kpi_value, params_json, description)
    VALUES ('FREE_GAME_RULE', N'Dinh nghia game mien phi (is_free)', 'stg_steam_games_cleaned', 'FORMULA_VARIANT', 'PRICE_EQUALS_ZERO',
            '{"max_price": 0, "include_100_discount": false}', N'Mac dinh price = 0. Co the doi max_price (vd 0.99) hoac tinh ca discount = 100%');

IF NOT EXISTS (SELECT 1 FROM dbo.etl_kpi_definitions WHERE kpi_code = 'POSITIVE_RATIO_FORMULA')
    INSERT INTO dbo.etl_kpi_definitions (kpi_code, kpi_name, target_model, formula_mode, kpi_value, params_json, description)
    VALUES ('POSITIVE_RATIO_FORMULA', N'Cong thuc tinh ty le danh gia tich cuc', 'stg_steam_games_cleaned', 'FORMULA_VARIANT', 'STANDARD',
            '{"min_reviews": 1, "alpha": 0}', N'STANDARD: pos/(pos+neg) khi >= min_reviews; LAPLACE_SMOOTHED: (pos+alpha)/(pos+neg+2*alpha)');
GO

IF OBJECT_ID('dbo.etl_metadata_state', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.etl_metadata_state (
        state_key   VARCHAR(64)   NOT NULL PRIMARY KEY,
        state_value NVARCHAR(256) NULL,
        updated_at  DATETIME2     NOT NULL CONSTRAINT df_etl_state_updated DEFAULT SYSUTCDATETIME()
    );
END;
GO
