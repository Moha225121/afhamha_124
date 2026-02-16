import os
import socket
from dotenv import load_dotenv
from openai import OpenAI

import time

# Increased timeout for large file uploads
socket.setdefaulttimeout(120)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def upload_with_retry(path, purpose, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.files.create(
                file=open(path, "rb"),
                purpose=purpose
            )
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 5
                print(f"⚠️ Upload failed for {os.path.basename(path)}. Retrying in {wait}s... ({e})")
                time.sleep(wait)
            else:
                raise e

PDF_ROOT = "static/References"

# Map folder names to human-readable names for OpenAI Vector Stores
FOLDER_NAMES = {
    "7th_grade": "7th Grade (Preparatory)",
    "8th_grade": "8th Grade (Preparatory)",
    "9th_grade": "9th Grade (Preparatory)",
    "1st_secandory": "1st Secondary (General)",
    "2nd_secandory_L": "2nd Secondary (Literary)",
    "2nd_secandory_s": "2nd Secondary (Scientific)",
    "3rd_secandory_L": "3rd Secondary (Literary)",
    "3rd_secandory_S": "3rd Secondary (Scientific)"
}

def upload_folder_as_vector_store(folder_path, store_name):
    print(f"\n📁 Processing: {store_name}...")
    
    # 1. Create a Vector Store for this grade
    vector_store = client.vector_stores.create(name=f"Libyan_Curriculum_{store_name}")
    print(f"✅ Created Vector Store: {vector_store.id}")
    
    file_ids = []
    
    # 2. Upload only PDFs from this specific folder
    for f in os.listdir(folder_path):
        if f.lower().endswith(".pdf"):
            path = os.path.join(folder_path, f)
            print(f"📤 Uploading: {f}")
            try:
                uploaded_file = upload_with_retry(path, "assistants")
                file_ids.append(uploaded_file.id)
            except Exception as e:
                print(f"❌ Failed to upload {f} after retries: {e}")

    if not file_ids:
        print(f"⚠️ No PDFs found in {folder_path}. Deleting empty vector store.")
        client.vector_stores.delete(vector_store.id)
        return None

    # 3. Attach files to the store
    print(f"🔗 Attaching {len(file_ids)} files...")
    client.vector_stores.file_batches.create(
        vector_store_id=vector_store.id,
        file_ids=file_ids
    )
    
    return vector_store.id

# Main Execution
env_updates = []

for folder in os.listdir(PDF_ROOT):
    full_path = os.path.join(PDF_ROOT, folder)
    if os.path.isdir(full_path) and folder in FOLDER_NAMES:
        store_id = upload_folder_as_vector_store(full_path, FOLDER_NAMES[folder])
        if store_id:
            env_key = f"VECTOR_STORE_{folder.upper()}"
            env_updates.append(f"{env_key}={store_id}")

print("\n" + "="*50)
print("📌 FINISHED! Add these to your .env file:")
print("="*50)
for update in env_updates:
    print(update)
print("="*50)
print("⚠️ Note: Indexing happens in the background. It may take a few minutes before the AI can see the new files.")
