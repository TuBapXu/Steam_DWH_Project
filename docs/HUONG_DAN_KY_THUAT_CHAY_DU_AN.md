# HƯỚNG DẪN KỸ THUẬT VẬN HÀNH TOÀN DIỆN HỆ THỐNG
# STEAM GAMES DATA WAREHOUSE & BUSINESS INTELLIGENCE PLATFORM
**Môn học:** Hệ thống thông tin phục vụ trí tuệ kinh doanh (23_1) — Nhóm 9  
**Ngày cập nhật:** 23/11/2026 — Phiên bản: 2.0 (Hệ thống Pipeline 8 Block, Star Schema mở rộng, 6 Dashboards & AI Copilot)

---

## 1. TỔNG QUAN HỆ THỐNG & KIẾN TRÚC KỸ THUẬT

Dự án triển khai một nền tảng dữ liệu hiện đại (**Modern Data Stack - ELT**) hoàn chỉnh, tự động hóa từ thu thập dữ liệu thô đến trực quan hóa và trí tuệ nhân tạo:

```
[ games.csv (Kaggle ~401MB) ]
             │
             ▼
[ Mage.ai Orchestrator (Port 6790) ]
   ├── 1. prepare_steam_chunks (Chia 126 chunk Parquet, 1.000 dòng/chunk)
   ├── 2. extract_steam_chunk  (Đọc song song từng chunk)
   ├── 3. validate_steam_chunk (Chuẩn hóa, bắt lỗi, tách bản ghi rác)
   ├── 4. load_steam_chunk     (Ghi bảng đệm buffer SQL _steam_full_<hash>)
   ├── 5. publish_steam_staging(Khử trùng AppID, commit vào Staging qua 1 giao dịch)
   ├── 6. report_steam_load    (Báo cáo số dòng, quản lý mốc batch LSET/CET)
   ├── 7. run_dbt_transform    (Kích hoạt dbt build thực thi 9 models)
   └── 8. check_dwh_results    (Đối soát 17 phép kiểm định DWH)
             │
             ▼
[ Microsoft SQL Server 2022 (Port 1435) ]
   ├── Schema dbo:
   │    ├── stg_steam_games          (125.856 dòng dữ liệu sạch)
   │    ├── stg_steam_games_rejected (8 bản ghi lỗi bị cô lập)
   │    ├── etl_audit_log            (33 dòng nhật ký thực thi chi tiết)
   │    └── vw_etl_monitoring        (View cấp dữ liệu cho Dashboard 5)
   ├── Schema dbt_staging:
   │    └── stg_steam_games_cleaned  (125.856 dòng đã chuẩn hóa nghiệp vụ)
   └── Schema dwh (Star Schema mở rộng):
        ├── dim_game                 (125.856 dòng sản phẩm)
        ├── dim_date                 (10.748 dòng lịch + khóa 0 Unknown)
        ├── dim_publisher            (62.635 nhà phát hành, 1.015 AAA / 61.620 Indie)
        ├── dim_platform             (8 tổ hợp hệ điều hành)
        ├── dim_operating_system     (3 dòng: Windows, Mac, Linux)
        ├── bridge_game_platform     (163.600 dòng ánh xạ N-N game & OS)
        └── fact_game_snapshot       (125.856 dòng Fact định kỳ, Composite PK)
             │
             ├─────────────────────────────────────────┐
             ▼                                         ▼
[ Microsoft Power BI Desktop ]             [ Steam Copilot AI Web App ]
  (Steam_Template.pbix - 6 Dashboards)       (Port 5000 - Python HTTP Server)
  ├── 1. Overview & Mùa vụ phát hành        ├── Module 1: Giám sát ETL Observability
  ├── 2. Hiệu suất & Chiến lược định giá    │   (Throughput, Duration SLA, Error Cards)
  ├── 3. Nhà phát hành & Nền tảng           └── Module 2: Chatbox đàm thoại Gemini AI
  ├── 4. Chi tiết game (Drill-through)          (Grounding Engine kết nối DWH thời gian thực)
  ├── 5. Giám sát đường ống ETL Observability
  └── 6. Cây phân rã AI (Decomposition Tree)
```

---

## 2. YÊU CẦU HỆ THỐNG & TIỀN ĐỀ CÀI ĐẶT

### 2.1. Phần cứng khuyến nghị
* **CPU:** 4 cores trở lên.
* **RAM:** Tối thiểu 8 GB RAM (cấp tối thiểu 4 GB cho Docker Desktop; SQL Server yêu cầu ít nhất 2 GB).
* **Ổ cứng trống:** Tối thiểu 10 GB SSD.

