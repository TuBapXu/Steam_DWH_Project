# Hướng dẫn AI agent chỉnh sửa dashboard Power BI Trang 3–4

Tài liệu giao việc, lập ngày 14/11/2026. Có thể đưa nguyên file này cho AI agent có quyền thao tác workspace và Power BI Desktop.

## 1. Nhiệm vụ và kết quả cần đạt

Hãy thực hiện chỉnh sửa dashboard Steam Games theo các yêu cầu trong tài liệu này, kiểm chứng dữ liệu và tương tác, rồi bàn giao file Power BI mở được. Không dừng ở việc đề xuất lại giải pháp.

Mục tiêu:

- Trang 3 so sánh đầy đủ AAA/Indie về doanh thu ước tính, số lượng game, Metacritic và độ phủ điểm; thể hiện cơ cấu hệ điều hành đúng ý nghĩa.
- Trang 4 nhận bộ lọc drill-through và cung cấp danh sách đầy đủ từng game, có khóa định danh và chỉ số chi tiết.
- Khắc phục lỗi tỷ trọng DAX, bộ lọc loại nhầm nhà phát hành, phân loại game thiếu reviews và các nhãn dễ gây hiểu sai.
- Bảo toàn phần việc đã có của người dùng; xác minh thay đổi bằng bằng chứng cụ thể.

**Phạm vi bắt buộc:** semantic model/DAX và giao diện Trang 3–4, tài liệu DAX, xuất PBIX/PBIT mới. Phần nâng cấp ETL/modeling tại mục 9 là công việc tiếp theo; không mở rộng thành tái thiết kế toàn bộ DWH để hoàn thành dashboard.

Đây là tài liệu hướng dẫn triển khai. Các thay đổi dưới đây chưa được áp dụng vào PBIX tại thời điểm lập tài liệu.

## 2. Workspace và nguồn cần đọc

Project root trên máy hiện tại:

```text
C:\Users\HP\Desktop\C++CodeLearn\HK1-2627\HTTT_Phuc_Vu_Tri_Tue_Kinh_Doanh\mini-project\Steam_DWH_Project
```

Các đường dẫn dưới đây tính từ project root; khi làm trên máy khác, tìm project root tương ứng trước.

| File | Mục đích |
|---|---|
| `bi_dashboard/Steam_Template.pbix` | Báo cáo làm việc gốc |
| `bi_dashboard/Dashboard_Review_2026-11-14.md` | Bằng chứng và kết luận rà soát |
| `bi_dashboard/DAX_Measures_Reference.md` | DAX tham chiếu; phải đối chiếu với model thực tế |
| `README.md`, phần Semantic Model & Dashboard | Yêu cầu phân tích của dự án |
| `dbt_transform/models/marts/dim_publisher.sql` | Quy tắc AAA/Indie và publisher đại diện |
| `dbt_transform/models/marts/fact_game_snapshot.sql` | Grain và ý nghĩa khóa ngày |
| `dbt_transform/models/staging/stg_steam_games_cleaned.sql` | Quy tắc NULL, giá, reviews, Metacritic |
| `dbt_transform/models/marts/dim_platform.sql` | Tổ hợp OS |
| `output/dashboard_review_20261114/Report/definition/` | PBIR trích từ lần lưu trước; chỉ là bằng chứng tham khảo |

Tên bảng đang được dùng: `_Measures`, `dwh fact_game_snapshot`, `dwh dim_game`, `dwh dim_publisher`, `dwh dim_date`, `dwh dim_platform`, `dwh dim_game_genres`, `dwh dim_operating_system`, `dwh bridge_game_platform`.

Trong lần rà soát, trang nghiệp vụ 3 tên `publishers`, trang nghiệp vụ 4 tên `Trang 1`. Đây là trang vật lý 2/3 và 3/3, không phải trang Overview. **Nhận diện trang bằng nội dung**, không chỉ bằng số thứ tự. `Template_Overview` thuộc phạm vi khác, phải giữ nguyên.

