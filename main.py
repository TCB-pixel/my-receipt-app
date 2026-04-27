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

# --- 1. ฟังก์ชันหาธาตุประจำวัน (เฉพาะ JPY และ CNY) ---
def get_daily_element(date_obj, currency):
    elements_lang = {
        "JPY (¥)": {
            0: "日", 1: "月", 2: "火", 
            3: "水", 4: "木", 5: "金", 6: "土"
        },
        "CNY (¥)": {
            0: "日", 1: "月", 2: "火", 
            3: "水", 4: "木", 5: "金", 6: "土"
        }
    }
    # ดึงค่าธาตุตามสกุลเงิน ถ้าไม่ใช่ JPY/CNY จะคืนค่าว่าง
    lang_set = elements_lang.get(currency, {})
    return lang_set.get(date_obj.weekday(), "")

# --- 2. ตั้งค่า Font และพื้นฐาน ---
st.set_page_config(page_title="Professional Receipt Maker", layout="centered")
FONT_NAME = "GlobalFont"
font_path = "NotoSansSC-VariableFont_wght.ttf"
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))

# ข้อมูลบริษัท (ที่อยู่และเบอร์โทรตามรูปต้นฉบับ)
company_info = {
    "Bandai Namco": {
        "full_name": "BANDAI NAMCO ENTERTAINMENT CO., LTD.",
        "address": "5-37-8 Shiba, Minato-ku, Tokyo, Japan",
        "tel": "03-6744-4000",
        "tax_id": "T5010401136065",
        "logo": "logo.png"
    },
    "Konami": {
        "full_name": "KONAMI DIGITAL ENTERTAINMENT CO., LTD.",
        "address": "1-11-1 Ginza, Chuo-ku, Tokyo, Japan",
        "tel": "03-5771-0511",
        "tax_id": "T7010401060341",
        "logo": "logo konami.png"
    }
}