### 2.2. Phần mềm cần chuẩn bị trên máy Host
1. **Docker Desktop:** Phiên bản mới nhất (bật tính năng WSL 2 backend trên Windows).
2. **Python 3.10+:** Để chạy ứng dụng AI Copilot và chạy các bài kiểm thử unit tests cục bộ.
3. **Microsoft Power BI Desktop:** Để mở Semantic Model và tương tác trên 6 trang Dashboard.
4. **SQL Server Management Studio (SSMS)** hoặc **Azure Data Studio:** (Tùy chọn) Để kết nối truy vấn cơ sở dữ liệu.
5. **Git / PowerShell:** Để thực thi các câu lệnh dòng lệnh.

---

## 3. CẤU HÌNH BIẾN MÔI TRƯỜNG & CHUẨN BỊ DỮ LIỆU

### Bước 3.1: Cấu hình biến môi trường `.env`
Từ thư mục gốc của đồ án (`Steam_DWH_Project`), sao chép tệp mẫu `.env.example` thành `.env`:
```powershell
Copy-Item .env.example .env
```
Mở tệp `.env` bằng trình soạn thảo bất kỳ và điền các thông tin:
```dotenv
# Mật khẩu quản trị sa của SQL Server (Khuyến cáo: Chứa chữ hoa, chữ thường, số, tránh ký tự #)
MSSQL_PASSWORD=YourStrongPasswordHere

# Cổng truy cập Mage UI từ máy Host (Mặc định: 6790)
STEAM_MAGE_PORT=6790

# API Key cho Trợ lý ảo AI Copilot (Google Gemini hoặc OpenAI)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=
```

### Bước 3.2: Chuẩn bị tệp dữ liệu nguồn `games.csv`
1. Đặt tệp `games.csv` tải từ Kaggle vào thư mục `data/games.csv`.
2. Kiểm tra mã băm SHA-256 để đảm bảo tính toàn vẹn (tránh file bị hỏng khi tải):
```powershell
Get-FileHash data/games.csv -Algorithm SHA256
```
*Mã băm chuẩn đối chiếu:* `343b59ffe6422f69eaf1d371779565679fc23fc76eee9de65e23121d21a49b00`

> **Lưu ý kỹ thuật:** Tệp CSV gốc có tiêu đề bị dính cột (`DiscountDLC count`). Pipeline của nhóm đã khai báo danh sách 40 tên cột tường minh (`pipeline_support/full_load.py`) nên hệ thống tự động bóc tách chuẩn xác 40 cột mà không bị xô lệch dữ liệu.

---

## 4. KHỞI ĐỘNG HỆ THỐNG CONTAINER DOCKER

Mở PowerShell tại thư mục gốc của đồ án và thực thi:

```powershell
# 1. Khởi động các container ở chế độ chạy ngầm
docker compose up -d --build

# 2. Kiểm tra trạng thái các container đang hoạt động
docker compose ps
```

### Kiểm tra quá trình khởi tạo tự động (Bootstrap):
Khi container `mage` khởi động, script `database_setup/bootstrap.py` sẽ tự động kích hoạt để:
1. Tạo database `steam_games_DWH` nếu chưa có.
2. Tạo các schema: `dbo`, `dwh`, `dbt_staging`.
3. Tạo các bảng staging, watermark, audit log mở rộng, bảng rejected và khung Star Schema DWH.
4. Tự động dọn dẹp các bảng tạm buffer mồ côi (`dbo._steam_full_%`) từ các lần chạy trước.

Để kiểm tra xem database đã sẵn sàng chưa, gõ lệnh:
```powershell
docker compose logs mage | Select-String "Steam database schema ready."
```
Khi thấy dòng thông báo trên xuất hiện, toàn bộ hệ thống cơ sở dữ liệu đã sẵn sàng!

### Bảng ánh xạ cổng dịch vụ:
| Dịch vụ | Địa chỉ URL / Cổng từ máy Host | Tài khoản / Mật khẩu | Chức năng |
|---|---|---|---|
| **Mage UI** | `http://localhost:6790` | Không cần đăng nhập | Giao diện điều phối và giám sát Pipeline ETL |
| **SQL Server** | `localhost,1435` | User: `sa`<br/>Password: lấy từ `.env` | Kho dữ liệu và vùng Staging |
| **Steam Copilot AI** | `http://localhost:5000` | Không cần đăng nhập | Trợ lý ảo AI Chatbox & Giám sát ETL trực quan |

---

## 5. VẬN HÀNH PIPELINE TRÊN MAGE.AI

