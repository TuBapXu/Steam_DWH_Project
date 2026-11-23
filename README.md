# Steam Games Data Warehouse & BI Semantic Model

Đồ án Data Warehouse trên tập dữ liệu **Steam Games**. Dự án xây dựng pipeline dữ liệu hoàn chỉnh từ file CSV tĩnh vào SQL Server thông qua Mage.ai, chuyển đổi và mô hình hóa Star Schema bằng dbt, và khởi tạo Semantic Model / DAX nền tảng trên Power BI:

| Giai đoạn | Công cụ | Trạng thái |
|---|---|---|
| **3.1 Data Ingestion (nạp vào Staging)** | Mage.ai + SQL Server | Chia chunk đọc tuần tự Parquet; mỗi chunk có nhánh Extract → Validate → Load chạy song song trên Mage. Full Load nạp staging trong giao dịch; Incremental Load cập nhật theo AppID và hash SHA-256; ghi nhận 8 dòng parser lỗi vào bảng rejected. |
| **3.2 Data Transformation** | dbt (dbt-sqlserver) | Làm sạch, chuẩn hóa và xây dựng các bảng DWH. Hệ thống gồm **9 dbt models**, **91 data tests** (100% PASS) và **32 unit tests** kiểm định toàn diện. |
| **3.3 Data Warehouse (Star Schema)** | SQL Server 2022 | Mô hình hình sao hoàn chỉnh gồm Fact Snapshot, 4 Dimension cốt lõi (`dim_date`, `dim_game`, `dim_platform`, `dim_publisher`), 1 Dimension OS và 1 Bridge Table Many-to-Many (`bridge_game_platform`). Ràng buộc toàn vẹn khóa ngoại (FK) và nonclustered index tối ưu hóa truy vấn. |
| **4.1 Semantic Model & BI Foundation** | Power BI Desktop | Kết nối DWH, thiết lập quan hệ 1-Nhiều (1:* Single filter), Date Hierarchy, phân nhóm dải tuổi/dải giá, cấu hình bảng cầu thể loại `dim_game_genres`, viết hệ thống DAX Measures nền tảng (KPIs, CCU, Doanh số ước tính Boxleiter) và xuất file template `Steam_Template.pbix` / `Steam_Template.pbit`. |
| **4.2 Advanced Dashboards & AI Copilot** | Power BI + Google Gemini API | Hoàn thiện **6 trang Dashboard Full HD 1080p** (Thị trường, Định giá, Nhà phát hành, Sentiment, Cây phân rã AI, Giám sát ETL) kết hợp ứng dụng **Steam Copilot Web App** (cổng 5000) và module **AI ETL Explainer** tự động sinh nhận định từ log DWH. |

## Kiến trúc tổng thể

```
games.csv ──► Mage.ai pipeline ──► SQL Server (steam_games_DWH)
                                     ├── dbo.stg_steam_games          (Staging chính thức)
                                     ├── dbo.stg_steam_games_rejected (8 bản ghi lỗi parser)
                                     ├── dbo.etl_steam_incremental_batch (Theo dõi batch)
                                     ├── dbo.etl_audit_log            (Nhật ký thực thi & metrics)
                                     └── dbo.dashboard_ai_insights    (Nhận định tự động từ AI)

dbo.stg_steam_games ──► dbt ──► dbt_staging.stg_steam_games_cleaned (table)
                                       │
                                       ├──► dwh.dim_* & dwh.bridge_*
                                       └──► dwh.fact_game_snapshot
                                                    │
                                                    ├───────────────────────────────┐
                                                    ▼                               ▼
                                       Power BI (6 Dashboards Full HD)    Steam Copilot Web App
                                       ├── Date Hierarchy & Star Schema   ├── Flask + Gemini 2.5 Flash
                                       ├── DAX Measures & Slicers         ├── GenAI Grounding Engine
                                       ├── AI Decomposition Tree          ├── Natural Language to SQL
                                       └── bi_dashboard/Steam_Template    └── bi_dashboard/steam_copilot.py
```

Docker Compose gồm `mage`, `sqlserver` và service `dbt` chạy theo yêu cầu.

## Cấu trúc thư mục