# --- 3. ฟังก์ชันสร้าง PDF (Format 80mm) ---
def create_pro_receipt(data):
    file_name = "pro_receipt.pdf"
    # คำนวณความสูงกระดาษตามจำนวนสินค้า
    dynamic_h = (len(data['items']) * 12) + 160
    w, h = 80*mm, dynamic_h*mm
    c = canvas.Canvas(file_name, pagesize=(w, h))
    curr_y = h - 10*mm

    # 1. Logo
    if os.path.exists(data['comp']['logo']):
        c.drawImage(data['comp']['logo'], (w-30*mm)/2, curr_y-15*mm, width=30*mm, preserveAspectRatio=True, mask='auto')
        curr_y -= 18*mm
    
    # 2. Header
    c.setFont(FONT_NAME, 11)
    c.drawCentredString(w/2, curr_y, data['comp']['full_name'])
    curr_y -= 6*mm
    c.setFont(FONT_NAME, 7)
    c.drawCentredString(w/2, curr_y, data['comp']['address'])
    curr_y -= 4*mm
    c.drawCentredString(w/2, curr_y, f"TEL: {data['comp']['tel']}")
    curr_y -= 4*mm
    c.drawCentredString(w/2, curr_y, f"TAX ID: {data['comp']['tax_id']}")
    curr_y -= 4*mm
    
    # แสดงวันที่และธาตุ (ธาตุจะปรากฏเฉพาะ JPY/CNY)
    display_date = f"{data['date_str']} {data['time_str']}"
    if data['element']:
        display_date += f" ({data['element']})"
    c.drawCentredString(w/2, curr_y, display_date)
    curr_y -= 6*mm

    # 3. Barcode (Code128)
    try:
        bc_class = barcode.get_barcode_class('code128')
        bc_obj = bc_class("SSP2TJJ1PQB4", writer=ImageWriter())
        bc_obj.save("temp_bc", options={"module_height": 5, "font_size": 1, "text_distance": 1})
        c.drawImage("temp_bc.png", (w-55*mm)/2, curr_y-12*mm, width=55*mm, height=12*mm)
        curr_y -= 15*mm
    except: curr_y -= 5*mm
    
    c.drawCentredString(w/2, curr_y, "------------------------------------------")
    curr_y -= 8*mm

    # 4. Items List
    total = 0
    c.setFont(FONT_NAME, 8)
    for name, qty, price in data['items']:
        sub = qty * price
        total += sub
        c.drawString(7*mm, curr_y, f"{name}")
        c.drawRightString(w-7*mm, curr_y, f"{sub:,.0f}")
        curr_y -= 5*mm
        c.setFont(FONT_NAME, 7)
        c.drawString(7*mm, curr_y, f"{qty} 点 x {price:,.0f}")
        curr_y -= 7*mm
        c.setFont(FONT_NAME, 8)

    # 5. Summary
    curr_y -= 2*mm
    c.line(5*mm, curr_y, w-5*mm, curr_y)
    curr_y -= 7*mm
    c.setFont(FONT_NAME, 12)
    c.drawString(7*mm, curr_y, "合計 (TOTAL)")
    symbol = "¥" if "THB" not in data['curr'] else "฿"
    c.drawRightString(w-7*mm, curr_y, f"{symbol}{total:,.0f}")
    
    # 6. Footer QR & Stars
    curr_y -= 28*mm
    qr = qrcode.make("https://maps.google.com")
    qr.save("temp_qr.png")
    c.drawImage("temp_qr.png", 8*mm, curr_y, width=18*mm, height=18*mm)
    
    c.setFont(FONT_NAME, 7)
    c.drawString(28*mm, curr_y+12*mm, "★★★★★")
    c.drawString(28*mm, curr_y+8*mm, "Googleマップのレビューを")
    c.drawString(28*mm, curr_y+4*mm, "お願いします！")
    
    c.save()
    with open(file_name, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# --- 4. หน้าจอ UI ---
st.title("🖨️ iShip Receipt Professional")

# เลือกค่ายและสกุลเงิน
col_top1, col_top2 = st.columns(2)
selected_comp = col_top1.selectbox("เลือกบริษัท (Company)", list(company_info.keys()))
selected_curr = col_top2.selectbox("สกุลเงิน (Currency)", ["JPY (¥)", "CNY (¥)", "THB (฿)"])

# วันที่และเวลา
col_dt1, col_dt2 = st.columns(2)
d = col_dt1.date_input("วันที่", datetime.now())
t = col_dt2.text_input("เวลา", datetime.now().strftime("%H:%M"))

# คำนวณธาตุ
element = get_daily_element(d, selected_curr)

if 'pro_basket' not in st.session_state: st.session_state.pro_basket = []

# ฟอร์มเพิ่มสินค้า
with st.form("add_item", clear_on_submit=True):
    name = st.text_input("ชื่อสินค้า (เช่น ONE PIECE CARD)")
    c1, c2 = st.columns(2)
    q = c1.number_input("จำนวน", min_value=1, step=1)
    p = c2.number_input("ราคาต่อหน่วย", min_value=0, step=10)
    if st.form_submit_button("➕ เพิ่มรายการ"):
        st.session_state.pro_basket.append((name, q, p))
        st.rerun()

if st.button("🗑️ ล้างรายการทั้งหมด"):
    st.session_state.pro_basket = []
    st.rerun()

# ปุ่มออกใบเสร็จ
if st.button("🎯 ออกใบเสร็จ & พิมพ์ (Print PDF)", use_container_width=True):
    if not st.session_state.pro_basket:
        st.warning("กรุณาเพิ่มสินค้าก่อนครับ")
    else:
        payload = {
            'comp': company_info[selected_comp], 
            'items': st.session_state.pro_basket,
            'curr': selected_curr,
            'date_str': d.strftime("%Y年%m月%d日"), 
            'time_str': t, 
            'element': element
        }
        pdf_b64 = create_pro_receipt(payload)
        js = f"window.open('data:application/pdf;base64,{pdf_b64}')"
        st.components.v1.html(f"<script>{js}</script>", height=0)
        st.success(f"ออกใบเสร็จเรียบร้อย! {f'(ธาตุ: {element})' if element else ''}")
