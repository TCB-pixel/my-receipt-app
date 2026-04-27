import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import os
import pandas as pd
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
import qrcode
from io import BytesIO

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Professional Receipt Pro", layout="wide")

# --- 2. ลงทะเบียน Font ---
FONT_NAME = "GlobalFont"
font_path = "NotoSansSC-VariableFont_wght.ttf" 
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
else:
    FONT_NAME = "Helvetica"

# --- 3. ฟังก์ชันหาธาตุประจำวัน ---
def get_daily_element(date_obj, currency):
    elements_lang = {
        "JPY (¥)": {0: "地", 1: "風", 2: "水", 3: "火", 4: "混合", 5: "烈火", 6: "金"},
        "CNY (¥)": {0: "土", 1: "风", 2: "水", 3: "火", 4: "混合", 5: "烈火", 6: "金"}
    }
    el = elements_lang.get(currency, {}).get(date_obj.weekday(), "")
    return f"({el}元素)" if el else ""

# --- 4. ข้อมูลบริษัท ---
company_config = {
    "Bandai Namco": {
        "full_name": "BANDAI NAMCO ENTERTAINMENT CO., LTD.",
        "address": "5-37-8 Shiba, Minato-ku, Tokyo, Japan",
        "tel": "03-6744-4000",
        "tax_id": "T5010401136065"
    },
    "Konami": {
        "full_name": "KONAMI DIGITAL ENTERTAINMENT CO., LTD.",
        "address": "1-11-1 Ginza, Chuo-ku, Tokyo, Japan",
        "tel": "03-5771-0511",
        "tax_id": "T7010401060341"
    }
}

currency_config = {
    "JPY (¥)": {"symbol": "¥", "disc_text": "割引", "date_fmt": "%Y年%m月%d日"},
    "THB (฿)": {"symbol": "฿", "disc_text": "ส่วนลด", "date_fmt": "%d/%m/%Y"},
    "CNY (¥)": {"symbol": "¥", "disc_text": "折扣", "date_fmt": "%Y年%m月%d日"}
}

# --- 5. ฟังก์ชันสร้าง PDF (แก้ไขส่วน Image Error) ---
def create_full_pdf(comp_info, basket, curr_info, date_str, time_str, element_text):
    buffer = BytesIO()
    w = 80 * mm
    h = (len(basket) * 25 + 180) * mm
    c = canvas.Canvas(buffer, pagesize=(w, h))
    curr_y = h - 15*mm

    # Company Header
    c.setFont(FONT_NAME, 10); c.drawCentredString(w/2, curr_y, comp_info["full_name"]); curr_y -= 6*mm
    c.setFont(FONT_NAME, 7); c.drawCentredString(w/2, curr_y, comp_info["address"]); curr_y -= 4*mm
    c.drawCentredString(w/2, curr_y, f"TEL: {comp_info['tel']}  TAX ID: {comp_info['tax_id']}"); curr_y -= 5*mm
    c.drawCentredString(w/2, curr_y, f"{date_str} {time_str} {element_text}"); curr_y -= 8*mm

    # Barcode Generation
    try:
        bc_class = barcode.get_barcode_class('code128')
        bc_obj = bc_class("SSP2TJJ1PQB4", writer=ImageWriter())
        bc_img = bc_obj.render() # เปลี่ยนเป็น PIL Image
        c.drawImage(ImageReader(bc_img), (w-55*mm)/2, curr_y-12*mm, width=55*mm, height=12*mm)
        curr_y -= 15*mm
    except: pass

    c.drawCentredString(w/2, curr_y, "------------------------------------------"); curr_y -= 8*mm

    # Items & Calculations
    grand_total = 0
    c.setFont(FONT_NAME, 8)
    for name, qty, price, disc in basket:
        sub = qty * price
        grand_total += (sub - disc)
        c.drawString(7*mm, curr_y, name)
        c.drawRightString(w-7*mm, curr_y, f"{sub:,.0f}")
        curr_y -= 5*mm
        if disc > 0:
            c.setFont(FONT_NAME, 7)
            c.drawString(10*mm, curr_y, f"({curr_info['disc_text']})")
            c.drawRightString(w-7*mm, curr_y, f"-{disc:,.0f}")
            curr_y -= 5*mm
        c.setFont(FONT_NAME, 8); curr_y -= 3*mm

    # Total Section
    curr_y -= 2*mm; c.line(5*mm, curr_y, w-5*mm, curr_y); curr_y -= 8*mm
    c.setFont(FONT_NAME, 12); c.drawString(7*mm, curr_y, "TOTAL")
    c.drawRightString(w-7*mm, curr_y, f"{curr_info['symbol']}{grand_total:,.0f}")

    # QR Code Generation (แก้ไข Error ในรูปภาพ)
    try:
        curr_y -= 30*mm
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data("https://www.google.com/maps")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        c.drawImage(ImageReader(qr_img.get_image()), 8*mm, curr_y, width=20*mm, height=20*mm)
        
        c.setFont(FONT_NAME, 7)
        c.drawString(30*mm, curr_y+12*mm, "★★★★★")
        c.drawString(30*mm, curr_y+8*mm, "Thank you for your visit!")
    except: pass

    c.showPage(); c.save()
    pdf_bytes = buffer.getvalue(); buffer.close()
    return pdf_bytes

