# Steam Games Data Warehouse

Đồ án Data Warehouse trên tập dữ liệu **Steam Games**. Dự án xây dựng pipeline ETL từ file CSV tĩnh vào SQL Server, gồm 3 giai đoạn:

| Giai đoạn | Công cụ | Trạng thái |
|---|---|---|
| 3.1 Data Ingestion (nạp vào Staging) | Mage.ai + SQL Server | Pipeline hỗ trợ Full Load và Incremental Load; Incremental đã chạy theo batch, Full Load cần xác nhận hoàn tất trên máy 8 GB RAM |
| 3.2 Data Transformation | dbt | Đã triển khai các model làm sạch, chuẩn hóa, marts và tests; các model incremental ở marts vừa được điều chỉnh, cần chạy lại để xác nhận |
| 3.3 Data Warehouse (Star Schema) | SQL Server | Có script DDL tạo Fact và 4 Dimension (`database_setup/02_create_star_schema_dwh.sql`) |

## Kiến trúc

```
games.csv ──► Mage.ai pipeline ──► SQL Server (steam_games_DWH)
                                     ├── dbo.stg_steam_games   (Staging, nguồn của dbt)
                                     ├── dbo.etl_watermark     (điều khiển incremental)
                                     └── dbo.etl_audit_log     (nhật ký thực thi)

dbo.stg_steam_games ──► dbt ──► dbt_staging.stg_steam_games_cleaned
                                       │
                                       └──► dbt_staging.stg_steam_game_classifications
                                       │
                                       └──► dwh.dim_* ──► dwh.fact_game_snapshot
```

Docker Compose gồm `mage`, `sqlserver` và service `dbt` chạy theo yêu cầu.

