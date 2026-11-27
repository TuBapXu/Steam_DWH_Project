# Kịch Bản Kiểm Thử Trực Tiếp & Đối Chiếu Thiết Kế Rule Ban Đầu

Tài liệu này tổng hợp bộ kịch bản kiểm thử end-to-end (chạy thật qua **Mage `PipelineExecutor` + SQL Server 2022 + dbt 1.12.6 + 17 phép đối soát DWH**) và **đối chiếu từng Test Case với thiết kế rule ban đầu** của đồ án.

---

## Phần 1: Bảng đối chiếu thiết kế Rule & KPI ban đầu vs Cơ chế Metadata-driven

| STT | Rule / KPI trong thiết kế ban đầu | Vị trí thiết kế ban đầu | Hành vi thiết kế ban đầu | Ánh xạ trong kiến trúc Metadata-driven |
|---|---|---|---|---|
| **R1** | Hợp đồng 40 cột & cú pháp CSV (`INVALID_CSV`, `TOO_MANY_FIELDS`) | [full_load.py](../pipeline_support/full_load.py) (`CSV_COLUMNS`, `read_chunks`) | Chặn dòng lỗi ngoặc kép/thừa cột tại `PREPARE`, ghi vào `dbo.stg_steam_games_rejected`. | Giữ nguyên tầng parser bất biến; ghi `PREPARE` vào `dbo.stg_steam_games_rejected`. |
| **R2** | Bắt buộc có `AppID` & `AppID` phải là số (`MISSING_APPID`, `INVALID_APPID`) | [cleaning.py](../pipeline_support/cleaning.py), [dynamic_chunks.py](../pipeline_support/dynamic_chunks.py) | Loại dòng không có/sai định dạng `AppID` tại `VALIDATE`, ghi vào `dbo.stg_steam_games_rejected`. | Rule `REQUIRE_APPID` & `VALID_APPID_NUMERIC` (`is_active=1`, `on_fail_action='REJECT_ROW'`) trong `dbo.etl_validation_rules`. |
| **R3** | Khử trùng `AppID` (giữ bản ghi cuối cùng) | [cleaning.py](../pipeline_support/cleaning.py), [sql_full_load.py](../pipeline_support/sql_full_load.py) | `drop_duplicates('appid', keep='last')` + `MAX(__source_row)` trên toàn file. | Giữ nguyên toàn vẹn khóa nghiệp vụ `AppID`. |
| **R4** | Tên game thiếu (`Name` NULL/rỗng) | [stg_steam_games_cleaned.sql](../dbt_transform/models/staging/stg_steam_games_cleaned.sql) | **Không xóa dòng**; thay bằng `'Unknown game <AppID>'` và đặt `is_title_missing = 1`. | Mặc định giữ nguyên (`REQUIRE_GAME_NAME` có `is_active=0`). Khi bật `REQUIRE_GAME_NAME = 1`, chặn dòng thiếu tên vào `rejected` không cần sửa code. |
| **R5** | Ngày phát hành thiếu / sai định dạng | [cleaning.py](../pipeline_support/cleaning.py), [fact_game_snapshot.sql](../dbt_transform/models/marts/fact_game_snapshot.sql) | **Không xóa dòng**; chỉ đếm `bad_dates` và ánh xạ vào `dim_date.date_key = 0` (`Unknown`). | Mặc định giữ nguyên (`REJECT_BAD_RELEASE_DATE` có `is_active=0`). Có thể bật để chặn dòng sai ngày nếu nghiệp vụ yêu cầu. |
| **R6** | Giá bán không âm (`Price >= 0`) | [stg_steam_games_cleaned.sql](../dbt_transform/models/staging/stg_steam_games_cleaned.sql), [schema.yml](../dbt_transform/models/staging/schema.yml) | Đưa `Price < 0` về `NULL` (`steam_nonnegative`), kiểm tra `valid_range` trong dbt. | Rule `PRICE_NON_NEGATIVE` (`NULLIFY`, `is_active=1`) và `REJECT_NEGATIVE_PRICE` (`REJECT_ROW`, `is_active=0`). `valid_range` tự thích ứng theo `rule_price_non_negative`. |
| **R7** | Mức giảm giá hợp lệ (`Discount` trong `[0, 100]`) | [stg_steam_games_cleaned.sql](../dbt_transform/models/staging/stg_steam_games_cleaned.sql), [schema.yml](../dbt_transform/models/staging/schema.yml) | Đưa giá trị ngoài `[0, 100]` về `NULL`, kiểm tra `valid_range(0, 100)`. | Rule `DISCOUNT_RANGE` (`NULLIFY`, `is_active=1`) và `REJECT_INVALID_DISCOUNT` (`REJECT_ROW`, `is_active=0`). |
| **R8** | Điểm Metacritic hợp lệ (`[1, 100]`) | [stg_steam_games_cleaned.sql](../dbt_transform/models/staging/stg_steam_games_cleaned.sql), [schema.yml](../dbt_transform/models/staging/schema.yml) | Đưa giá trị ngoài `[1, 100]` về `NULL`, kiểm tra `valid_range(1, 100)`. | Rule `METACRITIC_RANGE` (`NULLIFY`, `is_active=1`) điều khiển cả Python & dbt `valid_range`. |
| **K1** | Định nghĩa `is_free` | [stg_steam_games_cleaned.sql](../dbt_transform/models/staging/stg_steam_games_cleaned.sql), [assert_derived_metrics.sql](../dbt_transform/tests/assert_derived_metrics.sql) | Hardcode: `price = 0 -> 1`, `price > 0 -> 0`, `else NULL`. | KPI `FREE_GAME_RULE` trong `dbo.etl_kpi_definitions`: cấu hình `max_price` và `include_100_discount`. |
| **K2** | Định nghĩa `positive_review_ratio` | [stg_steam_games_cleaned.sql](../dbt_transform/models/staging/stg_steam_games_cleaned.sql), [assert_derived_metrics.sql](../dbt_transform/tests/assert_derived_metrics.sql) | Hardcode: `positive / (positive + negative)` khi tổng `> 0`. | KPI `POSITIVE_RATIO_FORMULA`: chọn `STANDARD` hoặc `LAPLACE_SMOOTHED`, kèm `min_reviews` và `alpha`. |
| **K3** | Phân tầng `publisher_tier` (`AAA` / `Indie`) | [dim_publisher.sql](../dbt_transform/models/marts/dim_publisher.sql) | Hardcode: `game_count >= 10 -> 'AAA' else 'Indie'`. | KPI `PUBLISHER_AAA_MIN_GAMES`: thay đổi ngưỡng `min_games` động; `dim_publisher` dùng `MERGE` giữ nguyên `publisher_key`. |