### Bước 5.1: Truy cập và kiểm tra Pipeline
1. Mở trình duyệt web, truy cập địa chỉ: `http://localhost:6790`.
2. Trong danh sách pipelines, nhấp chọn **`steam_staging_pipeline`**.
3. Vào mục **Pipeline settings / Variables** để kiểm tra các tham số mặc định:
   * `run_mode`: `full` (nạp toàn bộ) hoặc `incremental` (nạp tăng dần).
   * `source_file`: `data/games.csv`.
   * `chunk_size`: `1000` (kích thước mỗi chunk để kiểm soát RAM).
   * `demo_lset` & `demo_cet`: `null` (hệ thống mới quản lý batch theo mã băm SHA-256, không lọc ngày).
   * `dbt_timeout_seconds`: `3600`.

### Bước 5.2: Chạy Pipeline Full Load (Khởi tạo toàn bộ DWH)
1. Trong giao diện pipeline, vào tab **Triggers**.
2. Nhấp chọn trigger chạy thủ công hoặc bấm **Run pipeline now** (với biến `run_mode: full`).
3. **Theo dõi luồng thực thi:**
   * Block 1: `prepare_steam_chunks` đọc CSV tuần tự và sinh 126 chunk Parquet.
   * Block 2 $\rightarrow$ 4: Mage tự động khởi tạo 126 nhánh động chạy song song để Extract, Validate và nạp vào bảng đệm.
   * Block 5: `publish_steam_staging` khử trùng `AppID` và công bố vào `dbo.stg_steam_games` trong 1 giao dịch an toàn.
   * Block 6: `report_steam_load` ghi nhận thống kê vào `dbo.etl_audit_log`.
   * Block 7: `run_dbt_transform` tự động gọi `dbt build` chạy toàn bộ 9 models và 91 tests.
   * Block 8: `check_dwh_results` thực hiện 17 phép đối soát DWH và in thông báo `PIPELINE SUCCESS`.

### Bước 5.3: Chạy Pipeline Incremental Load (Nạp tăng dần theo batch)
1. Khi có đợt dữ liệu mới hoặc chạy mô phỏng định kỳ, đặt biến `run_mode: incremental`.
2. Pipeline sẽ tính toán hàm băm `row_hash` (SHA-256) trên các cột nghiệp vụ của từng `AppID`.
3. Chỉ những bản ghi mới hoặc có thay đổi mới được MERGE vào Staging và DWH; các game cũ giữ nguyên vẹn.
4. Thời gian chạy Incremental chỉ mất **3 – 25 giây** (tiết kiệm hơn 98% thời gian so với Full Load).

### Bước 5.4: Lập lịch tự động (Schedule Triggers)
Hệ thống đã tích hợp sẵn 2 cron trigger trong `triggers.yaml`:
* **`monthly_incremental`** (Cron: `0 0 1 * *` UTC = 07:00 ngày 1 hàng tháng): Lịch vận hành chính thức, tự động nạp gia tăng.
* **`test_every_15_min`** (Cron: `*/15 * * * *`): Trigger kiểm thử, bật tạm trên Mage UI để demo tính năng tự chạy định kỳ cho giảng viên xem.

---

## 6. KIỂM THỬ CHẤT LƯỢNG & ĐỐI SOÁT DỮ LIỆU

### Bước 6.1: Chạy toàn bộ 91 bài kiểm thử chất lượng dbt
Để kiểm tra tính toàn vẹn khóa chính, khóa ngoại và miền giá trị trên toàn kho dữ liệu:
```powershell
docker compose run --rm --no-deps dbt test
```
*Kết quả mong đợi:* **`PASS=91 WARN=0 ERROR=0 SKIP=0 TOTAL=91`** (Đạt 100%).

### Bước 6.2: Chạy 32 bài kiểm thử logic Python (Unit Tests)
Tại máy host (hoặc trong container), chạy lệnh unittest:
```powershell
python -m unittest discover tests
```
*Kết quả mong đợi:* **`Ran 32 tests in ...s — OK`**.

