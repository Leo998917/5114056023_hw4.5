import streamlit as st
import sqlite3
import pandas as pd
import cwa_crawler  # 匯入上面的爬蟲模組

# 設定頁面標題
st.set_page_config(page_title="台灣天氣預報 Dashboard", page_icon="🌦️")

st.title("🌦️ 台灣各縣市天氣預報 (CWA)")

# --- 側邊欄設定 ---
st.sidebar.header("功能選單")

# 嘗試從 secrets 讀取 API Key
try:
    api_key = st.secrets["cwa"]["api_key"]
    st.sidebar.success("API Key 已從 Secrets 載入 ✅")
except Exception:
    api_key = st.sidebar.text_input("請輸入 CWA API Key", type="password")
    st.sidebar.warning("尚未設定 secrets.toml，請手動輸入")

# 更新資料庫的按鈕
if st.sidebar.button("🔄 更新/重抓 資料庫"):
    if not api_key:
        st.error("請先設定 API Key 才能下載最新資料！")
    else:
        with st.spinner("正在向氣象局抓取資料並寫入 SQLite..."):
            # 呼叫爬蟲模組的函式
            raw_data = cwa_crawler.get_weather_data(api_key)
            cwa_crawler.parse_and_save_to_db(raw_data)
            st.success("資料庫更新完成！")
            # 重新整理頁面以顯示新數據 (Streamlit 特性)
            st.rerun()

# --- 主畫面：讀取 SQLite ---
db_path = "data.db"

def load_data():
    try:
        conn = sqlite3.connect(db_path)
        # 直接讀取成 DataFrame
        df = pd.read_sql("SELECT * FROM weather", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"讀取資料庫失敗 (可能尚未建立): {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # 顯示數據指標 (Metrics) - 稍微美化一下
    st.subheader("📊 資料總覽")
    col1, col2 = st.columns(2)
    col1.metric("資料筆數", f"{len(df)} 筆")
    col1.metric("資料來源", "中央氣象局 (CWA)")
    
    # 顯示表格
    st.subheader("📋 詳細天氣列表")
    # 整理一下欄位名稱顯示比較好看
    display_df = df[['location', 'min_temp', 'max_temp', 'description']].copy()
    display_df.columns = ['地區', '最低溫 (°C)', '最高溫 (°C)', '天氣狀況']
    
    st.dataframe(display_df, use_container_width=True)

    # (選用) 簡單的圖表：如果溫度是數字的話
    # 因為 JSON 裡有時是字串，這裡做個簡單轉換嘗試繪圖
    try:
        df['min_temp'] = pd.to_numeric(df['min_temp'])
        df['max_temp'] = pd.to_numeric(df['max_temp'])
        st.subheader("📈 氣溫分佈圖")
        st.bar_chart(df.set_index('location')[['min_temp', 'max_temp']])
    except:
        st.info("溫度資料格式無法轉換為圖表，僅顯示表格。")

else:
    st.warning("⚠️ 資料庫是空的或是找不到 `data.db`。")
    st.info("請確認 `F-A0010-001.json` 存在，或在側邊欄輸入 API Key 並點擊「更新資料庫」。")