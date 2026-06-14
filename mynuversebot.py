import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from enum import Enum

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, filters, ContextTypes
)

# ============ CONFIGURATION ============
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not found!")
    exit(1)

print("🤖 Bot Starting...")
print(f"Port: {PORT}")

# ============ STATES ============
class RegState(Enum):
    WAITING_NAME = 1
    WAITING_AGE = 2
    WAITING_LANG = 3
    WAITING_GENDER = 4
    WAITING_LOOKING = 5
    WAITING_VERIFY_PIC = 6
    WAITING_AGE_FILTER_MIN = 7
    WAITING_AGE_FILTER_MAX = 8
    WAITING_EDIT_NAME = 9
    WAITING_EDIT_AGE = 10

# ============ DATA ============
users: Dict[int, dict] = {}
waiting: List[int] = []
chats: Dict[int, int] = {}
states: Dict[int, RegState] = {}
match_track: Dict[int, dict] = {}

# ============ LANGUAGES ============
LANGUAGES = [
    {"code": "english", "name": "English", "flag": "🇬🇧"},
    {"code": "bangla", "name": "Bangla", "flag": "🇧🇩"},
    {"code": "hindi", "name": "Hindi", "flag": "🇮🇳"}
]

# ============ PREMIUM ============
PACKAGES = {
    "pkg_24h": {"name": "24 Hours", "days": 1, "stars": 39},
    "pkg_3d": {"name": "3 Days", "days": 3, "stars": 149},
    "pkg_5d": {"name": "5 Days", "days": 5, "stars": 249},
    "pkg_7d": {"name": "7 Days", "days": 7, "stars": 379},
    "pkg_14d": {"name": "14 Days", "days": 14, "stars": 499},
    "pkg_1m": {"name": "1 Month", "days": 30, "stars": 799}
}

