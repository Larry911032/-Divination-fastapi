from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import random
import datetime
import os
from typing import Optional, List
import uvicorn

# --------------------------
# 1. 初始化與 OAuth 設定
# --------------------------
app = FastAPI(title="Nebula 運勢 API (整合版)", version="4.0")

# Session 金鑰 (建議換成強密碼)
app.add_middleware(SessionMiddleware, secret_key="YOUR_SECRET_KEY")

oauth = OAuth()

# (1) Google 設定
oauth.register(
    name='google',
    client_id='33315278198-1ij28q4g7t9e8psn6ufl0lh0hksfpfda.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# (2) GitHub 設定
oauth.register(
    name='github',
    client_id='Ov23liJVUWetRg8ECZQE',
    client_secret='65a8b74e8906e2a885c6443ce910a97f2f07b2f8',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'}
)

# (3) Facebook 設定
oauth.register(
    name='facebook',
    client_id='4356589327993064',
    client_secret='7bb533f7a96858374dba745c31ff869d',
    access_token_url='https://graph.facebook.com/v19.0/oauth/access_token',
    authorize_url='https://www.facebook.com/v19.0/dialog/oauth',
    api_base_url='https://graph.facebook.com/v19.0/',
    client_kwargs={'scope': 'public_profile'}
)

# --------------------------
# 2. 登入路由邏輯
# --------------------------

@app.get("/login/{provider}")
async def login(request: Request, provider: str):
    redirect_uri = request.url_for('auth_callback', provider=provider)
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)

@app.get("/auth/{provider}")
async def auth_callback(request: Request, provider: str):
    try:
        client = oauth.create_client(provider)
        token = await client.authorize_access_token(request)
        
        user_info = {}
        if provider == 'google':
            user_info = token.get('userinfo')
        elif provider == 'github':
            resp = await client.get('user', token=token)
            profile = resp.json()
            user_info = {'name': profile.get('login'), 'email': profile.get('email')}
        elif provider == 'facebook':
            resp = await client.get('me?fields=id,name', token=token)
            profile = resp.json()
            user_info = {'name': profile.get('name'), 'email': 'FB用戶'}
        
        request.session['user'] = dict(user_info)
        return RedirectResponse(url='/')
    except Exception as e:
        return f"登入失敗 ({provider}): {str(e)}"

@app.get("/me")
async def get_current_user(request: Request):
    user = request.session.get('user')
    if user:
        return {"is_logged_in": True, "name": user.get('name')}
    return {"is_logged_in": False}

@app.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')

# --------------------------
# 3. 運勢核心資料庫 (來自原 divination.py)
# --------------------------

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

extra_tips = [
    "🍀 幸運色能帶給你好心情", "💤 今晚早點休息，明天會更好", "☕ 一杯熱飲能帶來平靜", 
    "📖 適合閱讀或吸收新知", "💬 小心別和親近的人起衝突", "💘 可能會收到意想不到的關心",
    "🧘‍♀️ 嘗試放空自己，釋放壓力", "💪 自信是今天最強的武器"
]

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

# --------------------------
# 4. 資料模型與運算邏輯
# --------------------------

class FortuneRequest(BaseModel):
    name: str
    birthday: str
    ask: List[str] = []  # 接收使用者勾選的項目

class SubFortune(BaseModel):
    stars: str
    message: str

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

def create_sub_fortune(category_name, level) -> SubFortune:
    category_dict = fortune_categories[category_name]
    specific_desc = category_dict.get(level, ["運勢如上"]) 
    return SubFortune(
        stars="★" * level + "☆" * (5 - level),
        message=f"{random.choice(sub_fortunes[level])} {random.choice(specific_desc)}"
    )

@app.post("/fortune", response_model=FortuneResponse)
def get_fortune(request: FortuneRequest):
    try:
        bday = datetime.datetime.strptime(request.birthday, "%Y-%m-%d")
    except ValueError:
        bday = datetime.datetime.today()

    zodiac = get_zodiac(bday.month, bday.day)
    c_zodiac = get_chinese_zodiac(bday.year)

    # 運勢計算
    all_categories = ["感情", "事業", "學業", "財運"]
    scores = {}
    for cat in all_categories:
        scores[cat] = random.randint(1, 5)

    average_score = sum(scores.values()) / len(scores)
    luck_val = int(round(average_score))
    luck_val = max(1, min(5, luck_val))

    luck_star, luck_msgs = luck_levels[luck_val]
    tip = random.choice(extra_tips)
    
    result = {
        "今天日期": datetime.date.today().isoformat(),
        "姓名": request.name,
        "出生年月日": request.birthday,
        "星座": zodiac,
        "生肖": c_zodiac,
        "運勢": luck_star,
        "描述": f"{zodiac_traits.get(zodiac, '')} {random.choice(luck_msgs)} {tip}",
        "幸運顏色": get_lucky_color(bday.year, c_zodiac),
        "幸運數字": random.randint(1, 99)
    }

    # 處理勾選細項
    for item in request.ask:
        if item in fortune_categories:
            item_score = scores.get(item, 3) 
            result[item] = create_sub_fortune(item, item_score)
    
    return result

@app.get("/")
async def read_index():
    return FileResponse("index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)