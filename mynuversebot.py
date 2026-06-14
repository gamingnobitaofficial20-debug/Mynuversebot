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
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found")

PORT = int(os.environ.get('PORT', 8080))

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

# ============ 3 LANGUAGES ============
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

# ============ MESSAGES (3 Languages) ============
MESSAGES = {
    'english': {
        'start': "👋 Welcome! Send your Name or Nickname:",
        'already_reg': "🤖 You are registered! Use menu below.",
        'find': "🚀 Find Partner",
        'next': "⏭️ Next Partner",
        'stop': "🛑 Stop Chat",
        'profile': "⚙️ My Profile",
        'premium': "💎 Premium",
        'help_btn': "❓ Help",
        'settings': "⚙️ Settings",
        'change_lang': "🌐 Change Language",
        'profile_txt': "⚙️ *Your Profile:*\n\n👤 Name: {name}\n🎂 Age: {age}\n🗣️ Language: {lang}\n⚥ Gender: {gender}\n🎯 Looking For: {looking_for}\n🛡️ Verified: {status}\n💎 Premium: {premium_status}\n📊 Today's Matches: {matches_used}/{matches_limit}",
        'partner_found': "🎉 *Partner Found!*\n\n👤 Name: {name}\n🎂 Age: {age}\n🗣️ Language: {lang}\n⚥ Gender: {gender}\n\nStart chatting!",
        'name_saved': "👍 Name saved: {text}\n\n🎂 Now enter your *Age* (numbers only, e.g., 22):",
        'select_lang': "🗣️ Select your chatting *Language*:",
        'select_gender': "⚥ Select your *Gender* (⚠️ This cannot be changed later):",
        'select_looking': "🎯 Who are you *looking for*?\n\n💡 *Free Users:* 5 preference matches/day, then unlimited random!\n💎 *Premium Users:* Unlimited preference matches!",
        'invalid_age': "⚠️ Please enter a valid age (15-99):",
        'enter_min_age': "🎯 Enter *Minimum Age* for partner (18-99):",
        'enter_max_age': "🎯 Enter *Maximum Age* for partner (18-99):",
        'filter_updated': "✅ Partner age filter updated!",
        'invalid_num': "⚠️ Please enter a valid number.",
        'already_chat': "⚠️ You are already in a chat!",
        'searching': "⏳ Searching for partner, please wait...",
        'search_start': "🔍 Searching for partner based on your preferences...",
        'search_cancel': "🛑 Partner search cancelled.",
        'you_stopped': "🛑 You stopped the chat.",
        'partner_stopped': "🛑 Your partner stopped the chat.",
        'not_connected': "⚠️ You are not connected to any chat.",
        'partner_left': "🛑 Your partner left the chat.",
        'premium_txt': "💎 *Premium VIP Membership*\n\n*Benefits:*\n✅ Unlimited preference matches\n✅ Priority matching\n✅ No daily limits\n\n*Packages:*\n⭐ 39 Stars - 24 Hours\n⭐ 149 Stars - 3 Days\n⭐ 249 Stars - 5 Days\n⭐ 379 Stars - 7 Days\n⭐ 499 Stars - 14 Days\n⭐ 799 Stars - 30 Days\n\nSelect your package:",
        'premium_purchase_success': "🎉 *Premium Activated!*\n\nPackage: {package}\nDuration: {days} days\nExpires: {expiry}\n\n✨ Unlimited preference matches unlocked!",
        'help_txt': "💡 *Help Guide*\n\n*Free Users:*\n• 5 preference matches per day\n• After limit, unlimited random matches\n\n*Premium Users:*\n• Unlimited preference matches\n• Priority matching\n\n• Gender is permanently locked after profile completion\n• Change language anytime in Settings",
        'start_chat_alert': "⚠️ Tap 'Find Partner' to start chatting.",
        'pic_verify_msg': "📸 *Face Verification*\n\nSend a clear photo of yourself:",
        'pic_verify_success': "🎉 Thank you! Your profile is VERIFIED!",
        'edit_name': "✍️ Edit Name",
        'edit_age': "✍️ Edit Age",
        'verify_pic': "📸 Verify Profile",
        'set_filter': "🎯 Set Age Filter",
        'gender_locked': "🔒 *Gender Locked*\n\nYour gender ({gender}) is permanently set and cannot be changed.",
        'gender_permanently_locked': "⚠️ *Cannot Change Gender*\n\nYour gender ({gender}) was permanently set when you completed your profile.",
        'profile_complete': "✅ *Profile Complete!*\n\nYour gender ({gender}) is now permanently locked.\n\nTap 'Find Partner' to start matching!",
        'gender_limit_reached': "⚠️ *Daily Limit Reached!*\n\nYou've used all 5 preference matches for today.\n\n✅ Now in *random mode* (unlimited matches)!\n💎 Upgrade to Premium for unlimited preference matches!",
        'random_mode_active': "🔄 *Random Mode Active*\n\nYou are now in random match mode (unlimited matches with anyone)!\n💎 Get Premium for gender preference matches!",
        'remaining_matches': "📊 Remaining preference matches today: {remaining}",
        'language_changed': "✅ Language changed to: {language}",
        'select_new_lang': "🌐 *Select your preferred language:*",
        'settings_menu': "⚙️ *Settings Menu*",
        'back_to_menu': "🔙 Back to Main Menu",
        'premium_only_feature': "🔒 *Premium Feature*\n\n💎 Upgrade to Premium for unlimited preference matches!",
        'welcome': "👋 Welcome to Mnuverse Bot!",
        'back': "🔙 Back",
        'male': "Male", 'female': "Female", 'gay': "Gay", 'lesbian': "Lesbian", 'everyone': "Everyone"
    },
    'bangla': {
        'start': "👋 স্বাগতম! আপনার নাম লিখুন:",
        'already_reg': "🤖 আপনি রেজিস্টার্ড! নিচের মেনু ব্যবহার করুন।",
        'find': "🚀 পার্টনার খুঁজুন",
        'next': "⏭️ পরবর্তী পার্টনার",
        'stop': "🛑 চ্যাট বন্ধ করুন",
        'profile': "⚙️ আমার প্রোফাইল",
        'premium': "💎 প্রিমিয়াম",
        'help_btn': "❓ সাহায্য",
        'settings': "⚙️ সেটিংস",
        'change_lang': "🌐 ভাষা পরিবর্তন",
        'profile_txt': "⚙️ *আপনার প্রোফাইল:*\n\n👤 নাম: {name}\n🎂 বয়স: {age}\n🗣️ ভাষা: {lang}\n⚥ লিঙ্গ: {gender}\n🎯 খুঁজছেন: {looking_for}\n🛡️ ভেরিফাইড: {status}\n💎 প্রিমিয়াম: {premium_status}\n📊 আজকের ম্যাচ: {matches_used}/{matches_limit}",
        'partner_found': "🎉 *পার্টনার পাওয়া গেছে!*\n\n👤 নাম: {name}\n🎂 বয়স: {age}\n🗣️ ভাষা: {lang}\n⚥ লিঙ্গ: {gender}\n\nচ্যাট শুরু করুন!",
        'name_saved': "👍 নাম সেভ: {text}\n\n🎂 এখন আপনার *বয়স* লিখুন:",
        'select_lang': "🗣️ আপনার *ভাষা* নির্বাচন করুন:",
        'select_gender': "⚥ আপনার *লিঙ্গ* নির্বাচন করুন (⚠️ পরে পরিবর্তন করা যাবে না):",
        'select_looking': "🎯 আপনি কেমন *পার্টনার* খুঁজছেন?\n\n💡 *ফ্রি ইউজার:* ৫টি প্রেফারেন্স ম্যাচ/দিন, তারপর আনলিমিটেড র্যান্ডম!\n💎 *প্রিমিয়াম:* আনলিমিটেড প্রেফারেন্স ম্যাচ!",
        'invalid_age': "⚠️ সঠিক বয়স দিন (১৫-৯৯):",
        'enter_min_age': "🎯 পার্টনারের *সর্বনিম্ন বয়স* (১৮-৯৯):",
        'enter_max_age': "🎯 পার্টনারের *সর্বোচ্চ বয়স* (১৮-৯৯):",
        'filter_updated': "✅ বয়স ফিল্টার আপডেট!",
        'invalid_num': "⚠️ সঠিক সংখ্যা দিন।",
        'already_chat': "⚠️ আপনি ইতিমধ্যে চ্যাটে!",
        'searching': "⏳ পার্টনার খোঁজা হচ্ছে...",
        'search_start': "🔍 আপনার পছন্দ অনুযায়ী পার্টনার খোঁজা হচ্ছে...",
        'search_cancel': "🛑 পার্টনার খোঁজা বাতিল।",
        'you_stopped': "🛑 আপনি চ্যাট বন্ধ করেছেন।",
        'partner_stopped': "🛑 আপনার পার্টনার চ্যাট বন্ধ করেছে।",
        'not_connected': "⚠️ আপনি কোনো চ্যাটে নাই।",
        'partner_left': "🛑 আপনার পার্টনার চলে গেছে।",
        'premium_txt': "💎 *প্রিমিয়াম ভিআইপি মেম্বারশিপ*\n\n*সুবিধা:*\n✅ আনলিমিটেড প্রেফারেন্স ম্যাচ\n✅ প্রায়োরিটি ম্যাচিং\n✅ কোন দৈনিক লিমিট নেই\n\n*প্যাকেজ:*\n⭐ ৩৯ স্টার - ২৪ ঘন্টা\n⭐ ১৪৯ স্টার - ৩ দিন\n⭐ ২৪৯ স্টার - ৫ দিন\n⭐ ৩৭৯ স্টার - ৭ দিন\n⭐ ৪৯৯ স্টার - ১৪ দিন\n⭐ ৭৯৯ স্টার - ৩০ দিন\n\nপ্যাকেজ নির্বাচন করুন:",
        'premium_purchase_success': "🎉 *প্রিমিয়াম সক্রিয়!*\n\nপ্যাকেজ: {package}\nমেয়াদ: {days} দিন\nমেয়াদ শেষ: {expiry}\n\n✨ আনলিমিটেড প্রেফারেন্স ম্যাচ আনলক!",
        'help_txt': "💡 *সাহায্য গাইড*\n\n*ফ্রি ইউজার:*\n• প্রতিদিন ৫টি প্রেফারেন্স ম্যাচ\n• লিমিট শেষে আনলিমিটেড র্যান্ডম ম্যাচ\n\n*প্রিমিয়াম ইউজার:*\n• আনলিমিটেড প্রেফারেন্স ম্যাচ\n• প্রায়োরিটি ম্যাচিং\n\n• প্রোফাইল সম্পূর্ণ হলে লিঙ্গ লক হয়ে যায়\n• সেটিংস থেকে যেকোনো সময় ভাষা পরিবর্তন করুন",
        'start_chat_alert': "⚠️ 'পার্টনার খুঁজুন' এ ক্লিক করুন।",
        'pic_verify_msg': "📸 *ফেস ভেরিফিকেশন*\n\nআপনার একটি ছবি পাঠান:",
        'pic_verify_success': "🎉 আপনার প্রোফাইল ভেরিফাইড!",
        'edit_name': "✍️ নাম পরিবর্তন",
        'edit_age': "✍️ বয়স পরিবর্তন",
        'verify_pic': "📸 ভেরিফাই",
        'set_filter': "🎯 বয়স ফিল্টার",
        'gender_locked': "🔒 *লিঙ্গ লক*\n\nআপনার লিঙ্গ ({gender}) স্থায়ীভাবে লক করা হয়েছে।",
        'gender_permanently_locked': "⚠️ *লিঙ্গ পরিবর্তন করা যাবে না*\n\nআপনার লিঙ্গ ({gender}) প্রোফাইল সম্পূর্ণ করার সময় লক করা হয়েছে।",
        'profile_complete': "✅ *প্রোফাইল সম্পূর্ণ!*\n\nআপনার লিঙ্গ ({gender}) স্থায়ীভাবে লক করা হয়েছে।\n\n'পার্টনার খুঁজুন' এ ক্লিক করুন!",
        'gender_limit_reached': "⚠️ *দৈনিক লিমিট শেষ!*\n\nআপনি আজকের ৫টি প্রেফারেন্স ম্যাচ ব্যবহার করেছেন।\n\n✅ এখন *র্যান্ডম মোডে* (সবার সাথে আনলিমিটেড ম্যাচ)!\n💎 প্রিমিয়াম নিন আনলিমিটেড প্রেফারেন্স ম্যাচের জন্য!",
        'random_mode_active': "🔄 *র্যান্ডম মোড সক্রিয়*\n\nআপনি এখন র্যান্ডম মোডে আছেন (সবার সাথে আনলিমিটেড ম্যাচ)!\n💎 প্রিমিয়াম নিন জেন্ডার প্রেফারেন্স ম্যাচের জন্য!",
        'remaining_matches': "📊 আজ বাকি প্রেফারেন্স ম্যাচ: {remaining}",
        'language_changed': "✅ ভাষা পরিবর্তন: {language}",
        'select_new_lang': "🌐 *আপনার পছন্দের ভাষা নির্বাচন করুন:*",
        'settings_menu': "⚙️ *সেটিংস মেনু*",
        'back_to_menu': "🔙 মূল মেনু",
        'premium_only_feature': "🔒 *প্রিমিয়াম ফিচার*\n\n💎 প্রিমিয়াম নিন আনলিমিটেড প্রেফারেন্স ম্যাচের জন্য!",
        'welcome': "👋 Mnuverse Bot-এ স্বাগতম!",
        'back': "🔙 পিছনে",
        'male': "পুরুষ", 'female': "মহিলা", 'gay': "গে", 'lesbian': "লেসবিয়ান", 'everyone': "সবাই"
    },
    'hindi': {
        'start': "👋 स्वागत है! अपना नाम लिखें:",
        'already_reg': "🤖 आप रजिस्टर्ड हैं! नीचे मेनू देखें।",
        'find': "🚀 साथी ढूंढें",
        'next': "⏭️ अगला साथी",
        'stop': "🛑 चैट बंद करें",
        'profile': "⚙️ मेरा प्रोफाइल",
        'premium': "💎 प्रीमियम",
        'help_btn': "❓ सहायता",
        'settings': "⚙️ सेटिंग्स",
        'change_lang': "🌐 भाषा बदलें",
        'profile_txt': "⚙️ *आपका प्रोफाइल:*\n\n👤 नाम: {name}\n🎂 उम्र: {age}\n🗣️ भाषा: {lang}\n⚥ लिंग: {gender}\n🎯 ढूंढ रहे: {looking_for}\n🛡️ सत्यापित: {status}\n💎 प्रीमियम: {premium_status}\n📊 आज के मैच: {matches_used}/{matches_limit}",
        'partner_found': "🎉 *साथी मिल गया!*\n\n👤 नाम: {name}\n🎂 उम्र: {age}\n🗣️ भाषा: {lang}\n⚥ लिंग: {gender}\n\nचैट शुरू करें!",
        'name_saved': "👍 नाम सहेजा: {text}\n\n🎂 अब अपनी *उम्र* लिखें:",
        'select_lang': "🗣️ अपनी *भाषा* चुनें:",
        'select_gender': "⚥ अपना *लिंग* चुनें (⚠️ बाद में नहीं बदल सकते):",
        'select_looking': "🎯 किसे *ढूंढ रहे* हैं?\n\n💡 *मुफ्त यूजर:* 5 पसंद मैच/दिन, फिर असीमित रैंडम!\n💎 *प्रीमियम:* असीमित पसंद मैच!",
        'invalid_age': "⚠️ सही उम्र दें (15-99):",
        'enter_min_age': "🎯 साथी की *न्यूनतम उम्र* (18-99):",
        'enter_max_age': "🎯 साथी की *अधिकतम उम्र* (18-99):",
        'filter_updated': "✅ उम्र फ़िल्टर अपडेट!",
        'invalid_num': "⚠️ सही संख्या दें।",
        'already_chat': "⚠️ आप पहले से चैट में हैं!",
        'searching': "⏳ साथी ढूंढ रहे...",
        'search_start': "🔍 आपकी पसंद के अनुसार साथी ढूंढ रहे...",
        'search_cancel': "🛑 साथी ढूंढना रद्द।",
        'you_stopped': "🛑 आपने चैट बंद की।",
        'partner_stopped': "🛑 आपके साथी ने चैट बंद की।",
        'not_connected': "⚠️ आप किसी चैट में नहीं हैं।",
        'partner_left': "🛑 आपका साथी चला गया।",
        'premium_txt': "💎 *प्रीमियम वीआईपी सदस्यता*\n\n*लाभ:*\n✅ असीमित पसंद मैच\n✅ प्राथमिकता मैचिंग\n✅ कोई दैनिक सीमा नहीं\n\n*पैकेज:*\n⭐ 39 स्टार - 24 घंटे\n⭐ 149 स्टार - 3 दिन\n⭐ 249 स्टार - 5 दिन\n⭐ 379 स्टार - 7 दिन\n⭐ 499 स्टार - 14 दिन\n⭐ 799 स्टार - 30 दिन\n\nपैकेज चुनें:",
        'premium_purchase_success': "🎉 *प्रीमियम सक्रिय!*\n\nपैकेज: {package}\nअवधि: {days} दिन\nसमाप्ति: {expiry}\n\n✨ असीमित पसंद मैच अनलॉक!",
        'help_txt': "💡 *सहायता गाइड*\n\n*मुफ्त यूजर:*\n• प्रतिदिन 5 पसंद मैच\n• सीमा के बाद असीमित रैंडम मैच\n\n*प्रीमियम यूजर:*\n• असीमित पसंद मैच\n• प्राथमिकता मैचिंग\n\n• प्रोफाइल पूरा होने पर लिंग लॉक हो जाता है\n• सेटिंग्स से कभी भी भाषा बदलें",
        'start_chat_alert': "⚠️ 'साथी ढूंढें' पर क्लिक करें।",
        'pic_verify_msg': "📸 *चेहरा सत्यापन*\n\nअपनी फोटो भेजें:",
        'pic_verify_success': "🎉 आपका प्रोफाइल सत्यापित!",
        'edit_name': "✍️ नाम बदलें",
        'edit_age': "✍️ उम्र बदलें",
        'verify_pic': "📸 सत्यापित",
        'set_filter': "🎯 उम्र फ़िल्टर",
        'gender_locked': "🔒 *लिंग लॉक*\n\nआपका लिंग ({gender}) स्थायी रूप से लॉक किया गया है।",
        'gender_permanently_locked': "⚠️ *लिंग नहीं बदल सकते*\n\nआपका लिंग ({gender}) प्रोफाइल पूरा होने पर लॉक किया गया था।",
        'profile_complete': "✅ *प्रोफाइल पूरा!*\n\nआपका लिंग ({gender}) स्थायी रूप से लॉक किया गया है।\n\n'साथी ढूंढें' पर क्लिक करें!",
        'gender_limit_reached': "⚠️ *दैनिक सीमा समाप्त!*\n\nआपने आज के सभी 5 पसंद मैच उपयोग कर लिए।\n\n✅ अब *रैंडम मोड* में (सबके साथ असीमित मैच)!\n💎 प्रीमियम लें असीमित पसंद मैच के लिए!",
        'random_mode_active': "🔄 *रैंडम मोड सक्रिय*\n\nअब आप रैंडम मोड में हैं (सबके साथ असीमित मैच)!\n💎 प्रीमियम लें लिंग पसंद मैच के लिए!",
        'remaining_matches': "📊 आज बचे पसंद मैच: {remaining}",
        'language_changed': "✅ भाषा बदली: {language}",
        'select_new_lang': "🌐 *अपनी पसंदीदा भाषा चुनें:*",
        'settings_menu': "⚙️ *सेटिंग्स मेनू*",
        'back_to_menu': "🔙 मुख्य मेनू",
        'premium_only_feature': "🔒 *प्रीमियम फीचर*\n\n💎 प्रीमियम लें असीमित पसंद मैच के लिए!",
        'welcome': "👋 Mnuverse Bot में स्वागत है!",
        'back': "🔙 वापस",
        'male': "पुरुष", 'female': "महिला", 'gay': "गे", 'lesbian': "लेस्बियन", 'everyone': "सभी"
    }
}