## 3. Cách bắt đầu và bảo toàn hiện trạng

1. Đọc `AGENTS.md` nếu có, kiểm tra git status và xác định đúng file/cửa sổ `Steam_Template` đang làm việc. Lần rà soát thấy README/PBIX đã có thay đổi của người dùng; không reset hay ghi đè các thay đổi đó.
2. Kiểm tra cả trạng thái đang mở và file đã lưu. Nếu phiên đang mở có chỉnh sửa mới hơn, dùng **Save As** từ phiên đó để tạo bản làm việc `bi_dashboard/Steam_Template_Optimized.pbix`; không chỉ sao chép bản trên đĩa rồi bỏ sót thay đổi chưa lưu.
3. Nếu chưa mở báo cáo, tạo bản sao làm việc trước khi sửa. Nếu tên output đã tồn tại, dùng hậu tố thời gian để không đè mất kết quả trước.
4. Chụp lại hai trang trước thay đổi; đọc DAX và quan hệ thực tế. Không suy luận rằng `.pbit` cũ phản ánh model hiện hành: template cũ chưa có các trang vừa dựng.
5. Ưu tiên công cụ Power BI/semantic model sẵn có; nếu phải thao tác Windows, đọc và dùng kỹ năng computer-use tương ứng. Chỉ dùng cách chỉnh sửa có hỗ trợ và luôn mở lại kết quả để xác minh.
6. Không chỉnh ZIP/PBIX theo phỏng đoán hoặc thay `DataModel` nhị phân thủ công. Không tự refresh/reset database khi chỉ đang sửa report. Giữ nguyên dữ liệu import để đối chiếu trước/sau, trừ khi việc sửa model thực sự đòi hỏi refresh.
7. Giải quyết các lựa chọn kỹ thuật thông thường theo mặc định trong tài liệu này. Nếu không có công cụ để sửa/lưu Power BI, hoàn thành các phần có thể làm, bàn giao script/cấu hình cụ thể và nêu đúng bước còn thiếu; không báo PBIX đã hoàn thành khi chưa mở kiểm tra được.

## 4. Quy ước phân tích phải thống nhất

| Nội dung | Mặc định cần thực hiện |
|---|---|
| AAA/Indie | Giữ quy tắc hiện tại: publisher có ≥10 game là AAA, còn lại Indie; ghi rõ là phân nhóm quy ước theo quy mô danh mục |
| Doanh thu ước tính | Giữ công thức `(positive_reviews + negative_reviews) × 30 × price`; ghi USD và phương pháp |
| Thời gian | Năm/quý/tháng là thời gian **phát hành game**, không phải thời gian phát sinh doanh thu |
| Tỷ trọng so sánh tier | Mẫu số là tổng doanh thu của các tier đang được chọn trong visual so sánh |
| Unknown | Không loại khỏi toàn bộ trang/report; loại riêng khỏi so sánh hai nhóm và bảng xếp hạng theo đúng mục đích |
| Metacritic thiếu | Giữ BLANK, hiển thị “Chưa có điểm” hoặc `—`; không đổi thành 0 |
| Reviews bằng 0 | Không kết luận không hài lòng hoặc kém hiệu quả; hiển thị chưa đủ dữ liệu |
| OS | Bar thể hiện hỗ trợ từng OS, có chồng lấp; donut thể hiện tổ hợp OS loại trừ nhau |
| Game chi tiết | Grain là một AppID/game_key; tên game không phải khóa duy nhất |

Ghi chú ngắn đặt trên Trang 3 hoặc tooltip luôn truy cập được:

> AAA/Indie được phân nhóm quy ước theo quy mô danh mục nhà phát hành, ngưỡng 10 game. Doanh thu ước tính = tổng reviews × 30 × giá tại thời điểm dữ liệu; không phải doanh thu kế toán.

## 5. Danh sách thay đổi bắt buộc

