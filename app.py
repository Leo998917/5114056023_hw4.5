import streamlit as st
import requests
import sqlite3
import pandas as pd
import os

# --- 設定區 ---
API_KEY = "CWA-1FFDDAEC-161F-46A3-BE71-93C32C52829F"
# 這是你提供的作業 JSON URL
JSON_URL = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001?Authorization={API_KEY}&downloadType=WEB&format=JSON"
DB_NAME = "data.db"

def fetch_and_save_data():
    """下載資料、解析並存入 SQLite (作業步驟 1~4)"""
    
    # 1️⃣ 下載 JSON 資料
    response = requests.get(JSON_URL)
    if response.status_code != 200:
        st.error(f"下載失敗，狀態碼：{response.status_code}")
        return False
    
    data = response.json()
    
    # 建立資料列表準備寫入
    weather_records = []

    try:
        # 2️⃣ 解析資料 (針對 F-A0010-001 的結構)
        # 資料結構通常是: cwaopendata -> dataset -> locations -> location (list)
        locations = data['cwaopendata']['dataset']['locations']['location']
        
        for loc in locations:
            city_name = loc.get('locationName', '未知') # 這裡通常是縣市或鄉鎮名
            
            # 初始化變數
            min_t = None
            max_t = None
            desc = None
            
            # 取出天氣元素 (Wx, MinT, MaxT)
            # 我們只取「第一個時段」(time[0]) 做為示範
            for element in loc['weatherElement']:
                ele_name = element['elementName']
                # 確保有時間區段資料
                if element['time']:
                    first_slot = element['time'][0]
                    value = first_slot['elementValue']['value']
                    
                    if ele_name == 'MinT':
                        min_t = value
                    elif ele_name == 'MaxT':
                        max_t = value
                    elif ele_name == 'Wx': # 天氣現象描述
                        desc = value
            
            # 整理一筆資料
            weather_records.append((city_name, min_t, max_t, desc))
            
    except KeyError as e:
        st.error(f"JSON 解析錯誤，欄位結構可能改變: {e}")
        return False

    # 3️⃣ & 4️⃣ 設計資料庫並寫入 SQLite3
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 建立 Table (如果不存在)
    c.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            min_temp REAL,
            max_temp REAL,
            description TEXT
        )
    ''')
    
    # 為了避免重複執行導致資料無限增加，我們先清空舊資料 (作業通常希望每次跑都是最新的)
    c.execute('DELETE FROM weather')
    
    # 寫入資料
    c.executemany('INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)', weather_records)
    
    conn.commit()
    conn.close()
    
    return True

# --- Streamlit 介面區 (作業步驟 5) ---

st.title("🌤️ 台灣各地鄉鎮天氣預報 (作業 Part 1)")

# 建立一個按鈕來觸發「下載與更新資料庫」的動作
if st.button("更新資料庫 (從 CWA API 下載)"):
    with st.spinner("正在下載並解析資料..."):
        success = fetch_and_save_data()
        if success:
            st.success("✅ 資料庫更新成功！已存入 data.db")
        else:
            st.error("❌ 更新失敗")

# 5️⃣ 顯示從 SQLite 讀出的資料表格
if os.path.exists(DB_NAME):
    st.subheader("📊 資料庫內容預覽")
    
    # 連接資料庫讀取資料
    conn = sqlite3.connect(DB_NAME)
    
    # 使用 Pandas 讀取 SQL (這是顯示表格最快的方法)
    df = pd.read_sql("SELECT * FROM weather", conn)
    conn.close()
    
    if not df.empty:
        # 顯示 Dataframe
        st.dataframe(df, use_container_width=True)
        
        # 額外加分題：簡單的統計數據
        st.info(f"目前資料庫中共有 {len(df)} 筆鄉鎮天氣資料。")
    else:
        st.warning("資料庫是空的，請點擊上方按鈕更新資料。")
else:
    st.warning("找不到 data.db，請點擊上方按鈕建立資料庫。")