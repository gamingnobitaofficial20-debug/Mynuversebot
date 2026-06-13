import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, filters, ContextTypes, ConversationHandler
)
from flask import Flask
import threading

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Bot token from environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

# Conversation states
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

# User data storage
users_profile: Dict[int, dict] = {}
waiting_room: List[int] = []
active_chats: Dict[int, int] = {}
user_states: Dict[int, RegState] = {}

# Track matches per user with gender preference
user_match_tracking: Dict[int, Dict] = {}

# 12 Languages with their codes and flags
AVAILABLE_LANGUAGES = [
    {"code": "english", "name": "English", "flag": "🇬🇧"},
    {"code": "bangla", "name": "Bangla", "flag": "🇧🇩"},
    {"code": "hindi", "name": "Hindi", "flag": "🇮🇳"},
    {"code": "japanese", "name": "Japanese", "flag": "🇯🇵"},
    {"code": "russian", "name": "Russian", "flag": "🇷🇺"},
    {"code": "arabic", "name": "Arabic", "flag": "🇸🇦"},
    {"code": "spanish", "name": "Spanish", "flag": "🇪🇸"},
    {"code": "french", "name": "French", "flag": "🇫🇷"},
    {"code": "korean", "name": "Korean", "flag": "🇰🇷"},
    {"code": "german", "name": "German", "flag": "🇩🇪"},
    {"code": "italian", "name": "Italian", "flag": "🇮🇹"},
    {"code": "portuguese", "name": "Portuguese", "flag": "🇵🇹"}
]

# Premium packages
PREMIUM_PACKAGES = {
    "pkg_24h": {"name": "24 Hours Membership", "days": 1, "stars": 39},
    "pkg_3d": {"name": "3 Days Membership", "days": 3, "stars": 149},
    "pkg_5d": {"name": "5 Days Membership", "days": 5, "stars": 249},
    "pkg_7d": {"name": "7 Days Membership", "days": 7, "stars": 379},
    "pkg_14d": {"name": "14 Days Membership", "days": 14, "stars": 499},
    "pkg_1m": {"name": "1 Month Membership", "days": 30, "stars": 799}
}

# Free user limits
FREE_USER_GENDER_MATCH_LIMITS = {
    "male": 5,
    "female": 5,
    "gay": 3,
    "lesbian": 3,
    "everyone": float('inf')
}
# Complete multilingual messages dictionary - First 3 Languages
MESSAGES = {
    'english': {
        'welcome': "👋 Welcome to Mnuverse Bot!",
        'start': "👋 Welcome to Mnuverse Bot!\n\nBefore starting, please set up your profile.\n\n📝 Please enter your Name or Nickname:",
        'already_reg': "🤖 You are already registered! Use the menu below.",
        'find': "🚀 Find Partner",
        'next': "⏭️ Next Partner",
        'stop': "🛑 Stop Chat",
        'profile': "⚙️ My Profile",
        'premium': "💎 Premium",
        'help_btn': "❓ Help",
        'settings': "⚙️ Settings",
        'change_lang': "🌐 Change Language",
        'profile_txt': "⚙️ **Your Profile:**\n\n👤 Name: {name}\n🎂 Age: {age}\n🗣️ Language: {lang}\n⚥ Gender: {gender} 🔒\n🎯 Looking For: {looking_for}\n🛡️ Verification: {status}\n💎 Premium: {premium_status}\n🎯 Age Range: {min_age}-{max_age}\n\n📊 **Matches:** {gender_matches_used}/{gender_matches_limit}\n\n_Gender is locked permanently_",
        'partner_found': "🎉 **Partner Found!**\n👤 Name: {name}\n🎂 Age: {age}\n🗣️ Language: {lang}\n⚥ Gender: {gender}\n\nStart chatting!",
        'name_saved': "👍 Name saved: {text}\n\n🎂 Now enter your **Age** (numbers only, e.g., 22):",
        'select_lang': "🗣️ Select your chatting **Language**:",
        'select_gender': "⚥ Select your **Gender** (This cannot be changed later):",
        'select_looking': "🎯 Who are you **looking for**?\n\n💡 **Free Users:** {gender_limit} preference matches, then unlimited random!\n💎 **Premium:** Unlimited matches!",
        'invalid_age': "⚠️ Please enter a valid age (15-99):",
        'invalid_lang_btn': "⚠️ Please select a language from the buttons.",
        'enter_min_age': "🎯 Enter **Minimum Age** for partner (e.g., 18):",
        'enter_max_age': "🎯 Enter **Maximum Age** for partner (e.g., 30):",
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
        'premium_txt': "💎 **Premium VIP Membership**\n\n**Benefits:**\n✅ Unlimited matches\n✅ Priority queue\n✅ Advanced filters\n\n**Packages:**\n⭐ 39 - 24H | ⭐ 149 - 3D\n⭐ 249 - 5D | ⭐ 379 - 7D\n⭐ 499 - 14D | ⭐ 799 - 30D\n\nSelect package:",
        'premium_purchase_success': "🎉 **Premium Activated!**\n\nPackage: {package}\nDuration: {days} days\nExpires: {expiry}\n\n✨ Unlimited matches unlocked!",
        'help_txt': "💡 **Help Guide:**\n\n**Free:** {limit} preference matches → unlimited random\n**Premium:** Unlimited preference matches\n\n• Gender is permanently locked\n• Change language anytime in Settings\n• Report inappropriate behavior",
        'start_chat_alert': "⚠️ Tap 'Find Partner' to start chatting.",
        'pic_verify_msg': "📸 **Face Verification**\n\nSend a clear photo of yourself:",
        'pic_verify_success': "🎉 Thank you! Your profile is VERIFIED!",
        'edit_name': "✍️ Edit Name",
        'edit_age': "✍️ Edit Age",
        'verify_pic': "📸 Verify",
        'set_filter': "🎯 Age Filter",
        'gender_locked': "🔒 **Gender Locked**\n\nYour gender ({gender}) is permanently set and cannot be changed.",
        'gender_permanently_locked': "⚠️ **Cannot Change Gender**\n\nYour gender ({gender}) was permanently set when you completed your profile.",
        'profile_complete': "✅ **Profile Complete!**\n\nYour gender ({gender}) is now permanently locked.\n\nTap 'Find Partner' to start matching!",
        'gender_limit_reached': "⚠️ **Limit Reached!**\n\nYou've used all {limit} preference matches.\n\n✅ Now in **random mode** (unlimited)!\n💎 Upgrade to Premium for unlimited preference matches!",
        'random_mode': "🔄 **Random Mode Active**\n\nUnlimited random matches!\n💎 Get Premium for preference matches!",
        'remaining_matches': "📊 Remaining preference matches: {remaining}",
        'language_changed': "✅ Language changed to: {language}\n\nAll messages will now appear in {language}.",
        'select_new_lang': "🌐 **Select your preferred language:**\n\nYou can change language anytime.",
        'settings_menu': "⚙️ **Settings Menu**\n\nChoose an option below:",
        'back_to_menu': "🔙 Back to Main Menu"
    },
    
    'bangla': {
        'welcome': "👋 Mnuverse Bot-এ স্বাগতম!",
        'start': "👋 Mnuverse Bot-এ স্বাগতম!\n\nশুরু করার আগে আপনার প্রোফাইল সেটআপ করুন।\n\n📝 আপনার নাম বা ডাকনাম লিখুন:",
        'already_reg': "🤖 আপনি ইতিমধ্যে রেজিস্টার্ড! নিচের মেনু ব্যবহার করুন।",
        'find': "🚀 পার্টনার খুঁজুন",
        'next': "⏭️ পরবর্তী পার্টনার",
        'stop': "🛑 চ্যাট বন্ধ করুন",
        'profile': "⚙️ আমার প্রোফাইল",
        'premium': "💎 প্রিমিয়াম",
        'help_btn': "❓ সাহায্য",
        'settings': "⚙️ সেটিংস",
        'change_lang': "🌐 ভাষা পরিবর্তন",
        'profile_txt': "⚙️ **আপনার প্রোফাইল:**\n\n👤 নাম: {name}\n🎂 বয়স: {age}\n🗣️ ভাষা: {lang}\n⚥ লিঙ্গ: {gender} 🔒\n🎯 খুঁজছেন: {looking_for}\n🛡️ ভেরিফিকেশন: {status}\n💎 প্রিমিয়াম: {premium_status}\n🎯 বয়স সীমা: {min_age}-{max_age}\n\n📊 **ম্যাচ:** {gender_matches_used}/{gender_matches_limit}\n\n_লিঙ্গ স্থায়ীভাবে লক করা আছে_',
        'partner_found': "🎉 **পার্টনার পাওয়া গেছে!**\n👤 নাম: {name}\n🎂 বয়স: {age}\n🗣️ ভাষা: {lang}\n⚥ লিঙ্গ: {gender}\n\nচ্যাট শুরু করুন!",
        'name_saved': "👍 নাম সেভ হয়েছে: {text}\n\n🎂 এখন আপনার **বয়স** লিখুন (শুধু সংখ্যা, যেমন: 22):",
        'select_lang': "🗣️ আপনার চ্যাটিং **ভাষা** নির্বাচন করুন:",
        'select_gender': "⚥ আপনার **লিঙ্গ** নির্বাচন করুন (এটি পরে পরিবর্তন করা যাবে না):",
        'select_looking': "🎯 আপনি কেমন **পার্টনার** খুঁজছেন?\n\n💡 **ফ্রি ইউজার:** {gender_limit}টি প্রেফারেন্স ম্যাচ, তারপর আনলিমিটেড র্যান্ডম!\n💎 **প্রিমিয়াম:** আনলিমিটেড ম্যাচ!",
        'invalid_age': "⚠️ সঠিক বয়স দিন (১৫-৯৯):",
        'invalid_lang_btn': "⚠️ অনুগ্রহ করে একটি ভাষা নির্বাচন করুন।",
        'enter_min_age': "🎯 পার্টনারের **সর্বনিম্ন বয়স** লিখুন (যেমন: ১৮):",
        'enter_max_age': "🎯 পার্টনারের **সর্বোচ্চ বয়স** লিখুন (যেমন: ৩০):",
        'filter_updated': "✅ বয়স ফিল্টার আপডেট হয়েছে!",
        'invalid_num': "⚠️ সঠিক সংখ্যা দিন।",
        'already_chat': "⚠️ আপনি ইতিমধ্যে চ্যাটে আছেন!",
        'searching': "⏳ পার্টনার খোঁজা হচ্ছে, দয়া করে অপেক্ষা করুন...",
        'search_start': "🔍 আপনার পছন্দ অনুযায়ী পার্টনার খোঁজা হচ্ছে...",
        'search_cancel': "🛑 পার্টনার খোঁজা বাতিল করা হয়েছে।",
        'you_stopped': "🛑 আপনি চ্যাট বন্ধ করেছেন।",
        'partner_stopped': "🛑 আপনার পার্টনার চ্যাট বন্ধ করেছে।",
        'not_connected': "⚠️ আপনি কোনো চ্যাটে যুক্ত নন।",
        'partner_left': "🛑 আপনার পার্টনার চ্যাট ছেড়ে গেছে।",
        'premium_txt': "💎 **প্রিমিয়াম ভিআইপি মেম্বারশিপ**\n\n**সুবিধা:**\n✅ আনলিমিটেড ম্যাচ\n✅ প্রায়োরিটি কিউ\n✅ অ্যাডভান্সড ফিল্টার\n\n**প্যাকেজ:**\n⭐ ৩৯ - ২৪ঘন্টা | ⭐ ১৪৯ - ৩দিন\n⭐ ২৪৯ - ৫দিন | ⭐ ৩৭৯ - ৭দিন\n⭐ ৪৯৯ - ১৪দিন | ⭐ ৭৯৯ - ৩০দিন\n\nপ্যাকেজ নির্বাচন করুন:",
        'premium_purchase_success': "🎉 **প্রিমিয়াম সক্রিয়!**\n\nপ্যাকেজ: {package}\nমেয়াদ: {days} দিন\nমেয়াদ শেষ: {expiry}\n\n✨ আনলিমিটেড ম্যাচ আনলক হয়েছে!",
        'help_txt': "💡 **সাহায্য গাইড:**\n\n**ফ্রি:** {limit}টি প্রেফারেন্স ম্যাচ → আনলিমিটেড র্যান্ডম\n**প্রিমিয়াম:** আনলিমিটেড প্রেফারেন্স ম্যাচ\n\n• লিঙ্গ স্থায়ীভাবে লক করা আছে\n• সেটিংস থেকে যেকোনো সময় ভাষা পরিবর্তন করুন\n• অসদাচরণ রিপোর্ট করুন",
        'start_chat_alert': "⚠️ চ্যাট শুরু করতে 'পার্টনার খুঁজুন' এ ক্লিক করুন।",
        'pic_verify_msg': "📸 **ফেস ভেরিফিকেশন**\n\nআপনার একটি ছবি পাঠান:",
        'pic_verify_success': "🎉 ধন্যবাদ! আপনার প্রোফাইল ভেরিফাইড!",
        'edit_name': "✍️ নাম পরিবর্তন",
        'edit_age': "✍️ বয়স পরিবর্তন",
        'verify_pic': "📸 ভেরিফাই",
        'set_filter': "🎯 বয়স ফিল্টার",
        'gender_locked': "🔒 **লিঙ্গ লক করা আছে**\n\nআপনার লিঙ্গ ({gender}) স্থায়ীভাবে সেট করা হয়েছে এবং পরিবর্তন করা যাবে না।",
        'gender_permanently_locked': "⚠️ **লিঙ্গ পরিবর্তন করা যাবে না**\n\nআপনার লিঙ্গ ({gender}) প্রোফাইল সম্পূর্ণ করার সময় স্থায়ীভাবে সেট করা হয়েছে।",
        'profile_complete': "✅ **প্রোফাইল সম্পূর্ণ!**\n\nআপনার লিঙ্গ ({gender}) এখন স্থায়ীভাবে লক করা হয়েছে।\n\nম্যাচিং শুরু করতে 'পার্টনার খুঁজুন' এ ক্লিক করুন!",
        'gender_limit_reached': "⚠️ **সীমা শেষ!**\n\nআপনি সব {limit}টি প্রেফারেন্স ম্যাচ ব্যবহার করেছেন।\n\n✅ এখন **র্যান্ডম মোডে** (আনলিমিটেড)!\n💎 প্রিমিয়াম নিন আনলিমিটেড প্রেফারেন্স ম্যাচের জন্য!",
        'random_mode': "🔄 **র্যান্ডম মোড সক্রিয়**\n\nআনলিমিটেড র্যান্ডম ম্যাচ!\n💎 প্রিমিয়াম নিন প্রেফারেন্স ম্যাচের জন্য!",
        'remaining_matches': "📊 বাকি প্রেফারেন্স ম্যাচ: {remaining}",
        'language_changed': "✅ ভাষা পরিবর্তন করা হয়েছে: {language}\n\nসমস্ত বার্তা এখন {language} এ দেখাবে।",
        'select_new_lang': "🌐 **আপনার পছন্দের ভাষা নির্বাচন করুন:**\n\nআপনি যেকোনো সময় ভাষা পরিবর্তন করতে পারেন।",
        'settings_menu': "⚙️ **সেটিংস মেনু**\n\nনিচের একটি অপশন নির্বাচন করুন:",
        'back_to_menu': "🔙 মেনুতে ফিরুন"
    },
    
    'hindi': {
        'welcome': "👋 Mnuverse Bot में आपका स्वागत है!",
        'start': "👋 Mnuverse Bot में आपका स्वागत है!\n\nशुरू करने से पहले, कृपया अपना प्रोफाइल सेट करें।\n\n📝 अपना नाम या उपनाम दर्ज करें:",
        'already_reg': "🤖 आप पहले से पंजीकृत हैं! नीचे दिए गए मेनू का उपयोग करें।",
        'find': "🚀 साथी ढूंढें",
        'next': "⏭️ अगला साथी",
        'stop': "🛑 चैट बंद करें",
        'profile': "⚙️ मेरा प्रोफाइल",
        'premium': "💎 प्रीमियम",
        'help_btn': "❓ सहायता",
        'settings': "⚙️ सेटिंग्स",
        'change_lang': "🌐 भाषा बदलें",
        'profile_txt': "⚙️ **आपका प्रोफाइल:**\n\n👤 नाम: {name}\n🎂 आयु: {age}\n🗣️ भाषा: {lang}\n⚥ लिंग: {gender} 🔒\n🎯 ढूंढ रहे हैं: {looking_for}\n🛡️ सत्यापन: {status}\n💎 प्रीमियम: {premium_status}\n🎯 आयु सीमा: {min_age}-{max_age}\n\n📊 **मैच:** {gender_matches_used}/{gender_matches_limit}\n\n_लिंग स्थायी रूप से लॉक किया गया है_",
        'partner_found': "🎉 **साथी मिल गया!**\n👤 नाम: {name}\n🎂 आयु: {age}\n🗣️ भाषा: {lang}\n⚥ लिंग: {gender}\n\nचैट शुरू करें!",
        'name_saved': "👍 नाम सहेजा गया: {text}\n\n🎂 अब अपनी **आयु** दर्ज करें (केवल संख्या, जैसे: 22):",
        'select_lang': "🗣️ अपनी चैटिंग **भाषा** चुनें:",
        'select_gender': "⚥ अपना **लिंग** चुनें (यह बाद में नहीं बदला जा सकता):",
        'select_looking': "🎯 आप किस तरह का **साथी** ढूंढ रहे हैं?\n\n💡 **मुफ्त उपयोगकर्ता:** {gender_limit} प्राथमिकता मैच, फिर असीमित रैंडम!\n💎 **प्रीमियम:** असीमित मैच!",
        'invalid_age': "⚠️ कृपया वैध आयु दर्ज करें (15-99):",
        'invalid_lang_btn': "⚠️ कृपया एक भाषा चुनें।",
        'enter_min_age': "🎯 साथी के लिए **न्यूनतम आयु** दर्ज करें (जैसे: 18):",
        'enter_max_age': "🎯 साथी के लिए **अधिकतम आयु** दर्ज करें (जैसे: 30):",
        'filter_updated': "✅ आयु फ़िल्टर अपडेट किया गया!",
        'invalid_num': "⚠️ कृपया वैध संख्या दर्ज करें।",
        'already_chat': "⚠️ आप पहले से चैट में हैं!",
        'searching': "⏳ साथी ढूंढ रहे हैं, कृपया प्रतीक्षा करें...",
        'search_start': "🔍 आपकी पसंद के अनुसार साथी ढूंढ रहे हैं...",
        'search_cancel': "🛑 साथी ढूंढना रद्द किया गया।",
        'you_stopped': "🛑 आपने चैट बंद कर दी।",
        'partner_stopped': "🛑 आपके साथी ने चैट बंद कर दी।",
        'not_connected': "⚠️ आप किसी चैट से कनेक्ट नहीं हैं।",
        'partner_left': "🛑 आपका साथी चैट छोड़ गया।",
        'premium_txt': "💎 **प्रीमियम वीआईपी सदस्यता**\n\n**लाभ:**\n✅ असीमित मैच\n✅ प्राथमिकता क्यू\n✅ उन्नत फ़िल्टर\n\n**पैकेज:**\n⭐ 39 - 24घंटा | ⭐ 149 - 3दिन\n⭐ 249 - 5दिन | ⭐ 379 - 7दिन\n⭐ 499 - 14दिन | ⭐ 799 - 30दिन\n\nपैकेज चुनें:",
        'premium_purchase_success': "🎉 **प्रीमियम सक्रिय!**\n\nपैकेज: {package}\nअवधि: {days} दिन\nसमाप्ति: {expiry}\n\n✨ असीमित मैच अनलॉक!",
        'help_txt': "💡 **सहायता गाइड:**\n\n**मुफ्त:** {limit} प्राथमिकता मैच → असीमित रैंडम\n**प्रीमियम:** असीमित प्राथमिकता मैच\n\n• लिंग स्थायी रूप से लॉक किया गया है\n• सेटिंग्स से कभी भी भाषा बदलें\n• अनुचित व्यवहार की रिपोर्ट करें",
        'start_chat_alert': "⚠️ चैट शुरू करने के लिए 'साथी ढूंढें' पर टैप करें।",
        'pic_verify_msg': "📸 **चेहरा सत्यापन**\n\nअपनी एक स्पष्ट फोटो भेजें:",
        'pic_verify_success': "🎉 धन्यवाद! आपका प्रोफाइल सत्यापित हो गया है!",
        'edit_name': "✍️ नाम बदलें",
        'edit_age': "✍️ आयु बदलें",
        'verify_pic': "📸 सत्यापित करें",
        'set_filter': "🎯 आयु फ़िल्टर",
        'gender_locked': "🔒 **लिंग लॉक किया गया**\n\nआपका लिंग ({gender}) स्थायी रूप से सेट किया गया है और इसे बदला नहीं जा सकता।",
        'gender_permanently_locked': "⚠️ **लिंग नहीं बदल सकते**\n\nआपका लिंग ({gender}) प्रोफाइल पूरा होने पर स्थायी रूप से सेट कर दिया गया था।",
        'profile_complete': "✅ **प्रोफाइल पूरा हुआ!**\n\nआपका लिंग ({gender}) अब स्थायी रूप से लॉक हो गया है।\n\nमैचिंग शुरू करने के लिए 'साथी ढूंढें' पर टैप करें!",
        'gender_limit_reached': "⚠️ **सीमा समाप्त!**\n\nआपने सभी {limit} प्राथमिकता मैच का उपयोग कर लिया है।\n\n✅ अब **रैंडम मोड** में (असीमित)!\n💎 असीमित प्राथमिकता मैच के लिए प्रीमियम लें!",
        'random_mode': "🔄 **रैंडम मोड सक्रिय**\n\nअसीमित रैंडम मैच!\n💎 प्राथमिकता मैच के लिए प्रीमियम लें!",
        'remaining_matches': "📊 शेष प्राथमिकता मैच: {remaining}",
        'language_changed': "✅ भाषा बदली गई: {language}\n\nसभी संदेश अब {language} में दिखेंगे।",
        'select_new_lang': "🌐 **अपनी पसंदीदा भाषा चुनें:**\n\nआप कभी भी भाषा बदल सकते हैं।",
        'settings_menu': "⚙️ **सेटिंग्स मेनू**\n\nनीचे एक विकल्प चुनें:",
        'back_to_menu': "🔙 मुख्य मेनू पर वापस"
    }
}