| Mã | Thực hiện | Điều kiện đạt |
|---|---|---|
| R01 | Đổi tên `publishers` thành `03 — Nhà phát hành & Nền tảng`; đổi trang chi tiết thành `04 — Chi tiết game` | Giữ nguyên trang Overview và các liên kết điều hướng |
| R02 | Thêm matrix so sánh theo `publisher_tier` | Có số game, doanh thu, tỷ trọng doanh thu, doanh thu/game, Metacritic TB, số game có điểm, độ phủ |
| R03 | Thay tooltip `% AAA Revenue Share` trên visual theo tier bằng `Tier Revenue Share` | AAA/Indie cùng chọn thì tổng tỷ trọng 100%; chọn một tier thì 100% là đúng |
| R04 | Thêm số mẫu/độ phủ Metacritic | Nhìn thấy trực tiếp hoặc tooltip rõ ràng; so sánh điểm không phóng đại bằng trục quá hẹp |
| R05 | Sửa filter Top 15 | Loại `publisher_key = 0`, bỏ danh sách loại tên có chứa Unknown |
| R06 | Sửa ý nghĩa nhãn theo năm | Dùng “Doanh thu ước tính của game theo năm phát hành”; thứ tự thời gian tăng dần |
| R07 | Sửa hành vi game thiếu reviews và game miễn phí | Game thiếu reviews không nhận nhãn “Kém hiệu quả”; price = 0 không bị diễn giải là không tạo doanh thu thực |
| R08 | Thêm bảng toàn bộ game trên Trang 4 | Không Top N; một dòng/AppID; KPI và danh sách cùng ngữ cảnh |
| R09 | Hoàn thiện drill-through | Publisher, tier, platform_combo hoạt động; giữ năm/thể loại; Back hoạt động |
| R10 | Sửa tiêu đề “Khoan sâu 4 cấp” | Mặc định bỏ lời hứa 4 cấp; không thêm developer đại diện làm cấp phân tích game |
| R11 | Đồng nhất định dạng và slicer | USD, % đúng thang; tên tiếng Việt; cùng màu tier; chỉ số phản hồi bộ lọc nhất quán |
| R12 | Lưu và kiểm chứng đầu ra | PBIX/PBIT mới mở được, tài liệu DAX cập nhật, có checklist và bằng chứng |

### 5.1. Thiết kế Trang 3

- Đưa tiêu đề, ghi chú nghiệp vụ và slicer **Năm phát hành / Thể loại / Phân nhóm nhà phát hành** lên đầu trang. Nhãn kỹ thuật như `genre_name` không dùng làm nhãn hiển thị.
- Matrix R02 dùng `publisher_tier` làm hàng, lọc riêng visual còn AAA/Indie. Tỷ trọng và doanh thu/game phải được tính lại theo cùng slicer.
- Nếu giữ hai card AAA/Indie, mặc định chúng **tôn trọng slicer tier**: chọn AAA thì card Indie để trống/không thuộc phạm vi, không tiếp tục hiển thị số toàn Indie mà không giải thích. Có thể thay bằng card tổng trong phạm vi chọn để giảm lặp.
- Giữ biểu đồ Top 15 publisher theo doanh thu ước tính, sort giảm dần; tooltip gồm số game, doanh thu/game, điểm, độ phủ và tỷ lệ reviews tích cực.
- Bỏ filter loại trừ tên `PLAYERUNKNOWN Productions`, `Unknown Worlds Entertainment` cùng các tên chỉ vì có chữ Unknown. Nếu cần loại placeholder như `-` hoặc `(none)`, dùng danh sách **khớp toàn bộ giá trị** sau kiểm tra, không tìm kiếm chuỗi con; ghi lại quy tắc đã áp dụng.
- Giữ bar hỗ trợ Windows/Mac/Linux và donut tổ hợp. Ghi “Một game có thể hỗ trợ nhiều hệ điều hành”. Có số lượng/tỷ lệ Unknown trong ngữ cảnh phù hợp, không che giấu 8.935 game của dữ liệu rà soát.
- Nếu giữ chart Metacritic, dùng trục 0–100 và ghi độ phủ. Tránh đường nối hai nhóm tạo cảm giác đây là chuỗi thời gian.
- Biểu đồ theo năm là tùy chọn giữ lại khi bố cục đủ chỗ; nếu giữ phải sửa nhãn theo R06. Không đánh đổi bảng so sánh bắt buộc để giữ chart này.

