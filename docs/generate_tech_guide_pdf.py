# -*- coding: utf-8 -*-
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Đăng ký font tiếng Việt
pdfmetrics.registerFont(TTFont('TimesNewRoman', 'C:/Windows/Fonts/times.ttf'))
pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', 'C:/Windows/Fonts/timesbd.ttf'))
pdfmetrics.registerFont(TTFont('TimesNewRoman-Italic', 'C:/Windows/Fonts/timesi.ttf'))
pdfmetrics.registerFont(TTFont('TimesNewRoman-BoldItalic', 'C:/Windows/Fonts/timesbi.ttf'))
pdfmetrics.registerFont(TTFont('Consolas', 'C:/Windows/Fonts/consola.ttf'))

pdfmetrics.registerFontFamily(
    'TimesNewRoman',
    normal='TimesNewRoman',
    bold='TimesNewRoman-Bold',
    italic='TimesNewRoman-Italic',
    boldItalic='TimesNewRoman-BoldItalic'
)

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        print(f'Total pages in Tech Guide PDF: {num_pages}')
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
            self.drawRightString(19.0 * cm, 28.2 * cm, 'HƯỚNG DẪN KỸ THUẬT VẬN HÀNH HỆ THỐNG')
            self.setStrokeColor(colors.HexColor('#CBD5E1'))
            self.setLineWidth(0.5)
            self.line(2.0 * cm, 28.0 * cm, 19.0 * cm, 28.0 * cm)

        # Footer
        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.5)
        self.line(2.0 * cm, 1.8 * cm, 19.0 * cm, 1.8 * cm)
        self.drawString(2.0 * cm, 1.3 * cm, 'Trường ĐH Khoa học Tự nhiên — ĐHQG-HCM | Khoa CNTT')
        self.drawRightString(19.0 * cm, 1.3 * cm, f'Trang {self._pageNumber} / {page_count}')
        self.restoreState()