# Continue adding remaining 9 languages below...
# (I'll provide them in the next message due to length limit)
# Japanese Language (4th)
MESSAGES['japanese'] = {
    'welcome': "👋 Mnuverse Botへようこそ！",
    'start': "👋 Mnuverse Botへようこそ！\n\n始める前に、プロフィールを設定してください。\n\n📝 名前またはニックネームを入力してください：",
    'already_reg': "🤖 すでに登録されています！下のメニューを使用してください。",
    'find': "🚀 パートナーを探す",
    'next': "⏭️ 次のパートナー",
    'stop': "🛑 チャットを終了",
    'profile': "⚙️ マイプロフィール",
    'premium': "💎 プレミアム",
    'help_btn': "❓ ヘルプ",
    'settings': "⚙️ 設定",
    'change_lang': "🌐 言語変更",
    'profile_txt': "⚙️ **プロフィール:**\n\n👤 名前: {name}\n🎂 年齢: {age}\n🗣️ 言語: {lang}\n⚥ 性別: {gender} 🔒\n🎯 探している相手: {looking_for}\n🛡️ 認証: {status}\n💎 プレミアム: {premium_status}\n🎯 年齢範囲: {min_age}-{max_age}\n\n📊 **マッチ数:** {gender_matches_used}/{gender_matches_limit}\n\n_性別は永久にロックされます_',
    'partner_found': "🎉 **パートナーが見つかりました！**\n👤 名前: {name}\n🎂 年齢: {age}\n🗣️ 言語: {lang}\n⚥ 性別: {gender}\n\nチャットを開始してください！",
    'name_saved': "👍 名前を保存しました: {text}\n\n🎂 次に**年齢**を入力してください（数字のみ、例：22）：",
    'select_lang': "🗣️ チャットの**言語**を選択してください：",
    'select_gender': "⚥ **性別**を選択してください（後で変更できません）：",
    'select_looking': "🎯 どのような**パートナー**を探していますか？\n\n💡 **無料ユーザー:** {gender_limit}回の優先マッチ、その後無制限ランダム！\n💎 **プレミアム:** 無制限マッチ！",
    'invalid_age': "⚠️ 有効な年齢を入力してください（15-99）：",
    'invalid_lang_btn': "⚠️ ボタンから言語を選択してください。",
    'enter_min_age': "🎯 パートナーの**最低年齢**を入力してください（例：18）：",
    'enter_max_age': "🎯 パートナーの**最高年齢**を入力してください（例：30）：",
    'filter_updated': "✅ 年齢フィルターを更新しました！",
    'invalid_num': "⚠️ 有効な数字を入力してください。",
    'already_chat': "⚠️ すでにチャット中です！",
    'searching': "⏳ パートナーを検索中、お待ちください...",
    'search_start': "🔍 あなたの好みに基づいてパートナーを検索中...",
    'search_cancel': "🛑 パートナー検索をキャンセルしました。",
    'you_stopped': "🛑 チャットを終了しました。",
    'partner_stopped': "🛑 パートナーがチャットを終了しました。",
    'not_connected': "⚠️ どのチャットにも接続されていません。",
    'partner_left': "🛑 パートナーがチャットを退出しました。",
    'premium_txt': "💎 **プレミアムVIPメンバーシップ**\n\n**特典:**\n✅ 無制限マッチ\n✅ 優先キュー\n✅ 高度なフィルター\n\n**パッケージ:**\n⭐ 39 - 24時間 | ⭐ 149 - 3日\n⭐ 249 - 5日 | ⭐ 379 - 7日\n⭐ 499 - 14日 | ⭐ 799 - 30日\n\nパッケージを選択：",
    'premium_purchase_success': "🎉 **プレミアムアクティブ化！**\n\nパッケージ: {package}\n期間: {days}日\n期限: {expiry}\n\n✨ 無制限マッチがアンロックされました！",
    'help_txt': "💡 **ヘルプガイド:**\n\n**無料:** {limit}回の優先マッチ → 無制限ランダム\n**プレミアム:** 無制限の優先マッチ\n\n• 性別は永久にロックされます\n• 設定からいつでも言語を変更できます\n• 不適切な行為を報告してください",
    'start_chat_alert': "⚠️ チャットを開始するには「パートナーを探す」をタップしてください。",
    'pic_verify_msg': "📸 **顔認証**\n\n自分の写真を送信してください：",
    'pic_verify_success': "🎉 ありがとうございます！プロフィールが認証されました！",
    'edit_name': "✍️ 名前を編集",
    'edit_age': "✍️ 年齢を編集",
    'verify_pic': "📸 認証",
    'set_filter': "🎯 年齢フィルター",
    'gender_locked': "🔒 **性別ロック**\n\nあなたの性別（{gender}）は永久的に設定されており、変更できません。",
    'gender_permanently_locked': "⚠️ **性別を変更できません**\n\nあなたの性別（{gender}）はプロフィール完了時に永久的に設定されました。",
    'profile_complete': "✅ **プロフィール完了！**\n\nあなたの性別（{gender}）は永久にロックされました。\n\nマッチングを開始するには「パートナーを探す」をタップしてください！",
    'gender_limit_reached': "⚠️ **制限に達しました！**\n\n{limit}回の優先マッチをすべて使用しました。\n\n✅ 現在**ランダムモード**（無制限）！\n💎 無制限の優先マッチのためにプレミアムにアップグレード！",
    'random_mode': "🔄 **ランダムモードアクティブ**\n\n無制限ランダムマッチ！\n💎 優先マッチのためにプレミアムを入手！",
    'remaining_matches': "📊 残りの優先マッチ: {remaining}",
    'language_changed': "✅ 言語を変更しました: {language}\n\nすべてのメッセージが{language}で表示されます。",
    'select_new_lang': "🌐 **希望する言語を選択してください：**\n\nいつでも言語を変更できます。",
    'settings_menu': "⚙️ **設定メニュー**\n\n以下からオプションを選択してください：",
    'back_to_menu': "🔙 メインメニューに戻る"
}