```
Steam_DWH_Project/
├── bi_dashboard/        # 6 Dashboards Power BI (.pbix, .pbit), Steam Copilot Web App (Flask + Gemini), AI ETL Explainer
├── data/                # Chứa games.csv (có .gitkeep, file CSV KHÔNG đẩy lên Git)
├── database_setup/      # Script DDL khởi tạo DB, Star Schema, bảng rejected, audit, bootstrap
├── dbt_transform/       # Profile, 9 models staging/marts, macro, 91 data tests
├── mage_pipeline/       # Dự án Mage.ai (8 blocks luồng động, exporter, callback)
│   ├── data_loaders/    # prepare_steam_chunks, extract_steam_chunk
│   ├── transformers/    # validate_steam_chunk: chuẩn hóa dữ liệu từng chunk
│   ├── data_exporters/  # load chunk, publish staging, report, dbt, đối soát DWH
│   ├── callbacks/       # Ghi trạng thái FAILED vào audit log
│   ├── pipelines/       # Định nghĩa pipeline steam_staging_pipeline
│   └── io_config.yaml   # Cấu hình kết nối SQL Server (đọc mật khẩu từ biến môi trường)
├── pipeline_support/    # Module dùng chung: chunking, validation, pyodbc array insert, đối soát
├── tests/               # 32 unit tests & kịch bản kiểm thử tích hợp (verify_mage_incremental)
├── docs/                # Tài liệu chi tiết các block Mage và đối soát end-to-end
├── .env.example         # Mẫu cấu hình biến môi trường
├── .env                 # Biến môi trường thật, chứa mật khẩu (KHÔNG đẩy lên Git)
├── .gitignore           # Loại trừ an toàn bí mật, CSV lớn, build artifacts
├── docker-compose.yml
└── Dockerfile
```

## Pipeline Mage: `steam_staging_pipeline`

```
prepare_steam_chunks
  → [extract_steam_chunk → validate_steam_chunk → load_steam_chunk] × số chunk
  → publish_steam_staging → report_steam_load → run_dbt_transform → check_dwh_results
```

| Block | Loại | Chức năng |
|---|---|---|
| `prepare_steam_chunks` | Dynamic data loader | Đọc tuần tự CSV ra Parquet từng chunk; lưu manifest và trả danh sách chunk cho Mage điều phối |
| `extract_steam_chunk` | Data loader | Trả DataFrame thô của một chunk và metadata định danh |
| `validate_steam_chunk` | Transformer | Làm sạch, chuẩn hóa kiểu dữ liệu, bắt lỗi và trả thống kê lỗi từng chunk |
| `load_steam_chunk` | Data exporter | Ghi chunk sạch vào bảng SQL làm việc riêng (`dbo._steam_full_<hash>`); trả biên nhận số dòng |
| `publish_steam_staging` | Data exporter | Chờ đủ mọi chunk, khử trùng AppID toàn file (giữ dòng cuối cùng) rồi công bố staging và dọn dẹp bảng tạm trong giao dịch |
| `report_steam_load` | Data exporter | Báo cáo số dòng thêm, cập nhật, giữ nguyên, dòng lỗi parser và quản lý cửa sổ batch LSET/CET |
| `run_dbt_transform` | Data exporter | Kích hoạt `dbt build` trong môi trường ảo riêng; thực thi 9 models và toàn bộ bộ test; ghi audit chi tiết |
| `check_dwh_results` | Data exporter | Đối soát tự động staging/cleaned/DWH, kiểm tra khóa ngoại, thuộc tính và measures; trả trạng thái `PIPELINE SUCCESS` |

Xem hướng dẫn chi tiết từng block: [Hướng dẫn tám block và các nhánh chunk](docs/MAGE_END_TO_END.md).

### Cơ chế Full Load và Incremental Load

- **Full Load:** Đọc toàn bộ CSV theo từng chunk. Staging chỉ được thay thế sau khi 100% chunk thành công và đã đối soát toàn vẹn.
- **Incremental Load:** Đọc toàn bộ CSV theo chunk để phát hiện game mới hoặc bản ghi có thay đổi. So khớp `AppID` và hàm băm `HASHBYTES('SHA2_256')` trên các thuộc tính nghiệp vụ đã ép kiểu SQL. Chỉ ghi nhận dữ liệu mới/khác biệt vào staging, sau đó cập nhật tiếp lên cleaned, dim_game và fact. Các game không xuất hiện trong file mới vẫn được bảo toàn nguyên vẹn.
- **Quản lý LSET/CET:** Theo dõi tuần tự theo batch (`batch_seq`), không lọc theo ngày phát hành game. Đặt `demo_lset` và `demo_cet` bằng `null`.

Nếu gián đoạn sau khi nạp staging, chạy lại toàn bộ pipeline với đúng nội dung CSV của batch đang dở để Mage tiếp tục dùng danh sách AppID đã lưu.