# ============ MESSAGES ============
MSG = {
    'english': {
        'start': "👋 Welcome! Send your Name:",
        'registered': "✅ Already registered! Use menu:",
        'find': "🔍 Find Partner",
        'next': "⏩ Next Partner",
        'stop': "⛔ Stop Chat",
        'profile': "👤 My Profile",
        'premium': "💎 Premium",
        'help': "❓ Help",
        'settings': "⚙️ Settings",
        'change_lang': "🌐 Change Language",
        'profile_txt': "📊 PROFILE\n\nName: {name}\nAge: {age}\nLanguage: {lang}\nGender: {gender}\nLooking: {looking}\nVerified: {verified}\nPremium: {premium}\nMatches: {matches}/5",
        'found': "🎉 PARTNER FOUND!\n\nName: {name}\nAge: {age}\nLanguage: {lang}\nGender: {gender}\n\nStart chatting! 💬",
        'name_saved': "✅ Name saved: {text}\n\n📅 Send your Age:",
        'ask_lang': "🌐 Select your language:",
        'ask_gender': "⚧ Select your gender (CANNOT change later):",
        'ask_looking': "🎯 Who are you looking for?\n\nFree: 5 matches/day\nPremium: Unlimited!",
        'invalid_age': "❌ Invalid age! Send number 15-99:",
        'ask_min_age': "🔞 Minimum age for partner (18-99):",
        'ask_max_age': "🔞 Maximum age for partner (18-99):",
        'filter_done': "✅ Age filter updated!",
        'in_chat': "⚠️ You're already in a chat!",
        'searching': "⏳ Searching for partner...",
        'search_cancel': "❌ Search cancelled",
        'chat_stop': "🛑 You stopped the chat",
        'partner_stop': "🛑 Your partner stopped the chat",
        'not_connected': "⚠️ Not connected to any chat",
        'partner_left': "👋 Your partner left the chat",
        'premium_text': "💎 PREMIUM MEMBERSHIP\n\n⭐ 39 stars - 24 Hours\n⭐ 149 stars - 3 Days\n⭐ 249 stars - 5 Days\n⭐ 379 stars - 7 Days\n⭐ 499 stars - 14 Days\n⭐ 799 stars - 30 Days\n\nChoose package:",
        'premium_activated': "🎉 PREMIUM ACTIVATED!\n\nPackage: {pkg}\nDuration: {days} days\nEnjoy unlimited matches! ✨",
        'help_text': "📖 HELP GUIDE\n\n🔹 Free: 5 gender-preference matches/day\n🔹 After limit: Unlimited random matches\n🔹 Premium: Unlimited gender-preference matches\n🔹 Gender is permanent after profile completion\n🔹 Change language anytime",
        'verify_photo': "📸 Send your photo for verification:",
        'verify_success': "✅ Profile verified! Gender locked: {gender}",
        'edit_name': "✏️ Edit Name",
        'edit_age': "✏️ Edit Age",
        'verify_btn': "📸 Verify",
        'filter_btn': "🎯 Age Filter",
        'gender_locked': "🔒 Gender locked: {gender}",
        'lang_changed': "✅ Language changed to {lang}",
        'choose_lang': "🌐 Choose your language:",
        'back': "🔙 Back",
        'male': "Male", 'female': "Female", 'gay': "Gay", 'lesbian': "Lesbian", 'everyone': "Everyone"
    },
    'bangla': {
        'start': "👋 স্বাগতম! আপনার নাম লিখুন:",
        'registered': "✅ আপনি রেজিস্টার্ড! মেনু ব্যবহার করুন:",
        'find': "🔍 পার্টনার খুঁজুন",
        'next': "⏩ পরবর্তী",
        'stop': "⛔ চ্যাট বন্ধ করুন",
        'profile': "👤 আমার প্রোফাইল",
        'premium': "💎 প্রিমিয়াম",
        'help': "❓ সাহায্য",
        'settings': "⚙️ সেটিংস",
        'change_lang': "🌐 ভাষা পরিবর্তন",
        'profile_txt': "📊 প্রোফাইল\n\nনাম: {name}\nবয়স: {age}\nভাষা: {lang}\nলিঙ্গ: {gender}\nখুঁজছেন: {looking}\nভেরিফাইড: {verified}\nপ্রিমিয়াম: {premium}\nম্যাচ: {matches}/5",
        'found': "🎉 পার্টনার পাওয়া গেছে!\n\nনাম: {name}\nবয়স: {age}\nভাষা: {lang}\nলিঙ্গ: {gender}\n\nচ্যাট শুরু করুন! 💬",
        'name_saved': "✅ নাম সেভ: {text}\n\n📅 আপনার বয়স লিখুন:",
        'ask_lang': "🌐 আপনার ভাষা নির্বাচন করুন:",
        'ask_gender': "⚧ আপনার লিঙ্গ নির্বাচন করুন (পরবর্তীতে পরিবর্তন করা যাবে না):",
        'ask_looking': "🎯 আপনি কাকে খুঁজছেন?\n\nফ্রি: ৫টি ম্যাচ/দিন\nপ্রিমিয়াম: আনলিমিটেড!",
        'invalid_age': "❌ ভুল বয়স! ১৫-৯৯ এর মধ্যে লিখুন:",
        'ask_min_age': "🔞 পার্টনারের সর্বনিম্ন বয়স (১৮-৯৯):",
        'ask_max_age': "🔞 পার্টনারের সর্বোচ্চ বয়স (১৮-৯৯):",
        'filter_done': "✅ বয়স ফিল্টার আপডেট!",
        'in_chat': "⚠️ আপনি ইতিমধ্যে চ্যাটে আছেন!",
        'searching': "⏳ পার্টনার খোঁজা হচ্ছে...",
        'search_cancel': "❌ খোঁজা বাতিল",
        'chat_stop': "🛑 আপনি চ্যাট বন্ধ করেছেন",
        'partner_stop': "🛑 আপনার পার্টনার চ্যাট বন্ধ করেছে",
        'not_connected': "⚠️ কোনো চ্যাটে সংযুক্ত নন",
        'partner_left': "👋 আপনার পার্টনার চলে গেছে",
        'premium_text': "💎 প্রিমিয়াম মেম্বারশিপ\n\n⭐ ৩৯ স্টার - ২৪ ঘন্টা\n⭐ ১৪৯ স্টার - ৩ দিন\n⭐ ২৪৯ স্টার - ৫ দিন\n⭐ ৩৭৯ স্টার - ৭ দিন\n⭐ ৪৯৯ স্টার - ১৪ দিন\n⭐ ৭৯৯ স্টার - ৩০ দিন\n\nপ্যাকেজ নির্বাচন:",
        'premium_activated': "🎉 প্রিমিয়াম সক্রিয়!\n\nপ্যাকেজ: {pkg}\nমেয়াদ: {days} দিন\nআনলিমিটেড ম্যাচ উপভোগ করুন! ✨",
        'help_text': "📖 সাহায্য গাইড\n\n🔹 ফ্রি: ৫টি প্রেফারেন্স ম্যাচ/দিন\n🔹 লিমিট শেষে: আনলিমিটেড র্যান্ডম ম্যাচ\n🔹 প্রিমিয়াম: আনলিমিটেড প্রেফারেন্স ম্যাচ\n🔹 প্রোফাইল完成后 লিঙ্গ লক\n🔹 যেকোনো সময় ভাষা পরিবর্তন",
        'verify_photo': "📸 ভেরিফিকেশনের জন্য আপনার ছবি পাঠান:",
        'verify_success': "✅ প্রোফাইল ভেরিফাইড! লিঙ্গ লক: {gender}",
        'edit_name': "✏️ নাম পরিবর্তন",
        'edit_age': "✏️ বয়স পরিবর্তন",
        'verify_btn': "📸 ভেরিফাই",
        'filter_btn': "🎯 বয়স ফিল্টার",
        'gender_locked': "🔒 লিঙ্গ লক: {gender}",
        'lang_changed': "✅ ভাষা পরিবর্তন: {lang}",
        'choose_lang': "🌐 আপনার ভাষা নির্বাচন করুন:",
        'back': "🔙 পেছনে",
        'male': "পুরুষ", 'female': "মহিলা", 'gay': "গে", 'lesbian': "লেসবিয়ান", 'everyone': "সবাই"
    },
    'hindi': {
        'start': "👋 स्वागत है! अपना नाम लिखें:",
        'registered': "✅ आप रजिस्टर्ड हैं! मेनू देखें:",
        'find': "🔍 साथी ढूंढें",
        'next': "⏩ अगला",
        'stop': "⛔ चैट बंद करें",
        'profile': "👤 मेरा प्रोफाइल",
        'premium': "💎 प्रीमियम",
        'help': "❓ सहायता",
        'settings': "⚙️ सेटिंग्स",
        'change_lang': "🌐 भाषा बदलें",
        'profile_txt': "📊 प्रोफाइल\n\nनाम: {name}\nउम्र: {age}\nभाषा: {lang}\nलिंग: {gender}\nढूंढ रहे: {looking}\nसत्यापित: {verified}\nप्रीमियम: {premium}\nमैच: {matches}/5",
        'found': "🎉 साथी मिल गया!\n\nनाम: {name}\nउम्र: {age}\nभाषा: {lang}\nलिंग: {gender}\n\nचैट शुरू करें! 💬",
        'name_saved': "✅ नाम सहेजा: {text}\n\n📅 अपनी उम्र लिखें:",
        'ask_lang': "🌐 अपनी भाषा चुनें:",
        'ask_gender': "⚧ अपना लिंग चुनें (बाद में नहीं बदल सकते):",
        'ask_looking': "🎯 किसे ढूंढ रहे हैं?\n\nमुफ्त: 5 मैच/दिन\nप्रीमियम: असीमित!",
        'invalid_age': "❌ गलत उम्र! 15-99 के बीच लिखें:",
        'ask_min_age': "🔞 साथी की न्यूनतम उम्र (18-99):",
        'ask_max_age': "🔞 साथी की अधिकतम उम्र (18-99):",
        'filter_done': "✅ उम्र फ़िल्टर अपडेट!",
        'in_chat': "⚠️ आप पहले से चैट में हैं!",
        'searching': "⏳ साथी ढूंढ रहे...",
        'search_cancel': "❌ खोज रद्द",
        'chat_stop': "🛑 आपने चैट बंद की",
        'partner_stop': "🛑 आपके साथी ने चैट बंद की",
        'not_connected': "⚠️ किसी चैट में नहीं हैं",
        'partner_left': "👋 आपका साथी चला गया",
        'premium_text': "💎 प्रीमियम सदस्यता\n\n⭐ 39 स्टार - 24 घंटे\n⭐ 149 स्टार - 3 दिन\n⭐ 249 स्टार - 5 दिन\n⭐ 379 स्टार - 7 दिन\n⭐ 499 स्टार - 14 दिन\n⭐ 799 स्टार - 30 दिन\n\nपैकेज चुनें:",
        'premium_activated': "🎉 प्रीमियम सक्रिय!\n\nपैकेज: {pkg}\nअवधि: {days} दिन\nअसीमित मैच का आनंद लें! ✨",
        'help_text': "📖 सहायता गाइड\n\n🔹 मुफ्त: 5 पसंद मैच/दिन\n🔹 सीमा के बाद: असीमित रैंडम मैच\n🔹 प्रीमियम: असीमित पसंद मैच\n🔹 प्रोफाइल पूरा होने पर लिंग लॉक\n🔹 कभी भी भाषा बदलें",
        'verify_photo': "📸 सत्यापन के लिए अपनी फोटो भेजें:",
        'verify_success': "✅ प्रोफाइल सत्यापित! लिंग लॉक: {gender}",
        'edit_name': "✏️ नाम बदलें",
        'edit_age': "✏️ उम्र बदलें",
        'verify_btn': "📸 सत्यापित",
        'filter_btn': "🎯 उम्र फ़िल्टर",
        'gender_locked': "🔒 लिंग लॉक: {gender}",
        'lang_changed': "✅ भाषा बदली: {lang}",
        'choose_lang': "🌐 अपनी भाषा चुनें:",
        'back': "🔙 वापस",
        'male': "पुरुष", 'female': "महिला", 'gay': "गे", 'lesbian': "लेस्बियन", 'everyone': "सभी"
    }
}

