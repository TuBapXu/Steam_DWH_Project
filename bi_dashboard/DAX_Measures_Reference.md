# Tài liệu Tham chiếu Hệ thống DAX Measures — Steam Games DWH

Tài liệu này tổng hợp toàn bộ công thức DAX chuẩn hóa cho Semantic Model (`Steam_Template.pbix`), đảm bảo tuân thủ đúng nguyên lý **Star Schema Modeling** (`Single Cross-filter Direction` từ Dimension $\rightarrow$ Fact và xử lý các bản ghi kỹ thuật `key = 0`).

---

## 1. Lưu ý chuẩn Modeling khi viết DAX

1. **Đếm chiều qua Khóa ngoại trên Fact (`fact_game_snapshot`):**
   Vì mô hình nối quan hệ 1-Nhiều (`1:*`, lọc đơn `Single`), các slicer từ `dim_date`, `dim_platform`, hay `dim_game_genres` chỉ lọc được xuống `fact_game_snapshot` chứ không lọc ngược lên `dim_publisher`. Do đó, `Total Publishers` phải đếm trên `'dwh fact_game_snapshot'[publisher_key]`.
2. **Xử lý Dummy Keys (`key = 0`):**
   - `publisher_key = 0` (`"Unknown Publisher"`, tier `"Unknown"`): Dùng `<> 0` trong các measure đếm Nhà phát hành thực tế.
   - `date_key = 0` (`0001-01-01` $\rightarrow$ `1900-01-01`): Dùng `<> 0` khi tính các chỉ số phát hành theo thời gian thực.

---

## 2. Bộ DAX Measures Nền tảng & Mở rộng cho Trang 3

### A. Nhóm 1: Core Volume & Phân tầng AAA vs Indie
```dax
// Tổng số tựa game duy nhất
Total Games = DISTINCTCOUNT('dwh fact_game_snapshot'[game_key])

// Tổng số game có ngày phát hành xác định (loại bỏ date_key = 0)
Released Games = CALCULATE([Total Games], 'dwh dim_date'[date_key] <> 0)

// Đếm số Nhà phát hành thực tế (tương thích mọi Slicer đa chiều)
Total Publishers = 
CALCULATE(
    DISTINCTCOUNT('dwh fact_game_snapshot'[publisher_key]),
    'dwh dim_publisher'[publisher_key] <> 0
)

// Số lượng & Tỷ trọng Game Miễn phí vs Trả phí
Free Games = CALCULATE([Total Games], 'dwh fact_game_snapshot'[price] = 0)
Paid Games = CALCULATE([Total Games], 'dwh fact_game_snapshot'[price] > 0)
% Free Games = DIVIDE([Free Games], [Total Games], 0)

// Số lượng & Tỷ trọng theo Phân tầng Nhà phát hành (AAA vs Indie)
AAA Games = CALCULATE([Total Games], 'dwh dim_publisher'[publisher_tier] = "AAA")
Indie Games = CALCULATE([Total Games], 'dwh dim_publisher'[publisher_tier] = "Indie")
% AAA Games = DIVIDE([AAA Games], [Total Games], 0)
% Indie Games = DIVIDE([Indie Games], [Total Games], 0)
```

### B. Nhóm 2: Commercial, Pricing & Doanh số ước tính (Boxleiter)
```dax
// Giá bán & Giảm giá
Avg Price = AVERAGE('dwh fact_game_snapshot'[price])
Avg Paid Price = CALCULATE(AVERAGE('dwh fact_game_snapshot'[price]), 'dwh fact_game_snapshot'[price] > 0)
Max Price = MAX('dwh fact_game_snapshot'[price])
Avg Discount = AVERAGE('dwh fact_game_snapshot'[discount])

// Doanh số ước tính (Boxleiter Formula: Reviews * 30 * Price)
Estimated Revenue = 
SUMX(
    'dwh fact_game_snapshot',
    (COALESCE('dwh fact_game_snapshot'[positive_reviews], 0) + COALESCE('dwh fact_game_snapshot'[negative_reviews], 0))
    * 30 
    * COALESCE('dwh fact_game_snapshot'[price], 0)
)

// Doanh số ước tính tách riêng AAA vs Indie (Dùng cho KPI Cards Trang 3)
AAA Revenue = CALCULATE([Estimated Revenue], 'dwh dim_publisher'[publisher_tier] = "AAA")
Indie Revenue = CALCULATE([Estimated Revenue], 'dwh dim_publisher'[publisher_tier] = "Indie")

// Tỷ trọng đóng góp Doanh thu
% AAA Revenue Share = DIVIDE([AAA Revenue], [Estimated Revenue], 0)
% Indie Revenue Share = DIVIDE([Indie Revenue], [Estimated Revenue], 0)

// Doanh thu trung bình trên mỗi tựa game (Hiệu suất thương mại)
Avg Revenue per Game = DIVIDE([Estimated Revenue], [Total Games], 0)

// Tỷ trọng đóng góp trong bối cảnh đang chọn (Dùng cho Bảng xếp hạng Top NPH)
% Share of Total Revenue = 
DIVIDE(
    [Estimated Revenue],
    CALCULATE(
        [Estimated Revenue],
        ALLSELECTED('dwh dim_publisher')
    ),
    0
)

% Share of Total Games = 
DIVIDE(
    [Total Games],
    CALCULATE(
        [Total Games],
        ALLSELECTED('dwh dim_publisher')
    ),
    0
)
```

