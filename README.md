# Steam Games Data Warehouse

Đồ án Data Warehouse trên tập dữ liệu **Steam Games**. Dự án xây dựng pipeline ETL từ file CSV tĩnh vào SQL Server, gồm 3 giai đoạn:

| Giai đoạn | Công cụ | Trạng thái |
|---|---|---|
| 3.1 Data Ingestion (nạp vào Staging) | Mage.ai + SQL Server | Hoàn thành |
| 3.2 Data Transformation | dbt | Chưa thực hiện |
| 3.3 Data Warehouse (Star Schema) | SQL Server | Chưa thực hiện |

## Kiến trúc

```
games.csv ──► Mage.ai pipeline ──► SQL Server (steam_games_DWH)
                                     ├── dbo.stg_steam_games   (Staging)
                                     ├── dbo.etl_watermark     (điều khiển incremental)
                                     └── dbo.etl_audit_log     (nhật ký thực thi)
```

Toàn bộ chạy trong Docker Compose gồm hai service: `mage` và `sqlserver`.

## Cấu trúc thư mục

```
Steam_DWH_Project/
├── bi_dashboard/        # (Dự kiến) dashboard BI
├── data/                # Chứa games.csv (KHÔNG đẩy lên Git)
├── database_setup/      # Script SQL khởi tạo database, bảng staging, watermark, audit
├── dbt_transform/       # (Dự kiến) dự án dbt cho giai đoạn 3.2
├── mage_pipeline/       # Dự án Mage.ai
│   ├── data_loaders/    # extract_steam_games: đọc CSV, chia batch Full/Incremental
│   ├── transformers/    # validate_clean: kiểm tra cấu trúc, chất lượng, làm sạch cơ bản
│   ├── data_exporters/  # load_to_staging, update_watermark_audit
│   ├── callbacks/       # Ghi trạng thái FAILED vào audit log
│   ├── pipelines/       # Định nghĩa pipeline steam_staging_pipeline
│   ├── io_config.yaml   # Cấu hình kết nối SQL Server (đọc mật khẩu từ biến môi trường)
│   └── metadata.yaml
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

Tải **Steam Games Dataset** (`games.csv`) từ Kaggle và đặt tại `data/games.csv`.

> Lưu ý: header của file gốc bị thiếu dấu phẩy (`DiscountDLC count` thay vì `Discount`, `DLC count`). Block `extract_steam_games` đặt tên 40 cột thủ công khi đọc file để tránh lệch cột.

### 3. Cấu hình biến môi trường

Tạo `.env` và đặt mật khẩu SQL Server (đủ mạnh: tối thiểu 8 ký tự, có chữ hoa, chữ thường, số, ký tự đặc biệt):

```dotenv
MSSQL_PASSWORD=your_password_here
```

Không đặt dấu ngoặc kép quanh giá trị. Nên tránh ký tự `#` trong mật khẩu vì một số trình đọc `.env` coi đó là chú thích.

### 4. Khởi động hệ thống

```bash
docker compose up -d
```

Đợi khoảng 30 giây để SQL Server khởi động hoàn tất.

| Dịch vụ | Địa chỉ |
|---|---|
| Mage UI | http://localhost:6789 |
| SQL Server (từ SSMS) | `localhost,1435`, user `sa` |
| SQL Server (từ trong Docker network, dùng bởi Mage) | `sqlserver:1433` |

### 5. Khởi tạo database

Trong SSMS, kết nối `localhost,1435` và chạy lần lượt các script trong `database_setup/`:

1. Chạy script 01_init_watermark_audit trong database_setup
2. Đặt watermark ban đầu gần ngày phát hành nhỏ nhất của dữ liệu:

```sql
UPDATE steam_games_DWH.dbo.etl_watermark
SET lset = '2010-01-01'
WHERE table_name = 'stg_steam_games';
```

### 6. Chạy pipeline

1. Mở Mage UI, chọn pipeline `steam_staging_pipeline`.
2. Đặt biến `run_mode` (`full` hoặc `incremental`).
3. Thêm biến demo_lset và demo_cet nếu cần
4. Chạy toàn bộ pipeline (không chạy riêng từng block).

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

## Bảo mật

- Không commit `.env`, `games.csv`, `mage_data/`.
- `io_config.yaml` chỉ tham chiếu mật khẩu qua `{{ env_var('MSSQL_PASSWORD') }}`.
- Khuyến nghị tạo user riêng với quyền vừa đủ thay vì dùng `sa` cho pipeline.

## Công nghệ

Mage.ai, SQL Server, Docker Compose, Python (pandas, pyodbc), dbt (dự kiến).

## Tác giả

1. `Phạm Lê Thanh Tú` - `23120388` - `HCMUS`
2. `Kiều Đỗ Song Tinh` - `23120373` - `HCMUS`
3. `Nguyễn Ngọc Bình` - `23120218` - `HCMUS`
