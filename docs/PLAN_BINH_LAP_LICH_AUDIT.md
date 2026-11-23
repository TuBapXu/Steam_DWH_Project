# Plan công việc – Nguyễn Ngọc Bình (đợt nộp 23/11/2026)

| Việc được giao | Kết quả cần có |
|---|---|
| 1. Cấu hình **Schedule Trigger** trên Mage.ai (cron) | Pipeline Mage có trigger **tự chạy** |
| 2. Hoàn thiện **ghi log audit và metrics chi tiết** vào SQL Server | Bảng `etl_audit_log` **đầy đủ dữ liệu** |
| 3. **Kiểm thử** các kịch bản chạy tự động (Success / Failure) | Có bằng chứng lượt thành công và lượt lỗi đều được ghi đúng |

**Đã chốt:**
- **Mở rộng chính bảng `etl_audit_log`**: thêm cột, không tạo bảng mới, không tạo view. **Mỗi bước vẫn là 1 dòng**; các dòng cùng một lượt chạy có chung **`run_id`**.
- **Lập lịch theo tháng**: incremental mỗi tháng một lần, cộng một trigger kiểm thử/demo chạy dày, mặc định tắt.

**Không ảnh hưởng dashboard cũ:** 4 trang Power BI hiện tại chỉ đọc schema `dwh`, không đọc `etl_audit_log`. Việc mở rộng chỉ **thêm cột cho phép NULL**: 6 cột cũ và dữ liệu cũ giữ nguyên, dữ liệu game trong kho không thay đổi.

**Liên quan tới bạn khác:**
- Bạn làm **dashboard giám sát** đọc `etl_audit_log`: gửi bạn ấy **danh sách cột mới** (mục 2.2) sớm nhất có thể.
- Bạn làm **AI** có thể đọc `metrics_json` để giải thích lượt chạy.

---

## 0. Hiện trạng (đọc từ code)

**`etl_audit_log` hiện có 6 cột:** `log_id`, `pipeline_name`, `run_date`, `status`, `records_processed`, `error_message`. Bảng đang được ghi từ **5 chỗ khác nhau**, mỗi chỗ một kiểu:

| # | Nơi ghi | Ghi khi nào | Thiếu gì |
|---|---|---|---|
| 1 | `pipeline_support/sql_full_load.py` – `publish` | Full load thành công | Không có run_id, thời lượng, số dòng bị loại |
| 2 | `pipeline_support/sql_full_load.py` – `publish_incremental` | Incremental thành công | Số thêm/sửa/giữ nguyên chỉ lưu ở `etl_steam_incremental_batch` |
| 3 | `sql_full_load.py` – `record_failure` | Staging lỗi | run_id bị nhét vào chuỗi `error_message` |
| 4 | `pipeline_support/mage_dwh.py` – `audit()` / `failure()` | Bước dbt, đối soát; lỗi chunk | Số model/test dbt và 17 phép đối soát chỉ in log hoặc lưu file JSON |
| 5 | `mage_pipeline/callbacks/log_failure.py` | Lỗi chưa được bước nào ghi | Ghép chuỗi SQL bằng tay, không có run_id |

Ngoài ra, lượt incremental có file **toàn dòng lỗi** (`NO_VALID_RECORDS`) hiện **không ghi dòng staging nào** vào audit.

**Lập lịch:** `metadata.yaml` có `triggers: null`, tức là chưa có trigger nào.

---

## 1. Schedule Trigger trên Mage (cron) – lập lịch theo tháng

### 1.1. Làm gì
Tạo file **`mage_pipeline/pipelines/steam_staging_pipeline/triggers.yaml`** (trigger viết bằng code, commit được, cả nhóm dùng chung) gồm 2 trigger:

