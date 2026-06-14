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

print("="*50)
print("🤖 Bot is starting...")
print(f"BOT_TOKEN: {'SET' if BOT_TOKEN else 'NOT SET'}")
print("="*50)

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not found in environment variables!")
    exit(1)

# ============ STATES ============
class RegState(Enum):
    WAITING_NAME = 1
    WAITING_AGE = 2
    WAITING_LANG = 3
    WAITING_GENDER = 4
    WAITING_LOOKING = 5
    WAITING_VERIFY_PIC = 6
    WAITING_TARGET_AGE_MIN = 7
    WAITING_TARGET_AGE_MAX = 8
    WAITING_EDIT_NAME = 9
    WAITING_EDIT_AGE = 10

# ============ DATA STORAGE ============
users_profile: Dict[int, dict] = {}
waiting_room: List[int] = []
active_chats: Dict[int, int] = {}
user_states: Dict[int, RegState] = {}
user_match_tracking: Dict[int, dict] = {}

# ============ LANGUAGES ============
AVAILABLE_LANGUAGES = [
    {"code": "english", "name": "English", "flag": "🇬🇧"},
    {"code": "bangla", "name": "Bangla", "flag": "🇧🇩"},
    {"code": "hindi", "name": "Hindi", "flag": "🇮🇳"}
]

# ============ PREMIUM PACKAGES ============
PREMIUM_PACKAGES = {
    "pkg_24h": {"name": "24 Hours", "days": 1, "stars": 39},
    "pkg_3d": {"name": "3 Days", "days": 3, "stars": 149},
    "pkg_5d": {"name": "5 Days", "days": 5, "stars": 249},
    "pkg_7d": {"name": "7 Days", "days": 7, "stars": 379},
    "pkg_14d": {"name": "14 Days", "days": 14, "stars": 499},
    "pkg_1m": {"name": "1 Month", "days": 30, "stars": 799}
}

# ============ MESSAGES ============
MESSAGES = {
    'english': {
        'start': "👋 Welcome! Send your Name:",
        'already_reg': "🤖 You are registered!",
        'find': "🚀 Find Partner",
        'next': "⏭️ Next",
        'stop': "🛑 Stop",
        'profile': "⚙️ Profile",
        'premium': "💎 Premium",
        'help_btn': "❓ Help",
        'settings': "⚙️ Settings",
        'change_lang': "🌐 Language",
        'profile_txt': "👤 {name}\n🎂 {age}\n🗣️ {lang}\n⚥ {gender}\n🎯 {looking_for}\n🛡️ {status}\n💎 {premium_status}",
        'partner_found': "🎉 Partner: {name}\nAge: {age}\nLanguage: {lang}\nGender: {gender}",
        'name_saved': "👍 Name: {text}\n🎂 Send Age:",
        'select_lang': "🗣️ Select Language:",
        'select_gender': "⚥ Select Gender (Permanent):",
        'select_looking': "🎯 Looking for?",
        'invalid_age': "⚠️ Valid age 15-99:",
        'enter_min_age': "🎯 Min age (18-99):",
        'enter_max_age': "🎯 Max age (18-99):",
        'filter_updated': "✅ Filter updated!",
        'already_chat': "⚠️ Already in chat!",
        'searching': "⏳ Searching...",
        'search_start': "🔍 Searching...",
        'search_cancel': "🛑 Cancelled",
        'you_stopped': "🛑 You stopped",
        'partner_stopped': "🛑 Partner stopped",
        'not_connected': "⚠️ Not connected",
        'partner_left': "🛑 Partner left",
        'premium_txt': "💎 Premium Packages:\n⭐39/24H ⭐149/3D ⭐249/5D ⭐379/7D ⭐499/14D ⭐799/30D",
        'premium_purchase_success': "🎉 Premium Activated!\nPackage: {package}\nDays: {days}",
        'help_txt': "💡 Help: /start",
        'pic_verify_msg': "📸 Send your photo:",
        'pic_verify_success': "🎉 Verified!",
        'edit_name': "✍️ Name",
        'edit_age': "✍️ Age",
        'verify_pic': "📸 Verify",
        'set_filter': "🎯 Filter",
        'gender_locked': "🔒 Gender locked: {gender}",
        'profile_complete': "✅ Profile complete!",
        'language_changed': "✅ Language: {language}",
        'select_new_lang': "🌐 Select language:",
        'settings_menu': "⚙️ Settings:",
        'welcome': "👋 Welcome!",
        'back': "🔙 Back",
    },
    'bangla': {
        'start': "👋 নাম লিখুন:",
        'find': "🚀 পার্টনার খুঁজুন",
        'next': "⏭️ পরবর্তী",
        'stop': "🛑 বন্ধ করুন",
        'profile': "⚙️ প্রোফাইল",
        'premium': "💎 প্রিমিয়াম",
        'help_btn': "❓ সাহায্য",
        'settings': "⚙️ সেটিংস",
        'change_lang': "🌐 ভাষা",
        'select_lang': "🗣️ ভাষা নির্বাচন:",
        'select_gender': "⚥ লিঙ্গ নির্বাচন:",
        'pic_verify_msg': "📸 ছবি পাঠান:",
        'pic_verify_success': "🎉 ভেরিফাইড!",
        'gender_locked': "🔒 লিঙ্গ লক: {gender}",
        'profile_complete': "✅ প্রোফাইল সম্পূর্ণ!",
        'language_changed': "✅ ভাষা: {language}",
        'welcome': "👋 স্বাগতম!",
    },
    'hindi': {
        'start': "👋 नाम लिखें:",
        'find': "🚀 साथी ढूंढें",
        'next': "⏭️ अगला",
        'stop': "🛑 बंद करें",
        'profile': "⚙️ प्रोफाइल",
        'premium': "💎 प्रीमियम",
        'help_btn': "❓ सहायता",
        'settings': "⚙️ सेटिंग्स",
        'change_lang': "🌐 भाषा",
        'select_lang': "🗣️ भाषा चुनें:",
        'select_gender': "⚥ लिंग चुनें:",
        'pic_verify_msg': "📸 फोटो भेजें:",
        'pic_verify_success': "🎉 सत्यापित!",
        'gender_locked': "🔒 लिंग लॉक: {gender}",
        'profile_complete': "✅ प्रोफाइल पूरा!",
        'language_changed': "✅ भाषा: {language}",
        'welcome': "👋 स्वागत है!",
    }
}