### 5.2. Thiết kế Trang 4

Giữ một hàng tiêu đề ngữ cảnh + Back và một hàng KPI thấp. Dành tối thiểu khoảng 50–60% diện tích nội dung cho bảng chi tiết; chỉ giữ thêm 1–2 biểu đồ hỗ trợ nếu còn chỗ.

Bảng bắt buộc có:

| Cột | Cách dùng |
|---|---|
| AppID | `dwh dim_game[appid_nk]`, Don't summarize |
| Tên game | `dwh dim_game[game_name]`; luôn đi cùng AppID |
| Nhà phát hành, tier | Thuộc đúng fact/game đang xét |
| Ngày phát hành | Ngày thực; khóa ngày 0 hiển thị chưa xác định |
| Nền tảng | Tổ hợp `platform_combo` |
| Giá USD | Giá của game; không SUM nhiều giá |
| Doanh thu ước tính USD | Measure `[Estimated Revenue]` |
| Tổng reviews | Measure `[Total Reviews]` |
| Tỷ lệ tích cực | Measure xử lý BLANK cho mẫu số 0 |
| Metacritic | Điểm hoặc BLANK; không chuyển điểm thiếu thành 0 |
| Peak CCU | Measure `[Peak CCU]` tại grain game |

- Bỏ mọi Top N khỏi bảng này; sắp xếp doanh thu giảm dần ban đầu. Có tìm kiếm tên game/AppID bằng slicer hoặc control sẵn có.
- AppID/game_key phải nằm trong ngữ cảnh nhóm của scatter nếu còn sử dụng scatter, tránh gộp game trùng tên.
- Với mô hình Single filter, việc đặt đồng thời nhiều cột từ các dimension độc lập có thể tạo tổ hợp không mong muốn. Kiểm tra đường lọc trước. Nếu cần, dùng measure lấy publisher/date/platform qua foreign key trên fact cho từng game, kết hợp visual filter `[Total Games] > 0`; không bật Both hàng loạt.
- Tắt Show items with no data nếu khiến bảng hiện game ngoài phạm vi. Không hiển thị tổng cộng của AppID/giá/điểm.
- Tiêu đề/phụ đề cho biết publisher hoặc tier/platform đã chọn, khoảng năm và thể loại. Phân biệt rõ “Tất cả nhà phát hành” với “Nhiều nhà phát hành”. Nếu ngữ cảnh dài, tách thành phụ đề hoặc tooltip.

### 5.3. Drill-through và tương tác

1. Giữ cấu hình các trường `publisher_name`, `publisher_tier`, `platform_combo` ở trang đích; kiểm tra từng điểm vào thay vì giả định đặt đủ trường là mọi visual đều đi được.
2. Bật Keep all filters. Đối chiếu cả publisher/tier/platform lẫn năm/thể loại ở trang đích.
3. Kiểm tra nút Back trong chế độ đọc hoặc thao tác phù hợp với chế độ biên tập Power BI.
4. Có thể ẩn tab Trang 4 khỏi điều hướng thường sau khi các đường vào đã hoạt động; không ẩn trước rồi làm mất cách mở trang chi tiết.
5. Trên bar OS hiện tại, ba measure `Windows Games`, `Mac Games`, `Linux Games` không tạo ra một cột OS để truyền drill-through. Trong phạm vi bắt buộc, dùng donut `platform_combo` làm đường vào nền tảng, không quảng bá bar OS là một bộ lọc OS.
6. Nếu mở rộng drill-through từng OS, dùng cột của `dim_operating_system` làm trục, thêm trường đó ở trang đích, xử lý đường lọc bridge cho **mọi KPI và bảng chi tiết**, và kiểm thử chọn một/nhiều OS. Chỉ sửa một measure đếm game là chưa đủ.

