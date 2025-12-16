import streamlit as st
import sqlite3
import pandas as pd
import json
import requests
import os
import urllib3

# ==========================================
# 核心功能區 (爬蟲 + 資料庫)
# ==========================================

DB_NAME = "data.db"
JSON_FILE = "F-A0010-001.json"
API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"

def get_weather_data(api_key):
    """下載或讀取資料 (含 SSL 修正 + 強制除錯)"""
    
    # 1. 如果本地已經有 JSON，先讀讀看
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            os.remove(JSON_FILE) # 壞檔就刪
            
    # 2. 用 API 去抓
    st.info(f"正在嘗試連線 CWA 下載資料 (Key 前 5 碼: {api_key[:5]})...")
    params = {
        "Authorization": api_key,
        "downloadType": "WEB",
        "format": "JSON"
    }
    try:
        # =========== SSL 憑證修正 ===========
        urllib3.disable_warnings() 
        response = requests.get(API_URL, params=params, verify=False)
        # ===================================
        
        if response.status_code == 200:
            try:
                data = response.json()
            except:
                st.error("❌ 下載內容不是有效的 JSON (可能是 HTML 錯誤頁面)")
                st.text(response.text[:500]) # 印出前500字看看到底是什麼
                return None
            
            # 寫入檔案前，先確認這是不是錯誤訊息
            # 如果裡面沒有 cwaopendata，或者有 success: false，可能就是報錯
            if 'cwaopendata' not in data:
                st.warning("⚠️ 警告：伺服器回傳了 JSON，但結構看起來不像天氣資料。")
                
            # 存檔
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return data
        else:
            st.error(f"❌ 下載失敗，HTTP 狀態碼: {response.status_code}")
            st.text(f"錯誤回應: {response.text}")
            return None
    except Exception as e:
        st.error(f"❌ 連線嚴重錯誤: {e}")
        return None

def parse_and_save_to_db(data):
    """解析並存入 SQLite (含詳細除錯訊息)"""
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
        # --- 除錯檢測區 ---
        # 1. 檢查根目錄
        if 'cwaopendata' not in data:
            st.error("❌ 解析失敗：JSON 根目錄找不到 'cwaopendata'")
            st.error("👇 這是伺服器回傳的內容，請檢查是否有 Error Message：")
            st.json(data) # 直接把內容印出來給你看
            return False

        # 2. 檢查 dataset
        if 'dataset' not in data['cwaopendata']:
            st.error("❌ 解析失敗：在 'cwaopendata' 裡面找不到 'dataset'")
            st.error("👇 這通常代表 API Key 有誤或權限不足，伺服器回傳了錯誤報告：")
            st.json(data) # 直接把內容印出來給你看
            return False
        # ----------------

        locations = data['cwaopendata']['dataset']['location']
        insert_list = []
        
        for loc in locations:
            city_name = loc['locationName']
            wx, min_t, max_t = "N/A", "N/A", "N/A"
            
            for elem in loc['weatherElement']:
                elem_name = elem['elementName']
                try:
                    # 嘗試抓取數值
                    if elem['time']:
                        first_val = elem['time'][0]['parameter']['parameterName']
                        if elem_name == 'Wx': wx = first_val
                        elif elem_name == 'MinT': min_t = first_val
                        elif elem_name == 'MaxT': max_t = first_val
                except:
                    continue
            
            insert_list.append((city_name, min_t, max_t, wx))

        if not insert_list:
            st.warning("⚠️ 解析完成，但沒有抓到任何地點資料 (List 是空的)")
            return False

        cursor.executemany("INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)", insert_list)
        conn.commit()
        return True

    except KeyError as e:
        st.error(f"❌ 解析過程中發生 Key 錯誤: {e}")
        st.json(data) # 出錯時印出資料
        if os.path.exists(JSON_FILE):
            os.remove(JSON_FILE) # 刪除壞檔
        return False
    except Exception as e:
        st.error(f"❌ 發生未預期的錯誤: {e}")
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
            # 強制刪除舊檔，確保我們看到的是最新的錯誤訊息
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