### C. Nhóm 3: Reviews, Metacritic & Engagement
```dax
// Tương tác & Giờ chơi
Peak CCU = MAX('dwh fact_game_snapshot'[peak_ccu])
Avg Peak CCU = AVERAGE('dwh fact_game_snapshot'[peak_ccu])
Avg Playtime (Hours) = DIVIDE(AVERAGE('dwh fact_game_snapshot'[average_playtime]), 60, 0)
Total Playtime (Hours) = DIVIDE(SUM('dwh fact_game_snapshot'[average_playtime]), 60, 0)

// Đánh giá người dùng
Total Positive Reviews = SUM('dwh fact_game_snapshot'[positive_reviews])
Total Negative Reviews = SUM('dwh fact_game_snapshot'[negative_reviews])
Total Reviews = [Total Positive Reviews] + [Total Negative Reviews]
Positive Review Ratio = DIVIDE([Total Positive Reviews], [Total Reviews], 0)

// Điểm đánh giá trung bình
Avg Metacritic Score = AVERAGE('dwh fact_game_snapshot'[metacritic_score])
Avg User Score = AVERAGE('dwh fact_game_snapshot'[user_score])

// So sánh điểm Metacritic & Tỷ lệ hài lòng giữa AAA vs Indie
AAA Avg Metacritic = CALCULATE([Avg Metacritic Score], 'dwh dim_publisher'[publisher_tier] = "AAA")
Indie Avg Metacritic = CALCULATE([Avg Metacritic Score], 'dwh dim_publisher'[publisher_tier] = "Indie")
AAA Positive Ratio = CALCULATE([Positive Review Ratio], 'dwh dim_publisher'[publisher_tier] = "AAA")
Indie Positive Ratio = CALCULATE([Positive Review Ratio], 'dwh dim_publisher'[publisher_tier] = "Indie")

// Số lượng game có chấm điểm Metacritic (Đo độ phủ mẫu)
Games with Metacritic = CALCULATE([Total Games], NOT(ISBLANK('dwh fact_game_snapshot'[metacritic_score])))
```

### D. Nhóm 4: Cơ cấu Hệ điều hành & Nền tảng (Platform & OS)
```dax
// Số lượng game hỗ trợ từng Hệ điều hành độc lập (từ dim_platform)
Windows Games = CALCULATE([Total Games], 'dwh dim_platform'[is_windows] = TRUE())
Mac Games = CALCULATE([Total Games], 'dwh dim_platform'[is_mac] = TRUE())
Linux Games = CALCULATE([Total Games], 'dwh dim_platform'[is_linux] = TRUE())

// Tỷ lệ % hỗ trợ trên tổng số game
% Windows Support = DIVIDE([Windows Games], [Total Games], 0)
% Mac Support = DIVIDE([Mac Games], [Total Games], 0)
% Linux Support = DIVIDE([Linux Games], [Total Games], 0)

// Tỷ lệ game hỗ trợ đa nền tảng hoàn toàn (Win + Mac + Linux)
Cross-Platform Games = CALCULATE([Total Games], 'dwh dim_platform'[platform_combo] = "Cross-platform")
% Cross-Platform = DIVIDE([Cross-Platform Games], [Total Games], 0)
```
*(Nếu dùng `dim_operating_system` và `bridge_game_platform` trong mô hình, có thể bổ sung:)*
```dax
OS Total Games = 
CALCULATE(
    [Total Games],
    CROSSFILTER('dwh bridge_game_platform'[game_key], 'dwh dim_game'[game_key], Both)
)
```

### E. Nhóm 5: Xếp hạng Động (Drill-down Ranking) & Tiêu đề Drill-through
```dax
// Thứ hạng Doanh thu tự động cập nhật theo cấp độ Drill-down trên Publisher Hierarchy
Publisher Revenue Rank = 
IF(
    ISINSCOPE('dwh dim_publisher'[developer_name]),
    RANKX(ALLSELECTED('dwh dim_publisher'[developer_name]), [Estimated Revenue], , DESC, DENSE),
    IF(
        ISINSCOPE('dwh dim_publisher'[publisher_name]),
        RANKX(ALLSELECTED('dwh dim_publisher'[publisher_name]), [Estimated Revenue], , DESC, DENSE),
        IF(
            ISINSCOPE('dwh dim_publisher'[publisher_tier]),
            RANKX(ALLSELECTED('dwh dim_publisher'[publisher_tier]), [Estimated Revenue], , DESC, DENSE)
        )
    )
)

// Thứ hạng theo Số lượng Game
Publisher Games Rank = 
IF(
    ISINSCOPE('dwh dim_publisher'[publisher_name]),
    RANKX(ALLSELECTED('dwh dim_publisher'[publisher_name]), [Total Games], , DESC, DENSE)
)

// Tiêu đề động cho trang Drill-through (Trang 4)
Drillthrough Header Title = 
VAR SelectedPub = SELECTEDVALUE('dwh dim_publisher'[publisher_name], "Nhiều Nhà phát hành")
VAR SelectedTier = SELECTEDVALUE('dwh dim_publisher'[publisher_tier], "")
VAR SelectedPlatform = SELECTEDVALUE('dwh dim_platform'[platform_combo], "")
RETURN
"Chi tiết tựa game — " & SelectedPub & 
IF(SelectedTier <> "", " (" & SelectedTier & ")", "") &
IF(SelectedPlatform <> "", " | Nền tảng: " & SelectedPlatform, "")
```
