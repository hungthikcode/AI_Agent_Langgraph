from agent_core.state import MultiRoleAgentState
from docx import Document
from typing import List, Dict, Any
from utils.llm_wrapper import GeminiSynthesizerLLM, GeminiAnalyzerLLM, GeminiChatParagraphSummarizer
from tools.tool_registry import TOOL_REGISTRY
import yaml
import re
import json
from connect_SQL.connect_SQL import connect_sql
from sqlalchemy import text


def user_input(state: MultiRoleAgentState ) -> str:
    return state["user_input"]


def _load_base_prompt(state: MultiRoleAgentState ) -> str:
    path = f"D:/Chatbot_Data4Life/v1/prompt/General_Prompt.docx"
    doc = Document(path)
    prompt_text = "/n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return prompt_text

def _load_tool_for_role() -> List[Dict[str, Any]]:
    """
    File YAML có dạng:
    tools:
      - name: search_project_documents
        description: "Tìm kiếm dữ liệu nội bộ theo từ khóa."
        parameters:
          query:
            type: string
            required: true
            description: "Chuỗi truy vấn hoặc từ khóa mô tả thông tin cần tìm"
            example: "doanh thu Q2 2025 khu vực VN"
        returns: "Danh sách bản ghi phù hợp"
    """

    path = f"D:/Chatbot_Data4Life/v1/prompt/tool.yaml"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        tools = data.get("tools", [])
        if not isinstance(tools, list):
            raise ValueError(f"⚠️ File YAML của role '{tool}' không đúng định dạng (tools phải là list).")

        # Chuẩn hóa thông tin
        normalized_tools = []
        for tool in tools:
            normalized_tools.append({
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
                "returns": tool.get("returns", "")
            })
        return normalized_tools

    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Không tìm thấy file YAML cho role")
    except Exception as e:
        raise RuntimeError(f"❌ Lỗi khi load tool cho role ")

def _load_memory(session_id: str ) -> list:
    if not session_id:
        return ""
  
    query = text(f"""
        SELECT TOP 3 user_message, bot_response
        FROM dbo.conversation_history
        WHERE session_id = :session_id
          AND timestamp >= DATEADD(HOUR, -4, GETDATE())   
        ORDER BY timestamp DESC;
    """)

    try:
        engine = connect_sql()
        with engine.connect() as conn:
            result = conn.execute(
                query,
                {"session_id": session_id}
            )
            rows = result.fetchall()

        print(rows)

        # Đảo ngược 
        history_records = reversed(rows)
        formatted_history = []
        for user_msg, bot_msg in history_records:
            formatted_history.append(f"User: {user_msg}")
            formatted_history.append(f"Assistant: {bot_msg}")
        return "\n".join(formatted_history)

    except Exception as e:
        print(f"ERROR: Không thể tải memory. Lỗi: {e}")
        return ""  

def role_manager(state: MultiRoleAgentState) -> None:
    state["tools"] = _load_tool_for_role()
    base_prompt = _load_base_prompt(state)
    state["base_prompt"] =  base_prompt

    conversation_history = _load_memory(session_id=state.get("session_id", ""))
    summarizer = GeminiChatParagraphSummarizer()
    summarise_conversation_history = summarizer.summarize_each_exchange(chat_json=conversation_history)
    state["conversation_history"] = summarise_conversation_history  

    # 3. Xây dựng template để chèn memory vào prompt
    # Đây là cách bạn "chèn vào prompt"
    final_prompt_template = (f"""
        {base_prompt} 
        ---
        ### LỊCH SỬ HỘI THOẠI GẦN ĐÂY:
        {summarise_conversation_history}
        ---
            """)

    # 4. Cập nhật state với prompt cuối cùng đã được bổ sung memory
    state["full_prompt"] = final_prompt_template
    print("Đã tải và kết hợp memory vào prompt thành công.")


def _normalize_role_tools(role_tools_raw: List[Any]) -> List[Dict[str, Any]]:
    """
    Chuẩn hoá role_tools: nếu item là str -> đổi thành {'name': str}
    Nếu item là dict và có 'name' giữ nguyên.
    """
    normalized = []
    for item in role_tools_raw or []:
        if isinstance(item, str):
            normalized.append({"name": item})
        elif isinstance(item, dict):
            if "name" in item:
                normalized.append(item)
            elif "tool_name" in item:
                item["name"] = item.pop("tool_name")
                normalized.append(item)
            else:
                continue
    return normalized

def _extract_json_from_text(text: str) -> Any:
    """
    Trích khối JSON từ văn bản trả về của LLM.
    """
    if not text:
        return None

    obj_match = re.search(r'(\{.*\})', text, flags=re.DOTALL)
    arr_match = re.search(r'(\[.*\])', text, flags=re.DOTALL)

    candidate = obj_match.group(1) if obj_match else (arr_match.group(1) if arr_match else text)

    # try direct json.loads
    try:
        return json.loads(candidate)
    except Exception:
        pass

    # sửa lỗi phổ biến: single quotes -> double quotes
    repaired = candidate.replace("'", '"')

    # remove trailing commas before } or ]
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    try:
        return json.loads(repaired)
    except Exception:
        return None

