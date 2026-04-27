import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit, ImageReader
import os
import barcode
from barcode.writer import ImageWriter
import qrcode
import base64
from datetime import datetime

# --- 1. ฟังก์ชันธาตุ (JPY/CNY) ---
def get_daily_element(date_obj, currency):
    elements_lang = {
        "JPY (¥)": {0: "日", 1: "月", 2: "火", 
            3: "水", 4: "木", 5: "金", 6: "土"},
        "CNY (¥)": {0: "日", 1: "月", 2: "火", 
            3: "水", 4: "木", 5: "金", 6: "土"}
    }
    return elements_lang.get(currency, {}).get(date_obj.weekday(), "")

# --- 2. ตั้งค่า Font ---
st.set_page_config(page_title="Professional Receipt Maker", layout="wide")
FONT_NAME = "GlobalFont"
font_path = "NotoSansSC-VariableFont_wght.ttf"
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))

# ข้อมูลบริษัท
company_info = {
    "Bandai Namco": {"full_name": "BANDAI NAMCO ENTERTAINMENT CO., LTD.", "address": "5-37-8 Shiba, Minato-ku, Tokyo, Japan", "tel": "03-6744-4000", "tax_id": "T5010401136065", "logo": "logo.png"},
    "Konami": {"full_name": "KONAMI DIGITAL ENTERTAINMENT CO., LTD.", "address": "1-11-1 Ginza, Chuo-ku, Tokyo, Japan", "tel": "03-5771-0511", "tax_id": "T7010401060341", "logo": "logo konami.png"}
}

# --- 3. ฟังก์ชันสร้าง PDF ---
def create_pdf(data):
    file_name = "receipt.pdf"
    dynamic_h = (len(data['items']) * 12) + 165
    w, h = 80*mm, dynamic_h*mm
    c = canvas.Canvas(file_name, pagesize=(w, h))
    curr_y = h - 10*mm

    # Logo
    if os.path.exists(data['comp']['logo']):
        c.drawImage(data['comp']['logo'], (w-30*mm)/2, curr_y-15*mm, width=30*mm, preserveAspectRatio=True, mask='auto')
        curr_y -= 18*mm
    
    # Header
    c.setFont(FONT_NAME, 10); c.drawCentredString(w/2, curr_y, data['comp']['full_name']); curr_y -= 6*mm
    c.setFont(FONT_NAME, 7)
    c.drawCentredString(w/2, curr_y, data['comp']['address']); curr_y -= 4*mm
    c.drawCentredString(w/2, curr_y, f"TEL: {data['comp']['tel']}"); curr_y -= 4*mm
    c.drawCentredString(w/2, curr_y, f"TAX ID: {data['comp']['tax_id']}"); curr_y -= 4*mm
    display_date = f"{data['date_str']} {data['time_str']}"
    if data['element']: display_date += f" ({data['element']})"
    c.drawCentredString(w/2, curr_y, display_date); curr_y -= 5*mm

    # Barcode
    try:
        bc_class = barcode.get_barcode_class('code128')
        bc_obj = bc_class("SSP2TJJ1PQB4", writer=ImageWriter())
        bc_obj.save("temp_bc", options={"module_height": 5, "font_size": 1, "text_distance": 1})
        c.drawImage("temp_bc.png", (w-55*mm)/2, curr_y-12*mm, width=55*mm, height=12*mm)
        curr_y -= 15*mm
    except: pass
    
    c.drawCentredString(w/2, curr_y, "------------------------------------------"); curr_y -= 8*mm

    # Items
    total = 0
    c.setFont(FONT_NAME, 8)
    for name, qty, price in data['items']:
        sub = qty * price
        total += sub
        c.drawString(7*mm, curr_y, name)
        c.drawRightString(w-7*mm, curr_y, f"{sub:,.0f}")
        curr_y -= 5*mm
        c.setFont(FONT_NAME, 7)
        c.drawString(7*mm, curr_y, f"{qty} 点 x {price:,.0f}")
        curr_y -= 7*mm; c.setFont(FONT_NAME, 8)

    # Total
    curr_y -= 2*mm; c.line(5*mm, curr_y, w-5*mm, curr_y); curr_y -= 7*mm
    c.setFont(FONT_NAME, 12); c.drawString(7*mm, curr_y, "合計 (TOTAL)")
    symbol = "¥" if "THB" not in data['curr'] else "฿"
    c.drawRightString(w-7*mm, curr_y, f"{symbol}{total:,.0f}")
    
    # QR
    curr_y -= 28*mm
    qr = qrcode.make("https://maps.google.com"); qr.save("temp_qr.png")
    c.drawImage("temp_qr.png", 8*mm, curr_y, width=18*mm, height=18*mm)
    c.setFont(FONT_NAME, 7)
    c.drawString(28*mm, curr_y+10*mm, "★★★★★")
    c.drawString(28*mm, curr_y+6*mm, "Thank you for your visit!")
    c.save()
    with open(file_name, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# --- 4. UI ---
st.title("🖨️ iShip Professional Receipt")
col_input, col_preview = st.columns([1, 1])

if 'pro_basket' not in st.session_state: st.session_state.pro_basket = []

with col_input:
    c1, c2 = st.columns(2)
    selected_comp = c1.selectbox("เลือกบริษัท", list(company_info.keys()))
    selected_curr = c2.selectbox("สกุลเงิน", ["JPY (¥)", "CNY (¥)", "THB (฿)"])
    
    c3, c4 = st.columns(2)
    d = c3.date_input("วันที่", datetime.now())
    t = c4.text_input("เวลา", datetime.now().strftime("%H:%M"))
    element = get_daily_element(d, selected_curr)

    with st.form("add", clear_on_submit=True):
        name = st.text_input("ชื่อสินค้า")
        q_col, p_col = st.columns(2)
        q = q_col.number_input("จำนวน", min_value=1)
        p = p_col.number_input("ราคา", min_value=0)
        if st.form_submit_button("➕ เพิ่มรายการ"):
            st.session_state.pro_basket.append((name, q, p))
            st.rerun()
    
    if st.button("🗑️ ล้างรายการ"):
        st.session_state.pro_basket = []
        st.rerun()

with col_preview:
    st.subheader("🔍 Preview")
    payload = {
        'comp': company_info[selected_comp], 'items': st.session_state.pro_basket,
        'curr': selected_curr, 'date_str': d.strftime("%Y/%m/%d"), 'time_str': t, 'element': element
    }
    
    if st.session_state.pro_basket:
        pdf_base64 = create_pdf(payload)
        # แสดง Preview เป็นกล่อง PDF ในหน้าเว็บ
        pdf_display = f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        if st.button("🎯 พิมพ์ใบเสร็จ (Print PDF)", use_container_width=True):
            js = f"window.open('data:application/pdf;base64,{pdf_base64}')"
            st.components.v1.html(f"<script>{js}</script>", height=0)
    else:
        st.info("เพิ่มสินค้าเพื่อดู Preview")