# ============ HELPERS ============
def get_text(uid, key, **kwargs):
    lang = users.get(uid, {}).get('lang', 'english')
    text = MSG.get(lang, MSG['english']).get(key, MSG['english'][key])
    return text.format(**kwargs) if kwargs else text

def is_premium(uid):
    exp = users.get(uid, {}).get('expiry')
    if exp:
        return datetime.now() < datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
    return False

def is_locked(uid):
    u = users.get(uid, {})
    return all([u.get('name'), u.get('age'), u.get('gender'), u.get('looking'), u.get('verified')])

def get_matches(uid):
    if uid not in match_track:
        match_track[uid] = {'count': 0, 'date': datetime.now().date()}
    today = datetime.now().date()
    if match_track[uid]['date'] != today:
        match_track[uid] = {'count': 0, 'date': today}
    return match_track[uid]['count']

def inc_match(uid):
    if is_premium(uid):
        return
    today = datetime.now().date()
    if uid not in match_track:
        match_track[uid] = {'count': 0, 'date': today}
    if match_track[uid]['date'] != today:
        match_track[uid] = {'count': 0, 'date': today}
    match_track[uid]['count'] += 1

def can_match(uid, looking):
    if is_premium(uid) or looking == 'everyone':
        return True
    return get_matches(uid) < 5