### Bước 6.3: Kiểm tra dữ liệu trong SQL Server bằng truy vấn
Mở SSMS kết nối vào `localhost,1435` và chạy script đối soát nhanh:
```sql
USE steam_games_DWH;
GO

-- 1. Kiểm tra số lượng bản ghi các bảng cốt lõi (Chuẩn: 125.856 dòng)
SELECT 'stg_steam_games' AS table_name, COUNT(*) AS total_rows FROM dbo.stg_steam_games
UNION ALL
SELECT 'fact_game_snapshot', COUNT(*) FROM dwh.fact_game_snapshot
UNION ALL
SELECT 'dim_game', COUNT(*) FROM dwh.dim_game
UNION ALL
SELECT 'bridge_game_platform', COUNT(*) FROM dwh.bridge_game_platform; -- Chuẩn: 163.600 dòng

-- 2. Kiểm tra các bản ghi lỗi bị cô lập (Chuẩn: 8 bản ghi)
SELECT reason_code, COUNT(*) AS count_rejected 
FROM dbo.stg_steam_games_rejected 
GROUP BY reason_code;

-- 3. Xem lịch sử thực thi Pipeline trong View Giám sát
SELECT TOP 10 run_id, step, status, records_processed, duration_sec, started_at 
FROM dbo.vw_etl_monitoring 
ORDER BY log_id DESC;
```

---

## 7. KHỞI CHẠY HỆ THỐNG BI DASHBOARD (POWER BI)

### Bước 7.1: Mở tệp báo cáo Power BI
1. Mở phần mềm **Microsoft Power BI Desktop**.
2. Mở tệp: `bi_dashboard/Steam_Template.pbix`.

### Bước 7.2: Cấu hình kết nối nguồn dữ liệu (nếu cần đổi cổng hoặc mật khẩu)
1. Trên thanh công cụ Power BI, chọn **Transform data** $\rightarrow$ **Data source settings**.
2. Chọn kết nối SQL Server và bấm **Change Source...**:
   * **Server:** `localhost,1435`
   * **Database:** `steam_games_DWH`
   * **Data Connectivity mode:** `Import`
3. Bấm **Edit Permissions...** $\rightarrow$ Chọn mục **Database** $\rightarrow$ Nhập User: `sa`, Password: mật khẩu trong file `.env`.
4. Bấm **Close & Apply** và nhấp nút **Refresh** để cập nhật toàn bộ 125.856 tựa game vào báo cáo.

### Bước 7.3: Khám phá 6 trang Dashboard chuyên sâu
* **Trang 1 — Overview & Mùa vụ phát hành:** Trả lời *"Nên ra mắt game khi nào?"*, phân tích chu kỳ YoY, tháng vắng nhất (Th01, Th06) và tháng đông đối thủ nhất (Th10).
* **Trang 2 — Hiệu suất thương mại & Chiến lược định giá:** Phân tích tương quan mức giảm giá vs Peak CCU, tỷ trọng Free-to-Play vs Paid, và thời lượng chơi theo dải độ tuổi.
* **Trang 3 — Nhà phát hành & Nền tảng:** So sánh nghịch lý doanh thu Indie (51,7%) vs AAA (48,3%), cơ cấu hệ điều hành Windows (79,1% độc tôn).
* **Trang 4 — Chi tiết game (Drill-through):** Bấm chuột phải vào bất kỳ Nhà phát hành nào ở Trang 3 (ví dụ Electronic Arts) $\rightarrow$ Drill-through sang Trang 4 để xem danh mục 134 game chi tiết và Ma trận BCG.
* **Trang 5 — Giám sát đường ống ETL (Observability):** Giám sát tình trạng sức khỏe pipeline qua 11 lượt chạy mẫu, SLA thời gian chạy, số bản ghi rejected và chẩn đoán sự cố AI.
* **Trang 6 — Trợ lý AI Copilot & Cây phân rã doanh thu:** Phân rã luồng tiền >38 tỷ USD qua visual AI Decomposition Tree; bấm nút *"MỞ AI CHATBOX"* để mở giao diện hỏi đáp AI.

---

## 8. KHỞI CHẠY TRỢ LÝ AI COPILOT WEB APP (PORT 5000)

Ứng dụng Steam Copilot được phát triển bằng Python, cung cấp giao diện web trực quan kết hợp giữa Giám sát đường ống ETL và Chatbox hỏi đáp thời gian thực với mô hình Gemini AI.

### Bước 8.1: Khởi động dịch vụ
Mở một cửa sổ PowerShell mới tại thư mục gốc và chạy:
```powershell
python bi_dashboard/steam_copilot.py
```
*Màn hình hiển thị:*
```
Steam DWH AI Copilot Server running on http://localhost:5000
Database connected: localhost,1435 (steam_games_DWH)
Gemini AI Engine: ONLINE (Grounding Enabled)
```

