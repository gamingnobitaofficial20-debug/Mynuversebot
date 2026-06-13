import os
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Running..."

BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

users_profile = {}  
waiting_room = []   
active_chats = {}   
user_states = {}    

def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🚀 Find Partner"), KeyboardButton("⏭️ Next Partner"))
    markup.row(KeyboardButton("🛑 Stop Chat"), KeyboardButton("⚙️ My Profile & Filters"))
    markup.row(KeyboardButton("💎 Premium"), KeyboardButton("❓ Help"))
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.chat.id
    if user_id not in users_profile:
        users_profile[user_id] = {'name': None, 'age': None, 'lang': None, 'verified': False, 'target_age_min': 18, 'target_age_max': 50}
        bot.send_message(user_id, "👋 Welcome to Mnuverse Bot!\n\nBefore starting, you need to set up your profile.\n\n📝 Please enter your Name or a Nickname:")
        user_states[user_id] = 'WAITING_NAME'
    else:
        bot.send_message(user_id, "🤖 You are already registered! Use the menu below.", reply_markup=main_menu_keyboard())

def show_profile(user_id):
    p = users_profile[user_id]
    status = "✅ Verified" if p['verified'] else "❌ Not Verified"
    text = (
        "⚙️ **Your Profile & Filters:**\n\n"
        f"👤 Name: {p['name']}\n"
        f"🎂 Age: {p['age']}\n"
        f"🗣️ Language: {p['lang']}\n"
        f"🛡️ Verification: {status}\n"
        f"🎯 Partner Age Range: {p['target_age_min']} - {p['target_age_max']} years\n\n"
        "Click the buttons below to change your information."
    )
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("✍️ Edit Name", callback_data="edit_name"), InlineKeyboardButton("✍️ Edit Age", callback_data="edit_age"))
    markup.row(InlineKeyboardButton("🗣️ Edit Language", callback_data="edit_lang"), InlineKeyboardButton("📸 Verify Profile Pic", callback_data="verify_pic"))
    markup.row(InlineKeyboardButton("🎯 Set Partner Age Filter", callback_data="edit_target_age"))
    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=markup)

def match_users(user_id):
    p = users_profile[user_id]
    for potential_partner in waiting_room:
        if potential_partner != user_id:
            partner_p = users_profile[potential_partner]
            if (p['target_age_min'] <= partner_p['age'] <= p['target_age_max']) and \
               (partner_p['target_age_min'] <= p['age'] <= partner_p['target_age_max']) and \
               (p['lang'] == partner_p['lang']):
                waiting_room.remove(potential_partner)
                if user_id in waiting_room:
                    waiting_room.remove(user_id)
                active_chats[user_id] = potential_partner
                active_chats[potential_partner] = user_id
                bot.send_message(user_id, f"🎉 **Partner Found!**\n👤 Name: {partner_p['name']}\n🎂 Age: {partner_p['age']}\n🗣️ Language: {partner_p['lang']}\n\nYou can chat now.", reply_markup=main_menu_keyboard())
                bot.send_message(potential_partner, f"🎉 **Partner Found!**\n👤 Name: {p['name']}\n🎂 Age: {p['age']}\n🗣️ Language: {p['lang']}\n\nYou can chat now.", reply_markup=main_menu_keyboard())
                return True
    return False