# Russian Language (5th)
MESSAGES['russian'] = {
    'welcome': "👋 Добро пожаловать в Mnuverse Bot!",
    'start': "👋 Добро пожаловать в Mnuverse Bot!\n\nПрежде чем начать, настройте свой профиль.\n\n📝 Введите ваше имя или никнейм:",
    'already_reg': "🤖 Вы уже зарегистрированы! Используйте меню ниже.",
    'find': "🚀 Найти партнера",
    'next': "⏭️ Следующий партнер",
    'stop': "🛑 Остановить чат",
    'profile': "⚙️ Мой профиль",
    'premium': "💎 Премиум",
    'help_btn': "❓ Помощь",
    'settings': "⚙️ Настройки",
    'change_lang': "🌐 Сменить язык",
    'profile_txt': "⚙️ **Ваш профиль:**\n\n👤 Имя: {name}\n🎂 Возраст: {age}\n🗣️ Язык: {lang}\n⚥ Пол: {gender} 🔒\n🎯 Ищете: {looking_for}\n🛡️ Верификация: {status}\n💎 Премиум: {premium_status}\n🎯 Диапазон возраста: {min_age}-{max_age}\n\n📊 **Матчи:** {gender_matches_used}/{gender_matches_limit}\n\n_Пол навсегда заблокирован_',
    'partner_found': "🎉 **Партнер найден!**\n👤 Имя: {name}\n🎂 Возраст: {age}\n🗣️ Язык: {lang}\n⚥ Пол: {gender}\n\nНачните общение!",
    'name_saved': "👍 Имя сохранено: {text}\n\n🎂 Теперь введите ваш **возраст** (только цифры, например: 22):",
    'select_lang': "🗣️ Выберите **язык** для общения:",
    'select_gender': "⚥ Выберите ваш **пол** (это нельзя будет изменить позже):",
    'select_looking': "🎯 Кого вы **ищете**?\n\n💡 **Бесплатные пользователи:** {gender_limit} предпочтительных матчей, затем безлимитные случайные!\n💎 **Премиум:** Безлимитные матчи!",
    'invalid_age': "⚠️ Пожалуйста, введите корректный возраст (15-99):",
    'invalid_lang_btn': "⚠️ Пожалуйста, выберите язык из кнопок.",
    'enter_min_age': "🎯 Введите **минимальный возраст** партнера (например: 18):",
    'enter_max_age': "🎯 Введите **максимальный возраст** партнера (например: 30):",
    'filter_updated': "✅ Фильтр возраста партнера обновлен!",
    'invalid_num': "⚠️ Пожалуйста, введите корректное число.",
    'already_chat': "⚠️ Вы уже в чате!",
    'searching': "⏳ Поиск партнера, пожалуйста подождите...",
    'search_start': "🔍 Поиск партнера на основе ваших предпочтений...",
    'search_cancel': "🛑 Поиск партнера отменен.",
    'you_stopped': "🛑 Вы остановили чат.",
    'partner_stopped': "🛑 Ваш партнер остановил чат.",
    'not_connected': "⚠️ Вы не подключены к чату.",
    'partner_left': "🛑 Ваш партнер покинул чат.",
    'premium_txt': "💎 **Премиум VIP подписка**\n\n**Преимущества:**\n✅ Безлимитные матчи\n✅ Приоритетная очередь\n✅ Расширенные фильтры\n\n**Пакеты:**\n⭐ 39 - 24ч | ⭐ 149 - 3д\n⭐ 249 - 5д | ⭐ 379 - 7д\n⭐ 499 - 14д | ⭐ 799 - 30д\n\nВыберите пакет:",
    'premium_purchase_success': "🎉 **Премиум активирован!**\n\nПакет: {package}\nДлительность: {days} дней\nИстекает: {expiry}\n\n✨ Безлимитные матчи разблокированы!",
    'help_txt': "💡 **Руководство:**\n\n**Бесплатно:** {limit} предпочтительных матчей → безлимитные случайные\n**Премиум:** Безлимитные предпочтительные матчи\n\n• Пол навсегда заблокирован\n• Измените язык в любое время в Настройках\n• Сообщайте о неподобающем поведении",
    'start_chat_alert': "⚠️ Нажмите 'Найти партнера' чтобы начать чат.",
    'pic_verify_msg': "📸 **Верификация лица**\n\nОтправьте четкое фото себя:",
    'pic_verify_success': "🎉 Спасибо! Ваш профиль ВЕРИФИЦИРОВАН!",
    'edit_name': "✍️ Изменить имя",
    'edit_age': "✍️ Изменить возраст",
    'verify_pic': "📸 Верифицировать",
    'set_filter': "🎯 Фильтр возраста",
    'gender_locked': "🔒 **Пол заблокирован**\n\nВаш пол ({gender}) установлен навсегда и не может быть изменен.",
    'gender_permanently_locked': "⚠️ **Нельзя изменить пол**\n\nВаш пол ({gender}) был навсегда установлен при завершении профиля.",
    'profile_complete': "✅ **Профиль завершен!**\n\nВаш пол ({gender}) теперь навсегда заблокирован.\n\nНажмите 'Найти партнера' чтобы начать поиск!",
    'gender_limit_reached': "⚠️ **Лимит достигнут!**\n\nВы использовали все {limit} предпочтительных матчей.\n\n✅ Теперь в **случайном режиме** (безлимитно)!\n💎 Перейдите на Премиум для безлимитных предпочтительных матчей!",
    'random_mode': "🔄 **Случайный режим активен**\n\nБезлимитные случайные матчи!\n💎 Получите Премиум для предпочтительных матчей!",
    'remaining_matches': "📊 Осталось предпочтительных матчей: {remaining}",
    'language_changed': "✅ Язык изменен на: {language}\n\nВсе сообщения теперь будут отображаться на {language}.",
    'select_new_lang': "🌐 **Выберите предпочитаемый язык:**\n\nВы можете изменить язык в любое время.",
    'settings_menu': "⚙️ **Меню настроек**\n\nВыберите опцию ниже:",
    'back_to_menu': "🔙 Вернуться в главное меню"
}

