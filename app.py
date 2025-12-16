import streamlit as st
import sqlite3
import pandas as pd
import json
import requests
import os
import urllib3

# ==========================================
# 設定區
# ==========================================

DB_NAME = "data.db"
JSON_FILE = "F-A0010-001.json"
API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"

# ==========================================
# 核心功能：全自動搜尋資料
# ==========================================

def find_location_list(data):
    """
    通用搜尋功能：
    不指定固定路徑，而是遞迴搜尋整個 JSON，
    找到第一個包含 'locationName' 的列表就回傳。
    """
    if isinstance(data, dict):
        # 如果這一層有 'locationName'，那它的上一層(List)應該就是我們要的，但這裡是 Dict，所以繼續往下找
        for key, value in data.items():
            result = find_location_list(value)
            if result:
                return result
    elif isinstance(data, list):
        # 如果這是一個列表，檢查裡面的第一個元素是否包含 'locationName'
        if len(data) > 0 and isinstance(data[0], dict) and 'locationName' in data[0]:
            return data
        # 如果不是，繼續對列表裡的每個元素做搜尋
        for item in data:
            result = find_location_list(item)
            if result:
                return result
    return None

def get_weather_data(api_key):
    """下載資料 (含 SSL 修正)"""
    # 1. 優先讀取本地檔案
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            os.remove(JSON_FILE) # 壞檔重抓
            
    # 2. API 下載
    st.info(f"正在連線 CWA 下載資料...")
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
    """解析並存入 SQLite"""
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
        # === 使用通用搜尋功能 ===
        locations = find_location_list(data)
        
        if not locations:
            st.error("❌ 解析失敗：在整份 JSON 裡都找不到含有 'locationName' 的資料列表")
            st.info("可能是 API Key 權限不符，或下載到了錯誤的資料集。")
            st.json(data) # 印出結構供檢查
            return False

        st.toast(f"✅ 成功找到 {len(locations)} 筆地點資料！", icon="🎉")

        # === 開始提取資料 ===
        insert_list = []
        for loc in locations:
            city_name = loc.get('locationName', '未知')
            wx, min_t, max_t = "N/A", "N/A", "N/A"
            
            # 嘗試抓取 weatherElement
            elements = loc.get('weatherElement', [])
            for elem in elements:
                elem_name = elem.get('elementName')
                time_list = elem.get('time', [])
                
                if not time_list: continue
                
                try:
                    # 抓取第一筆時間資料
                    first_time = time_list[0]
                    val = "N/A"
                    
                    # 處理各種可能的數值結構 (parameter 或 elementValue)
                    if 'parameter' in first_time:
                         val = first_time['parameter'].get('parameterName', 'N/A')
                    elif 'elementValue' in first_time:
                        ev = first_time['elementValue']
                        if isinstance(ev, list) and len(ev) > 0:
                            val = ev[0].get('value', 'N/A')
                        elif isinstance(ev, dict):
                            val = ev.get('value', 'N/A')
                    
                    # 對應欄位 (支援一般預報與農業預報的欄位名稱)
                    if elem_name == 'Wx': wx = val
                    elif elem_name in ['MinT', 'T']: min_t = val
                    elif elem_name in ['MaxT']: max_t = val
                except:
                    continue
            
            insert_list.append((city_name, min_t, max_t, wx))

        cursor.executemany("INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)", insert_list)
        conn.commit()
        return True

    except Exception as e:
        st.error(f"❌ 資料庫寫入錯誤: {e}")
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
        with st.spinner("正在連線並搜尋資料..."):
            # 強制刪除舊檔，確保使用最新邏輯解析
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