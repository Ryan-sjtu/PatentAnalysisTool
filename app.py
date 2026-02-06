import os
for k in [
    "HTTP_PROXY","HTTPS_PROXY","ALL_PROXY",
    "http_proxy","https_proxy","all_proxy",
    "NO_PROXY","no_proxy"
]:
    os.environ.pop(k, None)
import tempfile
import streamlit as st
from dotenv import load_dotenv

from pdf_utils import extract_pdf_text
from kimi_client import KimiClient
from docx_builder import build_docx

load_dotenv()

st.set_page_config(page_title="Kimi 专利分析工具", layout="wide")
st.title("📄 Kimi 专利分析工具（PDF → Word 报告）")

with st.sidebar:
    st.header("设置")
    max_pages = st.number_input("最多解析页数", min_value=1, max_value=600, value=200)
    temperature = st.slider("生成温度（越低越稳）", 0.0, 1.0, 0.2, 0.05)

st.write("上传 PDF 后点击 **询问**，系统会把 PDF 文本 + 固定 Prompt 发给 Kimi，返回内容生成 Word 报告。")

uploaded = st.file_uploader("上传专利 PDF", type=["pdf"])
ask_btn = st.button("💬 询问", type="primary", disabled=(uploaded is None))

def load_prompt() -> str:
    prompt_path = os.path.join("prompts", "patent_analysis_prompt.txt")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"缺少 Prompt 文件：{prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def clean_pdf_text(text: str) -> str:
    # 极简清洗：去控制字符 + 压缩空白
    import re
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

if ask_btn and uploaded:
    # =========================
    # ✅ 最小 UI 防抖：session_state 锁（防止重复触发）
    # =========================
    if st.session_state.get("busy", False):
        st.warning("正在生成中，请勿重复点击。")
        st.stop()
    st.session_state["busy"] = True

    try:
        pdf_bytes = uploaded.read()

        with st.spinner("1/3 正在解析PDF文本..."):
            pdf_text = extract_pdf_text(pdf_bytes, max_pages=int(max_pages))
            pdf_text = clean_pdf_text(pdf_text)
            if not pdf_text.strip():
                st.error("PDF 未解析到文本：可能是扫描版图片PDF。需要OCR后再分析。")
                st.stop()

        with st.spinner("2/3 正在调用Kimi生成分析报告..."):
            prompt = load_prompt()

            # ✅ 仅新增：从 .env 读取 API Key，并传给 KimiClient
            api_key = os.getenv("KIMI_API_KEY")
            if not api_key:
                st.error("❌ 未检测到 KIMI_API_KEY。请在项目根目录创建 .env 文件并写入：KIMI_API_KEY=你的key")
                st.stop()

            client = KimiClient(api_key=api_key)

            # 把 Prompt + PDF文本 拼成 user 内容（最稳、最简单）
            user_content = (
                f"{prompt}\n\n"
                f"====================\n"
                f"【以下是专利文件解析出的正文文本】\n"
                f"====================\n"
                f"{pdf_text}\n"
            )

            messages = [
                {"role": "system", "content": "你是专业专利分析师。请严格按用户Prompt结构输出。"},
                {"role": "user", "content": user_content},
            ]
            st.write("model env:", os.getenv("KIMI_TEXT_MODEL"))
            llm_text = client.chat(messages=messages, temperature=float(temperature))

        with st.spinner("3/3 正在生成Word文档..."):
            with tempfile.TemporaryDirectory() as td:
                out_path = os.path.join(td, f"{os.path.splitext(uploaded.name)[0]}_专利分析报告.docx")
                build_docx(out_path=out_path, pdf_name=uploaded.name, llm_text=llm_text)

                with open(out_path, "rb") as f:
                    st.success("✅ 已生成 Word 报告")
                    st.download_button(
                        label="📥 下载 Word 报告（.docx）",
                        data=f.read(),
                        file_name=os.path.basename(out_path),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

        with st.expander("查看Kimi原始输出（调试用）"):
            st.text(llm_text)
    except Exception as e:
        msg = str(e)
    # 尝试把 Kimi 服务端返回体也展示出来（如果有）
        if hasattr(e, "response") and e.response is not None:
            msg += "\n\n--- 服务端返回 ---\n" + e.response.text
        st.error(f"失败：{msg}")

    finally:
        # ✅ 无论成功失败都释放锁
        st.session_state["busy"] = False
