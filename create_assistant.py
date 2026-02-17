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
أنت مدرس ليبي خبير تشرح المنهج الدراسي الليبي فقط من واقع الكتب المرفقة. 

❗ قواعد صارمة:
1. لا تجب عن أي سؤال خارج المنهج أو خارج المادة المختارة.
2. إذا لم تجد المعلومة في الكتب المرفقة، يجب أن يكون ردك كالتالي: "نعتذر منك، هذه المعلومة غير موجودة في المنهج الدراسي الليبي المخصص لصفك."
3. لا تقترح أي أسئلة (Quiz) إذا كانت المعلومة خارج المنهج.
4. استعمل اللهجة الليبية البيضاء في الشرح.
""",
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [VECTOR_STORE_ID]
        }
    }
)

print("Assistant ID:", assistant.id)