## 6. DAX đề xuất

Các công thức dưới đây dùng tên model tại lần rà soát. Agent phải kiểm tra tên bảng/cột thật và dependency trước khi áp dụng. Đưa measure mới vào `_Measures`; format trong semantic model, tránh FORMAT biến số thành text nếu vẫn dùng để tính/sort.

### 6.1. Tỷ trọng tier và độ phủ

```dax
Tier Revenue Share =
DIVIDE(
    [Estimated Revenue],
    CALCULATE(
        [Estimated Revenue],
        ALLSELECTED('dwh dim_publisher'[publisher_tier])
    )
)

Games with Metacritic =
CALCULATE(
    [Total Games],
    KEEPFILTERS('dwh fact_game_snapshot'[metacritic_score] > 0)
)

Metacritic Coverage =
DIVIDE([Games with Metacritic], [Total Games])

Avg Revenue per Game =
DIVIDE([Estimated Revenue], [Total Games])
```

`Tier Revenue Share` dùng trên trục/hàng tier; không thay thế tùy tiện cho tỷ trọng publisher. ALLSELECTED giữ các lựa chọn bên ngoài visual. Nếu đang chọn chỉ AAA/Indie, mẫu số phải chỉ gồm hai nhóm đó. Không chia cho một tổng loại Unknown rồi gắn nhãn “toàn thị trường”.

`Games with Metacritic` dùng >0 vì SQL hiện đã đưa điểm ngoài 1–100 về NULL. Nếu model thực tế không còn bảo đảm điều này, xác minh dữ liệu trước khi quyết định thêm điều kiện <=100.

### 6.2. Card tôn trọng slicer và tỷ lệ reviews

Nếu giữ card cố định AAA/Indie, áp dụng cùng nguyên tắc cho các measure doanh thu/số game/điểm cần phản hồi slicer:

```dax
AAA Revenue =
CALCULATE(
    [Estimated Revenue],
    KEEPFILTERS('dwh dim_publisher'[publisher_tier] = "AAA")
)

Indie Revenue =
CALCULATE(
    [Estimated Revenue],
    KEEPFILTERS('dwh dim_publisher'[publisher_tier] = "Indie")
)

Positive Review Ratio =
DIVIDE([Total Positive Reviews], [Total Reviews])

Game Price =
IF(
    HASONEVALUE('dwh dim_game'[game_key]),
    SELECTEDVALUE('dwh fact_game_snapshot'[price])
)
```

Thay đổi Positive Review Ratio ảnh hưởng các visual/measure phụ thuộc, nhất là Game Status. Kiểm tra những nơi đang giả định BLANK = 0. Không xóa measure cũ khi còn visual khác sử dụng; chuyển visual theo tier sang measure mới trước và cập nhật tài liệu.

### 6.3. Game Status ở cấp từng game

Mặc định sửa thành trạng thái mô tả số liệu, có xử lý thiếu dữ liệu và miễn phí. Ngưỡng dưới đây giữ các mức quy ước 1 triệu USD, 80% và 70% của báo cáo hiện có; chưa phải mô hình dự báo hay kết luận lợi nhuận.

```dax
Game Status =
VAR OneGame = HASONEVALUE('dwh dim_game'[game_key])
VAR GamesInContext = [Total Games]
VAR Reviews = [Total Reviews]
VAR Price = SELECTEDVALUE('dwh fact_game_snapshot'[price])
VAR Revenue = [Estimated Revenue]
VAR PositiveRatio = [Positive Review Ratio]
RETURN
IF(
    NOT(OneGame) || COALESCE(GamesInContext, 0) = 0,
    BLANK(),
    SWITCH(
        TRUE(),
        COALESCE(Reviews, 0) = 0, "Chưa đủ dữ liệu đánh giá",
        ISBLANK(Price), "Thiếu giá — chưa đánh giá thương mại",
        Price = 0, "Miễn phí — tham chiếu reviews và CCU",
        Revenue >= 1000000 && PositiveRatio >= 0.80,
            "Doanh thu ước tính cao — đánh giá tốt",
        Revenue < 1000000 && PositiveRatio >= 0.80,
            "Doanh thu ước tính thấp — đánh giá tốt",
        Revenue >= 1000000 && PositiveRatio < 0.70,
            "Doanh thu ước tính cao — tỷ lệ tích cực thấp",
        Revenue >= 1000000,
            "Doanh thu ước tính cao — đánh giá trung bình",
        "Doanh thu ước tính thấp — cần xem thêm dữ liệu"
    )
)
```