# ============ KEYBOARDS ============
def menu(uid):
    b = lambda k: KeyboardButton(get_text(uid, k))
    return ReplyKeyboardMarkup([
        [b('find'), b('next')],
        [b('stop'), b('profile')],
        [b('premium'), b('settings')],
        [b('help')]
    ], resize_keyboard=True)

def lang_kb():
    kb = []
    row = []
    for i, l in enumerate(LANGUAGES):
        row.append(InlineKeyboardButton(f"{l['flag']} {l['name']}", callback_data=f"lang_{l['code']}"))
        if (i + 1) % 2 == 0:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    return InlineKeyboardMarkup(kb)

def gender_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👦 Male", callback_data="gender_male")],
        [InlineKeyboardButton("👧 Female", callback_data="gender_female")]
    ])

def looking_kb(uid, prefix):
    kb = []
    if is_premium(uid):
        kb = [
            [InlineKeyboardButton("👧 Girls", callback_data=f"{prefix}female")],
            [InlineKeyboardButton("👦 Boys", callback_data=f"{prefix}male")],
            [InlineKeyboardButton("🌍 Everyone", callback_data=f"{prefix}everyone")]
        ]
    else:
        kb = [
            [InlineKeyboardButton("👧 Girls (5/day)", callback_data=f"{prefix}female")],
            [InlineKeyboardButton("👦 Boys (5/day)", callback_data=f"{prefix}male")],
            [InlineKeyboardButton("🌍 Random (Unlimited)", callback_data=f"{prefix}everyone")],
            [InlineKeyboardButton("💎 Get Premium", callback_data="premium")]
        ]
    return InlineKeyboardMarkup(kb)

