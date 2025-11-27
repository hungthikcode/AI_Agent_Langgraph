# 🚀 Chatbot RAG – Vietnamese FAQ Assistant

Đây là dự án **Chatbot RAG (Retrieval-Augmented Generation)** hỗ trợ hỏi–đáp FAQs bằng tiếng Việt. Hệ thống sử dụng:

* FastAPI (hoặc framework bạn đang sử dụng)
* Vector DB: **ChromaDB**
* Embedding model tiếng Việt (tải từ Hugging Face)
* Pipeline RAG để trả lời câu hỏi chính xác hơn
* SQLite để lưu trữ dữ liệu nhỏ

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
├── requirements.txt
├── style.css
└── README.md
└── .env
```

---

## 🔧 1. Cài đặt môi trường

### Clone project

```bash
git clone https://github.com/<your-name>/<your-repo>.git
cd <your-repo>
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

```bash
streamlit run app.py
```

Ứng dụng chạy tại:

```
http://localhost:8501
```

---


## 🤖 6. Tính năng chính

* Chatbot hỏi đáp tiếng Việt dựa trên RAG
* Tìm kiếm embedding qua ChromaDB
* Agent sử dụng tools RAG
* Tạo DB từ file CSV câu hỏi thường gặp


---

## 📃 License

This project is licensed under the [MIT License](LICENSE). See the `LICENSE` file for more details.