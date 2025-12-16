import streamlit as st
import google.generativeai as genai
import PIL.Image

# 1. 版面設定
st.set_page_config(page_title="Gemini Chat", layout="centered")

# 2. 安全性檢查
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("❌ 錯誤：未偵測到 API Key。請檢查 .streamlit/secrets.toml 是否已建立。")
    st.stop()

# 3. 設定 Gemini
genai.configure(api_key=api_key)

# 4. 自動偵測可用模型 (關鍵修正：不再手動寫死名稱)
try:
    # 找出所有支援 'generateContent' 的模型
    available_models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    if not available_models:
        st.error("❌ 您的 API Key 沒有可用的模型權限。")
        st.stop()
    
    # 直接選用列表中的第一個模型 (通常是 gemini-1.5-flash 或 gemini-pro)
    # 這樣做保證模型名稱絕對正確，因為是 API 自己告訴我們的
    target_model_name = available_models[0].name
    
except Exception as e:
    st.error(f"❌ 無法取得模型清單，請檢查 API Key 或網路連線：{e}")
    st.stop()

# 5. 側邊欄設定
with st.sidebar:
    st.title("🔧 設定")
    # 顯示目前自動選到的模型，讓你心裡有數
    st.caption(f"目前使用模型：`{target_model_name}`")
    
    system_instruction = st.text_area(
        "系統指令 (System Instruction)", 
        value="你是一個繁體中文的 AI 助手，回答請簡潔有力。",
        height=150
    )
    
    # 圖片上傳功能
    uploaded_file = st.file_uploader("📸 上傳圖片 (可選)", type=['jpg', 'png', 'jpeg'])
    img = None
    if uploaded_file:
        img = PIL.Image.open(uploaded_file)
        st.image(img, caption="已上傳圖片", use_column_width=True)

    if st.button("🗑️ 清除對話"):
        st.session_state.messages = []
        st.rerun()

# 6. 狀態管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# 7. 顯示歷史訊息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image" in message:
            st.image(message["image"])

# 8. 處理輸入與回應
if prompt := st.chat_input("輸入你的問題..."):
    # 顯示使用者訊息
    with st.chat_message("user"):
        st.markdown(prompt)
        if img:
            st.image(img)
    
    user_msg = {"role": "user", "content": prompt}
    if img:
        user_msg["image"] = img
    st.session_state.messages.append(user_msg)

    # 呼叫 Gemini
    try:
        # 初始化模型 (加入 system_instruction)
        model = genai.GenerativeModel(
            target_model_name, 
            system_instruction=system_instruction
        )
        
        # 轉換歷史紀錄格式
        gemini_history = []
        for m in st.session_state.messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            parts = [m["content"]]
            if "image" in m:
                parts.append(m["image"])
            gemini_history.append({"role": role, "parts": parts})
        
        chat = model.start_chat(history=gemini_history)
        
        # 顯示 AI 思考中的狀態
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            with st.spinner(f"Gemini ({target_model_name}) 正在思考..."):
                # 判斷是否包含圖片傳送
                if img:
                    response = chat.send_message([prompt, img])
                else:
                    response = chat.send_message(prompt)
                response_placeholder.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"發生錯誤：{e}")