def get_msg(user_id: int, key: str, **kwargs) -> str:
    user_lang = users_profile.get(user_id, {}).get('lang', 'english')
    if user_lang not in MESSAGES:
        user_lang = 'english'
    msg = MESSAGES[user_lang].get(key, MESSAGES['english'].get(key, key))
    return msg.format(**kwargs) if kwargs else msg

def is_premium(user_id: int) -> bool:
    p = users_profile.get(user_id, {})
    expiry_str = p.get('premium_expiry')
    if expiry_str:
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
            return datetime.now() < expiry_date
        except:
            return False
    return False

def is_gender_locked(user_id: int) -> bool:
    p = users_profile.get(user_id, {})
    return all([p.get('name'), p.get('age'), p.get('gender'), p.get('looking_for'), p.get('verified')])

def main_menu(user_id: int):
    btn = lambda k: KeyboardButton(get_msg(user_id, k))
    return ReplyKeyboardMarkup([
        [btn('find'), btn('next')],
        [btn('stop'), btn('profile')],
        [btn('premium'), btn('settings')],
        [btn('help_btn')]
    ], resize_keyboard=True)

def lang_keyboard():
    kb = []
    row = []
    for i, lang in enumerate(AVAILABLE_LANGUAGES):
        row.append(InlineKeyboardButton(f"{lang['flag']} {lang['name']}", callback_data=f"lang_{lang['code']}"))
        if (i + 1) % 2 == 0:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    return InlineKeyboardMarkup(kb)

def gender_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👦 Male", callback_data="gender_male")],
        [InlineKeyboardButton("👧 Female", callback_data="gender_female")]
    ])

def looking_keyboard(user_id, prefix):
    kb = [
        [InlineKeyboardButton("👧 Girls", callback_data=f"{prefix}female")],
        [InlineKeyboardButton("👦 Boys", callback_data=f"{prefix}male")],
        [InlineKeyboardButton("🌍 Everyone", callback_data=f"{prefix}everyone")],
    ]
    if not is_premium(user_id):
        kb.append([InlineKeyboardButton("💎 Get Premium", callback_data="show_premium")])
    return InlineKeyboardMarkup(kb)

def premium_keyboard():
    kb = []
    row = []
    for i, (pid, pkg) in enumerate(PREMIUM_PACKAGES.items()):
        row.append(InlineKeyboardButton(f"⭐ {pkg['stars']} - {pkg['name']}", callback_data=f"buy_{pid}"))
        if (i + 1) % 2 == 0:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return InlineKeyboardMarkup(kb)

