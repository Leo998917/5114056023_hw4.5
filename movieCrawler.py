import requests
from bs4 import BeautifulSoup
import time
import random

# 設定目標網站基礎網址
BASE_URL = "https://ssr1.scrape.center/page/{}"

def fetch_page(page_number):
    """爬取單一頁面的 HTML"""
    url = BASE_URL.format(page_number)
    print(f"📥 正在爬取第 {page_number} 頁: {url}")
    
    try:
        # verify=False 防止 SSL 錯誤
        response = requests.get(url, verify=False) 
        if response.status_code == 200:
            return response.text
        else:
            return None
    except Exception as e:
        print(f"❌ 連線發生錯誤: {e}")
        return None

def parse_html(html):
    """解析 HTML 並提取電影資訊"""
    soup = BeautifulSoup(html, "html.parser")
    movies = []
    
    items = soup.find_all(class_="el-card")
    
    for item in items:
        try:
            # 1. 電影名稱
            title_tag = item.find("h2")
            title = title_tag.text.strip() if title_tag else "N/A"
            
            # 2. 圖片 URL
            img_tag = item.find("img", class_="cover")
            cover_url = img_tag["src"] if img_tag else "N/A"
            
            # 3. 評分
            score_tag = item.find(class_="score")
            score = score_tag.text.strip() if score_tag else "N/A"
            
            # 4. 類型
            categories_tag = item.find(class_="categories")
            if categories_tag:
                cats = [btn.text.strip() for btn in categories_tag.find_all("button")]
                category = ", ".join(cats)
            else:
                category = "N/A"
            
            movie_data = {
                "Title": title,
                "Cover URL": cover_url,
                "Score": score,
                "Category": category
            }
            movies.append(movie_data)
            
        except Exception as e:
            continue
            
    return movies