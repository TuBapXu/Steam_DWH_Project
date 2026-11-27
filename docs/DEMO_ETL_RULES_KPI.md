# Hướng dẫn Demo ETL Metadata-Driven (Tuần 12 - 1/12/2026)

Hệ thống đã được nâng cấp theo kiến trúc **Metadata-driven** với 3 bảng cấu hình trong SQL Server ([07_create_metadata_rules_kpi.sql](../database_setup/07_create_metadata_rules_kpi.sql)):
- `dbo.etl_validation_rules`: Danh sách rule kiểm tra dữ liệu (thêm/gỡ/bật/tắt không cần sửa code Python hay SQL).
- `dbo.etl_kpi_definitions`: Định nghĩa ngưỡng và công thức tính KPI (đổi công thức không cần sửa SQL model).
- `dbo.etl_metadata_state`: Lưu `LAST_APPLIED_CONFIG_HASH`. Khi rule hoặc KPI thay đổi, `run_dbt_transform` tự động phát hiện hash mới và bật `STEAM_RECOMPUTE_CONFIG=1` để tái tính lại dữ liệu cũ trong DWH kể cả khi chạy `incremental`.

Bạn có thể chỉnh sửa trực tiếp qua **SQL** hoặc qua tab **⚙️ Cấu Hình Rule & KPI** trên Steam Copilot Web App (`http://localhost:5000`).

---

## Khởi tạo bảng Metadata (chạy 1 lần nếu DB đã có sẵn)

Khi khởi động Docker (`bootstrap.py` tự động chạy script `07_create_metadata_rules_kpi.sql`), hoặc chạy thủ công:
```powershell
docker compose exec -T mage python /home/src/database_setup/bootstrap.py
```

---

## 4 Kịch bản Demo Incremental Load trên Mage (`steam_staging_pipeline`)

Mở Mage UI (`http://localhost:6790`) -> `steam_staging_pipeline` -> Triggers -> Run once, giữ nguyên `run_mode: incremental`, `chunk_size: 1000`, `demo_lset: null`, `demo_cet: null`, chỉ thay đổi biến `source_file`:

### Case 1: Dữ liệu đúng (Incremental Insert -> Update -> Unchanged)
1. **Lượt 1**: Đặt `source_file: tests/fixtures/demo/tc1_valid_incremental.csv` -> Run now.
   - Kết quả: `inserted = 3` (`920101`, `920102`, `920103`), `rejected = 0`, 91 dbt tests PASS, 17 checks PASS.
2. **Lượt 2**: Đặt `source_file: tests/fixtures/demo/tc1b_valid_update.csv` -> Run now.
   - Kết quả: `inserted = 1` (`920104`), `updated = 1` (`920101` đổi `Positive` từ `100` -> `150`), `unchanged = 2` (`920102`, `920103`).

### Case 2: Dữ liệu sai (Mixed Valid & Invalid)
- Đặt `source_file: tests/fixtures/demo/tc2_invalid_mixed.csv` -> Run now.
- Kết quả mong đợi:
  - `920201` (hợp lệ) và `920203` (cột phụ bẩn: `Price=-10`, `Discount=150`, `Metacritic=999`, `Release date=bad-date` được chuẩn hóa thành `NULL`) đi vào Staging & DWH.
  - 4 dòng lỗi bị chặn vào `dbo.stg_steam_games_rejected`:
    - `invalid-appid` -> `INVALID_APPID` (`VALIDATE`)
    - AppID rỗng -> `MISSING_APPID` (`VALIDATE`)
    - `"Ngoac kep loi"x` -> `INVALID_CSV` (`PREPARE`)
    - 41 cột -> `TOO_MANY_FIELDS` (`PREPARE`)
- Kiểm tra:
  ```sql
  SELECT source_file, line_start, rejected_stage, reason_code, reason_detail, raw_appid
  FROM dbo.stg_steam_games_rejected
  WHERE source_file LIKE '%tc2_invalid_mixed.csv%'
  ORDER BY line_start;
  ```

