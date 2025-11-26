# app.py
import time, json
import streamlit as st
from agent_core.graph import MultiRoleAgentGraph
from sqlalchemy import text
import uuid
from PIL import Image
from pathlib import Path
import unicodedata
from datetime import datetime, timezone, timedelta
from connect_SQL.connect_SQL import connect_sql
import re


@st.cache_resource
def load_agent_graph():
    return MultiRoleAgentGraph()

def log_to_database(session_id, user_query, ai_response, intermediate_steps):
    engine = connect_sql()
    VN_TZ = timezone(timedelta(hours=7))
    timestamp = datetime.now(VN_TZ).replace(tzinfo=None)
    print(session_id)
    with engine.connect() as conn:
        # Xu li bang ChatSessions
        is_new_session = False
        if not session_id:
            session_id = f"st_session_{uuid.uuid4()}"
            is_new_session = True

        if is_new_session:
            summary = user_query[:30] + ('...' if len(user_query) > 30 else '')
            stmt_session = text("""
                INSERT INTO ChatSessions (SessionId, FirstMessageSummary, CreatedAt) 
                VALUES (:sid, :summary,:timestamp)
            """)
            conn.execute(stmt_session, {
                "sid": session_id,
                "summary": summary,
                "timestamp": timestamp,
            })
            conn.commit()
    
        stmt_conv = text("""
                INSERT INTO dbo.conversation_history (session_id, user_message, bot_response,timestamp)
                OUTPUT INSERTED.id
                VALUES (:sid, :user_msg, :bot_res, :timestamp)
            """)
        result = conn.execute(stmt_conv, {
            "sid": session_id,
            "user_msg": user_query,
            "bot_res": ai_response,
            "timestamp": timestamp,
        })
        conversation_id = result.scalar_one()

        # 2. Chuẩn bị dữ liệu và ghi vào query_results

        stmt_query = text("""
                INSERT INTO dbo.query_results (conversation_id, query_text, response_text, retrieved_docs, model_name, timestamp)
                VALUES (:conv_id, :q_text, :res_text, :r_docs, :model,:timestamp)
            """)
        conn.execute(stmt_query, {
            "conv_id": conversation_id,
            "q_text": user_query,
            "res_text": ai_response,
            "r_docs": intermediate_steps,
            "model": "gemini-2.0-flash",
            "timestamp": timestamp,
        })
        conn.commit()

    print(f"Đã ghi log thành công cho conversation_id: {conversation_id}")
    return session_id

def get_chat_sessions(limit=5) -> list:
    engine = connect_sql()
    sessions = []
    query = text(f"""
        SELECT TOP (:limit) SessionId, FirstMessageSummary
        FROM dbo.ChatSessions
        ORDER BY CreatedAt DESC
    """)
    
    with engine.connect() as conn:
        try:
            rows = conn.execute(query, {"limit": limit}).fetchall() 
            sessions = [(row.SessionId, row.FirstMessageSummary) for row in rows]
        except Exception as e:
            print(f"Lỗi khi lấy danh sách session: {e}")
        return sessions

def get_messages_by_session(session_id: str) -> list:
    """
    Lấy toàn bộ tin nhắn của một SessionId cụ thể.
    Trả về list of dictionaries, phù hợp với st.session_state.messages.
    """
    engine = connect_sql()
    messages = []
    query = text("""SELECT user_message, bot_response 
            FROM [dbo].[conversation_history] 
            WHERE session_id = :session_id 
            ORDER BY timestamp ASC""")
    with engine.connect() as conn:
        try:
            rows = conn.execute(query, {'session_id': session_id}).fetchall()
            for row in rows:
                if row.user_message:
                    messages.append({"role": "user", "content": row.user_message})
                
                # 2. Tạo dictionary cho tin nhắn của bot
                if row.bot_response:
                    messages.append({"role": "assistant", "content": row.bot_response})
        except Exception as e:
            print(f"Lỗi khi lấy tin nhắn của session {session_id}: {e}")
        return messages

def truncate_text(text, max_length=10):
    """Cắt ngắn văn bản hiển thị trên sidebar"""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def local_css(file_name):
    # Thêm encoding="utf-8" vào đây
    with open(file_name, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def clean_retrieved_docs(raw_text):
    if isinstance(raw_text, dict):
        return json.dumps(raw_text, ensure_ascii=False)
    if isinstance(raw_text, str):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", raw_text.strip())
        try:
            json_obj = json.loads(cleaned)
            return json.dumps(json_obj, ensure_ascii=False)
        except json.JSONDecodeError:
            # Nếu không parse được, trả lại nguyên văn (để debug)
            return cleaned
    # Nếu là kiểu khác (list, None, etc.)
    return json.dumps(str(raw_text), ensure_ascii=False)



st.set_page_config(page_title="Chatbot hỗ trợ", layout="wide")
local_css("D:/Chatbot_Data4Life/v1/style.css")

with st.sidebar:
    st.title("🤖 Chatbot hỗ trợ")
    st.markdown("---")
    if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("### 🕒 Lịch sử gần đây")

    recent_sessions = get_chat_sessions(limit=5) 

    for s_id, summary in recent_sessions:
        display_text = truncate_text(summary, 30)
        
        # Kiểm tra xem nút này có phải session đang mở không để highlight (tùy chọn)
        is_active = (s_id == st.session_state.get("session_id"))
        
        # Dùng key unique để tránh lỗi duplicate widget ID
        if st.button(display_text, key=s_id, help=summary):
            st.session_state.session_id = s_id
            st.session_state.messages = get_messages_by_session(s_id)
            st.rerun()
    
    st.markdown("---")
    with st.expander("ℹ️ Hướng dẫn sử dụng"):
        st.caption("""
            1. Đặt câu hỏi của bạn.
            2. Dựa trên câu hỏi, AI sẽ truy xuất thông tin và trả lời.
            3. Lịch sử trò chuyện được lưu tự động.
            4. Sử dụng sidebar để bắt đầu cuộc trò chuyện mới hoặc truy cập lịch sử.
            """)

# --- Giao diện Chat chính ---
st.header(f"Trò chuyện với: Trợ lý AI")

# Khởi tạo session state nếu chưa có
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None 

# Hiển thị chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input
if user_input := st.chat_input("Hãy đặt câu hỏi của bạn ở đây..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("AI đang suy nghĩ..."):

            t0 = time.time()
            agent_graph = load_agent_graph()

            new_state = agent_graph.create_new_state(
                user_question=user_input,
                session_id=st.session_state.session_id or "",
            )

            result = agent_graph.run(new_state)
            
            t1 = time.time()
            ai_output = result.get('final_answer', 'Lỗi: Không có phản hồi.')
            llm_analysis = result.get('llm_analysis', [])
            try:
                new_sessions_id = log_to_database(
                    session_id=st.session_state.session_id,
                    user_query=user_input,
                    ai_response=ai_output,
                    intermediate_steps=clean_retrieved_docs(llm_analysis),
                )
                st.session_state.session_id = new_sessions_id
            except Exception as e:
                print(f"Lỗi khi ghi log vào CSDL: {e}")
                st.error("Không thể ghi log vào CSDL!")

            st.markdown(ai_output)
            for key, value in result.items():
               print(f"  - {key}: {value}")
            print(f"⏱️ Total: {t1 - t0:.3f}s")

    st.session_state.messages.append({"role": "assistant", "content": ai_output})
