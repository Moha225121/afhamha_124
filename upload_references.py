import os
import socket
from dotenv import load_dotenv
from openai import OpenAI

os.environ["HTTPX_FORCE_IPV4"] = "1"
os.environ["NO_PROXY"] = "*"
socket.setdefaulttimeout(30)

load_dotenv()
client = OpenAI()

PDF_ROOT = "static/References"

# 1️⃣ Create vector store
vector_store = client.vector_stores.create(
    name="Libyan Curriculum PDFs"
)

print("Vector Store ID:", vector_store.id)

# 2️⃣ Upload PDFs ONLY (no waiting)
file_ids = []

for root, _, files in os.walk(PDF_ROOT):
    for f in files:
        if f.lower().endswith(".pdf"):
            path = os.path.join(root, f)
            print("Uploading:", path)
            uploaded_file = client.files.create(
                file=open(path, "rb"),
                purpose="assistants"
            )
            file_ids.append(uploaded_file.id)

# 3️⃣ Attach files WITHOUT blocking
client.vector_stores.file_batches.create(
    vector_store_id=vector_store.id,
    file_ids=file_ids,
    poll=False  # 🔥 THIS IS THE KEY
)

print("Files attached. Indexing continues in background.")