# Arabic Language (6th)
MESSAGES['arabic'] = {
    'welcome': "👋 مرحبا بكم في بوت Mnuverse!",
    'start': "👋 مرحبا بكم في بوت Mnuverse!\n\nقبل البدء، يرجى إعداد ملفك الشخصي.\n\n📝 يرجى إدخال اسمك أو اسم مستعار:",
    'already_reg': "🤖 أنت مسجل بالفعل! استخدم القائمة أدناه.",
    'find': "🚀 ابحث عن شريك",
    'next': "⏭️ الشريك التالي",
    'stop': "🛑 إيقاف المحادثة",
    'profile': "⚙️ ملفي الشخصي",
    'premium': "💎 بريميوم",
    'help_btn': "❓ مساعدة",
    'settings': "⚙️ الإعدادات",
    'change_lang': "🌐 تغيير اللغة",
    'profile_txt': "⚙️ **ملفك الشخصي:**\n\n👤 الاسم: {name}\n🎂 العمر: {age}\n🗣️ اللغة: {lang}\n⚥ الجنس: {gender} 🔒\n🎯 تبحث عن: {looking_for}\n🛡️ التوثيق: {status}\n💎 بريميوم: {premium_status}\n🎯 نطاق العمر: {min_age}-{max_age}\n\n📊 **المطابقات:** {gender_matches_used}/{gender_matches_limit}\n\n_الجنس مؤمن بشكل دائم_',
    'partner_found': "🎉 **تم العثور على شريك!**\n👤 الاسم: {name}\n🎂 العمر: {age}\n🗣️ اللغة: {lang}\n⚥ الجنس: {gender}\n\nابدأ المحادثة!",
    'name_saved': "👍 تم حفظ الاسم: {text}\n\n🎂 الآن أدخل **عمرك** (أرقام فقط، مثال: 22):",
    'select_lang': "🗣️ اختر **لغة** المحادثة الخاصة بك:",
    'select_gender': "⚥ اختر **جنسك** (لا يمكن تغييره لاحقًا):",
    'select_looking': "🎯 من الذي **تبحث عنه**؟\n\n💡 **المستخدمون المجانيون:** {gender_limit} مطابقة مفضلة، ثم عشوائي غير محدود!\n💎 **بريميوم:** مطابقات غير محدودة!",
    'invalid_age': "⚠️ يرجى إدخال عمر صالح (15-99):",
    'invalid_lang_btn': "⚠️ يرجى اختيار لغة من الأزرار.",
    'enter_min_age': "🎯 أدخل **الحد الأدنى للعمر** للشريك (مثال: 18):",
    'enter_max_age': "🎯 أدخل **الحد الأقصى للعمر** للشريك (مثال: 30):",
    'filter_updated': "✅ تم تحديث فلتر عمر الشريك!",
    'invalid_num': "⚠️ يرجى إدخال رقم صالح.",
    'already_chat': "⚠️ أنت بالفعل في محادثة!",
    'searching': "⏳ جاري البحث عن شريك، يرجى الانتظار...",
    'search_start': "🔍 جاري البحث عن شريك بناءً على تفضيلاتك...",
    'search_cancel': "🛑 تم إلغاء البحث عن شريك.",
    'you_stopped': "🛑 لقد أوقفت المحادثة.",
    'partner_stopped': "🛑 أوقف شريكك المحادثة.",
    'not_connected': "⚠️ أنت غير متصل بأي محادثة.",
    'partner_left': "🛑 غادر شريكك المحادثة.",
    'premium_txt': "💎 **عضوية بريميوم VIP**\n\n**المزايا:**\n✅ مطابقات غير محدودة\n✅ قائمة انتظار ذات أولوية\n✅ فلاتر متقدمة\n\n**الباقات:**\n⭐ 39 - 24س | ⭐ 149 - 3أيام\n⭐ 249 - 5أيام | ⭐ 379 - 7أيام\n⭐ 499 - 14أيام | ⭐ 799 - 30يوم\n\nاختر الباقة:",
    'premium_purchase_success': "🎉 **تم تفعيل البريميوم!**\n\nالباقة: {package}\nالمدة: {days} أيام\nتنتهي: {expiry}\n\n✨ تم فتح المطابقات غير المحدودة!",
    'help_txt': "💡 **دليل المساعدة:**\n\n**مجاني:** {limit} مطابقة مفضلة → عشوائي غير محدود\n**بريميوم:** مطابقات مفضلة غير محدودة\n\n• الجنس مؤمن بشكل دائم\n• غيّر اللغة في أي وقت من الإعدادات\n• أبلغ عن السلوك غير اللائق",
    'start_chat_alert': "⚠️ اضغط على 'ابحث عن شريك' لبدء المحادثة.",
    'pic_verify_msg': "📸 **التحقق من الوجه**\n\nأرسل صورة واضحة لنفسك:",
    'pic_verify_success': "🎉 شكرًا لك! تم توثيق ملفك الشخصي!",
    'edit_name': "✍️ تعديل الاسم",
    'edit_age': "✍️ تعديل العمر",
    'verify_pic': "📸 توثيق",
    'set_filter': "🎯 فلتر العمر",
    'gender_locked': "🔒 **الجنس مؤمن**\n\nجنسك ({gender}) تم تعيينه بشكل دائم ولا يمكن تغييره.",
    'gender_permanently_locked': "⚠️ **لا يمكن تغيير الجنس**\n\nتم تعيين جنسك ({gender}) بشكل دائم عند إكمال ملفك الشخصي.",
    'profile_complete': "✅ **اكتمل الملف الشخصي!**\n\nجنسك ({gender}) الآن مؤمن بشكل دائم.\n\nاضغط على 'ابحث عن شريك' لبدء المطابقة!",
    'gender_limit_reached': "⚠️ **تم الوصول إلى الحد الأقصى!**\n\nلقد استخدمت جميع المطابقات المفضلة {limit}.\n\n✅ الآن في **الوضع العشوائي** (غير محدود)!\n💎 قم بالترقية إلى بريميوم للحصول على مطابقات مفضلة غير محدودة!",
    'random_mode': "🔄 **الوضع العشوائي نشط**\n\nمطابقات عشوائية غير محدودة!\n💎 احصل على بريميوم للمطابقات المفضلة!",
    'remaining_matches': "📊 المطابقات المفضلة المتبقية: {remaining}",
    'language_changed': "✅ تم تغيير اللغة إلى: {language}\n\nستظهر جميع الرسائل الآن باللغة {language}.",
    'select_new_lang': "🌐 **اختر لغتك المفضلة:**\n\nيمكنك تغيير اللغة في أي وقت.",
    'settings_menu': "⚙️ **قائمة الإعدادات**\n\nاختر خيارًا أدناه:",
    'back_to_menu': "🔙 العودة إلى القائمة الرئيسية"
}
# Spanish Language (7th)
MESSAGES['spanish'] = {
    'welcome': "👋 ¡Bienvenido a Mnuverse Bot!",
    'start': "👋 ¡Bienvenido a Mnuverse Bot!\n\nAntes de comenzar, configura tu perfil.\n\n📝 Ingresa tu nombre o apodo:",
    'already_reg': "🤖 ¡Ya estás registrado! Usa el menú de abajo.",
    'find': "🚀 Buscar Pareja",
    'next': "⏭️ Siguiente Pareja",
    'stop': "🛑 Detener Chat",
    'profile': "⚙️ Mi Perfil",
    'premium': "💎 Premium",
    'help_btn': "❓ Ayuda",
    'settings': "⚙️ Configuración",
    'change_lang': "🌐 Cambiar Idioma",
    'profile_txt': "⚙️ **Tu Perfil:**\n\n👤 Nombre: {name}\n🎂 Edad: {age}\n🗣️ Idioma: {lang}\n⚥ Género: {gender} 🔒\n🎯 Buscando: {looking_for}\n🛡️ Verificación: {status}\n💎 Premium: {premium_status}\n🎯 Rango de edad: {min_age}-{max_age}\n\n📊 **Emparejamientos:** {gender_matches_used}/{gender_matches_limit}\n\n_El género está bloqueado permanentemente_',
    'partner_found': "🎉 **¡Pareja Encontrada!**\n👤 Nombre: {name}\n🎂 Edad: {age}\n🗣️ Idioma: {lang}\n⚥ Género: {gender}\n\n¡Comienza a chatear!",
    'name_saved': "👍 Nombre guardado: {text}\n\n🎂 Ahora ingresa tu **Edad** (solo números, ej: 22):",
    'select_lang': "🗣️ Selecciona tu **Idioma** para chatear:",
    'select_gender': "⚥ Selecciona tu **Género** (Esto no se puede cambiar después):",
    'select_looking': "🎯 ¿A quién estás **buscando**?\n\n💡 **Usuarios Gratuitos:** {gender_limit} emparejamientos con preferencia, ¡luego aleatorio ilimitado!\n💎 **Premium:** ¡Emparejamientos ilimitados!",
    'invalid_age': "⚠️ Por favor ingresa una edad válida (15-99):",
    'invalid_lang_btn': "⚠️ Por favor selecciona un idioma de los botones.",
    'enter_min_age': "🎯 Ingresa la **Edad Mínima** para la pareja (ej: 18):",
    'enter_max_age': "🎯 Ingresa la **Edad Máxima** para la pareja (ej: 30):",
    'filter_updated': "✅ ¡Filtro de edad de pareja actualizado!",
    'invalid_num': "⚠️ Por favor ingresa un número válido.",
    'already_chat': "⚠️ ¡Ya estás en un chat!",
    'searching': "⏳ Buscando pareja, por favor espera...",
    'search_start': "🔍 Buscando pareja según tus preferencias...",
    'search_cancel': "🛑 Búsqueda de pareja cancelada.",
    'you_stopped': "🛑 Detuviste el chat.",
    'partner_stopped': "🛑 Tu pareja detuvo el chat.",
    'not_connected': "⚠️ No estás conectado a ningún chat.",
    'partner_left': "🛑 Tu pareja dejó el chat.",
    'premium_txt': "💎 **Membresía Premium VIP**\n\n**Beneficios:**\n✅ Emparejamientos ilimitados\n✅ Cola prioritaria\n✅ Filtros avanzados\n\n**Paquetes:**\n⭐ 39 - 24H | ⭐ 149 - 3D\n⭐ 249 - 5D | ⭐ 379 - 7D\n⭐ 499 - 14D | ⭐ 799 - 30D\n\nSelecciona paquete:",
    'premium_purchase_success': "🎉 **¡Premium Activado!**\n\nPaquete: {package}\nDuración: {days} días\nExpira: {expiry}\n\n✨ ¡Emparejamientos ilimitados desbloqueados!",
    'help_txt': "💡 **Guía de Ayuda:**\n\n**Gratis:** {limit} emparejamientos con preferencia → aleatorio ilimitado\n**Premium:** Emparejamientos con preferencia ilimitados\n\n• El género está bloqueado permanentemente\n• Cambia el idioma en cualquier momento en Configuración\n• Reporta comportamiento inapropiado",
    'start_chat_alert': "⚠️ Toca 'Buscar Pareja' para comenzar a chatear.",
    'pic_verify_msg': "📸 **Verificación de Rostro**\n\nEnvía una foto clara de ti mismo:",
    'pic_verify_success': "🎉 ¡Gracias! ¡Tu perfil está VERIFICADO!",
    'edit_name': "✍️ Editar Nombre",
    'edit_age': "✍️ Editar Edad",
    'verify_pic': "📸 Verificar",
    'set_filter': "🎯 Filtro de Edad",
    'gender_locked': "🔒 **Género Bloqueado**\n\nTu género ({gender}) está establecido permanentemente y no se puede cambiar.",
    'gender_permanently_locked': "⚠️ **No se puede cambiar el género**\n\nTu género ({gender}) se estableció permanentemente al completar tu perfil.",
    'profile_complete': "✅ **¡Perfil Completo!**\n\nTu género ({gender}) ahora está bloqueado permanentemente.\n\n¡Toca 'Buscar Pareja' para comenzar a emparejarte!",
    'gender_limit_reached': "⚠️ **¡Límite Alcanzado!**\n\nHas usado todos los {limit} emparejamientos con preferencia.\n\n✅ ¡Ahora en **modo aleatorio** (ilimitado)!\n💎 ¡Actualiza a Premium para emparejamientos con preferencia ilimitados!",
    'random_mode': "🔄 **Modo Aleatorio Activo**\n\n¡Emparejamientos aleatorios ilimitados!\n💎 ¡Obtén Premium para emparejamientos con preferencia!",
    'remaining_matches': "📊 Emparejamientos con preferencia restantes: {remaining}",
    'language_changed': "✅ Idioma cambiado a: {language}\n\nTodos los mensajes ahora aparecerán en {language}.",
    'select_new_lang': "🌐 **Selecciona tu idioma preferido:**\n\nPuedes cambiar el idioma en cualquier momento.",
    'settings_menu': "⚙️ **Menú de Configuración**\n\nElige una opción a continuación:",
    'back_to_menu': "🔙 Volver al Menú Principal"
}

# French Language (8th)
MESSAGES['french'] = {
    'welcome': "👋 Bienvenue sur Mnuverse Bot!",
    'start': "👋 Bienvenue sur Mnuverse Bot!\n\nAvant de commencer, configurez votre profil.\n\n📝 Entrez votre nom ou surnom:",
    'already_reg': "🤖 Vous êtes déjà inscrit! Utilisez le menu ci-dessous.",
    'find': "🚀 Trouver un Partenaire",
    'next': "⏭️ Partenaire Suivant",
    'stop': "🛑 Arrêter le Chat",
    'profile': "⚙️ Mon Profil",
    'premium': "💎 Premium",
    'help_btn': "❓ Aide",
    'settings': "⚙️ Paramètres",
    'change_lang': "🌐 Changer de Langue",
    'profile_txt': "⚙️ **Votre Profil:**\n\n👤 Nom: {name}\n🎂 Âge: {age}\n🗣️ Langue: {lang}\n⚥ Genre: {gender} 🔒\n🎯 Recherche: {looking_for}\n🛡️ Vérification: {status}\n💎 Premium: {premium_status}\n🎯 Tranche d'âge: {min_age}-{max_age}\n\n📊 **Matchs:** {gender_matches_used}/{gender_matches_limit}\n\n_Le genre est verrouillé définitivement_',
    'partner_found': "🎉 **Partenaire Trouvé!**\n👤 Nom: {name}\n🎂 Âge: {age}\n🗣️ Langue: {lang}\n⚥ Genre: {gender}\n\nCommencez à discuter!",
    'name_saved': "👍 Nom enregistré: {text}\n\n🎂 Entrez maintenant votre **Âge** (chiffres seulement, ex: 22):",
    'select_lang': "🗣️ Sélectionnez votre **Langue** de discussion:",
    'select_gender': "⚥ Sélectionnez votre **Genre** (Ceci ne peut pas être modifié plus tard):",
    'select_looking': "🎯 Qui **cherchez-vous**?\n\n💡 **Utilisateurs gratuits:** {gender_limit} matchs préférentiels, puis aléatoire illimité!\n💎 **Premium:** Matchs illimités!",
    'invalid_age': "⚠️ Veuillez entrer un âge valide (15-99):",
    'invalid_lang_btn': "⚠️ Veuillez sélectionner une langue dans les boutons.",
    'enter_min_age': "🎯 Entrez l'**Âge Minimum** pour le partenaire (ex: 18):",
    'enter_max_age': "🎯 Entrez l'**Âge Maximum** pour le partenaire (ex: 30):",
    'filter_updated': "✅ Filtre d'âge du partenaire mis à jour!",
    'invalid_num': "⚠️ Veuillez entrer un nombre valide.",
    'already_chat': "⚠️ Vous êtes déjà dans un chat!",
    'searching': "⏳ Recherche d'un partenaire, veuillez patienter...",
    'search_start': "🔍 Recherche d'un partenaire selon vos préférences...",
    'search_cancel': "🛑 Recherche de partenaire annulée.",
    'you_stopped': "🛑 Vous avez arrêté le chat.",
    'partner_stopped': "🛑 Votre partenaire a arrêté le chat.",
    'not_connected': "⚠️ Vous n'êtes connecté à aucun chat.",
    'partner_left': "🛑 Votre partenaire a quitté le chat.",
    'premium_txt': "💎 **Abonnement Premium VIP**\n\n**Avantages:**\n✅ Matchs illimités\n✅ File d'attente prioritaire\n✅ Filtres avancés\n\n**Forfaits:**\n⭐ 39 - 24H | ⭐ 149 - 3J\n⭐ 249 - 5J | ⭐ 379 - 7J\n⭐ 499 - 14J | ⭐ 799 - 30J\n\nSélectionnez le forfait:",
    'premium_purchase_success': "🎉 **Premium Activé!**\n\nForfait: {package}\nDurée: {days} jours\nExpire: {expiry}\n\n✨ Matchs illimités débloqués!",
    'help_txt': "💡 **Guide d'Aide:**\n\n**Gratuit:** {limit} matchs préférentiels → aléatoire illimité\n**Premium:** Matchs préférentiels illimités\n\n• Le genre est verrouillé définitivement\n• Changez la langue à tout moment dans Paramètres\n• Signalez tout comportement inapproprié",
    'start_chat_alert': "⚠️ Appuyez sur 'Trouver un Partenaire' pour commencer à discuter.",
    'pic_verify_msg': "📸 **Vérification du Visage**\n\nEnvoyez une photo claire de vous-même:",
    'pic_verify_success': "🎉 Merci! Votre profil est VÉRIFIÉ!",
    'edit_name': "✍️ Modifier le Nom",
    'edit_age': "✍️ Modifier l'Âge",
    'verify_pic': "📸 Vérifier",
    'set_filter': "🎯 Filtre d'Âge",
    'gender_locked': "🔒 **Genre Verrouillé**\n\nVotre genre ({gender}) est défini définitivement et ne peut pas être modifié.",
    'gender_permanently_locked': "⚠️ **Impossible de modifier le genre**\n\nVotre genre ({gender}) a été défini définitivement lors de la complétion de votre profil.",
    'profile_complete': "✅ **Profil Complet!**\n\nVotre genre ({gender}) est maintenant verrouillé définitivement.\n\nAppuyez sur 'Trouver un Partenaire' pour commencer les matchs!",
    'gender_limit_reached': "⚠️ **Limite Atteinte!**\n\nVous avez utilisé tous les {limit} matchs préférentiels.\n\n✅ Maintenant en **mode aléatoire** (illimité)!\n💎 Passez à Premium pour des matchs préférentiels illimités!",
    'random_mode': "🔄 **Mode Aléatoire Actif**\n\nMatchs aléatoires illimités!\n💎 Obtenez Premium pour des matchs préférentiels!",
    'remaining_matches': "📊 Matchs préférentiels restants: {remaining}",
    'language_changed': "✅ Langue changée en: {language}\n\nTous les messages apparaîtront maintenant en {language}.",
    'select_new_lang': "🌐 **Sélectionnez votre langue préférée:**\n\nVous pouvez changer la langue à tout moment.",
    'settings_menu': "⚙️ **Menu Paramètres**\n\nChoisissez une option ci-dessous:",
    'back_to_menu': "🔙 Retour au Menu Principal"
}

