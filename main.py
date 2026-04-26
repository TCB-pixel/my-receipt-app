import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit, ImageReader
import os
from datetime import datetime

# --- 1. ตั้งค่าหน้าจอ App ---
st.set_page_config(page_title="Game Receipt Pro", layout="wide")

# ปรับ CSS เพื่อให้ส่วน Preview (col_pre) แสดงผลกึ่งกลางและสวยงาม
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
font_path = "NotoSansSC-VariableFont_wght.ttf" 
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
else:
    st.error(f"❌ ไม่พบไฟล์ฟอนต์ {font_path}")

# --- 3. ข้อมูลบริษัท (ปรับชื่อไฟล์ตามที่คุณส่งมา) ---
company_config = {
    "Bandai Namco": {
        "full_name": "BANDAI NAMCO ENTERTAINMENT CO., LTD.",
        "logo_file": "logo.png" #
    },
    "Konami": {
        "full_name": "KONAMI DIGITAL ENTERTAINMENT CO., LTD.",
        "logo_file": "logo konami.png" #
    }
}

currency_config = {
    "JPY (¥)": {"symbol": "¥", "disc_text": "割引", "date_fmt": "%Y年%m月%d日", "thanks": "ありがとうございました"},
    "THB (฿)": {"symbol": "฿", "disc_text": "ส่วนลด", "date_fmt": "%d/%m/%Y", "thanks": "ขอบคุณที่ใช้บริการ"},
    "CNY (¥)": {"symbol": "¥", "disc_text": "折扣", "date_fmt": "%Y年%m月%d日", "thanks": "谢谢光临"},
    "HKD ($)": {"symbol": "$", "disc_text": "Discount", "date_fmt": "%d-%m-%Y", "thanks": "Thank You"}
}

# --- 4. ฟังก์ชันสร้าง PDF ---
def create_pdf(comp_info, basket, curr_info, date_str, time_str):
    file_name = "receipt.pdf"
    symbol = curr_info["symbol"]
    disc_label = curr_info["disc_text"]
    thanks_msg = curr_info["thanks"]
    
    width = 80 * mm
    height = (len(basket) * 35 + 145) * mm 
    c = canvas.Canvas(file_name, pagesize=(width, height))
    curr_y = height - 10*mm

    # จัดการ Logo
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
            display_w = 42 * mm # ปรับขนาดให้พอดี
            display_h = (display_w / img_w) * img_h
            c.drawImage(logo_path, (width - display_w) / 2, curr_y - display_h, width=display_w, height=display_h, mask='auto')
            curr_y -= (display_h + 10*mm)
        except: curr_y -= 5*mm
    else:
        curr_y -= 15*mm

    # หัวใบเสร็จ (ปรับกึ่งกลาง)
    c.setFont(FONT_NAME, 11) 
    c.drawCentredString(width/2, curr_y, comp_info["full_name"])
    curr_y -= 7*mm
    c.setFont(FONT_NAME, 9)
    c.drawCentredString(width/2, curr_y, "TAX INVOICE / RECEIPT")
    curr_y -= 6*mm
    c.setFont(FONT_NAME, 8)
    c.drawCentredString(width/2, curr_y, f"Date: {date_str}   Time: {time_str}")
    curr_y -= 4*mm
    c.line(5*mm, curr_y, width-5*mm, curr_y)
    
    # รายการสินค้า
    curr_y -= 10*mm
    grand_total = 0
    for name, qty, price, discount in basket:
        subtotal = qty * price
        line_total = subtotal - discount
        grand_total += line_total
        c.setFont(FONT_NAME, 10)
        lines = simpleSplit(name, FONT_NAME, 10, 65*mm)
        for line in lines:
            c.drawString(7*mm, curr_y, line); curr_y -= 5*mm
        c.setFont(FONT_NAME, 9)
        c.drawString(10*mm, curr_y, f"{qty} x {symbol}{price:,.2f}")
        c.drawRightString(width-7*mm, curr_y, f"{symbol}{subtotal:,.2f}")
        if discount > 0:
            curr_y -= 4*mm
            c.setFont(FONT_NAME, 8)
            c.drawString(12*mm, curr_y, f"({disc_label})")
            c.drawRightString(width-7*mm, curr_y, f"-{symbol}{discount:,.2f}")
        curr_y -= 10*mm

    # สรุปยอด
    c.line(5*mm, curr_y, width-5*mm, curr_y)
    curr_y -= 10*mm
    c.setFont(FONT_NAME, 14)
    c.drawString(7*mm, curr_y, "TOTAL")
    c.drawRightString(width-7*mm, curr_y, f"{symbol}{grand_total:,.2f}")
    curr_y -= 15*mm
    c.setFont(FONT_NAME, 10)
    c.drawCentredString(width/2, curr_y, thanks_msg)
    c.save()
    return file_name

