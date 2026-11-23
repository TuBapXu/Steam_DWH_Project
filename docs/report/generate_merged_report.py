# -*- coding: utf-8 -*-
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

def generate_merged_report():
    input_path = r'C:\Users\HP\.gemini\antigravity\brain\c39fa65f-13ba-4243-8c24-02173084f78b\.user_uploaded\media_1795410292051_d94cdd01.docx'
    output_path = r'c:\Users\HP\Desktop\C++CodeLearn\HK1-2627\HTTT_Phuc_Vu_Tri_Tue_Kinh_Doanh\mini-project\Steam_DWH_Project\Mini-Project_Report_Final_V2.docx'
    
    img_dash5 = 'dash5_clean.png'
    img_dash6 = 'dash6_clean.png'

    doc = docx.Document(input_path)
    PRIMARY_COLOR = RGBColor(15, 71, 97)

    # 1. Grab paragraph objects FIRST before any modification
    p_ch3 = None
    p_ch4 = None
    p_ch4_strat = None
    p_ch5 = None
    p_ch5_eval = None

    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt == 'CHƯƠNG 3: THIẾT KẾ VÀ TRIỂN KHAI HỆ THỐNG DASHBOARD PHÂN TÍCH':
            p_ch3 = p
        elif txt == 'CHƯƠNG 4: PHÂN TÍCH INSIGHT THƯƠNG MẠI & ĐỀ XUẤT CHIẾN LƯỢC':
            p_ch4 = p
        elif txt.startswith('Đề xuất chiến lược hành động dựa trên dữ liệu (Data-driven'):
            p_ch4_strat = p
        elif txt == 'CHƯƠNG 5: KẾT LUẬN & HƯỚNG PHÁT TRIỂN':
            p_ch5 = p
        elif txt.startswith('Bảng 5.1 Đánh giá mức độ hoàn thành của các thành'):
            p_ch5_eval = p

    print('Grabbed paragraph objects successfully.')

    def helper_bullet(target_p, text, bold_prefix=''):
        p = target_p.insert_paragraph_before(style='List Paragraph')
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        r_b = p.add_run('•  ')
        r_b.font.name = 'Times New Roman'
        r_b.font.size = Pt(12)
        r_b.font.bold = True
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(12)
            r_pre.font.bold = True
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)
        return p

    def helper_heading(target_p, text, style_name, size, bold=True, italic=False):
        p = target_p.insert_paragraph_before(style=style_name)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = PRIMARY_COLOR
        return p

    def helper_text(target_p, text, italic=False):
        p = target_p.insert_paragraph_before()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.italic = italic
        return p

    def helper_image(target_p, img_path, caption):
        if os.path.exists(img_path):
            p_img = target_p.insert_paragraph_before()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(8)
            p_img.paragraph_format.space_after = Pt(4)
            run_img = p_img.add_run()
            run_img.add_picture(img_path, width=Inches(6.3))

            p_cap = target_p.insert_paragraph_before()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(8)
            r_cap = p_cap.add_run(caption)
            r_cap.font.name = 'Times New Roman'
            r_cap.font.size = Pt(10.5)
            r_cap.font.italic = True
            r_cap.font.bold = True

    # 1. INSERTION BEFORE CHƯƠNG 3 (End of Chapter 2)
    helper_heading(p_ch3, 'Nhóm chỉ số Giám sát Vận hành & Phân tích Tương tác Đa chiều (Observability & Interactive DAX):', 'Heading 3', 12, bold=True, italic=True)
    helper_bullet(p_ch3, 'Thước đo sử dụng hàm SELECTEDVALUE để bắt chính xác định danh đợt chạy ETL đang được người dùng bấm chọn trong bảng Audit Log; tự động trả về giá trị mặc định khi chưa có lựa chọn.', 'Selected Run Log ID: ')
    helper_bullet(p_ch3, 'Thước đo truy vấn thông điệp chẩn đoán tự động từ tầng AI / Metadata cho đợt chạy tương ứng, phục vụ việc xuất khuyến nghị và giải thích nguyên nhân sự cố tức thì.', 'Run AI Diagnostic Message: ')
    helper_bullet(p_ch3, 'Đo lường tổng số lượt chạy pipeline trên toàn hệ thống nhưng được bọc trong hàm CALCULATE(..., ALL(vw_etl_monitoring)) nhằm cố định số liệu toàn cục, không bị lọc theo dòng khi click vào bảng nhật ký chạy.', 'Total ETL Runs (Audit Unfiltered): ')
    helper_bullet(p_ch3, 'Đo lường tỷ lệ phần trăm các phiên nạp dữ liệu hoàn tất thành công (status = SUCCESS) trên tổng số lượt thực thi, phản ánh mức độ sẵn sàng và độ tin cậy của đường ống dữ liệu.', 'Pipeline Success Rate (%): ')
    helper_bullet(p_ch3, 'Thước đo tổng hợp doanh thu theo phương pháp Boxleiter tích hợp trong cây phân tích (AI Decomposition Tree), cho phép thuật toán AI tự động tìm kiếm thuộc tính đóng góp cao nhất (High-value contribution split).', 'Decomposition Tree Revenue Metric: ')

    # 2. INSERTION BEFORE CHƯƠNG 4 (Dashboard 5 & Dashboard 6 in Chapter 3)
    # Dash 5
    helper_heading(p_ch4, 'Dashboard 5 — Giám sát Đường ống ETL & Kiểm soát Chất lượng Dữ liệu (Data Observability & Pipeline Health)', 'Heading 2', 13, bold=True)
    helper_heading(p_ch4, 'Mục tiêu phân tích & Đối tượng sử dụng', 'Heading 3', 12, bold=True, italic=True)
    helper_text(p_ch4, 'Dashboard 5 được thiết kế như một trung tâm chỉ huy dữ liệu thời gian thực (Data Observability Hub), cung cấp khả năng giám sát toàn diện tình trạng sức khỏe của đường ống dữ liệu, kiểm soát khối lượng bản ghi xử lý, đo lường thời gian thực thi đối chiếu với ngưỡng SLA cam kết và kiểm soát chất lượng dữ liệu thông qua bộ kiểm thử tự động của dbt.')
    helper_text(p_ch4, 'Đối tượng sử dụng chính: Đội ngũ Kỹ sư Dữ liệu (Data Engineers), Quản trị viên Cơ sở Dữ liệu (DBA) và Trưởng nhóm Kỹ thuật (Data Leads).')
    helper_heading(p_ch4, 'Bố cục không gian & Dải chỉ số then chốt (KPI Cards)', 'Heading 3', 12, bold=True, italic=True)
    helper_image(p_ch4, img_dash5, 'Hình 3.5. Giao diện Dashboard 5 — Giám sát Đường ống ETL và Kiểm soát Chất lượng Dữ liệu')
    helper_bullet(p_ch4, 'Gồm 4 thẻ chỉ số cố định trên đỉnh màn hình: Số lần ETL (11 lượt chạy), Tỷ lệ thành công (81.82%), Tổng test dbt passed (91 bài kiểm thử, đạt 100%), và Tổng bản ghi xử lý (376.905 dòng). Dải KPI này được cố định toàn cục bằng DAX ALL().', 'Dải KPI Vĩ mô Toàn cục (Top Cards): ')
    helper_bullet(p_ch4, 'Thẻ đa hàng (Multi-row Card) hiển thị chi tiết đợt nạp mới nhất (mã run_id, thời điểm hoàn tất, số dòng thêm mới inserted, số dòng cập nhật updated, số dòng lỗi rejected). Bên dưới là Thẻ văn bản Chẩn đoán AI (AI Diagnostic Card) tự động giải thích nguyên nhân vận hành và đưa ra khuyến nghị xử lý sự cố.', 'Khối Kiểm tra Đợt chạy Hiện tại & Chẩn đoán AI (Cột trái): ')
    helper_bullet(p_ch4, 'Biểu đồ cột chồng (Stacked Column Chart) so sánh cơ cấu bản ghi nạp qua các tháng (Tháng 10 và Tháng 11), trực quan hóa số lượng bản ghi mới, bản ghi cập nhật và bản ghi bất thường.', 'Biểu đồ Đối chiếu Thể tích Dữ liệu (Cột giữa): ')
    helper_bullet(p_ch4, 'Biểu đồ đường (Line Chart) theo dõi thời gian thực thi (duration_sec) của từng đợt chạy, làm nổi bật sự khác biệt giữa Full Load (hơn 1.000 giây) và Incremental Load (3 – 25 giây), đối chiếu với ngưỡng SLA cam kết 60 giây.', 'Biểu đồ Giám sát Thời lượng & SLA (Cột phải): ')
    helper_bullet(p_ch4, 'Bảng chi tiết toàn bộ lịch sử chạy ETL (Audit Log Trail Table) ghi nhận đầy đủ run_id, thời gian bắt đầu, thời gian kết thúc, chế độ chạy (full / incremental), phương thức kích hoạt và trạng thái hoàn tất.', 'Nhật ký Truy vết Chi tiết (Khu vực đáy): ')
    helper_heading(p_ch4, 'Phân tích chi tiết các biểu đồ trực quan & Cơ chế tương tác (Interactivity)', 'Heading 3', 12, bold=True, italic=True)
    helper_bullet(p_ch4, 'Khi người dùng click chọn một đợt chạy bất kỳ trong bảng Audit Log (ví dụ: đợt nạp thử nghiệm prod_demo_20261122_inc_006 hoặc sự cố nạp LEGACY_5), biểu đồ cột thể tích, biểu đồ thời lượng và thẻ chẩn đoán AI sẽ lập tức lọc sâu để phân tích chi tiết riêng cho lần chạy đó.', 'Tương tác Khoan sâu Sự cố (Selective Drill-down): ')
    helper_bullet(p_ch4, 'Nhờ tích hợp thước đo DAX ALL() kết hợp tính năng Edit Interactions -> None trong Power BI, dải 4 thẻ KPI vĩ mô trên đỉnh hoàn toàn không bị biến dạng khi tương tác với bảng, bảo đảm tính toàn vẹn của chỉ số quản trị cấp cao.', 'Bảo toàn Ngữ cảnh Toàn cục (Global Context Preservation): ')
    helper_heading(p_ch4, 'Đúc kết Insight vận hành & Ý nghĩa thực tiễn', 'Heading 3', 12, bold=True, italic=True)
    helper_bullet(p_ch4, 'Quy trình nạp đắp thêm (Incremental Load) giúp tiết kiệm đến hơn 98% thời gian vận hành so với Full Load ban đầu (chỉ mất 3 – 25 giây thay vì gần 20 phút), chứng minh tính tối ưu vượt trội của kiến trúc Data Warehouse.', 'Hiệu năng đường ống vượt trội: ')
    helper_bullet(p_ch4, '100% các bài kiểm thử dbt (91/91) đều vượt qua thành công, tỷ lệ bản ghi rejected được cô lập triệt để tại bảng trung gian, ngăn chặn hoàn toàn việc làm bẩn dữ liệu của các bảng Fact và Dimension phục vụ kinh doanh.', 'Độ tin cậy dữ liệu tuyệt đối: ')

    # Dash 6
    helper_heading(p_ch4, 'Dashboard 6 — Trợ lý AI Copilot & Phân tích Nghiệp vụ Kinh doanh (AI-Assisted Business Analytics)', 'Heading 2', 13, bold=True)
    helper_heading(p_ch4, 'Mục tiêu phân tích & Đối tượng sử dụng', 'Heading 3', 12, bold=True, italic=True)
    helper_text(p_ch4, 'Dashboard 6 đóng vai trò là cây cầu nối thông minh giữa dữ liệu phân tích vĩ mô và quyết định kinh doanh chiến lược, kết hợp giữa mô hình phân rã đa chiều bằng AI (Decomposition Tree) và hệ thống Trợ lý ảo AI Copilot tích hợp mô hình ngôn ngữ lớn (LLM) để tự động hóa việc đưa ra nhận định và khuyến nghị hành động.')
    helper_text(p_ch4, 'Đối tượng sử dụng chính: Giám đốc Điều hành (C-Level Executives), Giám đốc Chiến lược (CSO), Quản lý Sản phẩm (Product Leads) và các Quỹ đầu tư mạo hiểm.')
    helper_heading(p_ch4, 'Bố cục không gian & Hệ thống trực quan', 'Heading 3', 12, bold=True, italic=True)
    helper_image(p_ch4, img_dash6, 'Hình 3.6. Giao diện Dashboard 6 — Trợ lý AI Copilot và Phân tích Nghiệp vụ Kinh doanh')
    helper_bullet(p_ch4, 'Slicer dạng tab trên đỉnh cho phép chuyển đổi tức thì giữa 4 chủ đề phân tích cốt lõi (Trang 1: Tổng quan & Mùa vụ; Trang 2: Hiệu suất & Chiến lược giá; Trang 3: Nhà phát hành & Nền tảng; Trang 4: Chi tiết game & Pareto).', 'Thanh Điều hướng Chủ đề Nghiệp vụ (Top Slicer): ')
    helper_bullet(p_ch4, 'Gồm Thẻ "INSIGHT" (giải phẫu hiện trạng, cơ cấu doanh thu và điểm rơi thị trường) và Thẻ "ĐỀ XUẤT HÀNH ĐỘNG" (3 khuyến nghị thực thi cụ thể cho nhà quản lý).', 'Cụm Nhận định & Hành động Tự động (Cột trái): ')
    helper_bullet(p_ch4, 'Nút bấm tương tác Web URL dẫn trực tiếp đến ứng dụng Steam Copilot Web App (chạy tại http://localhost:5000), kết nối mô hình Gemini AI để người dùng trò chuyện và truy vấn dữ liệu tự nhiên theo ngữ cảnh.', 'Cổng Tương tác Trợ lý Đàm thoại AI (Action Button): ')
    helper_bullet(p_ch4, 'Visual AI Decomposition Tree trực quan hóa đường đi của hơn 38 tỷ USD doanh thu ước tính toàn sàn Steam, phân tách theo từng cấp bậc: Phân khúc Nhà phát hành (Indie vs AAA) → Thể loại (Action, Adventure, RPG...) → Tổ hợp Nền tảng (Windows Only, Win & Mac, Cross-platform...) → Tựa game cụ thể.', 'Cây Phân tích Đóng góp Doanh thu AI (Cột phải): ')
    helper_heading(p_ch4, 'Cơ chế tương tác & Giá trị phân tích của Cây Phân tích Phân rã (Decomposition Tree)', 'Heading 3', 12, bold=True, italic=True)
    helper_bullet(p_ch4, 'Visual Decomposition Tree ứng dụng thuật toán AI của Power BI để tự động xếp hạng và gợi ý chiều không gian có mức độ ảnh hưởng lớn nhất đến doanh thu, giúp người dùng không bỏ sót các cơ hội kinh doanh tiềm ẩn.', 'Khám phá Tự động Nhánh Giá trị Cao (AI-Powered High Value Split): ')
    helper_bullet(p_ch4, 'Người dùng có thể tự do mở rộng (expand) hoặc thu gọn (collapse) bất kỳ nhánh cây nào để tìm câu trả lời cho hiện tượng doanh thu: Ví dụ vì sao phân khúc Indie lại đạt gần 20 tỷ USD? Nhánh cây lập tức bóc tách rõ phần lớn đóng góp đến từ thể loại Adventure/Action trên hệ điều hành Windows Only.', 'Giải phẫu Đóng góp Đa chiều Không ràng buộc: ')
    helper_heading(p_ch4, 'Đúc kết Insight trọng tâm & Giá trị thực tiễn của Trợ lý AI', 'Heading 3', 12, bold=True, italic=True)
    helper_bullet(p_ch4, 'Hệ thống loại bỏ hoàn toàn độ trễ thông tin giữa người làm dữ liệu và cấp lãnh đạo; các khuyến nghị chiến lược được mô hình AI tổng hợp tức thì ngay bên cạnh biểu đồ, giúp việc ra quyết định trở nên nhanh chóng và có căn cứ xác thực.', 'Rút ngắn chu trình từ Dữ liệu đến Quyết định: ')
    helper_bullet(p_ch4, 'Cổng Chatbox AI mở rộng cung cấp khả năng hỏi đáp chuyên sâu (Ad-hoc Query) bằng ngôn ngữ tự nhiên, giúp người dùng không cần am hiểu kỹ thuật SQL hay DAX vẫn có thể khai phá dữ liệu hiệu quả.', 'Dân chủ hóa dữ liệu toàn diện (Data Democratization): ')

    # 3. INSERTION BEFORE ĐỀ XUẤT CHIẾN LƯỢC (Chapter 4 Finding 5 & 6)
    helper_heading(p_ch4_strat, 'Dashboard 5 — Giám sát Sức khỏe Đường ống ETL & Độ tin cậy Dữ liệu', 'Heading 3', 12, bold=True, italic=True)
    helper_bullet(p_ch4_strat, 'Việc chuyển từ Full Load ban đầu sang chiến lược Incremental Load giúp giảm thời gian nạp từ 19.5 phút xuống chỉ còn 3 – 25 giây cho mỗi mẻ dữ liệu, tiết kiệm hơn 98% tài nguyên tính toán và băng thông mạng.', 'Hiệu năng vận hành và Tối ưu hóa tài nguyên: ')
    helper_bullet(p_ch4_strat, 'Toàn bộ 91 bài kiểm thử dbt đạt tỷ lệ hoàn thành 100%, bảo đảm không có khóa ngoại mồ côi, không trùng lặp khóa chính và tính nhất quán tuyệt đối giữa 3 tầng Staging - Cleaned - Fact.', 'Chất lượng và Độ tin cậy dữ liệu DWH: ')
    helper_bullet(p_ch4_strat, 'Cơ chế ghi log chi tiết và giao dịch cơ sở dữ liệu (Database Transaction) tự động kích hoạt Rollback khi phát sinh sự cố mạng, bảo toàn tính toàn vẹn dữ liệu và hỗ trợ chẩn đoán nguyên nhân gốc rễ tự động qua AI.', 'Khả năng chịu lỗi và tự phục hồi: ')

    helper_heading(p_ch4_strat, 'Dashboard 6 — Cây giải phẫu Doanh thu (AI Decomposition Tree) & Khuyến nghị Chiến lược Tự động', 'Heading 3', 12, bold=True, italic=True)
    helper_bullet(p_ch4_strat, 'Cây phân rã AI chứng minh một phát hiện quan trọng: Nhóm game Indie ở thể loại Adventure và Action trên nền tảng Windows Only đóng góp doanh thu áp đảo (gần 14 tỷ USD), vượt qua nhiều dự án bom tấn AAA ở các thể loại truyền thống.', 'Quy luật Tập trung Giá trị từ AI Tree: ')
    helper_bullet(p_ch4_strat, 'Trợ lý AI tự động nhận diện và cảnh báo sớm nguy cơ "Bào mòn Uy tín Thương hiệu" (Brand Equity Erosion) khi nhiều tựa game bom tấn đạt doanh thu rất lớn nhưng tỷ lệ đánh giá tích cực lại rơi xuống mức báo động (< 50%).', 'Cảnh báo Rủi ro Thương mại từ AI Copilot: ')

    # 4. INSERTION BEFORE CHƯƠNG 5 (Chapter 4 Strategy Operations)
    helper_heading(p_ch5, 'Chiến lược Tối ưu hóa Vận hành & Quản trị Dữ liệu Doanh nghiệp (Data Governance & Operations)', 'Heading 3', 12, bold=True, italic=True)
    helper_bullet(p_ch5, 'Thiết lập cơ chế kích hoạt pipeline nạp gia tăng (Incremental) định kỳ 15 – 30 phút một lần để cung cấp dữ liệu gần thời gian thực (Near Real-time) cho các phòng ban kinh doanh.', 'Tự động hóa chu kỳ nạp dữ liệu: ')
    helper_bullet(p_ch5, 'Áp dụng ngưỡng cảnh báo SLA tự động (ví dụ: cảnh báo tức thì khi thời gian chạy vượt quá 60 giây hoặc tỷ lệ bản ghi rejected vượt ngưỡng 1%) thông qua webhook kết nối Teams/Slack.', 'Hệ thống cảnh báo ngưỡng SLA chủ động: ')
    helper_bullet(p_ch5, 'Ứng dụng Trợ lý AI Copilot làm công cụ tra cứu dữ liệu hàng ngày cho đội ngũ kinh doanh, giảm thiểu sự phụ thuộc vào các báo cáo ad-hoc thủ công từ phòng dữ liệu.', 'Chuẩn hóa quy trình phân tích tự phục vụ (Self-service BI): ')

    # 5. INSERTION AT CHAPTER 5 EVALUATION
    if p_ch5_eval:
        helper_bullet(p_ch5_eval, 'Xây dựng thành công hệ thống giám sát đường ống dữ liệu toàn diện (Dashboard 5) với đầy đủ chỉ số SLA, chất lượng dữ liệu và cơ chế chẩn đoán lỗi tự động bằng AI.', 'Hoàn thành trọn vẹn Module Giám sát Dữ liệu (Data Observability): ')
        helper_bullet(p_ch5_eval, 'Tích hợp thành công visual AI Decomposition Tree và mô hình ngôn ngữ lớn (Gemini AI) thông qua ứng dụng Steam Copilot Web App (Dashboard 6), tạo bước đột phá trong trải nghiệm người dùng.', 'Ứng dụng Trí tuệ Nhân tạo vào Business Intelligence: ')

    # Save to disk
    doc.save(output_path)
    print(f'Successfully merged and saved complete report to: {output_path}')

if __name__ == '__main__':
    generate_merged_report()
