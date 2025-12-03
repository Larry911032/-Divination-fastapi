from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import random
import datetime
from typing import Optional

# --------------------------
# API 初始化
# --------------------------
app = FastAPI(
    title="個人化每日運勢 API (含網頁版)",
    description="根據姓名與生日產生你的今日運勢 💫 可自由選擇查詢感情、事業、學業、財運",
    version="7.2"
)

# ==========================================
# 🔥 新增：掛載靜態檔案與首頁路由
# ==========================================

# 1. 告訴 FastAPI：static 資料夾裡的東西是靜態檔案 (css, js, html)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. 設定首頁路由：當使用者連到網址根目錄時，回傳 index.html
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# ==========================================
# 🔮 原本的運勢 API 邏輯
# ==========================================

# --- Pydantic 模型 ---
class FortuneRequest(BaseModel):
    name: str = Field(..., description="使用者的姓名", example="王小明")
    birthday: str = Field(..., description="使用者的生日 (YYYY-MM-DD)", example="1990-01-31", pattern=r"^\d{4}-\d{2}-\d{2}$")
    ask: list[str] = Field(["全部"], description="想詢問的運勢項目", example=["全部"])

class SubFortune(BaseModel):
    stars: str = Field(..., description="星等表示", example="★★★★☆")
    message: str = Field(..., description="運勢詳細訊息", example="✨ 有小驚喜")

class FortuneResponse(BaseModel):
    今天日期: str
    姓名: str
    出生年月日: str
    星座: str
    生肖: str
    運勢: str
    描述: str
    幸運顏色: str
    幸運數字: int
    感情: Optional[SubFortune] = None
    事業: Optional[SubFortune] = None
    學業: Optional[SubFortune] = None
    財運: Optional[SubFortune] = None
    error: Optional[dict] = None

# --- 輔助函數 ---
def get_zodiac(month: int, day: int) -> str:
    zodiac_dates = [
        ((1, 20), "摩羯座"), ((2, 19), "水瓶座"), ((3, 21), "雙魚座"),
        ((4, 20), "牡羊座"), ((5, 21), "金牛座"), ((6, 22), "雙子座"),
        ((7, 23), "巨蟹座"), ((8, 23), "獅子座"), ((9, 23), "處女座"),
        ((10, 24), "天秤座"), ((11, 23), "天蠍座"), ((12, 22), "射手座")
    ]
    target = (month, day)
    if target >= (12, 22) or target < (1, 20): return "摩羯座"
    for (m, d), sign in zodiac_dates:
        if target < (m, d): return sign
    return "未知星座"

def get_chinese_zodiac(year: int) -> str:
    zodiacs = ["鼠","牛","虎","兔","龍","蛇","馬","羊","猴","雞","狗","豬"]
    return zodiacs[(year - 1900) % 12]

def get_lucky_color(year: int, zodiac: str) -> str:
    # 簡化的顏色邏輯，確保程式碼簡潔
    colors = ["紅", "橙", "黃", "綠", "藍", "靛", "紫", "白", "黑", "金", "銀"]
    return random.choice(colors)

# --- 資料字典 ---
zodiac_traits = {
    "牡羊座": "🔥 充滿衝勁", "金牛座": "🌿 穩重可靠", "雙子座": "💫 靈活聰明",
    "巨蟹座": "🦀 情感豐富", "獅子座": "🦁 光芒四射", "處女座": "✏️ 謹慎細心",
    "天秤座": "⚖️ 人際運強", "天蠍座": "🦂 直覺敏銳", "射手座": "🏹 樂觀開朗",
    "摩羯座": "⛰️ 務實踏實", "水瓶座": "🪐 創意無限", "雙魚座": "🌊 感性浪漫"
}

luck_levels = {
    1: ("★☆☆☆☆", ["💀 大凶！低調行事", "☠️ 小心為上"]),
    2: ("★★☆☆☆", ["😞 小凶，凡事三思", "⚠️ 注意溝通"]),
    3: ("★★★☆☆", ["😐 平平，歲月靜好", "🤔 按部就班"]),
    4: ("★★★★☆", ["😄 小吉，貴人相助", "🌟 運勢不錯"]),
    5: ("★★★★★", ["🤩 大吉！心想事成", "🏆 強運當頭"])
}

sub_fortunes = {
    1: ["⚠️ 不太順利", "🛑 暫緩計畫"], 2: ["🔍 注意細節", "😕 有點小麻煩"],
    3: ["📘 穩定前進", "🧊 平淡是福"], 4: ["✨ 會有驚喜", "👍 手氣不錯"],
    5: ["🔥 氣勢如虹", "💎 把握機會"]
}

fortune_categories = {
    "感情": {1: ["💔 容易爭執"], 5: ["💖 桃花盛開"]},
    "事業": {1: ["⚠️ 壓力較大"], 5: ["🏆 表現亮眼"]},
    "學業": {1: ["💤 容易分心"], 5: ["🌟 學習力強"]},
    "財運": {1: ["💸 看緊荷包"], 5: ["🤑 財源廣進"]}
}

def pick_sub_fortune(category_dict) -> SubFortune:
    level = random.randint(1, 5)
    # 如果該等級沒有特定描述，就用通用描述
    specific_desc = category_dict.get(level, ["運勢如上"]) 
    return SubFortune(
        stars="★" * level + "☆" * (5 - level),
        message=f"{random.choice(sub_fortunes[level])} {random.choice(specific_desc)}"
    )

# --- API 核心路由 ---
@app.post("/fortune", response_model=FortuneResponse)
def get_fortune(request: FortuneRequest):
    bday = datetime.datetime.strptime(request.birthday, "%Y-%m-%d")
    zodiac = get_zodiac(bday.month, bday.day)
    c_zodiac = get_chinese_zodiac(bday.year)
    
    luck_val = random.randint(1, 5)
    luck_star, luck_msgs = luck_levels[luck_val]
    
    result = {
        "今天日期": datetime.date.today().isoformat(),
        "姓名": request.name,
        "出生年月日": request.birthday,
        "星座": zodiac,
        "生肖": c_zodiac,
        "運勢": luck_star,
        "描述": f"{zodiac_traits.get(zodiac, '')} {random.choice(luck_msgs)}",
        "幸運顏色": get_lucky_color(bday.year, c_zodiac),
        "幸運數字": random.randint(1, 99)
    }

    asks = request.ask
    if "全部" in asks:
        asks = ["感情", "事業", "學業", "財運"]
        
    for item in asks:
        if item in fortune_categories:
            result[item] = pick_sub_fortune(fortune_categories[item])
    
    return result