# --- 6. UI Logic ---
if 'basket' not in st.session_state: st.session_state.basket = []
if 'history' not in st.session_state: st.session_state.history = []

st.title("🖨️ Professional Receipt System")
col_in, col_pre = st.columns([1, 1])

with col_in:
    st.subheader("📝 บันทึกรายการ")
    sel_comp = st.radio("เลือกค่าย:", list(company_config.keys()), horizontal=True)
    sel_curr = st.selectbox("สกุลเงิน:", list(currency_config.keys()))
    in_date = st.date_input("วันที่:", datetime.now())
    in_time = st.text_input("เวลา:", datetime.now().strftime("%H:%M"))

    with st.form("add_item", clear_on_submit=True):
        name = st.text_input("ชื่อสินค้า")
        q, p, d = st.columns(3)
        qty = q.number_input("จำนวน", min_value=1, value=1)
        prc = p.number_input("ราคาต่อหน่วย", min_value=0.0)
        dsc = d.number_input("ส่วนลด", min_value=0.0)
        if st.form_submit_button("➕ เพิ่มลงตะกร้า"):
            st.session_state.basket.append((name, qty, prc, dsc))
            st.rerun()
    
    if st.button("🗑️ ล้างตะกร้า"):
        st.session_state.basket = []
        st.rerun()

with col_pre:
    st.subheader("👀 ตรวจสอบรายการ & พิมพ์")
    if st.session_state.basket:
        # แสดงตารางรายการให้ผู้ใช้ดูก่อน
        df = pd.DataFrame(st.session_state.basket, columns=["สินค้า", "จำนวน", "ราคา", "ส่วนลด"])
        st.table(df)
        
        curr_info = currency_config[sel_curr]
        element = get_daily_element(in_date, sel_curr)
        
        # สร้าง PDF
        pdf_data = create_full_pdf(company_config[sel_comp], st.session_state.basket, curr_info, in_date.strftime(curr_info["date_fmt"]), in_time, element)
        
        # ปุ่มดาวน์โหลด
        st.download_button(
            label="🎯 ดาวน์โหลดใบเสร็จ (PDF)",
            data=pdf_data,
            file_name=f"receipt_{sel_comp}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        if st.button("💾 บันทึกลงประวัติ"):
            total = sum((q*p)-d for n,q,p,d in st.session_state.basket)
            st.session_state.history.append({
                "วันที่": in_date.strftime("%Y-%m-%d"), 
                "บริษัท": sel_comp, 
                "ยอดรวม": f"{curr_info['symbol']}{total:,.0f}"
            })
            st.success("บันทึกประวัติเรียบร้อย!")
    else:
        st.info("กรุณาเพิ่มสินค้า")

# --- 7. History ---
st.divider()
st.subheader("📜 History")
if st.session_state.history:
    st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)
    if st.button("❌ ล้างประวัติ"):
        st.session_state.history = []
        st.rerun()
