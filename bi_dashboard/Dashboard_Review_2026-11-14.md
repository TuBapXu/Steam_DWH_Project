# Rà soát Trang 3 — Nhà phát hành & Nền tảng và Trang 4 — Chi tiết game

Ngày rà soát: 14/11/2026.

## Kết luận

**Đã có các thành phần chính, nhưng chưa đủ để nghiệm thu yêu cầu phân tích.** Hai phần thiếu trực tiếp là so sánh **số lượng game theo AAA/Indie trên Trang 3** và **bảng danh sách chi tiết đầy đủ trên Trang 4**. Ngoài ra có lỗi tỷ trọng DAX đã tái hiện, bộ lọc loại nhầm tên nhà phát hành và các nhãn phân tích cần làm rõ.

Đối chiếu với `README.md:223–245`, `bi_dashboard/DAX_Measures_Reference.md`, SQL modeling hiện tại, cấu hình lưu trong `Steam_Template.pbix`, và phiên Power BI đang mở. Trong file, các trang tương ứng đang tên `publishers` và `Trang 1`; số thứ tự vật lý là 2/3 và 3/3. `Template_Overview` chỉ có một card, nên đánh giá này chỉ nghiệm thu phạm vi Trang 3–4 được yêu cầu, không kết luận các phần việc Trang 1–2 của nhóm đã hoàn thành.

Đã đọc công thức trực tiếp qua `INFO.VIEW.MEASURES()` và chạy truy vấn DAX kiểm chứng. Không cập nhật measure, quan hệ, pipeline hoặc lưu đè PBIX. Có để lại một truy vấn chỉ đọc trong tab `Truy vấn 2` của phiên Power BI, đã trả giao diện về `publishers`.

## 1. Mức đáp ứng yêu cầu

| Yêu cầu | Bằng chứng hiện có | Đánh giá |
|---|---|---|
| Doanh thu ước tính AAA/Indie | Hai card và combo chart theo `publisher_tier` | Có, cần sửa tỷ trọng tooltip và chú thích phương pháp |
| Số lượng game AAA/Indie | Có measures `AAA Games`, `Indie Games`, `Total Games`; `Total Games` chỉ nằm trong tooltip Top 15 ở Trang 3 | Chưa có so sánh trực tiếp theo tier |
| Điểm Metacritic AAA/Indie | Đường trên combo chart | Có, thiếu số game có điểm và tỷ lệ bao phủ |
| Cơ cấu hệ điều hành | Bar Windows/Mac/Linux và donut `platform_combo` | Đúng hướng; phân biệt tỷ lệ hỗ trợ chồng lấp với cơ cấu tổ hợp |
| Drill-through | Đã cấu hình publisher, tier, platform; có tiêu đề động, nút Back và Keep all filters | Đã thử thành công từ Top 15 → Game Science, giữ publisher và năm |
| Danh sách chi tiết từng game | Scatter theo tên game, Top 10 game và tooltip | Chưa đạt: chưa có table/matrix đầy đủ |
| Khoan sâu nhà phát hành | Tiêu đề ghi “Khoan sâu 4 cấp”, nhưng Category trong file chỉ có `publisher_tier` | Tiêu đề vượt quá cấu hình hiện có |

## 2. Các phát hiện cần sửa trước nghiệm thu

### P1 — Thiếu bảng chi tiết game

Trang đích hiện có bốn KPI, Top 7 thể loại, biểu đồ theo năm, scatter và Top 10 game. Top 10 và tooltip không thay thế danh sách đầy đủ các game trong ngữ cảnh đã chọn.

**Đề xuất:** Dành ít nhất nửa dưới Trang 4 cho table, bỏ giới hạn Top N khỏi bảng này. Các cột: AppID, tên game, nhà phát hành, tier, ngày phát hành, tổ hợp OS, giá USD, doanh thu ước tính USD, tổng reviews, tỷ lệ tích cực, Metacritic, Peak CCU. Bổ sung tìm kiếm tên/AppID. Dùng AppID hoặc game_key để đảm bảo mỗi dòng là một game; `appid_nk` đặt **Don't summarize**, không dùng SUM. Giá tại cấp game dùng giá trị đơn/SELECTEDVALUE hoặc measure phù hợp, không mặc định cộng giá giữa các game trùng tên.

