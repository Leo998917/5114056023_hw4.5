import streamlit as st
import google.generativeai as genai

# 1. 嘗試從 Streamlit Secrets 安全讀取 API Key
# 這樣做的好處是本地開發用 secrets.toml，部署到 Streamlit Cloud 則用後台設定，程式碼完全不用改
api_key = st.secrets.get("GOOGLE_API_KEY")

# 2. 簡單的檢查邏輯
if not api_key:
    st.error("❌ 錯誤：未偵測到 API Key。請檢查 .streamlit/secrets.toml 是否已建立。")
else:
    try:
        # 嘗試配置 (僅做設定，尚未發送請求)
        genai.configure(api_key=api_key)
        
        # 3. 顯示成功訊息
        st.success("系統設置成功，API 連線測試中...")

        if st.button("測試與 Gemini 的連線"):
            try:
                # 1. 找出所有支援 generateContent 的模型
                available_models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_names = [m.name for m in available_models]
                
                # 2. 印出模型清單
                st.write("您的 API Key 可用的模型清單：")
                st.code(model_names)

                if model_names:
                    # 3. 自動選擇第一個模型進行測試
                    target_model = model_names[0]
                    st.info(f"自動選擇測試模型：{target_model}")
                    model = genai.GenerativeModel(target_model)
                    response = model.generate_content("嗨，請用繁體中文跟我打招呼")
                    st.success(f"連線成功！模型回應：{response.text}")
                else:
                    st.error("找不到任何支援 generateContent 的模型，請檢查 API Key 權限。")
            except Exception as e:
                st.error(f"連線失敗：{e}")
    except Exception as e:
        st.error(f"發生錯誤：{e}")