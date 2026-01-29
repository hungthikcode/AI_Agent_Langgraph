import time
import streamlit as st
import requests  
import os

# URL của Backend API 
API_URL = os.getenv("API_URL", "http://localhost:8000")

def local_css(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass

def truncate_text(text, max_length=30):
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Chatbot hỗ trợ", layout="wide")
local_css("style.css") 

# --- SIDEBAR
with st.sidebar:
    st.title("🤖 Chatbot hỗ trợ")
    st.markdown("---")
    
    if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("### 🕒 Lịch sử gần đây")

    # Lấy danh sách session từ API
    try:
        response = requests.get(f"{API_URL}/sessions")
        if response.status_code == 200:
            recent_sessions = response.json()
            for s in recent_sessions:
                display_text = truncate_text(s['summary'])
                if st.button(display_text, key=s['id'], help=s['summary'], use_container_width=True):
                    # Khi bấm vào session, gọi API lấy tin nhắn cũ
                    msg_resp = requests.get(f"{API_URL}/history/{s['id']}")
                    if msg_resp.status_code == 200:
                        st.session_state.session_id = s['id']
                        st.session_state.messages = msg_resp.json()
                        st.rerun()
    except Exception as e:
        st.error("Không thể kết nối Backend API")

# --- GIAO DIỆN CHAT CHÍNH ---
st.header("Trợ lý AI (Data4Life)")

# Khởi tạo session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None 

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input từ người dùng
if user_input := st.chat_input("Hãy đặt câu hỏi của bạn ở đây..."):
    # 1. Hiển thị tin nhắn user ngay lập tức
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Gọi API để lấy câu trả lời
    with st.chat_message("assistant"):
        with st.spinner("AI đang suy nghĩ..."):
            try:
                payload = {
                    "user_input": user_input,
                    "session_id": st.session_state.session_id
                }
                
                t0 = time.time()
                response = requests.post(f"{API_URL}/chat", json=payload)
                t1 = time.time()

                if response.status_code == 200:
                    data = response.json()
                    ai_output = data["ai_output"]
                    # Cập nhật session_id mới nếu đây là cuộc trò chuyện mới
                    st.session_state.session_id = data["session_id"]
                    
                    st.markdown(ai_output)
                    st.session_state.messages.append({"role": "assistant", "content": ai_output})
                    st.caption(f"⏱️ Phản hồi trong: {t1 - t0:.2f}s")
                else:
                    st.error("Lỗi từ Backend API")
            except Exception as e:
                st.error(f"Lỗi kết nối: {str(e)}")