Tên game đang là khóa nhóm của scatter và Top 10; chưa kiểm đếm tên trùng trong lượt rà soát này. Dùng khóa duy nhất sẽ phòng việc hai AppID cùng tên bị gộp. Khi dựng bảng từ nhiều dimension với quan hệ Single, kiểm tra bảng chỉ trả các game có fact trong ngữ cảnh; có thể thêm visual filter `[Total Games] > 0` và tránh bật Show items with no data.

### P1 — Tỷ trọng doanh thu sai trong ngữ cảnh tier

Công thức thực tế:

```dax
AAA Revenue =
CALCULATE([Estimated Revenue], 'dwh dim_publisher'[publisher_tier] = "AAA")

% AAA Revenue Share = DIVIDE([AAA Revenue], [Estimated Revenue], 0)
```

Measure `% AAA Revenue Share` đang dùng trong tooltip combo chart có trục `publisher_tier`. Khi xem Indie, tử số chuyển sang AAA nhưng mẫu số vẫn là Indie; khi xem AAA, cả hai là AAA nên luôn bằng 100%.

Kết quả truy vấn toàn mô hình, không có bộ lọc năm của trang:

| Tier | Số game | Có Metacritic | Điểm TB | Doanh thu ước tính USD | `% AAA Revenue Share` hiện tại |
|---|---:|---:|---:|---:|---:|
| AAA | 28.912 | 2.485 | 74,46 | 18.343.306.146,30 | 1,00 = 100% |
| Indie | 88.009 | 1.728 | 73,20 | 19.655.307.384,30 | khoảng 0,93 = 93% |
| Unknown | 8.935 | 45 | 69,51 | 41.395.841,10 | khoảng 443,12 lần |

**Thay tooltip bằng measure tỷ trọng của tier đang hiển thị:**

```dax
Tier Revenue Share =
DIVIDE(
    [Estimated Revenue],
    CALCULATE(
        [Estimated Revenue],
        ALLSELECTED('dwh dim_publisher'[publisher_tier])
    )
)
```

Đặt format Percentage. Công thức này được kiểm chứng bằng query-scoped measure, chỉ chọn AAA và Indie trên toàn mô hình: AAA **48,27%**, Indie **51,73%**. Mẫu số là các tier đang được chọn; chọn duy nhất một tier thì 100% là đúng. Đây là measure dành cho so sánh tier, không phải tỷ trọng nhà phát hành so với toàn thị trường.

Với card cố định AAA/Indie, xác định rõ hành vi slicer: nếu muốn card tôn trọng lựa chọn tier, dùng `KEEPFILTERS`; nếu muốn luôn giữ cả hai card để đối chiếu, cấu hình interaction có chủ đích và ghi rõ. Không để người đọc tưởng card đang tuân theo slicer trong khi measure đã ghi đè tier.

### P1 — AAA/Indie hiện là quy tắc quy mô danh mục

`dbt_transform/models/marts/dim_publisher.sql:59` dùng `game_count >= 10` để gán AAA, còn lại Indie. Dashboard hiện hiển thị Game Science là Indie; đây là kết quả của quy tắc đã chọn, không phải xác minh ngân sách hoặc tính độc lập của từng game.

**Phương án tối thiểu:** Giữ quy tắc của bài tập nhưng ghi ngay dưới tiêu đề: “AAA/Indie là phân nhóm quy ước theo số game của nhà phát hành trong bộ dữ liệu; ngưỡng 10 game”. Có thể đổi nhãn trình bày thành “Danh mục ≥10 game” / “Danh mục <10 game”.

**Phương án modeling tốt hơn:** Tạo bảng mapping được kiểm chứng có nguồn, ngày xác nhận và nhóm Unknown/Unclassified; xác định rõ phân loại ở cấp nhà phát hành hay tựa game. Không dùng số lượng game làm bằng chứng trực tiếp về ngân sách sản xuất.

