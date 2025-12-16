# ... (上面是原本 Part 1 的天氣程式碼) ...

# ==========================================
# Part 2: 電影爬蟲整合區
# ==========================================
import movieCrawler  # 匯入你寫好的爬蟲模組

st.markdown("---")
st.header("🎬 Part 2：電影網站爬蟲")

if st.button("🕷️ 開始爬取電影資料 (10頁)"):
    # 建立一個進度條
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 為了在 Streamlit 顯示進度，我們稍微修改一下呼叫方式
    # 這裡直接呼叫 movieCrawler 的功能
    try:
        import urllib3
        urllib3.disable_warnings()
        
        all_movies = []
        status_text.text("🚀 爬蟲啟動中...")
        
        for page in range(1, 11):
            # 更新進度
            status_text.text(f"📥 正在爬取第 {page}/10 頁...")
            progress_bar.progress(page * 10)
            
            # 呼叫爬蟲函式
            html = movieCrawler.fetch_page(page)
            if html:
                movies = movieCrawler.parse_html(html)
                all_movies.extend(movies)
            
            # 休息一下
            import time
            import random
            time.sleep(random.uniform(0.5, 1))
            
        status_text.success(f"✅ 爬取完成！共抓到 {len(all_movies)} 筆資料")
        
        # 轉成 DataFrame 顯示
        if all_movies:
            df_movie = pd.DataFrame(all_movies)
            st.dataframe(df_movie)
            
            # 製作 CSV 下載按鈕
            csv = df_movie.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下載 movie.csv",
                data=csv,
                file_name='movie.csv',
                mime='text/csv',
            )
            
    except Exception as e:
        st.error(f"爬蟲發生錯誤: {e}")