Đây là công thức đề xuất, **chưa được chạy trên model** trong lần rà soát trước. Agent phải kiểm chứng các nhánh bằng query hoặc mẫu dữ liệu thật. Không kết luận game “kém hiệu quả” chỉ từ doanh thu proxy vì không có chi phí và dữ liệu monetization đầy đủ.

### 6.4. Lấy nhãn publisher qua fact khi bảng chi tiết cần

Ví dụ dưới đây tránh giả định filter từ game tự đi ngược qua fact lên dim_publisher. Chỉ dùng nếu phù hợp quan hệ thực tế; kiểm tra hiệu năng khi nhiều dòng.

```dax
Game Publisher =
VAR PublisherKey =
    SELECTEDVALUE('dwh fact_game_snapshot'[publisher_key])
RETURN
IF(
    HASONEVALUE('dwh dim_game'[game_key])
        && NOT(ISBLANK(PublisherKey)),
    LOOKUPVALUE(
        'dwh dim_publisher'[publisher_name],
        'dwh dim_publisher'[publisher_key], PublisherKey
    )
)
```

Có thể áp dụng cùng mẫu cho tier, tổ hợp nền tảng và ngày phát hành thông qua foreign key tương ứng. Ngày có `date_key = 0` phải trả BLANK/nhãn chưa xác định. Không lấy developer đại diện trong dim_publisher để gán cho từng game.

## 7. Dữ liệu đối chiếu và kiểm thử

### 7.1. Baseline đã xác minh ngày 14/11/2026

Các số dưới đây thuộc **toàn bộ model, không có bộ lọc năm/thể loại của trang**. Đây là mốc đối chiếu nếu dữ liệu chưa refresh; không hardcode trong measure hoặc buộc dữ liệu mới phải khớp mốc cũ.

| Tier | Games | Có Metacritic | Độ phủ | Doanh thu proxy USD |
|---|---:|---:|---:|---:|
| AAA | 28.912 | 2.485 | 8,60% | 18.343.306.146,30 |
| Indie | 88.009 | 1.728 | 1,96% | 19.655.307.384,30 |
| Unknown | 8.935 | 45 | 0,50% | 41.395.841,10 |
| Tổng | 125.856 | 4.258 | 3,38% | 38.040.009.371,70 |

- Tỷ trọng chỉ trong AAA/Indie: **48,2736% / 51,7264%**.
- Không có reviews: AAA **7.291**, Indie **27.181**.
- Lần thử drill-through Game Science với bộ lọc năm hiện hành: **2 game**, khoảng **2,07 tỷ USD proxy**, Metacritic BLANK. Đây là ca tái hiện, không phải kỳ vọng bất biến khi thay slicer/dữ liệu.
- Số lượng game và doanh thu không được tự tăng chỉ vì thêm bảng chi tiết hoặc bridge vào visual.

Query tham khảo để kiểm tra matrix sau khi tạo measures:

```dax
EVALUATE
SUMMARIZECOLUMNS(
    'dwh dim_publisher'[publisher_tier],
    TREATAS({"AAA", "Indie"}, 'dwh dim_publisher'[publisher_tier]),
    "Games", [Total Games],
    "Revenue", [Estimated Revenue],
    "Share", [Tier Revenue Share],
    "Scored", [Games with Metacritic],
    "Coverage", [Metacritic Coverage]
)
```

