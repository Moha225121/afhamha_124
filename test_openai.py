from openai import OpenAI

client = OpenAI()

r = client.responses.create(
    model="gpt-4o-mini",
    input="قول مرحبا باللهجة الليبية"
)

print(r.output_text)
