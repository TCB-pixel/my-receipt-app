import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit, ImageReader
import os
import pandas as pd
from datetime import datetime
import base64
import barcode
from barcode.writer import ImageWriter
import qrcode

# --- 1. ตั้งค่าหน้าจอ App ---
st.set_page_config(page_title="Professional Receipt Pro + History", layout="wide")

# --- 2. ลงทะเบียน Font ---
FONT_NAME = "GlobalFont"
font_path = "NotoSansSC-VariableFont_wght.ttf" 
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
else:
    st.error(f"❌ ไม่พบไฟล์ฟอนต์ {font_path}")

# --- 3. ฟังก์ชันหาธาตุประจำวัน (เฉพาะ JPY และ CNY) ---
def get_daily_element(date_obj, currency):
    elements_lang = {
        "JPY (¥)": {0: "地のエレメント", 1: "風のエレメント", 2: "水のエレメント", 3: "火のエレメント", 4: "混合エレメント", 5: "究極の火", 6: "金のエレメント"},
        "CNY (¥)": {0: "土元素", 1: "风元素", 2: "水元素", 3: "火元素", 4: "混合元素", 5: "烈火元素", 6: "金元素"}
    }
    return elements_lang.get(currency, {}).get(date_obj.weekday(), "")

# --- 4. ข้อมูลบริษัทแบบละเอียด ---
company_config = {
    "Bandai Namco": {
        "full_name": "BANDAI NAMCO ENTERTAINMENT CO., LTD.",
        "address": "5-37-8 Shiba, Minato-ku, Tokyo, Japan",
        "tel": "03-6744-4000",
        "tax_id": "T5010401136065",
        "logo_file": "logo.png"
    },
    "Konami": {
        "full_name": "KONAMI DIGITAL ENTERTAINMENT CO., LTD.",
        "address": "1-11-1 Ginza, Chuo-ku, Tokyo, Japan",
        "tel": "03-5771-0511",
        "tax_id": "T7010401060341",
        "logo_file": "logo konami.png"
    }
}

currency_config = {
    "JPY (¥)": {"symbol": "¥", "disc_text": "割引", "date_fmt": "%Y年%m月%d日", "thanks": "ありがとうございました"},
    "THB (฿)": {"symbol": "฿", "disc_text": "ส่วนลด", "date_fmt": "%d/%m/%Y", "thanks": "ขอบคุณที่ใช้บริการ"},
    "CNY (¥)": {"symbol": "¥", "disc_text": "折扣", "date_fmt": "%Y年%m月%d日", "thanks": "谢谢光临"}
}