def _validate_and_format_required_tools(parsed_required: Any, normalized_role_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    parsed_required: parsed JSON 'required_tools' (list)
    normalized_role_tools: list of dicts with 'name' keys
    Trả về list chuẩn: [{'tool_name': name, 'params': {...}, 'available': True/False?}]
    """
    if not parsed_required:
        return []

    #print(normalized_role_tools)
    result = []
    available_names = {t["name"] for t in normalized_role_tools}

    for item in parsed_required:
        if isinstance(item, str):
            tool_name = item
            params = {}
        elif isinstance(item, dict):
            tool_name = item.get("tool_name") or item.get("name") or item.get("tool")
            params = item.get("params") or item.get("parameters") or {}
        else:
            continue

        if not isinstance(params, dict):
            if isinstance(params, str):
                params = {"value": params}
            else:
                params = {}

        entry = {"tool_name": tool_name, "params": params}
        if tool_name not in available_names:
            entry["available"] = False
        else:
            entry["available"] = True
        result.append(entry)

    return result


def task_analyzer(state: MultiRoleAgentState) -> None:
    """
    Node task_analyzer (in-place update).
    - Reads: state['user_question'], state['base_prompt'], state['role_tools']
    - Updates: state['llm_analysis'] (raw text) and state['required_tools'] (List[Dict])
    """
    user_question = state.get("user_input")
    base_prompt = state.get("full_prompt")
    role_tools_raw = state.get("tools", [])
    #print(f"state: {state}")

    if not user_question or not base_prompt:
        raise ValueError("task_analyzer: state thiếu user_question hoặc base_prompt")

    # chuẩn hoá role_tools thành list of dicts
    normalized_role_tools = _normalize_role_tools(role_tools_raw)

    # gọi LLM
    analyzer = GeminiAnalyzerLLM()
    raw_response = analyzer.analyze_task(base_prompt=base_prompt, user_question=user_question, role_tools=normalized_role_tools)

    state["llm_analysis"] = raw_response
    parsed = _extract_json_from_text(raw_response)
    required_raw = []
    if isinstance(parsed, dict) and "required_tools" in parsed:
        required_raw = parsed["required_tools"]
    elif isinstance(parsed, list):
        # LLM trả trực tiếp 1 list
        required_raw = parsed
    else:
        required_raw = []

    # validate & normalize
    required_tools_normalized = _validate_and_format_required_tools(required_raw, normalized_role_tools)

    state["required_tools"] = required_tools_normalized



def tool_executor(state: MultiRoleAgentState) -> None:

    required_tools = state.get("required_tools", [])
    tool_results = []

    for tool_info in required_tools:
        tool_name = tool_info.get("tool_name") or tool_info.get("name")
        params = tool_info.get("params", {})

        if not tool_name:
            continue
        tool_func = TOOL_REGISTRY.get(tool_name)

        if not tool_func:
            tool_results.append({
                "tool_name": tool_name,
                "params": params,
                "result": None
            })
            continue

        try:
            result = tool_func(**params)

        except Exception as e:
            result = f"❌ Lỗi khi thực thi {tool_name}: {str(e)}"

        # Lưu lại kết quả vào danh sách tool_results
        tool_results.append({
            "tool_name": tool_name,
            "params": params,
            "result": result
        })

    # Cập nhật state
    state["tool_results"] = tool_results

def llm_response(state: MultiRoleAgentState) -> None:
    """
    Node tổng hợp kết quả cuối cùng.
    - Dùng GeminiSynthesizerLLM để sinh câu trả lời hoàn chỉnh.
    """

    base_prompt = state.get("full_prompt", "")
    user_question = state.get("user_input", "")
    tool_results = state.get("tool_results", [])

    # --- Kiểm tra dữ liệu đầu vào ---
    if not base_prompt or not user_question:
        raise ValueError("❌ llm_response: thiếu base_prompt hoặc user_question trong state.")

    # --- Chuẩn bị nội dung tool_results (dạng dễ đọc cho LLM) ---
    if tool_results:
        formatted_tool_results = json.dumps(tool_results, ensure_ascii=False, indent=2)
    else:
        formatted_tool_results = "Không có tool nào được gọi hoặc không có kết quả."

    # --- Xây dựng prompt tổng hợp ---
    system_prompt = f"""
Bạn là AI assistant đảm nhận vai trò trả lời câu hỏi người dùng về kiến thúc và tài liệu liên quan đến thủ tục hành chính công.
Dưới đây là prompt hướng dẫn của vai trò này:

<base_PROMPT>
{base_prompt.strip()}
</base_PROMPT>

Người dùng đã hỏi:
<USER_QUESTION>
{user_question.strip()}
</USER_QUESTION>

Các công cụ đã được gọi và trả về kết quả:
<TOOL_RESULTS>
{formatted_tool_results}
</TOOL_RESULTS>

Nhiệm vụ của bạn:
- Dựa trên các thông tin ở trên, hãy viết một câu trả lời tự nhiên, rõ ràng.
- Nếu có dữ liệu từ tool, luôn ưu tiên sử dụng toàn bộ 100% thông tin để trả lời chính xác.
- Nếu trong dữ liệu từ tool có thông tin về link tài liệu, hãy cung cấp link cho người dùng tìm hiểu. Nếu có nhiều link giống nhau, hãy trả về một link (ví dụ a,a,b --> a,b)
- Nếu trả về link, vẫn cần phải tóm tắt nội dung chính trong câu trả lời.
- Nếu không có dữ liệu hoặc dữ liệu mâu thuẫn, hãy trả lời một cách trung lập.
"""

    # --- Gọi LLM tổng hợp ---
    synthesizer = GeminiSynthesizerLLM()
    final_answer = synthesizer.run(system_prompt)

    # --- Cập nhật vào state ---
    state["final_answer"] = final_answer.strip()