# Korean Language (9th)
MESSAGES['korean'] = {
    'welcome': "👋 Mnuverse 봇에 오신 것을 환영합니다!",
    'start': "👋 Mnuverse 봇에 오신 것을 환영합니다!\n\n시작하기 전에 프로필을 설정하세요.\n\n📝 이름 또는 닉네임을 입력하세요:",
    'already_reg': "🤖 이미 등록되어 있습니다! 아래 메뉴를 사용하세요.",
    'find': "🚀 파트너 찾기",
    'next': "⏭️ 다음 파트너",
    'stop': "🛑 채팅 중지",
    'profile': "⚙️ 내 프로필",
    'premium': "💎 프리미엄",
    'help_btn': "❓ 도움말",
    'settings': "⚙️ 설정",
    'change_lang': "🌐 언어 변경",
    'profile_txt': "⚙️ **내 프로필:**\n\n👤 이름: {name}\n🎂 나이: {age}\n🗣️ 언어: {lang}\n⚥ 성별: {gender} 🔒\n🎯 찾는 대상: {looking_for}\n🛡️ 인증: {status}\n💎 프리미엄: {premium_status}\n🎯 나이 범위: {min_age}-{max_age}\n\n📊 **매치:** {gender_matches_used}/{gender_matches_limit}\n\n_성별은 영구적으로 잠깁니다_',
    'partner_found': "🎉 **파트너를 찾았습니다!**\n👤 이름: {name}\n🎂 나이: {age}\n🗣️ 언어: {lang}\n⚥ 성별: {gender}\n\n채팅을 시작하세요!",
    'name_saved': "👍 이름 저장됨: {text}\n\n🎂 이제 **나이**를 입력하세요 (숫자만, 예: 22):",
    'select_lang': "🗣️ 채팅 **언어**를 선택하세요:",
    'select_gender': "⚥ **성별**을 선택하세요 (나중에 변경할 수 없습니다):",
    'select_looking': "🎯 어떤 **파트너**를 찾고 계신가요?\n\n💡 **무료 사용자:** {gender_limit}회 선호 매치, 이후 무제한 랜덤!\n💎 **프리미엄:** 무제한 매치!",
    'invalid_age': "⚠️ 유효한 나이를 입력하세요 (15-99):",
    'invalid_lang_btn': "⚠️ 버튼에서 언어를 선택하세요.",
    'enter_min_age': "🎯 파트너의 **최소 나이**를 입력하세요 (예: 18):",
    'enter_max_age': "🎯 파트너의 **최대 나이**를 입력하세요 (예: 30):",
    'filter_updated': "✅ 파트너 나이 필터가 업데이트되었습니다!",
    'invalid_num': "⚠️ 유효한 숫자를 입력하세요.",
    'already_chat': "⚠️ 이미 채팅 중입니다!",
    'searching': "⏳ 파트너를 검색 중입니다, 잠시만 기다려주세요...",
    'search_start': "🔍 선호도에 따라 파트너를 검색 중입니다...",
    'search_cancel': "🛑 파트너 검색이 취소되었습니다.",
    'you_stopped': "🛑 채팅을 중지했습니다.",
    'partner_stopped': "🛑 파트너가 채팅을 중지했습니다.",
    'not_connected': "⚠️ 어떤 채팅에도 연결되어 있지 않습니다.",
    'partner_left': "🛑 파트너가 채팅을 나갔습니다.",
    'premium_txt': "💎 **프리미엄 VIP 멤버십**\n\n**혜택:**\n✅ 무제한 매치\n✅ 우선 대기열\n✅ 고급 필터\n\n**패키지:**\n⭐ 39 - 24시간 | ⭐ 149 - 3일\n⭐ 249 - 5일 | ⭐ 379 - 7일\n⭐ 499 - 14일 | ⭐ 799 - 30일\n\n패키지 선택:",
    'premium_purchase_success': "🎉 **프리미엄 활성화!**\n\n패키지: {package}\n기간: {days}일\n만료: {expiry}\n\n✨ 무제한 매치 잠금 해제!",
    'help_txt': "💡 **도움말 가이드:**\n\n**무료:** {limit}회 선호 매치 → 무제한 랜덤\n**프리미엄:** 무제한 선호 매치\n\n• 성별은 영구적으로 잠깁니다\n• 설정에서 언제든지 언어를 변경하세요\n• 부적절한 행동 신고",
    'start_chat_alert': "⚠️ 채팅을 시작하려면 '파트너 찾기'를 탭하세요.",
    'pic_verify_msg': "📸 **얼굴 인증**\n\n자신의 선명한 사진을 보내세요:",
    'pic_verify_success': "🎉 감사합니다! 프로필이 인증되었습니다!",
    'edit_name': "✍️ 이름 수정",
    'edit_age': "✍️ 나이 수정",
    'verify_pic': "📸 인증",
    'set_filter': "🎯 나이 필터",
    'gender_locked': "🔒 **성별 잠김**\n\n성별({gender})이 영구적으로 설정되어 변경할 수 없습니다.",
    'gender_permanently_locked': "⚠️ **성별을 변경할 수 없습니다**\n\n프로필 완료 시 성별({gender})이 영구적으로 설정되었습니다.",
    'profile_complete': "✅ **프로필 완료!**\n\n성별({gender})이 영구적으로 잠겼습니다.\n\n매칭을 시작하려면 '파트너 찾기'를 탭하세요!",
    'gender_limit_reached': "⚠️ **제한 도달!**\n\n모든 {limit}회 선호 매치를 사용했습니다.\n\n✅ 이제 **랜덤 모드** (무제한)!\n💎 무제한 선호 매치를 위해 프리미엄으로 업그레이드하세요!",
    'random_mode': "🔄 **랜덤 모드 활성화**\n\n무제한 랜덤 매치!\n💎 선호 매치를 위해 프리미엄을 받으세요!",
    'remaining_matches': "📊 남은 선호 매치: {remaining}",
    'language_changed': "✅ 언어가 {language}(으)로 변경되었습니다.\n\n모든 메시지가 이제 {language}(으)로 표시됩니다.",
    'select_new_lang': "🌐 **선호하는 언어를 선택하세요:**\n\n언제든지 언어를 변경할 수 있습니다.",
    'settings_menu': "⚙️ **설정 메뉴**\n\n아래에서 옵션을 선택하세요:",
    'back_to_menu': "🔙 메인 메뉴로 돌아가기"
}
# German Language (10th)
MESSAGES['german'] = {
    'welcome': "👋 Willkommen bei Mnuverse Bot!",
    'start': "👋 Willkommen bei Mnuverse Bot!\n\nBevor Sie beginnen, richten Sie Ihr Profil ein.\n\n📝 Bitte geben Sie Ihren Namen oder Spitznamen ein:",
    'already_reg': "🤖 Sie sind bereits registriert! Benutzen Sie das Menü unten.",
    'find': "🚀 Partner finden",
    'next': "⏭️ Nächster Partner",
    'stop': "🛑 Chat beenden",
    'profile': "⚙️ Mein Profil",
    'premium': "💎 Premium",
    'help_btn': "❓ Hilfe",
    'settings': "⚙️ Einstellungen",
    'change_lang': "🌐 Sprache ändern",
    'profile_txt': "⚙️ **Ihr Profil:**\n\n👤 Name: {name}\n🎂 Alter: {age}\n🗣️ Sprache: {lang}\n⚥ Geschlecht: {gender} 🔒\n🎯 Suche: {looking_for}\n🛡️ Verifizierung: {status}\n💎 Premium: {premium_status}\n🎯 Altersspanne: {min_age}-{max_age}\n\n📊 **Matches:** {gender_matches_used}/{gender_matches_limit}\n\n_Geschlecht ist dauerhaft gesperrt_',
    'partner_found': "🎉 **Partner gefunden!**\n👤 Name: {name}\n🎂 Alter: {age}\n🗣️ Sprache: {lang}\n⚥ Geschlecht: {gender}\n\nBeginnen Sie zu chatten!",
    'name_saved': "👍 Name gespeichert: {text}\n\n🎂 Geben Sie jetzt Ihr **Alter** ein (nur Zahlen, z.B. 22):",
    'select_lang': "🗣️ Wählen Sie Ihre Chat-**Sprache**:",
    'select_gender': "⚥ Wählen Sie Ihr **Geschlecht** (Dies kann später nicht geändert werden):",
    'select_looking': "🎯 Wen **suchen** Sie?\n\n💡 **Kostenlose Benutzer:** {gender_limit} Präferenz-Matches, dann unbegrenzt zufällig!\n💎 **Premium:** Unbegrenzte Matches!",
    'invalid_age': "⚠️ Bitte geben Sie ein gültiges Alter ein (15-99):",
    'invalid_lang_btn': "⚠️ Bitte wählen Sie eine Sprache aus den Schaltflächen.",
    'enter_min_age': "🎯 Geben Sie das **Mindestalter** für Partner ein (z.B. 18):",
    'enter_max_age': "🎯 Geben Sie das **Höchstalter** für Partner ein (z.B. 30):",
    'filter_updated': "✅ Altersfilter für Partner aktualisiert!",
    'invalid_num': "⚠️ Bitte geben Sie eine gültige Zahl ein.",
    'already_chat': "⚠️ Sie sind bereits in einem Chat!",
    'searching': "⏳ Suche nach Partner, bitte warten...",
    'search_start': "🔍 Suche nach Partner basierend auf Ihren Präferenzen...",
    'search_cancel': "🛑 Partnersuche abgebrochen.",
    'you_stopped': "🛑 Sie haben den Chat beendet.",
    'partner_stopped': "🛑 Ihr Partner hat den Chat beendet.",
    'not_connected': "⚠️ Sie sind mit keinem Chat verbunden.",
    'partner_left': "🛑 Ihr Partner hat den Chat verlassen.",
    'premium_txt': "💎 **Premium VIP Mitgliedschaft**\n\n**Vorteile:**\n✅ Unbegrenzte Matches\n✅ Prioritätswarteschlange\n✅ Erweiterte Filter\n\n**Pakete:**\n⭐ 39 - 24S | ⭐ 149 - 3T\n⭐ 249 - 5T | ⭐ 379 - 7T\n⭐ 499 - 14T | ⭐ 799 - 30T\n\nPaket auswählen:",
    'premium_purchase_success': "🎉 **Premium aktiviert!**\n\nPaket: {package}\nDauer: {days} Tage\nLäuft ab: {expiry}\n\n✨ Unbegrenzte Matches freigeschaltet!",
    'help_txt': "💡 **Hilfeleitfaden:**\n\n**Kostenlos:** {limit} Präferenz-Matches → unbegrenzt zufällig\n**Premium:** Unbegrenzte Präferenz-Matches\n\n• Geschlecht ist dauerhaft gesperrt\n• Ändern Sie die Sprache jederzeit in den Einstellungen\n• Melden Sie unangemessenes Verhalten",
    'start_chat_alert': "⚠️ Tippen Sie auf 'Partner finden', um den Chat zu starten.",
    'pic_verify_msg': "📸 **Gesichtsverifizierung**\n\nSenden Sie ein klares Foto von sich:",
    'pic_verify_success': "🎉 Danke! Ihr Profil ist VERIFIZIERT!",
    'edit_name': "✍️ Name bearbeiten",
    'edit_age': "✍️ Alter bearbeiten",
    'verify_pic': "📸 Verifizieren",
    'set_filter': "🎯 Altersfilter",
    'gender_locked': "🔒 **Geschlecht gesperrt**\n\nIhr Geschlecht ({gender}) ist dauerhaft festgelegt und kann nicht geändert werden.",
    'gender_permanently_locked': "⚠️ **Geschlecht kann nicht geändert werden**\n\nIhr Geschlecht ({gender}) wurde bei der Profilvervollständigung dauerhaft festgelegt.",
    'profile_complete': "✅ **Profil vollständig!**\n\nIhr Geschlecht ({gender}) ist jetzt dauerhaft gesperrt.\n\nTippen Sie auf 'Partner finden', um mit dem Matchen zu beginnen!",
    'gender_limit_reached': "⚠️ **Limit erreicht!**\n\nSie haben alle {limit} Präferenz-Matches verwendet.\n\n✅ Jetzt im **Zufallsmodus** (unbegrenzt)!\n💎 Upgraden Sie auf Premium für unbegrenzte Präferenz-Matches!",
    'random_mode': "🔄 **Zufallsmodus aktiv**\n\nUnbegrenzte zufällige Matches!\n💎 Holen Sie sich Premium für Präferenz-Matches!",
    'remaining_matches': "📊 Verbleibende Präferenz-Matches: {remaining}",
    'language_changed': "✅ Sprache geändert zu: {language}\n\nAlle Nachrichten werden jetzt in {language} angezeigt.",
    'select_new_lang': "🌐 **Wählen Sie Ihre bevorzugte Sprache:**\n\nSie können die Sprache jederzeit ändern.",
    'settings_menu': "⚙️ **Einstellungsmenü**\n\nWählen Sie unten eine Option:",
    'back_to_menu': "🔙 Zurück zum Hauptmenü"
}