### Biến pipeline (Variables)

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `run_mode` | `full` hoặc `incremental` (mặc định: `full`) | Chọn chế độ nạp dữ liệu |
| `source_file` | `data/games.csv` | Đường dẫn file CSV nguồn trong project |
| `chunk_size` | `1000` | Số bản ghi mỗi chunk (từ 1 đến 10.000) |
| `max_workers` | `2` | Biến tương thích helper cũ; giới hạn song song thực tế của Mage là `concurrency_config.block_run_limit: 2` |
| `dbt_timeout_seconds` | `3600` | Thời gian chờ tối đa cho tiến trình transform của dbt |
| `demo_lset` | `null` | Không dùng để lọc ngày; quản lý tự động theo batch |
| `demo_cet` | `null` | Được tính toán tự động sau mỗi lượt incremental |
| `trigger_name` | `manual` | Tên trigger ghi vào audit log; các Schedule Trigger tự điền tên của mình |

### Lập lịch ETL (Schedule Trigger)

Trigger được khai báo dạng code trong `mage_pipeline/pipelines/steam_staging_pipeline/triggers.yaml`, Mage tự nạp khi khởi động. Giờ cron tính theo **UTC** (container chạy UTC, giờ Việt Nam = UTC+7).

| Trigger | Cron (UTC) | Giờ Việt Nam | Trạng thái | Mục đích |
|---|---|---|---|---|
| `monthly_incremental` | `0 0 1 * *` | 07:00 ngày 1 hằng tháng | `active` | Lịch chính: incremental theo AppID + row_hash |
| `test_every_15_min` | `*/15 * * * *` | Mỗi 15 phút | `inactive` | Bật tạm trong Mage UI (Triggers) để chứng minh trigger tự chạy, xong thì tắt |

Cả hai trigger đặt `skip_if_previous_running: true` (không chạy chồng lượt) và `timeout: 7200` giây. Trigger chạy lại an toàn: batch dở dang được tiếp tục với cùng cửa sổ LSET/CET.

### Ghi nhận trạng thái và lỗi (Audit & Rejection)
- Mỗi **bước** của một lượt chạy ghi đúng **một dòng** vào `dbo.etl_audit_log`; các dòng của cùng một lần chạy pipeline dùng chung `run_id`. Lần chạy lại một batch incremental bị lỗi là một `run_id` mới; dòng `staging` của nó có `"resumed": true` và cùng `batch_id` (trong `metrics_json`) với lần lỗi trước đó. Cột được thêm bằng `database_setup/05_extend_etl_audit_log.sql` (bootstrap tự chạy, không mất dữ liệu cũ).

| Cột | Ý nghĩa |
|---|---|
| `pipeline_name`, `run_date`, `status`, `records_processed`, `error_message` | Các cột gốc (`status` = `SUCCESS`/`FAILED`) |
| `run_id` | Mã lượt chạy (32 ký tự hex), dùng để gom các bước |
| `step` | `staging`, `dbt`, `check`; `chunk` (một chunk lỗi); `pipeline` (lỗi do callback ghi) |
| `trigger_name`, `run_mode` | Trigger đã chạy (`manual` nếu chạy tay) và `full`/`incremental` |
| `started_at`, `finished_at`, `duration_sec` | Thời điểm bắt đầu/kết thúc (UTC) và thời lượng của bước |
| `inserted`, `updated`, `unchanged`, `rejected` | Số bản ghi thêm mới / cập nhật / không đổi / bị loại ở bước staging |
| `dbt_tests` | Số dbt test đã chạy (0 nếu dbt được bỏ qua do `NO_VALID_RECORDS`) |
| `checks_failed` | Số kiểm tra đối soát DWH thất bại |
| `metrics_json` | Chi tiết bổ sung dạng JSON (số dòng đọc, chunk, cửa sổ LSET/CET, số dòng từng bảng DWH…) |

Truy vấn mẫu một dòng cho mỗi lượt chạy (dùng cho dashboard giám sát):

```sql
SELECT run_id, MAX(trigger_name) AS trigger_name, MAX(run_mode) AS run_mode,
       MIN(started_at) AS started_at, MAX(finished_at) AS finished_at,
       DATEDIFF(SECOND, MIN(started_at), MAX(finished_at)) AS duration_sec,
       -- Trạng thái cuối = trạng thái của dòng ghi sau cùng (lượt chạy lại thành công thì run là SUCCESS)
       (SELECT TOP 1 l.status FROM dbo.etl_audit_log l WHERE l.run_id = a.run_id ORDER BY l.log_id DESC) AS run_status,
       SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_steps,
       MAX(CASE WHEN step = 'staging' THEN inserted END) AS inserted,
       MAX(CASE WHEN step = 'staging' THEN updated END) AS updated,
       MAX(CASE WHEN step = 'staging' THEN rejected END) AS rejected,
       MAX(CASE WHEN step = 'dbt' THEN dbt_tests END) AS dbt_tests,
       MAX(CASE WHEN step = 'check' THEN checks_failed END) AS checks_failed
FROM dbo.etl_audit_log a
WHERE run_id IS NOT NULL
GROUP BY run_id
ORDER BY MIN(started_at) DESC;
```
- Các bản ghi thiếu AppID hoặc sai định dạng số trong file gốc được cách ly vào bảng `dbo.stg_steam_games_rejected` kèm lý do chi tiết và nội dung thô.

