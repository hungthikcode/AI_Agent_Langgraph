# tools/tool_registry.py

"""
Bản đồ ánh xạ tên tool (dưới dạng string) với hàm Python thực tế.
Các node như tool_executor sẽ sử dụng nó để gọi hàm tương ứng.
"""

from tools.rag import search_project_documents

TOOL_REGISTRY = {
    "search_project_documents": search_project_documents
}