# ============ HELPER FUNCTIONS ============
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

def get_today_matches(user_id: int) -> int:
    if user_id not in user_match_tracking:
        user_match_tracking[user_id] = {'count': 0, 'date': datetime.now().date()}
    today = datetime.now().date()
    if user_match_tracking[user_id]['date'] != today:
        user_match_tracking[user_id] = {'count': 0, 'date': today}
    return user_match_tracking[user_id]['count']

def get_match_limit(user_id: int, looking_for: str) -> int:
    if is_premium(user_id):
        return float('inf')
    limits = {'male': 5, 'female': 5, 'gay': 3, 'lesbian': 3, 'everyone': float('inf')}
    return limits.get(looking_for.lower(), 5)

def can_use_preference_match(user_id: int, looking_for: str) -> bool:
    if is_premium(user_id) or looking_for.lower() == 'everyone':
        return True
    return get_today_matches(user_id) < get_match_limit(user_id, looking_for)

def increment_match_count(user_id: int):
    if is_premium(user_id):
        return
    today = datetime.now().date()
    if user_id not in user_match_tracking:
        user_match_tracking[user_id] = {'count': 0, 'date': today}
    if user_match_tracking[user_id]['date'] != today:
        user_match_tracking[user_id] = {'count': 0, 'date': today}
    user_match_tracking[user_id]['count'] += 1