Các bước cấu hình, khởi tạo database và chạy pipeline/dbt được hướng dẫn trong mục [Hướng dẫn cài đặt và chạy](#hướng-dẫn-cài-đặt-và-chạy) bên dưới.

## Cấu trúc thư mục

```
Steam_DWH_Project/
├── bi_dashboard/        # (Dự kiến) dashboard BI
├── data/                # Chứa games.csv (KHÔNG đẩy lên Git)
├── database_setup/      # Script SQL khởi tạo database, bảng staging, watermark, audit
├── dbt_transform/       # Profile, models staging/marts, macro, tests và script kiểm thử dbt
├── mage_pipeline/       # Dự án Mage.ai
│   ├── data_loaders/    # extract_steam_games: đọc CSV, chia batch Full/Incremental
│   ├── transformers/    # validate_clean: kiểm tra cấu trúc, chất lượng, làm sạch cơ bản
│   ├── data_exporters/  # load_to_staging, update_watermark_audit
│   ├── callbacks/       # Ghi trạng thái FAILED vào audit log
│   ├── pipelines/       # Định nghĩa pipeline steam_staging_pipeline
│   ├── io_config.yaml   # Cấu hình kết nối SQL Server (đọc mật khẩu từ biến môi trường)
│   └── metadata.yaml
├── .env.example         # Mẫu cấu hình; sao chép thành .env rồi tự điền mật khẩu
├── .env                 # Biến môi trường, chứa mật khẩu (KHÔNG đẩy lên Git)
├── .gitignore
├── docker-compose.yml
└── Dockerfile
```

## Pipeline Mage: `steam_staging_pipeline`

```
extract_steam_games → validate_clean → load_to_staging → update_watermark_audit
```

| Block | Loại | Chức năng |
|---|---|---|
| `extract_steam_games` | Data loader | Đọc `games.csv`, ép kiểu ngày phát hành, lọc batch theo chế độ chạy |
| `validate_clean` | Transformer | Kiểm tra cột bắt buộc, ép kiểu, loại AppID lỗi/trùng, thêm cột `_loaded_at`, `_run_mode`, đếm dòng ngày lỗi |
| `load_to_staging` | Data exporter | Nạp vào `dbo.stg_steam_games` (Full: TRUNCATE rồi nạp; Incremental: xóa đúng AppID của batch rồi nạp, chạy lại không bị trùng) |
| `update_watermark_audit` | Data exporter | Ghi `etl_audit_log` (trạng thái, số bản ghi) và dời watermark |

### Cơ chế Full Load và Incremental Load

Dataset là file tĩnh, không có cột `updated_at`, nên dùng **`Release date`** làm cột watermark và **mô phỏng batch** bằng cửa sổ thời gian 2 năm:

- **Full Load**: nạp toàn bộ file, bỏ qua watermark, không dời watermark.
- **Incremental Load**: lấy các dòng thỏa `lset < Release date <= cet`, trong đó `cet = lset + 2 năm`. Sau khi nạp thành công, watermark được dời thêm 2 năm.
- **Demo**: truyền thủ công `demo_lset` và `demo_cet` để cắt một khoảng bất kỳ, không dời watermark.

File CSV không cần sắp xếp vì việc lọc dựa trên điều kiện, không phụ thuộc thứ tự dòng. Watermark dời theo cửa sổ cố định thay vì lấy `max(Release date)`.

### Biến pipeline (Variables)

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `run_mode` | `full` hoặc `incremental` (mặc định `incremental`) | Chọn chế độ nạp |
| `demo_lset` | ví dụ `2018-01-01` | (Tùy chọn) mốc bắt đầu thủ công |
| `demo_cet` | ví dụ `2020-01-01` | (Tùy chọn) mốc kết thúc thủ công |

### Ghi nhận trạng thái và lỗi

Mỗi lần chạy ghi một dòng vào `dbo.etl_audit_log` gồm `pipeline_name`, `run_date`, `status` (`SUCCESS` hoặc `FAILED`), `records_processed`, `error_message`.

## Hướng dẫn cài đặt và chạy

### 1. Yêu cầu

- Docker Desktop (khuyến nghị cấp tối thiểu 4 GB RAM cho Docker; SQL Server cần ít nhất 2 GB)
- SQL Server Management Studio (SSMS) để chạy script khởi tạo

### 2. Chuẩn bị dữ liệu

Tải [Steam Games Dataset trên Kaggle](https://www.kaggle.com/datasets/fronkongames/steam-games-dataset), lấy file `games.csv` và đặt tại `data/games.csv`.

Không commit file CSV lên Git; `.gitignore` đã loại `data/` và các file `*.csv`.

> Lưu ý: header của file gốc bị thiếu dấu phẩy (`DiscountDLC count` thay vì `Discount`, `DLC count`). Block `extract_steam_games` đặt tên 40 cột thủ công khi đọc file để tránh lệch cột.

### 3. Cấu hình biến môi trường

Từ thư mục gốc project, sao chép file mẫu rồi sửa mật khẩu trong `.env`:

```powershell
Copy-Item .env.example .env
```

Giữ lại các mặc định trong file và thay giá trị mẫu `MSSQL_PASSWORD` bằng mật khẩu đủ mạnh theo yêu cầu của SQL Server:

```dotenv
MSSQL_PASSWORD=replace_with_your_sql_server_password
```

Không đặt dấu ngoặc kép quanh giá trị. Nên tránh ký tự `#` trong mật khẩu vì một số trình đọc `.env` coi đó là chú thích.

### 4. Khởi động hệ thống

```powershell
docker compose up -d --build
docker compose ps
```

Đợi SQL Server khởi động hoàn tất; có thể theo dõi bằng `docker compose logs -f sqlserver`. Service `dbt` dùng profile `transform` và được chạy theo yêu cầu bằng `docker compose run`, không cần khởi động nền.

| Dịch vụ | Địa chỉ |
|---|---|
| Mage UI | http://localhost:6789 |
| SQL Server (từ SSMS) | `localhost,1435`, user `sa` |
| SQL Server (từ trong Docker network, dùng bởi Mage) | `sqlserver:1433` |

### 5. Khởi tạo database

Trong SSMS, kết nối `localhost,1435` và chạy lần lượt hai script trong `database_setup/`:

1. `01_init_watermark_audit.sql` tạo database `steam_games_DWH`, bảng Staging, watermark và audit log.
2. `02_create_star_schema_dwh.sql` tạo schema `dwh`, 4 Dimension và bảng Fact.
3. Đặt watermark ban đầu cho chế độ Incremental:

```sql
UPDATE steam_games_DWH.dbo.etl_watermark
SET lset = '2010-01-01'
WHERE table_name = 'stg_steam_games';
```

### 6. Chạy pipeline

1. Mở Mage UI, chọn pipeline `steam_staging_pipeline`.
2. Đặt biến `run_mode` (`full` hoặc `incremental`). Với máy có 8 GB RAM, ưu tiên Incremental theo batch vì Full Load từng đọc 125.853 dòng nhưng chưa được xác nhận hoàn tất.
3. Thêm `demo_lset` và `demo_cet` nếu cần chạy batch thử nghiệm; chế độ demo không cập nhật watermark.
4. Chạy toàn bộ pipeline theo thứ tự block, rồi kiểm tra trạng thái hoàn tất, Staging và audit log. Chỉ chạy riêng block extract sẽ không nạp dữ liệu vào SQL Server.

### 7. Chạy dbt sau khi nạp Staging

dbt được đóng gói trong Docker nên chạy các lệnh dưới đây từ thư mục gốc project; không chạy `dbt` trực tiếp trong PowerShell của máy host:

```powershell
docker compose run --rm --no-deps dbt debug
docker compose run --rm --no-deps dbt build
```

Lệnh đầu kiểm tra profile/kết nối; lệnh sau chạy model và tests. Nếu chỉ cần kiểm tra ba Dimension incremental vừa điều chỉnh (sau khi đã có staging models), có thể chạy:

```powershell
docker compose run --rm --no-deps dbt build --select dim_game dim_publisher dim_platform
```

Lệnh chọn riêng không chạy Fact; dùng `dbt build` không có `--select` để chạy toàn bộ luồng.

Trong `dim_game` và `dim_publisher`, incremental chỉ lấy natural key mới và cấp surrogate key tiếp nối sau khóa lớn nhất. `dim_platform` dùng mapping khóa cố định cho tám tổ hợp và chỉ thêm các khóa còn thiếu để không xóa dòng đang được Fact tham chiếu. Trước khi chạy trên database hiện có, kiểm tra `platform_key` đang lưu có khớp mapping trong `dim_platform.sql` hay không.

Lần build trước khi sửa ba Dimension đã ghi nhận `PASS=58, ERROR=3, SKIP=39`. Sau các thay đổi mã nguồn, cần chạy lại build và lưu log mới; chưa nên coi kết quả trước đó là bằng chứng build hiện tại thành công.

Kiểm thử các trường hợp dữ liệu lỗi trong schema riêng, tự dọn sau khi chạy:

```powershell
docker compose run --rm --no-deps --entrypoint python dbt scripts/verify_dbt.py
```

Các lệnh dbt không tự chạy pipeline Mage. Khi chưa có `data/games.csv`, có thể kiểm tra
trên staging đã nạp trước đó và bộ dữ liệu giả lập, nhưng chưa thể xác nhận toàn bộ CSV.

## Kiểm tra kết quả

```sql
SELECT COUNT(*) FROM dbo.stg_steam_games;
SELECT * FROM dbo.etl_watermark;
SELECT TOP 10 * FROM dbo.etl_audit_log ORDER BY log_id DESC;

-- Không được có AppID trùng
SELECT appid, COUNT(*) FROM dbo.stg_steam_games
GROUP BY appid HAVING COUNT(*) > 1;
```

Kịch bản kiểm thử gợi ý:

1. Chạy `full`, kiểm tra số dòng staging và dòng audit.
2. `TRUNCATE TABLE dbo.stg_steam_games`, đặt lại watermark, chạy `incremental` nhiều lần và quan sát watermark tăng dần.
3. Đặt lại watermark rồi chạy lại cùng một batch: số dòng staging không đổi (chạy lại an toàn).
4. Đối soát: tổng staging sau khi chạy hết các batch bằng số dòng Full Load trừ số dòng có ngày phát hành lỗi.

## Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| `Login failed for user 'sa' (18456)` | Mage nhận sai mật khẩu (biến `.env`); sau khi sửa `.env` phải chạy `docker compose down` rồi `up -d`, không chỉ restart |
| Batch incremental trả về 0 dòng | Watermark còn ở mốc quá sớm (ví dụ `1900-01-01`) |
| Staging rỗng nhưng audit báo SUCCESS | Block `load_to_staging` chưa nối đúng thứ tự hoặc chưa chạy |
| Block treo, ổ đĩa đầy | Docker/SQL Server cần dung lượng trống trên ổ chứa Docker |

## Bảo mật và dữ liệu

- Không commit `.env`, `games.csv`, `mage_data/`.
- Trước khi đổi repository sang Public, kiểm tra cả lịch sử commit để bảo đảm không còn mật khẩu, token hoặc dữ liệu không được phép công khai.
- `io_config.yaml` chỉ tham chiếu mật khẩu qua `{{ env_var('MSSQL_PASSWORD') }}`.
- Khuyến nghị tạo user riêng với quyền vừa đủ thay vì dùng `sa` cho pipeline.

## Hạn chế đã biết

- Dataset là CSV tĩnh, không có `updated_at`; Incremental dùng `Release date` để mô phỏng các batch hai năm và không phát hiện thay đổi trên game đã nạp.
- Loader đọc toàn bộ CSV vào DataFrame trước khi cắt batch. Trên máy 8 GB RAM, Full Load có thể chưa hoàn tất; chỉ xác nhận thành công khi pipeline kết thúc và Staging/audit có kết quả tương ứng.
- Các model `dim_game` và `dim_publisher` hiện bổ sung thành viên mới nhưng chưa cập nhật thuộc tính của natural key đã tồn tại.
- Dashboard Power BI/Generative AI chưa được tính là phần hoàn thành trong repository hiện tại.

## Công nghệ

Mage.ai, SQL Server, Docker Compose, Python (pandas, pyodbc), dbt Core + dbt-sqlserver.

## Tác giả

1. `Phạm Lê Thanh Tú` - `23120388` - `HCMUS`
2. `Kiều Đỗ Song Tinh` - `23120373` - `HCMUS`
3. `Nguyễn Ngọc Bình` - `23120218` - `HCMUS`
