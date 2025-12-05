from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import random
import datetime
import os
from typing import Optional, List

# --------------------------
# API 初始化
# --------------------------
app = FastAPI(
    title="個人化每日運勢 API (勾選版)",
    description="根據姓名與生日產生你的今日運勢，支援勾選特定運勢項目。",
    version="9.0"
)

# 設定 HTML 檔案名稱 (請確保這個檔案跟 main.py 在同一層)
HTML_FILENAME = "index.html"

@app.get("/")
async def read_index():
    # 檢查檔案是否存在
    if not os.path.exists(HTML_FILENAME):
        return f"錯誤：找不到 {HTML_FILENAME}，請確認它跟 main.py 在同一個資料夾內！"
    return FileResponse(HTML_FILENAME)

# ==========================================
# 🔮 運勢 API 邏輯
# ==========================================

# --- Pydantic 模型 ---
class FortuneRequest(BaseModel):
    name: str = Field(..., description="使用者的姓名", example="王小明")
    birthday: str = Field(..., description="使用者的生日 (YYYY-MM-DD)", example="1990-01-31")
    # 修改：這裡接收勾選的項目列表，若沒勾選則為空 list
    ask: List[str] = Field([], description="想詢問的運勢項目", example=["感情", "事業"])

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
    # 使用 Optional，沒選到的項目會回傳 null (前端就不會顯示)
    感情: Optional[SubFortune] = None
    事業: Optional[SubFortune] = None
    學業: Optional[SubFortune] = None
    財運: Optional[SubFortune] = None

# --- 輔助函數 (維持不變) ---
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
    colors = ["熱情紅", "活力橙", "耀眼黃", "森林綠", "天空藍", "神秘靛", "優雅紫", "純潔白", "酷炫黑", "奢華金", "時尚銀"]
    return random.choice(colors)

# --- 資料庫 ---
zodiac_traits = {
    "牡羊座": "🔥 充滿衝勁", "金牛座": "🌿 穩重可靠", "雙子座": "💫 靈活聰明",
    "巨蟹座": "🦀 情感豐富", "獅子座": "🦁 光芒四射", "處女座": "✏️ 謹慎細心",
    "天秤座": "⚖️ 人際運強", "天蠍座": "🦂 直覺敏銳", "射手座": "🏹 樂觀開朗",
    "摩羯座": "⛰️ 務實踏實", "水瓶座": "🪐 創意無限", "雙魚座": "🌊 感性浪漫"
}

luck_levels = {
    1: ("★☆☆☆☆", ["💀 低調行事", "☠️ 小心為上"]),
    2: ("★★☆☆☆", ["😞 凡事三思", "⚠️ 注意溝通"]),
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
    "感情": {1: ["💔 容易爭執"], 2: ["🧊 感情平淡"], 3: ["😊 穩定發展"], 4: ["🔥 魅力提升"], 5: ["💖 桃花盛開"]},
    "事業": {1: ["⚠️ 壓力較大"], 2: ["📉 遇到瓶頸"], 3: ["👍 表現中規中矩"], 4: ["💪 積極進取"], 5: ["🏆 表現亮眼"]},
    "學業": {1: ["💤 容易分心"], 2: ["📚 需要加把勁"], 3: ["✍️ 表現正常"], 4: ["💡 領悟力高"], 5: ["🌟 學習力強"]},
    "財運": {1: ["💸 看緊荷包"], 2: ["⚖️ 收支平衡"], 3: ["💰 小有進帳"], 4: ["📈 投資獲利"], 5: ["🤑 財源廣進"]}
}

def pick_sub_fortune(category_dict) -> SubFortune:
    level = random.randint(1, 5)
    specific_desc = category_dict.get(level, ["運勢如上"]) 
    return SubFortune(
        stars="★" * level + "☆" * (5 - level),
        message=f"{random.choice(sub_fortunes[level])} {random.choice(specific_desc)}"
    )

# --- API 核心路由 ---
@app.post("/fortune", response_model=FortuneResponse)
def get_fortune(request: FortuneRequest):
    # 處理日期
    try:
        bday = datetime.datetime.strptime(request.birthday, "%Y-%m-%d")
    except ValueError:
        bday = datetime.datetime.today()

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

    # 處理勾選邏輯
    # 直接讀取 request.ask (這是一個 list)
    # 如果 list 是空的，這個迴圈就不會執行，結果就只有上面的基本資料 (符合需求)
    for item in request.ask:
        if item in fortune_categories:
            result[item] = pick_sub_fortune(fortune_categories[item])
    
    return result

if __name__ == "__main__":
    import uvicorn
    print("---------------------------------------------------------")
    print(f"🔮 伺服器啟動中！請確認 {HTML_FILENAME} 就在同一資料夾內。")
    print("👉 請打開瀏覽器輸入: http://127.0.0.1:8000")
    print("---------------------------------------------------------")
    uvicorn.run(app, host="127.0.0.1", port=8000)