def premium_kb():
    kb = []
    row = []
    for i, (pid, pkg) in enumerate(PACKAGES.items()):
        row.append(InlineKeyboardButton(f"⭐ {pkg['stars']} - {pkg['name']}", callback_data=f"buy_{pid}"))
        if (i + 1) % 2 == 0:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return InlineKeyboardMarkup(kb)

def settings_kb(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(uid, 'change_lang'), callback_data="change_lang")],
        [InlineKeyboardButton(get_text(uid, 'back'), callback_data="back")]
    ])

def profile_kb(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_text(uid, 'edit_name'), callback_data="edit_name"),
         InlineKeyboardButton(get_text(uid, 'edit_age'), callback_data="edit_age")],
        [InlineKeyboardButton(get_text(uid, 'verify_btn'), callback_data="verify"),
         InlineKeyboardButton(get_text(uid, 'filter_btn'), callback_data="filter")]
    ])

# ============ MATCH ============
async def match_users(uid, context):
    user = users[uid]
    for pid in waiting[:]:
        if pid == uid:
            continue
        partner = users.get(pid)
        if not partner:
            waiting.remove(pid)
            continue
        if not (user['min_age'] <= partner['age'] <= user['max_age'] and
                partner['min_age'] <= user['age'] <= partner['max_age']):
            continue
        if user['lang'] != partner['lang']:
            continue
        waiting.remove(pid)
        if uid in waiting:
            waiting.remove(uid)
        inc_match(uid)
        inc_match(pid)
        chats[uid] = pid
        chats[pid] = uid
        await context.bot.send_message(uid, get_text(uid, 'found').format(
            name=partner['name'], age=partner['age'], lang=partner['lang'], gender=partner['gender']))
        await context.bot.send_message(pid, get_text(pid, 'found').format(
            name=user['name'], age=user['age'], lang=user['lang'], gender=user['gender']))
        return True
    return False

# ============ HANDLERS ============
async def start(update, context):
    uid = update.effective_user.id
    if uid not in users:
        users[uid] = {
            'name': None, 'age': None, 'lang': None, 'gender': None,
            'looking': 'everyone', 'verified': False, 'expiry': None,
            'min_age': 18, 'max_age': 50
        }
        states[uid] = RegState.WAITING_NAME
        await update.message.reply_text(get_text(uid, 'start'))
    else:
        await update.message.reply_text(get_text(uid, 'registered'), reply_markup=menu(uid))

