import streamlit as st
import sqlite3
import pandas as pd
import json
import requests
import os
import urllib3

# ==========================================
# 核心功能區
# ==========================================

DB_NAME = "data.db"
JSON_FILE = "F-A0010-001.json"
API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"

def get_weather_data(api_key):
    """下載或讀取資料"""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            os.remove(JSON_FILE)
            
    print(f"正在使用 Key: {api_key[:5]}... 下載資料")
    params = {
        "Authorization": api_key,
        "downloadType": "WEB",
        "format": "JSON"
    }
    try:
        urllib3.disable_warnings() 
        response = requests.get(API_URL, params=params, verify=False)
        
        if response.status_code == 200:
            try:
                data = response.json()
                with open(JSON_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                return data
            except:
                st.error("❌ 下載內容不是有效的 JSON")
                return None
        else:
            st.error(f"❌ 下載失敗，狀態碼: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"❌ 連線錯誤: {e}")
        return None

def parse_and_save_to_db(data):
    """解析並存入 SQLite (支援多種 JSON 結構)"""
    if not data: return False

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
        # --- 智慧路徑搜尋 ---
        locations = []
        root = data.get('cwaopendata', {})
        
        # 1. 嘗試標準路徑 (dataset -> location)
        if 'dataset' in root and 'location' in root['dataset']:
            locations = root['dataset']['location']
            
        # 2. 嘗試資源路徑 (resources -> resource -> data -> locations -> location)
        # 針對 F-A0010-001 (農業預報)
        elif 'resources' in root:
            try:
                # 這裡路徑比較深，我們要一層一層挖
                res = root['resources']['resource']
                # 有時候 data 是 siblings，看截圖推測結構
                if 'data' in res:
                    if 'locations' in res['data'] and 'location' in res['data']['locations']:
                        locations = res['data']['locations']['location']
                    elif 'location' in res['data']:
                        locations = res['data']['location']
            except Exception as e:
                st.warning(f"嘗試解析 resources 路徑時失敗: {e}")

        if not locations:
            st.error("❌ 解析失敗：找不到 'location' 列表")
            st.info("👇 目前抓到的資料結構 (根目錄 keys):")
            st.write(list(root.keys()))
            if 'resources' in root:
                st.info("👇 Resources 內部結構:")
                st.json(root['resources'])
            return False

        # --- 開始提取資料 ---
        insert_list = []
        for loc in locations:
            city_name = loc.get('locationName', '未知')
            wx, min_t, max_t = "N/A", "N/A", "N/A"
            
            # 處理 weatherElement
            # 注意：農業預報的 element 結構可能也跟一般不同，這裡做一個通用嘗試
            elements = loc.get('weatherElement', [])
            for elem in elements:
                elem_name = elem.get('elementName')
                time_list = elem.get('time', [])
                
                if not time_list: continue
                
                # 嘗試取出數值，這裡做多重保險
                try:
                    first_time = time_list[0]
                    val = "N/A"
                    
                    # 情況 A: parameter -> parameterName (一般預報)
                    if 'parameter' in first_time:
                         val = first_time['parameter'].get('parameterName', 'N/A')
                    # 情況 B: elementValue -> value (農業/其他預報)
                    elif 'elementValue' in first_time:
                        # 有可能是 list 或 dict
                        ev = first_time['elementValue']
                        if isinstance(ev, list) and len(ev) > 0:
                            val = ev[0].get('value', 'N/A')
                        elif isinstance(ev, dict):
                            val = ev.get('value', 'N/A')
                    
                    # 對應欄位
                    if elem_name == 'Wx': wx = val
                    elif elem_name in ['MinT', 'T']: min_t = val # 農業預報有時是 T (平均溫)
                    elif elem_name in ['MaxT']: max_t = val
                except:
                    continue
            
            insert_list.append((city_name, min_t, max_t, wx))

        cursor.executemany("INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)", insert_list)
        conn.commit()
        return True

    except Exception as e:
        st.error(f"❌ 發生未預期的錯誤: {e}")
        st.write(data) # 印出資料幫忙除錯
        return False
    finally:
        conn.close()

# ==========================================
# Streamlit 介面區
# ==========================================

st.set_page_config(page_title="台灣天氣預報 Dashboard", page_icon="🌦️")
st.title("🌦️ 台灣各縣市天氣預報 (CWA)")

st.sidebar.header("功能選單")

# API Key 讀取
api_key = None
if "cwa" in st.secrets and "api_key" in st.secrets["cwa"]:
    api_key = st.secrets["cwa"]["api_key"]
elif "api_key" in st.secrets:
    api_key = st.secrets["api_key"]

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
        with st.spinner("正在連線中央氣象局..."):
            # 強制刪除舊檔
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
    st.info("👋 請點擊左側的 **「🔄 更新/重抓 資料庫」** 按鈕來初始化。")