# Italian Language (11th)
MESSAGES['italian'] = {
    'welcome': "👋 Benvenuto su Mnuverse Bot!",
    'start': "👋 Benvenuto su Mnuverse Bot!\n\nPrima di iniziare, configura il tuo profilo.\n\n📝 Inserisci il tuo nome o soprannome:",
    'already_reg': "🤖 Sei già registrato! Usa il menu qui sotto.",
    'find': "🚀 Cerca Partner",
    'next': "⏭️ Partner Successivo",
    'stop': "🛑 Ferma Chat",
    'profile': "⚙️ Il Mio Profilo",
    'premium': "💎 Premium",
    'help_btn': "❓ Aiuto",
    'settings': "⚙️ Impostazioni",
    'change_lang': "🌐 Cambia Lingua",
    'profile_txt': "⚙️ **Il Tuo Profilo:**\n\n👤 Nome: {name}\n🎂 Età: {age}\n🗣️ Lingua: {lang}\n⚥ Genere: {gender} 🔒\n🎯 Cerchi: {looking_for}\n🛡️ Verifica: {status}\n💎 Premium: {premium_status}\n🎯 Fascia d'età: {min_age}-{max_age}\n\n📊 **Match:** {gender_matches_used}/{gender_matches_limit}\n\n_Il genere è bloccato permanentemente_',
    'partner_found': "🎉 **Partner Trovato!**\n👤 Nome: {name}\n🎂 Età: {age}\n🗣️ Lingua: {lang}\n⚥ Genere: {gender}\n\nInizia a chattare!",
    'name_saved': "👍 Nome salvato: {text}\n\n🎂 Ora inserisci la tua **Età** (solo numeri, es: 22):",
    'select_lang': "🗣️ Seleziona la tua **Lingua** per chattare:",
    'select_gender': "⚥ Seleziona il tuo **Genere** (Questo non può essere modificato in seguito):",
    'select_looking': "🎯 Chi **cerchi**?\n\n💡 **Utenti Gratuiti:** {gender_limit} match di preferenza, poi illimitati casuali!\n💎 **Premium:** Match illimitati!",
    'invalid_age': "⚠️ Inserisci un'età valida (15-99):",
    'invalid_lang_btn': "⚠️ Seleziona una lingua dai pulsanti.",
    'enter_min_age': "🎯 Inserisci l'**Età Minima** per il partner (es: 18):",
    'enter_max_age': "🎯 Inserisci l'**Età Massima** per il partner (es: 30):",
    'filter_updated': "✅ Filtro età partner aggiornato!",
    'invalid_num': "⚠️ Inserisci un numero valido.",
    'already_chat': "⚠️ Sei già in una chat!",
    'searching': "⏳ Ricerca partner, attendere prego...",
    'search_start': "🔍 Ricerca partner in base alle tue preferenze...",
    'search_cancel': "🛑 Ricerca partner annullata.",
    'you_stopped': "🛑 Hai fermato la chat.",
    'partner_stopped': "🛑 Il tuo partner ha fermato la chat.",
    'not_connected': "⚠️ Non sei connesso a nessuna chat.",
    'partner_left': "🛑 Il tuo partner ha lasciato la chat.",
    'premium_txt': "💎 **Abbonamento Premium VIP**\n\n**Vantaggi:**\n✅ Match illimitati\n✅ Coda prioritaria\n✅ Filtri avanzati\n\n**Pacchetti:**\n⭐ 39 - 24O | ⭐ 149 - 3G\n⭐ 249 - 5G | ⭐ 379 - 7G\n⭐ 499 - 14G | ⭐ 799 - 30G\n\nSeleziona pacchetto:",
    'premium_purchase_success': "🎉 **Premium Attivato!**\n\nPacchetto: {package}\nDurata: {days} giorni\nScade: {expiry}\n\n✨ Match illimitati sbloccati!",
    'help_txt': "💡 **Guida di Aiuto:**\n\n**Gratuito:** {limit} match di preferenza → illimitati casuali\n**Premium:** Match di preferenza illimitati\n\n• Il genere è bloccato permanentemente\n• Cambia lingua in qualsiasi momento nelle Impostazioni\n• Segnala comportamenti inappropriati",
    'start_chat_alert': "⚠️ Tocca 'Cerca Partner' per iniziare a chattare.",
    'pic_verify_msg': "📸 **Verifica del Viso**\n\nInvia una foto chiara di te stesso:",
    'pic_verify_success': "🎉 Grazie! Il tuo profilo è VERIFICATO!",
    'edit_name': "✍️ Modifica Nome",
    'edit_age': "✍️ Modifica Età",
    'verify_pic': "📸 Verifica",
    'set_filter': "🎯 Filtro Età",
    'gender_locked': "🔒 **Genere Bloccato**\n\nIl tuo genere ({gender}) è impostato permanentemente e non può essere modificato.",
    'gender_permanently_locked': "⚠️ **Impossibile modificare il genere**\n\nIl tuo genere ({gender}) è stato impostato permanentemente al completamento del profilo.",
    'profile_complete': "✅ **Profilo Completo!**\n\nIl tuo genere ({gender}) è ora bloccato permanentemente.\n\nTocca 'Cerca Partner' per iniziare il match!",
    'gender_limit_reached': "⚠️ **Limite Raggiunto!**\n\nHai usato tutti i {limit} match di preferenza.\n\n✅ Ora in **modalità casuale** (illimitata)!\n💎 Passa a Premium per match di preferenza illimitati!",
    'random_mode': "🔄 **Modalità Casuale Attiva**\n\nMatch casuali illimitati!\n💎 Ottieni Premium per match di preferenza!",
    'remaining_matches': "📊 Match di preferenza rimanenti: {remaining}",
    'language_changed': "✅ Lingua cambiata in: {language}\n\nTutti i messaggi ora appariranno in {language}.",
    'select_new_lang': "🌐 **Seleziona la tua lingua preferita:**\n\nPuoi cambiare lingua in qualsiasi momento.",
    'settings_menu': "⚙️ **Menu Impostazioni**\n\nScegli un'opzione qui sotto:",
    'back_to_menu': "🔙 Torna al Menu Principale"
}

# Portuguese Language (12th)
MESSAGES['portuguese'] = {
    'welcome': "👋 Bem-vindo ao Mnuverse Bot!",
    'start': "👋 Bem-vindo ao Mnuverse Bot!\n\nAntes de começar, configure seu perfil.\n\n📝 Digite seu nome ou apelido:",
    'already_reg': "🤖 Você já está registrado! Use o menu abaixo.",
    'find': "🚀 Encontrar Parceiro",
    'next': "⏭️ Próximo Parceiro",
    'stop': "🛑 Parar Chat",
    'profile': "⚙️ Meu Perfil",
    'premium': "💎 Premium",
    'help_btn': "❓ Ajuda",
    'settings': "⚙️ Configurações",
    'change_lang': "🌐 Mudar Idioma",
    'profile_txt': "⚙️ **Seu Perfil:**\n\n👤 Nome: {name}\n🎂 Idade: {age}\n🗣️ Idioma: {lang}\n⚥ Gênero: {gender} 🔒\n🎯 Procurando: {looking_for}\n🛡️ Verificação: {status}\n💎 Premium: {premium_status}\n🎯 Faixa etária: {min_age}-{max_age}\n\n📊 **Correspondências:** {gender_matches_used}/{gender_matches_limit}\n\n_Gênero está permanentemente bloqueado_',
    'partner_found': "🎉 **Parceiro Encontrado!**\n👤 Nome: {name}\n🎂 Idade: {age}\n🗣️ Idioma: {lang}\n⚥ Gênero: {gender}\n\nComece a conversar!",
    'name_saved': "👍 Nome salvo: {text}\n\n🎂 Agora digite sua **Idade** (apenas números, ex: 22):",
    'select_lang': "🗣️ Selecione seu **Idioma** para conversar:",
    'select_gender': "⚥ Selecione seu **Gênero** (Isso não pode ser alterado depois):",
    'select_looking': "🎯 Quem você está **procurando**?\n\n💡 **Usuários Gratuitos:** {gender_limit} correspondências de preferência, depois aleatório ilimitado!\n💎 **Premium:** Correspondências ilimitadas!",
    'invalid_age': "⚠️ Digite uma idade válida (15-99):",
    'invalid_lang_btn': "⚠️ Selecione um idioma nos botões.",
    'enter_min_age': "🎯 Digite a **Idade Mínima** para o parceiro (ex: 18):",
    'enter_max_age': "🎯 Digite a **Idade Máxima** para o parceiro (ex: 30):",
    'filter_updated': "✅ Filtro de idade do parceiro atualizado!",
    'invalid_num': "⚠️ Digite um número válido.",
    'already_chat': "⚠️ Você já está em um chat!",
    'searching': "⏳ Procurando parceiro, aguarde...",
    'search_start': "🔍 Procurando parceiro com base em suas preferências...",
    'search_cancel': "🛑 Busca de parceiro cancelada.",
    'you_stopped': "🛑 Você parou o chat.",
    'partner_stopped': "🛑 Seu parceiro parou o chat.",
    'not_connected': "⚠️ Você não está conectado a nenhum chat.",
    'partner_left': "🛑 Seu parceiro saiu do chat.",
    'premium_txt': "💎 **Assinatura Premium VIP**\n\n**Benefícios:**\n✅ Correspondências ilimitadas\n✅ Fila prioritária\n✅ Filtros avançados\n\n**Pacotes:**\n⭐ 39 - 24H | ⭐ 149 - 3D\n⭐ 249 - 5D | ⭐ 379 - 7D\n⭐ 499 - 14D | ⭐ 799 - 30D\n\nSelecione o pacote:",
    'premium_purchase_success': "🎉 **Premium Ativado!**\n\nPacote: {package}\nDuração: {days} dias\nExpira: {expiry}\n\n✨ Correspondências ilimitadas desbloqueadas!",
    'help_txt': "💡 **Guia de Ajuda:**\n\n**Grátis:** {limit} correspondências de preferência → aleatório ilimitado\n**Premium:** Correspondências de preferência ilimitadas\n\n• Gênero está permanentemente bloqueado\n• Mude o idioma a qualquer momento nas Configurações\n• Denuncie comportamento inadequado",
    'start_chat_alert': "⚠️ Toque em 'Encontrar Parceiro' para começar a conversar.",
    'pic_verify_msg': "📸 **Verificação Facial**\n\nEnvie uma foto clara sua:",
    'pic_verify_success': "🎉 Obrigado! Seu perfil está VERIFICADO!",
    'edit_name': "✍️ Editar Nome",
    'edit_age': "✍️ Editar Idade",
    'verify_pic': "📸 Verificar",
    'set_filter': "🎯 Filtro de Idade",
    'gender_locked': "🔒 **Gênero Bloqueado**\n\nSeu gênero ({gender}) está definido permanentemente e não pode ser alterado.",
    'gender_permanently_locked': "⚠️ **Não é possível alterar o gênero**\n\nSeu gênero ({gender}) foi definido permanentemente quando você completou seu perfil.",
    'profile_complete': "✅ **Perfil Completo!**\n\nSeu gênero ({gender}) agora está permanentemente bloqueado.\n\nToque em 'Encontrar Parceiro' para começar a combinar!",
    'gender_limit_reached': "⚠️ **Limite Atingido!**\n\nVocê usou todas as {limit} correspondências de preferência.\n\n✅ Agora em **modo aleatório** (ilimitado)!\n💎 Atualize para Premium para correspondências de preferência ilimitadas!",
    'random_mode': "🔄 **Modo Aleatório Ativo**\n\nCorrespondências aleatórias ilimitadas!\n💎 Obtenha Premium para correspondências de preferência!",
    'remaining_matches': "📊 Correspondências de preferência restantes: {remaining}",
    'language_changed': "✅ Idioma alterado para: {language}\n\nTodas as mensagens agora aparecerão em {language}.",
    'select_new_lang': "🌐 **Selecione seu idioma preferido:**\n\nVocê pode alterar o idioma a qualquer momento.",
    'settings_menu': "⚙️ **Menu de Configurações**\n\nEscolha uma opção abaixo:",
    'back_to_menu': "🔙 Voltar ao Menu Principal"
}
# ==================== PART 6: HELPER FUNCTIONS AND HANDLERS ====================

def get_msg(user_id: int, key: str, **kwargs) -> str:
    """Get message in user's preferred language with automatic translation"""
    user_lang = users_profile.get(user_id, {}).get('lang', 'english')
    
    # Default to English if language not found
    if not user_lang or user_lang.lower() not in MESSAGES:
        user_lang = 'english'
    
    # Get message in user's language
    msg = MESSAGES.get(user_lang.lower(), MESSAGES['english']).get(key, MESSAGES['english'].get(key, key))
    
    # Format with kwargs if provided
    if kwargs:
        try:
            msg = msg.format(**kwargs)
        except:
            pass
    
    return msg


def is_premium(user_id: int) -> bool:
    """Check if user has active premium subscription"""
    p = users_profile.get(user_id, {})
    expiry_str = p.get('premium_expiry')
    if expiry_str:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < expiry_date:
            return True
    return False


def get_premium_expiry(user_id: int) -> Optional[datetime]:
    """Get premium expiry date"""
    p = users_profile.get(user_id, {})
    expiry_str = p.get('premium_expiry')
    if expiry_str:
        return datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
    return None


def is_profile_complete(user_id: int) -> bool:
    """Check if user profile is fully completed (gender locked)"""
    p = users_profile.get(user_id, {})
    return all([
        p.get('name'),
        p.get('age'),
        p.get('lang'),
        p.get('gender'),
        p.get('looking_for'),
        p.get('verified', False)
    ])


def is_gender_locked(user_id: int) -> bool:
    """Check if user's gender is locked (profile complete)"""
    return is_profile_complete(user_id)


def initialize_user_tracking(user_id: int):
    """Initialize match tracking for a user"""
    if user_id not in user_match_tracking:
        user_match_tracking[user_id] = {
            'gender_matches': {
                'male': 0,
                'female': 0,
                'gay': 0,
                'lesbian': 0
            },
            'last_reset': datetime.now().date(),
            'random_mode': False
        }


def reset_daily_tracking():
    """Reset tracking for new day"""
    today = datetime.now().date()
    for user_id, tracking in user_match_tracking.items():
        if tracking['last_reset'] != today:
            for gender in tracking['gender_matches']:
                tracking['gender_matches'][gender] = 0
            tracking['last_reset'] = today
            tracking['random_mode'] = False


