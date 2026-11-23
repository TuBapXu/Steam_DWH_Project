# -*- coding: utf-8 -*-
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# 1. Đăng ký font tiếng Việt Times New Roman
pdfmetrics.registerFont(TTFont('TimesNewRoman', 'C:/Windows/Fonts/times.ttf'))
pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', 'C:/Windows/Fonts/timesbd.ttf'))
pdfmetrics.registerFont(TTFont('TimesNewRoman-Italic', 'C:/Windows/Fonts/timesi.ttf'))
pdfmetrics.registerFont(TTFont('TimesNewRoman-BoldItalic', 'C:/Windows/Fonts/timesbi.ttf'))

pdfmetrics.registerFontFamily(
    'TimesNewRoman',
    normal='TimesNewRoman',
    bold='TimesNewRoman-Bold',
    italic='TimesNewRoman-Italic',
    boldItalic='TimesNewRoman-BoldItalic'
)

# 2. Canvas đánh số trang tự động (Page X of Y) và Header/Footer
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        print(f'Total pages in PDF: {num_pages}')
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont('TimesNewRoman', 9)
        self.setFillColor(colors.HexColor('#64748B'))

        # Header (từ trang 2 trở đi)
        if self._pageNumber > 1:
            self.drawString(2.0 * cm, 28.2 * cm, 'ĐỒ ÁN STEAM DWH & BI — NHÓM 9 (LỚP 23_1)')
            self.drawRightString(19.0 * cm, 28.2 * cm, 'KẾ HOẠCH ĐIỀU CHỈNH BÁO CÁO & PHÂN CÔNG')
            self.setStrokeColor(colors.HexColor('#CBD5E1'))
            self.setLineWidth(0.5)
            self.line(2.0 * cm, 28.0 * cm, 19.0 * cm, 28.0 * cm)

        # Footer (tất cả các trang)
        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.5)
        self.line(2.0 * cm, 1.8 * cm, 19.0 * cm, 1.8 * cm)
        self.drawString(2.0 * cm, 1.3 * cm, 'Trường ĐH Khoa học Tự nhiên — ĐHQG-HCM | Khoa CNTT')
        self.drawRightString(19.0 * cm, 1.3 * cm, f'Trang {self._pageNumber} / {page_count}')
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm
    )

    styles = getSampleStyleSheet()

    # Định nghĩa các Style văn bản chuẩn
    PRIMARY_COLOR = colors.HexColor('#0F4761')
    SECONDARY_COLOR = colors.HexColor('#1E293B')
    ACCENT_COLOR = colors.HexColor('#0369A1')
    TEXT_COLOR = colors.HexColor('#1F2937')

    style_title = ParagraphStyle(
        'DocTitle',
        fontName='TimesNewRoman-Bold',
        fontSize=17,
        leading=22,
        alignment=1, # Center
        textColor=PRIMARY_COLOR,
        spaceAfter=6
    )

    style_subtitle = ParagraphStyle(
        'DocSubTitle',
        fontName='TimesNewRoman-BoldItalic',
        fontSize=12,
        leading=16,
        alignment=1,
        textColor=ACCENT_COLOR,
        spaceAfter=15
    )

    style_meta = ParagraphStyle(
        'MetaBox',
        fontName='TimesNewRoman',
        fontSize=10,
        leading=14,
        textColor=SECONDARY_COLOR
    )

    style_h1 = ParagraphStyle(
        'Heading1_Custom',
        fontName='TimesNewRoman-Bold',
        fontSize=13,
        leading=17,
        textColor=PRIMARY_COLOR,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'Heading2_Custom',
        fontName='TimesNewRoman-Bold',
        fontSize=11.5,
        leading=15,
        textColor=ACCENT_COLOR,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'Body_Custom',
        fontName='TimesNewRoman',
        fontSize=10.5,
        leading=14.5,
        textColor=TEXT_COLOR,
        spaceAfter=5
    )

    style_body_bold = ParagraphStyle(
        'Body_Bold_Custom',
        fontName='TimesNewRoman-Bold',
        fontSize=10.5,
        leading=14.5,
        textColor=TEXT_COLOR,
        spaceAfter=5
    )

    style_bullet = ParagraphStyle(
        'Bullet_Custom',
        fontName='TimesNewRoman',
        fontSize=10,
        leading=14,
        textColor=TEXT_COLOR,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )

    style_table_header = ParagraphStyle(
        'TableHeader',
        fontName='TimesNewRoman-Bold',
        fontSize=9.5,
        leading=12.5,
        alignment=1,
        textColor=colors.white
    )

    style_table_cell = ParagraphStyle(
        'TableCell',
        fontName='TimesNewRoman',
        fontSize=9,
        leading=12,
        textColor=TEXT_COLOR
    )

    style_table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='TimesNewRoman-Bold',
        fontSize=9,
        leading=12,
        textColor=TEXT_COLOR
    )

    story = []

    # ==========================================
    # HEADER PHẦN ĐẦU TÀI LIỆU
    # ==========================================
    header_table_data = [
        [
            Paragraph('<b>TRƯỜNG ĐẠI HỌC KHOA HỌC TỰ NHIÊN — ĐHQG-HCM</b><br/>KHOA CÔNG NGHỆ THÔNG TIN<br/>BỘ MÔN HỆ THỐNG THÔNG TIN', ParagraphStyle('UnivHeader', fontName='TimesNewRoman', fontSize=9, leading=12, alignment=1)),
            Paragraph('<b>HỆ THỐNG THÔNG TIN PHỤC VỤ BI (23_1)</b><br/><b>NHÓM 9 — HỌC KỲ 1, NĂM HỌC 2026–2027</b><br/><i>TP. Hồ Chí Minh, ngày 23/11/2026</i>', ParagraphStyle('GroupHeader', fontName='TimesNewRoman', fontSize=9, leading=12, alignment=1))
        ]
    ]
    t_header = Table(header_table_data, colWidths=[8.5*cm, 8.5*cm])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY_COLOR, spaceAfter=12))

    # TIÊU ĐỀ CHÍNH
    story.append(Paragraph('KẾ HOẠCH ĐIỀU CHỈNH TOÀN DIỆN BÁO CÁO CUỐI KỲ<br/>& PHÂN CÔNG CÔNG VIỆC NHÓM 9', style_title))
    story.append(Paragraph('Thống nhất Kiến trúc Pipeline, Đồng bộ Database DWH, Bổ sung Video Demo & Hoàn thiện Báo cáo', style_subtitle))

    # BẢNG THÔNG TIN DỰ ÁN
    meta_data = [
        [Paragraph('<b>Tên đồ án:</b>', style_meta), Paragraph('Xây dựng Kho dữ liệu và Hệ thống BI phân tích hiệu suất trò chơi trên Steam', style_meta)],
        [Paragraph('<b>Thành viên nhóm:</b>', style_meta), Paragraph('1. <b>Phạm Lê Thanh Tú</b> (Nhóm trưởng) — 23120388<br/>2. <b>Nguyễn Ngọc Bình</b> — 23120218<br/>3. <b>Kiều Đỗ Song Tinh</b> — 23120373', style_meta)],
        [Paragraph('<b>Hiện trạng thực tế:</b>', style_meta), Paragraph('<b>Video Demo các phần trước (Pipeline, dbt, Dashboard 1–4) ĐÃ HOÀN THÀNH</b>. Nhiệm vụ quay màn hình còn lại DUY NHẤT là Dashboard 5, 6 và AI Chatbox (giao cho Tú thực hiện). Trọng tâm còn lại là biên tập dứt điểm các mâu thuẫn báo cáo và ghép video tổng.', style_meta)],
        [Paragraph('<b>Mục tiêu kế hoạch:</b>', style_meta), Paragraph('Thống nhất cấu trúc báo cáo bằng mục "Tiến hóa kiến trúc", chuẩn hóa số liệu toàn văn, phân chia công việc sửa báo cáo cân bằng và hoàn thiện video demo tổng thể.', style_meta)]
    ]
    t_meta = Table(meta_data, colWidths=[3.2*cm, 13.8*cm])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # ==========================================
    # PHẦN I: HIỆN TRẠNG & NGUYÊN NHÂN MÂU THUẪN
    # ==========================================
    story.append(Paragraph('I. HIỆN TRẠNG BÁO CÁO & NGUYÊN NHÂN MÂU THUẪN', style_h1))
    story.append(Paragraph(
        'Qua rà soát đối chiếu toàn diện giữa văn bản báo cáo hiện tại với hệ thống mã nguồn thực tế (Mage.ai, dbt, SQL Server, Power BI và AI Copilot), nhóm đã phát hiện báo cáo đang gặp phải một <b>mâu thuẫn cấu trúc nghiêm trọng</b>:',
        style_body
    ))
    story.append(Paragraph(
        '• <b>Nửa đầu báo cáo (Mục I đến VIII - Báo cáo Giai đoạn 1):</b> Được viết ở đợt nộp ban đầu khi hệ thống còn ở giai đoạn thử nghiệm sơ khai. Phần này mô tả pipeline chỉ gồm 4 block, nạp tăng dần cắt theo <i>Release date</i> 2 năm (được 515 dòng), Fact và Staging chỉ có 858 dòng, 100 tests dbt, mô hình Star Schema chỉ có 4 Dimension cơ bản, và đặc biệt tại mục 7.5 kết luận <i>"chưa có dashboard Power BI hoặc lớp Generative AI trong project"</i>.',
        style_bullet
    ))
    story.append(Paragraph(
        '• <b>Nửa sau báo cáo (Chương 1 đến Chương 5 - Báo cáo Giai đoạn 2):</b> Được biên soạn sau khi nhóm đã tối ưu và nâng cấp toàn diện pipeline: chia 126 chunk động (1.000 dòng/chunk) lưu Parquet, nạp tăng dần thông minh theo <i>AppID + SHA-256 row_hash</i>, Fact nạp đủ 125.856 tựa game, 91 tests dbt pass 100%, bổ sung chiều OS và bảng bridge, triển khai trọn vẹn <b>6 trang Dashboard</b> chuyên sâu và <b>Trợ lý AI Copilot</b> kết nối mô hình Gemini AI tại cổng 5000.',
        style_bullet
    ))
    story.append(Paragraph(
        '<b>Hệ quả:</b> Việc ghép nguyên xi hai phần vào một văn bản khiến báo cáo <b>tự phủ nhận chính mình</b>. Giảng viên đọc vào sẽ thấy sự thiếu nhất quán về mặt kỹ thuật, số liệu chênh lệch và đặt dấu hỏi về độ tin cậy của đồ án. Do đó, việc biên tập và tái cấu trúc là yêu cầu cấp thiết số 1 trước khi xuất bản bản nộp cuối cùng.',
        style_body
    ))
    story.append(Spacer(1, 6))

    # ==========================================
    # PHẦN II: CHIẾN LƯỢC THỐNG NHẤT CẤU TRÚC
    # ==========================================
    story.append(Paragraph('II. CHIẾN LƯỢC THỐNG NHẤT CẤU TRÚC: "TIẾN HÓA KIẾN TRÚC VÀ ƯU ĐIỂM CẢI TIẾN"', style_h1))
    story.append(Paragraph(
        'Thay vì cắt bỏ trắng trơn Giai đoạn 1 làm mất đi quá trình nghiên cứu thực tế, nhóm thống nhất <b>chiến lược biên tập học thuật</b>: Giữ cấu trúc mạch lạc nhưng biến phần Giai đoạn 1 thành phần trình bày <b>Sự tiến hóa của kiến trúc (Architectural Evolution)</b>, làm nổi bật năng lực giải quyết vấn đề kỹ thuật của nhóm qua 4 bài toán lớn:',
        style_body
    ))

    evo_table_data = [
        [
            Paragraph('Thành phần', style_table_header),
            Paragraph('Thiết kế ban đầu (Phase 1)', style_table_header),
            Paragraph('Thiết kế nâng cấp hoàn chỉnh (Phase 2)', style_table_header),
            Paragraph('Ưu điểm vượt trội khi cải tiến', style_table_header)
        ],
        [
            Paragraph('<b>Kiến trúc Pipeline Ingestion</b>', style_table_cell_bold),
            Paragraph('4 block tuần tự (`extract_steam_games` $\\rightarrow$ `validate` $\\rightarrow$ `load` $\\rightarrow$ `watermark`). Nạp nguyên DataFrame lớn vào RAM.', style_table_cell),
            Paragraph('<b>8 block động</b> trên Mage.ai (`prepare_chunks` $\\rightarrow$ chia 126 chunk Parquet $\\rightarrow$ nhánh động Extract/Validate/Load $\\rightarrow$ `publish_staging` qua Transaction $\\rightarrow$ `report` $\\rightarrow$ `dbt` $\\rightarrow$ `check_dwh`).', style_table_cell),
            Paragraph('<b>Triệt tiêu nghẽn RAM</b> (máy 8GB RAM vẫn chạy mượt mà 125k dòng); kiểm soát lỗi theo từng chunk; Staging chỉ cập nhật khi 100% chunk thành công.', style_table_cell)
        ],
        [
            Paragraph('<b>Cơ chế Nạp tăng dần (Incremental)</b>', style_table_cell_bold),
            Paragraph('Cắt lát theo ngày phát hành `Release date` 2 năm một lần (dùng `demo_lset`, `demo_cet`).', style_table_cell),
            Paragraph('So khớp khóa tự nhiên `AppID` kết hợp hàm băm <b>SHA-256 (`row_hash`)</b> trên toàn bộ thuộc tính nghiệp vụ đã chuẩn hóa.', style_table_cell),
            Paragraph('<b>Đúng chuẩn CDC thực tế:</b> Bắt trọn vẹn cả game mới lẫn các thay đổi giá, discount, CCU và review của game cũ; loại bỏ phụ thuộc sai lệch vào ngày phát hành.', style_table_cell)
        ],
        [
            Paragraph('<b>Mô hình Data Warehouse</b>', style_table_cell_bold),
            Paragraph('Star Schema sơ cấp gồm 4 Dim (`Date`, `Game`, `Platform`, `Publisher`) và 1 Fact.', style_table_cell),
            Paragraph('Star Schema chuẩn hóa mở rộng: Bổ sung <b>`dim_operating_system`</b> (3 dòng) và bảng cầu <b>`bridge_game_platform`</b> (163.600 dòng). Fact dùng Composite PK.', style_table_cell),
            Paragraph('Giải quyết triệt để <b>quan hệ N-N</b> giữa game và hệ điều hành; cho phép phân tích độc lập độ thâm nhập từng OS trên Power BI mà không bị đếm trùng Fact.', style_table_cell)
        ],
        [
            Paragraph('<b>Chất lượng & Giám sát (DQC)</b>', style_table_cell_bold),
            Paragraph('Loại bỏ dòng lỗi bằng `on_bad_lines="skip"`. Audit log ghi nhận 6 cột đơn giản.', style_table_cell),
            Paragraph('Cô lập lỗi vào <b>`dbo.stg_steam_games_rejected`</b> (8 bản ghi); mở rộng audit log (`run_id`, `step`, `duration_sec`, `metrics_json`...); xây dựng <b>View `vw_etl_monitoring`</b>.', style_table_cell),
            Paragraph('<b>Độ tin cậy dữ liệu tuyệt đối:</b> Không mất dấu vết dữ liệu thô; theo dõi SLA và hiệu năng đường ống tức thì; cấp dữ liệu trực tiếp cho Dashboard 5.', style_table_cell)
        ]
    ]

    t_evo = Table(evo_table_data, colWidths=[3.2*cm, 4.4*cm, 4.7*cm, 4.7*cm])
    t_evo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
    ]))
    story.append(t_evo)
    story.append(Spacer(1, 10))

    # ==========================================
    # PHẦN III: BẢNG QUY CHUẨN SỐ LIỆU ĐỒNG NHẤT
    # ==========================================
    story.append(Paragraph('III. BẢNG QUY CHUẨN SỐ LIỆU ĐỒNG NHẤT (SINGLE SOURCE OF TRUTH)', style_h1))
    story.append(Paragraph(
        'Tất cả thành viên trong nhóm bắt buộc phải sử dụng <b>chính xác các thông số định lượng dưới đây</b> khi viết báo cáo, làm slide và thuyết trình video demo, tránh tình trạng mỗi chương một số liệu khác nhau:',
        style_body
    ))

    data_sync_table = [
        [
            Paragraph('Chỉ số / Thực thể', style_table_header),
            Paragraph('Số liệu chuẩn xác', style_table_header),
            Paragraph('Giải thích ngữ cảnh & Lưu ý khi viết báo cáo', style_table_header)
        ],
        [
            Paragraph('<b>Tổng số game trong DWH</b>', style_table_cell_bold),
            Paragraph('<b>125.856 tựa game</b>', style_table_cell_bold),
            Paragraph('Số dòng thực tế hiện tại trong `stg_steam_games`, `fact_game_snapshot` và `dim_game` (Snapshot gốc có 125.853 game; qua các đợt chạy incremental mô phỏng hiện là 125.856).', style_table_cell)
        ],
        [
            Paragraph('<b>Phạm vi phân tích theo thời gian</b>', style_table_cell_bold),
            Paragraph('<b>122.537 game</b> (1997–2025)<br/><b>121.874 game</b> (2010–2025)', style_table_cell),
            Paragraph('Toàn sàn 1997–2026 là 125.856 game. Riêng năm 2026 có 3.319 game chưa trọn vẹn nên chuỗi YoY Dashboard 1 chỉ lấy đến 2025; ảnh chụp Dashboard 1 lọc 2010–2025.', style_table_cell)
        ],
        [
            Paragraph('<b>Bản ghi lỗi bị cô lập (Rejected)</b>', style_table_cell_bold),
            Paragraph('<b>8 bản ghi lỗi</b>', style_table_cell_bold),
            Paragraph('Lưu trữ tại `dbo.stg_steam_games_rejected`, phân loại theo 4 mã lỗi: `INVALID_APPID`, `MISSING_APPID`, `INVALID_CSV`, `TOO_MANY_FIELDS` (không viết 2 dòng như cũ).', style_table_cell)
        ],
        [
            Paragraph('<b>Số lượng bảng chiều & cầu</b>', style_table_cell_bold),
            Paragraph('• `dim_date`: <b>10.748 dòng</b><br/>• `dim_publisher`: <b>62.635 dòng</b><br/>• `dim_platform`: <b>8 tổ hợp</b><br/>• `dim_operating_system`: <b>3 dòng</b><br/>• `bridge_game_platform`: <b>163.600 dòng</b>', style_table_cell),
            Paragraph('Khóa `date_key = 0` đại diện cho ngày phát hành chưa xác định (Unknown). Phân hạng Publisher gồm 1.015 AAA và 61.620 Indie. Bảng cầu hệ điều hành ánh xạ chính xác 163.600 lượt tương thích OS.', style_table_cell)
        ],
        [
            Paragraph('<b>Số lượng model & test dbt</b>', style_table_cell_bold),
            Paragraph('• Models: <b>9 models</b><br/>• dbt tests: <b>91 tests (100% PASS)</b><br/>• Unit tests: <b>32 unit tests</b>', style_table_cell_bold),
            Paragraph('Gồm 2 staging models, 7 marts models. Không có model `stg_steam_game_classifications`. Toàn bộ 91 bài test tự động của dbt đều đạt trạng thái PASS. 32 unit tests python kiểm tra logic pipeline.', style_table_cell)
        ],
        [
            Paragraph('<b>Hệ thống Dashboard Power BI</b>', style_table_cell_bold),
            Paragraph('<b>Đầy đủ 6 trang Dashboard</b>', style_table_cell_bold),
            Paragraph('Định dạng 1920×1080 (16:9): DB1: Mùa vụ; DB2: Định giá; DB3: Nhà phát hành; DB4: Drill-through; DB5: Giám sát ETL (Observability); DB6: AI Decomposition Tree.', style_table_cell)
        ],
        [
            Paragraph('<b>Phân hệ Trợ lý ảo AI Copilot</b>', style_table_cell_bold),
            Paragraph('<b>Steam Copilot Web App</b><br/>(Cổng `http://localhost:5000`)', style_table_cell),
            Paragraph('Tích hợp Gemini AI + Grounding Engine, truy vấn bảng `dbo.dashboard_ai_insights` (4 dòng insight) và dữ liệu SQL Server, hỗ trợ đàm thoại ngôn ngữ tự nhiên.', style_table_cell)
        ]
    ]

    t_sync = Table(data_sync_table, colWidths=[3.8*cm, 4.2*cm, 9.0*cm])
    t_sync.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY_COLOR),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#F8FAFC')),
    ]))
    story.append(t_sync)
    story.append(Spacer(1, 10))

    # ==========================================
    # PHẦN IV: PHÂN CÔNG NHIỆM VỤ CHI TIẾT
    # ==========================================
    story.append(Paragraph('IV. BẢNG PHÂN CÔNG NHIỆM VỤ CHI TIẾT & CÂN BẰNG KHỐI LƯỢNG', style_h1))
    story.append(Paragraph(
        '<b>Lưu ý quan trọng về Video Demo:</b> Các phân đoạn video trước (Pipeline Mage.ai, dbt test, Dashboard 1, 2, 3, 4) <b>ĐÃ ĐƯỢC NHÓM QUAY HOÀN THÀNH</b>. Do đó, <b>nhiệm vụ quay màn hình còn lại DUY NHẤT</b> là phân đoạn <b>Dashboard 5, Dashboard 6 và Trợ lý AI Chatbox</b> (giao cho <b>Phạm Lê Thanh Tú</b> thực hiện). Khối lượng công việc được phân bổ lại tập trung tối đa vào việc biên tập dứt điểm các mâu thuẫn báo cáo và ghép video tổng.',
        style_body
    ))

    task_table_data = [
        [
            Paragraph('Thành viên & Vai trò', style_table_header),
            Paragraph('Phụ trách Báo cáo (Chương & Nội dung cần sửa)', style_table_header),
            Paragraph('Phụ trách Video Demo (Tình trạng & Nhiệm vụ)', style_table_header),
            Paragraph('Trách nhiệm hoàn thiện & Hậu kỳ', style_table_header)
        ],
        [
            Paragraph('<b>Phạm Lê Thanh Tú</b><br/>(Nhóm trưởng)<br/>MSSV: 23120388', style_table_cell_bold),
            Paragraph(
                '• <b>Chương 2:</b> Rà soát Semantic Model, cập nhật quan hệ bảng bridge `bridge_game_platform`, bảng `dim_game_genres` và hệ thống DAX.<br/>'
                '• <b>Chương 3 (Mục 3.3, 3.4):</b> Rà soát nội dung Dashboard 3 (Nhà phát hành) và Dashboard 4 (Drill-through).<br/>'
                '• <b>Dashboard 5 & 6:</b> Rà soát, chuẩn hóa văn phong và hình ảnh cho Dashboard 5 (Giám sát ETL) và Dashboard 6 (AI Copilot & Decomposition Tree).',
                style_table_cell
            ),
            Paragraph(
                '• <b>Phần video cũ (Dashboard 3 & 4):</b> <font color="#059669"><b>ĐÃ HOÀN THÀNH</b></font>.<br/>'
                '• <b>QUAY PHẦN DUY NHẤT CÒN LẠI:</b><br/>'
                '  + <b>Dashboard 5 (ETL Observability):</b> Thuyết minh giao diện giám sát, SLA <60s, khối lượng bản ghi và thẻ chẩn đoán AI.<br/>'
                '  + <b>Dashboard 6 (AI Decomposition Tree):</b> Thao tác cây phân tích đóng góp doanh thu AI.<br/>'
                '  + <b>AI Chatbox Copilot:</b> Mở trình duyệt demo Chatbox (`http://localhost:5000`), gõ câu hỏi và nhận câu trả lời từ Gemini AI.',
                style_table_cell
            ),
            Paragraph(
                '• Điều phối tiến độ chung toàn nhóm.<br/>'
                '• Bàn giao clip Dashboard 5, 6 và AI Chatbox cho Bình ghép video trước 20:00.<br/>'
                '• Kiểm duyệt tổng thể tính logic giữa Báo cáo, DAX và Video Demo.',
                style_table_cell
            )
        ],
        [
            Paragraph('<b>Nguyễn Ngọc Bình</b><br/>MSSV: 23120218', style_table_cell_bold),
            Paragraph(
                '• <b>Chương 1:</b> Viết lại toàn bộ kiến trúc pipeline 8 block Mage.ai, cơ chế chia 126 chunk Parquet, nạp tăng dần bằng mã băm SHA-256 (`row_hash`), watermark `batch_seq`, và bảng rejected.<br/>'
                '• <b>Viết mục mới:</b> <i>"Quá trình nâng cấp kiến trúc và ưu điểm cải tiến"</i> theo Bảng ở Mục II.<br/>'
                '• <b>Chương 3 (Mục 3.1):</b> Rà soát và cập nhật nội dung Dashboard 1 (Thời điểm & Mùa vụ phát hành).',
                style_table_cell
            ),
            Paragraph(
                '• <b>Phần video cũ (Pipeline Mage & Dashboard 1):</b> <font color="#059669"><b>ĐÃ HOÀN THÀNH</b></font>.<br/>'
                '• <b>KHÔNG CẦN QUAY THÊM</b>.<br/>'
                '• <b>TẬP TRUNG HẬU KỲ VIDEO TỔNG:</b> Nhận clip Dashboard 5, 6 và AI Chatbox từ Tú để chèn vào video tổng thể đã có sẵn; căn chỉnh âm thanh, chuyển cảnh và xuất bản video 1080p.',
                style_table_cell
            ),
            Paragraph(
                '• <b>Hậu kỳ & Biên tập Video:</b> Phụ trách kỹ thuật dựng video.<br/>'
                '• Chèn slide tiêu đề mở đầu, chuyển cảnh mượt mà, căn chỉnh âm lượng đồng đều và xuất file Video đạt chuẩn Full HD 1080p sẵn sàng nộp.',
                style_table_cell
            )
        ],
        [
            Paragraph('<b>Kiều Đỗ Song Tinh</b><br/>MSSV: 23120373', style_table_cell_bold),
            Paragraph(
                '• <b>Chương 3 (Mục 3.2):</b> Rà soát và hoàn thiện nội dung Dashboard 2 (Hiệu suất thương mại, tương quan giảm giá, độ tuổi và CCU).<br/>'
                '• <b>Chương 4:</b> Rà soát 4 nhóm phát hiện kinh doanh (Insight 1-4) và các đề xuất chiến lược cho Studio Indie, Nhà phát hành AAA và Quỹ đầu tư.<br/>'
                '• <b>Chương 5:</b> Cập nhật Bảng 5.1 (đánh giá 100% hoàn thành cho 3 thành viên), bổ sung nhận định về Dashboard 5, 6 và AI Copilot.<br/>'
                '• <b>Đồng bộ số liệu:</b> Quét toàn bộ văn bản để chuẩn hóa số 125.856 game, 91 tests, 8 rejected...',
                style_table_cell
            ),
            Paragraph(
                '• <b>Phần video cũ (Dashboard 2 & dbt test):</b> <font color="#059669"><b>ĐÃ HOÀN THÀNH</b></font>.<br/>'
                '• <b>KHÔNG CẦN QUAY THÊM</b>.<br/>'
                '• <b>TẬP TRUNG TOÀN LỰC HẬU KỲ BÁO CÁO:</b> Ráp nối các phần nội dung đã sửa từ Bình và Tú vào file Word chuẩn phong cách KHTN.',
                style_table_cell
            ),
            Paragraph(
                '• <b>Tổng hợp Báo cáo:</b> Căn chỉnh định dạng (Times New Roman 12pt, lề chuẩn 2-2-3-2cm, dãn dòng 1.15, đánh số bảng/hình tự động, tạo mục lục tự động).<br/>'
                '• <b>Xuất file Báo cáo PDF hoàn chỉnh</b> sẵn sàng nộp.',
                style_table_cell
            )
        ]
    ]

    t_task = Table(task_table_data, colWidths=[3.2*cm, 4.6*cm, 5.4*cm, 3.8*cm])
    t_task.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
    ]))
    story.append(t_task)
    story.append(Spacer(1, 10))

    # ==========================================
    # PHẦN V: KỊCH BẢN VIDEO DEMO TỔNG THỂ
    # ==========================================
    story.append(Paragraph('V. KỊCH BẢN TỔNG HỢP VIDEO DEMO TỔNG THỂ (DỰ KIẾN 12–15 PHÚT)', style_h1))
    story.append(Paragraph(
        'Bảng theo dõi trạng thái phân đoạn video demo: Các phần đã quay xong sẽ được giữ nguyên bản; Bình sẽ nhận clip Dashboard 5, 6 và AI Chatbox từ Tú để ghép vào đoạn cuối video:',
        style_body
    ))

    video_timeline_data = [
        [
            Paragraph('Thời lượng', style_table_header),
            Paragraph('Phân đoạn nội dung', style_table_header),
            Paragraph('Người phụ trách', style_table_header),
            Paragraph('Tình trạng & Điểm nhấn nội dung', style_table_header)
        ],
        [
            Paragraph('00:00 – 01:00', style_table_cell_bold),
            Paragraph('<b>Intro & Kiến trúc Tổng thể</b>', style_table_cell),
            Paragraph('Nguyễn Ngọc Bình', style_table_cell),
            Paragraph('<font color="#059669"><b>[ĐÃ QUAY XONG]</b></font> Giới thiệu đề tài, nhóm 9, trình bày sơ đồ End-to-End từ CSV $\\rightarrow$ Mage $\\rightarrow$ SQL $\\rightarrow$ dbt $\\rightarrow$ Power BI + AI.', style_table_cell)
        ],
        [
            Paragraph('01:00 – 03:30', style_table_cell_bold),
            Paragraph('<b>Pipeline ETL Mage.ai & Giám sát</b>', style_table_cell),
            Paragraph('Nguyễn Ngọc Bình', style_table_cell),
            Paragraph('<font color="#059669"><b>[ĐÃ QUAY XONG]</b></font> Mage UI (6790): 126 chunk Parquet, trigger `monthly_incremental`, bảng rejected và nhật ký audit log.', style_table_cell)
        ],
        [
            Paragraph('03:30 – 05:00', style_table_cell_bold),
            Paragraph('<b>Kiểm thử DQC dbt & Kho dữ liệu</b>', style_table_cell),
            Paragraph('Kiều Đỗ Song Tinh', style_table_cell),
            Paragraph('<font color="#059669"><b>[ĐÃ QUAY XONG]</b></font> Chạy `dbt test` đạt PASS 91/91 tests; đối soát Star Schema, bảng cầu `bridge_game_platform` và Fact Composite PK.', style_table_cell)
        ],
        [
            Paragraph('05:00 – 07:00', style_table_cell_bold),
            Paragraph('<b>Dashboard 1: Thời điểm & Mùa vụ</b>', style_table_cell),
            Paragraph('Nguyễn Ngọc Bình', style_table_cell),
            Paragraph('<font color="#059669"><b>[ĐÃ QUAY XONG]</b></font> Chu kỳ tăng trưởng YoY, tháng cao điểm (Th10) vs tháng trũng (Th01, Th06), mật độ ra mắt dịp Steam Sale.', style_table_cell)
        ],
        [
            Paragraph('07:00 – 09:00', style_table_cell_bold),
            Paragraph('<b>Dashboard 2: Định giá & Cạnh tranh</b>', style_table_cell),
            Paragraph('Kiều Đỗ Song Tinh', style_table_cell),
            Paragraph('<font color="#059669"><b>[ĐÃ QUAY XONG]</b></font> Tương quan giảm giá vs CCU, Free vs Paid, thời lượng chơi theo độ tuổi, khoảng giá tối ưu $10–$29.99.', style_table_cell)
        ],
        [
            Paragraph('09:00 – 11:30', style_table_cell_bold),
            Paragraph('<b>Dashboard 3 & 4: Thị phần & Drill-through</b>', style_table_cell),
            Paragraph('Phạm Lê Thanh Tú', style_table_cell),
            Paragraph('<font color="#059669"><b>[ĐÃ QUAY XONG]</b></font> So sánh AAA vs Indie (Indie chiếm 51.7%), độc tôn Windows (99%), Drill-through vào EA (Top 5 game gánh 76% doanh thu).', style_table_cell)
        ],
        [
            Paragraph('11:30 – 13:30', style_table_cell_bold),
            Paragraph('<b>Dashboard 5: Giám sát ETL Observability</b>', style_table_cell),
            Paragraph('Phạm Lê Thanh Tú', style_table_cell),
            Paragraph('<font color="#DC2626"><b>[CẦN QUAY BỔ SUNG]</b></font> Thuyết minh KPI vĩ mô (11 lượt chạy, SLA <60s, tỷ lệ thành công 81.82%), thông lượng bản ghi và thẻ chẩn đoán AI.', style_table_cell)
        ],
        [
            Paragraph('13:30 – 15:00', style_table_cell_bold),
            Paragraph('<b>Dashboard 6 & AI Chatbox Copilot</b>', style_table_cell),
            Paragraph('Phạm Lê Thanh Tú', style_table_cell),
            Paragraph('<font color="#DC2626"><b>[CẦN QUAY BỔ SUNG]</b></font> Thao tác Cây phân rã AI (Decomposition Tree); mở web app (`localhost:5000`) demo Chatbox đàm thoại tự nhiên với Gemini AI.', style_table_cell)
        ],
        [
            Paragraph('Hậu kỳ tổng', style_table_cell_bold),
            Paragraph('<b>Ghép nối, Căn chỉnh & Xuất Video</b>', style_table_cell),
            Paragraph('Nguyễn Ngọc Bình', style_table_cell),
            Paragraph('<font color="#0284C7"><b>[HẬU KỲ TỔNG HỢP]</b></font> Ghép các clip đã có với clip mới từ Tú; chèn slide mở đầu/kết thúc; xuất file video Full HD 1080p chuẩn mực.', style_table_cell)
        ]
    ]

    t_video = Table(video_timeline_data, colWidths=[2.6*cm, 4.4*cm, 3.6*cm, 6.4*cm])
    t_video.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY_COLOR),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,9), (-1,9), colors.HexColor('#EFF6FF')),
    ]))
    story.append(t_video)
    story.append(Spacer(1, 10))

    # ==========================================
    # PHẦN VI: CHECKLIST NGHIỆM THU & MỐC THỜI GIAN
    # ==========================================
    story.append(Paragraph('VI. TIẾN ĐỘ THỰC HIỆN & CHECKLIST NGHIỆM THU NỘP BÀI', style_h1))
    story.append(Paragraph(
        '• <b>Mốc 1 (Trước 18:00 ngày 23/11):</b> Hoàn thành viết và chỉnh sửa nội dung báo cáo theo từng phần phân công; gửi bản Word cho Tinh tổng hợp.<br/>'
        '• <b>Mốc 2 (Trước 20:30 ngày 23/11):</b> Tú hoàn thành quay clip bổ sung Dashboard 5, 6 và AI Chatbox (Full HD 1080p, mic rõ tiếng), gửi cho Bình.<br/>'
        '• <b>Mốc 3 (Trước 22:30 ngày 23/11):</b> Bình hoàn thành ghép nối clip mới vào video tổng có sẵn; Tinh hoàn tất căn chỉnh và xuất bản file Báo cáo PDF; Tú kiểm duyệt lần cuối.<br/>'
        '• <b>Mốc 4 (Đúng hạn quy định):</b> Nhóm trưởng nộp bài lên hệ thống Moodle / Portal môn học.',
        style_body
    ))
    story.append(Spacer(1, 5))

    checklist_data = [
        [
            Paragraph('Hạng mục bàn giao', style_table_header),
            Paragraph('Quy cách chuẩn mực & Tình trạng', style_table_header),
            Paragraph('Người chịu trách nhiệm chính', style_table_header)
        ],
        [
            Paragraph('<b>File Báo cáo Word (.docx) & PDF</b>', style_table_cell_bold),
            Paragraph('Font Times New Roman 12pt, lề chuẩn KHTN, hình ảnh sắc nét, không còn mâu thuẫn giữa 2 giai đoạn, số liệu đồng nhất 100%.', style_table_cell),
            Paragraph('Kiều Đỗ Song Tinh', style_table_cell)
        ],
        [
            Paragraph('<b>Clip quay màn hình Dashboard 5, 6 & AI</b>', style_table_cell_bold),
            Paragraph('Clip bổ sung sắc nét 1080p, thuyết minh rõ ràng Dashboard 5 (Observability), Dashboard 6 (Decomposition Tree) và AI Chatbox (`localhost:5000`).', style_table_cell),
            Paragraph('Phạm Lê Thanh Tú (Nhóm trưởng)', style_table_cell)
        ],
        [
            Paragraph('<b>Video Demo hoàn chỉnh (.mp4)</b>', style_table_cell_bold),
            Paragraph('Ghép nối các phần đã quay sẵn trước đó với clip mới của Tú; căn chỉnh âm lượng đồng đều; xuất file video Full HD 1080p hoàn chỉnh.', style_table_cell),
            Paragraph('Nguyễn Ngọc Bình', style_table_cell)
        ],
        [
            Paragraph('<b>File Power BI Template (.pbix)</b>', style_table_cell_bold),
            Paragraph('Gồm đầy đủ 6 trang Dashboard chuẩn 1920×1080, các Measure DAX không lỗi, cấu hình lọc chéo và drill-through hoàn hảo.', style_table_cell),
            Paragraph('Phạm Lê Thanh Tú', style_table_cell)
        ],
        [
            Paragraph('<b>Mã nguồn GitHub & Container</b>', style_table_cell_bold),
            Paragraph('Toàn bộ repository sạch sẽ, file `README.md` cập nhật chi tiết, Docker Compose khởi động mượt mà không lỗi.', style_table_cell),
            Paragraph('Cả nhóm (Tú chủ trì)', style_table_cell)
        ]
    ]

    t_check = Table(checklist_data, colWidths=[4.2*cm, 8.5*cm, 4.3*cm])
    t_check.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
    ]))
    story.append(t_check)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f'Plan PDF generated successfully: {filename} ({os.path.getsize(filename)} bytes)')


if __name__ == '__main__':
    target_dir = os.path.dirname(os.path.abspath(__file__))
    out_pdf = os.path.join(target_dir, 'KE_HOACH_SUA_BAO_CAO_VA_PHAN_CONG_NHOM_9.pdf')
    build_pdf(out_pdf)
    root_pdf = os.path.join(os.path.dirname(os.path.dirname(target_dir)), 'KE_HOACH_SUA_BAO_CAO_VA_PHAN_CONG_NHOM_9.pdf')
    import shutil
    try:
        shutil.copyfile(out_pdf, root_pdf)
        print(f'Copied to root: {root_pdf}')
    except PermissionError:
        print(f'Note: {root_pdf} is currently open in a PDF viewer. Updated file is at {out_pdf}')