def settings_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(user_id, 'change_lang'), callback_data="change_lang")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users_profile:
        users_profile[uid] = {
            'name': None, 'age': None, 'lang': None, 'gender': None,
            'looking_for': 'everyone', 'verified': False, 'premium_expiry': None,
            'target_age_min': 18, 'target_age_max': 50
        }
        user_states[uid] = RegState.WAITING_NAME
        await update.message.reply_text(get_msg(uid, 'start'))
    else:
        await update.message.reply_text(get_msg(uid, 'already_reg'), reply_markup=main_menu(uid))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    
    if uid in user_states:
        state = user_states[uid]
        if state == RegState.WAITING_NAME:
            users_profile[uid]['name'] = text
            await update.message.reply_text(get_msg(uid, 'name_saved').format(text=text))
            user_states[uid] = RegState.WAITING_AGE
            return
        elif state == RegState.WAITING_AGE:
            if text.isdigit() and 15 <= int(text) <= 99:
                users_profile[uid]['age'] = int(text)
                await update.message.reply_text(get_msg(uid, 'select_lang'), reply_markup=lang_keyboard())
                user_states[uid] = RegState.WAITING_LANG
            else:
                await update.message.reply_text(get_msg(uid, 'invalid_age'))
            return
        elif state == RegState.WAITING_TARGET_AGE_MIN:
            if text.isdigit():
                users_profile[uid]['target_age_min'] = int(text)
                await update.message.reply_text(get_msg(uid, 'enter_max_age'))
                user_states[uid] = RegState.WAITING_TARGET_AGE_MAX
            return
        elif state == RegState.WAITING_TARGET_AGE_MAX:
            if text.isdigit():
                users_profile[uid]['target_age_max'] = int(text)
                del user_states[uid]
                await update.message.reply_text(get_msg(uid, 'filter_updated'), reply_markup=main_menu(uid))
            return
        elif state == RegState.WAITING_EDIT_NAME:
            users_profile[uid]['name'] = text
            del user_states[uid]
            await update.message.reply_text("✅ Name updated!", reply_markup=main_menu(uid))
            return
        elif state == RegState.WAITING_EDIT_AGE:
            if text.isdigit() and 15 <= int(text) <= 99:
                users_profile[uid]['age'] = int(text)
                del user_states[uid]
                await update.message.reply_text("✅ Age updated!", reply_markup=main_menu(uid))
            return
    
    cmd = text
    find_cmd = get_msg(uid, 'find')
    next_cmd = get_msg(uid, 'next')
    stop_cmd = get_msg(uid, 'stop')
    profile_cmd = get_msg(uid, 'profile')
    premium_cmd = get_msg(uid, 'premium')
    settings_cmd = get_msg(uid, 'settings')
    help_cmd = get_msg(uid, 'help_btn')
    
    if cmd in ["🚀 Find Partner", find_cmd]:
        if uid in active_chats:
            await update.message.reply_text(get_msg(uid, 'already_chat'))
            return
        waiting_room.append(uid)
        await update.message.reply_text(get_msg(uid, 'search_start'))
    elif cmd in ["🛑 Stop Chat", stop_cmd]:
        if uid in waiting_room:
            waiting_room.remove(uid)
        elif uid in active_chats:
            pid = active_chats[uid]
            del active_chats[uid]
            del active_chats[pid]
            await context.bot.send_message(pid, get_msg(pid, 'partner_stopped'))
        await update.message.reply_text(get_msg(uid, 'you_stopped'), reply_markup=main_menu(uid))
    elif cmd in ["⏭️ Next Partner", next_cmd]:
        if uid in active_chats:
            pid = active_chats[uid]
            del active_chats[uid]
            del active_chats[pid]
            await context.bot.send_message(pid, get_msg(pid, 'partner_left'))
        waiting_room.append(uid)
        await update.message.reply_text(get_msg(uid, 'search_start'))
    elif cmd in ["⚙️ Profile", profile_cmd]:
        p = users_profile[uid]
        await update.message.reply_text(get_msg(uid, 'profile_txt').format(
            name=p['name'], age=p['age'], lang=p['lang'], gender=p.get('gender', 'Not Set'),
            looking_for=p.get('looking_for', 'everyone'), status="✅" if p['verified'] else "❌",
            premium_status="✅" if is_premium(uid) else "❌"))
    elif cmd in ["💎 Premium", premium_cmd]:
        await update.message.reply_text(get_msg(uid, 'premium_txt'), reply_markup=premium_keyboard())
    elif cmd in ["⚙️ Settings", settings_cmd]:
        await update.message.reply_text(get_msg(uid, 'settings_menu'), reply_markup=settings_keyboard(uid))
    elif cmd in ["❓ Help", help_cmd]:
        await update.message.reply_text(get_msg(uid, 'help_txt'))
    elif uid in active_chats:
        await context.bot.send_message(active_chats[uid], text)
    else:
        await update.message.reply_text(get_msg(uid, 'searching'), reply_markup=main_menu(uid))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_states and user_states[uid] == RegState.WAITING_VERIFY_PIC:
        users_profile[uid]['verified'] = True
        del user_states[uid]
        await update.message.reply_text(get_msg(uid, 'pic_verify_success'), reply_markup=main_menu(uid))
    elif uid in active_chats:
        await context.bot.send_photo(active_chats[uid], update.message.photo[-1].file_id)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    
    if data.startswith("lang_"):
        lang = data.replace("lang_", "")
        users_profile[uid]['lang'] = lang
        await query.edit_message_text(get_msg(uid, 'language_changed').format(language=lang))
        if uid in user_states and user_states[uid] == RegState.WAITING_LANG:
            user_states[uid] = RegState.WAITING_GENDER
            await query.message.reply_text(get_msg(uid, 'select_gender'), reply_markup=gender_keyboard())
        return
    if data.startswith("gender_"):
        if is_gender_locked(uid):
            await query.message.reply_text(get_msg(uid, 'gender_locked').format(gender=users_profile[uid]['gender']))
            return
        gender = "Male" if "male" in data else "Female"
        users_profile[uid]['gender'] = gender
        await query.edit_message_text(get_msg(uid, 'select_looking'))
        await query.message.reply_text(get_msg(uid, 'select_looking'), reply_markup=looking_keyboard(uid, "look_"))
        user_states[uid] = RegState.WAITING_LOOKING
        return
    if data.startswith("look_"):
        looking = data.replace("look_", "")
        users_profile[uid]['looking_for'] = looking.capitalize()
        await query.edit_message_text(get_msg(uid, 'pic_verify_msg'))
        await query.message.reply_text(get_msg(uid, 'pic_verify_msg'))
        user_states[uid] = RegState.WAITING_VERIFY_PIC
        return
    if data == "edit_name":
        await query.edit_message_text("✍️ Send new name:")
        user_states[uid] = RegState.WAITING_EDIT_NAME
        return
    if data == "edit_age":
        await query.edit_message_text("🎂 Send new age:")
        user_states[uid] = RegState.WAITING_EDIT_AGE
        return
    if data == "verify_pic":
        await query.edit_message_text(get_msg(uid, 'pic_verify_msg'))
        user_states[uid] = RegState.WAITING_VERIFY_PIC
        return
    if data == "set_filter":
        await query.edit_message_text(get_msg(uid, 'enter_min_age'))
        user_states[uid] = RegState.WAITING_TARGET_AGE_MIN
        return
    if data == "change_lang":
        await query.edit_message_text(get_msg(uid, 'select_new_lang'), reply_markup=lang_keyboard())
        return
    if data == "back":
        await query.edit_message_text(get_msg(uid, 'welcome'))
        await query.message.reply_text(get_msg(uid, 'welcome'), reply_markup=main_menu(uid))
        return
    if data == "show_premium":
        await query.message.reply_text(get_msg(uid, 'premium_txt'), reply_markup=premium_keyboard())
        return
    if data.startswith("buy_"):
        pkg_id = data.replace("buy_", "")
        pkg = PREMIUM_PACKAGES.get(pkg_id)
        if pkg:
            await context.bot.send_invoice(uid, f"Mnuverse: {pkg['name']}", f"{pkg['days']} days", f"prem_{pkg_id}", "", "XTR", [LabeledPrice(pkg['name'], pkg['stars'])])
        return

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    if payload.startswith("prem_"):
        pkg_id = payload.replace("prem_", "")
        pkg = PREMIUM_PACKAGES.get(pkg_id)
        if pkg:
            expiry = datetime.now() + timedelta(days=pkg['days'])
            users_profile[uid]['premium_expiry'] = expiry.strftime("%Y-%m-%d %H:%M:%S")
            await update.message.reply_text(get_msg(uid, 'premium_purchase_success').format(package=pkg['name'], days=pkg['days']), reply_markup=main_menu(uid))

# ============ MAIN ============
async def main():
    print("🚀 Starting application...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ Bot is ready!")
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook"
    )

if __name__ == '__main__':
    asyncio.run(main())
