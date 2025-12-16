import streamlit as st
import sqlite3
import pandas as pd
import json
import requests
import os

# ==========================================
# 原本 cwa_crawler.py 的內容 (直接貼在這裡)
# ==========================================

DB_NAME = "data.db"
JSON_FILE = "F-A0010-001.json"
API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"

def get_weather_data(api_key=None):
    # ... (這裡放原本 crawler 的 get_weather_data 函式內容) ...
    # 為了節省篇幅，請把 cwa_crawler.py 的 get_weather_data 整段複製過來
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    elif api_key:
        params = {"Authorization": api_key, "downloadType": "WEB", "format": "JSON"}
        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return data
    return None

def parse_and_save_to_db(data):
    # ... (這裡放原本 crawler 的 parse_and_save_to_db 函式內容) ...
    # 請把 cwa_crawler.py 的 parse_and_save_to_db 整段複製過來
    if not data: return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
            for elem in loc['weatherElement']:
                elem_name = elem['elementName']
                first_val = elem['time'][0]['parameter']['parameterName']
                if elem_name == 'Wx': wx = first_val
                elif elem_name == 'MinT': min_t = first_val
                elif elem_name == 'MaxT': max_t = first_val
            insert_list.append((city_name, min_t, max_t, wx))
        cursor.executemany("INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)", insert_list)
        conn.commit()
    except Exception as e:
        print(e)
    finally:
        conn.close()

# ==========================================
# 原本 app.py 的 Streamlit 介面程式碼
# ==========================================

st.set_page_config(page_title="台灣天氣預報 Dashboard", page_icon="🌦️")
st.title("🌦️ 台灣各縣市天氣預報 (CWA)")

st.sidebar.header("功能選單")

# API Key 處理
if "cwa" in st.secrets:
    api_key = st.secrets["cwa"]["api_key"]
    st.sidebar.success("API Key 已載入 ✅")
else:
    api_key = st.sidebar.text_input("請輸入 CWA API Key", type="password")

if st.sidebar.button("🔄 更新/重抓 資料庫"):
    if not api_key:
        st.error("請先設定 API Key！")
    else:
        with st.spinner("更新中..."):
            # 直接呼叫上面定義好的函式，不用 cwa_crawler. 了
            raw_data = get_weather_data(api_key)
            parse_and_save_to_db(raw_data)
            st.success("完成！")
            st.rerun()

# 讀取 DB 顯示
if os.path.exists(DB_NAME):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM weather", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df[['location', 'min_temp', 'max_temp', 'description']], use_container_width=True)
    else:
        st.warning("資料庫是空的")
else:
    st.info("尚未建立資料庫，請點擊左側更新按鈕")