def get_remaining_matches(user_id: int, looking_for: str) -> int:
    if is_premium(user_id) or looking_for.lower() == 'everyone':
        return float('inf')
    limit = get_match_limit(user_id, looking_for)
    used = get_today_matches(user_id)
    return max(0, limit - used)

# ============ KEYBOARDS ============
def main_menu(user_id: int) -> ReplyKeyboardMarkup:
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
    kb = []
    if is_premium(user_id):
        kb = [
            [InlineKeyboardButton("👧 Girls", callback_data=f"{prefix}female")],
            [InlineKeyboardButton("👦 Boys", callback_data=f"{prefix}male")],
            [InlineKeyboardButton("🏳️‍🌈 Gay", callback_data=f"{prefix}gay")],
            [InlineKeyboardButton("🏳️‍🌈 Lesbian", callback_data=f"{prefix}lesbian")],
            [InlineKeyboardButton("🌍 Everyone", callback_data=f"{prefix}everyone")]
        ]
    else:
        kb = [
            [InlineKeyboardButton("👧 Girls (5/day)", callback_data=f"{prefix}female")],
            [InlineKeyboardButton("👦 Boys (5/day)", callback_data=f"{prefix}male")],
            [InlineKeyboardButton("🏳️‍🌈 Gay (3/day)", callback_data=f"{prefix}gay")],
            [InlineKeyboardButton("🏳️‍🌈 Lesbian (3/day)", callback_data=f"{prefix}lesbian")],
            [InlineKeyboardButton("🌍 Random (Unlimited)", callback_data=f"{prefix}everyone")],
            [InlineKeyboardButton("💎 Get Premium", callback_data="show_premium")]
        ]
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
        [InlineKeyboardButton(get_msg(user_id, 'back'), callback_data="back")]
    ])

