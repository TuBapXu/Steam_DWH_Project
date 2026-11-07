# Steam Games Data Warehouse

Đồ án Data Warehouse trên tập dữ liệu **Steam Games**. Dự án xây dựng pipeline ETL từ file CSV tĩnh vào SQL Server, gồm 3 giai đoạn:

| Giai đoạn | Công cụ | Trạng thái |
|---|---|---|
| 3.1 Data Ingestion (nạp vào Staging) | Mage.ai + SQL Server | Mỗi chunk có nhánh Extract → Validate → Load trên Mage; tối đa 2 block đồng thời. Full Load thay staging, Incremental Load cập nhật theo AppID và row_hash. |
| 3.2 Data Transformation | dbt | Tạo bảng cleaned cho các model DWH. Luồng chính gồm 6 model thực thi và 86 test. |
| 3.3 Data Warehouse (Star Schema) | SQL Server | Có script DDL tạo Fact và 4 Dimension (`database_setup/02_create_star_schema_dwh.sql`) |

## Kiến trúc

```
games.csv ──► Mage.ai pipeline ──► SQL Server (steam_games_DWH)
                                     ├── dbo.stg_steam_games   (Staging, nguồn của dbt)
                                     ├── dbo.etl_steam_incremental_batch (theo dõi batch theo AppID)
                                     └── dbo.etl_audit_log     (nhật ký thực thi)

dbo.stg_steam_games ──► dbt ──► dbt_staging.stg_steam_games_cleaned (table)
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
│   ├── data_loaders/    # prepare_steam_chunks, extract_steam_chunk
│   ├── transformers/    # validate_steam_chunk: dùng lại logic làm sạch hiện có
│   ├── data_exporters/  # load chunk, publish staging, report, dbt, đối soát
│   ├── callbacks/       # Ghi trạng thái FAILED vào audit log
│   ├── pipelines/       # Định nghĩa pipeline steam_staging_pipeline
│   ├── io_config.yaml   # Cấu hình kết nối SQL Server (đọc mật khẩu từ biến môi trường)
│   └── metadata.yaml
├── pipeline_support/    # Logic validate cũ dùng chung, đọc chunk và nạp song song
├── tests/               # Kiểm thử hồi quy Full Load, chạy không cần Docker
├── .env.example         # Mẫu cấu hình; sao chép thành .env rồi tự điền mật khẩu
├── .env                 # Biến môi trường, chứa mật khẩu (KHÔNG đẩy lên Git)
├── .gitignore
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
| `prepare_steam_chunks` | Dynamic data loader | Đọc tuần tự CSV ra Parquet từng chunk; trả danh sách chunk cho Mage điều phối |
| `extract_steam_chunk` | Data loader | Trả DataFrame thô của một chunk và metadata |
| `validate_steam_chunk` | Transformer | Trả DataFrame sạch và thống kê lỗi, dùng lại hàm validate cũ |
| `load_steam_chunk` | Data exporter | Ghi chunk sạch vào bảng SQL làm việc riêng; trả biên nhận số dòng |
| `publish_steam_staging` | Data exporter | Chờ đủ chunk, khử trùng AppID toàn file rồi công bố staging trong giao dịch |
| `report_steam_load` | Data exporter | Báo số dòng thêm, cập nhật, giữ nguyên, dòng lỗi và cửa sổ LSET/CET |
| `run_dbt_transform` | Data exporter | Chạy nguyên project `dbt build` và bộ test trong môi trường riêng; stream log lên Mage, ghi audit theo bước |
| `check_dwh_results` | Data exporter | Đối soát staging/cleaned/DWH, khóa liên kết, thuộc tính và measure; trả báo cáo số dòng và lỗi trên Mage |

Chạy cả nạp staging, dbt và kiểm tra DWH trên Mage: [Hướng dẫn tám block và các nhánh chunk](docs/MAGE_END_TO_END.md). Cần build lại image Mage khi thay dependencies bằng `docker compose up -d --build mage`.

### Cơ chế Full Load và Incremental Load

- **Full Load** đọc hết file theo chunk. Staging chỉ được thay sau khi tất cả chunk thành công.
- **Incremental Load** đọc hết file theo chunk để phát hiện game mới hoặc đổi dữ liệu. So `AppID` và SHA-256 trên các cột nghiệp vụ đã ép kiểu. Chỉ ghi dữ liệu nghiệp vụ mới hoặc khác vào staging, rồi cập nhật cleaned, dim_game và fact theo AppID thay đổi. Game vắng trong file được giữ lại.
- **LSET/CET**: theo dõi batch, không lọc theo ngày phát hành game. Để hai biến `demo_lset` và `demo_cet` bằng `null`; cách cắt khoảng ngày phát hành chỉ còn trong các block cũ đã tách khỏi pipeline này.

Nếu gián đoạn sau khi nạp staging, chạy lại toàn bộ pipeline với đúng nội dung CSV của batch đang dở để Mage tiếp tục dùng danh sách AppID đã lưu.

### Biến pipeline (Variables)

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `run_mode` | `full` hoặc `incremental` (pipeline hiện đặt `full`) | Chọn chế độ nạp |
| `source_file` | `data/games.csv` | Đường dẫn CSV trong project |
| `chunk_size` | `1000` | Số bản ghi mỗi chunk, từ 1 đến 10.000 |
| `max_workers` | `2` | Biến tương thích helper cũ; giới hạn song song thực tế của Mage là `concurrency_config.block_run_limit: 2` trong metadata pipeline |
| `dbt_timeout_seconds` | `3600` | Thời gian tối đa của tiến trình dbt trong block transform |
| `demo_lset` | `null` | Không dùng để lọc ngày trong pipeline AppID + row_hash |
| `demo_cet` | `null` | LSET/CET batch được quản lý tự động |

### Ghi nhận trạng thái và lỗi

Mỗi lần chạy ghi một dòng vào `dbo.etl_audit_log` gồm `pipeline_name`, `run_date`, `status` (`SUCCESS` hoặc `FAILED`), `records_processed`, `error_message`.

## Hướng dẫn cài đặt và chạy

### 1. Yêu cầu

- Docker Desktop (khuyến nghị cấp tối thiểu 4 GB RAM cho Docker; SQL Server cần ít nhất 2 GB)
- SQL Server Management Studio (SSMS) để chạy script khởi tạo

### 2. Chuẩn bị dữ liệu

Tải [Steam Games Dataset trên Kaggle](https://www.kaggle.com/datasets/fronkongames/steam-games-dataset), lấy file `games.csv` và đặt tại `data/games.csv`.

Không commit file CSV lên Git; `.gitignore` đã loại `data/` và các file `*.csv`.

> Lưu ý: header của file gốc bị thiếu dấu phẩy (`DiscountDLC count` thay vì `Discount`, `DLC count`). Bộ đọc CSV dùng chung đặt tên 40 cột thủ công để tránh lệch cột; quy tắc này được giữ trong luồng chunk mới.

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
| Mage UI | http://localhost:6790 (đổi bằng `STEAM_MAGE_PORT` nếu cần) |
| SQL Server (từ SSMS) | `localhost,1435`, user `sa` |
| SQL Server (từ trong Docker network, dùng bởi Mage) | `sqlserver:1433` |

### 5. Khởi tạo database

Khi khởi động, Mage chờ SQL Server rồi chạy `database_setup/bootstrap.py`. Bootstrap tạo database, schema, staging, bảng lỗi, audit, checkpoint và các bảng DWH có ràng buộc. Nó cũng nâng cấp khóa fact nếu dùng database từ bản cũ. Chạy lại bootstrap giữ nguyên staging đã nạp. dbt tạo bảng cleaned, dimension hệ điều hành và bảng cầu trong lượt pipeline đầu tiên.

Kiểm tra log khởi tạo bằng `docker compose logs mage` và tìm dòng `Steam database schema ready.`.

Nếu đã chạy bản cũ, sao lưu `mage_data/` ra ngoài thư mục repo trước khi pull để giữ tài khoản, trigger và lịch sử Mage cục bộ. Bản mới loại database SQLite của Mage khỏi Git. Dữ liệu SQL Server nằm trong volume `sqlserver_data`.
### 6. Chạy pipeline

1. Mở Mage UI, chọn pipeline `steam_staging_pipeline`.
2. Để nạp hết CSV: đặt `run_mode=full`, `source_file=data/games.csv`, `chunk_size=1000`; để `demo_lset`, `demo_cet` bằng `null`. Giới hạn song song nằm ở `concurrency_config.block_run_limit`.
3. Để nạp dữ liệu thay đổi, đặt `run_mode=incremental`, `source_file=data/games.csv` và để trống cả hai biến demo.
4. Chạy toàn bộ pipeline bằng trigger để Mage tạo các nhánh động. Xem output từng nhánh trong lượt chạy. Chỉ chạy riêng block extract sẽ không nạp dữ liệu vào SQL Server.

Pipeline có 8 block trên sơ đồ; mỗi chunk có một nhánh Extract → Validate → Load thật. Chờ block `check_dwh_results` báo `PIPELINE SUCCESS` để xác nhận toàn bộ luồng hoàn tất. Các file Parquet và output của Mage được giữ để xem và chạy lại, vì vậy cần thêm dung lượng đĩa so với luồng worker nội bộ cũ.

### 7. Chạy dbt thủ công khi cần

Pipeline đã tự chạy dbt; các lệnh dưới đây dành cho trường hợp muốn chạy transform riêng.

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

Trong luồng incremental theo hash của Mage, `dim_game` giữ surrogate key của game đã có và chỉ cấp khóa mới cho AppID mới. `dim_publisher` vẫn bổ sung publisher mới theo logic hiện có. `dim_platform` dùng mapping khóa cố định cho tám tổ hợp. Trước khi chạy trên database hiện có, kiểm tra `platform_key` đang lưu có khớp mapping trong `dim_platform.sql` hay không.

Kiểm thử bootstrap, full load và incremental V1/V2/V3 qua Mage trên database riêng:

```powershell
docker compose exec -T -w /home/src/mage_pipeline mage python /home/src/tests/verify_mage_incremental.py
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