### 7.2. Checklist bắt buộc ghi kết quả

| Test | Thao tác | Kỳ vọng |
|---|---|---|
| T01 | So sánh tổng fact và DISTINCTCOUNT game_key trước/sau | Grain giữ nguyên; không nhân dòng |
| T02 | Chọn đồng thời AAA/Indie, không lọc năm | Tỷ trọng cộng 100%; khớp baseline nếu chưa refresh |
| T03 | Chọn chỉ AAA rồi chỉ Indie | Matrix và card phản hồi nhất quán; tier duy nhất có tỷ trọng 100% |
| T04 | Chọn một năm và một genre | Số game, doanh thu, điểm, độ phủ thay đổi theo cùng phạm vi |
| T05 | Drill-through từ một publisher | Chỉ có AppID thuộc publisher và bộ lọc nguồn; KPI khớp bảng |
| T06 | Drill-through từ một tier | Danh sách đúng tier; không chỉ Top 10 |
| T07 | Drill-through từ một platform_combo | Bảng đúng tổ hợp OS; năm/genre vẫn được giữ |
| T08 | Dùng nút Back | Trở lại trang nguồn, ngữ cảnh nguồn đúng |
| T09 | Đối chiếu distinct AppID trong bảng chi tiết với Total Games | Bằng nhau trong cùng ngữ cảnh; không đếm số dòng đang nhìn thấy do cuộn/virtualization |
| T10 | Kiểm tra hai AppID trùng tên nếu dữ liệu có | Hai game vẫn tách biệt; nếu không có, ghi N/A thay vì bịa mẫu |
| T11 | Chọn game chưa có reviews/Metacritic | Tỷ lệ/điểm hiển thị thiếu dữ liệu; không gắn “Kém hiệu quả” |
| T12 | Chọn game miễn phí và game thiếu giá | Phân biệt price = 0 với BLANK; không suy diễn doanh thu thực bằng 0 |
| T13 | Kiểm tra publisher có chữ Unknown trong dữ liệu | Không bị loại do tên; có thể ngoài Top 15 vì thứ hạng bình thường |
| T14 | Cộng số game theo các tổ hợp OS | Bằng tổng game khi cùng bộ lọc, có tính Unknown; bar OS có thể chồng lấp |
| T15 | Kiểm tra nhãn và thứ tự thời gian | Năm phát hành; sort tăng dần; không hiển thị ngày kỹ thuật như ngày thực |
| T16 | Lưu, đóng/mở lại bản output an toàn | Các trang, measures, tên và drill-through được lưu; không visual lỗi |
| T17 | Xuất PBIT mới và kiểm tra cấu trúc | Có hai trang mới và model cập nhật; không đánh đồng yêu cầu refresh dữ liệu với lỗi template |

Nếu chưa kiểm thử được một mục, ghi **Chưa kiểm thử** và nguyên nhân, không đánh dấu Passed. Kiểm thử logic DAX không thay thế kiểm thử filter propagation trong UI.

Sau khi đúng chức năng, dùng Performance Analyzer nếu có để ghi thời gian các visual chính trong cùng điều kiện trước/sau. Chỉ tuyên bố nhanh hơn khi có số đo. Không chuyển SUMX sang ETL hay bật Both chỉ vì dự đoán có thể nhanh hơn.

## 8. Trình tự triển khai và đầu ra

Thứ tự thực hiện:

1. Kiểm tra hiện trạng và tạo bản làm việc bảo toàn chỉnh sửa chưa lưu.
2. Sửa measure và ngữ nghĩa dữ liệu, kiểm tra query.
3. Sửa filter và dựng phần so sánh Trang 3.
4. Dựng bảng chi tiết Trang 4 theo grain game.
5. Kiểm thử drill-through, slicer, Back và các trường hợp thiếu dữ liệu.
6. Hoàn thiện format/bố cục và kiểm tra lại visual ở kích thước trình chiếu.
7. Lưu PBIX mới, xuất PBIT mới, mở lại kiểm tra, cập nhật tài liệu và bàn giao.

