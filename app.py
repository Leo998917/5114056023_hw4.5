import streamlit as st
import sqlite3
import pandas as pd
import json
import os

# --- 設定區 ---
JSON_FILE_NAME = "F-A0010-001.json"  # 請確認你的 JSON 檔名完全一樣
DB_NAME = "data.db"

def process_local_json_to_db():
    """讀取本地 JSON -> 解析 -> 存入 SQLite"""
    
    # 1. 檢查檔案是否存在
    if not os.path.exists(JSON_FILE_NAME):
        st.error(f"❌ 找不到檔案：{JSON_FILE_NAME}，請確認它是否在 app.py 旁邊。")
        return False

    try:
        # 2. 讀取本地 JSON 檔案
        with open(JSON_FILE_NAME, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 3. 解析資料 (針對 F-A0010-001 結構)
        # 結構通常是: cwaopendata -> dataset -> locations -> location
        # 注意：不同 API 版本結構可能有微小差異，若報錯請檢查 JSON 根目錄
        if 'cwaopendata' in data:
            root = data['cwaopendata']['dataset']
        else:
            # 有些舊版或不同下載點的根目錄不同
            root = data['records'] 

        locations = root['locations']['location']
        
        weather_records = []
        
        for loc in locations:
            city_name = loc.get('locationName', '未知地區')
            
            min_t, max_t, desc = None, None, None
            
            # 遍歷天氣因子 (MinT, MaxT, Wx)
            for element in loc['weatherElement']:
                ele_name = element['elementName']
                # 取第一筆時間段 (最近的預報)
                if element['time']:
                    first_value = element['time'][0]['elementValue']
                    # 有些格式是 list，有些是 dict，做個防呆
                    val = first_value[0]['value'] if isinstance(first_value, list) else first_value['value']
                    
                    if ele_name == 'MinT':
                        min_t = val
                    elif ele_name == 'MaxT':
                        max_t = val
                    elif ele_name == 'Wx':
                        desc = val
            
            weather_records.append((city_name, min_t, max_t, desc))
            
    except Exception as e:
        st.error(f"❌ JSON 解析失敗：{e}")
        return False

    # 4. 存入 SQLite 資料庫
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 建立 Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            min_temp REAL,
            max_temp REAL,
            description TEXT
        )
    ''')
    
    # 清空舊資料 (避免重複)
    c.execute('DELETE FROM weather')
    
    # 寫入新資料
    c.executemany('INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)', weather_records)
    
    conn.commit()
    conn.close()
    return True

# --- Streamlit 介面 ---
st.title("🌤️ 台灣鄉鎮天氣預報 (Local JSON 版)")

st.write("### 作業 Part 1：解析本地 JSON 並存入資料庫")

# 操作按鈕
if st.button("🚀 讀取 JSON 並寫入資料庫"):
    if process_local_json_to_db():
        st.success("✅ 成功！資料已解析並存入 data.db")
        st.balloons()

# 顯示資料庫內容
if os.path.exists(DB_NAME):
    st.subheader("📊 資料庫目前的內容 (data.db)")
    
    conn = sqlite3.connect(DB_NAME)
    # 用 Pandas 讀取最漂亮
    try:
        df = pd.read_sql("SELECT * FROM weather", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.info(f"共讀取到 {len(df)} 筆資料")
        else:
            st.warning("資料庫目前是空的，請點擊上方按鈕載入資料。")
    except Exception as e:
        st.warning("尚未建立資料表。")
    finally:
        conn.close()
else:
    st.info("👈 請點擊按鈕開始處理資料")