### Case 3: Thêm / Gỡ Rule KHÔNG sửa code
- Đặt `source_file: tests/fixtures/demo/tc3_rule_toggle.csv` (gồm `920301` hợp lệ, `920302` giá `-5.00`, `920303` thiếu tên, `920304` discount `150`).
1. **Mặc định** (`REJECT_NEGATIVE_PRICE = 0`, `REQUIRE_GAME_NAME = 0`): Chạy incremental -> cả 4 dòng đi qua (`Price=-5`, `Discount=150` được `NULLIFY`, `920303` thành `'Unknown game 920303'`).
2. **Thêm / Bật rule (không sửa code)**: Vào tab **⚙️ Cấu Hình Rule & KPI** (hoặc chạy SQL):
   ```sql
   UPDATE dbo.etl_validation_rules SET is_active = 1 WHERE rule_code IN ('REJECT_NEGATIVE_PRICE', 'REQUIRE_GAME_NAME');
   ```
   Chạy lại incremental với `tc3_rule_toggle.csv` -> `920302` và `920303` lập tức bị chặn vào `dbo.stg_steam_games_rejected` với `reason_code = 'REJECT_NEGATIVE_PRICE'` và `'REQUIRE_GAME_NAME'`.
3. **Gỡ / Tắt rule (không sửa code)**:
   ```sql
   UPDATE dbo.etl_validation_rules SET is_active = 0 WHERE rule_code IN ('REJECT_NEGATIVE_PRICE', 'REQUIRE_GAME_NAME');
   ```
   (Hoặc thêm rule mới hoàn toàn, ví dụ `MAX_PRICE_50`, trực tiếp trên giao diện hoặc `INSERT INTO dbo.etl_validation_rules ...`).

### Case 4: Thay đổi định nghĩa cách tính KPI KHÔNG sửa code
- Đặt `source_file: tests/fixtures/demo/tc4_kpi_change.csv` (3 game của `KPI Demo Pub`: `920401` giá `$0.99` có `2 pos / 0 neg`; `920402` giá `$19.99` giảm `100%`; `920403` giá `$14.99`).
1. **Chạy với định nghĩa KPI mặc định**:
   - `KPI Demo Pub` (3 game < 10) -> `publisher_tier = 'Indie'`.
   - `920401` (`$0.99`) và `920402` (`100% discount`) -> `is_free = 0`.
   - `920401` (`2/2`) -> `positive_review_ratio = 1.0000`.
2. **Đổi định nghĩa KPI trong SQL / Tab Cấu Hình Rule & KPI** (không sửa model dbt):
   ```sql
   UPDATE dbo.etl_kpi_definitions SET kpi_value = '3', params_json = '{"min_games": 3}', version_no = version_no + 1
   WHERE kpi_code = 'PUBLISHER_AAA_MIN_GAMES';

   UPDATE dbo.etl_kpi_definitions SET kpi_value = 'INCLUDE_100_DISCOUNT', params_json = '{"max_price": 0.99, "include_100_discount": true}', version_no = version_no + 1
   WHERE kpi_code = 'FREE_GAME_RULE';

   UPDATE dbo.etl_kpi_definitions SET kpi_value = 'LAPLACE_SMOOTHED', params_json = '{"min_reviews": 1, "alpha": 1}', version_no = version_no + 1
   WHERE kpi_code = 'POSITIVE_RATIO_FORMULA';
   ```
3. **Chạy lại incremental với đúng `tc4_kpi_change.csv`**:
   - `run_dbt_transform` tự động phát hiện `LAST_APPLIED_CONFIG_HASH` thay đổi -> tái tính lại DWH:
     - `KPI Demo Pub` chuyển từ `'Indie'` -> `'AAA'`.
     - `920401` và `920402` chuyển từ `is_free = 0` -> `is_free = 1`.
     - `920401` chuyển `positive_review_ratio` từ `1.0000` -> `0.7500` (`(2+1)/(2+0+2)`).
   - Kiểm tra kết quả:
     ```sql
     SELECT c.game_id, c.game_title, c.price, c.discount_percentage, c.is_free, c.positive_review_ratio, p.publisher_name, p.publisher_tier
     FROM dbt_staging.stg_steam_games_cleaned c
     JOIN dwh.dim_game g ON g.appid_nk = c.game_id
     JOIN dwh.fact_game_snapshot f ON f.game_key = g.game_key
     JOIN dwh.dim_publisher p ON p.publisher_key = f.publisher_key
     WHERE c.game_id BETWEEN 920401 AND 920403;
     ```
