from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uuid
import time
import traceback   
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
import uvicorn
from agent_core.graph import MultiRoleAgentGraph
from connect_SQL.connect_SQL import connect_sql
import re
import json



app = FastAPI(title="Chatbot Backend API")

agent_graph = MultiRoleAgentGraph()

class ChatRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None

def clean_retrieved_docs(raw_text):
    if isinstance(raw_text, dict):
        return json.dumps(raw_text, ensure_ascii=False)
    if isinstance(raw_text, str):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", raw_text.strip())
        try:
            json_obj = json.loads(cleaned)
            return json.dumps(json_obj, ensure_ascii=False)
        except:
            return cleaned
    return json.dumps(str(raw_text), ensure_ascii=False)

def log_to_database_internal(session_id, user_query, ai_response, intermediate_steps):
    engine = connect_sql()
    VN_TZ = timezone(timedelta(hours=7))
    timestamp = datetime.now(VN_TZ).replace(tzinfo=None)
    
    with engine.connect() as conn:
        if not session_id:
            session_id = f"st_session_{uuid.uuid4()}"
            summary = user_query[:30] + ('...' if len(user_query) > 30 else '')
            conn.execute(text("""
                INSERT INTO ChatSessions (SessionId, FirstMessageSummary, CreatedAt) 
                VALUES (:sid, :summary, :timestamp)
            """), {"sid": session_id, "summary": summary, "timestamp": timestamp})
            conn.commit()
    
        result = conn.execute(text("""
                INSERT INTO dbo.conversation_history (session_id, user_message, bot_response, timestamp)
                OUTPUT INSERTED.id VALUES (:sid, :user_msg, :bot_res, :timestamp)
            """), {"sid": session_id, "user_msg": user_query, "bot_res": ai_response, "timestamp": timestamp})
        conversation_id = result.scalar_one()

        conn.execute(text("""
                INSERT INTO dbo.query_results (conversation_id, query_text, response_text, retrieved_docs, model_name, timestamp)
                VALUES (:conv_id, :q_text, :res_text, :r_docs, :model, :timestamp)
            """), {
                "conv_id": conversation_id, "q_text": user_query, "res_text": ai_response,
                "r_docs": intermediate_steps, "model": "gemini-2.5-flash", "timestamp": timestamp
            })
        conn.commit()
    return session_id

# --- Các Endpoint API ---

@app.get("/sessions")
def get_sessions():
    """Lấy danh sách session cho sidebar"""
    engine = connect_sql()
    query = text("SELECT TOP 5 SessionId, FirstMessageSummary FROM dbo.ChatSessions ORDER BY CreatedAt DESC")
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
        return [{"id": r[0], "summary": r[1]} for r in rows]

@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Lấy lịch sử tin nhắn khi bấm vào một session trên sidebar"""
    engine = connect_sql()
    query = text("SELECT user_message, bot_response FROM conversation_history WHERE session_id = :sid ORDER BY timestamp ASC")
    with engine.connect() as conn:
        rows = conn.execute(query, {"sid": session_id}).fetchall()
        messages = []
        for r in rows:
            messages.append({"role": "user", "content": r[0]})
            messages.append({"role": "assistant", "content": r[1]})
        return messages

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Xử lý chat chính"""
    try:
        new_state = agent_graph.create_new_state(
            user_question=req.user_input,
            session_id=req.session_id or "",
        )
        result = agent_graph.run(new_state)
        
        ai_output = result.get('final_answer', 'Lỗi: Không có phản hồi.')
        llm_analysis = result.get('llm_analysis', [])
        
        # Ghi log database
        new_sid = log_to_database_internal(
            session_id=req.session_id,
            user_query=req.user_input,
            ai_response=ai_output,
            intermediate_steps=clean_retrieved_docs(llm_analysis)
        )
        
        return {
            "ai_output": ai_output,
            "session_id": new_sid
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)