def get_gender_match_limit(looking_for: str) -> int:
    """Get the match limit for a specific gender preference"""
    looking_lower = looking_for.lower()
    return FREE_USER_GENDER_MATCH_LIMITS.get(looking_lower, 5)


def can_match_with_preference(user_id: int, looking_for: str) -> bool:
    """Check if user can still match with gender preference"""
    if is_premium(user_id):
        return True
    
    if user_id in user_match_tracking and user_match_tracking[user_id].get('random_mode', False):
        return False
    
    initialize_user_tracking(user_id)
    reset_daily_tracking()
    
    looking_lower = looking_for.lower()
    current_usage = user_match_tracking[user_id]['gender_matches'].get(looking_lower, 0)
    limit = get_gender_match_limit(looking_for)
    
    return current_usage < limit


def increment_gender_match(user_id: int, looking_for: str) -> int:
    """Increment gender match count"""
    if is_premium(user_id):
        return 0
    
    initialize_user_tracking(user_id)
    reset_daily_tracking()
    
    looking_lower = looking_for.lower()
    limit = get_gender_match_limit(looking_for)
    
    user_match_tracking[user_id]['gender_matches'][looking_lower] += 1
    current_usage = user_match_tracking[user_id]['gender_matches'][looking_lower]
    
    if current_usage >= limit:
        user_match_tracking[user_id]['random_mode'] = True
    
    return current_usage


def get_remaining_gender_matches(user_id: int, looking_for: str) -> int:
    """Get remaining gender-specific matches"""
    if is_premium(user_id):
        return float('inf')
    
    initialize_user_tracking(user_id)
    reset_daily_tracking()
    
    looking_lower = looking_for.lower()
    current_usage = user_match_tracking[user_id]['gender_matches'].get(looking_lower, 0)
    limit = get_gender_match_limit(looking_for)
    
    remaining = limit - current_usage
    return max(0, remaining)


def is_random_mode(user_id: int) -> bool:
    """Check if user is in random match mode"""
    if is_premium(user_id):
        return False
    
    initialize_user_tracking(user_id)
    reset_daily_tracking()
    return user_match_tracking[user_id].get('random_mode', False)


def main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Create main menu keyboard"""
    keyboard = [
        [KeyboardButton(get_msg(user_id, 'find')), KeyboardButton(get_msg(user_id, 'next'))],
        [KeyboardButton(get_msg(user_id, 'stop')), KeyboardButton(get_msg(user_id, 'profile'))],
        [KeyboardButton(get_msg(user_id, 'premium')), KeyboardButton(get_msg(user_id, 'settings'))],
        [KeyboardButton(get_msg(user_id, 'help_btn'))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def language_selection_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard with all 12 languages"""
    keyboard = []
    row = []
    for i, lang in enumerate(AVAILABLE_LANGUAGES):
        button_text = f"{lang['flag']} {lang['name']}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"set_lang_{lang['code']}"))
        if (i + 1) % 2 == 0:  # 2 buttons per row
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)


def gender_keyboard() -> InlineKeyboardMarkup:
    """Create gender selection keyboard (permanent choice)"""
    keyboard = [
        [InlineKeyboardButton("👦 Male", callback_data="set_gender_male")],
        [InlineKeyboardButton("👧 Female", callback_data="set_gender_female")]
    ]
    return InlineKeyboardMarkup(keyboard)


def looking_keyboard(user_id: int = None, prefix: str = "looking_") -> InlineKeyboardMarkup:
    """Create looking for selection keyboard with limits info"""
    keyboard = []
    
    if user_id and is_premium(user_id):
        # Premium user - show all options
        keyboard = [
            [InlineKeyboardButton("👧 Girls", callback_data=f"{prefix}female")],
            [InlineKeyboardButton("👦 Boys", callback_data=f"{prefix}male")],
            [InlineKeyboardButton("🏳️‍🌈 Gay", callback_data=f"{prefix}gay")],
            [InlineKeyboardButton("🏳️‍🌈 Lesbian", callback_data=f"{prefix}lesbian")],
            [InlineKeyboardButton("🌍 Everyone (Random)", callback_data=f"{prefix}everyone")]
        ]
    else:
        # Free user - show options with limits
        keyboard = [
            [InlineKeyboardButton(f"👧 Girls ({FREE_USER_GENDER_MATCH_LIMITS['female']} matches)", callback_data=f"{prefix}female")],
            [InlineKeyboardButton(f"👦 Boys ({FREE_USER_GENDER_MATCH_LIMITS['male']} matches)", callback_data=f"{prefix}male")],
            [InlineKeyboardButton(f"🏳️‍🌈 Gay ({FREE_USER_GENDER_MATCH_LIMITS['gay']} matches)", callback_data=f"{prefix}gay")],
            [InlineKeyboardButton(f"🏳️‍🌈 Lesbian ({FREE_USER_GENDER_MATCH_LIMITS['lesbian']} matches)", callback_data=f"{prefix}lesbian")],
            [InlineKeyboardButton("🌍 Random (Unlimited)", callback_data=f"{prefix}everyone")],
            [InlineKeyboardButton("💎 Get Unlimited", callback_data="show_premium")]
        ]
    
    return InlineKeyboardMarkup(keyboard)


def premium_keyboard() -> InlineKeyboardMarkup:
    """Create premium packages keyboard"""
    keyboard = []
    row = []
    for i, (pkg_id, pkg) in enumerate(PREMIUM_PACKAGES.items()):
        row.append(InlineKeyboardButton(f"⭐ {pkg['stars']} - {pkg['name']}", callback_data=f"buy_{pkg_id}"))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


def settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Create settings keyboard"""
    keyboard = [
        [InlineKeyboardButton(get_msg(user_id, 'change_lang'), callback_data="change_language")],
        [InlineKeyboardButton(get_msg(user_id, 'back_to_menu'), callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Create profile edit keyboard (no gender edit)"""
    keyboard = [
        [InlineKeyboardButton(get_msg(user_id, 'edit_name'), callback_data="edit_name"),
         InlineKeyboardButton(get_msg(user_id, 'edit_age'), callback_data="edit_age")],
        [InlineKeyboardButton(get_msg(user_id, 'verify_pic'), callback_data="verify_pic"),
         InlineKeyboardButton(get_msg(user_id, 'set_filter'), callback_data="set_filter")]
    ]
    return InlineKeyboardMarkup(keyboard)


def check_premium_status(user_id: int) -> str:
    """Check if user has premium and return status string"""
    if is_premium(user_id):
        expiry = get_premium_expiry(user_id)
        if expiry:
            return f"✅ Active (Until: {expiry.strftime('%d %b %Y')})"
    return "❌ Not Premium"


