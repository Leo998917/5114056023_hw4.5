import streamlit as st
import sqlite3
import pandas as pd
import json
import os

# --- 設定區 ---
JSON_FILE_NAME = "F-A0010-001.json"
DB_NAME = "data.db"

def find_locations_list(data):
    """
    聰明的路徑搜尋器：嘗試在 JSON 中找到 'locations' -> 'location' 的列表
    """
    # 嘗試路徑 1: 標準 CWA API (cwaopendata -> dataset)
    try:
        return data['cwaopendata']['dataset']['locations']['location']
    except KeyError:
        pass
    
    # 嘗試路徑 2: 另一種常見格式 (records)
    try:
        return data['records']['locations']['location']
    except KeyError:
        pass

    # 嘗試路徑 3: 只有 dataset 開頭
    try:
        return data['dataset']['locations']['location']
    except KeyError:
        pass
        
    return None

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
            
        # 3. 解析資料 (使用聰明搜尋)
        locations = find_locations_list(data)
        
        if locations is None:
            # 如果還是找不到，把最上層的 keys 印出來給你看，方便除錯
            st.error(f"❌ 無法識別 JSON 結構。")
            st.write("你的 JSON 最上層欄位是：", list(data.keys()))
            return False
            
        weather_records = []
        
        for loc in locations:
            city_name = loc.get('locationName', '未知地區')
            min_t, max_t, desc = None, None, None
            
            # 遍歷天氣因子
            for element in loc['weatherElement']:
                ele_name = element['elementName']
                if element['time']:
                    # 處理時間段結構
                    time_entry = element['time'][0]
                    first_value = time_entry.get('elementValue', time_entry.get('parameter', {}))
                    
                    # 防呆：有些格式是 list，有些是 dict
                    if isinstance(first_value, list):
                        val = first_value[0]['value']
                    elif isinstance(first_value, dict):
                        # 有些舊版是用 parameterName/parameterValue
                        val = first_value.get('value', first_value.get('parameterName'))
                    else:
                        val = str(first_value)

                    if ele_name == 'MinT':
                        min_t = val
                    elif ele_name == 'MaxT':
                        max_t = val
                    elif ele_name == 'Wx':
                        desc = val
            
            weather_records.append((city_name, min_t, max_t, desc))
            
    except Exception as e:
        st.error(f"❌ 處理過程發生錯誤：{e}")
        return False

    # 4. 存入 SQLite 資料庫
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            min_temp REAL,
            max_temp REAL,
            description TEXT
        )
    ''')
    
    c.execute('DELETE FROM weather')
    c.executemany('INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)', weather_records)
    conn.commit()
    conn.close()
    return True

# --- Streamlit 介面 ---
st.title("🌤️ 台灣鄉鎮天氣預報 (Local JSON 版)")
st.write("### 作業 Part 1：解析本地 JSON 並存入資料庫")

if st.button("🚀 讀取 JSON 並寫入資料庫"):
    if process_local_json_to_db():
        st.success("✅ 成功！資料已解析並存入 data.db")
        st.balloons()

if os.path.exists(DB_NAME):
    st.subheader("📊 資料庫目前的內容 (data.db)")
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql("SELECT * FROM weather", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.info(f"共讀取到 {len(df)} 筆資料")
        else:
            st.warning("資料庫目前是空的。")
    except:
        st.warning("尚未建立資料表。")
    finally:
        conn.close()
else:
    st.info("👈 請點擊按鈕開始處理資料")