| Trigger | Cron (UTC) | Giờ Việt Nam | Trạng thái | Mục đích |
|---|---|---|---|---|
| `monthly_incremental` | `0 0 1 * *` | **07:00 sáng ngày 1 hằng tháng** | **active** | Lịch chính: mỗi tháng nạp phần thay đổi một lần |
| `test_every_15_min` | `*/15 * * * *` | mỗi 15 phút | **inactive** | Chỉ bật khi kiểm thử hoặc demo, vì lịch tháng phải đợi tới ngày 1 mới thấy chạy |

Cả hai đặt biến `run_mode: incremental`, `source_file: data/games.csv`, `chunk_size: 1000`, và thêm biến **`trigger_name`** bằng đúng tên trigger để audit ghi được lượt nào do trigger nào chạy (lượt bấm tay ghi `manual`). Cấu hình thêm `skip_if_previous_running: true` (không chạy chồng) và `timeout: 7200` (quá 2 giờ thì dừng, báo FAILED).

### 1.2. Vì sao
- Mage có sẵn bộ lập lịch, đúng ý "**điều phối**" trong yêu cầu, không cần cron của hệ điều hành.
- **Theo tháng:** bộ dữ liệu Steam trên Kaggle được cập nhật theo đợt, không đổi từng giờ, nên mỗi tháng nạp một lần là hợp lý và tránh chạy thừa.
- Dùng **incremental** vì lượt định kỳ chỉ cần nạp phần thay đổi.
- Container chạy giờ **UTC**: `0 0 1 * *` là 00:00 UTC ngày 1, tức **07:00 giờ Việt Nam ngày 1**. Muốn đúng nửa đêm giờ VN ngày 1 thì phải chạy 17:00 UTC ngày cuối tháng trước, cron không biểu diễn gọn được "ngày cuối tháng", nên chọn 07:00 sáng ngày 1.

### 1.3. Kiểm tra
- `docker compose restart mage` → Mage UI → pipeline → **Triggers**: thấy 2 trigger, `monthly_incremental` **Active** và **Next run** là ngày 1 tháng sau.
- Bật tạm `test_every_15_min` → chờ 1 lượt **tự chạy** → tab **Runs** báo *completed* → tắt lại.

---

## 2. Audit log và metrics chi tiết (mở rộng `etl_audit_log`)

### 2.1. Thiết kế
- **Giữ nguyên** 6 cột cũ, nên truy vấn cũ không hỏng.
- **Mỗi bước 1 dòng:** `staging`, `dbt`, `check`; bước lỗi cũng 1 dòng. Các dòng của cùng một lượt chạy có chung **`run_id`**, nên muốn xem cả lượt thì `GROUP BY run_id`.
- Thêm cột bằng `ALTER TABLE … ADD` có kiểm tra `COL_LENGTH` (chạy lại nhiều lần không lỗi). Đặt trong script **`database_setup/05_extend_etl_audit_log.sql`**, gọi từ `bootstrap.py`, tức là tự chạy khi Mage khởi động.

### 2.2. Các cột thêm mới (gửi cho bạn làm dashboard)

| Cột | Kiểu | Ý nghĩa | Có giá trị ở bước |
|---|---|---|---|
| `run_id` | `char(32)` | Mã lượt chạy, gom các bước của 1 lượt | tất cả |
| `step` | `varchar(20)` | `staging` / `dbt` / `check` / `chunk` / `pipeline` (lỗi từ callback) | tất cả |
| `trigger_name` | `nvarchar(100)` | `monthly_incremental`, `test_every_15_min` hoặc `manual` | tất cả |
| `run_mode` | `varchar(20)` | `full` / `incremental` | tất cả |
| `started_at`, `finished_at` | `datetime2` | Bắt đầu, kết thúc của bước (giờ **UTC**, như `run_date` hiện tại) | tất cả |
| `duration_sec` | `int` | Thời lượng bước (giây) | tất cả |
| `inserted`, `updated`, `unchanged` | `int` | Số game thêm / sửa / giữ nguyên | staging |
| `rejected` | `int` | Số dòng bị loại (lỗi parser + AppID sai) | staging |
| `dbt_tests` | `int` | Số test dbt đã chạy (kèm số model trong `metrics_json`) | dbt |
| `checks_failed` | `int` | Số phép đối soát lỗi (trên tổng 17) | check |
| `metrics_json` | `nvarchar(max)` | Toàn bộ chi tiết của bước: số dòng nguồn, số trùng, số model dbt, số dòng từng bảng DWH, giá trị từng phép đối soát, cửa sổ LSET/CET | tất cả |

