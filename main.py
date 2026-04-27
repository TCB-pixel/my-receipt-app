import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit, ImageReader
import os
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 1. ตั้งค่าหน้าจอ App ---
st.set_page_config(page_title="Game Receipt Pro", layout="wide")

st.markdown("""
    <style>
    .reportview-container .main .block-container { max-width: 1200px; }
    .company-header {
        width: 100%;
        text-align: center;
        font-weight: bold;
        line-height: 1.2;
        margin-bottom: 5px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🖨️ เครื่องสร้างใบเสร็จ (Official Co., Ltd. Edition)")

# --- 2. ลงทะเบียน Font ---
FONT_NAME = "GlobalFont"
font_path = os.path.join(BASE_DIR, "NotoSansSC-VariableFont_wght.ttf")
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
else:
    st.error(f"❌ ไม่พบไฟล์ฟอนต์ {font_path}")

# --- 3. ข้อมูลบริษัท ---
company_config = {
    "Bandai Namco": {
        "full_name": "BANDAI NAMCO ENTERTAINMENT CO., LTD.",
        "logo_file": os.path.join(BASE_DIR, "logo_Bandai")
    },
    "Konami": {
        "full_name": "KONAMI DIGITAL ENTERTAINMENT CO., LTD.",
        "logo_file": os.path.join(BASE_DIR, "logo_konami")
    }
}

currency_config = {
    "JPY (¥)": {"symbol": "¥", "disc_text": "割引", "date_fmt": "%Y年%m月%d日", "thanks": "ありがとうございました"},
    "THB (฿)": {"symbol": "฿", "disc_text": "ส่วนลด", "date_fmt": "%d/%m/%Y", "thanks": "ขอบคุณที่ใช้บริการ"},
    "CNY (¥)": {"symbol": "¥", "disc_text": "折扣", "date_fmt": "%Y年%m月%d日", "thanks": "谢谢光临"},
    "HKD ($)": {"symbol": "$", "disc_text": "Discount", "date_fmt": "%d-%m-%Y", "thanks": "Thank You"}
}

# --- 4. ฟังก์ชันแปลงปี ค.ศ. → ปฏิทินญี่ปุ่น (元号) ---
def to_japanese_era(d: date) -> str:
    eras = [
        (date(2019, 5, 1),  "令和", 2019),
        (date(1989, 1, 8),  "平成", 1989),
        (date(1926, 12, 25),"昭和", 1926),
        (date(1912, 7, 30), "大正", 1912),
        (date(1868, 1, 25), "明治", 1868),
    ]
    for start, kanji, base_year in eras:
        if d >= start:
            era_year = d.year - base_year + 1
            year_str = "元年" if era_year == 1 else f"{era_year}年"
            return f"{kanji}{year_str}{d.month}月{d.day}日"
    return d.strftime("%Y年%m月%d日")

def to_japanese_era_full(d: date) -> str:
    """令和7年4月27日（2025年） — แสดงทั้ง 元号 + ค.ศ."""
    return f"{to_japanese_era(d)}（{d.year}年）"

# --- 5. ฟังก์ชันสร้าง PDF ---
def create_pdf(comp_info, address_lines, receipt_date, basket, curr_info,
               time_str, member_pct, rakuten_pts):
    file_name = "receipt.pdf"
    symbol = curr_info["symbol"]
    disc_label = curr_info["disc_text"]
    thanks_msg = curr_info["thanks"]

    width = 80 * mm
    extra = 60 + (len([l for l in address_lines if l.strip()]) * 6)
    extra += 10 if member_pct > 0 else 0
    extra += 10 if rakuten_pts > 0 else 0
    height = (len(basket) * 35 + extra + 145) * mm
    c = canvas.Canvas(file_name, pagesize=(width, height))
    curr_y = height - 10 * mm

    # Logo
    logo_name = comp_info["logo_file"]
    logo_path = None
    for ext in ["", ".png", ".jpg"]:
        if os.path.exists(logo_name + ext):
            logo_path = logo_name + ext
            break

    if logo_path:
        try:
            img = ImageReader(logo_path)
            img_w, img_h = img.getSize()
            display_w = 42 * mm
            display_h = (display_w / img_w) * img_h
            c.drawImage(logo_path, (width - display_w) / 2, curr_y - display_h,
                        width=display_w, height=display_h, mask='auto')
            curr_y -= (display_h + 10 * mm)
        except:
            curr_y -= 5 * mm
    else:
        curr_y -= 15 * mm

    # ชื่อบริษัท
    c.setFont(FONT_NAME, 11)
    c.drawCentredString(width / 2, curr_y, comp_info["full_name"])
    curr_y -= 7 * mm

    # ที่อยู่ (รูปแบบญี่ปุ่น)
    c.setFont(FONT_NAME, 8)
    for line in address_lines:
        if line.strip():
            c.drawCentredString(width / 2, curr_y, line.strip())
            curr_y -= 5 * mm
    curr_y -= 2 * mm

    # TAX INVOICE
    c.setFont(FONT_NAME, 9)
    c.drawCentredString(width / 2, curr_y, "TAX INVOICE / RECEIPT")
    curr_y -= 6 * mm

    # วันที่ — ปฏิทินญี่ปุ่น + ค.ศ.
    era_str = to_japanese_era_full(receipt_date)
    c.setFont(FONT_NAME, 8)
    c.drawCentredString(width / 2, curr_y, f"{era_str}　{time_str}")
    curr_y -= 4 * mm
    c.line(5 * mm, curr_y, width - 5 * mm, curr_y)

    # รายการสินค้า
    curr_y -= 10 * mm
    subtotal_items = 0
    for name, qty, price, discount in basket:
        subtotal = qty * price
        line_total = subtotal - discount
        subtotal_items += line_total

        c.setFont(FONT_NAME, 10)
        lines = simpleSplit(name, FONT_NAME, 10, 65 * mm)
        for line in lines:
            c.drawString(7 * mm, curr_y, line)
            curr_y -= 5 * mm

        c.setFont(FONT_NAME, 9)
        c.drawString(10 * mm, curr_y, f"{qty} x {symbol}{price:,.2f}")
        c.drawRightString(width - 7 * mm, curr_y, f"{symbol}{subtotal:,.2f}")

        if discount > 0:
            curr_y -= 4 * mm
            c.setFont(FONT_NAME, 8)
            c.drawString(12 * mm, curr_y, f"({disc_label})")
            c.drawRightString(width - 7 * mm, curr_y, f"-{symbol}{discount:,.2f}")
        curr_y -= 10 * mm

    # เส้นคั่น + Subtotal
    c.line(5 * mm, curr_y, width - 5 * mm, curr_y)
    curr_y -= 8 * mm

    grand_total = subtotal_items

    # ส่วนลด Member
    member_disc_amt = 0
    if member_pct > 0:
        member_disc_amt = subtotal_items * (member_pct / 100)
        grand_total -= member_disc_amt
        c.setFont(FONT_NAME, 9)
        c.drawString(7 * mm, curr_y, f"会員割引 {member_pct}% OFF")
        c.drawRightString(width - 7 * mm, curr_y, f"-{symbol}{member_disc_amt:,.2f}")
        curr_y -= 7 * mm

    # ส่วนลด Rakuten Points
    if rakuten_pts > 0:
        grand_total -= rakuten_pts
        c.setFont(FONT_NAME, 9)
        c.drawString(7 * mm, curr_y, f"楽天ポイント利用 ({rakuten_pts:,} pt)")
        c.drawRightString(width - 7 * mm, curr_y, f"-{symbol}{rakuten_pts:,.2f}")
        curr_y -= 7 * mm

    if member_pct > 0 or rakuten_pts > 0:
        c.line(5 * mm, curr_y, width - 5 * mm, curr_y)
        curr_y -= 8 * mm

    # ยอดรวม
    c.setFont(FONT_NAME, 14)
    c.drawString(7 * mm, curr_y, "合計 TOTAL")
    c.drawRightString(width - 7 * mm, curr_y, f"{symbol}{grand_total:,.2f}")
    curr_y -= 15 * mm

    c.setFont(FONT_NAME, 10)
    c.drawCentredString(width / 2, curr_y, thanks_msg)
    c.save()
    return file_name


# ============================================================
# --- 6. UI ---
# ============================================================
col_in, col_pre = st.columns([1, 1])

with col_in:
    st.subheader("🏢 ตั้งค่าบริษัท")
    selected_comp_name = st.radio("เลือกบริษัท:", list(company_config.keys()), horizontal=True)
    comp_info = company_config[selected_comp_name]

    st.divider()
    st.subheader("📝 รายละเอียด")
    selected_curr = st.selectbox("สกุลเงิน:", list(currency_config.keys()))
    curr_info = currency_config[selected_curr]

    # วันที่ + เวลา
    c_dt1, c_dt2 = st.columns(2)
    input_date = c_dt1.date_input("วันที่:", datetime.now())
    input_time = c_dt2.text_input("เวลา:", datetime.now().strftime("%H:%M"))

    # Preview ปฏิทินญี่ปุ่น
    era_preview = to_japanese_era_full(input_date)
    st.caption(f"📅 ปฏิทินญี่ปุ่น: **{era_preview}**")

    st.divider()

    # ที่อยู่รูปแบบญี่ปุ่น
    st.subheader("🏢 ที่อยู่ร้าน (รูปแบบญี่ปุ่น)")
    addr_postal     = st.text_input("รหัสไปรษณีย์ (〒)", "〒163-0566")
    addr_prefecture = st.text_input("จังหวัด (都道府県)", "東京都")
    addr_city       = st.text_input("เมือง/เขต (市区町村)", "新宿区西新宿")
    addr_street     = st.text_input("ถนน/อาคาร (番地・建物名)", "1丁目26番2号　新宿野村ビル")
    addr_tel        = st.text_input("เบอร์โทร (TEL)", "TEL: 03-1234-5678")

    address_lines = [
        addr_postal,
        f"{addr_prefecture}{addr_city}",
        addr_street,
        addr_tel,
    ]

    st.divider()

    # ส่วนลดพิเศษ
    st.subheader("🎫 ส่วนลดพิเศษ")
    disc_col1, disc_col2 = st.columns(2)
    with disc_col1:
        member_pct = st.selectbox(
            "ส่วนลด Member",
            options=[0, 5, 10, 15, 20],
            format_func=lambda x: "ไม่มี" if x == 0 else f"{x}% OFF"
        )
    with disc_col2:
        rakuten_pts = st.number_input(
            "Rakuten Point (1pt = 1¥)",
            min_value=0, step=100, value=0
        )
    if rakuten_pts > 0:
        st.caption(f"💎 ใช้ {rakuten_pts:,} pt = ลด {curr_info['symbol']}{rakuten_pts:,.2f}")

    st.divider()

    # รายการสินค้า
    st.subheader("🛒 รายการสินค้า")
    if 'basket' not in st.session_state:
        st.session_state.basket = []

    with st.form("add_item", clear_on_submit=True):
        item_name = st.text_input("ชื่อสินค้า (รองรับภาษาญี่ปุ่น/จีน)")
        c1, c2, c3 = st.columns(3)
        qty  = c1.number_input("จำนวน", min_value=1, value=1)
        price = c2.number_input("ราคา", min_value=0.0)
        disc  = c3.number_input("ส่วนลด", min_value=0.0)
        if st.form_submit_button("➕ เพิ่มรายการ"):
            st.session_state.basket.append((item_name, qty, price, disc))
            st.rerun()

    if st.button("🗑️ ล้างข้อมูลทั้งหมด"):
        st.session_state.basket = []
        st.rerun()


# ============================================================
# Preview Panel
# ============================================================
with col_pre:
    st.subheader("👀 Preview (80mm)")
    formatted_date = input_date.strftime(curr_info["date_fmt"])

    with st.container(border=True):
        # Logo
        logo_to_show = None
        for ext in ["", ".png", ".jpg"]:
            if os.path.exists(comp_info["logo_file"] + ext):
                logo_to_show = comp_info["logo_file"] + ext
                break

        if logo_to_show:
            _, p_m, _ = st.columns([1, 2, 1])
            with p_m:
                st.image(logo_to_show, use_container_width=True)

        # ชื่อบริษัท
        st.markdown(
            f"<div class='company-header'>"
            f"<span style='font-size:1.1em;letter-spacing:0.5px;'>{comp_info['full_name']}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        # ที่อยู่
        for line in address_lines:
            if line.strip():
                st.markdown(
                    f"<p style='text-align:center;font-size:0.75em;margin:1px 0;color:#aaa;'>{line}</p>",
                    unsafe_allow_html=True
                )

        # วันที่ปฏิทินญี่ปุ่น
        st.markdown(
            f"<p style='text-align:center;font-size:0.9em;margin:6px 0 2px 0;'>TAX INVOICE / RECEIPT</p>"
            f"<p style='text-align:center;font-size:0.8em;color:gray;margin-bottom:8px;'>"
            f"📅 {era_preview} &nbsp; {input_time}</p>",
            unsafe_allow_html=True
        )
        st.write("---")

        # รายการสินค้า
        subtotal_val = 0
        for n, q, p, d in st.session_state.basket:
            sub = q * p
            subtotal_val += (sub - d)
            st.write(f"**{n}**")
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;'>"
                f"<span>{q} x {p:,.2f}</span>"
                f"<span>{curr_info['symbol']}{sub:,.2f}</span></div>",
                unsafe_allow_html=True
            )
            if d > 0:
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"color:#ff4b4b;font-size:0.9em;'>"
                    f"<span>({curr_info['disc_text']})</span>"
                    f"<span>-{curr_info['symbol']}{d:,.2f}</span></div>",
                    unsafe_allow_html=True
                )

        if st.session_state.basket:
            st.write("---")

            grand_total_val = subtotal_val

            # Member Discount
            if member_pct > 0:
                m_disc = subtotal_val * (member_pct / 100)
                grand_total_val -= m_disc
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"color:orange;font-size:0.9em;'>"
                    f"<span>🏷️ 会員割引 {member_pct}% OFF</span>"
                    f"<span>-{curr_info['symbol']}{m_disc:,.2f}</span></div>",
                    unsafe_allow_html=True
                )

            # Rakuten Points
            if rakuten_pts > 0:
                grand_total_val -= rakuten_pts
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"color:#bf5700;font-size:0.9em;'>"
                    f"<span>💎 楽天ポイント ({rakuten_pts:,} pt)</span>"
                    f"<span>-{curr_info['symbol']}{rakuten_pts:,.2f}</span></div>",
                    unsafe_allow_html=True
                )

            if member_pct > 0 or rakuten_pts > 0:
                st.write("---")

            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-size:1.4em;'>"
                f"<b>合計 TOTAL</b>"
                f"<b>{curr_info['symbol']}{grand_total_val:,.2f}</b></div>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<p style='text-align:center;margin-top:20px;font-weight:bold;'>"
                f"{curr_info['thanks']}</p>",
                unsafe_allow_html=True
            )

    # ปุ่ม PDF
    if st.session_state.basket:
        if st.button("🚀 บันทึกเป็น PDF"):
            path = create_pdf(
                comp_info=comp_info,
                address_lines=address_lines,
                receipt_date=input_date,
                basket=st.session_state.basket,
                curr_info=curr_info,
                time_str=input_time,
                member_pct=member_pct,
                rakuten_pts=rakuten_pts,
            )
            with open(path, "rb") as f:
                st.download_button(
                    "💾 Download Receipt",
                    f,
                    file_name=f"receipt_{selected_comp_name.replace(' ', '')}.pdf"
                )