import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import os
import re
import json
import time
from datetime import datetime, timedelta
import altair as alt
import shutil
import requests
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# 修正 Pydantic 錯誤
try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict

# --- 1. 頁面與 CSS (V158: 年度循環分析版) ---
st.set_page_config(layout="wide", page_title="StockTrack V158", page_icon="💰")

st.markdown("""
<style>
    /* 全域設定 */
    .stApp { background-color: #F0F2F6 !important; color: #333333 !important; font-family: 'Helvetica', 'Arial', sans-serif; }
    h1, h2, h3, h4, h5, h6, p, div, span, label, li { color: #333333; }
    
    /* 標題區 */
    .title-box { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; border-radius: 15px; margin-bottom: 25px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
    .title-box h1 { color: #FFFFFF !important; font-size: 36px !important; margin-bottom: 10px !important; }
    .title-box p { color: #E0E0E0 !important; font-size: 18px !important; }
    
    /* 數據卡片 */
    div.metric-container { background-color: #FFFFFF !important; border-radius: 12px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; border: 1px solid #E0E0E0; border-top: 5px solid #3498db; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 140px; margin-bottom: 10px; }
    .metric-value { font-size: 2.8rem !important; font-weight: 800; color: #2c3e50 !important; margin: 5px 0; }
    .metric-label { font-size: 1.3rem !important; color: #666666 !important; font-weight: 600; }
    .metric-sub { font-size: 1.1rem !important; color: #888888 !important; font-weight: bold; margin-top: 5px; }
    
    /* 全球指數卡片 */
    .market-card { background-color: #FFFFFF; border-radius: 10px; padding: 15px; margin: 5px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.08); border: 1px solid #EAEAEA; transition: transform 0.2s; }
    .market-card:hover { transform: translateY(-3px); box-shadow: 0 4px 8px rgba(0,0,0,0.12); }
    .market-name { font-size: 1.0rem; font-weight: bold; color: #555; margin-bottom: 5px; }
    .market-price { font-size: 1.8rem; font-weight: 900; margin: 5px 0; font-family: 'Roboto', sans-serif; }
    .market-change { font-size: 1.1rem; font-weight: 700; }
    .up-color { color: #e74c3c !important; } .down-color { color: #27ae60 !important; } .flat-color { color: #7f8c8d !important; }
    .card-up { border-bottom: 4px solid #e74c3c; background: linear-gradient(to bottom, #fff, #fff5f5); }
    .card-down { border-bottom: 4px solid #27ae60; background: linear-gradient(to bottom, #fff, #f0fdf4); }
    .card-flat { border-bottom: 4px solid #95a5a6; }
    
    /* 趨勢定義卡片 (V153: 縮小優化版) */
    .trend-card {
        border-radius: 12px; /* 稍微減小圓角 */
        padding: 10px;       /* 減少內距 (原本20px) */
        color: white !important;
        margin: 5px;
        box-shadow: 0 3px 8px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        height: 100%;
        transition: transform 0.2s;
    }
    .trend-card:hover { transform: scale(1.02); }
    .trend-icon { font-size: 2.0rem; margin-bottom: 5px; text-shadow: 0 1px 2px rgba(0,0,0,0.2); } /* 縮小 ICON (3rem -> 2rem) */
    .trend-title { font-size: 1.8rem !important; font-weight: 800 !important; margin-bottom: 5px !important; color: white !important; text-shadow: 0 1px 2px rgba(0,0,0,0.2); }
    .trend-desc { font-size: 1.2rem !important; font-weight: 500 !important; line-height: 1.4; color: rgba(255,255,255,0.95) !important; }
    
    /* 漸層背景 */
    .bg-strong { background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%); } /* 紅色系 */
    .bg-chaos { background: linear-gradient(135deg, #834d9b 0%, #d04ed6 100%); } /* 紫色系 */
    .bg-weak { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }   /* 綠色系 */

    /* 股票標籤 */
    .stock-tag { 
        display: inline-block; background-color: #FFFFFF; color: #2c3e50 !important; 
        border: 2px solid #bdc3c7; padding: 10px 18px; margin: 8px; 
        border-radius: 10px; font-weight: 800; font-size: 1.6rem; 
        box-shadow: 0 3px 6px rgba(0,0,0,0.1); 
        vertical-align: middle;
        text-align: center;
        min-width: 140px;
    }
    .stock-tag-cb { background-color: #fff8e1; border-color: #f1c40f; color: #d35400 !important; }
    .cb-badge { background-color: #e67e22; color: #FFFFFF !important; font-size: 0.6em; padding: 2px 6px; border-radius: 4px; margin-left: 5px; vertical-align: text-top; }
    
    /* 成交值顯示 */
    .turnover-val {
        display: block;
        font-size: 0.8em;
        font-weight: 900;
        color: #d35400; 
        margin-top: 4px;
        padding-top: 4px;
        border-top: 1px dashed #ccc;
        font-family: 'Arial', sans-serif;
    }

    .stDataFrame table { text-align: center !important; }
    .stDataFrame th { font-size: 18px !important; color: #000000 !important; background-color: #E6E9EF !important; text-align: center !important; font-weight: 900 !important; }
    .stDataFrame td { font-size: 18px !important; color: #333333 !important; background-color: #FFFFFF !important; text-align: center !important; }
    
    .strategy-banner { padding: 15px 25px; border-radius: 8px; margin-top: 35px; margin-bottom: 20px; display: flex; align-items: center; box-shadow: 0 3px 6px rgba(0,0,0,0.15); }
    .banner-text { color: #FFFFFF !important; font-size: 24px !important; font-weight: 800 !important; margin: 0 !important; }
    .worker-banner { background: linear-gradient(90deg, #2980b9, #3498db); }
    .boss-banner { background: linear-gradient(90deg, #c0392b, #e74c3c); }
    .revenue-banner { background: linear-gradient(90deg, #d35400, #e67e22); }
    
    /* 下拉選單修正 */
    button[data-baseweb="tab"] { background-color: #FFFFFF !important; border: 1px solid #ddd !important; }
    button[data-baseweb="tab"][aria-selected="true"] { background-color: #e3f2fd !important; border-bottom: 4px solid #3498db !important; }
    .stSelectbox label { font-size: 18px !important; color: #333333 !important; font-weight: bold !important; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: #2c3e50 !important; color: white !important; }
    .stSelectbox div[data-baseweb="select"] > div * { color: #FFFFFF !important; }
    .stSelectbox div[data-baseweb="select"] svg { fill: #FFFFFF !important; color: #FFFFFF !important; }
    li[role="option"] { background-color: #2c3e50 !important; color: #FFFFFF !important; }
    li[role="option"]:hover { background-color: #34495e !important; color: #f1c40f !important; }
    
    /* 恐懼貪婪表格 */
    .fg-history-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #eee; font-size: 14px; }
    .fg-label { color: #666; font-weight: bold; }
    .fg-val-box { padding: 2px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 14px; min-width: 40px; text-align: center; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. 設定 ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    else:
        GOOGLE_API_KEY = "請輸入API KEY" 
except:
    GOOGLE_API_KEY = ""

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class DailyRecord(TypedDict):
    col_01: str; col_02: str; col_03: int; col_04: int; col_05: int
    col_06: str; col_07: str; col_08: str; col_09: str; col_10: str
    col_11: str; col_12: str; col_13: str; col_14: str; col_15: str
    col_16: str; col_17: str; col_18: str; col_19: str; col_20: str
    col_21: str; col_22: str; col_23: str

generation_config = {
    "temperature": 0.0,
    "response_mime_type": "application/json",
    "response_schema": list[DailyRecord],
}

if GOOGLE_API_KEY:
    model_name_to_use = "gemini-2.0-flash"
    model = genai.GenerativeModel(
        model_name=model_name_to_use,
        generation_config=generation_config,
    )

DB_FILE = 'stock_data_v74.csv' 
BACKUP_FILE = 'stock_data_backup.csv'
HISTORY_FILE = 'kite_history.csv' # 新增歷史檔名常數

# --- 3. 核心資料庫 (MASTER_STOCK_DB) ---
MASTER_STOCK_DB = {
    # 修正錯誤與新增
    "1560": ("中砂", "再生晶圓/鑽石碟"), 
    "3551": ("世禾", "半導體設備"), "3715": ("定穎投控", "PCB"),
    "2404": ("漢唐", "無塵室/廠務"), "3402": ("漢科", "廠務設備"),
    "2887": ("台新新光", "金融"), "6830": ("汎銓", "電子上游IC"),
    
    # 權值/熱門 (上市)
    "2330": ("台積電", "晶圓代工"), "2317": ("鴻海", "AI伺服器組裝代工"), "2454": ("聯發科", "IC設計"), 
    "2382": ("廣達", "AI伺服器組裝代工"), "3231": ("緯創", "AI伺服器組裝代工"), "2603": ("長榮", "航運"),
    "3008": ("大立光", "光學鏡頭"), "3037": ("欣興", "ABF載板"), "3034": ("聯詠", "IC設計"),
    "2379": ("瑞昱", "IC設計"), "2303": ("聯電", "晶圓代工"), "2881": ("富邦金", "金融"),
    "2308": ("台達電", "電源/EV"), "1519": ("華城", "重電"), "1513": ("中興電", "重電"),
    "2449": ("京元電子", "封測"), "6290": ("良維", "連接器"), "6781": ("AES-KY", "電池模組"),
    "2427": ("三商電", "系統整合"), "2357": ("華碩", "AI伺服器"), "2356": ("英業達", "AI伺服器"),
    "6669": ("緯穎", "AI伺服器"), "3035": ("智原", "IP矽智財"), "3443": ("創意", "IP矽智財"),
    "3661": ("世芯-KY", "IP矽智財"), "3017": ("奇鋐", "散熱"), "3324": ("雙鴻", "散熱"),
    "2345": ("智邦", "網通"), "3711": ("日月光投控", "封測"), "2368": ("金像電", "PCB"),
    "2383": ("台光電", "CCL銅箔"), "6213": ("聯茂", "CCL銅箔"), "6805": ("富世達", "軸承/散熱"),
    "2353": ("宏碁", "AI PC"), "2324": ("仁寶", "組裝代工"), "2301": ("光寶科", "電源"),
    "2327": ("國巨", "被動元件"), "2344": ("華邦電", "記憶體"), "2408": ("南亞科", "記憶體"),
    "8110": ("華東", "封測"), "1605": ("華新", "電線電纜"), "2609": ("陽明", "航運"),
    "2615": ("萬海", "航運"), "1503": ("士電", "重電"), "1504": ("東元", "重電"),
    "1815": ("富喬", "PCB材料"), "2376": ("技嘉", "板卡/伺服器"), "2377": ("微星", "板卡"),
    "2492": ("華新科", "被動元件"), "3044": ("健鼎", "PCB"), "4958": ("臻鼎-KY", "PCB"),
    "4938": ("和碩", "組裝代工"), "9958": ("世紀鋼", "風電"), "6415": ("矽力-KY", "IC設計"),
    "3406": ("玉晶光", "光學鏡頭"), "2409": ("友達", "面板"), "3481": ("群創", "面板"),
    "6239": ("力成", "封測"), "6770": ("力積電", "晶圓代工"), "2401": ("凌陽", "IC設計"), 
    "3014": ("聯陽", "IC設計"), "6176": ("瑞儀", "背光模組"), "3036": ("文曄", "IC通路"), 
    "2915": ("潤泰全", "百貨/壽險"), "2360": ("致茂", "檢測設備"), "2480": ("敦陽科", "系統整合"), 
    "2359": ("所羅門", "機器人"), "2464": ("盟立", "機器人"), "6664": ("群翊", "PCB設備"),
    "8499": ("鼎炫-KY", "EMI材料"), "6446": ("藥華藥", "生技新藥"), "6139": ("亞翔", "無塵室/廠務"),
    "2059": ("川湖", "伺服器導軌"), "6449": ("鈺邦", "被動元件"), "3706": ("神達", "伺服器"),
    "2312": ("金寶", "組裝代工"), "3413": ("京鼎", "半導體設備"), "8155": ("博智", "PCB/伺服器板"),
    "5388": ("中磊", "網通"), "3217": ("優群", "連接器"), "3090": ("日電貿", "被動元件"),
    "2472": ("立隆電", "被動元件"), "8042": ("金山電", "被動元件"), "2337": ("旺宏", "記憶體"),
    "3357": ("臺慶科", "被動元件"), "6667": ("信紘科", "廠務設備"), "2404": ("漢唐", "無塵室/廠務"),
    "6691": ("洋基工程", "廠務工程"), "1802": ("台玻", "玻璃"), "3529": ("力旺", "IP矽智財"),
    "3105": ("穩懋", "砷化鎵"), "5347": ("世界", "晶圓代工"), "5269": ("祥碩", "IC設計"),
    "2887": ("台新新光", "金融"), "6830": ("汎銓", "電子上游IC"),"7769": ("鴻勁", "半導體設備"),

    
    # 權值/熱門 (上櫃)
    "8299": ("群聯", "記憶體控制"), "8069": ("元太", "電子紙"), "6488": ("環球晶", "矽晶圓"),
    "3293": ("鈊象", "遊戲"), "3131": ("弘塑", "CoWoS設備"), "4966": ("譜瑞-KY", "IC設計"),
    "5274": ("信驊", "IC設計"), "6274": ("台燿", "CCL銅箔"), "3374": ("精材", "封測"), 
    "6147": ("頎邦", "封測"), "5483": ("中美晶", "矽晶圓"), "6223": ("旺矽", "探針卡"),
    "3081": ("聯亞", "光通訊"), "3450": ("聯鈞", "CPO/光通訊"), "4979": ("華星光", "光通訊"),
    "5289": ("宜鼎", "工控記憶體"), "4760": ("勤凱", "被動元件/材料"), "6683": ("雍智科技", "測試介面"),
    "8996": ("高力", "散熱"), "6187": ("萬潤", "CoWoS設備"), "3583": ("辛耘", "CoWoS設備"),
    "6138": ("茂達", "IC設計"), "3680": ("家登", "半導體設備"), "5425": ("台半", "二極體"),
    "3260": ("威剛", "記憶體模組"), "8046": ("南電", "ABF載板"), "4768": ("晶呈科技", "半導體特氣"), 
    "8112": ("至上", "IC通路"), "5314": ("世紀", "IC設計"), "3162": ("精確", "車用零組件"), 
    "3167": ("大量", "半導體設備"), "8021": ("尖點", "PCB鑽針"), "8358": ("金居", "CCL銅箔"), 
    "3163": ("波若威", "光通訊"), "4908": ("前鼎", "光通訊"), "3363": ("上詮", "光通訊"), 
    "4961": ("天鈺", "IC設計"), "6279": ("胡連", "車用連接器"), "3693": ("營邦", "機殼"), 
    "8210": ("勤誠", "機殼"), "3558": ("神準", "網通"), "6180": ("橘子", "遊戲"), 
    "6515": ("穎崴", "測試介面"), "6182": ("合晶", "矽晶圓"), "8086": ("宏捷科", "砷化鎵"), 
    "5284": ("JPP-KY", "航太/機殼"), "6895": ("宏碩系統", "微波設備"), 
    "6739": ("竹陞科技", "智能工廠"), "4971": ("IET-KY", "三五族/砷化鎵"), "9105": ("泰金寶-DR", "組裝代工")
}

# --- 4. 自動生成索引 ---
NAME_TO_SECTOR = {}
NAME_TO_CODE = {}
for code, (name, sector) in MASTER_STOCK_DB.items():
    NAME_TO_SECTOR[name] = sector
    NAME_TO_CODE[name] = code

# 別名對照
ALIAS_MAP = {
    "京元電": "京元電子", "亞翔工程": "亞翔", "聖暉*": "聖暉", "聖暉工程": "聖暉",
    "IET": "IET-KY", "JPP": "JPP-KY", "AES": "AES-KY", "世芯": "世芯-KY",
    "譜瑞": "譜瑞-KY", "力積": "力積電", "台積": "台積電", "聯發": "聯發科",
    "日月光": "日月光投控", "欣 興": "欣興", "群 聯": "群聯", "國巨*": "國巨",
    "藥華": "藥華藥", "聖 暉": "聖暉", "金 居": "金居", "定穎": "定穎投控",
    "漢唐": "漢唐", "漢科": "漢科",
    # 新增別名
    "台新金": "台新新光", "台新新光金": "台新新光", "新光金": "台新新光"
}

# 強制修正表
FORCE_FIX_SECTOR = {
    "京元電子": "封測", "IET-KY": "三五族/砷化鎵", "亞翔": "無塵室/廠務",
    "聖暉": "無塵室/廠務", "聖暉*": "無塵室/廠務", "金寶": "組裝代工",
    "神達": "伺服器", "宏碩系統": "微波設備", "竹陞科技": "智能工廠", "宇瞻": "記憶體模組",
    "群翊": "PCB設備", "鼎炫-KY": "EMI材料", "博智": "PCB/伺服器板", "定穎投控": "PCB",
    "藥華藥": "生技新藥", "川湖": "伺服器導軌", "鈺邦": "被動元件", "金居": "CCL銅箔/材料",
    "世禾": "半導體設備", "漢唐": "無塵室/廠務", "漢科": "廠務設備", "中砂": "再生晶圓/鑽石碟"
}

# --- 智慧查找函式 ---
def smart_get_code_and_sector(stock_input):
    raw = str(stock_input).strip()
    clean = raw.replace("(CB)", "").strip()
    if clean in ALIAS_MAP: clean = ALIAS_MAP[clean]
    clean_no_star = clean.replace("*", "")
    
    code = None
    if clean in NAME_TO_CODE: code = NAME_TO_CODE[clean]
    elif clean_no_star in NAME_TO_CODE: code = NAME_TO_CODE[clean_no_star]
    elif clean.isdigit() and clean in MASTER_STOCK_DB: code = clean
        
    sector = "其他"
    if clean in FORCE_FIX_SECTOR: sector = FORCE_FIX_SECTOR[clean]
    elif code and code in MASTER_STOCK_DB: sector = MASTER_STOCK_DB[code][1]
        
    name = clean
    if code and code in MASTER_STOCK_DB: name = MASTER_STOCK_DB[code][0]
    
    return code, name, sector

def get_stock_sector(identifier):
    _, _, sector = smart_get_code_and_sector(identifier)
    return sector

def smart_get_code(stock_name):
    code, _, _ = smart_get_code_and_sector(stock_name)
    return code

# --- 【V145】預先批次抓取成交值 (終極修復：加入 Fast Info 即時救援) ---
@st.cache_data(ttl=300)
def prefetch_turnover_data(stock_list_str, target_date, manual_override_json=None):
    if not stock_list_str: stock_list_str = []
    unique_names = set()
    for s in stock_list_str:
        if pd.isna(s): continue
        names = [n.strip() for n in str(s).split('、') if n.strip()]
        for name in names:
            unique_names.add(name.replace("(CB)", ""))
            
    result_map = {}
    
    # 1. Manual Override
    if manual_override_json:
        try:
            manual_data = json.loads(manual_override_json)
            if isinstance(manual_data, dict):
                for k, v in manual_data.items():
                    result_map[k] = float(v)
                    code, name, _ = smart_get_code_and_sector(k)
                    if code: result_map[code] = float(v)
                    if name: result_map[name] = float(v)
        except: pass

    # 2. 準備爬蟲名單
    to_fetch_names = [name for name in unique_names if name not in result_map]
    if not to_fetch_names: return result_map

    code_map = {}
    tickers = []
    for name in to_fetch_names:
        code, db_name, _ = smart_get_code_and_sector(name)
        if code:
            code_map[code] = name 
            tickers.append(f"{code}.TW")
            tickers.append(f"{code}.TWO")
            
    if not tickers: return result_map
    
    # 3. 嘗試批次下載 (History)
    try:
        t_date_dt = pd.to_datetime(target_date)
        start_dt = t_date_dt - timedelta(days=5) 
        end_dt = t_date_dt + timedelta(days=2)
        
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        
        # 使用 threads=True 加速
        data = yf.download(tickers, start=start_str, end=end_str, group_by='ticker', progress=False, threads=True)
        
        for code, name in code_map.items():
            found_val = 0
            # A. 先試 History Data
            for suffix in ['.TW', '.TWO']:
                try:
                    ticker = f"{code}{suffix}"
                    if ticker in data.columns.levels[0]:
                        df = data[ticker]
                        if not df.empty:
                            df.index = df.index.tz_localize(None).normalize()
                            target_ts = t_date_dt.normalize()
                            
                            # 優先抓取 target_date
                            if target_ts in df.index:
                                row = df.loc[target_ts]
                            else:
                                # 抓最近的一筆
                                valid_rows = df[df.index <= target_ts]
                                if not valid_rows.empty: row = valid_rows.iloc[-1]
                                else: continue
                                    
                            price = float(row['Close'])
                            vol = float(row['Volume'])
                            if price > 0 and vol > 0:
                                val = (price * vol) / 100000000
                                if val > 0.01:
                                    found_val = val
                                    break
                except: pass
            
            # B. 【關鍵修復】如果 History 抓不到 (found_val=0)，改用 Fast Info (即時數據)
            if found_val == 0:
                for suffix in ['.TW', '.TWO']:
                    try:
                        ticker_obj = yf.Ticker(f"{code}{suffix}")
                        fi = ticker_obj.fast_info
                        # 檢查是否有今日數據
                        last_price = fi.get('last_price', 0)
                        last_vol = fi.get('last_volume', 0)
                        
                        # 簡單檢核：如果價格>0且量>0，就當作是有效的
                        if last_price > 0 and last_vol > 0:
                            val = (last_price * last_vol) / 100000000
                            if val > 0.01:
                                found_val = val
                                break
                    except: pass

            if found_val > 0:
                result_map[name] = found_val
                result_map[code] = found_val
                
        return result_map
    except Exception as e:
        return result_map


# --- 修正後的繪圖函式：加入數據正規化 ---
def plot_sparkline(data_list, color_hex):
    # 1. 基礎防呆：如果資料不足，回傳 None
    if not data_list or len(data_list) < 2:
        return None
    
    # 過濾掉可能的 NaN 值 (yfinance 有時會有空值)
    valid_data = [x for x in data_list if pd.notna(x)]
    if len(valid_data) < 2: return None

    # 2. 計算最大最小值
    min_val = min(valid_data)
    max_val = max(valid_data)
    range_val = max_val - min_val
    
    # 3. 數據正規化 (Normalization) - 關鍵步驟！
    # 將股價縮放到 0.1 ~ 1.0 的區間，讓波動佔滿整個畫布
    # 底部留 0.1 (10%) 的緩衝，避免線條貼底不好看
    if range_val == 0:
        # 如果完全沒波動 (死魚盤)，畫一條中間的線
        normalized_data = [0.5] * len(valid_data)
    else:
        normalized_data = [0.1 + (x - min_val) / range_val * 0.9 for x in valid_data]

    x_data = list(range(len(normalized_data)))
    
    # 4. 顏色處理 (轉為 RGBA 設定透明度)
    hex_color = color_hex.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    fill_color = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.15)" # 背景填色 (淺)
    line_color = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 1.0)"  # 線條顏色 (深)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_data, 
        y=normalized_data, # 使用正規化後的數據
        mode='lines', 
        fill='tozeroy',       
        fillcolor=fill_color, 
        line=dict(color=line_color, width=2.5, shape='spline', smoothing=0.5), # 線條加粗
        hoverinfo='skip' # 隱藏數值 (因為是正規化過的，顯示也沒意義)
    ))
    
    # 5. 極簡化版面設定
    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=5, b=0), # 邊界縮到最小，t=5 留一點頭部空間
        height=50,  # 設定高度
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False, showgrid=False, range=[0, len(valid_data)-1]), 
        yaxis=dict(visible=False, showgrid=False, range=[0, 1.1]), # 固定 Y 軸範圍 0~1.1
        hovermode=False 
    )
    return fig


# --- 1. SVG 繪圖函式 (修正版：增加尺寸限制) ---
def make_sparkline_svg(data_list, color_hex, width=200, height=50):
    if not data_list or len(data_list) < 2: return ""
    
    valid_data = [x for x in data_list if pd.notna(x)]
    if len(valid_data) < 2: return ""
    
    min_val, max_val = min(valid_data), max(valid_data)
    rng = max_val - min_val
    if rng == 0: rng = 1 
    
    points = []
    
    # --- 優化：增加上下邊距，防止線條切邊 ---
    margin_top = 5
    margin_bottom = 12 # 加大底部空間，讓線條完整顯示
    draw_height = height - margin_top - margin_bottom 
    
    step = width / (len(valid_data) - 1)
    
    for i, val in enumerate(valid_data):
        x = i * step
        # 座標計算
        y = height - margin_bottom - ((val - min_val) / rng * draw_height)
        points.append(f"{x:.1f},{y:.1f}")
        
    polyline_points = " ".join(points)
    
    hex_color = color_hex.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    fill_color = f"rgba({r},{g},{b},0.15)"
    stroke_color = f"rgba({r},{g},{b},1)"
    
    # 填色路徑：延伸到最底端
    path_d = f"M {points[0]} L {polyline_points} L {width},{height} L 0,{height} Z"
    
    return f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="width:100%; height:{height}px; display:block; overflow:hidden;"><path d="{path_d}" fill="{fill_color}" stroke="none" /><polyline points="{polyline_points}" fill="none" stroke="{stroke_color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round"/></svg>'


from datetime import datetime
import pytz # 確保有導入時區庫，用於判斷台股日期

# --- 全球市場即時報價 (V168: 櫃買走勢修復 + 台股昨收強制校正版) ---
@st.cache_data(ttl=20)
def get_global_market_data_with_chart():
    try:
        indices = {
            "^TWII": "🇹🇼 加權指數", 
            "^TWOII": "🇹🇼 櫃買指數", 
            "^N225": "🇯🇵 日經225",
            "^DJI": "🇺🇸 道瓊工業", 
            "^IXIC": "🇺🇸 那斯達克", 
            "^SOX": "🇺🇸 費城半導體",
            "BTC-USD": "₿ 比特幣", 
            "ETH-USD": "Ξ 乙太幣"
        }
        market_data = []
        
        # 設定台北時區，確保日期判斷正確
        tz_tw = pytz.timezone('Asia/Taipei')
        
        for ticker_code, name in indices.items():
            try:
                stock = yf.Ticker(ticker_code)
                
                # --- 1. 修復走勢圖 (Trend Fix) ---
                # 預設抓取當日分時 (5分K)
                is_crypto = "-USD" in ticker_code
                interval = "15m" if is_crypto else "5m"
                
                # 嘗試 1: 抓取當日數據
                hist_intra = stock.history(period="1d", interval=interval)
                
                # 嘗試 2 (櫃買指數救援): 如果當日數據全空或太少
                if hist_intra.empty or len(hist_intra) < 5:
                    # 改抓「近 5 日」的「60分K」，確保一定有線條可畫
                    hist_intra = stock.history(period="5d", interval="60m")
                
                # 嘗試 3 (最後防線): 如果還是空，抓日線
                if hist_intra.empty:
                    hist_intra = stock.history(period="1mo", interval="1d")

                # 取出數據
                trend_data = hist_intra['Close'].dropna().tolist()

                # --- 2. 修復漲跌幅 (Price Fix) ---
                # 取得 5 日日線資料，這是計算昨收最準確的來源
                hist_daily = stock.history(period="5d")
                
                last_price = None
                prev_close = None
                
                # A. 先嘗試取得即時報價 (fast_info)
                try:
                    fi = stock.fast_info
                    last_price = fi.last_price
                    prev_close = fi.previous_close
                except: pass
                
                # B. 台股強制校正邏輯 (Taiwan Fix)
                # 針對加權與櫃買，強制檢查日線日期，不完全信任 fast_info 的昨收
                if ticker_code in ["^TWII", "^TWOII"] and not hist_daily.empty:
                    # 取得資料庫中最後一筆的日期
                    last_candle_date = hist_daily.index[-1].date()
                    current_date = datetime.now(tz_tw).date()
                    
                    # 判斷邏輯：
                    # 如果日線最後一筆是「今天」，代表盤中或已收盤 -> 昨收是「倒數第二筆」
                    if last_candle_date == current_date:
                        if len(hist_daily) >= 2:
                            prev_close = float(hist_daily.iloc[-2]['Close'])
                            # 如果 fast_info 沒抓到最新價，就用日線收盤價
                            if last_price is None: 
                                last_price = float(hist_daily.iloc[-1]['Close'])
                    else:
                        # 如果日線最後一筆是「昨天」(尚未更新到今天) -> 昨收就是「最後一筆」
                        prev_close = float(hist_daily.iloc[-1]['Close'])

                # C. 一般防呆 (若上述都失敗)
                if last_price is None and not hist_daily.empty:
                    last_price = float(hist_daily.iloc[-1]['Close'])
                
                # 如果 prev_close 還是空的，嘗試用日線補
                if (prev_close is None or pd.isna(prev_close)) and len(hist_daily) >= 2:
                    prev_close = float(hist_daily.iloc[-2]['Close'])

                # 若真的缺資料，跳過此檔
                if last_price is None or prev_close is None: continue

                # 計算漲跌
                change = last_price - prev_close
                pct_change = (change / prev_close) * 100
                
                # 顏色邏輯 (紅漲綠跌)
                color_hex = "#DC2626" if change > 0 else ("#059669" if change < 0 else "#6B7280")
                
                market_data.append({
                    "name": name, 
                    "price": f"{last_price:,.2f}", 
                    "change": change, 
                    "pct_change": pct_change, 
                    "color_hex": color_hex,
                    "trend": trend_data
                })
            except Exception as e:
                print(f"Error {ticker_code}: {e}")
                continue
        return market_data
    except Exception as e:
        return []	

# --- 恐懼與貪婪指數 (V154: 結構相容修復版) ---
@st.cache_data(ttl=300) 
def get_cnn_fear_greed_full():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.cnn.com/",
        "Origin": "https://www.cnn.com",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache", 
        "Pragma": "no-cache"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            
            # 保留小數點後 1 位
            def safe_num(v): 
                try: return round(float(v), 1)
                except: return 50
                
            def safe_ts(v):
                try: return float(v)
                except: return None
            
            fg_obj = data.get('fear_and_greed', {})
            current_score = safe_num(fg_obj.get('score', 50))
            timestamp = safe_ts(fg_obj.get('timestamp'))
            
            history_data = data.get('fear_and_greed_historical', {}).get('data', [])
            
            # 搜尋歷史數據 helper
            def get_past(days):
                if not history_data: return None, None
                target = (datetime.now() - timedelta(days=days)).timestamp() * 1000
                closest = min(history_data, key=lambda x: abs((float(x['x']) if 'x' in x else 0) - target))
                try: 
                    return round(float(closest['y']), 1), datetime.fromtimestamp(float(closest['x'])/1000).strftime('%Y/%m/%d')
                except: return None, None

            p_sc, p_dt = get_past(1)
            w_sc, w_dt = get_past(7)
            m_sc, m_dt = get_past(30)
            y_sc, y_dt = get_past(365)
            
            date_str = datetime.fromtimestamp(timestamp/1000).strftime('%Y/%m/%d') if timestamp else ""
            
            # V154 Fix: 改回 Dictionary 結構以符合您的 render_global_markets 函式
            return {
                "score": current_score,
                "date": date_str,
                "history": {
                    "prev": {"score": p_sc, "date": p_dt},
                    "week": {"score": w_sc, "date": w_dt},
                    "month": {"score": m_sc, "date": m_dt},
                    "year": {"score": y_sc, "date": y_dt}
                }
            }
        return {"error": f"HTTP {r.status_code}"}
    except Exception as e: return {"error": str(e)}

def get_rating_label_cn(score):
    if score is None: return "未知", "#95a5a6"
    if score < 25: return "極度恐懼", "#e74c3c" # Red
    elif score < 45: return "恐懼", "#e67e22" # Orange
    elif score <= 55: return "中立", "#95a5a6" # Gray
    elif score < 75: return "貪婪", "#2ecc71" # Light Green
    else: return "極度貪婪", "#27ae60" # Dark Green

def plot_fear_greed_gauge(score):
    # 【需求1】字體美化並放大
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        number = {'font': {'size': 60, 'color': '#2c3e50', 'family': 'Impact'}}, # 放大至 80, 使用 Impact 字體
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "市場情緒指標", 'font': {'size': 18, 'color': '#666', 'weight': 'bold'}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#333", 'tickfont': {'size': 14}},
            'bar': {'color': "#2c3e50", 'thickness': 0.15}, # 指針顏色
            'bgcolor': "white",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 25], 'color': "#f6b26b"},   # 極度恐懼 (淡紅)
                {'range': [25, 45], 'color': "#f9cb9c"},  # 恐懼 (橘黃)
                {'range': [45, 55], 'color': "#eeeeee"},  # 中立 (灰)
                {'range': [55, 75], 'color': "#b6d7a8"},  # 貪婪 (淡綠)
                {'range': [75, 100], 'color': "#93c47d"}  # 極度貪婪 (深綠)
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'family': "Arial"})
    return fig

import textwrap # 務必確認有匯入這個標準函式庫

# --- 2. 渲染函式 (防呆修正版：解決縮排導致的黑框問題) ---
def render_global_markets():
    st.markdown("### 🌏 全球指數與加密貨幣 (Real-time Trend)")
    
    markets = get_global_market_data_with_chart()
    
    if not markets:
        st.info("⏳ 市場資料讀取中...")
        st.divider()
        return

    # --- 1. 產生卡片 HTML ---
    cards_list = []
    for m in markets:
        svg_chart = make_sparkline_svg(m['trend'], m['color_hex'], height=50)
        
        if m['change'] > 0:
            arrow = "▲"; color_cls = "color-up"
        elif m['change'] < 0:
            arrow = "▼"; color_cls = "color-down"
        else:
            arrow = "-"; color_cls = "color-flat"
        
        badge = m['name'].split(' ')[0] if ' ' in m['name'] else 'MK'
        clean_name = ' '.join(m['name'].split(' ')[1:]) if ' ' in m['name'] else m['name']
        
        # 單行 HTML
        card_html = f'<div class="market-card-item"><div class="card-content-top"><div class="card-header-flex"><span class="card-title-text">{clean_name}</span><span class="card-badge-box">{badge}</span></div><div class="card-price-flex"><div class="card-price-num">{m["price"]}</div><div class="card-price-chg {color_cls}">{arrow} {abs(m["change"]):.2f} ({abs(m["pct_change"]):.2f}%)</div></div></div><div class="card-chart-bottom">{svg_chart}</div></div>'
        cards_list.append(card_html)

    all_cards_str = "".join(cards_list)

    # --- 2. CSS 樣式 (優化版) ---
    css_styles = """
    <style>
        /* --- 電腦版佈局 (Grid) --- */
        .market-dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 15px;
            width: 100%;
            margin-bottom: 20px;
            padding: 5px; /* 增加一點內距避免陰影被切 */
        }
        
        /* 卡片基礎樣式 */
        .market-card-item {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 140px;
            overflow: hidden;
            flex-shrink: 0; /* 防止在 Flex 模式下被壓縮 */
        }
        
        /* --- 優化 2：手機版佈局 (橫向滑動/Carousel) --- */
        @media (max-width: 768px) {
            .market-dashboard-grid {
                display: flex !important;       /* 改為彈性盒子 */
                overflow-x: auto !important;    /* 開啟水平捲動 */
                grid-template-columns: none !important; /* 取消 Grid */
                flex-wrap: nowrap !important;   /* 禁止換行 */
                gap: 12px;
                padding-bottom: 10px; /* 預留底部空間給滑動條或手指 */
                -webkit-overflow-scrolling: touch; /* iOS 滑動優化 */
                
                /* 隱藏捲軸但保留功能 (針對 Chrome/Safari) */
                scrollbar-width: none; /* Firefox */
                -ms-overflow-style: none;  /* IE 10+ */
            }
            .market-dashboard-grid::-webkit-scrollbar { 
                display: none; /* Chrome/Safari/Webkit */
            }
            
            .market-card-item {
                width: 200px !important;    /* 手機上固定寬度 */
                min-width: 200px !important; 
            }
        }

        /* 文字與排版樣式 (保持不變) */
        .card-content-top { padding: 15px 15px 5px 15px; flex-grow: 1; }
        .card-header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
        .card-title-text { font-size: 0.95rem; font-weight: 700; color: #4B5563; }
        .card-badge-box { font-size: 0.75rem; background: #F3F4F6; padding: 2px 8px; border-radius: 999px; color: #6B7280; }
        .card-price-num { font-size: 1.6rem; font-weight: 800; color: #111827; line-height: 1.1; font-family: sans-serif; }
        .card-price-chg { font-size: 0.85rem; font-weight: 600; margin-top: 2px; }
        .color-up { color: #DC2626 !important; }
        .color-down { color: #059669 !important; }
        .color-flat { color: #6B7280 !important; }
        .card-chart-bottom { height: 50px; width: 100%; margin-bottom: -1px; opacity: 0.95; overflow: hidden; }
    </style>
    """

    final_html = f'<div class="market-dashboard-grid">{all_cards_str}</div>'

    st.markdown(css_styles, unsafe_allow_html=True)
    st.markdown(final_html, unsafe_allow_html=True)
    
    st.divider()

# --- 真實爬蟲排行 ---
@st.cache_data(ttl=60) 
def get_yahoo_realtime_rank(limit=20):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://tw.stock.yahoo.com/"}
        urls = [
            ("https://tw.stock.yahoo.com/rank/turnover?exchange=TAI", "上市"),
            ("https://tw.stock.yahoo.com/rank/turnover?exchange=TWO", "上櫃")
        ]
        all_data = []
        for url, market in urls:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                dfs = pd.read_html(io.StringIO(r.text))
                target_df = None
                for df in dfs:
                    if any("成交值" in str(c) for c in df.columns):
                        target_df = df
                        break
                if target_df is not None:
                    cols = target_df.columns.tolist()
                    name_idx = next((i for i, c in enumerate(cols) if "股" in str(c) and "名" in str(c)), 1)
                    price_idx = next((i for i, c in enumerate(cols) if "價" in str(c)), 2)
                    turnover_idx = next((i for i, c in enumerate(cols) if "值" in str(c) or "金額" in str(c)), 6)
                    change_idx = next((i for i, c in enumerate(cols) if "幅" in str(c)), 4)
                    for idx, row in target_df.iterrows():
                        try:
                            raw_str = str(row.iloc[name_idx])
                            tokens = raw_str.split(' ')
                            code = tokens[0]
                            name = tokens[1] if len(tokens) > 1 else code
                            _, _, sector = smart_get_code_and_sector(name)
                            price = float(re.sub(r"[^\d.]", "", str(row.iloc[price_idx])))
                            turnover = float(re.sub(r"[^\d.]", "", str(row.iloc[turnover_idx])))
                            change_str = str(row.iloc[change_idx])
                            if "▼" in change_str or "-" in change_str: change = -abs(float(re.sub(r"[^\d.]", "", change_str)))
                            else: change = abs(float(re.sub(r"[^\d.]", "", change_str)))
                            if turnover > 0:
                                all_data.append({"代號": code, "名稱": name, "股價": price, "漲跌幅%": change, "成交值(億)": turnover, "市場": market, "族群": sector, "來源": "Yahoo"})
                        except: continue
        if all_data:
            df = pd.DataFrame(all_data)
            df = df.sort_values(by="成交值(億)", ascending=False).reset_index(drop=True)
            df.index = df.index + 1
            df.insert(0, '排名', df.index)
            return df.head(limit)
    except: pass
    
    # 備援：yfinance (V139 保底)
    tickers = [f"{c}.TW" for c in MASTER_STOCK_DB.keys()] + [f"{c}.TWO" for c in MASTER_STOCK_DB.keys()]
    try:
        data = yf.download(tickers, period="1d", group_by='ticker', progress=False, threads=False)
        yf_list = []
        for ticker in tickers:
            try:
                code = re.sub(r"\D", "", ticker)
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker not in data.columns.levels[0]: continue
                    df_stock = data[ticker]
                else:
                    if len(tickers) == 1: df_stock = data
                    else: continue
                
                if df_stock.empty: continue
                latest = df_stock.iloc[-1]
                price = latest['Close']
                volume = latest['Volume']
                if pd.isna(price) or pd.isna(volume) or price <= 0: continue
                turnover = (price * volume) / 100000000
                if turnover < 1: continue 
                op = latest['Open']
                chg = ((price - op)/op)*100 if op > 0 else 0
                _, name, sector = smart_get_code_and_sector(code)
                market = "上櫃" if ".TWO" in ticker else "上市"
                yf_list.append({"代號": code, "名稱": name, "股價": round(float(price),2), "漲跌幅%": round(float(chg),2), "成交值(億)": round(float(turnover),2), "市場": market, "族群": sector, "來源": "YahooFinance"})
            except: continue
        if yf_list:
            df = pd.DataFrame(yf_list)
            df = df.sort_values(by="成交值(億)", ascending=False).reset_index(drop=True)
            df.index = df.index + 1
            df.insert(0, '排名', df.index)
            return df.head(limit)
    except: pass
    return pd.DataFrame()

def plot_market_index(index_type='上市', period='6mo'):
    ticker_map = {'上市': '^TWII', '上櫃': '^TWOII'}
    ticker = ticker_map.get(index_type, '^TWII')
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty: return None, f"無法取得 {index_type} 指數資料"
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=(f'{index_type}指數', '成交量'), row_width=[0.2, 0.8])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='#9C27B0', width=1.5), name='MA5 (週)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='#FFC107', width=1.5), name='MA10 (雙週)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#2196F3', width=1.5), name='MA20 (月)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#4CAF50', width=1.5), name='MA60 (季)'), row=1, col=1)
        colors = ['#ef5350' if row['Open'] - row['Close'] <= 0 else '#26a69a' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
        fig.update_layout(height=600, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='white', plot_bgcolor='#FAFAFA', font=dict(family="Arial, sans-serif", size=12, color='#333333'), legend=dict(orientation="h", yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255, 255, 255, 0.8)", bordercolor="#E0E0E0", borderwidth=1), xaxis_rangeslider_visible=False, hovermode='x unified')
        grid_style = dict(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')
        fig.update_xaxes(**grid_style, row=1, col=1)
        fig.update_yaxes(**grid_style, title='指數', row=1, col=1)
        fig.update_xaxes(**grid_style, row=2, col=1)
        fig.update_yaxes(**grid_style, title='量', row=2, col=1)
        return fig, ""
    except Exception as e: return None, f"繪圖錯誤: {str(e)}"

# --- UI 輔助函數 ---
def render_metric_card(col, label, value, color_border="gray", sub_value=""):
    sub_html = f'<div class="metric-sub">{sub_value}</div>' if sub_value else ""
    col.markdown(f"""
    <div class="metric-container" style="border-top: 5px solid {color_border};">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

# 【需求2】趨勢定義卡片函數 (V153: 微調版)
def render_trend_card(col, title, desc, bg_class, icon):
    col.markdown(f"""
    <div class="trend-card {bg_class}">
        <div class="trend-icon">{icon}</div>
        <div class="trend-title">{title}</div>
        <div class="trend-desc">{desc}</div>
    </div>
    """, unsafe_allow_html=True)

def render_stock_tags_v113(stock_str, turnover_map):
    if pd.isna(stock_str) or not stock_str: return "<span style='color:#bdc3c7; font-size:1.2rem; font-weight:600;'>（無標的）</span>"
    stock_names = [s.strip() for s in str(stock_str).split('、') if s.strip()]
    html = ""
    for s in stock_names:
        clean_s = s.replace("(CB)", "").replace("*", "")
        t_str = ""
        # 1. 查名稱
        if clean_s in turnover_map:
            t_str = f"<span class='turnover-val'>💰 {turnover_map[clean_s]:.1f}億</span>"
        else:
            # 2. 查代碼
            code = smart_get_code(clean_s)
            if code and code in turnover_map:
                 t_str = f"<span class='turnover-val'>💰 {turnover_map[code]:.1f}億</span>"
        
        if "(CB)" in s: html += f"<div class='stock-tag stock-tag-cb'>{clean_s}<span class='cb-badge'>CB</span>{t_str}</div>"
        else: html += f"<div class='stock-tag'>{clean_s}{t_str}</div>"
    return html

def load_db():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
            
            # 處理數字欄位
            numeric_cols = ['part_time_count', 'worker_strong_count', 'worker_trend_count']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            # V150 Fix: 即使 CSV 檔沒有 'manual_turnover' 欄位 (雲端舊檔)，也強制在記憶體中建立
            if 'manual_turnover' not in df.columns:
                df['manual_turnover'] = ""
            
            # V150 Fix: 強制轉型，避免編輯器報錯
            df['manual_turnover'] = df['manual_turnover'].astype(str).replace('nan', '')
                
            if 'date' in df.columns:
                df['date'] = df['date'].astype(str)
                return df.sort_values('date', ascending=False)
        except Exception as e:
            print(f"Load DB Error: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# V158: 新增歷史資料讀取函數
def load_history_data():
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE)
            # 簡單檢查欄位
            if '日期' in df.columns and '風度' in df.columns:
                # 處理日期格式 YYYY.MM.DD
                df['日期'] = pd.to_datetime(df['日期'], format='%Y.%m.%d', errors='coerce')
                df = df.dropna(subset=['日期']).sort_values('日期')
                return df
        except Exception as e:
            print(f"Load History Error: {e}")
    return pd.DataFrame()

def save_batch_data(records_list):
    df = load_db()
    if os.path.exists(DB_FILE):
        try: shutil.copy(DB_FILE, BACKUP_FILE)
        except: pass
    if isinstance(records_list, list): new_data = pd.DataFrame(records_list)
    else: new_data = records_list
    
    if not new_data.empty:
        new_data['date'] = new_data['date'].astype(str)
        # V143: 新資料也要確保有欄位
        if 'manual_turnover' not in new_data.columns:
            new_data['manual_turnover'] = ""
            
        if not df.empty:
            df = df[~df['date'].isin(new_data['date'])]
            df = pd.concat([df, new_data], ignore_index=True)
        else: df = new_data
    df = df.sort_values('date', ascending=False)
    df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    return df

def save_full_history(df_to_save):
    if not df_to_save.empty:
        df_to_save['date'] = df_to_save['date'].astype(str)
        df_to_save = df_to_save.sort_values('date', ascending=False)
        df_to_save.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

def clear_db():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)

def calculate_wind_streak(df, current_date_str):
    if df.empty: return 0
    past_df = df[df['date'] <= current_date_str].copy()
    if past_df.empty: return 0
    past_df = past_df.sort_values('date', ascending=False).reset_index(drop=True)
    def clean_wind(w): return str(w).replace("(CB)", "").strip()
    current_wind = clean_wind(past_df.iloc[0]['wind'])
    streak = 1
    for i in range(1, len(past_df)):
        prev_wind = clean_wind(past_df.iloc[i]['wind'])
        if prev_wind == current_wind: streak += 1
        else: break
    return streak

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
        
        # 【V132】Robust Lookup
        def find_sector(stock_name):
            _, _, sector = smart_get_code_and_sector(stock_name)
            return sector
            
        counts['Industry'] = counts['stock'].apply(find_sector)
        all_stats.append(counts)
        
    if not all_stats: return pd.DataFrame()
    final_df = pd.concat(all_stats)
    final_df = final_df.sort_values(['Month', 'Strategy', 'Count'], ascending=[False, True, False])
    return final_df
    
# --- AI 分析函式 ---
def ai_analyze_v86(image):
    prompt = """
    你是一個精準的表格座標讀取器。請分析圖片中的每一行，回傳 JSON Array。
    【欄位對應表】
    1. `col_01`: 日期
    2. `col_02`: 風度
    3. `col_03`: 打工數
    4. `col_04`: 強勢週數
    5. `col_05`: 週趨勢數
    --- 黃色區塊 ---
    6. `col_06`: 強勢週 Stock 1
    7. `col_07`: 強勢週 Stock 2
    8. `col_08`: 強勢週 Stock 3
    9. `col_09`: 週趨勢 Stock 1
    10. `col_10`: 週趨勢 Stock 2
    11. `col_11`: 週趨勢 Stock 3
    --- 藍色區塊 ---
    12. `col_12`: 週拉回 Stock 1
    13. `col_13`: 週拉回 Stock 2
    14. `col_14`: 週拉回 Stock 3
    15. `col_15`: 廉價收購 Stock 1
    16. `col_16`: 廉價收購 Stock 2
    17. `col_17`: 廉價收購 Stock 3
    --- 灰色區塊 ---
    18. `col_18` ~ 23. `col_23`: 營收創高 Top 6
    【標記】橘色背景請加 (CB)，空白填 null。
    請回傳 JSON Array。
    """
    try:
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e: return json.dumps({"error": str(e)})

# --- 5. 頁面視圖：戰情儀表板 (前台) [含重新整理按鈕版] ---
def show_dashboard():
    df = load_db()
    if df.empty:
        st.info("👋 目前無資料。請至後台新增。")
        return

    st.sidebar.divider(); st.sidebar.header("📅 歷史回顧")
    
    # --- 日期選擇器 ---
    df['dt_temp'] = pd.to_datetime(df['date'], errors='coerce')
    if not df.empty:
        min_d = df['dt_temp'].min().date()
        max_d = df['dt_temp'].max().date()
        default_d = max_d
    else:
        min_d = datetime.now().date()
        max_d = datetime.now().date()
        default_d = datetime.now().date()

    picked_dt = st.sidebar.date_input("選擇日期", value=default_d, min_value=min_d, max_value=max_d)
    selected_date = picked_dt.strftime("%Y-%m-%d")
    
    # --- 資料過濾 ---
    df['compare_date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
    day_df = df[df['compare_date'] == selected_date]

    if day_df.empty: 
        st.error(f"❌ {selected_date} 無資料 (可能是假日或尚未歸檔)，請選擇其他日期。")
        return
    day_data = day_df.iloc[0]

    # --- 預先抓取成交值 ---
    turnover_map = {}
    with st.spinner("正在計算策略選股成交值..."):
        all_strategy_stocks = [
            day_data.get('worker_strong_list', ''),
            day_data.get('worker_trend_list', ''),
            day_data.get('boss_pullback_list', ''),
            day_data.get('boss_bargain_list', ''),
            day_data.get('top_revenue_list', '')
        ]
        manual_json = day_data.get('manual_turnover', None)
        if pd.isna(manual_json): manual_json = None
        turnover_map = prefetch_turnover_data(all_strategy_stocks, selected_date, manual_override_json=manual_json)
    
    # --- [新增] 頂部工具列 (重新整理按鈕) ---
    # 使用 columns 排版，左邊留空，右邊放按鈕
    col_space, col_btn = st.columns([8, 1.2]) 
    
    with col_btn:
        # 定義 callback: 清除快取並重新執行
        def force_refresh():
            get_global_market_data_with_chart.clear() # 清除市場數據快取
            
        # 按鈕：點擊後會觸發 force_refresh 清除快取，Streamlit 會自動 rerun
        st.button("🔄 手動即時更新", on_click=force_refresh, help="強制清除快取並抓取最新報價", type="primary", use_container_width=True)

    # --- 標題區塊 ---
    st.markdown(f"""<div class="title-box"><h1 style='margin:0; font-size: 2.8rem;'>📅 {selected_date} 風箏市場戰情室</h1><p style='margin-top:10px; opacity:0.9;'>資料更新於: {day_data['last_updated']}</p></div>""", unsafe_allow_html=True)

    # --- 下方內容保持不變 ---
    render_global_markets()

    with st.expander("📊 大盤指數走勢圖 (點擊展開)", expanded=False):
        col_m1, col_m2 = st.columns([1, 4])
        with col_m1:
            market_type = st.radio("選擇市場", ["上市", "上櫃"], horizontal=True)
            market_period = st.selectbox("週期", ["1mo", "3mo", "6mo", "1y"], index=2, key="market_period")
        with col_m2:
            fig, err = plot_market_index(market_type, market_period)
            if fig: st.plotly_chart(fig, use_container_width=True)
            else: st.warning(err)
            
    st.divider()

    # ... (以下其餘程式碼保持原樣: 每日風度、策略卡片、圖表分析等) ...
    # 為了節省篇幅，請保留您原本 show_dashboard 函式中，st.divider() 之後的所有程式碼
    # --- 接續原本的程式碼 ---
    
    # --- V196: 每日風度與風箏數 ---
    st.markdown("### 🌬️ 每日風度與風箏數")

    wind_status = day_data['wind']
    wind_streak = calculate_wind_streak(df, selected_date)
    streak_text = f"已持續 {wind_streak} 天"
    
    wind_color = "#2ecc71" 
    if "強" in str(wind_status): wind_color = "#e74c3c"
    elif "亂" in str(wind_status): wind_color = "#9b59b6"
    elif "陣" in str(wind_status): wind_color = "#f1c40f"

    st.markdown("""
    <style>
        div.metrics-grid { display: grid !important; grid-template-columns: repeat(2, 1fr) !important; gap: 15px !important; margin-bottom: 20px !important; width: 100% !important; }
        @media (min-width: 768px) { div.metrics-grid { grid-template-columns: repeat(4, 1fr) !important; } }
        div.metrics-grid .metric-box { background-color: #FFFFFF !important; border-radius: 12px !important; padding: 15px 10px !important; text-align: center !important; border-left: 1px solid #E0E0E0 !important; border-right: 1px solid #E0E0E0 !important; border-bottom: 1px solid #E0E0E0 !important; box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important; display: flex !important; flex-direction: column !important; justify-content: center !important; align-items: center !important; min-height: 120px !important; margin: 0 !important; }
        .m-label { font-size: 1.6rem; color: #666; font-weight: 600; margin-bottom: 5px; }
        .m-value { font-size: 2.5rem; font-weight: 800; color: #2c3e50; margin: 0; line-height: 1.2; }
        .m-sub { font-size: 0.9rem; color: #888; font-weight: bold; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

    html_metrics = '<div class="metrics-grid">'
    html_metrics += f'<div class="metric-box" style="border-top: 5px solid {wind_color} !important;"><div class="m-label">🍃 今日風向</div><div class="m-value">{wind_status}</div><div class="m-sub">{streak_text}</div></div>'
    html_metrics += f'<div class="metric-box" style="border-top: 5px solid #f39c12 !important;"><div class="m-label">🪁 打工型風箏</div><div class="m-value">{day_data["part_time_count"]}</div></div>'
    html_metrics += f'<div class="metric-box" style="border-top: 5px solid #3498db !important;"><div class="m-label">💪 上班族強勢週</div><div class="m-value">{day_data["worker_strong_count"]}</div></div>'
    html_metrics += f'<div class="metric-box" style="border-top: 5px solid #9b59b6 !important;"><div class="m-label">📈 上班族週趨勢</div><div class="m-value">{day_data["worker_trend_count"]}</div></div>'
    html_metrics += '</div>'
    st.markdown(html_metrics, unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner worker-banner"><p class="banner-text">👨‍💼 上班族策略 (Worker Strategy)</p></div>', unsafe_allow_html=True)
    w1, w2 = st.columns(2)
    with w1: st.markdown("### 🚀 強勢週 TOP 3"); st.markdown(render_stock_tags_v113(day_data['worker_strong_list'], turnover_map), unsafe_allow_html=True)
    with w2: st.markdown("### 📈 週趨勢"); st.markdown(render_stock_tags_v113(day_data['worker_trend_list'], turnover_map), unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner boss-banner"><p class="banner-text">👑 老闆策略 (Boss Strategy)</p></div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1: st.markdown("### ↩️ 週拉回"); st.markdown(render_stock_tags_v113(day_data['boss_pullback_list'], turnover_map), unsafe_allow_html=True)
    with b2: st.markdown("### 🏷️ 廉價收購"); st.markdown(render_stock_tags_v113(day_data['boss_bargain_list'], turnover_map), unsafe_allow_html=True)

    st.markdown('<div class="strategy-banner revenue-banner"><p class="banner-text">💰 營收創高 (TOP 6)</p></div>', unsafe_allow_html=True)
    st.markdown(render_stock_tags_v113(day_data['top_revenue_list'], turnover_map), unsafe_allow_html=True)

    st.markdown("---")
    st.header("📊 市場數據趨勢分析")
    chart_df = df.copy(); chart_df['date_dt'] = pd.to_datetime(chart_df['date']); chart_df = chart_df.sort_values('date_dt', ascending=True)
    chart_df['Month'] = chart_df['date_dt'].dt.strftime('%Y-%m')

    tab1, tab2, tab3, tab4 = st.tabs(["📈 每日風箏數量", "🌬️ 每日風度分佈", "🔄 2025 年風度循環回顧",  "📅 每月風度統計"])
    
    common_axis_config = dict(
        showline=True, 
        linewidth=2, 
        linecolor='#333333', 
        gridcolor='#d4d4d4',
        tickfont=dict(size=14, weight='bold', color='#000000'), 
        title_font=dict(size=16, weight='bold', color='#000000') 
    )
    
    axis_config_alt = alt.Axis(labelFontSize=16, titleFontSize=20, labelColor='#000000', titleColor='#000000', labelFontWeight='bold', grid=True, gridColor='#E0E0E0')
    legend_config_alt = alt.Legend(orient='top', labelFontSize=16, titleFontSize=20, labelColor='#000000', titleColor='#000000')

    with tab1:
        fig_line = go.Figure()
        lines_config = [{"col": "part_time_count", "name": "打工型風箏", "color": "#f39c12"}, {"col": "worker_strong_count", "name": "上班族強勢週", "color": "#3498db"}, {"col": "worker_trend_count", "name": "上班族週趨勢", "color": "#9b59b6"}]
        for cfg in lines_config:
            fig_line.add_trace(go.Scatter(x=chart_df['date'], y=chart_df[cfg['col']], name=cfg['name'], mode='lines+markers', line=dict(shape='spline', smoothing=1.3, width=3, color=cfg['color']), marker=dict(size=7, symbol='circle')))
        all_counts = []; 
        for c in ['part_time_count', 'worker_strong_count', 'worker_trend_count']: all_counts.extend(chart_df[c].tolist())
        max_y = max(all_counts) if all_counts else 10; indicator_y = max_y * 1.10
        wind_color_map = {'強風': '#e74c3c', '亂流': '#9b59b6', '陣風': '#f1c40f', '無風': '#2ecc71'}
        wind_colors = [wind_color_map.get(str(w).strip(), '#999') for w in chart_df['wind']]
        wind_texts = [str(w).strip()[0] if str(w).strip() else "?" for w in chart_df['wind']]
        fig_line.add_trace(go.Scatter(x=chart_df['date'], y=[indicator_y]*len(chart_df), mode='markers+text', name='當日風度', text=wind_texts, textposition="top center", textfont=dict(size=13, color='#000000', family='Arial Black', weight='bold'), marker=dict(size=15, color=wind_colors, symbol='circle', line=dict(width=1, color='#333')), hoverinfo='text', hovertext=[f"日期: {d}<br>風度: {w}" for d, w in zip(chart_df['date'], chart_df['wind'])]))
        
        fig_line.update_layout(
            autosize=True, template="plotly_white", height=450, paper_bgcolor='white', plot_bgcolor='white', 
            font=dict(family="Arial, sans-serif", size=14, color='#000000'), 
            xaxis=dict(title="日期", **common_axis_config), 
            yaxis=dict(title="數量", range=[0, max_y * 1.25], **common_axis_config), 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=14, color='#000000', weight='bold')), 
            margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified"
        )
        st.plotly_chart(fig_line, use_container_width=True)
    
    with tab2:
        st.markdown("#### 🌬️ 市場觀察趨勢定義")
        st.markdown("""<style>div.trend-scroll-box { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; overflow-x: auto !important; gap: 10px !important; padding: 5px 2px 10px 2px !important; width: 100% !important; -webkit-overflow-scrolling: touch; align-items: stretch !important; } div.trend-scroll-box .t-card { flex: 0 0 auto !important; width: 160px !important; min-width: 160px !important; border-radius: 10px !important; padding: 10px 8px !important; color: #FFFFFF !important; box-shadow: 0 3px 6px rgba(0,0,0,0.1) !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; text-align: center !important; margin: 0 !important; border: 1px solid rgba(255,255,255,0.2) !important; } @media (min-width: 768px) { div.trend-scroll-box { overflow-x: hidden !important; justify-content: space-between !important; } div.trend-scroll-box .t-card { flex: 1 1 0px !important; width: auto !important; min-width: 0 !important; } } .t-icon { font-size: 2.0rem !important; margin-bottom: 5px !important; text-shadow: 0 1px 2px rgba(0,0,0,0.1); } .t-title { font-size: 1.3rem !important; font-weight: 800 !important; margin-bottom: 5px !important; color: #FFFFFF !important; text-shadow: 0 1px 2px rgba(0,0,0,0.1); line-height: 1.2 !important; } .t-desc { font-size: 1.0rem !important; font-weight: 500 !important; line-height: 1.4 !important; color: rgba(255,255,255,0.95) !important; } .bg-strong-v199 { background: linear-gradient(135deg, #FF8A80 0%, #E57373 100%) !important; } .bg-chaos-v199 { background: linear-gradient(135deg, #BA68C8 0%, #9575CD 100%) !important; } .bg-weak-v199 { background: linear-gradient(135deg, #81C784 0%, #4DB6AC 100%) !important; } div.trend-scroll-box::-webkit-scrollbar { height: 4px; } div.trend-scroll-box::-webkit-scrollbar-thumb { background-color: #ccc; border-radius: 4px; }</style>""", unsafe_allow_html=True)
        t_html = '<div class="trend-scroll-box"><div class="t-card bg-strong-v199"><div class="t-icon">🔥</div><div class="t-title">強風/亂流循環</div><div class="t-desc">易漲行情<br>股價走勢有延續性<br>(打工/上班型)</div></div><div class="t-card bg-chaos-v199"><div class="t-icon">🌪️</div><div class="t-title">循環的交界</div><div class="t-desc">待觀察<br>行情無明確方向<br>(等方向出來再積極)</div></div><div class="t-card bg-weak-v199"><div class="t-icon">🍃</div><div class="t-title">陣風/無風循環</div><div class="t-desc">易跌行情<br>股價走勢難延續<br>(老闆/成長型)</div></div></div>'
        st.markdown(t_html, unsafe_allow_html=True)
        wind_order = ['強風', '亂流', '陣風', '無風'] 
        wind_chart = alt.Chart(chart_df).mark_circle(size=350, opacity=0.9).encode(x=alt.X('date:O', title='日期', axis=axis_config_alt), y=alt.Y('wind:N', title='風度', sort=wind_order, axis=axis_config_alt), color=alt.Color('wind:N', title='狀態', legend=legend_config_alt, scale=alt.Scale(domain=['無風', '陣風', '亂流', '強風'], range=['#2ecc71', '#f1c40f', '#9b59b6', '#e74c3c'])), tooltip=['date', 'wind']).properties(height=450, width='container').configure(background='white').interactive()
        st.altair_chart(wind_chart, use_container_width=True)
        
    with tab4:
        monthly_wind = chart_df.groupby(['Month', 'wind']).size().reset_index(name='count')
        color_map = {'無風': '#2ecc71', '陣風': '#f1c40f', '亂流': '#9b59b6', '強風': '#e74c3c'}
        wind_types = ['無風', '陣風', '亂流', '強風']
        fig = go.Figure()
        for w_type in wind_types:
            sub_df = monthly_wind[monthly_wind['wind'] == w_type]
            if not sub_df.empty: fig.add_trace(go.Bar(x=sub_df['Month'], y=sub_df['count'], name=w_type, marker_color=color_map.get(w_type, '#333'), marker_line_width=1.5, marker_line_color='rgba(0,0,0,0.2)', opacity=0.9))
        
        fig.update_layout(
            autosize=True, template="plotly_white", barmode='group', height=450, paper_bgcolor='white', plot_bgcolor='white', 
            font=dict(family="Arial, sans-serif", size=14, color='#000000'), 
            xaxis=dict(title="月份", type='category', **common_axis_config), 
            yaxis=dict(title="天數", **common_axis_config), 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=14, color='#000000', weight='bold')), 
            margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        c_title, c_ctrl = st.columns([3, 1])
        with c_title: 
            st.markdown("#### 🔄 2025 年度風度循環分析 (Wind Cycle Analysis)")
        with c_ctrl: 
            leverage = st.number_input("⚖️ 操作槓桿倍數", min_value=0.1, max_value=10.0, value=1.0, step=0.1, help="例如：操作正2 ETF 請設 2.0；操作個股可設 1.0 或其 Beta 值。")
        
        hist_df = load_history_data()
        if not hist_df.empty:
            hist_df['日期'] = pd.to_datetime(hist_df['日期'], format='mixed', errors='coerce')
            hist_df = hist_df.sort_values('日期', ascending=True).reset_index(drop=True)
            
            min_date = hist_df['日期'].iloc[0]
            max_date = hist_df['日期'].iloc[-1] 

            hist_df['wind_clean'] = hist_df['風度'].fillna('').astype(str).str.strip()

            col_20ma = next((c for c in hist_df.columns if '20ma' in c.lower().replace(' ', '')), None)
            hist_df['MA20'] = pd.to_numeric(hist_df[col_20ma], errors='coerce') if col_20ma else hist_df['收'].rolling(window=20, min_periods=1).mean()
            
            target_col = next((c for c in hist_df.columns if '行情' in c or '方向' in c), None)
            
            if target_col:
                hist_df[target_col] = hist_df[target_col].astype(str).str.strip()
                def get_cycle_v179(val):
                    if '強風' in val and '亂流' in val: return 'active'
                    if '無風' in val and '陣風' in val: return 'passive'
                    return 'transition'
                hist_df['cycle'] = hist_df[target_col].apply(get_cycle_v179)
            else:
                hist_df['cycle'] = hist_df['wind_clean'].apply(
                    lambda w: 'active' if ('強風' in w or '亂流' in w) and not ('無風' in w or '陣風' in w) else 
                             ('passive' if ('無風' in w or '陣風' in w) and not ('強風' in w or '亂流' in w) else 'transition')
                )

            d_act = len(hist_df[hist_df['cycle'] == 'active'])
            d_pass = len(hist_df[hist_df['cycle'] == 'passive'])
            d_tran = len(hist_df[hist_df['cycle'] == 'transition'])
            total_days = len(hist_df)
            
            p_act = (d_act / total_days * 100) if total_days > 0 else 0
            p_pass = (d_pass / total_days * 100) if total_days > 0 else 0
            p_tran = (d_tran / total_days * 100) if total_days > 0 else 0

            cnt_strong = hist_df['wind_clean'].str.contains('強風').sum()
            cnt_chaos = hist_df['wind_clean'].str.contains('亂流').sum()
            cnt_calm = hist_df['wind_clean'].str.contains('無風').sum()
            cnt_gust = hist_df['wind_clean'].str.contains('陣風').sum()

            zones = []
            cycle_stats = {'active': {'return': []}, 'passive': {'return': []}, 'transition': {'return': []}}
            
            curr_start = hist_df.iloc[0]['日期']; curr_price = hist_df.iloc[0]['收']; curr_cycle = hist_df.iloc[0]['cycle']
            for i in range(1, len(hist_df)):
                row = hist_df.iloc[i]
                if row['cycle'] != curr_cycle:
                    end_date = row['日期']; end_price = hist_df.iloc[i-1]['收']
                    ret = ((end_price - curr_price) / curr_price * 100) if curr_price > 0 else 0
                    zones.append({'start': curr_start, 'end': end_date, 'type': curr_cycle})
                    if curr_cycle in cycle_stats: cycle_stats[curr_cycle]['return'].append(ret)
                    curr_start = row['日期']; curr_price = row['收']; curr_cycle = row['cycle']
            
            last_end = hist_df.iloc[-1]['日期'] + pd.Timedelta(days=1); last_price = hist_df.iloc[-1]['收']
            last_ret = ((last_price - curr_price) / curr_price * 100) if curr_price > 0 else 0
            zones.append({'start': curr_start, 'end': last_end, 'type': curr_cycle})
            if curr_cycle in cycle_stats: cycle_stats[curr_cycle]['return'].append(last_ret)

            def avg_leveraged(l): base_avg = sum(l)/len(l) if l else 0; return base_avg * leverage
            r_act = avg_leveraged(cycle_stats['active']['return'])
            r_pass = avg_leveraged(cycle_stats['passive']['return'])
            r_tran = avg_leveraged(cycle_stats['transition']['return'])
            
            c_act_val = '#e74c3c' if r_act > 0 else '#27ae60'; c_pass_val = '#e74c3c' if r_pass > 0 else '#27ae60'; c_tran_val = '#e74c3c' if r_tran > 0 else ('#27ae60' if r_tran < 0 else '#95a5a6')
            
            st.markdown("""<style>.dashboard-grid-v183 { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin-bottom: 25px; } @media (max-width: 768px) { .dashboard-grid-v183 { grid-template-columns: 1fr 1fr; } } .m-card { background: #fff; border-radius: 12px; padding: 15px 5px; text-align: center; border: 1px solid #f0f0f0; box-shadow: 0 2px 5px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: center; height: 100%; } .bd-red { border-top: 4px solid #e74c3c; } .bd-yellow { border-top: 4px solid #f1c40f; } .bd-green { border-top: 4px solid #2ecc71; } .mc-lbl { font-size: 18px; font-weight: bold; color: #555; margin-bottom: 5px; } .mc-val { font-size: 22px; font-weight: 800; color: #2c3e50; margin: 2px 0; font-family: Arial, sans-serif; } .mc-sub { font-size: 12px; color: #888; margin-top: 2px; } .p-bg { width: 100%; height: 4px; background: #f1f2f6; border-radius: 2px; margin-top: 8px; overflow: hidden; margin-left: auto; margin-right: auto; } .p-fill { height: 100%; border-radius: 2px; }</style>""", unsafe_allow_html=True)
            
            def make_card_html(border_class, title, value_html, sub_text, bar_color=None, bar_pct=0):
                bar_html = f'<div class="p-bg"><div class="p-fill" style="width:{bar_pct}%; background:{bar_color};"></div></div>' if bar_color else ""
                return f"""<div class="m-card {border_class}"><div class="mc-lbl">{title}</div><div class="mc-val">{value_html}</div><div class="mc-sub">{sub_text}</div>{bar_html}</div>"""
            
            sub_text_suffix = f" (x{leverage})" if leverage != 1.0 else ""
            
            val_act = f"{d_act} <span style='font-size:16px; color:#999'>({cnt_strong}/{cnt_chaos})</span> <span style='font-size:12px'>天</span>"
            c1 = make_card_html("bd-red", "🔴 強風/亂流循環", val_act, f"佔比 {p_act:.0f}%", "#e74c3c", p_act)
            c2 = make_card_html("bd-red", "🚀 積極績效", f"<span style='color:{c_act_val}'>{r_act:+.2f}%</span>", f"預估報酬{sub_text_suffix}")
            
            val_tran = f"{d_tran} <span style='font-size:12px'>天</span>"
            c3 = make_card_html("bd-yellow", "🟡 循環交界", val_tran, f"佔比 {p_tran:.0f}%", "#f1c40f", p_tran)
            c4 = make_card_html("bd-yellow", "⚖️ 無方向績效", f"<span style='color:{c_tran_val}'>{r_tran:+.2f}%</span>", f"預估波動{sub_text_suffix}")
            
            val_pass = f"{d_pass} <span style='font-size:16px; color:#999'>({cnt_calm}/{cnt_gust})</span> <span style='font-size:12px'>天</span>"
            c5 = make_card_html("bd-green", "🟢 無風/陣風循環", val_pass, f"佔比 {p_pass:.0f}%", "#2ecc71", p_pass)
            c6 = make_card_html("bd-green", "🛡️ 保守績效", f"<span style='color:{c_pass_val}'>{r_pass:+.2f}%</span>", f"預估損益{sub_text_suffix}")
            
            st.markdown(f'<div class="dashboard-grid-v183">{c1}{c2}{c3}{c4}{c5}{c6}</div>', unsafe_allow_html=True)
            
            st.caption("🌈 線上的顏色代表當日的風度：🔴強風 🟣亂流 🟡陣風 🟢無風 ____實線為 上櫃指數 ----虛線為 20MA (月線)。")
            
            wind_colors_map = {'強風': '#e74c3c', '亂流': '#9b59b6', '陣風': '#f1c40f', '無風': '#2ecc71'}
            point_colors = [wind_colors_map.get(str(w).strip(), '#999') for w in hist_df['wind_clean']]
            
            fig = go.Figure()
            color_map_cycle = {'active': 'rgba(231, 76, 60, 0.15)', 'passive': 'rgba(46, 204, 113, 0.15)', 'transition': 'rgba(150, 150, 150, 0.2)'}
            shapes = []
            for z in zones: 
                shapes.append(dict(
                    type="rect", 
                    xref="x", yref="paper", 
                    x0=z['start'], x1=z['end'], 
                    y0=0, y1=1, 
                    fillcolor=color_map_cycle.get(z['type'], '#eee'), 
                    opacity=1, layer="below", line_width=0
                ))
            
            if '收' in hist_df.columns: 
                fig.add_trace(go.Scatter(x=hist_df['日期'], y=hist_df['收'], mode='lines', name='上櫃指數', line=dict(color='#34495e', width=1.5, shape='spline', smoothing=1.3)))
            
            if 'MA20' in hist_df.columns: 
                fig.add_trace(go.Scatter(x=hist_df['日期'], y=hist_df['MA20'], mode='lines', name='20MA', line=dict(color='#9b59b6', width=2, dash='dash', shape='spline', smoothing=1.3)))
            
            fig.add_trace(go.Scatter(x=hist_df['日期'], y=hist_df['收'], mode='markers', name='每日風度', marker=dict(color=point_colors, size=8.5, line=dict(width=1, color='white'), symbol='circle'), hoverinfo='skip'))

            hover_text = []
            for idx, row in hist_df.iterrows():
                raw_dir = row['wind_clean']
                cycle_zh = {"active":"積極", "passive":"保守", "transition":"無方向"}.get(row['cycle'], "-")
                hover_text.append(f"<b>{row['日期'].strftime('%Y-%m-%d')}</b><br>收: {row['收']:,.0f}<br>向: {raw_dir}<br>態: {cycle_zh}")
            fig.add_trace(go.Scatter(x=hist_df['日期'], y=hist_df['收'], mode='markers', name='資訊', marker=dict(size=0, opacity=0), hoverinfo='text', hovertext=hover_text))
            
            fig.update_layout(
                title=dict(text="📊 市場循環趨勢圖", font=dict(size=20, color='#000000', weight='bold'), x=0.01, y=0.98), 
                shapes=shapes, 
                template="plotly_white", paper_bgcolor='white', plot_bgcolor='white', height=500, 
                font=dict(family="Arial, sans-serif", color='#000000', size=12), 
                xaxis=dict(
                    type="date", 
                    range=[min_date, max_date],
                    rangeslider=dict(visible=True, thickness=0.05, bgcolor='#f8f9fa', borderwidth=0), 
                    rangeselector=dict(buttons=list([dict(count=1, label="1M", step="month", stepmode="backward"), dict(count=3, label="3M", step="month", stepmode="backward"), dict(count=6, label="6M", step="month", stepmode="backward"), dict(step="all", label="All")]), bgcolor="#ecf0f1", activecolor="#3498db", font=dict(color="#2c3e50"), x=0, y=1.05),
                    **common_axis_config
                ), 
                yaxis=dict(title="", zeroline=False, **common_axis_config),
                margin=dict(t=80, l=0, r=0, b=40), 
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", y=1.02, 
                    xanchor="right", x=1, 
                    bgcolor='rgba(255,255,255,0.8)', 
                    bordercolor='#eee', 
                    borderwidth=1, 
                    font=dict(size=12, color='#000000', weight='bold')
                ), 
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        else: st.warning("⚠️ 無資料，請確認 CSV 是否已上傳。")

    st.markdown("---")

    st.header("🏆 策略選股月度風雲榜")
    st.caption("統計各策略下，股票出現的次數與所屬族群。")
    stats_df = calculate_monthly_stats(df)
    if not stats_df.empty:
        month_list = stats_df['Month'].unique()
        selected_month = st.selectbox("選擇統計月份", options=month_list)
        filtered_stats = stats_df[stats_df['Month'] == selected_month]
        strategies_list = filtered_stats['Strategy'].unique()
        cols1 = st.columns(3); cols2 = st.columns(3)
        for i, strategy in enumerate(strategies_list):
            strat_data = filtered_stats[filtered_stats['Strategy'] == strategy].head(10)
            col_config = {"stock": "股票名稱", "Count": st.column_config.ProgressColumn("出現次數", format="%d次", min_value=0, max_value=int(strat_data['Count'].max()) if not strat_data.empty else 1), "Industry": st.column_config.TextColumn("族群", help="所屬產業類別")}
            if i < 3:
                with cols1[i]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count', 'Industry']], hide_index=True, use_container_width=True, column_config=col_config)
            else:
                with cols2[i-3]:
                    st.subheader(f"{strategy}")
                    st.dataframe(strat_data[['stock', 'Count', 'Industry']], hide_index=True, use_container_width=True, column_config=col_config)
    else: st.info("累積足夠資料後，將在此顯示統計排行。")

    st.markdown("---")
    st.header("🔥 今日市場重點監控 (權值股/熱門股 成交值排行)")
    st.caption("資料來源：Yahoo 股市 (即時爬蟲) / Yahoo Finance (備援) | 單位：億元")
    
    with st.spinner("正在計算最新成交資料..."):
        rank_df = get_yahoo_realtime_rank(20)
        
        if isinstance(rank_df, pd.DataFrame) and not rank_df.empty:
            max_turnover = rank_df['成交值(億)'].max()
            safe_max = int(max_turnover) if max_turnover > 0 else 1
            st.dataframe(rank_df, hide_index=True, use_container_width=True, column_config={"排名": st.column_config.NumberColumn("#", width="small"), "代號": st.column_config.TextColumn("代號"), "名稱": st.column_config.TextColumn("名稱", width="medium"), "股價": st.column_config.NumberColumn("股價", format="$%.2f"), "漲跌幅%": st.column_config.NumberColumn("漲跌幅", format="%.2f%%", help="日漲跌幅估算"), "成交值(億)": st.column_config.ProgressColumn("成交值 (億)", format="$%.2f億", min_value=0, max_value=safe_max), "市場": st.column_config.TextColumn("市場", width="small"), "族群": st.column_config.TextColumn("族群"), "來源": st.column_config.TextColumn("來源", width="small")})
        else: 
            st.warning("⚠️ 無法取得即時排行，顯示歷史數據")

    st.markdown("---")
    
    with st.expander("🔗 常用連結與好朋友推薦 (Useful Links)", expanded=True):
        col_l1, col_l2, col_l3 = st.columns(3)
        
        with col_l1:
            st.markdown("#### 🛠️ 市場工具")
            st.markdown('<a href="https://tw.stock.yahoo.com/" target="_blank" class="link-btn">Yahoo! 股市</a>', unsafe_allow_html=True)
            st.markdown('<a href="https://www.wantgoo.com/" target="_blank" class="link-btn">玩股網</a>', unsafe_allow_html=True)
            st.markdown('<a href="https://goodinfo.tw/tw/index.asp" target="_blank" class="link-btn">Goodinfo! 台灣股市資訊網</a>', unsafe_allow_html=True)

        with col_l2:
            st.markdown("#### 📰 新聞與資訊")
            st.markdown('<a href="https://news.cnyes.com/" target="_blank" class="link-btn">鉅亨網</a>', unsafe_allow_html=True)
            st.markdown('<a href="https://ctee.com.tw/" target="_blank" class="link-btn">工商時報</a>', unsafe_allow_html=True)
            st.markdown('<a href="https://money.udn.com/money/index" target="_blank" class="link-btn">經濟日報</a>', unsafe_allow_html=True)

        with col_l3:
            st.markdown("#### 🤝 好朋友推薦")
            st.markdown('<a href="https://www.instagram.com/alpha_kitev/" target="_blank" class="link-btn">👍強推 不魯放風箏選股IG</a>', unsafe_allow_html=True)
            st.markdown('<a href="https://birdbrainfood-windofkite.streamlit.app" target="_blank" class="link-btn">鴿子-不魯放風箏的風度圖</a>', unsafe_allow_html=True)
            st.markdown('<a href="https://service-82255878134.us-west1.run.app/"  target="_blank" class="link-btn">Ding-風箏策略儀表板</a>', unsafe_allow_html=True)

# --- 6. 頁面視圖：管理後台 (後台) ---
def show_admin_panel():
    st.title("⚙️ 資料管理後台")
    if not GOOGLE_API_KEY: st.error("❌ 未設定 API Key"); return
    
    # ... (上傳 CSV 的程式碼保持不變，略過以節省篇幅，請保留原有的上傳功能) ...
    # 這裡插入你的 CSV 上傳程式碼 (history_uploader) ...
    # ----------------------------------------------------
    st.subheader("📥 上傳年度風度歷史檔 (CSV)")
    history_file = st.file_uploader("上傳 kite_history.csv", type=["csv"], key="history_uploader")
    
    if history_file is not None:
        # (保留原本的讀取與儲存邏輯)
        try:
            history_file.seek(0)
            file_bytes = history_file.read()
            success = False
            for enc in ['utf-8-sig', 'utf-8', 'big5', 'cp950']:
                try:
                    temp_df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
                    temp_df.columns = temp_df.columns.str.strip()
                    if '日期' in temp_df.columns and '風度' in temp_df.columns:
                        temp_df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
                        st.success(f"✅ 歷史檔案已更新！(編碼: {enc}, {len(temp_df)} 筆資料)")
                        success = True
                        break
                except: continue
            if not success: st.error("❌ 檔案讀取失敗")
        except Exception as e: st.error(f"❌ 嚴重錯誤: {e}")

    # --- V164 新增：後台專屬的詳細循環清單 (Debug) ---
    if os.path.exists(HISTORY_FILE):
        st.markdown("---")
        st.subheader("🕵️‍♂️ 系統診斷 (Debug Info)")
        try:
            current_df = load_history_data() # 使用共用的讀取函式
            
            tab_debug1, tab_debug2 = st.tabs(["📋 原始數據預覽", "🔄 循環判斷測試"])
            
            with tab_debug1:
                st.write(f"目前檔案路徑: `{os.path.abspath(HISTORY_FILE)}`")
                st.dataframe(current_df, use_container_width=True, height=300)
            
            with tab_debug2:
                # 在後台重現循環計算，供管理員檢查
                st.markdown("**循環邏輯驗證：**")
                debug_df = current_df.copy()
                
                # 重複一次邏輯以便顯示
                def get_debug_cycle(wind):
                    w = str(wind).strip()
                    if w in ['強風', '亂流']: return '🔴 積極'
                    if w in ['陣風', '無風']: return '🟢 保守'
                    return '🟡 交界'
                
                debug_df['系統判定循環'] = debug_df['風度'].apply(get_debug_cycle)
                st.dataframe(debug_df[['日期', '風度', '系統判定循環', '收']], use_container_width=True)

        except Exception as e:
            st.error(f"無法讀取現有檔案: {e}")

    st.divider()
    # ----------------------------------------------------

    st.subheader("📥 新增/更新資料 (每日截圖)")
    uploaded_file = st.file_uploader("上傳截圖", type=["png", "jpg", "jpeg"])
    if 'preview_df' not in st.session_state: st.session_state.preview_df = None
    
    if uploaded_file and st.button("開始解析", type="primary"):
        with st.spinner("AI 解析中..."):
            img = Image.open(uploaded_file)
            try:
                json_text = ai_analyze_v86(img)
                if "error" in json_text and len(json_text) < 100: st.error(f"API 錯誤: {json_text}")
                else:
                    raw_data = json.loads(json_text)
                    if isinstance(raw_data, dict) and "error" in raw_data:
                        error_msg = raw_data["error"]
                        st.error(f"⚠️ API 回傳錯誤: {error_msg}")
                        if "429" in str(error_msg) or "quota" in str(error_msg).lower():
                            st.warning("💡 提示：您的 API 免費額度暫時滿了。請等待 1 分鐘後再試。")
                        st.stop()
                    def find_valid_records(data):
                        found = []
                        if isinstance(data, list):
                            for item in data: found.extend(find_valid_records(item))
                        elif isinstance(data, dict):
                            if "col_01" in data: found.append(data)
                            else:
                                for val in data.values(): found.extend(find_valid_records(val))
                        return found
                    raw_data = find_valid_records(raw_data)
                    with st.expander("🕵️‍♂️ 開發者除錯資訊"):
                        st.write("解析出的資料筆數:", len(raw_data))
                    if not isinstance(raw_data, list): raw_data = []
                    processed_list = []
                    for item in raw_data:
                        if not isinstance(item, dict): continue
                        def get_col_stocks(start, end):
                            res = []; seen = set()
                            for i in range(start, end + 1):
                                val = item.get(f"col_{i:02d}")
                                if val and str(val).lower() != 'null':
                                    val_str = str(val).strip()
                                    if val_str not in seen: res.append(val_str); seen.add(val_str)
                            return "、".join(res)
                        if not item.get("col_01"): continue
                        record = {
                            "date": str(item.get("col_01")).replace("/", "-"),
                            "wind": item.get("col_02", ""),
                            "part_time_count": item.get("col_03", 0),
                            "worker_strong_count": item.get("col_04", 0),
                            "worker_trend_count": item.get("col_05", 0),
                            "worker_strong_list": get_col_stocks(6, 8),
                            "worker_trend_list": get_col_stocks(9, 11),
                            "boss_pullback_list": get_col_stocks(12, 14),
                            "boss_bargain_list": get_col_stocks(15, 17),
                            "top_revenue_list": get_col_stocks(18, 23),
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "manual_turnover": "" # V143 初始化欄位
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
        st.markdown("在此可修改所有歷史紀錄，**包含新增的 'manual_turnover' (手動成交值) 欄位**。")
        st.caption("手動救援格式範例 (JSON): `{\"世禾\": 20.5, \"定穎投控\": 15.2}`")
        
        # V144 Double Check: 再次確保進入編輯器前，該欄位絕對是字串型態
        if 'manual_turnover' in df.columns:
            df['manual_turnover'] = df['manual_turnover'].astype(str).replace('nan', '')
        else:
            df['manual_turnover'] = ""

        # 設定 column config
        col_config = {
            "manual_turnover": st.column_config.TextColumn(
                "手動成交值 (JSON)", 
                help="格式: {\"股票名\": 億元, ...}",
                validate=None # 不做過度嚴格驗證
            )
        }
        
        try:
            edited_history = st.data_editor(
                df, 
                num_rows="dynamic", 
                use_container_width=True, 
                column_config=col_config
            )
            
            if st.button("💾 儲存變更"):
                save_full_history(edited_history)
                st.success("更新成功！")
                time.sleep(1)
                st.rerun()
                
            if st.button("🗑️ 清空資料庫 (慎用)"): 
                clear_db()
                st.warning("已清空")
                st.rerun()
                
        except Exception as e:
            st.error(f"編輯器載入失敗，請檢查資料格式: {e}")
            
    else: st.info("目前無資料")

# --- 7. 主導航 ---
def main():
    st.sidebar.title("導航")
    if 'is_admin' not in st.session_state: st.session_state.is_admin = False
    options = ["📊 戰情儀表板"]
    if not st.session_state.is_admin:
        with st.sidebar.expander("管理員登入"):
            pwd = st.text_input("密碼", type="password")
            if pwd == "8899abc168": st.session_state.is_admin = True; st.rerun()
    if st.session_state.is_admin:
        options.append("⚙️ 資料管理後台")
        if st.sidebar.button("登出"): st.session_state.is_admin = False; st.rerun()
    page = st.sidebar.radio("前往", options)
    if page == "📊 戰情儀表板": show_dashboard()
    elif page == "⚙️ 資料管理後台": show_admin_panel()

if __name__ == "__main__":
    main()