async def handle_msg(update, context):
    uid = update.effective_user.id
    text = update.message.text
    
    if uid in states:
        s = states[uid]
        if s == RegState.WAITING_NAME:
            users[uid]['name'] = text
            await update.message.reply_text(get_text(uid, 'name_saved').format(text=text))
            states[uid] = RegState.WAITING_AGE
            return
        elif s == RegState.WAITING_AGE:
            if text.isdigit() and 15 <= int(text) <= 99:
                users[uid]['age'] = int(text)
                await update.message.reply_text(get_text(uid, 'ask_lang'), reply_markup=lang_kb())
                states[uid] = RegState.WAITING_LANG
            else:
                await update.message.reply_text(get_text(uid, 'invalid_age'))
            return
        elif s == RegState.WAITING_AGE_FILTER_MIN:
            if text.isdigit():
                users[uid]['min_age'] = int(text)
                await update.message.reply_text(get_text(uid, 'ask_max_age'))
                states[uid] = RegState.WAITING_AGE_FILTER_MAX
            return
        elif s == RegState.WAITING_AGE_FILTER_MAX:
            if text.isdigit():
                users[uid]['max_age'] = int(text)
                del states[uid]
                await update.message.reply_text(get_text(uid, 'filter_done'), reply_markup=menu(uid))
            return
        elif s == RegState.WAITING_EDIT_NAME:
            users[uid]['name'] = text
            del states[uid]
            await update.message.reply_text("✅ Name updated!", reply_markup=menu(uid))
            return
        elif s == RegState.WAITING_EDIT_AGE:
            if text.isdigit() and 15 <= int(text) <= 99:
                users[uid]['age'] = int(text)
                del states[uid]
                await update.message.reply_text("✅ Age updated!", reply_markup=menu(uid))
            return
    
    cmd = text
    if cmd in ["🔍 Find Partner", get_text(uid, 'find')]:
        if uid in chats:
            await update.message.reply_text(get_text(uid, 'in_chat'))
            return
        if not can_match(uid, users[uid]['looking']):
            await update.message.reply_text("⚠️ Daily limit reached! Using random mode.")
            users[uid]['looking'] = 'everyone'
        waiting.append(uid)
        await update.message.reply_text(get_text(uid, 'searching'))
        await match_users(uid, context)
    elif cmd in ["⛔ Stop Chat", get_text(uid, 'stop')]:
        if uid in waiting:
            waiting.remove(uid)
        elif uid in chats:
            pid = chats[uid]
            del chats[uid]
            del chats[pid]
            await context.bot.send_message(pid, get_text(pid, 'partner_stop'))
        await update.message.reply_text(get_text(uid, 'chat_stop'), reply_markup=menu(uid))
    elif cmd in ["⏩ Next Partner", get_text(uid, 'next')]:
        if uid in chats:
            pid = chats[uid]
            del chats[uid]
            del chats[pid]
            await context.bot.send_message(pid, get_text(pid, 'partner_left'))
        waiting.append(uid)
        await match_users(uid, context)
    elif cmd in ["👤 My Profile", get_text(uid, 'profile')]:
        u = users[uid]
        await update.message.reply_text(get_text(uid, 'profile_txt').format(
            name=u['name'], age=u['age'], lang=u['lang'], gender=u['gender'] or "Not set",
            looking=u['looking'], verified="✅" if u['verified'] else "❌",
            premium="✅" if is_premium(uid) else "❌", matches=get_matches(uid)), reply_markup=profile_kb(uid))
    elif cmd in ["💎 Premium", get_text(uid, 'premium')]:
        await update.message.reply_text(get_text(uid, 'premium_text'), reply_markup=premium_kb())
    elif cmd in ["⚙️ Settings", get_text(uid, 'settings')]:
        await update.message.reply_text("⚙️ Settings:", reply_markup=settings_kb(uid))
    elif cmd in ["❓ Help", get_text(uid, 'help')]:
        await update.message.reply_text(get_text(uid, 'help_text'))
    elif uid in chats:
        await context.bot.send_message(chats[uid], text)
    else:
        await update.message.reply_text(get_text(uid, 'searching'), reply_markup=menu(uid))