Lưu ý modeling liên quan: nhánh incremental của `dim_publisher.sql:79–82` chỉ nạp tên nhà phát hành chưa tồn tại. Nhà phát hành từ 9 lên 10 game có thể vẫn giữ tier cũ. Cần cập nhật thuộc tính/tier cho khóa hiện có, bảo toàn `publisher_key`; kiểm tra bằng tình huống 9 → 10 game trước khi triển khai. Chưa chạy thử incremental trong lượt rà soát dashboard này.

### P1 — Bộ lọc Top 15 loại quá rộng

Visual `6b4cba7a7c66007051cb` lưu danh sách loại trừ nhiều tên chứa “Unknown”, gồm `PLAYERUNKNOWN Productions`, `Unknown Worlds Entertainment` và các tên khác, cùng với `Unknown Publisher`. Bộ lọc này còn được truyền sang trang chi tiết khi Keep all filters bật.

**Sửa:** Loại bản ghi kỹ thuật bằng `publisher_key <> 0`. Với các giá trị placeholder như `-`, `--`, `(none)`, chuẩn hóa bằng danh sách giá trị chính xác hoặc cờ chất lượng dữ liệu trong ETL; không loại một nhà phát hành chỉ vì tên chứa chuỗi “Unknown”. Hiển thị riêng số game chưa xác định nhà phát hành. Hiện có **8.935/125.856 game, khoảng 7,10%**, thuộc tier Unknown.

### P1 — Nhãn thời gian dễ tạo kết luận sai

`fact_game_snapshot.sql` dùng ngày phát hành làm `date_key` và incremental có `unique_key = game_key`. Mô hình hiện cung cấp trạng thái game tại lần nạp, chưa có chuỗi snapshot theo thời gian đủ để tính doanh thu phát sinh từng năm.

**Sửa nhanh:** Đổi “Xu hướng Doanh thu: AAA vs Indie theo Năm” thành **“Doanh thu ước tính của game theo năm phát hành”**. Với biểu đồ trang chi tiết, làm rõ cột là số game phát hành, đường là doanh thu ước tính của nhóm game đó. Kiểm tra sort theo năm/quý/tháng tăng dần; cấu hình lưu hiện chọn sort bằng measure, dù hình đang xem vẫn hiện các năm theo thứ tự.

Nếu cần tăng trưởng doanh thu theo năm thật sự: bổ sung snapshot_date và lịch sử chỉ số, hoặc dữ liệu giao dịch theo ngày. Chênh lệch proxy reviews × giá giữa hai snapshot cũng không tự động trở thành doanh thu giao dịch thực.

### P2 — Thiếu độ phủ Metacritic và so sánh quy mô

Toàn mô hình có **4.258/125.856 game có điểm**, khoảng **3,38%**. Độ phủ AAA **8,60%**, Indie **1,96%**. Vì vậy so sánh điểm trung bình chỉ mô tả nhóm có điểm, chưa đại diện cho toàn bộ danh mục. SQL cleaning đã chuyển điểm ngoài 1–100 thành NULL; không cần mặc định cho rằng điểm 0 đang bị tính vào trung bình.

Thêm matrix hai hàng AAA/Indie với số game, doanh thu, doanh thu/game, Metacritic TB, số game có điểm và độ phủ. Bổ sung các measure:

```dax
Games with Metacritic =
CALCULATE(
    [Total Games],
    KEEPFILTERS('dwh fact_game_snapshot'[metacritic_score] > 0)
)

Metacritic Coverage = DIVIDE([Games with Metacritic], [Total Games])
```

Logic coverage đã được kiểm chứng trong truy vấn tạm. Trên biểu đồ điểm, dùng miền 0–100 hoặc một thiết kế ghi rõ độ phóng đại; trục đang tự co quanh khoảng điểm rất hẹp làm chênh lệch nhỏ trông lớn. Giữ doanh thu và điểm thành hai biểu đồ cạnh nhau cũng dễ đọc hơn đường nối hai nhóm phân loại.

