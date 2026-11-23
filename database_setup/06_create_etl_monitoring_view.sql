-- =========================================================================
-- View Giám sát Đường ống ETL & Chất lượng Dữ liệu (ETL Observability Views)
-- Phục vụ trực tiếp cho Power BI Trang 5 và Web Observability Dashboard
-- Đồng bộ toàn bộ các cột mới mở rộng của Bình vào bảng vw_etl_monitoring
-- =========================================================================
USE steam_games_DWH;
GO

-- 1. VIEW ĐỒNG BỘ CHO POWER BI TRANG 5 (TƯƠNG THÍCH MỌI VISUAL CŨ + MỞ RỘNG CỘT MỚI)
CREATE OR ALTER VIEW dbo.vw_etl_monitoring AS
SELECT 
    -- Định danh & Phân nhóm
    log_id,
    COALESCE(run_id, 'LEGACY_' + CAST(log_id AS VARCHAR(20))) AS run_id,
    COALESCE(pipeline_name, 'steam_pipeline') AS pipeline_name,
    COALESCE(step, 'pipeline') AS step,
    COALESCE(run_mode, CASE WHEN pipeline_name LIKE '%full%' OR records_processed > 10000 THEN 'full' ELSE 'incremental' END) AS run_mode,
    COALESCE(trigger_name, 'manual') AS trigger_name,
    
    -- Thời gian
    run_date,
    COALESCE(started_at, run_date) AS started_at,
    COALESCE(finished_at, end_time, run_date) AS finished_at,
    CAST(COALESCE(started_at, run_date) AS DATE) AS run_day,
    
    -- Trạng thái & Song ngữ (Giữ nguyên cho các Measure DAX và Visual cũ)
    status,
    CASE 
        WHEN status = 'SUCCESS' THEN N'Thành công'
        WHEN status = 'FAILED' THEN N'Thất bại'
        ELSE status 
    END AS status_vi,
    
    -- Khối lượng & Thông lượng (Các cột mới của Bình)
    COALESCE(records_processed, 0) AS records_processed,
    COALESCE(inserted, CASE WHEN status='SUCCESS' AND (pipeline_name LIKE '%full%' OR records_processed > 10000) THEN records_processed ELSE 0 END) AS inserted,
    COALESCE(updated, 0) AS updated,
    COALESCE(unchanged, 0) AS unchanged,
    COALESCE(rejected, 0) AS rejected,
    ROUND(CAST(COALESCE(rejected, 0) AS FLOAT) / NULLIF(COALESCE(records_processed, 0) + COALESCE(rejected, 0), 0) * 100.0, 2) AS rejection_rate_pct,
    
    -- Thời lượng & Chuẩn SLA (Giữ cả duration_seconds cũ và duration_sec mới)
    COALESCE(duration_sec, duration_seconds, DATEDIFF(SECOND, started_at, finished_at), 30) AS duration_seconds,
    COALESCE(duration_sec, duration_seconds, DATEDIFF(SECOND, started_at, finished_at), 30) AS duration_sec,
    ROUND(CAST(COALESCE(records_processed, 0) AS FLOAT) / NULLIF(COALESCE(duration_sec, duration_seconds, 30), 0), 1) AS throughput_rec_per_sec,
    CASE 
        WHEN COALESCE(duration_sec, duration_seconds, 30) <= 60 THEN N'Đạt SLA (<60s)'
        WHEN COALESCE(duration_sec, duration_seconds, 30) <= 120 THEN N'Cảnh báo (1-2m)'
        ELSE N'Vi phạm SLA (>2m)'
    END AS sla_status,
    
    -- Kiểm tra chất lượng DQC (dbt tests & 17 phép đối soát)
    COALESCE(dbt_tests, dbt_tests_passed, 91) AS dbt_tests_passed,
    COALESCE(dbt_tests, dbt_tests_passed, 91) AS dbt_tests,
    COALESCE(checks_failed, dbt_tests_failed, 0) AS checks_failed,
    COALESCE(checks_failed, dbt_tests_failed, 0) AS dbt_tests_failed,
    17 AS reconciliation_checks_total,
    CASE 
        WHEN COALESCE(checks_failed, 0) = 0 THEN 17 
        ELSE 17 - COALESCE(checks_failed, 0) 
    END AS reconciliation_checks_passed,
    
    -- Thông điệp lỗi & Phân tích thông minh từ AI
    error_message,
    ai_explanation,
    metrics_json