---

## Hướng dẫn cài đặt và chạy

### 1. Yêu cầu hệ thống
- Docker Desktop (cấp tối thiểu 4 GB RAM cho Docker; SQL Server cần ít nhất 2 GB).
- Power BI Desktop (để mở Semantic Model và dựng Dashboard).
- SQL Server Management Studio (SSMS) hoặc Azure Data Studio (tùy chọn).

### 2. Chuẩn bị dữ liệu
1. Tải [Steam Games Dataset trên Kaggle](https://www.kaggle.com/datasets/fronkongames/steam-games-dataset), lấy file `games.csv` đặt vào thư mục `data/games.csv`.
2. Kiểm tra tính toàn vẹn của file bằng PowerShell:
   ```powershell
   Get-FileHash data/games.csv -Algorithm SHA256
   ```
   Mã băm SHA-256 bản chuẩn đối chiếu: `343b59ffe6422f69eaf1d371779565679fc23fc76eee9de65e23121d21a49b00`.

> *Lưu ý:* Header của file gốc bị dính cột (`DiscountDLC count`). Bộ đọc CSV dùng chung đặt tên 40 cột tường minh để tránh lệch cột; quy tắc này được bảo toàn trong pipeline.

### 3. Cấu hình biến môi trường
Từ thư mục gốc project, sao chép file mẫu thành `.env`:
```powershell
Copy-Item .env.example .env
```
> **Lưu ý tiện ích:** File `.env.example` đã được nhóm điền sẵn toàn bộ cấu hình chuẩn cùng **Gemini API Key** hợp lệ (`AQ.Ab8RN6L_oYEtcnUgYcBlHLWChmcXu6QiusQAfUHxZ_nQwEMa7Q`). Người chấm chỉ cần sao chép sang `.env` là có thể chạy ngay toàn bộ hệ thống (Mage ETL, SQL Server và Steam Copilot AI) mà không cần cấu hình thêm:
```dotenv
MSSQL_PASSWORD=thanhtu185B#2005
GEMINI_API_KEY="AQ.Ab8RN6L_oYEtcnUgYcBlHLWChmcXu6QiusQAfUHxZ_nQwEMa7Q"
```

### 4. Khởi động hệ thống
```powershell
docker compose up -d --build
docker compose ps
```
Theo dõi khởi động SQL Server: `docker compose logs -f sqlserver`.

| Dịch vụ | Địa chỉ kết nối | Thông tin đăng nhập |
|---|---|---|
| **Mage UI** | http://localhost:6790 | Giao diện điều phối pipeline |
| **SQL Server (từ máy host / Power BI)** | `localhost,1435` | User: `sa`, Password: trong `.env` |
| **SQL Server (nội bộ Docker network)** | `sqlserver:1433` | Dùng bởi Mage và container dbt |

### 5. Khởi tạo Database tự động
Khi container Mage khởi động, script `database_setup/bootstrap.py` tự động:
1. Tạo database `steam_games_DWH`, schema `dwh`, `dbt_staging`.
2. Tạo bảng staging, watermark, audit log, rejected table và khung Star Schema DWH có ràng buộc khóa ngoại.
3. **Tự động dọn dẹp các bảng tạm buffer mồ côi (`dbo._steam_full_%`)** nếu có từ các phiên chạy trước.
4. Nâng cấp composite primary key cho Fact nếu dùng database từ phiên bản cũ.

Kiểm tra log: `docker compose logs mage` và tìm dòng `Steam database schema ready.`.

### 6. Chạy pipeline Ingestion & Transformation trên Mage
1. Mở trình duyệt vào http://localhost:6790, chọn pipeline `steam_staging_pipeline`.
2. Vào mục **Triggers** $\rightarrow$ Tạo trigger **Run once** với các biến:
   * `run_mode`: `full`
   * `source_file`: `data/games.csv`
   * `chunk_size`: `1000`
   * `demo_lset`: `null`
   * `demo_cet`: `null`
3. Bấm **Run now** để kích hoạt toàn bộ 8 block. Mage sẽ tạo động 126 nhánh `Extract` $\rightarrow$ `Validate` $\rightarrow$ `Load`.
4. Sau khi nạp staging thành công, block `run_dbt_transform` sẽ tự động build models và chạy 91 bài test dbt.
5. Chờ block cuối cùng `check_dwh_results` hiển thị log `PIPELINE SUCCESS`.

### 7. Kiểm thử thủ công và Chạy dbt riêng biệt (Khi cần)
dbt đã được đóng gói trong Docker, chạy trực tiếp từ máy host:
```powershell
# Kiểm tra kết nối dbt
docker compose run --rm --no-deps dbt debug

# Thực thi toàn bộ models và 91 data tests
docker compose run --rm --no-deps dbt build

# Chạy riêng bộ kiểm tra chất lượng dữ liệu
docker compose run --rm --no-deps dbt test

# Chạy bộ 32 unit tests python trong container Mage
docker compose exec -T -w /home/src mage python -m unittest discover -s tests -p "test_*.py"

# Kiểm thử tích hợp trên DB tạm: Full/Incremental V1/V2/V3, lỗi staging, lỗi dbt và các dòng audit
docker compose exec -T -w /home/src/mage_pipeline mage python /home/src/tests/verify_mage_incremental.py
```

### 8. Khởi chạy Trợ lý AI Steam Copilot & AI Explainer

Ứng dụng Web Copilot hỗ trợ người dùng phân tích nghiệp vụ hỏi đáp dữ liệu tự nhiên bằng Tiếng Việt / Tiếng Anh có trích dẫn dữ liệu nguồn:

```powershell
# 1. Khởi chạy Steam Copilot Web App (cổng 5000)
python bi_dashboard/steam_copilot.py
# Mở trình duyệt truy cập: http://localhost:5000

# 2. Chạy module tự động phân tích và giải thích log ETL & Data Quality
python bi_dashboard/ai_etl_explainer.py
```

---

## Đối soát kết quả dữ liệu

Sau khi lượt chạy Full Load và các kịch bản kiểm thử hoàn tất, số dòng trong toàn bộ database đạt trạng thái chuẩn xác như sau:

| Tên bảng / View | Số dòng thực tế | Vai trò trong hệ thống |
|---|---:|---|
| `dbo.stg_steam_games` | **125.856** | Bảng Staging chính thức sau khi khử trùng AppID toàn file |
| `dbo.stg_steam_games_rejected` | **8** | Bảng cách ly các bản ghi lỗi parser định dạng AppID |
| `dbt_staging.stg_steam_games_cleaned` | **125.856** | Bảng trung gian đã làm sạch, chuẩn hóa kiểu dữ liệu |
| `dwh.dim_game` | **125.856** | Chiều Game (chứa tên, độ tuổi, thể loại, ngôn ngữ) |
| `dwh.dim_publisher` | **62.635** | Chiều Nhà phát hành (gồm 62.634 publisher + 1 dummy Unknown) |
| `dwh.dim_date` | **10.748** | Chiều Thời gian (chuỗi ngày liên tục 1997–2025 + 1 dummy Unknown) |
| `dwh.dim_platform` | **8** | Chiều Nền tảng (8 tổ hợp Win/Mac/Linux cố định) |
| `dwh.dim_operating_system` | **3** | Chiều Hệ điều hành (1: Windows, 2: Mac, 3: Linux) |
| `dwh.bridge_game_platform` | **163.600** | Bảng cầu Many-to-Many giữa Game và Hệ điều hành |
| `dwh.fact_game_snapshot` | **125.856** | Bảng Fact trung tâm (Grain: 1 dòng = 1 game tại thời điểm nạp) |
| `dbo.etl_audit_log` | **33** | Bảng nhật ký audit toàn diện (ghi nhận từng bước staging, dbt, check, chunk) |
| `dbo.dashboard_ai_insights` | **4** | Bảng lưu nhận định phân tích tự động từ AI ETL Explainer |
| `dbo.vw_etl_monitoring` | **33** | View tổng hợp chỉ số hiệu năng ETL phục vụ Dashboard 6 |
| `dbo.vw_dashboard_ai_insights` | **4** | View cung cấp khối giải thích AI trực quan hóa trên Power BI |

Truy vấn kiểm tra nhanh trong SQL Server:
```sql
USE steam_games_DWH;

-- Kiểm tra số dòng bảng Fact và Staging
SELECT COUNT(*) AS total_fact FROM dwh.fact_game_snapshot;
SELECT COUNT(*) AS total_staging FROM dbo.stg_steam_games;

-- Kiểm tra tính toàn vẹn: Không được có AppID trùng
SELECT appid, COUNT(*) FROM dbo.stg_steam_games GROUP BY appid HAVING COUNT(*) > 1;

-- Xem nhật ký thực thi gần nhất
SELECT TOP 5 * FROM dbo.etl_audit_log ORDER BY log_id DESC;
```

---

## Giai đoạn BI: Semantic Model & Hệ thống 6 Power BI Dashboards

Thư mục `bi_dashboard/` lưu trữ cấu trúc Semantic Model nền tảng, template chuẩn, bộ 6 báo cáo Dashboard và mã nguồn trợ lý AI:
- `Steam_Template.pbix`: File làm việc Power BI đã kết nối sẵn vào DWH và thiết lập quan hệ Star Schema chuẩn Full HD (1920×1080).
- `Steam_Template.pbit`: File mẫu template (dung lượng < 1 MB) chứa toàn bộ Schema, M Query, quan hệ và DAX measures; thành viên khác mở lên sẽ tự refresh với database cục bộ.

### Kiến trúc Semantic Model trong Power BI:
1. **Quan hệ Star Schema:** Kết nối 1-Nhiều (`1:* Single filter`) từ các Dimension (`dim_game`, `dim_date`, `dim_platform`, `dim_publisher`) vào `fact_game_snapshot`.
2. **Phân cấp ngày (Date Hierarchy):** `Year` → `Quarter` → `Month` → `Full Date` phục vụ phân tích xu hướng và Drill-down.
3. **Bảng cầu thể loại (`dim_game_genres`):** Tách từ chuỗi gộp trong Power Query thành cấu trúc chuẩn để trực quan hóa Top 10 thể loại.
4. **Cột phân nhóm (Calculated Columns):**
   * `Age Bracket`: Phân nhóm dải độ tuổi (`All Ages (0+)`, `Pre-Teen (7-12)`, `Teen (13-16)`, `Mature (17+/18+)`).
   * `Price Tier`: Phân nhóm mức giá (`Free to Play`, `Under $10`, `$10 - $29.99`, `$30 - $59.99`, `$60+`).
5. **Bộ DAX Measures nền tảng (`_Measures`):**
   * **Core Volume:** `Total Games`, `Free Games`, `Paid Games`, `% Free Games`, `Total Publishers`, `AAA Games`, `Indie Games`.
   * **Engagement:** `Peak CCU`, `Avg Peak CCU`, `Avg Playtime (Hours)`, `Total Playtime (Hours)`.
   * **Pricing & Revenue:** `Avg Price`, `Avg Paid Price`, `Max Price`, `Avg Discount`, `Estimated Revenue` (Doanh số ước tính theo phương pháp Boxleiter chuẩn Steam).
   * **Reviews & Sentiment:** `Total Positive Reviews`, `Total Negative Reviews`, `Total Reviews`, `Positive Review Ratio` (%), `Avg Metacritic Score`, `Avg User Score`.

### Hệ thống 6 Power BI Dashboards (Full HD 1920×1080)
Dự án đã hoàn thiện 6 trang báo cáo chuyên sâu phục vụ đa góc nhìn phân tích từ vĩ mô thị trường đến vi mô tựa game và kỹ thuật vận hành:

1. **Dashboard 1 - Tổng quan Thị trường & Xu hướng Phát hành (Market Overview & Trends):**
   - Hàng KPI Cards vĩ mô (`Total Games`, `Free Ratio`, `Total Publishers`, `Avg Price`).
   - Biểu đồ đường xu hướng ra mắt game theo năm/tháng với tính toán tăng trưởng YoY.
   - Phân tích mùa vụ (Quý / Mùa / Kỳ nghỉ lễ Summer & Winter Sale) và mật độ game ra mắt mỗi ngày.
   - Cơ cấu Top 10 thể loại phổ biến và hệ thống Slicers lọc đa chiều.
2. **Dashboard 2 - Hiệu suất Thương mại & Chiến lược Giá (Commercial Performance & Pricing Strategy):**
   - Phân tích cơ cấu Free-to-Play vs Trả phí (Paid).
   - Ma trận phân tán (Scatter Plot) đo lường tương quan giữa Tỷ lệ Giảm giá (`discount`) vs `peak_ccu` và `user_score`.
   - Phân bổ thời lượng chơi trung bình (`avg_playtime_hours`) theo các dải độ tuổi (`required_age`).
3. **Dashboard 3 - Đánh giá Nhà phát hành & Nền tảng (Publishers & Platform Analysis):**
   - So sánh đối đầu giữa phân khúc AAA vs Indie (Doanh thu Boxleiter ước tính, số lượng tựa game, Điểm Metacritic chuyên gia).
   - Cơ cấu hỗ trợ hệ điều hành (Windows, macOS, Linux đơn lẻ và phối hợp).
   - Tích hợp trang **Drill-through** chi tiết xem sâu vào từng tựa game cụ thể.
4. **Dashboard 4 - Thấu cảm Người chơi & Phân tích Đánh giá (Player Sentiment & Engagement):**
   - Phân tích tương quan giữa điểm số chuyên môn (`Metacritic Score`) và đánh giá cộng đồng (`User Score`).
   - Tỷ trọng đánh giá Tích cực vs Tiêu cực và phân nhóm mức độ hài lòng của game thủ.
   - Tương quan giữa độ gắn kết (giờ chơi thực tế) với khối lượng đánh giá.
5. **Dashboard 5 - Phân tích Chi tiết & Cây Phân rã Doanh thu AI (Deep Dive & Revenue Decomposition Tree):**
   - Ứng dụng **AI Decomposition Tree** (Cây phân rã AI) bóc tách chỉ số Doanh thu ước tính tự động theo `Thể loại` → `Dải giá` → `Nhà phát hành`.
   - Bảng phân tích chi tiết hỗ trợ tìm kiếm và sắp xếp các tựa game ngoại lai (Outliers).
6. **Dashboard 6 - Giám sát Vận hành ETL & Chất lượng Dữ liệu (ETL Performance & Data Quality Monitoring):**
   - Dành riêng cho đội ngũ Data Engineer giám sát trực quan 33 lượt log từ `dbo.vw_etl_monitoring`.
   - Tỷ lệ thành công Pipeline (Success Rate), phân bổ thời gian thực thi của từng bước (Staging, dbt, Audit).
   - Trực quan hóa kết quả 91/91 dbt tests đạt chuẩn và khối hiển thị nhận định tự động từ AI (`dbo.vw_dashboard_ai_insights`).

### Ứng dụng Trợ lý AI Steam Copilot & Module AI ETL Explainer
- **Steam Copilot Web App (`bi_dashboard/steam_copilot.py`):**
  - Giao diện Web trợ lý ảo chạy trên cổng `http://localhost:5000`.
  - Tích hợp mô hình ngôn ngữ lớn **Google Gemini 2.5 Flash** (hỗ trợ OpenAI fallback).
  - Cơ chế **Grounding Engine**: Chuyển đổi ngôn ngữ tự nhiên (Tiếng Việt / Tiếng Anh) thành câu truy vấn SQL Server trực tiếp, ép AI chỉ trả lời dựa trên dữ liệu thật của DWH để loại bỏ hoàn toàn hiện tượng ảo giác (Hallucination). Tự động render biểu đồ Chart.js và bảng dữ liệu tương tác.
- **AI ETL Explainer (`bi_dashboard/ai_etl_explainer.py`):**
  - Tự động kích hoạt sau khi chạy pipeline để phân tích log `dbo.etl_audit_log` và kết quả kiểm định dbt.
  - Tự động diễn giải nguyên nhân lỗi, đánh giá độ ổn định và ghi nhận định vào `dbo.dashboard_ai_insights` để Power BI hiển thị.

---

## Bảo mật và Dữ liệu

- Tuyệt đối **không commit** `.env`, `data/games.csv`, `mage_data/` và các file tạm vào Git.
- File `.gitignore` đã được cấu hình chặt chẽ để bảo vệ credentials và loại trừ các build artifacts (`target/`, `logs/`, `output/`).
- `io_config.yaml` chỉ tham chiếu mật khẩu thông qua biến môi trường `{{ env_var('MSSQL_PASSWORD') }}`.

## Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `Login failed for user 'sa' (18456)` | Mage hoặc dbt nhận sai mật khẩu `.env` | Kiểm tra lại `.env`, chạy `docker compose down` rồi `docker compose up -d` (không dùng restart) |
| Lỗi "Cột ngày không được có khoảng trống" khi Mark as Date Table | Bảng `dim_date` có dòng `0001-01-01` tạo khoảng cách với năm 1997 | Không cần bấm "Đánh dấu là bảng ngày", sử dụng trực tiếp **Date Hierarchy** đã tạo để drill-down |
| Lỗi không tìm thấy bảng khi tạo cột DAX | Tên bảng trong Power BI có tiền tố (ví dụ `'dwh dim_game'`) | Viết trực tiếp tên cột trong ngoặc vuông `[required_age]` hoặc bao bọc dấu nháy đơn `'dwh dim_game'[required_age]` |
| Incremental load cập nhật 0 dòng | Dữ liệu trong CSV hoàn toàn khớp với staging hiện có | Bình thường; pipeline tự so hash để tránh cập nhật dư thừa |

---

## Lý do lựa chọn công nghệ (Technology Stack Rationale)

Hệ thống được thiết kế theo tư duy **Modern Data Stack (MDS)** với nguyên tắc tách biệt trách nhiệm (Separation of Concerns), bảo đảm tính tái lập, khả năng mở rộng và hiệu năng phân tích cao nhất:

| Công nghệ | Vai trò | Vì sao lựa chọn? (So sánh & Ưu thế vượt trội) |
|---|---|---|
| **Mage.ai** | Data Ingestion & Orchestration | **Thay thế Apache Airflow truyền thống:** Airflow quá cồng kềnh với nhiều services phụ thuộc (Webserver, Scheduler, PostgreSQL, Celery/Redis). Mage.ai chạy gọn nhẹ trong container đơn, lập trình pipeline theo phong cách Native Python trực quan, hỗ trợ chia dynamic blocks theo chunk Parquet cực mượt, tích hợp sẵn cơ chế kiểm tra dữ liệu và theo dõi luồng dữ liệu thời gian thực. |
| **dbt Core (dbt-sqlserver)** | Data Transformation & Quality Control | **Thay thế Stored Procedures / SSIS:** dbt áp dụng triết lý *Software Engineering for Data*: toàn bộ biến đổi được viết bằng SQL SELECT thuần túy, quản lý phiên bản qua Git, sử dụng Jinja macros để tự động hóa mã lặp lại. dbt tích hợp sẵn kiểm thử chất lượng tự động (**91 data tests** PASS 100%) và tự động sinh tài liệu dòng dữ liệu (Data Lineage / `dbt docs`). |
| **Microsoft SQL Server 2022** | Staging & Enterprise Data Warehouse | **Hệ quản trị CSDL chuẩn doanh nghiệp:** Đóng vai trò kép (Staging Database + Star Schema DWH). Khác với NoSQL, SQL Server cung cấp tính toàn vẹn giao dịch ACID tuyệt đối, kiểm soát chặt chẽ ràng buộc khóa ngoại (Foreign Keys) và hỗ trợ Nonclustered Indexing tối ưu cho các truy vấn tổng hợp BI. Ngoài ra, SQL Server tương thích tự nhiên 100% với Power BI. |
| **Microsoft Power BI Desktop** | Semantic Modeling & Visual Analytics | **Nền tảng Business Intelligence hàng đầu:** Sở hữu bộ máy in-memory dạng cột **VertiPaq** siêu nhanh, hỗ trợ mô hình hóa quan hệ Star Schema 1-Nhiều chuẩn mực, hệ thống hàm **DAX** mạnh mẽ để tính toán chỉ số phức tạp (Boxleiter Revenue, CCU tương quan, Time Intelligence), cùng khả năng tương tác chiều sâu (Drill-through, AI Decomposition Tree). |
| **Docker & Docker Compose** | Infrastructure as Code & Containerization | **Chuẩn hóa môi trường triển khai:** Đóng gói độc lập toàn bộ các dịch vụ (Mage, SQL Server, dbt) vào các container, loại bỏ hoàn toàn lỗi xung đột môi trường (*"chạy được trên máy tôi nhưng lỗi trên máy bạn"*), thiết lập mạng nội bộ an toàn và giúp khởi chạy toàn bộ hạ tầng chỉ bằng duy nhất một câu lệnh `docker compose up -d`. |
| **Generative AI (Google Gemini 2.5 Flash)** | AI Copilot & Automated Insight Generation | **Tự động hóa thông minh (Augmented Analytics):** Kết hợp mô hình ngôn ngữ lớn (LLM) với cơ chế **Grounding Engine** trực tiếp từ SQL Server. Giải quyết bài toán "ảo giác" (Hallucination) bằng cách ép AI chỉ diễn giải dựa trên số liệu thực tế của DWH và log ETL; hỗ trợ người dùng cuối hỏi đáp kinh doanh bằng ngôn ngữ tự nhiên thông qua giao diện Web Copilot. |

## Tác giả

1. **Phạm Lê Thanh Tú** - `23120388` - `HCMUS`
2. **Kiều Đỗ Song Tinh** - `23120373` - `HCMUS`
3. **Nguyễn Ngọc Bình** - `23120218` - `HCMUS`
