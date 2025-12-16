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
    except Exception as e:
        st.error(f"發生錯誤：{e}")