def build_tech_guide_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm
    )

    styles = getSampleStyleSheet()

    PRIMARY_COLOR = colors.HexColor('#0F4761')
    SECONDARY_COLOR = colors.HexColor('#1E293B')
    ACCENT_COLOR = colors.HexColor('#0369A1')
    TEXT_COLOR = colors.HexColor('#1F2937')
    CODE_BG = colors.HexColor('#F1F5F9')

    style_title = ParagraphStyle(
        'DocTitle',
        fontName='TimesNewRoman-Bold',
        fontSize=16,
        leading=21,
        alignment=1,
        textColor=PRIMARY_COLOR,
        spaceAfter=5
    )

    style_subtitle = ParagraphStyle(
        'DocSubTitle',
        fontName='TimesNewRoman-BoldItalic',
        fontSize=11.5,
        leading=15.5,
        alignment=1,
        textColor=ACCENT_COLOR,
        spaceAfter=12
    )

    style_meta = ParagraphStyle(
        'MetaBox',
        fontName='TimesNewRoman',
        fontSize=9.5,
        leading=13.5,
        textColor=SECONDARY_COLOR
    )

    style_h1 = ParagraphStyle(
        'Heading1_Custom',
        fontName='TimesNewRoman-Bold',
        fontSize=12.5,
        leading=16.5,
        textColor=PRIMARY_COLOR,
        spaceBefore=11,
        spaceAfter=5,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'Heading2_Custom',
        fontName='TimesNewRoman-Bold',
        fontSize=11,
        leading=15,
        textColor=ACCENT_COLOR,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'Body_Custom',
        fontName='TimesNewRoman',
        fontSize=10,
        leading=14,
        textColor=TEXT_COLOR,
        spaceAfter=5
    )

    style_bullet = ParagraphStyle(
        'Bullet_Custom',
        fontName='TimesNewRoman',
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_COLOR,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )

    style_code_box = ParagraphStyle(
        'CodeBox',
        fontName='Consolas',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=3,
        spaceAfter=5
    )

    style_table_header = ParagraphStyle(
        'TableHeader',
        fontName='TimesNewRoman-Bold',
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.white
    )

    style_table_cell = ParagraphStyle(
        'TableCell',
        fontName='TimesNewRoman',
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_COLOR
    )

    style_table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='TimesNewRoman-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_COLOR
    )

    def make_code_table(code_text):
        p = Preformatted(code_text.strip(), style_code_box)
        t = Table([[p]], colWidths=[17.0*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), CODE_BG),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        return t

    story = []

    # HEADER TÀI LIỆU
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
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY_COLOR, spaceAfter=10))

    # TIÊU ĐỀ CHÍNH
    story.append(Paragraph('HƯỚNG DẪN KỸ THUẬT VẬN HÀNH TOÀN DIỆN HỆ THỐNG<br/>STEAM GAMES DWH & BUSINESS INTELLIGENCE', style_title))
    story.append(Paragraph('Pipeline 8 Block Mage.ai, Star Schema SQL Server, Kiểm thử dbt, 6 Dashboards & AI Copilot', style_subtitle))

    # BẢNG THÔNG TIN
    meta_data = [
        [Paragraph('<b>Mục đích tài liệu:</b>', style_meta), Paragraph('Cung cấp quy trình chi tiết từng bước để cài đặt, khởi động, nạp dữ liệu, kiểm thử chất lượng và tương tác trên toàn bộ hệ thống đồ án Kho dữ liệu Steam.', style_meta)],
        [Paragraph('<b>Công nghệ cốt lõi:</b>', style_meta), Paragraph('Docker Compose, Mage.ai (EL), Microsoft SQL Server 2022 (DWH), dbt-sqlserver (Transform), Microsoft Power BI Desktop (Semantic & Dashboards), Google Gemini AI (Copilot).', style_meta)],
        [Paragraph('<b>Nhóm thực hiện:</b>', style_meta), Paragraph('<b>Nhóm 9</b>: Phạm Lê Thanh Tú (Nhóm trưởng) — 23120388 | Nguyễn Ngọc Bình — 23120218 | Kiều Đỗ Song Tinh — 23120373', style_meta)]
    ]
    t_meta = Table(meta_data, colWidths=[3.5*cm, 13.5*cm])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # MỤC 1: KIẾN TRÚC TỔNG THỂ
    story.append(Paragraph('1. KIẾN TRÚC TỔNG THỂ & LUỒNG DỮ LIỆU END-TO-END', style_h1))
    story.append(Paragraph(
        'Hệ thống vận hành theo mô hình <b>ELT (Extract - Load - Transform)</b> hiện đại được container hóa hoàn toàn qua Docker Compose:',
        style_body
    ))
    story.append(Paragraph(
        '• <b>1. Trích xuất & Nạp thô (Mage.ai):</b> Đọc file CSV nguồn (`games.csv` ~401MB), chia nhỏ thành 126 chunk Parquet (1.000 dòng/chunk) để kiểm soát bộ nhớ. Mỗi chunk chạy qua một nhánh động Extract $\\rightarrow$ Validate $\\rightarrow$ Load vào bảng đệm. Sau đó, block `publish_steam_staging` gom các bảng đệm, khử trùng AppID và công bố vào `dbo.stg_steam_games` trong một giao dịch cơ sở dữ liệu duy nhất.',
        style_bullet
    ))
    story.append(Paragraph(
        '• <b>2. Chuyển đổi & Kiểm định (dbt):</b> Khởi tạo schema `dbt_staging` và `dwh`. Làm sạch chuẩn hóa qua `stg_steam_games_cleaned` và nạp vào 5 Dimension, 1 Bridge Table (`bridge_game_platform`) và 1 Fact Table (`fact_game_snapshot`). Tự động thực thi <b>91 bài kiểm thử chất lượng dbt (pass 100%)</b>.',
        style_bullet
    ))
    story.append(Paragraph(
        '• <b>3. Trực quan hóa & Khai phá (Power BI):</b> Kết nối trực tiếp vào schema `dwh` qua cổng 1435, xây dựng Semantic Model với hệ thống thước đo DAX đa tầng và triển khai trọn vẹn <b>6 Dashboard chuẩn 1920×1080 px</b>.',
        style_bullet
    ))
    story.append(Paragraph(
        '• <b>4. Trợ lý Thông minh (AI Copilot):</b> Ứng dụng web độc lập (`http://localhost:5000`) tích hợp mô hình Google Gemini AI và Grounding Engine kết nối trực tiếp cơ sở dữ liệu, cho phép hỏi đáp đàm thoại ngôn ngữ tự nhiên.',
        style_bullet
    ))
    story.append(Spacer(1, 6))

    # MỤC 2: YÊU CẦU HỆ THỐNG
    story.append(Paragraph('2. YÊU CẦU HỆ THỐNG & PHẦN MỀM CẦN THIẾT', style_h1))
    story.append(Paragraph(
        '• <b>Docker Desktop:</b> Cần cấp tối thiểu <b>4 GB RAM</b> cho Docker (SQL Server cần ít nhất 2 GB).<br/>'
        '• <b>Microsoft Power BI Desktop:</b> Để mở tệp `bi_dashboard/Steam_Template.pbix`.<br/>'
        '• <b>Python 3.10+:</b> Cài đặt trên máy Host để khởi chạy ứng dụng Steam Copilot (`steam_copilot.py`) và chạy unit tests.<br/>'
        '• <b>SQL Server Management Studio (SSMS):</b> (Khuyến nghị) Để truy vấn trực tiếp kiểm tra dữ liệu qua cổng `1435`.',
        style_body
    ))
    story.append(Spacer(1, 6))

    # MỤC 3: CẤU HÌNH BIẾN MÔI TRƯỜNG & CHUẨN BỊ DỮ LIỆU
    story.append(Paragraph('3. CẤU HÌNH BIẾN MÔI TRƯỜNG & CHUẨN BỊ DỮ LIỆU', style_h1))
    story.append(Paragraph('<b>Bước 3.1: Tạo file cấu hình `.env`</b>', style_h2))
    story.append(Paragraph('Tại thư mục gốc dự án, sao chép tệp `.env.example` thành `.env`:', style_body))
    story.append(make_code_table('Copy-Item .env.example .env'))
    story.append(Paragraph(
        '<i>Lưu ý:</i> Tệp <font face="Consolas">.env.example</font> đã điền sẵn mật khẩu SQL Server và '
        '<b>Gemini API Key</b> của nhóm để Thầy/Cô và người chấm có thể chạy ngay toàn bộ hệ thống '
        '(Mage ETL, SQL Server, Steam Copilot AI):',
        style_body
    ))
    story.append(make_code_table(
        'MSSQL_PASSWORD=thanhtu185B#2005\n'
        'STEAM_MAGE_PORT=6790\n'
        'GEMINI_API_KEY="AQ.Ab8RN6L_oYEtcnUgYcBlHLWChmcXu6QiusQAfUHxZ_nQwEMa7Q"'
    ))

    story.append(Paragraph('<b>Bước 3.2: Đặt file dữ liệu `games.csv`</b>', style_h2))
    story.append(Paragraph(
        'Tải tập dữ liệu từ Kaggle tại đường dẫn: '
        '<font color="#0369A1"><u>https://www.kaggle.com/datasets/fronkongames/steam-games-dataset</u></font>.<br/>'
        'Giải nén và đặt tệp <font face="Consolas">games.csv</font> vào thư mục <font face="Consolas">data/games.csv</font>. '
        'Kiểm tra mã băm SHA-256 bằng PowerShell:',
        style_body
    ))
    story.append(make_code_table('Get-FileHash data/games.csv -Algorithm SHA256'))
    story.append(Paragraph('<i>Mã băm chuẩn đối chiếu:</i> <font face="Consolas" size="8">343b59ffe6422f69eaf1d371779565679fc23fc76eee9de65e23121d21a49b00</font>', style_body))
    story.append(Spacer(1, 6))

    # MỤC 4: KHỞI ĐỘNG HỆ THỐNG DOCKER
    story.append(Paragraph('4. KHỞI ĐỘNG HỆ THỐNG CONTAINER DOCKER', style_h1))
    story.append(Paragraph('Mở PowerShell tại thư mục gốc và thực thi lệnh khởi động:', style_body))
    story.append(make_code_table(
        '# Khởi động toàn bộ container chạy ngầm\n'
        'docker compose up -d --build\n\n'
        '# Kiểm tra trạng thái hoạt động\n'
        'docker compose ps'
    ))
    story.append(Paragraph(
        '<b>Cơ chế Khởi tạo Tự động (Bootstrap):</b> Container `mage` sẽ tự động thực thi script `database_setup/bootstrap.py` để tạo cơ sở dữ liệu `steam_games_DWH`, các schema `dbo`, `dwh`, `dbt_staging`, các bảng audit, watermark, rejected và toàn bộ cấu trúc Star Schema có ràng buộc khóa ngoại.',
        style_body
    ))
    story.append(Paragraph('Kiểm tra log sẵn sàng của Database bằng lệnh:', style_body))
    story.append(make_code_table('docker compose logs mage | Select-String "Steam database schema ready."'))

    # Bảng port
    ports_data = [
        [Paragraph('Dịch vụ', style_table_header), Paragraph('Cổng truy cập Host', style_table_header), Paragraph('Tài khoản / Thông tin', style_table_header), Paragraph('Chức năng chính', style_table_header)],
        [Paragraph('<b>Mage UI</b>', style_table_cell_bold), Paragraph('`http://localhost:6790`', style_table_cell), Paragraph('Không cần đăng nhập', style_table_cell), Paragraph('Điều phối pipeline, theo dõi 8 blocks và triggers', style_table_cell)],
        [Paragraph('<b>SQL Server</b>', style_table_cell_bold), Paragraph('`localhost,1435`', style_table_cell), Paragraph('User: `sa` | Mật khẩu: trong `.env`', style_table_cell), Paragraph('Lưu trữ Staging, Rejected và Data Warehouse', style_table_cell)],
        [Paragraph('<b>AI Copilot Web</b>', style_table_cell_bold), Paragraph('`http://localhost:5000`', style_table_cell), Paragraph('Không cần đăng nhập', style_table_cell), Paragraph('Giám sát ETL trực quan & Chatbox Gemini AI', style_table_cell)],
    ]
    t_ports = Table(ports_data, colWidths=[3.2*cm, 4.0*cm, 4.5*cm, 5.3*cm])
    t_ports.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
    ]))
    story.append(Spacer(1, 4))
    story.append(t_ports)
    story.append(Spacer(1, 8))

    # MỤC 5: VẬN HÀNH PIPELINE TRÊN MAGE.AI
    story.append(Paragraph('5. VẬN HÀNH PIPELINE DATA INGESTION & TRANSFORMATION', style_h1))
    story.append(Paragraph('<b>Bước 5.1: Truy cập Mage UI & Thiết lập thông số</b>', style_h2))
    story.append(Paragraph(
        '1. Mở trình duyệt truy cập: <font color="#0284C7"><b>http://localhost:6790</b></font>.<br/>'
        '2. Chọn pipeline <b>`steam_staging_pipeline`</b>.<br/>'
        '3. Trong mục Variables, đảm bảo các biến điều khiển như sau:',
        style_body
    ))
    story.append(make_code_table(
        'run_mode: full                  # Chọn full (khởi tạo) hoặc incremental (định kỳ)\n'
        'source_file: data/games.csv\n'
        'chunk_size: 1000                # Giữ nguyên 1000 dòng/chunk để tối ưu bộ nhớ\n'
        'demo_lset: null                 # Đặt null (batch quản lý tự động theo row_hash)\n'
        'demo_cet: null\n'
        'dbt_timeout_seconds: 3600'
    ))

    story.append(Paragraph('<b>Bước 5.2: Chạy Pipeline Full Load / Incremental Load</b>', style_h2))
    story.append(Paragraph(
        '• <b>Chạy Full Load:</b> Chọn tab <b>Triggers</b> $\\rightarrow$ Nhấp chọn trigger chạy 1 lần $\\rightarrow$ Bấm <b>Run now</b>. Pipeline sẽ chia 126 chunk, nạp thô vào buffer, khử trùng AppID trong giao dịch, tự động gọi dbt build và đối soát 17 phép kiểm tra DWH.<br/>'
        '• <b>Chạy Incremental Load:</b> Đổi biến `run_mode: incremental`. Pipeline sẽ so khớp `AppID` và hàm băm `row_hash` (SHA-256). Chỉ các game mới hoặc có thay đổi mới được MERGE; thời gian nạp chỉ mất <b>3 – 25 giây</b>.<br/>'
        '• <b>Lập lịch tự động (Cron):</b> File `triggers.yaml` đã tích hợp 2 schedule triggers: `monthly_incremental` (07:00 ngày 1 hàng tháng) và `test_every_15_min` (chạy mỗi 15 phút, bật tạm để demo).',
        style_body
    ))
    story.append(Spacer(1, 6))

    # MỤC 6: KIỂM THỬ CHẤT LƯỢNG & ĐỐI SOÁT
    story.append(Paragraph('6. KIỂM THỬ CHẤT LƯỢNG DỮ LIỆU & ĐỐI SOÁT DWH', style_h1))
    story.append(Paragraph('<b>Bước 6.1: Chạy 91 bài kiểm thử dbt (Data Quality Tests)</b>', style_h2))
    story.append(Paragraph('Thực thi lệnh sau trên PowerShell để kiểm tra toàn bộ 91 ràng buộc logic của DWH:', style_body))
    story.append(make_code_table('docker compose run --rm --no-deps dbt test'))
    story.append(Paragraph('<i>Kết quả chuẩn:</i> <font face="Consolas" size="8">Done. PASS=91 WARN=0 ERROR=0 SKIP=0 TOTAL=91</font> (Đạt 100%).', style_body))

    story.append(Paragraph('<b>Bước 6.2: Chạy 32 bài kiểm thử tự động Python (Unit Tests)</b>', style_h2))
    story.append(Paragraph('Kiểm tra logic chunking, audit log và kiểm soát lỗi:', style_body))
    story.append(make_code_table('python -m unittest discover tests'))
    story.append(Paragraph('<i>Kết quả chuẩn:</i> <font face="Consolas" size="8">Ran 32 tests in ...s — OK</font>.', style_body))

    story.append(Paragraph('<b>Bước 6.3: Truy vấn đối soát số liệu chuẩn trên SQL Server (SSMS)</b>', style_h2))
    story.append(Paragraph('Kết nối SSMS vào `localhost,1435` (sa / password) và thực thi script kiểm tra:', style_body))
    story.append(make_code_table(
        'USE steam_games_DWH;\n'
        '-- 1. Đối soát số dòng khớp tuyệt đối 125.856 dòng\n'
        'SELECT \'stg_steam_games\' AS tbl, COUNT(*) AS rows FROM dbo.stg_steam_games\n'
        'UNION ALL SELECT \'fact_game_snapshot\', COUNT(*) FROM dwh.fact_game_snapshot\n'
        'UNION ALL SELECT \'dim_game\', COUNT(*) FROM dwh.dim_game\n'
        'UNION ALL SELECT \'bridge_game_platform\', COUNT(*) FROM dwh.bridge_game_platform; -- 163.600 dòng\n\n'
        '-- 2. Kiểm tra 8 bản ghi lỗi bị cô lập trong bảng rejected\n'
        'SELECT reason_code, COUNT(*) FROM dbo.stg_steam_games_rejected GROUP BY reason_code;'
    ))
    story.append(Spacer(1, 6))

    # MỤC 7: KHỞI CHẠY POWER BI
    story.append(Paragraph('7. KHỞI CHẠY HỆ THỐNG BI DASHBOARD (POWER BI)', style_h1))
    story.append(Paragraph(
        '1. Mở phần mềm <b>Power BI Desktop</b>.<br/>'
        '2. Mở file báo cáo mẫu: <b>`bi_dashboard/Steam_Template.pbix`</b>.<br/>'
        '3. <b>Cấu hình kết nối nguồn dữ liệu (nếu đổi mật khẩu):</b><br/>'
        '   • Chọn <i>Transform data</i> $\\rightarrow$ <i>Data source settings</i> $\\rightarrow$ <i>Change Source...</i><br/>'
        '   • Nhập Server: <b>`localhost,1435`</b> | Database: <b>`steam_games_DWH`</b>.<br/>'
        '   • Chọn mục <i>Database</i> $\\rightarrow$ Nhập User: <b>`sa`</b> và Password trong `.env`.<br/>'
        '4. Bấm nút <b>Refresh</b> trên thanh công cụ để cập nhật toàn bộ 125.856 tựa game.<br/>'
        '5. <b>Trải nghiệm 6 trang Dashboard trực quan:</b><br/>'
        '   • <i>Trang 1 — Overview & Mùa vụ:</i> Phân tích chu kỳ YoY, tháng cao điểm Th10 và các đợt Steam Sale.<br/>'
        '   • <i>Trang 2 — Hiệu suất & Định giá:</i> Tương quan giảm giá vs Peak CCU, cơ cấu Free vs Paid, dải độ tuổi.<br/>'
        '   • <i>Trang 3 — Nhà phát hành & Nền tảng:</i> Nghịch lý doanh thu Indie (51,7%), độc tôn Windows (79,1%).<br/>'
        '   • <i>Trang 4 — Chi tiết game (Drill-through):</i> Click chuột phải vào Nhà phát hành (như EA) $\\rightarrow$ Drill-through sang trang 4 xem danh mục 134 game chi tiết và Ma trận BCG.<br/>'
        '   • <i>Trang 5 — Giám sát ETL Observability:</i> Theo dõi SLA thời lượng chạy, throughput và thẻ chẩn đoán AI.<br/>'
        '   • <i>Trang 6 — Trợ lý AI & Cây phân rã:</i> Thao tác Cây phân rã AI giải phẫu luồng doanh thu >38 tỷ USD; bấm nút <i>"MỞ AI CHATBOX"</i> mở web app.',
        style_body
    ))
    story.append(Spacer(1, 6))

    # MỤC 8: KHỞI CHẠY AI COPILOT
    story.append(Paragraph('8. KHỞI CHẠY TRỢ LÝ AI COPILOT WEB APP (PORT 5000)', style_h1))
    story.append(Paragraph('Mở một cửa sổ PowerShell mới tại máy host và chạy lệnh:', style_body))
    story.append(make_code_table('python bi_dashboard/steam_copilot.py'))
    story.append(Paragraph(
        'Mở trình duyệt web truy cập địa chỉ: <font color="#0284C7"><b>http://localhost:5000</b></font>.<br/>'
        '• <b>Phân hệ Giám sát ETL:</b> Xem biểu đồ trực quan thông lượng nạp, thời gian chạy SLA và tỷ lệ thành công.<br/>'
        '• <b>Phân hệ AI Chatbox:</b> Nhập câu hỏi tự nhiên để trò chuyện với Gemini AI (Ví dụ: <i>"Tôi là studio Indie thì nên phát hành game vào tháng nào để ít bị cạnh tranh?"</i> hoặc <i>"Top 5 tựa game đóng góp doanh thu lớn nhất cho Electronic Arts là gì?"</i>).',
        style_body
    ))
    story.append(Spacer(1, 6))

    # MỤC 9: XỬ LÝ SỰ CỐ THƯỜNG GẶP
    story.append(Paragraph('9. HƯỚNG DẪN XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)', style_h1))
    trouble_data = [
        [Paragraph('Tình huống sự cố', style_table_header), Paragraph('Nguyên nhân khả dĩ', style_table_header), Paragraph('Giải pháp khắc phục', style_table_header)],
        [Paragraph('<b>Lỗi xung đột cổng (1435 hoặc 6790)</b>', style_table_cell_bold), Paragraph('Cổng đang bị phần mềm khác chiếm dụng trên máy.', style_table_cell), Paragraph('Đổi cổng `1435:1433` thành `1436:1433` trong `docker-compose.yml` hoặc đổi cổng Mage qua biến `STEAM_MAGE_PORT=6791` trong `.env`.', style_table_cell)],
        [Paragraph('<b>Lỗi kết nối SQL Server (Login failed)</b>', style_table_cell_bold), Paragraph('Mật khẩu sa trong container khác với file `.env`.', style_table_cell), Paragraph('Xóa volume cũ: `docker compose down -v` rồi khởi động lại: `docker compose up -d --build`.', style_table_cell)],
        [Paragraph('<b>Pipeline bị OOM (Out of Memory)</b>', style_table_cell_bold), Paragraph('RAM cấp cho Docker Desktop bị thiếu (<4GB).', style_table_cell), Paragraph('Vào Docker Desktop $\\rightarrow$ Settings $\\rightarrow$ Resources $\\rightarrow$ Nâng RAM lên tối thiểu 4GB. Giữ `chunk_size: 1000`.', style_table_cell)],
        [Paragraph('<b>Chatbox AI không phản hồi</b>', style_table_cell_bold), Paragraph('Chưa có Gemini API Key hoặc mất mạng.', style_table_cell), Paragraph('Hệ thống có **Grounding Engine tự động fallback**: Vẫn tự động truy vấn bảng `dbo.dashboard_ai_insights` để phản hồi mà không bị lỗi.', style_table_cell)],
    ]
    t_trouble = Table(trouble_data, colWidths=[4.2*cm, 5.0*cm, 7.8*cm])
    t_trouble.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY_COLOR),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F8FAFC')),
    ]))
    story.append(t_trouble)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f'Tech Guide PDF generated successfully: {filename} ({os.path.getsize(filename)} bytes)')


if __name__ == '__main__':
    target_dir = os.path.dirname(os.path.abspath(__file__))
    out_pdf = os.path.join(target_dir, 'HUONG_DAN_KY_THUAT_CHAY_DU_AN.pdf')
    build_tech_guide_pdf(out_pdf)
    root_pdf = os.path.join(os.path.dirname(target_dir), 'HUONG_DAN_KY_THUAT_CHAY_DU_AN.pdf')
    import shutil
    try:
        shutil.copyfile(out_pdf, root_pdf)
        print(f'Copied to root: {root_pdf}')
    except Exception as e:
        print(f'Note: {e}')