# --- 5. ฟังก์ชันสร้าง PDF ---
def create_pdf(comp_info, basket, curr_info, date_str, time_str, element, curr_name):
    file_name = "receipt_temp.pdf"
    width = 80 * mm
    dynamic_h = (len(basket) * 20) + 160
    height = dynamic_h * mm 
    c = canvas.Canvas(file_name, pagesize=(width, height))
    curr_y = height - 10*mm

    # Logo
    logo_path = comp_info["logo_file"]
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            img_w, img_h = img.getSize()
            display_w = 30 * mm
            display_h = (display_w / img_w) * img_h
            c.drawImage(logo_path, (width - display_w) / 2, curr_y - display_h, width=display_w, height=display_h, mask='auto')
            curr_y -= (display_h + 8*mm)
        except: curr_y -= 5*mm

    # Header แบบละเอียด
    c.setFont(FONT_NAME, 10); c.drawCentredString(width/2, curr_y, comp_info["full_name"]); curr_y -= 6*mm
    c.setFont(FONT_NAME, 7)
    c.drawCentredString(width/2, curr_y, comp_info["address"]); curr_y -= 4*mm
    c.drawCentredString(width/2, curr_y, f"TEL: {comp_info['tel']}"); curr_y -= 4*mm
    c.drawCentredString(width/2, curr_y, f"TAX ID: {comp_info['tax_id']}"); curr_y -= 4*mm
    
    display_date = f"Date: {date_str}  Time: {time_str}"
    if element: display_date += f" ({element})"
    c.drawCentredString(width/2, curr_y, display_date); curr_y -= 5*mm

    # Barcode
    try:
        bc_class = barcode.get_barcode_class('code128')
        bc_obj = bc_class("SSP2TJJ1PQB4", writer=ImageWriter())
        bc_obj.save("temp_bc", options={"module_height": 5, "font_size": 1, "text_distance": 1})
        c.drawImage("temp_bc.png", (width-55*mm)/2, curr_y-12*mm, width=55*mm, height=12*mm)
        curr_y -= 15*mm
    except: pass

    c.line(5*mm, curr_y, width-5*mm, curr_y); curr_y -= 8*mm
    
    # Items
    grand_total = 0
    for name, qty, price, discount in basket:
        subtotal = qty * price
        line_total = subtotal - discount
        grand_total += line_total
        
        c.setFont(FONT_NAME, 9)
        lines = simpleSplit(name, FONT_NAME, 9, 60*mm)
        for line in lines:
            c.drawString(7*mm, curr_y, line); curr_y -= 5*mm
        
        c.setFont(FONT_NAME, 8)
        c.drawString(10*mm, curr_y, f"{qty} x {curr_info['symbol']}{price:,.0f}")
        c.drawRightString(width-7*mm, curr_y, f"{curr_info['symbol']}{subtotal:,.0f}")
        
        if discount > 0:
            curr_y -= 4*mm
            c.setFont(FONT_NAME, 7)
            c.drawString(12*mm, curr_y, f"({curr_info['disc_text']})")
            c.drawRightString(width-7*mm, curr_y, f"-{curr_info['symbol']}{discount:,.0f}")
        curr_y -= 8*mm

    # Footer
    curr_y -= 2*mm; c.line(5*mm, curr_y, width-5*mm, curr_y); curr_y -= 8*mm
    c.setFont(FONT_NAME, 12)
    c.drawString(7*mm, curr_y, "TOTAL")
    c.drawRightString(width-7*mm, curr_y, f"{curr_info['symbol']}{grand_total:,.0f}")
    
    # QR Code & Review
    curr_y -= 25*mm
    qr = qrcode.make("https://maps.google.com"); qr.save("temp_qr.png")
    c.drawImage("temp_qr.png", 8*mm, curr_y, width=18*mm, height=18*mm)
    c.setFont(FONT_NAME, 7)
    c.drawString(28*mm, curr_y+10*mm, "★★★★★")
    c.drawString(28*mm, curr_y+6*mm, "Thank you for your visit!")
    
    c.save()
    with open(file_name, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8'), grand_total

# --- 6. จัดการระบบเก็บข้อมูล (History) ---
if 'history' not in st.session_state:
    st.session_state.history = []

# --- 7. ส่วน UI ---
col_in, col_pre = st.columns([1, 1])

with col_in:
    st.subheader("🏢 เลือกบริษัท & รายการ")
    selected_comp_name = st.radio("ค่ายเกม:", list(company_config.keys()), horizontal=True)
    comp_info = company_config[selected_comp_name]
    
    selected_curr = st.selectbox("สกุลเงิน:", list(currency_config.keys()))
    curr_info = currency_config[selected_curr]
    
    c_dt1, c_dt2 = st.columns(2)
    input_date = c_dt1.date_input("วันที่:", datetime.now())
    input_time = c_dt2.text_input("เวลา:", datetime.now().strftime("%H:%M"))
    formatted_date = input_date.strftime(curr_info["date_fmt"])
    
    # คำนวณธาตุ
    element = get_daily_element(input_date, selected_curr)

    if 'basket' not in st.session_state: st.session_state.basket = []

    with st.form("add_item", clear_on_submit=True):
        item_name = st.text_input("ชื่อสินค้า")
        c1, c2, c3 = st.columns(3)
        qty = c1.number_input("จำนวน", min_value=1, value=1)
        price = c2.number_input("ราคา", min_value=0.0)
        disc = c3.number_input("ส่วนลด", min_value=0.0)
        if st.form_submit_button("➕ เพิ่มลงตะกร้า"):
            st.session_state.basket.append((item_name, qty, price, disc))
            st.rerun()

    if st.button("🗑️ ล้างตะกร้า"):
        st.session_state.basket = []
        st.rerun()

with col_pre:
    st.subheader("👀 Preview")
    if st.session_state.basket:
        # สร้าง PDF เพื่อ Preview
        pdf_base64, final_total = create_pdf(comp_info, st.session_state.basket, curr_info, formatted_date, input_time, element, selected_curr)
        
        # แสดงผล Preview ในหน้าจอ
        pdf_display = f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="550" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        if st.button("🎯 ออกใบเสร็จ & บันทึกข้อมูล", use_container_width=True):
            # บันทึกลง History
            st.session_state.history.append({
                "เวลา": f"{formatted_date} {input_time}",
                "บริษัท": selected_comp_name,
                "รายการ": ", ".join([x[0] for x in st.session_state.basket]),
                "ยอดรวม": f"{curr_info['symbol']}{final_total:,.2f}"
            })
            # สั่ง Print
            js = f"window.open('data:application/pdf;base64,{pdf_base64}')"
            st.components.v1.html(f"<script>{js}</script>", height=0)
            st.success("✅ บันทึกข้อมูลเรียบร้อย!")
    else:
        st.info("กรุณาเพิ่มสินค้าเพื่อดู Preview")

# --- 8. ส่วนแสดงประวัติ (History Table) ---
st.divider()
st.subheader("📜 ประวัติการออกใบเสร็จ (History)")
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    st.table(df)
    if st.button("❌ ล้างประวัติทั้งหมด"):
        st.session_state.history = []
        st.rerun()
else:
    st.info("ยังไม่มีข้อมูลการออกใบเสร็จในเซสชั่นนี้")