@bot.message_handler(func=lambda message: True)
def handle_all_texts(message):
    user_id = message.chat.id
    text = message.text

    if user_id in user_states:
        state = user_states[user_id]
        if state == 'WAITING_NAME':
            users_profile[user_id]['name'] = text
            bot.send_message(user_id, f"👍 Name saved: {text}\n\n🎂 Now enter your **Age** (Numbers only, e.g., 22):")
            user_states[user_id] = 'WAITING_AGE'
            return
        elif state == 'WAITING_AGE':
            if text.isdigit() and 15 <= int(text) <= 99:
                users_profile[user_id]['age'] = int(text)
                markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                markup.row(KeyboardButton("Bangla"), KeyboardButton("English"))
                bot.send_message(user_id, "🗣️ Select your chatting **Language**:", reply_markup=markup)
                user_states[user_id] = 'WAITING_LANG'
            else:
                bot.send_message(user_id, "⚠️ Please enter a valid age (numbers between 15 and 99):")
            return
        elif state == 'WAITING_LANG':
            if text in ["Bangla", "English"]:
                users_profile[user_id]['lang'] = text
                del user_states[user_id]
                bot.send_message(user_id, "🎉 Profile setup completed! You are now ready to chat.\n\n💡 Tap '⚙️ My Profile & Filters' to verify your profile pic or set partner filters.", reply_markup=main_menu_keyboard())
            else:
                bot.send_message(user_id, "⚠️ Please select 'Bangla' or 'English' from the buttons below.")
            return
        elif state == 'WAITING_TARGET_AGE_MIN':
            if text.isdigit():
                users_profile[user_id]['target_age_min'] = int(text)
                bot.send_message(user_id, "🎯 Now enter the **Maximum Age** of your partner (e.g., 30):")
                user_states[user_id] = 'WAITING_TARGET_AGE_MAX'
            else:
                bot.send_message(user_id, "⚠️ Please enter a valid number:")
            return
        elif state == 'WAITING_TARGET_AGE_MAX':
            if text.isdigit():
                users_profile[user_id]['target_age_max'] = int(text)
                del user_states[user_id]
                bot.send_message(user_id, "✅ Partner age filter successfully updated!", reply_markup=main_menu_keyboard())
                show_profile(user_id)
            else:
                bot.send_message(user_id, "⚠️ Please enter a valid number:")
            return

    if user_id not in users_profile or users_profile[user_id]['name'] is None:
        start_cmd(message)
        return

    if text == "🚀 Find Partner":
        if user_id in active_chats:
            bot.send_message(user_id, "⚠️ You are already in a chat!")
            return
        if user_id in waiting_room:
            bot.send_message(user_id, "⏳ Searching for a partner, please wait...")
            return
        waiting_room.append(user_id)
        bot.send_message(user_id, "🔍 Searching for a partner based on your filters...")
        match_users(user_id)
    elif text == "🛑 Stop Chat":
        if user_id in waiting_room:
            waiting_room.remove(user_id)
            bot.send_message(user_id, "🛑 Partner search cancelled.")
        elif user_id in active_chats:
            partner_id = active_chats[user_id]
            del active_chats[user_id]
            del active_chats[partner_id]
            bot.send_message(user_id, "🛑 You stopped the chat.")
            bot.send_message(partner_id, "🛑 Your partner stopped the chat.")
        else:
            bot.send_message(user_id, "⚠️ You are not connected to any chat.")
    elif text == "⏭️ Next Partner":
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            del active_chats[user_id]
            del active_chats[partner_id]
            bot.send_message(partner_id, "🛑 Your partner left the chat.")
        if user_id in waiting_room:
            waiting_room.remove(user_id)
        bot.send_message(user_id, "⏭️ Searching for a new partner...")
        waiting_room.append(user_id)
        match_users(user_id)
    elif text == "⚙️ My Profile & Filters":
        show_profile(user_id)
    elif text == "💎 Premium":
        bot.send_message(user_id, "💎 **Premium Features:**\n\nPremium features are under development. Direct gender filters (Male/Female) will be added very soon!")
    elif text == "❓ Help":
        bot.send_message(user_id, "💡 **Help Guide:**\n\n• Tap '🚀 Find Partner' to start a chat.\n• Tap '⏭️ Next Partner' to change partner.\n• Any abusive or inappropriate behavior will lead to an account ban.")
    else:
        if user_id in active_chats:
            bot.send_message(active_chats[user_id], text)
        else:
            bot.send_message(user_id, "⚠️ Tap '🚀 Find Partner' to start a chat.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    bot.delete_message(user_id, call.message.message_id)
    
    if call.data == "edit_name":
        bot.send_message(user_id, "✍️ Enter your new name or nickname:")
        user_states[user_id] = 'WAITING_NAME'
    elif call.data == "edit_age":
        bot.send_message(user_id, "🎂 Enter your new age in numbers:")
        user_states[user_id] = 'WAITING_AGE'
    elif call.data == "edit_lang":
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row(KeyboardButton("Bangla"), KeyboardButton("English"))
        bot.send_message(user_id, "🗣️ Change language:", reply_markup=markup)
        user_states[user_id] = 'WAITING_LANG'
    elif call.data == "edit_target_age":
        bot.send_message(user_id, "🎯 What is the **Minimum Age** (e.g., 18) you prefer for a partner?")
        user_states[user_id] = 'WAITING_TARGET_AGE_MIN'
    elif call.data == "verify_pic":
        bot.send_message(user_id, "📸 **Face Verification:**\n\nPlease send a clear picture of yourself or a live face photo.")
        user_states[user_id] = 'WAITING_VERIFY_PIC'

@bot.message_handler(content_types=['photo', 'sticker', 'voice', 'video'])
def handle_media(message):
    user_id = message.chat.id
    
    if user_id in user_states and user_states[user_id] == 'WAITING_VERIFY_PIC' and message.content_type == 'photo':
        users_profile[user_id]['verified'] = True  
        del user_states[user_id]
        bot.send_message(user_id, "🎉 Thank you! Your picture has been received and your profile is now Verified.", reply_markup=main_menu_keyboard())
        return

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        if message.content_type == 'photo':
            bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption)
        elif message.content_type == 'sticker':
            bot.send_sticker(partner_id, message.sticker.file_id)
        elif message.content_type == 'voice':
            bot.send_voice(partner_id, message.voice.file_id)
        elif message.content_type == 'video':
            bot.send_video(partner_id, message.video.file_id)
    else:
        bot.send_message(user_id, "⚠️ You are not currently connected to any chat.")

if __name__ == "__main__":
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
