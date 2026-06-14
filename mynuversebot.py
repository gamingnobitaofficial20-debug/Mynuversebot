import asyncio
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from motor.motor_asyncio import AsyncIOMotorClient
from googletrans import Translator

TOKEN = "YOUR_TOKEN"
MONGO_URL = "YOUR_MONGO_URL"

bot = Bot(token=TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URL)
db = client.chat_bot
translator = Translator()

LANGS = {
    "en": {"start": "Welcome! Please use /set_en, /set_bn, or /set_hi", "search": "Searching for partner...", "found": "Partner found!", "limit": "Daily limit of 5 matches reached!", "profile": "Use: /profile Name|Age|m/f", "v_req": "Please send a photo for verification."},
    "bn": {"start": "স্বাগতম! অনুগ্রহ করে /set_en, /set_bn, বা /set_hi ব্যবহার করুন", "search": "পার্টনার খুঁজছি...", "found": "পার্টনার পাওয়া গেছে!", "limit": "৫টি ম্যাচের দৈনিক সীমা শেষ!", "profile": "ব্যবহার করুন: /profile নাম|বয়স|m/f", "v_req": "অনুগ্রহ করে ভেরিফিকেশনের জন্য একটি ছবি পাঠান।"},
    "hi": {"start": "स्वागत है! कृपया /set_en, /set_bn, या /set_hi का उपयोग करें", "search": "पार्टनर ढूंढ रहे हैं...", "found": "पार्टनर मिल गया!", "limit": "5 मैचों की दैनिक सीमा समाप्त!", "profile": "उपयोग करें: /profile नाम|उम्र|m/f", "v_req": "कृपया वेरिफिकेशन के लिए एक फोटो भेजें।"}
}

async def get_user_data(uid):
    user = await db.users.find_one({"uid": uid})
    return user if user else {"uid": uid, "lang": "en", "premium": False, "expiry": None, "matches": 0, "date": datetime.date.today(), "verified": False}

async def translate_msg(text, target_lang):
    if target_lang == "en": return text
    return (await translator.translate(text, dest=target_lang)).text

@dp.message(Command("start"))
async def start(msg: types.Message):
    await db.users.update_one({"uid": msg.from_user.id}, {"$set": {"lang": "en", "matches": 0, "date": datetime.date.today(), "premium": False, "verified": False}}, upsert=True)
    await msg.answer(LANGS["en"]["start"])

@dp.message(Command(commands=["set_en", "set_bn", "set_hi"]))
async def set_lang(msg: types.Message):
    lang = msg.text.split("_")[1]
    await db.users.update_one({"uid": msg.from_user.id}, {"$set": {"lang": lang}})
    await msg.answer(LANGS[lang]["profile"])

@dp.message(Command("profile"))
async def profile(msg: types.Message):
    try:
        parts = msg.text.replace("/profile ", "").split("|")
        await db.users.update_one({"uid": msg.from_user.id}, {"$set": {"name": parts[0], "age": parts[1], "gender": parts[2]}})
        user = await get_user_data(msg.from_user.id)
        await msg.answer(LANGS[user["lang"]]["v_req"])
    except:
        await msg.answer("Format: /profile Name|Age|m/f")

@dp.message(F.photo)
async def verify(msg: types.Message):
    await db.users.update_one({"uid": msg.from_user.id}, {"$set": {"verified": True}})
    await msg.answer("Verified!")

@dp.message(Command("find"))
async def find(msg: types.Message):
    uid = msg.from_user.id
    user = await get_user_data(uid)
    l = user["lang"]
    
    if user["date"] != datetime.date.today():
        await db.users.update_one({"uid": uid}, {"$set": {"matches": 0, "date": datetime.date.today()}})
        user["matches"] = 0

    if not user["premium"] and user["matches"] >= 5:
        await msg.answer(LANGS[l]["limit"])
        return

    partner = await db.queue.find_one({"uid": {"$ne": uid}})
    if partner:
        await db.matches.insert_one({"u1": uid, "u2": partner["uid"]})
        await db.queue.delete_one({"uid": partner["uid"]})
        await msg.answer(LANGS[l]["found"])
        await bot.send_message(partner["uid"], await translate_msg(LANGS[partner["lang"]]["found"], partner["lang"]))
    else:
        await db.queue.insert_one({"uid": uid, "lang": l})
        await msg.answer(LANGS[l]["search"])

@dp.message(Command("premium"))
async def buy_premium(msg: types.Message):
    expiry = datetime.datetime.now() + datetime.timedelta(days=30)
    await db.users.update_one({"uid": msg.from_user.id}, {"$set": {"premium": True, "expiry": expiry}})
    await msg.answer("Premium activated for 1 month!")

@dp.message(F.text & ~F.text.startswith('/'))
async def chat(msg: types.Message):
    uid = msg.from_user.id
    match = await db.matches.find_one({"$or": [{"u1": uid}, {"u2": uid}]})
    if match:
        tid = match["u2"] if match["u1"] == uid else match["u1"]
        t_user = await get_user_data(tid)
        await bot.send_message(tid, await translate_msg(msg.text, t_user["lang"]))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
