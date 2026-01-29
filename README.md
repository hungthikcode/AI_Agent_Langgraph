<div align="center">

# 🚀 Chatbot RAG – Vietnamese FAQ Assistant

![Typing SVG](https://readme-typing-svg.demolab.com?center=true&width=600&lines=Vietnamese+RAG+Chatbot;LangGraph+%7C+ChromaDB+%7C+FastAPI;Built+for+Public+Service+FAQs)


> 🤖 Trợ lý hỏi–đáp tiếng Việt dựa trên **Retrieval-Augmented Generation (RAG)**  
> 📚 Dữ liệu từ Cổng Dịch vụ công Quốc gia

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![RAG](https://img.shields.io/badge/RAG-Enabled-success)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-purple)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

</div>

---

## 🧠 Giới thiệu

Đây là dự án **Chatbot RAG** hỗ trợ trả lời **các câu hỏi hành chính công bằng tiếng Việt**,  
sử dụng kiến trúc **RAG (Retrieval-Augmented Generation)** để tăng độ chính xác và giảm hallucination.

📌 **Nguồn dữ liệu**:  
🔗 https://dichvucong.gov.vn/p/home/dvc-cau-hoi-pho-bien.html

---

## 🏗️ Kiến trúc hệ thống

Dự án sử dụng mô hình **Client-Server**:
1.  **Backend (FastAPI):** Điều phối bộ não LangGraph, quản lý các Agent, truy vấn ChromaDB và SQL Server.
2.  **Frontend (Streamlit):** Giao diện người dùng thân thiện, giao tiếp với Backend qua REST API.
3.  **Database:** SQL Server (Lưu lịch sử chat) & ChromaDB (Lưu Vector dữ liệu FAQ).

---

## ⚙️ Công nghệ sử dụng

- **LangGraph** – điều phối agent, state và graph
- **LLM API (Gemini)**
- **Embedding tiếng Việt** (Hugging Face)
- **Vector Database**: ChromaDB
- **RAG Pipeline** cho truy vấn chính xác hơn
- **SQLite** cho lưu trữ dữ liệu nhẹ


---
## 📂 Cấu trúc thư mục

```
project/
│
├── agent_core/              # Logic agent, state, graph
├── chroma_db/               # Chroma vector DB
│   └── chroma.sqlite3       
│
├── connect_SQL/             # Kết nối SQL Server
├── create_vect_db/          # Tạo vector DB từ file CSV
│   ├── faqs.csv
│   └── create_faq_db.py
│
├── models/                  
│   └── Vietnamese_Embedding/  
│
├── prompt/
│   ├── tool.yaml
│   └── General_Prompt.docx
│
├── tools/
│   ├── rag.py
│   └── tool_registry.py
│
├── utils/              
├── app.py       
├── api.py           
├── requirements.txt
├── style.css
└── README.md
└── .env
```

---

## 🐳 CÁCH 1: TRIỂN KHAI NHANH VỚI DOCKER (Khuyên dùng)

Bạn không cần cài đặt Python hay Driver SQL Server, chỉ cần Docker Desktop.

### 1. Chuẩn bị file cấu hình
- Tạo `.env` ở thư mục gốc: `GOOGLE_API_KEY=your_key_here`
- Tạo `connect_SQL/config.json` (Dùng IP `host.docker.internal` nếu SQL Server chạy trên máy cùng máy vật lý).
- Đảm bảo folder `models/Vietnamese_Embedding` đã có sẵn file model.

### 2. Khởi chạy
Chỉ cần chạy một lệnh duy nhất:
```bash
docker-compose up -d
```
Docker sẽ tự động tải các Image `txhungg/langgraph-chatbot` và `txhungg/langgraph-frontend` về và khởi chạy.

- **UI:** `http://localhost:8501`
- **API Docs:** `http://localhost:8000/docs`

---

## 🔧 CÁCH 2: CÀI ĐẶT THỦ CÔNG (Dành cho Dev)

### Clone project

```bash
git https://github.com/hungthikcode/AI_Agent_Langgraph.git
```

### Tạo môi trường Python

```bash
python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows
```

### Cài đặt thư viện

```bash
pip install -r requirements.txt
```

---

## 🔑 2. Tạo file `.env`

Tạo file `.env` ở thư mục gốc:

```
GOOGLE_API_KEY=<your-openai-key>
```

Tạo file `config.json` ở thư mục `connect_SQL` cho database tương ứng:


```
{
    "connection": {
        "server": "",
        "database": "",
        "username": "",
        "password": ""
    }
} 
```

## 🧠 3. Tải mô hình Embedding

Mô hình không kèm theo repo để giảm dung lượng.

Tạo folder `models` trong thư mục dự án và tải từ Hugging Face:

👉 https://huggingface.co/AITeamVN/Vietnamese_Embedding


## 📚 4. Tạo vector database (Chroma)

1. Tạo file `config.json` ở thư mục `create_vecto_db` tương ứng:


```
{
  "faq_csv_path": "",
  "db_path": "", # Tên folder chứa model
  "db_folder": "chroma_db_faqs", # Tạo thêm 1 folder con trong db_path để giúp thao tác xóa
  "collection_name": "faqs_collection",  # Tên collection trong ChromaDB, mặc định là faqs_collection
  "local_model_path": "" # Path của file model đã tải
}
```

2 Tạo vector DB:

```bash
python create_vect_db/create_faq_db.py
```

---

## ▶️ 5. Chạy ứng dụng

**Khởi chạy song song**

Cần mở 2 terminal:
- **Terminal 1 (Backend):** `python api.py`
- **Terminal 2 (Frontend):** `streamlit run app.py`


---


## 🤖 6. Tính năng chính

* Chatbot FAQ hỏi đáp liên quan tới thủ tục hành chính công 
* Tìm kiếm embedding qua ChromaDB
* Agent sử dụng tools RAG
* Tạo DB từ file CSV câu hỏi thường gặp


---

## 📃 License

This project is licensed under the [MIT License](LICENSE). See the `LICENSE` file for more details.