import streamlit as st
import google.generativeai as genai

# 版面設定
st.set_page_config(page_title="Gemini Chat")

# 安全性保持：讀取 API Key
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ 錯誤：未偵測到 API Key。請檢查 .streamlit/secrets.toml 是否已建立。")
    st.stop()

# 設定 Gemini
genai.configure(api_key=api_key)

# 側邊欄設定
with st.sidebar:
    st.title("設定")
    system_instruction = st.text_area("系統指令 (System Instruction)", value="你是一個有用的 AI 助手")
    if st.button("清除對話"):
        st.session_state.messages = []
        st.rerun()

# 狀態管理：初始化對話紀錄
if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示歷史訊息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 處理輸入與回應
if prompt := st.chat_input("輸入你的問題..."):
    # 1. 顯示並儲存使用者訊息
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. 呼叫 Gemini 模型
    try:
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
        #model = genai.GenerativeModel("models/gemini-1.5-flash")
        # 準備對話歷史以保持上下文 (將 Streamlit 格式轉換為 Gemini 格式)
        gemini_history = []
        for msg in st.session_state.messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})
        
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(prompt)
        
        # 3. 顯示並儲存 AI 回應
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"發生錯誤：{e}")