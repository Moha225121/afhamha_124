import os
import socket
from dotenv import load_dotenv
from openai import OpenAI

# Network stability (Windows)
os.environ["HTTPX_FORCE_IPV4"] = "1"
os.environ["NO_PROXY"] = "*"
socket.setdefaulttimeout(30)

# Load environment variables
load_dotenv()

# ❗ DO NOT hardcode API keys
client = OpenAI()



assistant = client.beta.assistants.create(
    name="افهمها وفهمني – المدرس الليبي",
    model="gpt-4.1-mini",
    instructions="""
أنت مدرس ليبي تشرح المنهج الليبي فقط.
❗ لا تجب إلا من الكتب المرفقة.
❗ إذا لم يوجد الجواب في المراجع، قل: "المعلومة غير موجودة في المنهج".
الشرح يكون باللهجة الليبية البيضاء.
""",
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [VECTOR_STORE_ID]
        }
    }
)

print("Assistant ID:", assistant.id)