---

## Phần 2: Kịch bản & Kết quả Kiểm thử Trực tiếp (Live E2E trên Docker)

Hai bộ kiểm thử tích hợp được chạy trực tiếp trong container `mage` kết nối SQL Server thật:
1. `tests/verify_mage_incremental.py`: **PASS** (kiểm tra baseline Full/Incremental V1/V2/V3, lỗi staging, lỗi dbt + resume cùng batch window LSET/CET, thay đổi platform/publisher/date).
2. `tests/verify_demo_rules_kpi.py`: **ALL DEMO METADATA E2E TESTS PASSED!** — chi tiết 10 test case bên dưới:

| Test Case | File CSV Incremental | Cấu hình Metadata áp dụng | Đối chiếu Rule ban đầu | Kết quả thực tế quan sát được (Live Run) | Trạng thái |
|---|---|---|---|---|---|
| **TC1** (Dữ liệu đúng - Nạp mới) | `tc1_valid_incremental.csv` | Mặc định (giống thiết kế ban đầu) | R2, R3, R6–R8, K1–K3 | `inserted=3`, `rejected=0`, `dbt_tests=91`, `checks_failed=0`; game `920103` (`$29.99, discount=100, 3 pos/1 neg`) đạt `is_free=0`, `positive_review_ratio=0.75`, `publisher_tier='Indie'`. | **PASS** |
| **TC1b** (Dữ liệu đúng - Cập nhật & Lặp lại) | `tc1b_valid_update.csv` | Mặc định | R3 + cơ chế `row_hash` Incremental | Lần 1: `inserted=1` (`920104`), `updated=1` (`920101` `positive_reviews=150`), `unchanged=2`, `rejected=0`. Chạy lại lần 2: `inserted=0, updated=0, unchanged=4`. | **PASS** |
| **TC2** (Dữ liệu sai - Hỗn hợp) | `tc2_invalid_mixed.csv` | Mặc định | R1 (`INVALID_CSV`, `TOO_MANY_FIELDS`), R2 (`INVALID_APPID`, `MISSING_APPID`), R5–R8 | `inserted=2` (`920201`, `920203`), `rejected=4` ghi đúng 4 mã lỗi `['INVALID_APPID', 'MISSING_APPID', 'INVALID_CSV', 'TOO_MANY_FIELDS']` vào `stg_steam_games_rejected`; dòng `920203` có cột bẩn (`Price=-10, Discount=150, Metacritic=999, Date=bad-date`) được chuẩn hóa về `(None, None, None, None, date_key=0)`. | **PASS** |
| **TC3a** (Rule mặc định trước khi đổi) | `tc3_rule_toggle.csv` | `REJECT_NEGATIVE_PRICE=0`, `REQUIRE_GAME_NAME=0` | R4 (`Unknown game`), R6 (`Price < 0 -> NULL`), R7 (`Discount 150 -> NULL`) | `inserted=4, rejected=0`; `920302` (`price=NULL`), `920303` (`Unknown game 920303`, `is_title_missing=1`), `920304` (`discount=NULL`). | **PASS** |
| **TC3b** (Bật rule chặn qua SQL, không sửa code) | `tc3_rule_toggle.csv` | `UPDATE etl_validation_rules SET is_active=1` cho `REJECT_NEGATIVE_PRICE`, `REQUIRE_GAME_NAME` | Mở rộng R4, R6 từ `NULLIFY`/`FILL` sang `REJECT_ROW` | Chặn đúng 2 dòng vi phạm vào `stg_steam_games_rejected`: `('REJECT_NEGATIVE_PRICE', '920302')` và `('REQUIRE_GAME_NAME', '920303')`; 91 dbt tests & 17 checks PASS. | **PASS** |
| **TC3c** (Thêm rule mới hoàn toàn qua SQL) | `tc3_rule_toggle.csv` | `INSERT` rule mới `MAX_PRICE_10` (`MAX_VALUE`, `{"max": 10}`, `REJECT_ROW`) | Chứng minh mở rộng rule mới hoàn toàn không có trong code | Tự động chặn `920301` (`Price=12.99 > 10`) với `reason_code='MAX_PRICE_10'` vào `stg_steam_games_rejected`. | **PASS** |
| **TC3d** (Gỡ rule & tắt `PRICE_NON_NEGATIVE`) | CSV phát sinh từ `tc3` (`920305`, `Price=-7.50`) | `DELETE MAX_PRICE_10`, tắt `PRICE_NON_NEGATIVE=0` rồi bật lại `=1` | Đối chiếu R6 + `valid_range` dbt test | Khi tắt `PRICE_NON_NEGATIVE`: `920305` đi qua DWH với `price=-7.50` và dbt tests vẫn PASS. Khi bật lại `=1`: pipeline tự phát hiện đổi config và tái tính `920305` về `price=NULL`. | **PASS** |
| **TC4a** (KPI mặc định) | `tc4_kpi_change.csv` | `AAA>=10`, `is_free=(price=0)`, `ratio=STANDARD(min=1)` | K1, K2, K3 ban đầu | `KPI Demo Pub` (`3` game < 10) = `'Indie'`; `920401` (`$0.99, 2/0`) = `(is_free=0, ratio=1.0)`; `920402` (`$19.99, 100% off`) = `(is_free=0, ratio=0.8)`. | **PASS** |
| **TC4b** (Đổi cả 3 định nghĩa KPI qua SQL) | `tc4_kpi_change.csv` | `AAA>=3`, `max_price=0.99 & include_100_discount=true`, `LAPLACE_SMOOTHED(alpha=1)` | Thay đổi K1, K2, K3 đồng thời tái tính dữ liệu cũ qua `STEAM_RECOMPUTE_CONFIG=1` | `recompute_config=True`; `KPI Demo Pub` giữ nguyên `publisher_key=5` và đổi sang `'AAA'`; `920401` -> `(is_free=1, ratio=0.75)`; `920402` -> `(is_free=1, ratio=21/27 ≈ 0.7778)`. | **PASS** |
| **TC4c** (Đổi công thức `min_reviews=5`) | `tc4_kpi_change.csv` | `POSITIVE_RATIO_FORMULA = STANDARD`, `{"min_reviews": 5, "alpha": 0}` | Thay đổi K2 lần 2 (lọc game ít review) | `920401` (chỉ có 2 reviews < 5) đổi `ratio=NULL`; `920402` (25 reviews >= 5) giữ `ratio=0.8`. | **PASS** |

---

## Phần 3: Cách chạy lại toàn bộ kiểm thử

```powershell
# 1. Bộ 37 unit tests Python (chạy offline trên host)
python -m unittest discover -s tests -p "test_*.py" -v

# 2. Kiểm thử tích hợp baseline trên Docker (SQL Server + Mage + dbt)
docker compose exec -T -w /home/src/mage_pipeline mage python /home/src/tests/verify_mage_incremental.py

# 3. Kiểm thử E2E toàn bộ 4 nhóm kịch bản demo (TC1 -> TC4c) trên Docker
docker compose exec -T -w /home/src/mage_pipeline mage python /home/src/tests/verify_demo_rules_kpi.py
```
