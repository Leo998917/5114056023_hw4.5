import streamlit as st
import sqlite3
import pandas as pd
import json
import requests
import os

# ==========================================
# 核心功能區 (爬蟲 + 資料庫)
# ==========================================

DB_NAME = "data.db"
JSON_FILE = "F-A0010-001.json"
# 使用 API 的網址
API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"

def get_weather_data(api_key):
    """下載或讀取資料"""
    # 1. 如果本地已經有 JSON，直接讀取
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
            
    # 2. 如果沒有，才用 API 去抓
    print(f"正在使用 Key: {api_key[:5]}... 下載資料") # Debug用
    params = {
        "Authorization": api_key,
        "downloadType": "WEB",
        "format": "JSON"
    }
    try:
        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            # 存一份在本地
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return data
        else:
            st.error(f"下載失敗，HTTP 狀態碼: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"連線錯誤: {e}")
        return None

def parse_and_save_to_db(data):
    """解析並存入 SQLite"""
    if not data: return False

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 重置資料表
    cursor.execute("DROP TABLE IF EXISTS weather")
    cursor.execute("""
        CREATE TABLE weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT, min_temp TEXT, max_temp TEXT, description TEXT
        )
    """)

    try:
        locations = data['cwaopendata']['dataset']['location']
        insert_list = []
        for loc in locations:
            city_name = loc['locationName']
            wx, min_t, max_t = "N/A", "N/A", "N/A"
            
            # 簡單抓取第一個時段的資料
            for elem in loc['weatherElement']:
                elem_name = elem['elementName']
                try:
                    first_val = elem['time'][0]['parameter']['parameterName']
                    if elem_name == 'Wx': wx = first_val
                    elif elem_name == 'MinT': min_t = first_val
                    elif elem_name == 'MaxT': max_t = first_val
                except:
                    continue
            
            insert_list.append((city_name, min_t, max_t, wx))

        cursor.executemany("INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)", insert_list)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"解析資料錯誤: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# Streamlit 介面區
# ==========================================

st.set_page_config(page_title="台灣天氣預報 Dashboard", page_icon="🌦️")
st.title("🌦️ 台灣各縣市天氣預報 (CWA)")

st.sidebar.header("功能選單")

# --- 修正後的 API Key 讀取邏輯 ---
api_key = None

# 1. 先找有沒有 [cwa] 下的 api_key
if "cwa" in st.secrets and "api_key" in st.secrets["cwa"]:
    api_key = st.secrets["cwa"]["api_key"]
# 2. 再找有沒有直接寫在根目錄的 api_key
elif "api_key" in st.secrets:
    api_key = st.secrets["api_key"]

# --- 介面邏輯 ---
if api_key:
    st.sidebar.success(f"API Key 已載入 (開頭: {api_key[:4]}...) ✅")
else:
    st.sidebar.warning("⚠️ 未偵測到 Secrets，請手動輸入")
    api_key = st.sidebar.text_input("輸入 CWA API Key", type="password")

# 更新按鈕
if st.sidebar.button("🔄 更新/重抓 資料庫"):
    if not api_key:
        st.error("❌ 沒有 API Key，無法下載！")
    else:
        with st.spinner("正在連線中央氣象局下載資料..."):
            # 刪除舊的 json 確保抓到新的
            if os.path.exists(JSON_FILE):
                os.remove(JSON_FILE)
            
            raw_data = get_weather_data(api_key)
            if raw_data:
                success = parse_and_save_to_db(raw_data)
                if success:
                    st.success("✅ 資料庫更新完成！")
                    st.rerun()

# 顯示資料
if os.path.exists(DB_NAME):
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql("SELECT * FROM weather", conn)
        conn.close()
        
        if not df.empty:
            st.subheader("📊 天氣資料總覽")
            st.dataframe(df[['location', 'min_temp', 'max_temp', 'description']], use_container_width=True)
        else:
            st.warning("資料庫是空的，請點擊更新按鈕。")
    except Exception as e:
        st.error(f"讀取資料庫失敗: {e}")
else:
    st.info("👋 嗨！這是第一次執行，系統還找不到資料庫。")
    if api_key:
        st.markdown("👉 請點擊左側的 **「🔄 更新/重抓 資料庫」** 按鈕來初始化。")
    else:
        st.markdown("👉 請先輸入 Key，再點擊更新按鈕。")