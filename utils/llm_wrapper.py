import os
import json
from typing import List, Dict, Any
import google.generativeai as genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class GeminiAnalyzerLLM:
    """
    LLM dùng trong agent_executor_node
    → nhiệm vụ: phân tích câu hỏi, chọn tool, suy luận logic
    """
    def __init__(self, model_name: str = "gemini-2.0-flash", api_key_env: str = "GOOGLE_API_KEY_1"):
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"❌ Missing API key: {api_key_env}")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)


    def analyze_task(self, base_prompt: str, user_question: str, role_tools: List[Dict[str, Any]]) -> str:
        """
        Gọi Gemini để phân tích nhiệm vụ.
        -> Trả về CHUỖI chứa JSON (thô) theo schema:
        {
          "analysis": "...",
          "required_tools": [
            {"tool_name": "...", "params": {...}},
            ...
          ]
        }
        """

        tool_descriptions = "\n".join([
            f"- {t['name']}: {t.get('description', '')}\n  Parameters: {t.get('parameters', {})}\n  Returns: {t.get('returns', '')}"
            for t in role_tools
        ])
        system_instruction = (
            "Bạn là một AI chuyên phân tích nhiệm vụ cho hệ thống Multi-Role Agent.\n"
            "Dựa trên prompt của vai trò và danh sách tool có sẵn dưới đây, "
            "hãy chọn một hoặc nhiều tool cần dùng cho câu hỏi người dùng và xác định tham số cho từng tool.\n\n"
            "RẤT QUAN TRỌNG: Đầu ra PHẢI LÀ CHỈ MỘT đối tượng JSON hợp lệ (KHÔNG có giải thích văn bản). "
            "Schema mong muốn:\n"
            "{\n"
            "  \"analysis\": \"<mô tả ngắn về logic>\",\n"
            "  \"required_tools\": [\n"
            "    {\"tool_name\": \"<tên>\", \"params\": {<param_name>: <value>, ...}},\n"
            "    ...\n"
            "  ]\n"
            "}\n\n"
            "Nếu không cần gọi tool nào, trả required_tools = [].\n"
            "Ngôn ngữ trả về: nếu input là tiếng Việt thì trả bằng tiếng Việt."
        )

        example = (
            "Ví dụ JSON hợp lệ:\n"
            "{\n"
            "  \"analysis\": \"Người dùng muốn biết doanh thu Q2, cần tra DB và tóm tắt.\",\n"
            "  \"required_tools\": [\n"
            "    {\"tool_name\": \"search_database\", \"params\": {\"query\": \"doanh thu Q2 2025\", \"limit\": 10}},\n"
            "    {\"tool_name\": \"summarize_report\", \"params\": {\"file_path\": \"search_database:0\"}}\n"
            "  ]\n"
            "}\n"
        )

        prompt = (
            f"{system_instruction}\n\n"
            f"--- ROLE PROMPT ---\n{base_prompt}\n\n"
            f"--- AVAILABLE TOOLS ---\n{tool_descriptions}\n\n"
            f"--- USER QUESTION ---\n{user_question}\n\n"
            f"{example}\n"
            "TRẢ LẠI CHỈ JSON, KHÔNG THÊM BẤT KỲ VĂN BẢN NÀO KHÁC."
        )

        # Gọi Gemini (implementation may vary — dùng generate_content như ví dụ trước)
        response = self.model.generate_content(prompt)

        # Lấy text an toàn
        raw_text = getattr(response, "text", None)
        if raw_text is None:
            # try other representations
            raw_text = str(response)

        return raw_text.strip()

class GeminiSynthesizerLLM:
    """
    LLM dùng trong llm_response_synthesizer
    → nhiệm vụ: tổng hợp kết quả từ tool và sinh câu trả lời cuối cùng
    """
    def __init__(self, model_name: str = "gemini-2.0-flash", api_key_env: str = "GOOGLE_API_KEY_2"):
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"❌ Missing API key: {api_key_env}")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def run(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"[GeminiSynthesizerLLM Error] {str(e)}"
        
        
class GeminiChatParagraphSummarizer:
    """
    LLM dùng để tóm tắt từng cặp hội thoại (user - chatbot)
    """

    def __init__(self, model_name: str = "gemini-2.0-flash", api_key_env: str = "GOOGLE_API_KEY_3"):
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"❌ Missing API key: {api_key_env}")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def summarize_each_exchange(self, chat_json: list) -> str:
        """
        Nhận đầu vào: danh sách hội thoại [{user, chatbot}]
        → Trả về: mỗi phần tử được viết thành 1 đoạn riêng, có xuống dòng.
        """
        chat_data = json.dumps(chat_json, ensure_ascii=False, indent=2)
        system_prompt = f"""
        Bạn là một chuyên gia ngôn ngữ có nhiệm vụ viết lại từng cặp hội thoại giữa người dùng và chatbot
        thành các đoạn văn ngắn, dễ hiểu, mô tả nội dung trao đổi của từng lượt.

        ### Dữ liệu hội thoại
        {chat_data}

        ### Yêu cầu
        - Mỗi cặp {{user, chatbot}} được viết thành **một đoạn văn riêng** (xuống dòng giữa các đoạn).
        - Diễn đạt tự nhiên, tóm tắt ý chính của cả người dùng và chatbot.
        - Không thêm số thứ tự, không dùng gạch đầu dòng.
        - Đầu ra chỉ là các đoạn văn, không kèm ký hiệu hay chú thích khác.
        """
        response = self.model.generate_content(system_prompt)
        raw_text = getattr(response, "text", None)
        if raw_text is None:
            raw_text = str(response)
        return raw_text.strip()