**Truy vấn mẫu cho dashboard** (1 dòng / lượt chạy):
```sql
SELECT run_id, MIN(started_at) AS started_at, MAX(finished_at) AS finished_at,
       DATEDIFF(SECOND, MIN(started_at), MAX(finished_at)) AS duration_sec,
       MAX(run_mode) AS run_mode, MAX(trigger_name) AS trigger_name,
       CASE WHEN SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) > 0 THEN 'FAILED' ELSE 'SUCCESS' END AS run_status,
       MAX(inserted) AS inserted, MAX(updated) AS updated, MAX(unchanged) AS unchanged, MAX(rejected) AS rejected,
       MAX(dbt_tests) AS dbt_tests, MAX(checks_failed) AS checks_failed
FROM dbo.etl_audit_log
WHERE run_id IS NOT NULL
GROUP BY run_id;
```

### 2.3. Sửa code
1. **Hàm ghi audit dùng chung** `write_audit(connection, *, pipeline_name, step, status, run_id, …)` trong file mới **`pipeline_support/audit.py`**: dùng tham số `?` (không ghép chuỗi SQL), tự tính `duration_sec`, tự chuyển `metrics` sang JSON.
2. Thay cả **5 chỗ** ở mục 0 bằng hàm này và điền đủ số liệu:
   - staging full / incremental: `inserted`, `updated`, `unchanged`, `rejected`, cùng số dòng nguồn và số trùng trong `metrics_json`. **Thêm** dòng audit cho trường hợp `NO_VALID_RECORDS`.
   - dbt: `dbt_tests`, cùng số model trong `metrics_json` (lấy từ kết quả `build_dbt`).
   - check: `checks_failed`, cùng giá trị 17 phép đối soát và số dòng từng bảng DWH trong `metrics_json` (lấy từ `inspect_dwh`).
3. **Truyền `run_id`, `started_at`, `trigger_name` xuyên suốt pipeline:** đưa vào `plan` ở bước `prepare_steam_chunks`, đi theo kết quả giữa các block (staging → dbt → check). Nhờ vậy cả 3 dòng có cùng `run_id`. Chạy lại một batch đang dở là một lần chạy mới (`run_id` mới): dòng `staging` của lần đó ghi `"resumed": true` và cùng `batch_id` (trong `metrics_json`) với lần bị lỗi.
4. **Callback `log_failure.py`:** dùng `write_audit`, ghi `step='pipeline'`, `trigger_name`, `run_mode` từ biến pipeline. Vẫn giữ cơ chế không ghi trùng khi bước lỗi đã tự ghi.
5. Giữ nguyên chữ ký các hàm `publish(expected)` / `record_failure(message)` để không làm hỏng test hiện có. Thông tin lượt chạy được truyền qua thuộc tính của đối tượng store.

### 2.4. Kiểm tra
```sql
SELECT TOP 20 log_id, run_id, step, pipeline_name, run_mode, trigger_name, status,
       started_at, duration_sec, records_processed, inserted, updated, unchanged, rejected,
       dbt_tests, checks_failed, error_message
FROM dbo.etl_audit_log ORDER BY log_id DESC;
```

---

## 3. Kiểm thử các kịch bản chạy tự động (Success / Failure)