async def notify_match(user_id: int, partner_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Send match notifications to both users"""
    user = users_profile[user_id]
    partner = users_profile[partner_id]
    
    user_msg = get_msg(user_id, 'partner_found').format(
        name=partner['name'], age=partner['age'], 
        lang=partner['lang'], gender=partner.get('gender', '')
    )
    partner_msg = get_msg(partner_id, 'partner_found').format(
        name=user['name'], age=user['age'],
        lang=user['lang'], gender=user.get('gender', '')
    )
    
    # Add match info for free users
    if not is_premium(user_id):
        remaining = get_remaining_gender_matches(user_id, user.get('looking_for', 'everyone'))
        if remaining > 0 and remaining != float('inf'):
            user_msg += f"\n\n{get_msg(user_id, 'remaining_matches').format(remaining=remaining)}"
        elif is_random_mode(user_id):
            user_msg += f"\n\n{get_msg(user_id, 'random_mode')}"
    
    if not is_premium(partner_id):
        remaining = get_remaining_gender_matches(partner_id, partner.get('looking_for', 'everyone'))
        if remaining > 0 and remaining != float('inf'):
            partner_msg += f"\n\n{get_msg(partner_id, 'remaining_matches').format(remaining=remaining)}"
        elif is_random_mode(partner_id):
            partner_msg += f"\n\n{get_msg(partner_id, 'random_mode')}"
    
    await context.bot.send_message(user_id, user_msg, reply_markup=main_menu_keyboard(user_id))
    await context.bot.send_message(partner_id, partner_msg, reply_markup=main_menu_keyboard(partner_id))


async def notify_limit_reached(user_id: int, context: ContextTypes.DEFAULT_TYPE, looking_for: str):
    """Notify user that they've reached their gender match limit"""
    limit = get_gender_match_limit(looking_for)
    msg = get_msg(user_id, 'gender_limit_reached').format(limit=limit)
    await context.bot.send_message(user_id, msg, parse_mode='Markdown')


async def notify_random_mode(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Notify user that they're now in random match mode"""
    msg = get_msg(user_id, 'random_mode')
    await context.bot.send_message(user_id, msg, parse_mode='Markdown')


async def show_profile(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile with match tracking info"""
    p = users_profile[user_id]
    status = "✅ Verified" if p.get('verified', False) else "❌ Not Verified"
    premium_status = check_premium_status(user_id)
    
    looking_for = p.get('looking_for', 'everyone')
    
    if is_premium(user_id):
        gender_matches_used = "∞"
        gender_matches_limit = "∞"
    else:
        initialize_user_tracking(user_id)
        reset_daily_tracking()
        looking_lower = looking_for.lower()
        current_usage = user_match_tracking[user_id]['gender_matches'].get(looking_lower, 0)
        limit = get_gender_match_limit(looking_for)
        gender_matches_used = str(current_usage)
        gender_matches_limit = str(limit) if limit != float('inf') else "Unlimited"
    
    text = get_msg(user_id, 'profile_txt').format(
        name=p['name'], age=p['age'], lang=p['lang'],
        gender=p.get('gender', 'Not Set'), looking_for=looking_for.capitalize(),
        status=status, premium_status=premium_status,
        min_age=p.get('target_age_min', 18), max_age=p.get('target_age_max', 50),
        gender_matches_used=gender_matches_used, gender_matches_limit=gender_matches_limit
    )
    
    await context.bot.send_message(
        user_id, text, parse_mode='Markdown',
        reply_markup=profile_keyboard(user_id)
    )


def match_users(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Match users based on preferences and premium status"""
    user = users_profile.get(user_id)
    if not user:
        return False
    
    user_looking = user.get('looking_for', 'everyone').lower()
    is_user_random_mode = is_random_mode(user_id)
    
    for potential_id in waiting_room[:]:
        if potential_id == user_id:
            continue
        
        partner = users_profile.get(potential_id)
        if not partner:
            waiting_room.remove(potential_id)
            continue
        
        # Age match check
        age_match = (user['target_age_min'] <= partner['age'] <= user['target_age_max'] and
                    partner['target_age_min'] <= user['age'] <= partner['target_age_max'])
        
        # Language match check
        lang_match = user['lang'].lower() == partner['lang'].lower()
        
        # Gender preference matching logic
        gender_match = False
        partner_looking = partner.get('looking_for', 'everyone').lower()
        is_partner_random_mode = is_random_mode(potential_id)
        
        if is_user_random_mode or is_partner_random_mode or user_looking == 'everyone' or partner_looking == 'everyone':
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
        
        if age_match and lang_match and gender_match:
            # Check if user can still use gender preference
            if not is_random_mode(user_id) and user_looking != 'everyone':
                if not can_match_with_preference(user_id, user_looking):
                    user_match_tracking[user_id]['random_mode'] = True
                    asyncio.create_task(notify_random_mode(user_id, context))
                    continue
            
            # Remove both from waiting room
            waiting_room.remove(potential_id)
            if user_id in waiting_room:
                waiting_room.remove(user_id)
            
            # Increment match counters if using gender preference
            if not is_random_mode(user_id) and user_looking != 'everyone':
                used = increment_gender_match(user_id, user_looking)
                remaining = get_remaining_gender_matches(user_id, user_looking)
                
                if remaining == 0:
                    asyncio.create_task(notify_limit_reached(user_id, context, user_looking))
            
            if not is_random_mode(potential_id) and partner_looking != 'everyone':
                increment_gender_match(potential_id, partner_looking)
            
            # Create chat connection
            active_chats[user_id] = potential_id
            active_chats[potential_id] = user_id
            
            # Notify both users
            asyncio.create_task(notify_match(user_id, potential_id, context))
            return True
    
    return False


# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    if user_id not in users_profile:
        users_profile[user_id] = {
            'name': None, 'age': None, 'lang': None, 'gender': None,
            'looking_for': 'everyone', 'verified': False, 'premium_expiry': None,
            'target_age_min': 18, 'target_age_max': 50
        }
        user_states[user_id] = RegState.WAITING_NAME
        await update.message.reply_text(MESSAGES['english']['start'])
    else:
        await update.message.reply_text(
            get_msg(user_id, 'already_reg'),
            reply_markup=main_menu_keyboard(user_id)
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    user_id = update.effective_user.id
    if user_id in user_states:
        del user_states[user_id]
    await update.message.reply_text("Operation cancelled.", reply_markup=main_menu_keyboard(user_id))
    return ConversationHandler.END


# ==================== MESSAGE HANDLERS ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Handle registration states
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == RegState.WAITING_NAME:
            users_profile[user_id]['name'] = text
            await update.message.reply_text(get_msg(user_id, 'name_saved').format(text=text))
            user_states[user_id] = RegState.WAITING_AGE
            return
        
        elif state == RegState.WAITING_AGE:
            if text.isdigit() and 15 <= int(text) <= 99:
                users_profile[user_id]['age'] = int(text)
                await update.message.reply_text(
                    get_msg(user_id, 'select_lang'),
                    reply_markup=language_selection_keyboard()
                )
                user_states[user_id] = RegState.WAITING_LANG
            else:
                await update.message.reply_text(get_msg(user_id, 'invalid_age'))
            return
        
        elif state == RegState.WAITING_TARGET_AGE_MIN:
            if text.isdigit() and 15 <= int(text) <= 99:
                users_profile[user_id]['target_age_min'] = int(text)
                await update.message.reply_text(get_msg(user_id, 'enter_max_age'))
                user_states[user_id] = RegState.WAITING_TARGET_AGE_MAX
            else:
                await update.message.reply_text(get_msg(user_id, 'invalid_num'))
            return
        
        elif state == RegState.WAITING_TARGET_AGE_MAX:
            if text.isdigit() and int(text) > users_profile[user_id]['target_age_min']:
                users_profile[user_id]['target_age_max'] = int(text)
                del user_states[user_id]
                await update.message.reply_text(
                    get_msg(user_id, 'filter_updated'),
                    reply_markup=main_menu_keyboard(user_id)
                )
                await show_profile(user_id, context)
            else:
                await update.message.reply_text(get_msg(user_id, 'invalid_num'))
            return
        
        elif state == RegState.WAITING_EDIT_NAME:
            users_profile[user_id]['name'] = text
            del user_states[user_id]
            await update.message.reply_text("✅ Name updated!", reply_markup=main_menu_keyboard(user_id))
            await show_profile(user_id, context)
            return
        
        elif state == RegState.WAITING_EDIT_AGE:
            if text.isdigit() and 15 <= int(text) <= 99:
                users_profile[user_id]['age'] = int(text)
                del user_states[user_id]
                await update.message.reply_text("✅ Age updated!", reply_markup=main_menu_keyboard(user_id))
                await show_profile(user_id, context)
            else:
                await update.message.reply_text(get_msg(user_id, 'invalid_age'))
            return
    
    # Handle main menu commands
    if text in ["🚀 Find Partner", get_msg(user_id, 'find')]:
        if user_id in active_chats:
            await update.message.reply_text(get_msg(user_id, 'already_chat'))
            return
        if user_id in waiting_room:
            await update.message.reply_text(get_msg(user_id, 'searching'))
            return
        
        # Show match info
        looking_for = users_profile[user_id].get('looking_for', 'everyone')
        if not is_premium(user_id) and looking_for != 'everyone':
            remaining = get_remaining_gender_matches(user_id, looking_for)
            if remaining > 0:
                await update.message.reply_text(
                    get_msg(user_id, 'remaining_matches').format(remaining=remaining),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    get_msg(user_id, 'random_mode'),
                    parse_mode='Markdown'
                )
        
        waiting_room.append(user_id)
        await update.message.reply_text(get_msg(user_id, 'search_start'))
        
        if not match_users(user_id, context):
            # Wait for match
            pass
    
    elif text in ["🛑 Stop Chat", get_msg(user_id, 'stop')]:
        if user_id in waiting_room:
            waiting_room.remove(user_id)
            await update.message.reply_text(get_msg(user_id, 'search_cancel'))
        elif user_id in active_chats:
            partner_id = active_chats[user_id]
            del active_chats[user_id]
            del active_chats[partner_id]
            await update.message.reply_text(get_msg(user_id, 'you_stopped'))
            await context.bot.send_message(partner_id, get_msg(partner_id, 'partner_stopped'))
        else:
            await update.message.reply_text(get_msg(user_id, 'not_connected'))
    
    elif text in ["⏭️ Next Partner", get_msg(user_id, 'next')]:
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            del active_chats[user_id]
            del active_chats[partner_id]
            await context.bot.send_message(partner_id, get_msg(partner_id, 'partner_left'))
        
        if user_id in waiting_room:
            waiting_room.remove(user_id)
        
        waiting_room.append(user_id)
        await update.message.reply_text(get_msg(user_id, 'searching'))
        match_users(user_id, context)
    
    elif text in ["⚙️ My Profile", get_msg(user_id, 'profile')]:
        await show_profile(user_id, context)
    
    elif text in ["💎 Premium", get_msg(user_id, 'premium')]:
        await update.message.reply_text(
            get_msg(user_id, 'premium_txt'),
            parse_mode='Markdown',
            reply_markup=premium_keyboard()
        )
    
    elif text in ["⚙️ Settings", get_msg(user_id, 'settings')]:
        await update.message.reply_text(
            get_msg(user_id, 'settings_menu'),
            reply_markup=settings_keyboard(user_id)
        )
    
    elif text in ["❓ Help", get_msg(user_id, 'help_btn')]:
        limit = FREE_USER_GENDER_MATCH_LIMITS.get(
            users_profile[user_id].get('looking_for', 'everyone'), 5
        )
        await update.message.reply_text(
            get_msg(user_id, 'help_txt').format(limit=limit),
            parse_mode='Markdown'
        )
    
    else:
        # Forward message to partner if in chat
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            await context.bot.send_message(partner_id, text)
        else:
            await update.message.reply_text(get_msg(user_id, 'start_chat_alert'))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    user_id = update.effective_user.id
    
    # Handle verification photo
    if user_id in user_states and user_states[user_id] == RegState.WAITING_VERIFY_PIC:
        users_profile[user_id]['verified'] = True
        del user_states[user_id]
        
        # Check if profile is now complete
        if is_profile_complete(user_id):
            await update.message.reply_text(
                get_msg(user_id, 'profile_complete').format(gender=users_profile[user_id].get('gender', '')),
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard(user_id)
            )
        else:
            await update.message.reply_text(
                get_msg(user_id, 'pic_verify_success'),
                reply_markup=main_menu_keyboard(user_id)
            )
        return
    
    # Forward photo to partner
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        photo = update.message.photo[-1]
        await context.bot.send_photo(partner_id, photo.file_id, caption=update.message.caption)
    else:
        await update.message.reply_text(get_msg(user_id, 'not_connected'))


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_voice(partner_id, update.message.voice.file_id)
    else:
        await update.message.reply_text(get_msg(user_id, 'not_connected'))


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video messages"""
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_video(partner_id, update.message.video.file_id)
    else:
        await update.message.reply_text(get_msg(user_id, 'not_connected'))


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sticker messages"""
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_sticker(partner_id, update.message.sticker.file_id)
    else:
        await update.message.reply_text(get_msg(user_id, 'not_connected'))


# ==================== CALLBACK QUERY HANDLER ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # ========== LANGUAGE SELECTION ==========
    if data.startswith("set_lang_"):
        lang_code = data.replace("set_lang_", "")
        lang_name = next((l['name'] for l in AVAILABLE_LANGUAGES if l['code'] == lang_code), lang_code)
        users_profile[user_id]['lang'] = lang_code
        await query.edit_message_text(get_msg(user_id, 'language_changed').format(language=lang_name))
        if user_id in user_states and user_states[user_id] == RegState.WAITING_LANG:
            user_states[user_id] = RegState.WAITING_GENDER
            await query.message.reply_text(get_msg(user_id, 'select_gender'), reply_markup=gender_keyboard())
        else:
            await query.message.reply_text(get_msg(user_id, 'welcome'), reply_markup=main_menu_keyboard(user_id))
        return
    
    # ========== GENDER SELECTION (PERMANENT) ==========
    if data.startswith("set_gender_"):
        if is_gender_locked(user_id):
            await query.message.reply_text(get_msg(user_id, 'gender_permanently_locked').format(gender=users_profile[user_id].get('gender', '')))
            return
        gender = "Male" if "male" in data else "Female"
        users_profile[user_id]['gender'] = gender
        limit = FREE_USER_GENDER_MATCH_LIMITS.get('female' if gender == 'Female' else 'male', 5)
        await query.edit_message_text(get_msg(user_id, 'select_looking').format(gender_limit=limit))
        await query.message.reply_text(get_msg(user_id, 'select_looking').format(gender_limit=limit), reply_markup=looking_keyboard(user_id, "reg_looking_"))
        user_states[user_id] = RegState.WAITING_LOOKING
        return
    
    # ========== LOOKING FOR SELECTION (REGISTRATION) ==========
    if data.startswith("reg_looking_"):
        looking = data.replace("reg_looking_", "").capitalize()
        if not is_premium(user_id) and looking != "Everyone" and looking != "Random":
            remaining = get_remaining_gender_matches(user_id, looking)
            if remaining <= 0:
                await query.message.reply_text(get_msg(user_id, 'gender_limit_reached').format(limit=FREE_USER_GENDER_MATCH_LIMITS.get(looking.lower(), 5)))
                return
        users_profile[user_id]['looking_for'] = looking
        await query.edit_message_text(get_msg(user_id, 'pic_verify_msg'))
        await query.message.reply_text(get_msg(user_id, 'pic_verify_msg'))
        user_states[user_id] = RegState.WAITING_VERIFY_PIC
        return
    
    # ========== EDIT LOOKING FOR (AFTER REGISTRATION) ==========
    if data.startswith("edit_looking_"):
        looking = data.replace("edit_looking_", "").capitalize()
        if not is_premium(user_id) and looking != "Everyone" and looking != "Random":
            remaining = get_remaining_gender_matches(user_id, looking)
            if remaining <= 0:
                await query.message.reply_text(get_msg(user_id, 'gender_limit_reached').format(limit=FREE_USER_GENDER_MATCH_LIMITS.get(looking.lower(), 5)))
                return
        users_profile[user_id]['looking_for'] = looking
        await query.edit_message_text("✅ Preferences updated!")
        await show_profile(user_id, context)
        return
    
    # ========== EDIT GENDER (PREMIUM ONLY) ==========
    if data.startswith("edit_gender_"):
        if not is_premium(user_id):
            await query.message.reply_text(get_msg(user_id, 'premium_only_feature'), reply_markup=main_menu_keyboard(user_id))
            return
        gender = data.replace("edit_gender_", "").capitalize()
        users_profile[user_id]['gender'] = gender
        await query.edit_message_text("✅ Gender updated!")
        await query.message.reply_text(get_msg(user_id, 'select_looking'), reply_markup=looking_keyboard(user_id, "edit_looking_"))
        return
    
    # ========== EDIT PROFILE OPTIONS ==========
    if data == "edit_name":
        await query.edit_message_text("✍️ Send your new name:")
        user_states[user_id] = RegState.WAITING_EDIT_NAME
        return
    
    if data == "edit_age":
        await query.edit_message_text("🎂 Send your new age (15-99):")
        user_states[user_id] = RegState.WAITING_EDIT_AGE
        return
    
    if data == "verify_pic":
        await query.edit_message_text(get_msg(user_id, 'pic_verify_msg'))
        user_states[user_id] = RegState.WAITING_VERIFY_PIC
        return
    
    if data == "set_filter":
        await query.edit_message_text(get_msg(user_id, 'enter_min_age'))
        user_states[user_id] = RegState.WAITING_TARGET_AGE_MIN
        return
    
    # ========== SETTINGS ==========
    if data == "change_language":
        await query.edit_message_text(get_msg(user_id, 'select_new_lang'), reply_markup=language_selection_keyboard())
        return
    
    if data == "back_to_main":
        await query.edit_message_text(get_msg(user_id, 'welcome'))
        await query.message.reply_text(get_msg(user_id, 'welcome'), reply_markup=main_menu_keyboard(user_id))
        return
    
    # ========== PREMIUM ==========
    if data == "show_premium":
        await query.message.reply_text(get_msg(user_id, 'premium_txt'), parse_mode='Markdown', reply_markup=premium_keyboard())
        return
    
    if data.startswith("buy_"):
        pkg_id = data.replace("buy_", "")
        pkg = PREMIUM_PACKAGES.get(pkg_id)
        if pkg:
            title = f"Mnuverse VIP: {pkg['name']}"
            description = f"Get premium access for {pkg['days']} days"
            payload = f"premium_{pkg_id}"
            currency = "XTR"
            prices = [LabeledPrice(label=pkg['name'], amount=pkg['stars'])]
            await context.bot.send_invoice(user_id, title, description, payload, provider_token="", currency=currency, prices=prices)
        return


# ==================== PAYMENT HANDLERS ====================

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query"""
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment"""
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    
    if payload.startswith("premium_"):
        pkg_id = payload.replace("premium_", "")
        pkg = PREMIUM_PACKAGES.get(pkg_id)
        
        if pkg:
            current_expiry = users_profile[user_id].get('premium_expiry')
            if current_expiry:
                start_date = max(datetime.now(), datetime.strptime(current_expiry, "%Y-%m-%d %H:%M:%S"))
            else:
                start_date = datetime.now()
            
            new_expiry = start_date + timedelta(days=pkg['days'])
            users_profile[user_id]['premium_expiry'] = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
            
            # Reset random mode for premium user
            if user_id in user_match_tracking:
                user_match_tracking[user_id]['random_mode'] = False
            
            await update.message.reply_text(
                get_msg(user_id, 'premium_purchase_success').format(
                    package=pkg['name'],
                    days=pkg['days'],
                    expiry=new_expiry.strftime('%d %b %Y')
                ),
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard(user_id)
            )


# ==================== MAIN FUNCTION ====================

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    
    # Start Flask server for health checks (for deployment)
    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start bot
    print("=" * 50)
    print("🤖 Mnuverse Bot is Starting...")
    print("=" * 50)
    print(f"📊 Total Languages Supported: {len(AVAILABLE_LANGUAGES)}")
    print("🌐 Languages available:")
    for lang in AVAILABLE_LANGUAGES:
        print(f"   {lang['flag']} {lang['name']}")
    print("=" * 50)
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
