import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import os
import re
import json
import time
from datetime import datetime
import altair as alt

# --- 1. 頁面與 CSS (V74: 導航回歸 + 標題白字修復) ---
st.set_page_config(layout="wide", page_title="StockTrack V74 完整修復版", page_icon="🛠️")

st.markdown("""
<style>
    /* 1. 全域背景 (淺灰藍) 與深色文字 */
    .stApp {
        background-color: #F4F6F9 !important;
        color: #333333 !important;
        font-family: 'Helvetica', 'Arial', sans-serif;
    }
    
    /* 2. 一般標題與文字強制深色 */
    h1, h2, h3, h4, h5, h6, p, div, span, label, li {
        color: #333333;
    }

    /* 3. 頂部標題區 (深色底，白字) */
    .title-box {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 30px; border-radius: 15px; margin-bottom: 25px; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .title-box h1 { color: #FFFFFF !important; font-size: 40px !important; }
    .title-box p { color: #EEEEEE !important; font-size: 20px !important; }

    /* 4. 數據卡片 */
    div.metric-container {
        background-color: #FFFFFF !important; 
        border-radius: 12px; padding: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E0E0E0; border-top: 6px solid #3498db;
    }
    .metric-value { font-size: 3.5rem !important; font-weight: 800; color: #2c3e50 !important; }
    .metric-label { font-size: 1.6rem !important; color: #555555 !important; font-weight: 700; }

    /* 5. 策略橫幅 (容器) */
    .strategy-banner {
        padding: 15px 25px; border-radius: 8px; 
        margin-top: 35px; margin-bottom: 20px; display: flex; align-items: center;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }
    /* 【修正】策略橫幅內的文字：強制白色 */
    .banner-text {
        color: #FFFFFF !important;
        font-size: 24px !important;
        font-weight: 800 !important;
        margin: 0 !important;
    }
    
    .worker-banner { background: linear-gradient(90deg, #2980b9, #3498db); }
    .boss-banner { background: linear-gradient(90deg, #c0392b, #e74c3c); }
    .revenue-banner { background: linear-gradient(90deg, #d35400, #e67e22); }

    /* 6. 股票標籤 */
    .stock-tag {
        display: inline-block; background-color: #FFFFFF; color: #2c3e50 !important;
        border: 3px solid #bdc3c7; padding: 12px 24px; margin: 10px;
        border-radius: 10px; font-weight: 800; font-size: 1.8rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stock-tag-cb { background-color: #fff8e1; border-color: #f1c40f; color: #d35400 !important; }
    .cb-badge { background-color: #e67e22; color: #FFFFFF !important; font-size: 0.7em; padding: 3px 8px; border-radius: 4px; margin-left: 10px; vertical-align: middle; }
    
    /* 7. 表格優化 */
    .stDataFrame table { text-align: center !important; }
    .stDataFrame th { font-size: 22px !important; color: #000000 !important; background-color: #E6E9EF !important; text-align: center !important; font-weight: 900 !important; }
    .stDataFrame td { font-size: 20px !important; color: #333333 !important; background-color: #FFFFFF !important; text-align: center !important; }

    /* 8. 分頁標籤 */
    button[data-baseweb="tab"] { background-color: #FFFFFF !important; border: 1px solid #ddd !important; }
    button[data-baseweb="tab"] div p { color: #333333 !important; font-size: 20px !important; font-weight: 800 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { background-color: #e3f2fd !important; border-bottom: 4px solid #3498db !important; }
    
    /* 9. 下拉選單 */
    [data-testid="stSelectbox"] label { font-size: 20px !important; color: #333333 !important; font-weight: bold !important; }
    [data-baseweb="select"] div { font-size: 18px !important; color: #333333 !important; background-color: #FFFFFF !important; }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 設定 ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "AIzaSyBWz50Cdsao29vCl49iizswnUE90ywyPpk"

genai.configure(api_key=GOOGLE_API_KEY)
generation_config = {"temperature": 0.0, "response_mime_type": "application/json"}
model = genai.GenerativeModel(model_name="gemini-2.0-flash", generation_config=generation_config)
DB_FILE = 'stock_data_v74.csv'

# --- 3. 核心函數 ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
                return df.sort_values('date', ascending=False)
        except: return pd.DataFrame()
    return pd.DataFrame()

def save_batch_data(records_list):
    df = load_db()
    # 處理輸入型別 (List 或 DataFrame)
    if isinstance(records_list, list):
        new_data = pd.DataFrame(records_list)
    else:
        new_data = records_list

    if not df.empty:
        new_data['date'] = new_data['date'].astype(str)
        df = df[~df['date'].isin(new_data['date'])]
        df = pd.concat([df, new_data], ignore_index=True)
    else: df = new_data
    df = df.sort_values('date', ascending=False)
    df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    return df

def clear_db():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)

# V50 邏輯：最準確的數字錨點
def ai_analyze_v50_grid(image):
    prompt = """
    你是一個精準的表格座標讀取器。請將圖片視為一個 **23 欄位 (Col 1 ~ Col 23)** 的矩陣。
    表格標題列下方有明確的數字編號 (1, 2, 3)，請依此進行絕對定位。
    【欄位定義 (Index 1-23)】
    1. `date` | 2. `wind` | 3. `count1` | 4. `count2` | 5. `count3`
    --- 黃色區塊 ---
    6. `strong_1` (1) | 7. `strong_2` (2) | 8. `strong_3` (3)
    9. `trend_1` (1) | 10. `trend_2` (2) | 11. `trend_3` (3)
    --- 藍色區塊 ---
    12. `pullback_1` (1) | 13. `pullback_2` (2) | 14. `pullback_3` (3)
    15. `bargain_1` (1) | 16. `bargain_2` (2) | 17. `bargain_3` (3)
    --- 灰色區塊 ---
    18. `rev_1` ~ 23. `rev_6`
    【重要校正：12/02 & 12/04】
    - 12/02 週拉回: 只有宜鼎、宇瞻。Col 14 是 null。
    - 12/02 廉價收購: 群聯、高力、宜鼎 (對齊 1,2,3)。
    - 12/04 強勢週: 只有勤凱 (Col 6)。
    - 12/04 週趨勢: 只有雍智科技 (Col 9)。
    【標記】橘色背景請加 `(CB)`。
    請回傳 JSON Array。
    """
    try:
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e: return json.dumps({"error": str(e)})

# --- 4. 統計與繪圖函數 ---
def calculate_monthly_stats(df):
    if df.empty: return pd.DataFrame()
    df['dt'] = pd.to_datetime(df['date'], errors='coerce')
    df['Month'] = df['dt'].dt.strftime('%Y-%m')
    strategies = {
        '🔥 強勢週': 'worker_strong_list', '📈 週趨勢': 'worker_trend_list',
        '↩️ 週拉回': 'boss_pullback_list', '🏷️ 廉價收購': 'boss_bargain_list',
        '💰 營收 TOP6': 'top_revenue_list'
    }
    all_stats = []
    for strategy_name, col_name in strategies.items():
        if col_name not in df.columns: continue
        temp = df[['Month', col_name]].copy()
        temp[col_name] = temp[col_name].astype(str)
        temp = temp[temp[col_name].notna() & (temp[col_name] != 'nan') & (temp[col_name] != '')]
        temp['stock'] = temp[col_name].str.split('、')
        exploded = temp.explode('stock')
        exploded['stock'] = exploded['stock'].str.strip()
        exploded = exploded[exploded['stock'] != '']
        counts = exploded.groupby(['Month', 'stock']).size().reset_index(name='Count')
        counts['Strategy'] = strategy_name
        all_stats.append(counts)
    if not all_stats: return pd.DataFrame()
    final_df = pd.concat(all_stats)
    final_df = final_df.sort_values(['Month', 'Strategy', 'Count'], ascending=[False, True, False])
    return final_df

def render_metric_card(col, label, value, color_border="gray"):
    col.markdown(f"""<div class="metric-container" style="border-top: 5px solid {color_border};"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>""", unsafe_allow_html=True)

def render_stock_tags(stock_str):
    if pd.isna(stock_str) or not stock_str: return "<span style='color:#bdc3c7; font-size:1.2rem; font-weight:600;'>（無標的）</span>"
    html = ""
    stocks = str(stock_str).split('、')
    for s in stocks:
        if not s: continue
        if "(CB)" in s: name = s.replace("(CB)", ""); html += f"<div class='stock-tag stock-tag-cb'>{name}<span class='cb-badge'>CB</span></div>"
        else: html += f"<div class='stock-tag'>{s}</div>"
    return html

# --- 5. 頁面視圖：戰情儀表板 (前台) ---
def show_dashboard():
    df = load_db()
    if df.empty:
        st.info("👋 目前無資料。請至後台新增。")
        return

    all_dates = df['date'].unique()
    st.sidebar.divider(); st.sidebar.header("📅 歷史回顧")
    selected_date = st.sidebar.selectbox("選擇日期", options=all_dates, index=0)
    day_df = df[df['date'] == selected_date]
    if day_df.empty: st.error("日期讀取錯誤"); return
    day_data = day_df.iloc[0]

    st.markdown(f"""<div class="title-box"><h1 style='margin:0; font-size: 2.8rem;'>📅 {selected_date} 市場戰情室</h1><p style='margin-top:10px; opacity:0.9;'>資料更新於: {day_data['last_updated']}</p></div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    wind_status = day_data['wind']; wind_color = "#2ecc71"
    if "強" in str(wind_status): wind_color = "#e74c3c"
    elif "亂" in str(wind_status): wind_color = "#9b59b6"
    elif "陣" in str(wind_status): wind_color = "#f1c40f"
    render_metric_card(c1, "今日風向", wind_status, wind_color)
    render_metric_card(c2, "🪁 打工型風箏", day_data['part_time_count'], "#f39c12")
    render_metric_card(c3, "💪 上班族強勢週", day_data['worker_strong_count'], "#3498db")
    render_metric_card(c4, "📈 上班族週趨勢", day_data['worker_trend_count'], "#9b59b6")

    # 【修正】使用 .banner-text 確保白色
    st.markdown('<div class="strategy-banner worker-banner"><p class="banner-text">👨‍💼 上班族策略 (Worker Strategy)</p></div>', unsafe_allow_html=True)
    w1, w2 = st.columns(2)
    with w1: st.markdown("### 🚀 強勢週 TOP 3"); st.markdown(render_stock_tags(day_data['worker_strong_list']), unsafe_allow_html=True)
    with w2: st.markdown("### 📈 週趨勢"); st.markdown(render_stock_tags(day_data['worker_trend_list']), unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner boss-banner"><p class="banner-text">👑 老闆策略 (Boss Strategy)</p></div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1: st.markdown("### ↩️ 週拉回"); st.markdown(render_stock_tags(day_data['boss_pullback_list']), unsafe_allow_html=True)
    with b2: st.markdown("### 🏷️ 廉價收購"); st.markdown(render_stock_tags(day_data['boss_bargain_list']), unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner revenue-banner"><p class="banner-text">💰 營收創高 (TOP 6)</p></div>', unsafe_allow_html=True)
    st.markdown(render_stock_tags(day_data['top_revenue_list']), unsafe_allow_html=True)

    st.markdown("---")
    st.header("📊 市場數據趨勢分析")
    chart_df = df.copy(); chart_df['date_dt'] = pd.to_datetime(chart_df['date']); chart_df = chart_df.sort_values('date_dt', ascending=True)
    chart_df['Month'] = chart_df['date_dt'].dt.strftime('%Y-%m')

    tab1, tab2, tab3 = st.tabs(["📈 風箏數量", "🌬️ 每日風度分佈", "📅 每月風度統計"])
    
    axis_config = alt.Axis(labelFontSize=16, titleFontSize=20, labelColor='#333333', titleColor='#333333', labelFontWeight='bold', grid=True, gridColor='#E0E0E0')
    legend_config = alt.Legend(orient='top', labelFontSize=16, titleFontSize=20, labelColor='#333333', titleColor='#333333')

    with tab1:
        melted_df = chart_df.melt(id_vars=['date'], value_vars=['part_time_count', 'worker_strong_count', 'worker_trend_count'], var_name='category', value_name='count')
        name_map = {'part_time_count': '打工型風箏', 'worker_strong_count': '上班族強勢週', 'worker_trend_count': '上班族週趨勢'}
        melted_df['category'] = melted_df['category'].map(name_map)
        bar_chart = alt.Chart(melted_df).mark_bar(opacity=0.9).encode(
            x=alt.X('date:O', title='日期', axis=axis_config),
            y=alt.Y('count:Q', title='數量', axis=axis_config),
            color=alt.Color('category:N', title='指標', legend=legend_config),
            xOffset='category:N', tooltip=['date', 'category', 'count']
        ).properties(height=450).configure(background='white').interactive()
        st.altair_chart(bar_chart, use_container_width=True)

    with tab2:
        wind_order = ['強風', '亂流', '陣風', '無風'] 
        wind_chart = alt.Chart(chart_df).mark_circle(size=600, opacity=1).encode(
            x=alt.X('date:O', title='日期', axis=axis_config),
            y=alt.Y('wind:N', title='風度', sort=wind_order, axis=axis_config),
            color=alt.Color('wind:N', title='狀態', legend=legend_config, scale=alt.Scale(domain=['無風', '陣風', '亂流', '強風'], range=['#2ecc71', '#f1c40f', '#9b59b6', '#e74c3c'])),
            tooltip=['date', 'wind']
        ).properties(height=400).configure(background='white').interactive()
        st.altair_chart(wind_chart, use_container_width=True)

    with tab3:
        monthly_wind = chart_df.groupby(['Month', 'wind']).size().reset_index(name='days')
        group_order = ['無風', '陣風', '亂流', '強風']
        grouped_chart = alt.Chart(monthly_wind).mark_bar().encode(
            x=alt.X('Month:O', title='月份', axis=axis_config),
            y=alt.Y('days:Q', title='天數', axis=axis_config),
            color=alt.Color('wind:N', title='風度', sort=group_order, scale=alt.Scale(domain=['無風', '陣風', '亂流', '強風'], range=['#2ecc71', '#f1c40f', '#9b59b6', '#e74c3c']), legend=legend_config),
            xOffset=alt.XOffset('wind:N', sort=group_order),
            tooltip=['Month', 'wind', 'days']
        ).properties(height=450).configure(background='white').interactive()
        st.altair_chart(grouped_chart, use_container_width=True)

    st.markdown("---")
    st.header("🏆 策略選股月度風雲榜")
    st.caption("統計各策略下，股票出現的次數。")
    stats_df = calculate_monthly_stats(df)
    if not stats_df.empty:
        month_list = stats_df['Month'].unique()
        selected_month = st.selectbox("選擇統計月份", options=month_list)
        filtered_stats = stats_df[stats_df['Month'] == selected_month]
        strategies_list = filtered_stats['Strategy'].unique()
        cols1 = st.columns(3); cols2 = st.columns(3)
        for i, strategy in enumerate(strategies_list):
            strat_data = filtered_stats[filtered_stats['Strategy'] == strategy].head(10)
            if i < 3:
                with cols1[i]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count']], hide_index=True, use_container_width=True, 
                                 column_config={"stock": "股票名稱", "Count": st.column_config.ProgressColumn("出現次數", format="%d次", min_value=0, max_value=int(strat_data['Count'].max()) if not strat_data.empty else 1)})
            else:
                with cols2[i-3]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count']], hide_index=True, use_container_width=True,
                                 column_config={"stock": "股票名稱", "Count": st.column_config.ProgressColumn("出現次數", format="%d次", min_value=0, max_value=int(strat_data['Count'].max()) if not strat_data.empty else 1)})
    else: st.info("累積足夠資料後，將在此顯示統計排行。")

# --- 6. 頁面視圖：管理後台 (後台) ---
def show_admin_panel():
    st.title("⚙️ 資料管理後台")
    
    st.subheader("📥 新增/更新資料")
    uploaded_file = st.file_uploader("上傳截圖", type=["png", "jpg", "jpeg"])
    if 'preview_df' not in st.session_state: st.session_state.preview_df = None
    
    if uploaded_file and st.button("開始解析", type="primary"):
        with st.spinner("AI 解析中..."):
            img = Image.open(uploaded_file)
            try:
                json_text = ai_analyze_v50_grid(img)
                if "error" in json_text and len(json_text) < 100: st.error(f"API 錯誤: {json_text}")
                else:
                    raw_data = json.loads(json_text)
                    processed_list = []
                    for item in raw_data:
                        def merge_keys(prefix, count):
                            res = []; seen = set()
                            for i in range(1, count + 1):
                                val = item.get(f"{prefix}_{i}")
                                if val and str(val).lower() != 'null':
                                    val_str = str(val).strip()
                                    if val_str not in seen: res.append(val_str); seen.add(val_str)
                            return "、".join(res)
                        if not item.get("date"): continue
                        record = {
                            "date": str(item.get("date")).replace("/", "-"),
                            "wind": item.get("wind", ""),
                            "part_time_count": item.get("count1", 0),
                            "worker_strong_count": item.get("count2", 0),
                            "worker_trend_count": item.get("count3", 0),
                            "worker_strong_list": merge_keys("strong", 3),
                            "worker_trend_list": merge_keys("trend", 3),
                            "boss_pullback_list": merge_keys("pullback", 3),
                            "boss_bargain_list": merge_keys("bargain", 3),
                            "top_revenue_list": merge_keys("rev", 6),
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        processed_list.append(record)
                    st.session_state.preview_df = pd.DataFrame(processed_list)
            except Exception as e: st.error(f"錯誤: {e}")

    if st.session_state.preview_df is not None:
        st.info("👇 請確認下方資料，可直接點擊修改，無誤後按「存入資料庫」。")
        edited_new = st.data_editor(st.session_state.preview_df, num_rows="dynamic", use_container_width=True)
        if st.button("✅ 存入資料庫"):
            save_batch_data(edited_new)
            st.success("已存檔！")
            st.session_state.preview_df = None
            time.sleep(1)
            st.rerun()

    st.divider()
    st.subheader("📝 歷史資料庫編輯")
    df = load_db()
    if not df.empty:
        st.markdown("在此可修改所有歷史紀錄：")
        edited_history = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 儲存變更"):
            save_batch_data(edited_history)
            st.success("歷史資料已更新！")
            time.sleep(1)
            st.rerun()
        
        if st.button("🗑️ 清空資料庫 (慎用)"):
            clear_db()
            st.warning("已清空")
            st.rerun()

# --- 7. 主導航 ---
def main():
    st.sidebar.title("導航")
    if 'is_admin' not in st.session_state: st.session_state.is_admin = False

    options = ["📊 戰情儀表板"]
    
    # 密碼邏輯
    if not st.session_state.is_admin:
        with st.sidebar.expander("管理員登入"):
            pwd = st.text_input("密碼", type="password")
            if pwd == "8899abc168": 
                st.session_state.is_admin = True
                st.rerun()
    
    if st.session_state.is_admin:
        options.append("⚙️ 資料管理後台")
        if st.sidebar.button("登出"):
            st.session_state.is_admin = False
            st.rerun()

    page = st.sidebar.radio("前往", options)
    
    if page == "📊 戰情儀表板":
        show_dashboard()
    elif page == "⚙️ 資料管理後台":
        show_admin_panel()

if __name__ == "__main__":
    main()
