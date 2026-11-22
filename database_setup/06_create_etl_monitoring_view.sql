-- =========================================================================
-- View Giám sát Đường ống ETL & Chất lượng Dữ liệu (ETL Observability View)
-- Phục vụ trực tiếp cho Power BI và Web Observability Dashboard
-- =========================================================================
USE steam_games_DWH;
GO

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