### 3.1. Kiểm thử bằng code
- **Unit test mới** `tests/test_audit.py`: `write_audit` tạo đúng câu SQL và tham số (kết nối giả, không cần Docker), tính đúng `duration_sec`, chuyển đúng `metrics_json`.
- **Mở rộng `tests/verify_mage_incremental.py`** (chạy pipeline thật qua engine Mage trên **database test riêng**): kiểm tra các cột mới cho từng kịch bản.
- Chạy lại toàn bộ test hiện có. Lưu ý trước khi sửa, chạy trên Windows đã có 1 test fail và 3 test lỗi do môi trường máy (pandas / pyodbc), không phải do code mới. Sẽ chạy trong container Mage để có kết quả chuẩn.

### 3.2. Kịch bản kiểm thử
S1–S5 chạy trên **database test riêng** để không làm bẩn dữ liệu thật.

| # | Kịch bản | Cách tạo | Kết quả mong đợi trong `etl_audit_log` |
|---|---|---|---|
| S1 | Full load thành công | `run_mode=full`, fixture V1 | 3 dòng cùng `run_id`: staging / dbt / check đều SUCCESS; `dbt_tests` > 0; `checks_failed = 0` |
| S2 | Incremental có thay đổi | fixture V2 | staging SUCCESS, `inserted=1`, `updated=1`, `unchanged=1` |
| S3 | Incremental toàn dòng lỗi | fixture V3 | staging SUCCESS (`NO_VALID_RECORDS`), `rejected=4` |
| S4 | **Lỗi bước staging** | `source_file` trỏ tới file không tồn tại | 1 dòng **FAILED**, `error_message` rõ ràng |
| S5 | **Lỗi bước dbt** | dùng cách test hiện có: ràng buộc CHECK làm dbt lỗi | staging SUCCESS + dbt **FAILED** cùng `run_id`; chạy lại thì thành công |
| S6 | **Trigger tự chạy** | bật `test_every_15_min` trên database thật với `games.csv` | dòng mới có `trigger_name = test_every_15_min`, không ai bấm chạy, 0 thay đổi |

Mỗi kịch bản: chụp **Mage Runs** và kết quả truy vấn mục 2.4 làm bằng chứng cho báo cáo và video.

### 3.3. Lưu ý dữ liệu
Fixture V1/V2/V3 thêm game test vào DWH (lý do file `.pbix` từng ra 125.856 dòng), nên chỉ chạy chúng trên database test. S6 chạy `games.csv` trên database thật, kết quả 0 thay đổi, không làm bẩn dữ liệu.

---

## 4. Thứ tự làm và thời gian

| # | Việc | Ước lượng |
|---|---|---|
| 1 | Script `05_extend_etl_audit_log.sql` + gọi trong `bootstrap.py` | 20 phút |
| 2 | `pipeline_support/audit.py` + thay 5 chỗ ghi audit + truyền `run_id` / `started_at` / `trigger_name` | 1,5 giờ |
| 3 | Unit test + mở rộng `verify_mage_incremental.py` | 1 giờ |
| 4 | `triggers.yaml` (tháng + kiểm thử) + kiểm tra trên Mage UI | 30 phút |
| 5 | Chạy kịch bản S1–S6, chụp bằng chứng | 1 giờ (chủ yếu chờ chạy) |
| 6 | Cập nhật README (mục Lập lịch, Audit log), gửi danh sách cột cho bạn làm dashboard | 20 phút |

**Tổng:** khoảng 4,5–5 giờ. Làm trên nhánh **`Binh`**, chưa push cho tới khi bạn duyệt.

---

## 5. Câu hỏi còn mở (không chặn việc làm)
- Bạn làm dashboard có cần thêm cột nào ngoài mục 2.2 không? Nên hỏi trước khi làm bước 2.
- Lịch tháng chọn **07:00 sáng ngày 1** (giờ VN). Nếu nhóm muốn giờ khác (ví dụ 02:00), mình đổi cron.