def profile_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(get_msg(user_id, 'edit_name'), callback_data="edit_name"),
         InlineKeyboardButton(get_msg(user_id, 'edit_age'), callback_data="edit_age")],
        [InlineKeyboardButton(get_msg(user_id, 'verify_pic'), callback_data="verify_pic"),
         InlineKeyboardButton(get_msg(user_id, 'set_filter'), callback_data="set_filter")]
    ])

# ============ MATCHING ============
async def match_users(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    user = users_profile[user_id]
    user_looking = user.get('looking_for', 'everyone').lower()
    user_can_prefer = can_use_preference_match(user_id, user_looking)
    
    for pid in waiting_room[:]:
        if pid == user_id:
            continue
        partner = users_profile.get(pid)
        if not partner:
            waiting_room.remove(pid)
            continue
        
        if not (user['target_age_min'] <= partner['age'] <= user['target_age_max'] and
                partner['target_age_min'] <= user['age'] <= partner['target_age_max']):
            continue
        
        if user['lang'] != partner['lang']:
            continue
        
        partner_looking = partner.get('looking_for', 'everyone').lower()
        partner_can_prefer = can_use_preference_match(pid, partner_looking)
        
        gender_match = False
        if not user_can_prefer or not partner_can_prefer or user_looking == 'everyone' or partner_looking == 'everyone':
            gender_match = True
        else:
            user_gen = user.get('gender', '').lower()
            partner_gen = partner.get('gender', '').lower()
            if user_looking == 'female' and partner_looking == 'male' and user_gen == 'male' and partner_gen == 'female':
                gender_match = True
            elif user_looking == 'male' and partner_looking == 'female' and user_gen == 'female' and partner_gen == 'male':
                gender_match = True
            elif user_looking == 'gay' and partner_looking == 'gay' and user_gen == 'male' and partner_gen == 'male':
                gender_match = True
            elif user_looking == 'lesbian' and partner_looking == 'lesbian' and user_gen == 'female' and partner_gen == 'female':
                gender_match = True
        
        if gender_match:
            waiting_room.remove(pid)
            if user_id in waiting_room:
                waiting_room.remove(user_id)
            
            if user_can_prefer and user_looking != 'everyone':
                increment_match_count(user_id)
            if partner_can_prefer and partner_looking != 'everyone':
                increment_match_count(pid)
            
            active_chats[user_id] = pid
            active_chats[pid] = user_id
            
            await context.bot.send_message(user_id, get_msg(user_id, 'partner_found').format(
                name=partner['name'], age=partner['age'], lang=partner['lang'], gender=partner.get('gender', '')), parse_mode='Markdown')
            await context.bot.send_message(pid, get_msg(pid, 'partner_found').format(
                name=user['name'], age=user['age'], lang=user['lang'], gender=user.get('gender', '')), parse_mode='Markdown')
            return True
    return False

# ============ HANDLERS ============
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
            if text.isdigit() and 18 <= int(text) <= 99:
                users_profile[uid]['target_age_min'] = int(text)
                await update.message.reply_text(get_msg(uid, 'enter_max_age'))
                user_states[uid] = RegState.WAITING_TARGET_AGE_MAX
            return
        elif state == RegState.WAITING_TARGET_AGE_MAX:
            if text.isdigit() and int(text) > users_profile[uid]['target_age_min']:
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
        looking_for = users_profile[uid].get('looking_for', 'everyone')
        if not can_use_preference_match(uid, looking_for) and looking_for.lower() != 'everyone':
            await update.message.reply_text(get_msg(uid, 'gender_limit_reached'))
            users_profile[uid]['looking_for'] = 'everyone'
            await update.message.reply_text(get_msg(uid, 'random_mode_active'))
        remaining = get_remaining_matches(uid, looking_for)
        if 0 < remaining < float('inf'):
            await update.message.reply_text(get_msg(uid, 'remaining_matches').format(remaining=remaining))
        waiting_room.append(uid)
        await update.message.reply_text(get_msg(uid, 'search_start'))
        await match_users(uid, context)
    elif cmd in ["🛑 Stop Chat", stop_cmd]:
        if uid in waiting_room:
            waiting_room.remove(uid)
            await update.message.reply_text(get_msg(uid, 'search_cancel'))
        elif uid in active_chats:
            pid = active_chats[uid]
            del active_chats[uid]
            del active_chats[pid]
            await context.bot.send_message(pid, get_msg(pid, 'partner_stopped'))
            await update.message.reply_text(get_msg(uid, 'you_stopped'), reply_markup=main_menu(uid))
        else:
            await update.message.reply_text(get_msg(uid, 'not_connected'))
    elif cmd in ["⏭️ Next Partner", next_cmd]:
        if uid in active_chats:
            pid = active_chats[uid]
            del active_chats[uid]
            del active_chats[pid]
            await context.bot.send_message(pid, get_msg(pid, 'partner_left'))
        waiting_room.append(uid)
        await match_users(uid, context)
    elif cmd in ["⚙️ My Profile", profile_cmd]:
        p = users_profile[uid]
        looking_for = p.get('looking_for', 'everyone')
        matches_used = str(get_today_matches(uid)) if not is_premium(uid) else "∞"
        limit = get_match_limit(uid, looking_for)
        matches_limit = str(limit) if limit != float('inf') else "∞"
        await update.message.reply_text(get_msg(uid, 'profile_txt').format(
            name=p['name'], age=p['age'], lang=p['lang'], gender=p.get('gender', 'Not Set'),
            looking_for=looking_for.capitalize(), status="✅" if p['verified'] else "❌",
            premium_status="✅ Premium" if is_premium(uid) else "❌ Free",
            matches_used=matches_used, matches_limit=matches_limit), parse_mode='Markdown', reply_markup=profile_keyboard(uid))
    elif cmd in ["💎 Premium", premium_cmd]:
        await update.message.reply_text(get_msg(uid, 'premium_txt'), parse_mode='Markdown', reply_markup=premium_keyboard())
    elif cmd in ["⚙️ Settings", settings_cmd]:
        await update.message.reply_text(get_msg(uid, 'settings_menu'), reply_markup=settings_keyboard(uid))
    elif cmd in ["❓ Help", help_cmd]:
        await update.message.reply_text(get_msg(uid, 'help_txt'), parse_mode='Markdown')
    elif uid in active_chats:
        await context.bot.send_message(active_chats[uid], text)
    else:
        await update.message.reply_text(get_msg(uid, 'searching'), reply_markup=main_menu(uid))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_states and user_states[uid] == RegState.WAITING_VERIFY_PIC:
        users_profile[uid]['verified'] = True
        del user_states[uid]
        if is_gender_locked(uid):
            await update.message.reply_text(get_msg(uid, 'profile_complete').format(gender=users_profile[uid]['gender']), parse_mode='Markdown', reply_markup=main_menu(uid))
        else:
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
        await query.edit_message_text(get_msg(uid, 'select_looking').format(gender_limit=5))
        await query.message.reply_text(get_msg(uid, 'select_looking').format(gender_limit=5), reply_markup=looking_keyboard(uid, "look_"))
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
        await query.edit_message_text("✍️ Send your new name:")
        user_states[uid] = RegState.WAITING_EDIT_NAME
        return
    if data == "edit_age":
        await query.edit_message_text("🎂 Send your new age (15-99):")
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
        await query.message.reply_text(get_msg(uid, 'premium_txt'), parse_mode='Markdown', reply_markup=premium_keyboard())
        return
    if data.startswith("buy_"):
        pkg_id = data.replace("buy_", "")
        pkg = PREMIUM_PACKAGES.get(pkg_id)
        if pkg:
            await context.bot.send_invoice(uid, f"Mnuverse: {pkg['name']}", f"{pkg['days']} days premium access", f"prem_{pkg_id}", "", "XTR", [LabeledPrice(pkg['name'], pkg['stars'])])
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
            await update.message.reply_text(get_msg(uid, 'premium_purchase_success').format(
                package=pkg['name'], days=pkg['days'], expiry=expiry.strftime('%d %b %Y')), parse_mode='Markdown', reply_markup=main_menu(uid))

# ============ MAIN ============
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("="*50)
    print("🤖 Mnuverse Bot Started Successfully!")
    print(f"📊 Languages: English, Bangla, Hindi")
    print("✅ Premium System: 6 packages")
    print("✅ Free Users: 5 preference matches/day → unlimited random")
    print("✅ Gender Lock: Active after profile completion")
    print("="*50)
    
    # For Render - use webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook"
    )

if __name__ == '__main__':
    main()
