import json
import sqlite3
import requests
import os
import sys

# 設定資料庫名稱
DB_NAME = "data.db"
# 設定 JSON 來源 (API 或 本地檔案)
JSON_FILE = "F-A0010-001.json"
API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"

def get_weather_data(api_key=None):
    """
    嘗試讀取本地 JSON，如果沒有則使用 API 下載
    """
    if os.path.exists(JSON_FILE):
        print(f"📄 發現本地檔案 {JSON_FILE}，正在讀取...")
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    elif api_key:
        print("🌐 本地無檔案，正在透過 API 下載...")
        params = {
            "Authorization": api_key,
            "downloadType": "WEB",
            "format": "JSON"
        }
        response = requests.get(API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            # 順便存一份在本地，方便下次使用
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return data
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
            return None
    else:
        print("❌ 找不到本地檔案且未提供 API Key。")
        return None

def parse_and_save_to_db(data):
    """
    解析 JSON 並存入 SQLite
    """
    if not data:
        return

    # 1. 建立資料庫連線
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 2. 建立資料表 (如果已存在則先刪除重蓋，確保資料乾淨)
    cursor.execute("DROP TABLE IF EXISTS weather")
    cursor.execute("""
        CREATE TABLE weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            min_temp TEXT,
            max_temp TEXT,
            description TEXT
        )
    """)

    # 3. 解析 JSON 結構
    # CWA 的結構通常是: cwaopendata -> dataset -> location (List)
    try:
        locations = data['cwaopendata']['dataset']['location']
        
        insert_list = []
        for loc in locations:
            city_name = loc['locationName']
            
            # 預設值
            wx = "N/A" # 天氣現象
            min_t = "N/A" # 最低溫
            max_t = "N/A" # 最高溫

            # 取出天氣元素 (WeatherElement)
            # F-A0010-001 是預報資料，通常包含三個時段，這裡示範取「第一個時段」(最近的預報)
            for elem in loc['weatherElement']:
                elem_name = elem['elementName']
                # 取第一個時段的值
                first_time_slot = elem['time'][0]
                
                if elem_name == 'Wx':
                    wx = first_time_slot['parameter']['parameterName']
                elif elem_name == 'MinT':
                    min_t = first_time_slot['parameter']['parameterName']
                elif elem_name == 'MaxT':
                    max_t = first_time_slot['parameter']['parameterName']
            
            insert_list.append((city_name, min_t, max_t, wx))

        # 4. 批次寫入資料庫
        cursor.executemany("INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)", insert_list)
        conn.commit()
        print(f"✅ 成功寫入 {len(insert_list)} 筆資料到 {DB_NAME}")

    except KeyError as e:
        print(f"❌ JSON 結構解析錯誤: 找不到鍵值 {e}")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        conn.close()

# 為了讓這個檔案可以被 import 也可以直接執行
if __name__ == "__main__":
    # 如果你是直接執行這個檔案，請手動填入 Key 或確保本地有 JSON
    # 這裡示範嘗試從環境變數或直接呼叫
    # 實際運作時，App.py 會傳入 Key，或者依賴本地 JSON
    data = get_weather_data(api_key="CWA-1FFDDAEC-161F-46A3-BE71-93C32C52829F") 
    parse_and_save_to_db(data)