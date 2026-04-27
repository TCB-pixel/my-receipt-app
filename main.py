import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit, ImageReader
import os

# --- ตั้งค่าหน้าจอ App ---
st.set_page_config(page_title="Bandai Namco Receipt Pro", layout="wide")
st.title("🖨️ เครื่องสร้างใบเสร็จ Pro (Full Version)")

# --- ลงทะเบียน Font ---
FONT_NAME = "GlobalFont"
font_path = "NotoSansSC-VariableFont_wght.ttf" 

if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
else:
    st.error(f"❌ ไม่พบไฟล์ฟอนต์ {font_path}")

# ข้อมูลสกุลเงินและคำศัพท์ส่วนลด
currency_config = {
    "JPY (¥)": {"symbol": "¥", "disc_text": "割引"},
    "THB (฿)": {"symbol": "฿", "disc_text": "ส่วนลด"},
    "CNY (¥)": {"symbol": "¥", "disc_text": "折扣"},
    "HKD ($)": {"symbol": "$", "disc_text": "Discount"}
}

# --- ฟังก์ชันสร้าง PDF ---
def create_pdf(shop_name, basket, curr_info):
    file_name = "receipt.pdf"
    symbol = curr_info["symbol"]
    disc_label = curr_info["disc_text"]
    
    width = 80 * mm
    # คำนวณความสูงกระดาษตามจำนวนสินค้า
    height = (len(basket) * 30 + 120) * mm 
    c = canvas.Canvas(file_name, pagesize=(width, height))
    curr_y = height - 10*mm

    # 1. จัดการ Logo (คำนวณจากขนาดจริง)
    logo_file = None
    for f in ["logo", "logo.png", "logo.jpg"]:
        if os.path.exists(f):
            logo_file = f
            break

    if logo_file:
        try:
            img = ImageReader(logo_file)
            img_w, img_h = img.getSize()
            display_w = 45 * mm  # กำหนดความกว้างโลโก้ในใบเสร็จ
            display_h = (display_w / img_w) * img_h # รักษาสัดส่วนภาพ
            
            center_x = (width - display_w) / 2
            c.drawImage(logo_file, center_x, curr_y - display_h, width=display_w, height=display_h, mask='auto')
            curr_y -= (display_h + 10*mm)
        except:
            curr_y -= 5*mm

    # 2. หัวใบเสร็จ
    c.setFont(FONT_NAME, 14)
    c.drawCentredString(width/2, curr_y, shop_name)
    curr_y -= 10*mm
    c.setFont(FONT_NAME, 10)
    c.drawCentredString(width/2, curr_y, "TAX INVOICE / RECEIPT")
    curr_y -= 5*mm
    c.line(5*mm, curr_y, width-5*mm, curr_y)
    
    # 3. รายการสินค้า
    curr_y -= 10*mm
    grand_total = 0
    for name, qty, price, discount in basket:
        subtotal = qty * price
        line_total = subtotal - discount
        grand_total += line_total
        
        c.setFont(FONT_NAME, 10)
        # ตัดคำถ้าชื่อสินค้ายาวเกินไป
        lines = simpleSplit(name, FONT_NAME, 10, 65*mm)
        for line in lines:
            c.drawString(7*mm, curr_y, line)
            curr_y -= 5*mm
        
        c.setFont(FONT_NAME, 9)
        c.drawString(10*mm, curr_y, f"{qty} x {symbol}{price:,.2f}")
        c.drawRightString(width-7*mm, curr_y, f"{symbol}{subtotal:,.2f}")
        
        if discount > 0:
            curr_y -= 4*mm
            c.setFont(FONT_NAME, 8)
            c.drawString(12*mm, curr_y, f"({disc_label})")
            c.drawRightString(width-7*mm, curr_y, f"-{symbol}{discount:,.2f}")
        curr_y -= 10*mm

    # 4. สรุปยอดเงิน
    c.line(5*mm, curr_y, width-5*mm, curr_y)
    curr_y -= 10*mm
    c.setFont(FONT_NAME, 14)
    c.drawString(7*mm, curr_y, "TOTAL")
    c.drawRightString(width-7*mm, curr_y, f"{symbol}{grand_total:,.2f}")
    
    curr_y -= 15*mm
    c.setFont(FONT_NAME, 9)
    c.drawCentredString(width/2, curr_y, "Thank you / ありがとうございました")
    
    c.save()
    return file_name

# --- ส่วนหน้าจอ UI ---
col_input, col_preview = st.columns([1, 1])

with col_input:
    st.subheader("📝 ข้อมูลใบเสร็จ")
    shop = st.text_input("ชื่อร้านค้า", "BANDAI NAMCO ENTERTAINMENT")
    selected_curr = st.selectbox("เลือกสกุลเงิน", list(currency_config.keys()))
    curr_info = currency_config[selected_curr]

    if 'basket' not in st.session_state:
        st.session_state.basket = []

    with st.form("add_item", clear_on_submit=True):
        name = st.text_input("ชื่อสินค้า")
        c1, c2, c3 = st.columns(3)
        qty = c1.number_input("จำนวน", min_value=1, value=1)
        price = c2.number_input("ราคาต่อชิ้น", min_value=0.0)
        disc = c3.number_input("ส่วนลดรวม", min_value=0.0)
        if st.form_submit_button("➕ เพิ่มรายการ"):
            st.session_state.basket.append((name, qty, price, disc))
            st.rerun()

    if st.button("🗑️ ล้างตะกร้า"):
        st.session_state.basket = []
        st.rerun()

with col_preview:
    st.subheader("👀 Preview")
    with st.container(border=True):
        # จัดการ Logo ใน Preview ให้กึ่งกลาง
        logo_path = None
        for f in ["logo.png", "logo", "logo.jpg"]:
            if os.path.exists(f):
                logo_path = f
                break
        
        if logo_path:
            p_l, p_m, p_r = st.columns([1, 2, 1])
            with p_m:
                st.image(logo_path, use_container_width=True)
        
        st.markdown(f"<h3 style='text-align: center; margin:0;'>{shop}</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.8em;'>TAX INVOICE / RECEIPT</p>", unsafe_allow_html=True)
        st.write("---")
        
        total_val = 0
        for n, q, p, d in st.session_state.basket:
            sub = q * p
            total_val += (sub - d)
            st.write(f"**{n}**")
            st.markdown(f"<div style='display: flex; justify-content: space-between;'><span>{q} x {p:,.2f}</span> <span>{curr_info['symbol']}{sub:,.2f}</span></div>", unsafe_allow_html=True)
            if d > 0:
                st.markdown(f"<div style='display: flex; justify-content: space-between; color: red; font-size: 0.9em;'><span>({curr_info['disc_text']})</span> <span>-{curr_info['symbol']}{d:,.2f}</span></div>", unsafe_allow_html=True)
        
        st.write("---")
        st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 1.5em;'><b>TOTAL</b> <b>{curr_info['symbol']}{total_val:,.2f}</b></div>", unsafe_allow_html=True)

    if st.session_state.basket:
        if st.button("🚀 ออกใบเสร็จ PDF"):
            path = create_pdf(shop, st.session_state.basket, curr_info)
            with open(path, "rb") as f:
                st.download_button("💾 Download PDF", f, file_name="receipt.pdf")