# --- 5. ส่วน UI (Streamlit) ---
col_in, col_pre = st.columns([1, 1])

with col_in:
    st.subheader("🏢 ตั้งค่าบริษัท")
    selected_comp_name = st.radio("เลือกบริษัท:", list(company_config.keys()), horizontal=True)
    comp_info = company_config[selected_comp_name]

    st.divider()
    st.subheader("📝 รายละเอียด")
    selected_curr = st.selectbox("สกุลเงิน & วันที่:", list(currency_config.keys()))
    curr_info = currency_config[selected_curr]

    c_dt1, c_dt2 = st.columns(2)
    input_date = c_dt1.date_input("วันที่:", datetime.now())
    input_time = c_dt2.text_input("เวลา:", datetime.now().strftime("%H:%M"))
    formatted_date = input_date.strftime(curr_info["date_fmt"])

    if 'basket' not in st.session_state: st.session_state.basket = []

    with st.form("add_item", clear_on_submit=True):
        item_name = st.text_input("ชื่อสินค้า (รองรับภาษาญี่ปุ่น/จีน)")
        c1, c2, c3 = st.columns(3)
        qty = c1.number_input("จำนวน", min_value=1, value=1)
        price = c2.number_input("ราคา", min_value=0.0)
        disc = c3.number_input("ส่วนลด", min_value=0.0)
        if st.form_submit_button("➕ เพิ่มรายการ"):
            st.session_state.basket.append((item_name, qty, price, disc))
            st.rerun()
    
    if st.button("🗑️ ล้างข้อมูลทั้งหมด"):
        st.session_state.basket = []
        st.rerun()

with col_pre:
    st.subheader("👀 Preview (80mm)")
    with st.container(border=True):
        # Logo Preview
        logo_to_show = None
        for ext in ["", ".png", ".jpg"]:
            if os.path.exists(comp_info["logo_file"] + ext):
                logo_to_show = comp_info["logo_file"] + ext
                break
        
        if logo_to_show:
            _, p_m, _ = st.columns([1, 2, 1])
            with p_m: st.image(logo_to_show, use_container_width=True)
        
        # ชื่อบริษัท (บังคับกึ่งกลางด้วย HTML/CSS)
        st.markdown(f"""
            <div class="company-header">
                <span style="font-size: 1.2em; letter-spacing: 0.5px;">{comp_info['full_name']}</span>
            </div>
            <p style='text-align: center; margin: 0; font-size: 0.9em;'>TAX INVOICE / RECEIPT</p>
            <p style='text-align: center; font-size: 0.8em; color: gray; margin-bottom: 10px;'>
                Date: {formatted_date} &nbsp;&nbsp; Time: {input_time}
            </p>
        """, unsafe_allow_html=True)
        
        st.write("---")
        
        total_val = 0
        for n, q, p, d in st.session_state.basket:
            sub = q * p
            total_val += (sub - d)
            st.write(f"**{n}**")
            st.markdown(f"<div style='display: flex; justify-content: space-between;'><span>{q} x {p:,.2f}</span> <span>{curr_info['symbol']}{sub:,.2f}</span></div>", unsafe_allow_html=True)
            if d > 0:
                st.markdown(f"<div style='display: flex; justify-content: space-between; color: #ff4b4b; font-size: 0.9em;'><span>({curr_info['disc_text']})</span> <span>-{curr_info['symbol']}{d:,.2f}</span></div>", unsafe_allow_html=True)
        
        if st.session_state.basket:
            st.write("---")
            st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 1.4em;'><b>TOTAL</b> <b>{curr_info['symbol']}{total_val:,.2f}</b></div>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; margin-top: 30px; font-weight: bold;'>{curr_info['thanks']}</p>", unsafe_allow_html=True)

    if st.session_state.basket:
        if st.button("🚀 บันทึกเป็น PDF"):
            path = create_pdf(comp_info, st.session_state.basket, curr_info, formatted_date, input_time)
            with open(path, "rb") as f:
                st.download_button("💾 Download Receipt", f, file_name=f"receipt_{selected_comp_name.replace(' ', '')}.pdf")