### Bước 8.2: Truy cập và sử dụng trên trình duyệt
1. Mở trình duyệt web, truy cập: **`http://localhost:5000`**.
2. **Giao diện Giám sát ETL (Observability Hub):** Xem biểu đồ cột Throughput nạp dữ liệu, biểu đồ đường Duration SLA, tỷ lệ thành công (81.82%) và các thẻ tóm tắt chất lượng dữ liệu.
3. **Giao diện Chatbox AI:** Nhập các câu hỏi đàm thoại tự nhiên, ví dụ:
   * *"Tôi là studio Indie thì nên phát hành game vào tháng nào để ít bị cạnh tranh?"*
   * *"Nhà phát hành nào đang có doanh thu cao nhất trên sàn Steam?"*
   * *"Doanh thu ước tính của các tựa game thuộc thể loại Action là bao nhiêu?"*
   * *"Tại sao đợt nạp fail_005 lại thất bại và cách xử lý thế nào?"*
4. AI Copilot sẽ tự động trích xuất ngữ cảnh từ DWH và trả về câu trả lời sắc bén, chính xác theo đúng số liệu thực tế.

---

## 9. HƯỚNG DẪN XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

| Tình huống sự cố | Nguyên nhân khả dĩ | Giải pháp khắc phục |
|---|---|---|
| **Lỗi `port is already allocated` khi chạy docker compose up** | Cổng 1435 hoặc 6790 đang bị một ứng dụng khác chiếm dụng trên máy host. | Kiểm tra tiến trình bằng `netstat -ano \| findstr :1435`. Hoặc đổi cổng `1435:1433` thành `1436:1433` trong `docker-compose.yml` và đổi cổng Mage qua biến `STEAM_MAGE_PORT=6791` trong `.env`. |
| **Mage báo lỗi kết nối SQL Server (Login failed for user 'sa')** | Mật khẩu trong `.env` không trùng khớp với mật khẩu container SQL Server đang chạy. | Kiểm tra file `.env`. Nếu trước đó đã chạy container với mật khẩu cũ, cần gỡ bỏ volume cũ bằng: `docker compose down -v` rồi khởi động lại bằng `docker compose up -d --build`. |
| **Pipeline Full Load bị treo hoặc báo OOM (Out of Memory)** | Bộ nhớ RAM cấp cho Docker Desktop bị thiếu khi xử lý file lớn. | Vào Docker Desktop $\rightarrow$ Settings $\rightarrow$ Resources $\rightarrow$ Nâng mức RAM lên tối thiểu **4 GB**. Đảm bảo tham số `chunk_size` trong Mage đặt là `1000`. |
| **Chatbox AI báo lỗi API Key hoặc phản hồi chậm** | Chưa điền `GEMINI_API_KEY` trong `.env` hoặc kết nối mạng bị gián đoạn. | Ứng dụng `steam_copilot.py` được thiết kế có **Grounding Fallback Engine**: Dù không có API Key, hệ thống vẫn tự động truy vấn trực tiếp bảng `dbo.dashboard_ai_insights` trong DWH để phản hồi chính xác 4 chủ đề phân tích cốt lõi mà không làm gián đoạn trải nghiệm người dùng. |
| **Lỗi khóa chính trùng khi chạy lại dbt run** | Sử dụng database cũ từ các phiên bản sơ đồ trước. | Chạy script nâng cấp khóa phức hợp Fact: `database_setup/03_migrate_fact_composite_key.sql` trên SSMS, sau đó thực hiện lại lệnh `dbt build`. |

---

## 10. DANH MỤC TỆP TIN VÀ TÀI LIỆU QUAN TRỌNG

* **Mã nguồn Pipeline Mage:** `mage_pipeline/pipelines/steam_staging_pipeline/`
* **Module hỗ trợ Dynamic Chunking & Hash:** `pipeline_support/dynamic_chunks.py`, `pipeline_support/sql_full_load.py`
* **Dự án dbt & Mô hình Star Schema:** `dbt_transform/models/` (9 models), `dbt_transform/tests/` (5 singular tests)
* **Script khởi tạo Database:** `database_setup/` (từ `01_...` đến `06_...` và `bootstrap.py`)
* **Tệp Báo cáo Power BI:** `bi_dashboard/Steam_Template.pbix`
* **Ứng dụng Trợ lý AI Copilot:** `bi_dashboard/steam_copilot.py`
* **Tài liệu Kế hoạch sửa báo cáo & Phân công:** `docs/report/KE_HOACH_SUA_BAO_CAO_VA_PHAN_CONG_NHOM_9.pdf`
* **Tài liệu Hướng dẫn kỹ thuật (bản PDF):** `docs/HUONG_DAN_KY_THUAT_CHAY_DU_AN.pdf`

---
*Tài liệu được xây dựng và chuẩn hóa bởi Nhóm 9 — Môn học Hệ thống thông tin phục vụ trí tuệ kinh doanh (23_1).*
