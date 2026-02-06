from openai import OpenAI

client = OpenAI(
    api_key="sk-vOFtTBRdiJ76JIRU1tfdBQ02w0Zat4TfJkEHlWcbtObSJrUi",  # 替换为从平台获取的 Key
    base_url="https://api.moonshot.cn/v1",
)

completion = client.chat.completions.create(
    model="kimi-k2-turbo-preview",  # 或其他可用模型
    messages=[
        {"role": "system", "content": "你是Kimi，由Moonshot AI提供的人工智能助手"},
        {"role": "user", "content": "你好，请介绍一下自己"}
    ],
    temperature=0.6,
)

print(completion.choices[0].message.content)