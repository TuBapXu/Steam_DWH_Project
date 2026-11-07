# Chạy pipeline theo từng chunk trên Mage

Pipeline steam_staging_pipeline có 8 block trên sơ đồ.

| Block | Output |
|---|---|
| prepare_steam_chunks | Danh sách chunk và metadata định danh. CSV được đọc tuần tự ra các file Parquet riêng của lượt chạy |
| extract_steam_chunk | DataFrame thô của một chunk và thông tin chunk |
| validate_steam_chunk | DataFrame sạch và số dòng lỗi, trùng của chunk đó |
| load_steam_chunk | Biên nhận số dòng đã ghi vào bảng SQL làm việc riêng |
| publish_steam_staging | Tổng hợp đủ mọi chunk, giữ AppID cuối cùng trong file, công bố staging và ghi audit trong giao dịch |
| report_steam_load | Báo cáo nạp staging, gồm LSET/CET cho incremental |
| run_dbt_transform | Kết quả dbt build và toàn bộ test hiện có |
| check_dwh_results | Đối soát DWH, hoàn tất batch và cập nhật LSET |

Mage tạo một nhánh Extract → Validate → Load cho mỗi chunk. Với games.csv đã kiểm thử trước đây và chunk_size=1000, có 126 nhánh. Ba bước cuối chạy một lần sau khi staging đã công bố.

## Chạy trên giao diện

Mở http://localhost:6790 và chọn `steam_staging_pipeline`. Có thể đổi cổng qua `STEAM_MAGE_PORT` trong `.env`. Trên bản clone mới, tạo trigger trên giao diện Mage theo thứ tự lượt chạy trong README.

Trong Variables đặt:

```yaml
run_mode: full
source_file: data/games.csv
chunk_size: 1000
demo_lset: null
demo_cet: null
dbt_timeout_seconds: 3600
```

Vào Triggers của pipeline, tạo trigger chạy một lần (Run once), kiểm tra Variables của trigger rồi bấm Run now. Nếu dùng trigger đã tồn tại, kiểm tra các giá trị ghi đè của trigger. Cần tạo lượt chạy mới sau khi đổi biến, không tiếp tục xem output của lượt chạy cũ.

Mage sẽ tạo các nhánh động. Xem từng nhánh chunk ở lượt chạy, mở output của extract_steam_chunk và validate_steam_chunk để xem DataFrame. Chờ check_dwh_results báo PIPELINE SUCCESS. Không dùng menu Run của notebook/kernel để thay cho trigger điều phối cả pipeline.

Giới hạn chạy đồng thời nằm trong concurrency_config.block_run_limit của metadata pipeline, hiện là 2. max_workers của luồng cũ được thay bằng giới hạn điều phối này.

## Incremental và chạy lại

Đặt run_mode=incremental để dùng AppID và row_hash. Quy tắc chuẩn hóa, phép tính dbt và các test được dùng lại. Nếu dbt lỗi sau khi staging đã ghi, chạy lại với cùng nội dung CSV để tiếp tục batch đang dở. LSET chỉ tiến lên khi đối soát đạt.

File Parquet thô được giữ trong output/mage_chunks/<run_id> để phục vụ kiểm tra và chạy lại. Mage cũng lưu output mỗi block. Các bảng SQL làm việc của chunk được dọn sau khi staging đã công bố. Nếu chunk lỗi, staging chính thức vẫn giữ dữ liệu đã công bố trước đó.

## Kiểm thử

Với DWH đã tồn tại từ trước khi đổi khóa fact, chạy `database_setup/03_migrate_fact_composite_key.sql` trên database Steam khi pipeline đang rảnh và không có batch incremental đang chờ. Script điền khóa Unknown và đổi PK trong một giao dịch. Sau đó, có thể chạy `dbt build --select dim_operating_system bridge_game_platform` trên cùng database để tạo bảng cầu từ fact hiện có. DWH tạo mới dùng trực tiếp DDL trong `02_create_star_schema_dwh.sql`.

Khóa ngày `0` biểu thị ngày phát hành chưa biết. Khi phân tích lịch theo `full_date`, lọc riêng khóa này để ngày kỹ thuật `0001-01-01` không xuất hiện như ngày phát hành thật. Khi đếm game qua nhiều hệ điều hành, đếm distinct `game_key`.

```powershell
docker compose exec -T -w /home/src/mage_pipeline mage python /home/src/tests/verify_mage_incremental.py
```

Bài kiểm thử dùng metadata Mage và database SQL riêng, chạy qua engine dynamic của Mage. Nó kiểm tra Full V1, Incremental V1/V2, lỗi dbt thật, chạy lại cùng batch và chạy lại V2 không thêm dòng trùng. Kiểm tra đọc toàn bộ games.csv qua Extract/Validate mà không ghi SQL bằng `docker compose exec -T mage python /home/src/tests/verify_dynamic_csv.py`.

Kết quả mong đợi trên V1/V2: V2 thêm 1 game, đổi rating 1 game, giữ nguyên 1 game; chạy lại V2 có 0 thêm, 0 đổi, 3 giữ nguyên. LSET/CET lần lượt là 1/1 sau V1, 1/2 khi dbt V2 lỗi, 2/2 sau retry thành công, và 3/3 sau lượt chạy V2 tiếp theo.
