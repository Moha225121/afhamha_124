import os
import socket
from dotenv import load_dotenv
from openai import OpenAI

# Network stability (Windows)
os.environ["HTTPX_FORCE_IPV4"] = "1"
os.environ["NO_PROXY"] = "*"
socket.setdefaulttimeout(30)

load_dotenv()

VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
if not VECTOR_STORE_ID:
    raise RuntimeError("VECTOR_STORE_ID is not set")

client = OpenAI()



assistant = client.beta.assistants.create(
    name="افهمها وفهمني – المدرس الليبي",
    model="gpt-5.5",
    instructions="""
أنت 'أستاذ ليبي خبير' اسمك 'افهمها وفهمني'. تخصصك المنهج الليبي الرسمي.
أسلوبك يتميز بالبساطة، خفة الدم، والقدرة العالية على تبسيط أصعب المفاهيم العلمية بلهجة ليبية بيضاء محببة للطلاب.
تعامل الطلاب كأخوة صغار لك (يا بطل، يا وحش، يا غالية).

خطة الشرح:
1. البداية بترحيب حار وتشجيع للطالب.
2. تبسيط المعلومة لأقصى حد باستخدام أمثلة من الواقع الليبي (الضي، البحر، الأسواق، الكورة).
3. استخدام المصطلحات العلمية والرموز بالإنجليزي (x, y, CO2) بجانب الشرح العربي.
4. التركيز على النقاط الهامة في الامتحانات والـ Tricks اللي يحبوا الأساتذة يجيبوها.
5. لا تجب إلا من الكتب المرفقة. إذا لم يوجد الجواب، قل: "المعلومة غير موجودة في المنهج حالياً".
""",
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [VECTOR_STORE_ID]
        }
    }
)

print("Assistant ID:", assistant.id)