### P2 — Game thiếu reviews bị gắn “Kém hiệu quả”

Công thức thực tế `Positive Review Ratio = DIVIDE([Total Positive Reviews], [Total Reviews], 0)` trả 0 khi mẫu số bằng 0. Trong `Game Status`, nhánh `Rev = 0 && ISBLANK(PosRatio)` vì thế không nhận diện đúng game chưa có reviews.

Truy vấn đã đếm **7.291 game AAA và 27.181 game Indie không có reviews** theo điều kiện COALESCE(positive, 0) + COALESCE(negative, 0) = 0. Các game này không có cơ sở để kết luận bị đánh giá kém.

**Sửa:** Kiểm tra `COALESCE([Total Reviews], 0) = 0` trước các nhánh đánh giá và trả “Chưa đủ dữ liệu”. Nếu muốn biểu đồ tỷ lệ bỏ các điểm không có mẫu số, dùng `DIVIDE([Total Positive Reviews], [Total Reviews])` để trả BLANK. Cần tách cách đọc game miễn phí: price = 0 làm proxy doanh thu bằng 0, không có nghĩa game không tạo tiền từ nguồn khác. Ngưỡng 1 triệu USD/80% trong Game Status là quy ước, nên ghi rõ và cân nhắc điều kiện số reviews tối thiểu.

## 3. Tối ưu OS và drill-through

- **Giữ donut theo `platform_combo`:** các tổ hợp loại trừ nhau nên dùng để biểu diễn cơ cấu. Với bar Windows/Mac/Linux, một game có thể thuộc nhiều thanh; tỷ lệ hỗ trợ không bắt buộc cộng thành 100%.
- Bar OS hiện dùng ba measures, không có cột OS làm Category. Chọn thanh “Mac Games” không tương đương việc lọc cột OS = Mac để truyền sang drill-through. Nếu cần luồng này, dựng trục từ `dim_operating_system`, xử lý đường lọc qua bridge bằng measure phù hợp, rồi thêm đúng trường OS vào drill-through và tiêu đề. Có thể dùng CROSSFILTER trong measure hoặc TREATAS có kiểm soát; không bật Both toàn bộ mô hình chỉ để sửa một biểu đồ.
- Giữ Keep all filters; đã xác minh publisher và điều kiện năm được truyền. Kiểm thử thêm tier, platform_combo và genre. Chưa xác nhận trực tiếp tất cả các nhánh này trong lượt rà soát.
- Đổi tên trang thành `03 — Nhà phát hành & Nền tảng`, `04 — Chi tiết game`; cân nhắc ẩn tab trang 04 khỏi điều hướng thông thường. Có nút Back, nhưng lượt rà soát chỉ xác minh cấu hình, chưa thực thi nút này.
- Tiêu đề động nên ghi cả năm/thể loại/OS có ảnh hưởng và dùng “Tất cả nhà phát hành” khi không có bộ lọc, thay vì mặc định mọi trường hợp là “Nhiều Nhà phát hành”.
- Bỏ chữ “Khoan sâu 4 cấp” nếu chưa cấu hình hierarchy. Nếu muốn bổ sung, có thể dùng tier → publisher → game. Không dùng `dim_publisher[developer_name]` như developer của từng game: SQL chỉ lấy một developer đại diện của game đầu tiên cho mỗi publisher. Muốn phân tích developer đúng cần dimension/bridge theo game.

## 4. Bố cục đề xuất

**Trang 3:** hàng trên là tên trang, ghi chú quy tắc tier, slicer năm phát hành/thể loại/tier; dưới đó là matrix so sánh hai nhóm gồm số game, doanh thu ước tính, doanh thu/game, điểm và độ phủ. Hàng giữa là Top nhà phát hành và biểu đồ điểm/quy mô. Hàng cuối là hỗ trợ OS và cơ cấu tổ hợp nền tảng. Có thể chuyển biểu đồ theo năm thành tooltip hoặc dành vùng riêng nếu còn diện tích.