Để tái hiện dữ liệu demo trên volume SQL mới, cả nhóm cần cùng bản `data/games.csv`. File được chia sẻ ngoài Git. Kiểm tra bằng `Get-FileHash data/games.csv -Algorithm SHA256`. SHA-256 bản đối chiếu là `343b59ffe6422f69eaf1d371779565679fc23fc76eee9de65e23121d21a49b00`.

| Lượt chạy từ trigger Mage | File | Số dòng staging/fact sau khi hoàn tất | LSET/CET sau khi đối soát |
|---|---|---:|---|
| Full | `data/games.csv` | 125.853 | 0/0 |
| Incremental V1 | `tests/fixtures/games_incremental_v1.csv` | 125.855 | 1/1 |
| Incremental V2 | `tests/fixtures/games_incremental_v2.csv` | 125.856 | 2/2 |
| Incremental V3 | `tests/fixtures/games_incremental_v3.csv` | 125.856 | 2/2 |

Chờ `PIPELINE SUCCESS` giữa các lượt. V2 báo thêm 1, cập nhật 1, giữ nguyên 1. V3 báo `NO_VALID_RECORDS` và ghi 4 lỗi theo `run_id`. Đặt lại trigger trên máy mới vì lịch sử và cấu hình trigger cục bộ nằm trong SQLite của Mage. Timestamp, ID lượt chạy, mật khẩu và lịch sử audit phụ thuộc môi trường; đối chiếu theo AppID, chỉ số nghiệp vụ, số dòng, lỗi và checkpoint.

## Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| `Login failed for user 'sa' (18456)` | Mage nhận sai mật khẩu (biến `.env`); sau khi sửa `.env` phải chạy `docker compose down` rồi `up -d`, không chỉ restart |
| Incremental thêm và cập nhật 0 dòng | Các AppID và dữ liệu nghiệp vụ trong CSV đã khớp staging |
| Chỉ thấy kết quả của vài chunk | Kiểm tra toàn bộ lượt chạy và block `publish_steam_staging`; output một chunk chưa phải kết quả cả file |
| Block treo, ổ đĩa đầy | Docker/SQL Server cần dung lượng trống trên ổ chứa Docker |

## Bảo mật và dữ liệu

- Không commit `.env`, `games.csv`, `mage_data/`.
- Trước khi đổi repository sang Public, kiểm tra cả lịch sử commit để bảo đảm không còn mật khẩu, token hoặc dữ liệu không được phép công khai.
- `io_config.yaml` chỉ tham chiếu mật khẩu qua `{{ env_var('MSSQL_PASSWORD') }}`.
- Khuyến nghị tạo user riêng với quyền vừa đủ thay vì dùng `sa` cho pipeline.

## Hạn chế đã biết

- CSV không cung cấp thời điểm chỉnh sửa từng game. Incremental phát hiện thay đổi qua nội dung tại thời điểm pipeline đọc file.
- Full Load đã đọc và validate toàn bộ CSV thật theo chunk; việc nạp SQL song song/rollback được kiểm thử trên fixture. Chưa chạy ghi toàn bộ CSV thật vào staging hiện tại trong lần cải tiến này.
- Incremental đọc và ghi tạm toàn bộ CSV để so hash trên dữ liệu đã ép kiểu SQL. Chỉ các AppID mới hoặc đổi nội dung được ghi lại vào staging và xử lý lại ở cleaned, dim_game và fact.
- Full Load cần dung lượng SQL cho bảng làm việc, staging và transaction log. Lỗi giữa chừng chạy lại toàn bộ, chưa có checkpoint để tiếp tục từ chunk đã dừng.
- Các model `dim_game` và `dim_publisher` hiện bổ sung thành viên mới nhưng chưa cập nhật thuộc tính của natural key đã tồn tại.
- Dashboard Power BI/Generative AI chưa được tính là phần hoàn thành trong repository hiện tại.

## Công nghệ

Mage.ai, SQL Server, Docker Compose, Python (pandas, pyodbc), dbt Core + dbt-sqlserver.

## Tác giả

1. `Phạm Lê Thanh Tú` - `23120388` - `HCMUS`
2. `Kiều Đỗ Song Tinh` - `23120373` - `HCMUS`
3. `Nguyễn Ngọc Bình` - `23120218` - `HCMUS`