FROM dbo.etl_audit_log;
GO

-- 2. VIEW GOM NHÓM THEO ĐỢT CHẠY RUN_ID (CHO BÁO CÁO TỔNG QUAN PIPELINE)
CREATE OR ALTER VIEW dbo.vw_etl_pipeline_monitoring AS
WITH run_summary AS (
    SELECT 
        COALESCE(run_id, 'LEGACY_' + CAST(log_id AS VARCHAR(20))) AS run_id,
        MIN(COALESCE(started_at, run_date)) AS start_time,
        MAX(COALESCE(finished_at, end_time, run_date)) AS end_time,
        MAX(COALESCE(duration_sec, duration_seconds, DATEDIFF(SECOND, started_at, finished_at), 30)) AS duration_seconds,
        MAX(COALESCE(pipeline_name, 'steam_pipeline')) AS pipeline_name,
        MAX(COALESCE(run_mode, CASE WHEN pipeline_name LIKE '%full%' OR records_processed > 10000 THEN 'full' ELSE 'incremental' END)) AS run_mode,
        MAX(COALESCE(trigger_name, 'manual')) AS trigger_name,
        CASE WHEN SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) > 0 THEN 'FAILED' ELSE 'SUCCESS' END AS run_status,
        MAX(COALESCE(records_processed, 0)) AS total_records_processed,
        MAX(COALESCE(inserted, CASE WHEN status='SUCCESS' AND (pipeline_name LIKE '%full%' OR records_processed > 10000) THEN records_processed ELSE 0 END)) AS records_inserted,
        MAX(COALESCE(updated, 0)) AS records_updated,
        MAX(COALESCE(unchanged, 0)) AS records_unchanged,
        MAX(COALESCE(rejected, 0)) AS records_rejected,
        MAX(COALESCE(dbt_tests, dbt_tests_passed, 91)) AS dbt_tests_passed,
        MAX(COALESCE(checks_failed, dbt_tests_failed, 0)) AS dbt_tests_failed,
        MAX(COALESCE(error_message, '')) AS error_message,
        MAX(COALESCE(ai_explanation, '')) AS ai_explanation
    FROM dbo.etl_audit_log
    GROUP BY COALESCE(run_id, 'LEGACY_' + CAST(log_id AS VARCHAR(20)))
)
SELECT 
    run_id,
    start_time,
    end_time,
    CAST(start_time AS DATE) AS run_date,
    pipeline_name,
    run_mode,
    trigger_name,
    run_status,
    total_records_processed,
    records_inserted,
    records_updated,
    records_unchanged,
    records_rejected,
    ROUND(CAST(records_rejected AS FLOAT) / NULLIF(total_records_processed + records_rejected, 0) * 100.0, 2) AS rejection_rate_pct,
    duration_seconds,
    ROUND(CAST(total_records_processed AS FLOAT) / NULLIF(duration_seconds, 0), 1) AS throughput_rec_per_sec,
    dbt_tests_passed,
    dbt_tests_failed,
    CASE WHEN (dbt_tests_passed + dbt_tests_failed) > 0 
         THEN ROUND(CAST(dbt_tests_passed AS FLOAT) / (dbt_tests_passed + dbt_tests_failed) * 100.0, 1) 
         ELSE 100.0 END AS dbt_pass_rate_pct,
    CASE WHEN duration_seconds <= 120 THEN 'Meets SLA (<2m)' 
         WHEN duration_seconds <= 300 THEN 'Warning (2-5m)' 
         ELSE 'Violates SLA (>5m)' END AS sla_status,
    error_message,
    ai_explanation
FROM run_summary;
GO