**Trang 4:** tên ngữ cảnh + Back; một hàng KPI thấp; bảng chi tiết là nội dung chính. Chỉ giữ thêm một hoặc hai biểu đồ chẩn đoán thực sự cần thiết. Hiện card và biểu đồ chiếm gần toàn trang nên thiếu chỗ cho danh sách.

Định dạng tiền thành USD với 1–2 số lẻ và đơn vị triệu/tỷ. Các card hiện hiển thị 5 chữ số lẻ, ví dụ `11.03267 tỷ`. Đổi nhãn kỹ thuật `publisher_tier`, `genre_name`, `platform_combo` thành tiếng Việt. Dùng cùng màu AAA/Indie ở mọi biểu đồ; giảm tiêu đề phụ tự sinh liệt kê toàn bộ tên measure. Thêm ghi chú: “Ước tính = (reviews tích cực + tiêu cực) × 30 × giá tại snapshot; không phải doanh thu kế toán”.

Hiệu năng: chưa đo bằng Performance Analyzer nên không kết luận dashboard chậm. Sau khi hoàn thiện yêu cầu, đo theo từng visual; ưu tiên giảm số visual không cần thiết và giới hạn scatter ở trang tổng hợp, nhưng giữ bảng danh sách đầy đủ ở trang chi tiết. Chỉ chuyển tính doanh thu theo game sang ETL khi phép đo cho thấy SUMX là điểm nghẽn và hệ số 30 được chốt cố định.

## 5. Checklist nghiệm thu sau chỉnh sửa

1. Trang 3 nhìn trực tiếp được cả số game, doanh thu và Metacritic cho AAA/Indie trong cùng ngữ cảnh lọc.
2. Tỷ trọng hai nhóm cộng 100% khi mẫu số chỉ bao gồm hai nhóm; khi tính cả Unknown, thể hiện rõ nhóm này trong mẫu số.
3. Có số mẫu và độ phủ cạnh điểm Metacritic; dữ liệu thiếu không hiển thị thành điểm 0 hoặc “kém hiệu quả”.
4. Top 15 chỉ loại đúng dummy/placeholder; không còn danh sách loại theo tên chứa Unknown.
5. Từ publisher, tier và platform_combo → Trang 4: KPI và danh sách khớp ngữ cảnh; kiểm tra giữ năm và thể loại, rồi kiểm tra nút Back.
6. Số AppID phân biệt trong bảng chi tiết bằng `[Total Games]` khi không có lọc Top N; kiểm tra riêng trường hợp tên game trùng.
7. Số game theo tổ hợp OS cộng bằng tổng game; số hỗ trợ OS độc lập có thể chồng lấp. Nếu thêm drill-through từng OS, kiểm thử từng hệ điều hành và đa lựa chọn.
8. Nhãn năm phản ánh năm phát hành; không gọi proxy theo nhóm năm phát hành là doanh thu phát sinh trong năm.
9. Bỏ hoặc triển khai đúng lời hứa “4 cấp”; không dùng developer đại diện của publisher để quy toàn bộ game cho developer đó.
10. Sau khi sửa xong mới lưu PBIX và xuất lại PBIT. PBIT hiện có timestamp 08/11/2026 và chỉ chứa trang Overview; chưa phản ánh các trang vừa dựng.

## Nguồn kỹ thuật

- [Microsoft — CALCULATE và hành vi ghi đè filter](https://learn.microsoft.com/en-us/dax/calculate-function-dax/).
- [Microsoft — Drillthrough và trường trong visual nguồn](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-drillthrough).
- [Microsoft — Hướng dẫn lọc hai chiều và CROSSFILTER trong measure](https://learn.microsoft.com/en-us/power-bi/guidance/relationships-bidirectional-filtering).
- [Microsoft — INFO.VIEW.MEASURES](https://learn.microsoft.com/en-us/dax/info-view-measures-function-dax).

Cấu hình PBIR đã đọc được lưu cục bộ trong `output/dashboard_review_20261114/Report/definition/` để đối chiếu; thư mục output nằm trong gitignore. File PBIT cũ chỉ được dùng xác định độ cập nhật, không dùng thay thế model đang mở khi kết luận công thức DAX.
