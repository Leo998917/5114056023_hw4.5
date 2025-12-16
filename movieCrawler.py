import requests
from bs4 import BeautifulSoup
import csv
import time
import random

# 設定目標網站基礎網址
BASE_URL = "https://ssr1.scrape.center/page/{}"
# 設定 CSV 檔案名稱
CSV_FILENAME = "movie.csv"

def fetch_page(page_number):
    """
    爬取單一頁面的 HTML
    """
    url = BASE_URL.format(page_number)
    print(f"📥 正在爬取第 {page_number} 頁: {url}")
    
    try:
        # 發送 GET 請求
        # verify=False 是為了防止某些環境下的 SSL 錯誤 (跟 Part 1 一樣)
        response = requests.get(url, verify=False) 
        if response.status_code == 200:
            return response.text
        else:
            print(f"❌ 第 {page_number} 頁爬取失敗，狀態碼: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 連線發生錯誤: {e}")
        return None

def parse_html(html):
    """
    使用 BeautifulSoup 解析 HTML 並提取電影資訊
    """
    soup = BeautifulSoup(html, "html.parser")
    movies = []
    
    # 尋找所有電影卡片 (根據網站結構，通常是 .el-card__body 或 .item)
    # 觀察 ssr1.scrape.center，每個電影都在一個 class="el-card item m-t is-hover-shadow" 裡
    items = soup.find_all(class_="el-card")
    
    for item in items:
        try:
            # 1. 電影名稱 (通常在 h2 標籤)
            title_tag = item.find("h2")
            title = title_tag.text.strip() if title_tag else "N/A"
            
            # 2. 圖片 URL (img 標籤的 src)
            img_tag = item.find("img", class_="cover")
            cover_url = img_tag["src"] if img_tag else "N/A"
            
            # 3. 評分 (class="score")
            score_tag = item.find(class_="score")
            score = score_tag.text.strip() if score_tag else "N/A"
            
            # 4. 類型 (class="categories") -> 裡面有多個 button
            categories_tag = item.find(class_="categories")
            if categories_tag:
                # 找出裡面所有按鈕文字，合併成字串
                cats = [btn.text.strip() for btn in categories_tag.find_all("button")]
                category = ", ".join(cats) # 例如: "劇情, 愛情"
            else:
                category = "N/A"
            
            # 整理成字典
            movie_data = {
                "Title": title,
                "Cover URL": cover_url,
                "Score": score,
                "Category": category
            }
            movies.append(movie_data)
            
        except Exception as e:
            print(f"⚠️ 解析單筆資料時發生錯誤: {e}")
            continue
            
    return movies

def save_to_csv(all_movies):
    """
    將資料寫入 CSV
    """
    if not all_movies:
        print("⚠️ 沒有資料可以寫入 CSV")
        return

    fieldnames = ["Title", "Cover URL", "Score", "Category"]
    
    try:
        with open(CSV_FILENAME, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader() # 寫入標題列
            writer.writerows(all_movies) # 寫入資料
        print(f"✅ 成功儲存 {len(all_movies)} 筆電影資料到 {CSV_FILENAME}！")
    except Exception as e:
        print(f"❌ 寫入 CSV 失敗: {e}")

def main():
    import urllib3
    urllib3.disable_warnings() # 關閉 SSL 警告
    
    all_movies = []
    total_pages = 10 # 題目要求爬 1~10 頁
    
    print("🚀 電影爬蟲啟動...")
    
    for page in range(1, total_pages + 1):
        html = fetch_page(page)
        if html:
            page_movies = parse_html(html)
            all_movies.extend(page_movies)
            print(f"   📄 第 {page} 頁解析完成，抓到 {len(page_movies)} 筆資料")
        
        # 禮貌性暫停，避免對伺服器造成太大負擔 (雖然是練習站，但這是好習慣)
        time.sleep(random.uniform(0.5, 1.5))
        
    print("-" * 30)
    print(f"📊 總共抓取 {len(all_movies)} 筆電影資料")
    save_to_csv(all_movies)

if __name__ == "__main__":
    main()