async def handle_photo(update, context):
    uid = update.effective_user.id
    if uid in states and states[uid] == RegState.WAITING_VERIFY_PIC:
        users[uid]['verified'] = True
        del states[uid]
        await update.message.reply_text(get_text(uid, 'verify_success').format(gender=users[uid]['gender']), reply_markup=menu(uid))
    elif uid in chats:
        await context.bot.send_photo(chats[uid], update.message.photo[-1].file_id)

async def handle_callback(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data
    
    if data.startswith("lang_"):
        lang = data.replace("lang_", "")
        users[uid]['lang'] = lang
        await q.edit_message_text(get_text(uid, 'lang_changed').format(lang=lang))
        if uid in states and states[uid] == RegState.WAITING_LANG:
            states[uid] = RegState.WAITING_GENDER
            await q.message.reply_text(get_text(uid, 'ask_gender'), reply_markup=gender_kb())
        return
    if data.startswith("gender_"):
        if is_locked(uid):
            await q.message.reply_text(get_text(uid, 'gender_locked').format(gender=users[uid]['gender']))
            return
        gender = "Male" if "male" in data else "Female"
        users[uid]['gender'] = gender
        await q.edit_message_text(get_text(uid, 'ask_looking'))
        await q.message.reply_text(get_text(uid, 'ask_looking'), reply_markup=looking_kb(uid, "look_"))
        states[uid] = RegState.WAITING_LOOKING
        return
    if data.startswith("look_"):
        looking = data.replace("look_", "")
        users[uid]['looking'] = looking
        await q.edit_message_text(get_text(uid, 'verify_photo'))
        await q.message.reply_text(get_text(uid, 'verify_photo'))
        states[uid] = RegState.WAITING_VERIFY_PIC
        return
    if data == "edit_name":
        await q.edit_message_text("✏️ Send new name:")
        states[uid] = RegState.WAITING_EDIT_NAME
        return
    if data == "edit_age":
        await q.edit_message_text("📅 Send new age (15-99):")
        states[uid] = RegState.WAITING_EDIT_AGE
        return
    if data == "verify":
        await q.edit_message_text(get_text(uid, 'verify_photo'))
        states[uid] = RegState.WAITING_VERIFY_PIC
        return
    if data == "filter":
        await q.edit_message_text(get_text(uid, 'ask_min_age'))
        states[uid] = RegState.WAITING_AGE_FILTER_MIN
        return
    if data == "change_lang":
        await q.edit_message_text(get_text(uid, 'choose_lang'), reply_markup=lang_kb())
        return
    if data == "back":
        await q.edit_message_text("Main Menu")
        await q.message.reply_text(get_text(uid, 'registered'), reply_markup=menu(uid))
        return
    if data == "premium":
        await q.message.reply_text(get_text(uid, 'premium_text'), reply_markup=premium_kb())
        return
    if data.startswith("buy_"):
        pid = data.replace("buy_", "")
        pkg = PACKAGES.get(pid)
        if pkg:
            await context.bot.send_invoice(uid, f"Mnuverse: {pkg['name']}", f"{pkg['days']} days", f"prem_{pid}", "", "XTR", [LabeledPrice(pkg['name'], pkg['stars'])])
        return

async def pre_checkout(update, context):
    await update.pre_checkout_query.answer(ok=True)

async def payment(update, context):
    uid = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    if payload.startswith("prem_"):
        pid = payload.replace("prem_", "")
        pkg = PACKAGES.get(pid)
        if pkg:
            expiry = datetime.now() + timedelta(days=pkg['days'])
            users[uid]['expiry'] = expiry.strftime("%Y-%m-%d %H:%M:%S")
            await update.message.reply_text(get_text(uid, 'premium_activated').format(pkg=pkg['name'], days=pkg['days']), reply_markup=menu(uid))

# ============ MAIN ============
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ Bot is running!")
    await app.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook")

if __name__ == "__main__":
    asyncio.run(main())