Đầu ra cần có trong `bi_dashboard/`:

- `Steam_Template_Optimized.pbix`: dashboard hoàn chỉnh; nếu tên đã tồn tại dùng hậu tố thời gian và ghi rõ tên thực.
- `Steam_Template_Optimized.pbit`: template xuất từ bản hoàn chỉnh.
- `DAX_Measures_Reference.md`: cập nhật đúng công thức, format, ngữ cảnh dùng và quy tắc thiếu dữ liệu đã triển khai; giữ phần còn đúng.
- `Dashboard_Implementation_Notes.md`: ánh xạ R01–R12 → thay đổi → bằng chứng; kết quả T01–T17; vấn đề còn lại; model/data có refresh hay không.
- Ảnh toàn Trang 3, Trang 4 và ít nhất một ca drill-through trong `output/dashboard_optimization/`. Không đưa dữ liệu nhạy cảm/credentials vào bằng chứng.

Trả lời bàn giao ngắn gọn: link PBIX/PBIT, những thay đổi chính, các kiểm thử đã đạt, phần còn chưa làm hoặc chưa kiểm thử. Không tự push/publish lên Power BI Service; nhiệm vụ này kết thúc ở artifact cục bộ có thể mở và review.

## 9. Nâng cấp modeling để làm tiếp

Các mục này cần kế hoạch/kiểm thử riêng và không phải lý do trì hoãn phần dashboard bắt buộc:

1. **Tier bị cũ khi incremental:** hiện `dim_publisher.sql` chỉ thêm publisher chưa tồn tại. Nếu triển khai sửa, cập nhật thuộc tính publisher hiện có mà giữ nguyên `publisher_key`; không delete/reinsert khóa đang được fact tham chiếu. Kiểm thử publisher từ 9 → 10 game, kiểm tra khóa/FK và khả năng chạy lại không đổi kết quả. Chỉ làm trên môi trường kiểm thử phù hợp, không full-refresh database đang dùng để trình diễn chỉ để tái hiện ca này.
2. **Phân loại AAA/Indie có nguồn:** thay heuristic bằng mapping được kiểm chứng có nguồn và ngày xác nhận; phân biệt tier publisher với phân loại từng game. Không tự gán nhãn theo kiến thức nhớ lại hoặc đánh đồng publisher nhỏ với game ngân sách nhỏ.
3. **Developer đúng grain:** bổ sung quan hệ game–developer nếu cần phân tích developer; cột developer hiện tại chỉ là đại diện của publisher.
4. **Lịch sử theo thời gian:** bổ sung snapshot_date và dữ liệu lịch sử nếu yêu cầu mở rộng sang biến động theo kỳ. Revenue proxy chênh giữa snapshot không tương đương doanh thu giao dịch.
5. **Drill-through từng OS:** xử lý bridge và mọi KPI/detail đồng bộ, kiểm thử đa lựa chọn; tránh tạo đường lọc mơ hồ bằng Both hàng loạt.

Ghi các mục chưa triển khai vào implementation notes với trạng thái “Ngoài phạm vi dashboard lần này”, không mô tả chúng như lỗi đã sửa.

## 10. Nguồn kỹ thuật để đối chiếu khi triển khai

- [Microsoft — CALCULATE và filter context](https://learn.microsoft.com/en-us/dax/calculate-function-dax/)
- [Microsoft — Drillthrough](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-drillthrough)
- [Microsoft — Bi-directional filtering guidance](https://learn.microsoft.com/en-us/power-bi/guidance/relationships-bidirectional-filtering)
- [Microsoft — INFO.VIEW.MEASURES](https://learn.microsoft.com/en-us/dax/info-view-measures-function-dax)

Những dữ kiện baseline và lỗi đã tái hiện nằm trong `Dashboard_Review_2026-11-14.md`. Khi trạng thái hiện tại khác baseline, kiểm tra nguyên nhân và dùng dữ liệu thực tế; không sửa số liệu để ép khớp tài liệu.
