# -*- coding: utf-8 -*-
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def create_guide_docx():
    doc = docx.Document()

    # Set page margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    PRIMARY_COLOR = RGBColor(15, 71, 97)    # #0F4761 (Màu chuẩn của báo cáo nhóm 9)
    ACCENT_COLOR = RGBColor(192, 57, 43)    # Đỏ gạch làm nổi bật vị trí
    BOX_BG = 'EBF2F7'                       # Nền hộp hướng dẫn xanh nhạt
    BORDER_COLOR = '0F4761'

    # Configure Heading Styles
    for h_name, size, is_bold, is_italic in [
        ('Heading 1', 14, True, False),
        ('Heading 2', 13, True, False),
        ('Heading 3', 12, True, True),
    ]:
        style = doc.styles[h_name]
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(size)
        font.bold = is_bold
        font.italic = is_italic
        font.color.rgb = PRIMARY_COLOR

    def add_doc_title(title, subtitle):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(title)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = PRIMARY_COLOR
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        p2 = doc.add_paragraph()
        p2.paragraph_format.space_after = Pt(14)
        run2 = p2.add_run(subtitle)
        run2.font.name = 'Times New Roman'
        run2.font.size = Pt(11)
        run2.font.italic = True
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def add_loc_box(part_num, part_title, find_keyword, insert_before, action_note):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{BOX_BG}"/>')
        cell._tc.get_or_add_tcPr().append(shd)
        
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:top w:val="none"/>'
            f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{BORDER_COLOR}"/>'
            f'<w:bottom w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'</w:tcBorders>'
        )
        cell._tc.get_or_add_tcPr().append(borders)

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15

        r_title = p.add_run(f'📍 {part_num}: {part_title.upper()}\n')
        r_title.font.name = 'Times New Roman'
        r_title.font.size = Pt(12)
        r_title.font.bold = True
        r_title.font.color.rgb = PRIMARY_COLOR

        r_f1 = p.add_run('🔍 Bước 1 (Tìm vị trí): ')
        r_f1.font.name = 'Times New Roman'
        r_f1.font.bold = True
        r_f2 = p.add_run(f'Trong file báo cáo, nhấn Ctrl + F và tìm đoạn:\n"{find_keyword}"\n')
        r_f2.font.name = 'Times New Roman'
        r_f2.font.italic = True

        r_b1 = p.add_run('📌 Bước 2 (Điểm đặt con trỏ chuột): ')
        r_b1.font.name = 'Times New Roman'
        r_b1.font.bold = True
        r_b2 = p.add_run(f'Đặt con trỏ chuột NGAY SAU đoạn văn trên (đứng trước tiêu đề "{insert_before}").\n')
        r_b2.font.name = 'Times New Roman'

        r_a1 = p.add_run('📋 Bước 3 (Hành động): ')
        r_a1.font.name = 'Times New Roman'
        r_a1.font.bold = True
        r_a1.font.color.rgb = ACCENT_COLOR
        r_a2 = p.add_run(f'{action_note}\n')
        r_a2.font.name = 'Times New Roman'

        p_spacer = doc.add_paragraph()
        p_spacer.paragraph_format.space_before = Pt(0)
        p_spacer.paragraph_format.space_after = Pt(4)

    def add_h1(text):
        p = doc.add_paragraph(text, style='Heading 1')
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)

    def add_h2(text):
        p = doc.add_paragraph(text, style='Heading 2')
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)

    def add_h3(text):
        p = doc.add_paragraph(text, style='Heading 3')
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(3)

    def add_p(text, bold_prefix='', italic=False):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(12)
            r_pre.font.bold = True
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)
        r.font.italic = italic

    def add_bullet(text, bold_prefix=''):
        p = doc.add_paragraph(style='List Paragraph')
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        r_bullet = p.add_run('•  ')
        r_bullet.font.name = 'Times New Roman'
        r_bullet.font.size = Pt(12)
        r_bullet.font.bold = True
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(12)
            r_pre.font.bold = True
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)

    def add_image_placeholder(caption_text, guide_note):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="FFF9E6"/>') # Vàng kem nhạt
        cell._tc.get_or_add_tcPr().append(shd)
        border = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:top w:val="dashed" w:sz="12" w:space="0" w:color="D4AC0D"/>'
            f'<w:left w:val="dashed" w:sz="12" w:space="0" w:color="D4AC0D"/>'
            f'<w:bottom w:val="dashed" w:sz="12" w:space="0" w:color="D4AC0D"/>'
            f'<w:right w:val="dashed" w:sz="12" w:space="0" w:color="D4AC0D"/>'
            f'</w:tcBorders>'
        )
        cell._tc.get_or_add_tcPr().append(border)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(8)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        r1 = p.add_run('🖼️ [VỊ TRÍ DÁN ẢNH CHỤP GIAO DIỆN POWER BI]\n')
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(11)
        r1.font.bold = True
        r1.font.color.rgb = RGBColor(183, 149, 11)

        r2 = p.add_run(f'({guide_note})\n\n')
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(10)
        r2.font.italic = True

        r3 = p.add_run(caption_text)
        r3.font.name = 'Times New Roman'
        r3.font.size = Pt(10.5)
        r3.font.bold = True
        
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_after = Pt(4)

    # -------------------------------------------------------------
    # HEADER TÀI LIỆU
    # -------------------------------------------------------------
    add_doc_title(
        'TÀI LIỆU HƯỚNG DẪN & NỘI DUNG CHÈN VÀO BÁO CÁO MINI-PROJECT\n(BỔ SUNG DASHBOARD 5 & DASHBOARD 6)',
        'Được thiết kế chuẩn hóa định dạng Microsoft Word cho Nhóm 9 — Lớp 23_1 (Bình, Tinh, Tú)'
    )

    # -------------------------------------------------------------
    # PHẦN 1: CHƯƠNG 2
    # -------------------------------------------------------------
    add_loc_box(
        part_num='Đoạn 1',
        part_title='Bổ sung Thước đo DAX vào Chương 2',
        find_keyword='Chỉ số Mùa vụ (Seasonality & Time-Intelligence): Tận dụng phân cấp thời gian từ dim_date',
        insert_before='CHƯƠNG 3: THIẾT KẾ VÀ TRIỂN KHAI HỆ THỐNG DASHBOARD PHÂN TÍCH',
        action_note='Quét chọn khối văn bản bên dưới, nhấn Ctrl + C, quay lại file báo cáo chính đặt con trỏ chuột ngay trước CHƯƠNG 3 và nhấn Ctrl + V.'
    )

    add_h3('Nhóm chỉ số Giám sát Vận hành & Phân tích Tương tác Đa chiều (Observability & Interactive DAX):')
    add_bullet('Thước đo sử dụng hàm SELECTEDVALUE để bắt chính xác định danh đợt chạy ETL đang được người dùng bấm chọn trong bảng Audit Log; tự động trả về giá trị mặc định khi chưa có lựa chọn.', 'Selected Run Log ID: ')
    add_bullet('Thước đo truy vấn thông điệp chẩn đoán tự động từ tầng AI / Metadata cho đợt chạy tương ứng, phục vụ việc xuất khuyến nghị và giải thích nguyên nhân sự cố tức thì.', 'Run AI Diagnostic Message: ')
    add_bullet('Đo lường tổng số lượt chạy pipeline trên toàn hệ thống nhưng được bọc trong hàm CALCULATE(..., ALL(vw_etl_monitoring)) nhằm cố định số liệu toàn cục, không bị lọc theo dòng khi click vào bảng nhật ký chạy.', 'Total ETL Runs (Audit Unfiltered): ')
    add_bullet('Đo lường tỷ lệ phần trăm các phiên nạp dữ liệu hoàn tất thành công (status = SUCCESS) trên tổng số lượt thực thi, phản ánh mức độ sẵn sàng và độ tin cậy của đường ống dữ liệu.', 'Pipeline Success Rate (%): ')
    add_bullet('Thước đo tổng hợp doanh thu theo phương pháp Boxleiter tích hợp trong cây phân tích (AI Decomposition Tree), cho phép thuật toán AI tự động tìm kiếm thuộc tính đóng góp cao nhất (High-value contribution split).', 'Decomposition Tree Revenue Metric: ')

    doc.add_page_break()

    # -------------------------------------------------------------
    # PHẦN 2: CHƯƠNG 3
    # -------------------------------------------------------------
    add_loc_box(
        part_num='Đoạn 2',
        part_title='Thêm mới Dashboard 5 & Dashboard 6 vào cuối Chương 3',
        find_keyword='Ngưỡng an toàn thương mại: Biểu đồ phân tán chứng minh rằng các tựa game đạt mốc doanh thu trên 1 triệu USD hầu hết đều phải sở hữu tỷ lệ đánh giá tích cực trên 80%.',
        insert_before='CHƯƠNG 4: PHÂN TÍCH INSIGHT THƯƠNG MẠI & ĐỀ XUẤT CHIẾN LƯỢC',
        action_note='Quét chọn toàn bộ nội dung Dashboard 5 và Dashboard 6 bên dưới, nhấn Ctrl + C, quay lại file báo cáo chính đặt con trỏ chuột ngay trước CHƯƠNG 4 và nhấn Ctrl + V.'
    )

    # Dashboard 5
    add_h2('Dashboard 5 — Giám sát Đường ống ETL & Kiểm soát Chất lượng Dữ liệu (Data Observability & Pipeline Health)')
    
    add_h3('Mục tiêu phân tích & Đối tượng sử dụng')
    add_p('Dashboard 5 được thiết kế như một trung tâm chỉ huy dữ liệu thời gian thực (Data Observability Hub), cung cấp khả năng giám sát toàn diện tình trạng sức khỏe của đường ống dữ liệu, kiểm soát khối lượng bản ghi xử lý, đo lường thời gian thực thi đối chiếu với ngưỡng SLA cam kết và kiểm soát chất lượng dữ liệu thông qua bộ kiểm thử tự động của dbt.')
    add_p('Đối tượng sử dụng chính của Dashboard bao gồm: Đội ngũ Kỹ sư Dữ liệu (Data Engineers), Quản trị viên Cơ sở Dữ liệu (DBA) và Trưởng nhóm Kỹ thuật (Data Leads).')

    add_h3('Bố cục không gian & Dải chỉ số then chốt (KPI Cards)')
    add_image_placeholder(
        caption_text='Hình 3.5. Giao diện Dashboard 5 — Giám sát Đường ống ETL và Kiểm soát Chất lượng Dữ liệu',
        guide_note='Chụp màn hình trang "5. Giám sát đường ống ETL" trên Power BI Desktop và dán đè vào khung này'
    )
    add_p('Bố cục không gian của Dashboard 5 tuân thủ nghiêm ngặt tiêu chuẩn thiết kế phân tầng:')
    add_bullet('Gồm 4 thẻ chỉ số cố định trên đỉnh màn hình: Số lần ETL (11 lượt chạy), Tỷ lệ thành công (81.82%), Tổng test dbt passed (91 bài kiểm thử, đạt 100%), và Tổng bản ghi xử lý (376.905 dòng). Dải KPI này được cố định toàn cục bằng DAX ALL().', 'Dải KPI Vĩ mô Toàn cục (Top Cards): ')
    add_bullet('Thẻ đa hàng (Multi-row Card) hiển thị chi tiết đợt nạp mới nhất (mã run_id, thời điểm hoàn tất, số dòng thêm mới inserted, số dòng cập nhật updated, số dòng lỗi rejected). Bên dưới là Thẻ văn bản Chẩn đoán AI (AI Diagnostic Card) tự động giải thích nguyên nhân vận hành và đưa ra khuyến nghị xử lý sự cố.', 'Khối Kiểm tra Đợt chạy Hiện tại & Chẩn đoán AI (Cột trái): ')
    add_bullet('Biểu đồ cột chồng (Stacked Column Chart) so sánh cơ cấu bản ghi nạp qua các tháng (Tháng 10 và Tháng 11), trực quan hóa số lượng bản ghi mới, bản ghi cập nhật và bản ghi bất thường.', 'Biểu đồ Đối chiếu Thể tích Dữ liệu (Cột giữa): ')
    add_bullet('Biểu đồ đường (Line Chart) theo dõi thời gian thực thi (duration_sec) của từng đợt chạy, làm nổi bật sự khác biệt giữa Full Load (hơn 1.000 giây) và Incremental Load (3 – 25 giây), đối chiếu với ngưỡng SLA cam kết 60 giây.', 'Biểu đồ Giám sát Thời lượng & SLA (Cột phải): ')
    add_bullet('Bảng chi tiết toàn bộ lịch sử chạy ETL (Audit Log Trail Table) ghi nhận đầy đủ run_id, thời gian bắt đầu, thời gian kết thúc, chế độ chạy (full / incremental), phương thức kích hoạt và trạng thái hoàn tất.', 'Nhật ký Truy vết Chi tiết (Khu vực đáy): ')

    add_h3('Phân tích chi tiết các biểu đồ trực quan & Cơ chế tương tác (Interactivity)')
    add_p('Hệ thống áp dụng cơ chế điều hướng tương tác phân tầng đặc biệt:')
    add_bullet('Khi người dùng click chọn một đợt chạy bất kỳ trong bảng Audit Log (ví dụ: đợt nạp thử nghiệm prod_demo_20261122_inc_006 hoặc sự cố nạp LEGACY_5), biểu đồ cột thể tích, biểu đồ thời lượng và thẻ chẩn đoán AI sẽ lập tức lọc sâu để phân tích chi tiết riêng cho lần chạy đó.', 'Tương tác Khoan sâu Sự cố (Selective Drill-down): ')
    add_bullet('Nhờ tích hợp thước đo DAX ALL() kết hợp tính năng Edit Interactions -> None trong Power BI, dải 4 thẻ KPI vĩ mô trên đỉnh hoàn toàn không bị biến dạng khi tương tác với bảng, bảo đảm tính toàn vẹn của chỉ số quản trị cấp cao.', 'Bảo toàn Ngữ cảnh Toàn cục (Global Context Preservation): ')

    add_h3('Đúc kết Insight vận hành & Ý nghĩa thực tiễn')
    add_bullet('Quy trình nạp đắp thêm (Incremental Load) giúp tiết kiệm đến hơn 98% thời gian vận hành so với Full Load ban đầu (chỉ mất 3 – 25 giây thay vì gần 20 phút), chứng minh tính tối ưu vượt trội của kiến trúc Data Warehouse.', 'Hiệu năng đường ống vượt trội: ')
    add_bullet('100% các bài kiểm thử dbt (91/91) đều vượt qua thành công, tỷ lệ bản ghi rejected được cô lập triệt để tại bảng trung gian, ngăn chặn hoàn toàn việc làm bẩn dữ liệu của các bảng Fact và Dimension phục vụ kinh doanh.', 'Độ tin cậy dữ liệu tuyệt đối: ')

    # Dashboard 6
    add_h2('Dashboard 6 — Trợ lý AI Copilot & Phân tích Nghiệp vụ Kinh doanh (AI-Assisted Business Analytics)')
    
    add_h3('Mục tiêu phân tích & Đối tượng sử dụng')
    add_p('Dashboard 6 đóng vai trò là cây cầu nối thông minh giữa dữ liệu phân tích vĩ mô và quyết định kinh doanh chiến lược, kết hợp giữa mô hình phân rã đa chiều bằng AI (Decomposition Tree) và hệ thống Trợ lý ảo AI Copilot tích hợp mô hình ngôn ngữ lớn (LLM) để tự động hóa việc đưa ra nhận định và khuyến nghị hành động.')
    add_p('Đối tượng sử dụng chính: Giám đốc Điều hành (C-Level Executives), Giám đốc Chiến lược (CSO), Quản lý Sản phẩm (Product Leads) và các Quỹ đầu tư mạo hiểm.')

    add_h3('Bố cục không gian & Hệ thống trực quan')
    add_image_placeholder(
        caption_text='Hình 3.6. Giao diện Dashboard 6 — Trợ lý AI Copilot và Phân tích Nghiệp vụ Kinh doanh',
        guide_note='Chụp màn hình trang "6. Trợ lý AI & Phân tích nghiệp vụ" trên Power BI Desktop và dán đè vào khung này'
    )
    add_bullet('Slicer dạng tab trên đỉnh cho phép chuyển đổi tức thì giữa 4 chủ đề phân tích cốt lõi (Trang 1: Tổng quan & Mùa vụ; Trang 2: Hiệu suất & Chiến lược giá; Trang 3: Nhà phát hành & Nền tảng; Trang 4: Chi tiết game & Pareto).', 'Thanh Điều hướng Chủ đề Nghiệp vụ (Top Slicer): ')
    add_bullet('Gồm Thẻ "INSIGHT" (giải phẫu hiện trạng, cơ cấu doanh thu và điểm rơi thị trường) và Thẻ "ĐỀ XUẤT HÀNH ĐỘNG" (3 khuyến nghị thực thi cụ thể cho nhà quản lý).', 'Cụm Nhận định & Hành động Tự động (Cột trái): ')
    add_bullet('Nút bấm tương tác Web URL dẫn trực tiếp đến ứng dụng Steam Copilot Web App (chạy tại http://localhost:5000), kết nối mô hình Gemini AI để người dùng trò chuyện và truy vấn dữ liệu tự nhiên theo ngữ cảnh.', 'Cổng Tương tác Trợ lý Đàm thoại AI (Action Button): ')
    add_bullet('Visual AI Decomposition Tree trực quan hóa đường đi của hơn 38 tỷ USD doanh thu ước tính toàn sàn Steam, phân tách theo từng cấp bậc: Phân khúc Nhà phát hành (Indie vs AAA) → Thể loại (Action, Adventure, RPG...) → Tổ hợp Nền tảng (Windows Only, Win & Mac, Cross-platform...) → Tựa game cụ thể.', 'Cây Phân tích Đóng góp Doanh thu AI (Cột phải): ')

    add_h3('Cơ chế tương tác & Giá trị phân tích của Cây Phân tích Phân rã (Decomposition Tree)')
    add_bullet('Visual Decomposition Tree ứng dụng thuật toán AI của Power BI để tự động xếp hạng và gợi ý chiều không gian có mức độ ảnh hưởng lớn nhất đến doanh thu, giúp người dùng không bỏ sót các cơ hội kinh doanh tiềm ẩn.', 'Khám phá Tự động Nhánh Giá trị Cao (AI-Powered High Value Split): ')
    add_bullet('Người dùng có thể tự do mở rộng (expand) hoặc thu gọn (collapse) bất kỳ nhánh cây nào để tìm câu trả lời cho hiện tượng doanh thu: Ví dụ vì sao phân khúc Indie lại đạt gần 20 tỷ USD? Nhánh cây lập tức bóc tách rõ phần lớn đóng góp đến từ thể loại Adventure/Action trên hệ điều hành Windows Only.', 'Giải phẫu Đóng góp Đa chiều Không ràng buộc: ')

    add_h3('Đúc kết Insight trọng tâm & Giá trị thực tiễn của Trợ lý AI')
    add_bullet('Hệ thống loại bỏ hoàn toàn độ trễ thông tin giữa người làm dữ liệu và cấp lãnh đạo; các khuyến nghị chiến lược được mô hình AI tổng hợp tức thì ngay bên cạnh biểu đồ, giúp việc ra quyết định trở nên nhanh chóng và có căn cứ xác thực.', 'Rút ngắn chu trình từ Dữ liệu đến Quyết định: ')
    add_bullet('Cổng Chatbox AI mở rộng cung cấp khả năng hỏi đáp chuyên sâu (Ad-hoc Query) bằng ngôn ngữ tự nhiên, giúp người dùng không cần am hiểu kỹ thuật SQL hay DAX vẫn có thể khai phá dữ liệu hiệu quả.', 'Dân chủ hóa dữ liệu toàn diện (Data Democratization): ')

    doc.add_page_break()

    # -------------------------------------------------------------
    # PHẦN 3: CHƯƠNG 4
    # -------------------------------------------------------------
    add_loc_box(
        part_num='Đoạn 3A',
        part_title='Bổ sung Phát hiện chính của Dashboard 5 & 6 vào Chương 4',
        find_keyword='Các tựa game có tỷ lệ tích cực dưới 70% (mức Đánh giá trái chiều / Mixed) gặp bất lợi lớn trong việc giữ chân người chơi',
        insert_before='Đề xuất chiến lược hành động dựa trên dữ liệu (Data-driven action recommendation)',
        action_note='Quét chọn 2 mục bên dưới, nhấn Ctrl + C, quay lại file báo cáo chính dán vào trước tiêu đề "Đề xuất chiến lược hành động dựa trên dữ liệu".'
    )

    add_h3('Dashboard 5 — Giám sát Sức khỏe Đường ống ETL & Độ tin cậy Dữ liệu')
    add_bullet('Việc chuyển từ Full Load ban đầu sang chiến lược Incremental Load giúp giảm thời gian nạp từ 19.5 phút xuống chỉ còn 3 – 25 giây cho mỗi mẻ dữ liệu, tiết kiệm hơn 98% tài nguyên tính toán và băng thông mạng.', 'Hiệu năng vận hành và Tối ưu hóa tài nguyên: ')
    add_bullet('Toàn bộ 91 bài kiểm thử dbt đạt tỷ lệ hoàn thành 100%, bảo đảm không có khóa ngoại mồ côi, không trùng lặp khóa chính và tính nhất quán tuyệt đối giữa 3 tầng Staging - Cleaned - Fact.', 'Chất lượng và Độ tin cậy dữ liệu DWH: ')
    add_bullet('Cơ chế ghi log chi tiết và giao dịch cơ sở dữ liệu (Database Transaction) tự động kích hoạt Rollback khi phát sinh sự cố mạng, bảo toàn tính toàn vẹn dữ liệu và hỗ trợ chẩn đoán nguyên nhân gốc rễ tự động qua AI.', 'Khả năng chịu lỗi và tự phục hồi: ')

    add_h3('Dashboard 6 — Cây giải phẫu Doanh thu (AI Decomposition Tree) & Khuyến nghị Chiến lược Tự động')
    add_bullet('Cây phân rã AI chứng minh một phát hiện quan trọng: Nhóm game Indie ở thể loại Adventure và Action trên nền tảng Windows Only đóng góp doanh thu áp đảo (gần 14 tỷ USD), vượt qua nhiều dự án bom tấn AAA ở các thể loại truyền thống.', 'Quy luật Tập trung Giá trị từ AI Tree: ')
    add_bullet('Trợ lý AI tự động nhận diện và cảnh báo sớm nguy cơ "Bào mòn Uy tín Thương hiệu" (Brand Equity Erosion) khi nhiều tựa game bom tấn đạt doanh thu rất lớn nhưng tỷ lệ đánh giá tích cực lại rơi xuống mức báo động (< 50%).', 'Cảnh báo Rủi ro Thương mại từ AI Copilot: ')

    add_loc_box(
        part_num='Đoạn 3B',
        part_title='Bổ sung Chiến lược Vận hành Dữ liệu vào Đề xuất Chiến lược Chương 4',
        find_keyword='Căn cứ: Doanh thu tổng hợp của Indie vượt AAA, chứng minh mô hình danh mục phân tán mang lại tỷ suất lợi nhuận trên rủi ro (Risk-adjusted Return) hấp dẫn hơn.',
        insert_before='CHƯƠNG 5: KẾT LUẬN & HƯỚNG PHÁT TRIỂN',
        action_note='Quét chọn mục Chiến lược Vận hành Dữ liệu bên dưới, nhấn Ctrl + C, dán vào trước tiêu đề "CHƯƠNG 5: KẾT LUẬN & HƯỚNG PHÁT TRIỂN".'
    )

    add_h3('Chiến lược Tối ưu hóa Vận hành & Quản trị Dữ liệu Doanh nghiệp (Data Governance & Operations)')
    add_bullet('Thiết lập cơ chế kích hoạt pipeline nạp gia tăng (Incremental) định kỳ 15 – 30 phút một lần để cung cấp dữ liệu gần thời gian thực (Near Real-time) cho các phòng ban kinh doanh.', 'Tự động hóa chu kỳ nạp dữ liệu: ')
    add_bullet('Áp dụng ngưỡng cảnh báo SLA tự động (ví dụ: cảnh báo tức thì khi thời gian chạy vượt quá 60 giây hoặc tỷ lệ bản ghi rejected vượt ngưỡng 1%) thông qua webhook kết nối Teams/Slack.', 'Hệ thống cảnh báo ngưỡng SLA chủ động: ')
    add_bullet('Ứng dụng Trợ lý AI Copilot làm công cụ tra cứu dữ liệu hàng ngày cho đội ngũ kinh doanh, giảm thiểu sự phụ thuộc vào các báo cáo ad-hoc thủ công từ phòng dữ liệu.', 'Chuẩn hóa quy trình phân tích tự phục vụ (Self-service BI): ')

    doc.add_page_break()

    # -------------------------------------------------------------
    # PHẦN 4: CHƯƠNG 5
    # -------------------------------------------------------------
    add_loc_box(
        part_num='Đoạn 4',
        part_title='Cập nhật Đánh giá hoàn thành và Hạn chế mở rộng ở Chương 5',
        find_keyword='Bảng 5.1 Đánh giá mức độ hoàn thành của các thành viên',
        insert_before='(Thay thế / cập nhật trực tiếp nội dung trong Chương 5)',
        action_note='Mở Chương 5 trong file báo cáo, bổ sung các gạch đầu dòng dưới đây vào mục Đánh giá kết quả, Bảng phân công 5.1 và mục Hướng phát triển.'
    )

    add_h2('Bổ sung vào mục: Đánh giá kết quả hoàn thành đồ án')
    add_bullet('Xây dựng thành công hệ thống giám sát đường ống dữ liệu toàn diện (Dashboard 5) với đầy đủ chỉ số SLA, chất lượng dữ liệu và cơ chế chẩn đoán lỗi tự động bằng AI.', 'Hoàn thành trọn vẹn Module Giám sát Dữ liệu (Data Observability): ')
    add_bullet('Tích hợp thành công visual AI Decomposition Tree và mô hình ngôn ngữ lớn (Gemini AI) thông qua ứng dụng Steam Copilot Web App (Dashboard 6), tạo bước đột phá trong trải nghiệm người dùng.', 'Ứng dụng Trí tuệ Nhân tạo vào Business Intelligence: ')

    add_p('Cập nhật nội dung chi tiết cho Bảng 5.1 — Phân công nhiệm vụ thành viên:', bold_prefix='Bảng 5.1. ')
    add_bullet('Phụ trách thiết kế và tối ưu hóa đường ống dữ liệu (ETL Pipeline), xây dựng cơ chế Logging & Audit Trail, triển khai view giám sát vw_etl_monitoring và thiết kế bố cục Dashboard 5.', 'Nguyễn Ngọc Bình (23120218): ')
    add_bullet('Phụ trách xây dựng hệ thống 91 bài kiểm thử dbt, thiết kế mô hình Semantic Model trong Power BI, lập trình hệ thống thước đo DAX nâng cao và triển khai visual AI Decomposition Tree trên Dashboard 6.', 'Kiều Đỗ Song Tinh (23120373): ')
    add_bullet('Phụ trách phát triển ứng dụng Steam Copilot Web App kết nối API Gemini, xây dựng view khuyến nghị tự động vw_dashboard_ai_insights, tích hợp trải nghiệm tương tác UI/UX và tổng hợp báo cáo chuyên sâu.', 'Phạm Lê Thanh Tú (23120388): ')

    add_h2('Bổ sung vào mục: Hạn chế của đề tài & Hướng nghiên cứu mở rộng')
    add_bullet('Tích hợp thêm kiến trúc RAG (Retrieval-Augmented Generation) kết hợp Vector Database để trợ lý AI Copilot có thể đọc hiểu thêm toàn bộ tài liệu kỹ thuật, bình luận chi tiết của cộng đồng người chơi (User Reviews text).', 'Nâng cấp Năng lực AI Copilot: ')
    add_bullet('Tự động hóa hoàn toàn quy trình xử lý sự cố (Auto-healing Pipeline), tự động chạy lại các batch lỗi và gửi báo cáo sự cố tức thời qua kênh Telegram / Slack của đội ngũ kỹ thuật.', 'Cơ chế Phục hồi Tự động và Thông báo Đa kênh: ')

    output_path = r'c:\Users\HP\Desktop\C++CodeLearn\HK1-2627\HTTT_Phuc_Vu_Tri_Tue_Kinh_Doanh\mini-project\Steam_DWH_Project\FILE_CHEN_NOI_DUNG_BAO_CAO_DASHBOARD_5_VA_6.docx'
    doc.save(output_path)
    print(f'Successfully created guide document at: {output_path}')

if __name__ == '__main__':
    create_guide_docx()
