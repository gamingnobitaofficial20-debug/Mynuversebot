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

AVAILABLE_LANGUAGES = ["Bangla", "English", "Hindi", "Japanese", "Russian", "Arabic", "Spanish", "French", "Korean"]

MESSAGES = {
    'bangla': {
        'start': "👋 Mnuverse Bot-এ আপনাকে স্বাগতম!\n\nচ্যাট শুরু করার আগে আপনার প্রোফাইল সেটআপ করতে হবে।\n\n📝 আপনার **নাম** বা একটি নিকনেম (Nickname) লিখুন:",
        'already_reg': "🤖 আপনি অলরেডি রেজিস্টার্ড আছেন! নিচের মেনু ব্যবহার করুন.",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **Your Profile & Filters:**\n\n👤 Name: {name}\n🎂 Age: {age}\n🗣️ Language: {lang}\n🛡️ Verification: {status}\n🎯 Partner Age Range: {min_age} - {max_age} years\n\nনিচের বাটনে ক্লিক করে যেকোনো তথ্য পরিবর্তন করতে পারেন.",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **পার্টনার পাওয়া গেছে!**\n👤 নাম: {name}\n🎂 বয়স: {age}\n🗣️ ভাষা: {lang}\n\nএখন চ্যাট করতে পারেন.",
        'name_saved': "👍 নাম সেভ হয়েছে: {text}\n\n🎂 এবার আপনার **বয়স** (শুধু সংখ্যায়, যেমন: 22) লিখুন:",
        'select_lang': "🗣️ নিচের বাটন থেকে আপনার চ্যাটিংয়ের **ভাষা** সিলেক্ট করুন:",
        'invalid_age': "⚠️ দয়া করে সঠিক বয়স দিন (১৫ থেকে ৯৯ এর মধ্যে সংখ্যা লিখুন):",
        'invalid_lang_btn': "⚠️ নিচের বাটন থেকে একটি ভাষা সিলেক্ট করুন.",
        'enter_min_age': "🎯 পার্টনারের **সর্বনিম্ন বয়স** (Minimum Age, যেমন: 18) কত চান?",
        'enter_max_age': "🎯 এবার পার্টনারের **সর্বোচ্চ বয়স** (Maximum Age, যেমন: 30) লিখুন:",
        'filter_updated': "✅ পার্টনারের বয়স ফিল্টার সাকসেসফুলি আপডেট হয়েছে!",
        'invalid_num': "⚠️ সঠিক সংখ্যা লিখুন:",
        'already_chat': "⚠️ আপনি অলরেডি চ্যাটে আছেন!",
        'searching': "⏳ পার্টনার খোঁজা হচ্ছে, দয়া করে অপেক্ষা করুন...",
        'search_start': "🔍 আপনার ফিল্টার অনুযায়ী পার্টনার খোঁজা হচ্ছে...",
        'search_cancel': "🛑 পার্টনার খোঁজা বাতিল করা হয়েছে।",
        'you_stopped': "🛑 আপনি চ্যাট বন্ধ করেছেন।",
        'partner_stopped': "🛑 আপনার পার্টনার চ্যাট বন্ধ করে দিয়েছে।",
        'not_connected': "⚠️ আপনি কোনো চ্যাটে যুক্ত নেই।",
        'partner_left': "🛑 আপনার পার্টনার চ্যাট ছেড়ে চলে গেছে।",
        'premium_txt': "💎 **Premium Features:**\n\nপ্রিমিয়াম ফিচারের কাজ চলছে। খুব দ্রুতই সরাসরি জেন্ডার ফিল্টার (Male/Female) যোগ করা হবে!",
        'help_txt': "💡 **হেল্প গাইড:**\n\n• চ্যাট করতে '🚀 Find Partner' চাপুন।\n• চ্যাট বদলাতে '⏭️ Next Partner' চাপুন।\n• কোনো প্রকার অশালীন আচরণ করলে অ্যাকাউন্ট ব্যান করা হবে।",
        'start_chat_alert': "⚠️ চ্যাট শুরু করতে '🚀 Find Partner' বাটনে ক্লিক করুন।",
        'pic_verify_msg': "📸 **ফেস ভেরিফিকেশন:**\n\nআপনার ক্যামেরার সামনের লাইভ ফেস বা নিজের একটি পরিষ্কার ছবি পাঠান।",
        'pic_verify_success': "🎉 ধন্যবাদ! আপনার ছবি পাওয়া গেছে এবং প্রোফাইলটি ভেরিফাইড (Verified) করা হয়েছে।"
    },
    'english': {
        'start': "👋 Welcome to Mnuverse Bot!\n\nBefore starting, you need to set up your profile.\n\n📝 Please enter your Name or a Nickname:",
        'already_reg': "🤖 You are already registered! Use the menu below.",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **Your Profile & Filters:**\n\n👤 Name: {name}\n🎂 Age: {age}\n🗣️ Language: {lang}\n🛡️ Verification: {status}\n🎯 Partner Age Range: {min_age} - {max_age} years\n\nClick the buttons below to change your information.",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **Partner Found!**\n👤 Name: {name}\n🎂 Age: {age}\n🗣️ Language: {lang}\n\nYou can chat now.",
        'name_saved': "👍 Name saved: {text}\n\n🎂 Now enter your **Age** (Numbers only, e.g., 22):",
        'select_lang': "🗣️ Select your chatting **Language** from below:",
        'invalid_age': "⚠️ Please enter a valid age (numbers between 15 and 99):",
        'invalid_lang_btn': "⚠️ Please tap one of the language buttons above.",
        'enter_min_age': "🎯 What is the **Minimum Age** (e.g., 18) you prefer for a partner?",
        'enter_max_age': "🎯 Now enter the **Maximum Age** of your partner (e.g., 30):",
        'filter_updated': "✅ Partner age filter successfully updated!",
        'invalid_num': "⚠️ Please enter a valid number:",
        'already_chat': "⚠️ You are already in a chat!",
        'searching': "⏳ Searching for a partner, please wait...",
        'search_start': "🔍 Searching for a partner based on your filters...",
        'search_cancel': "🛑 Partner search cancelled.",
        'you_stopped': "🛑 You stopped the chat.",
        'partner_stopped': "🛑 Your partner stopped the chat.",
        'not_connected': "⚠️ You are not connected to any chat.",
        'partner_left': "🛑 Your partner left the chat.",
        'premium_txt': "💎 **Premium Features:**\n\nPremium features are under development. Direct gender filters (Male/Female) will be added very soon!",
        'help_txt': "💡 **Help Guide:**\n\n• Tap '🚀 Find Partner' to start a chat.\n• Tap '⏭️ Next Partner' to change partner.\n• Any abusive or inappropriate behavior will lead to an account ban.",
        'start_chat_alert': "⚠️ Tap '🚀 Find Partner' to start a chat.",
        'pic_verify_msg': "📸 **Face Verification:**\n\nPlease send a clear picture of yourself or a live face photo.",
        'pic_verify_success': "🎉 Thank you! Your picture has been received and your profile is now Verified."
    },
    'hindi': {
        'start': "👋 Mnuverse Bot में आपका स्वागत है!\n\nचैट शुरू करने से पहले आपको अपना प्रोफाइल सेट करना होगा।\n\n📝 कृपया अपना नाम या उपनाम दर्ज करें:",
        'already_reg': "🤖 आप पहले से ही पंजीकृत हैं! नीचे दिए गए मेनू का उपयोग करें।",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **आपका प्रोफ़ाइल और फ़िल्टर:**\n\n👤 नाम: {name}\n🎂 आयु: {age}\n🗣️ भाषा: {lang}\n🛡️ सत्यापन: {status}\n🎯 पार्टनर आयु सीमा: {min_age} - {max_age} वर्ष\n\nअपनी जानकारी बदलने के लिए नीचे दिए गए बटन पर क्लिक करें।",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **पार्टनर मिल गया!**\n👤 नाम: {name}\n🎂 आयु: {age}\n🗣️ भाषा: {lang}\n\nअब आप चैट कर सकते हैं।",
        'name_saved': "👍 नाम सहेजा गया: {text}\n\n🎂 अब अपनी **आयु** दर्ज करें (केवल संख्या, जैसे: 22):",
        'select_lang': "🗣️ नीचे से अपनी चैटिंग **भाषा** चुनें:",
        'invalid_age': "⚠️ कृपया एक मान्य आयु दर्ज करें (15 और 99 के बीच की संख्या):",
        'invalid_lang_btn': "⚠️ कृपया ऊपर दिए गए भाषा बटन में से किसी एक पर टैप करें।",
        'enter_min_age': "🎯 आप अपने पार्टनर की **न्यूनतम आयु** (Minimum Age, जैसे: 18) क्या पसंद करते हैं?",
        'enter_max_age': "🎯 अब अपने पार्टनर की **अधिकतम आयु** (Maximum Age, जैसे: 30) दर्ज करें:",
        'filter_updated': "✅ पार्टनर आयु फ़िल्टर सफलतापूर्वक अपडेट किया गया!",
        'invalid_num': "⚠️ कृपया एक मान्य संख्या दर्ज करें:",
        'already_chat': "⚠️ आप पहले से ही एक चैट में हैं!",
        'searching': "⏳ पार्टनर की तलाश की जा रही है, कृपया प्रतीक्षा करें...",
        'search_start': "🔍 आपके फ़िल्टर के आधार पर पार्टनर की तलाश की जा रही है...",
        'search_cancel': "🛑 पार्टनर की खोज रद्द कर दी गई।",
        'you_stopped': "🛑 आपने चैट बंद कर दी।",
        'partner_stopped': "🛑 आपके पार्टनर ने चैट बंद कर दी है।",
        'not_connected': "⚠️ आप वर्तमान में किसी चैट से जुड़े नहीं हैं।",
        'partner_left': "🛑 आपका पार्टनर चैट छोड़कर चला गया है।",
        'premium_txt': "💎 **Premium Features:**\n\nप्रीमियम सुविधाएं अभी विकास के अधीन हैं। डायरेक्ट जेंडर फ़िल्टर (पुरुष/महिला) बहुत जल्द जोड़े जाएंगे!",
        'help_txt': "💡 **सहायता गाइड:**\n\n• चैट शुरू करने के लिए '🚀 Find Partner' पर टैप करें।\n• पार्टनर बदलने के लिए '⏭️ Next Partner' पर टैप करें।\n• किसी भी अपमानजनक या अनुचित व्यवहार के कारण खाते पर प्रतिबंध लगा दिया जाएगा।",
        'start_chat_alert': "⚠️ चैट शुरू करने के लिए '🚀 Find Partner' पर टैप करें।",
        'pic_verify_msg': "📸 **चेहरा सत्यापन:**\n\nकृपया अपनी एक स्पष्ट तस्वीर या लाइव चेहरे का फोटो भेजें।",
        'pic_verify_success': "🎉 धन्यवाद! आपकी तस्वीर प्राप्त हो गई है और आपका प्रोफ़ाइल अब सत्यापित (Verified) है।"
    },
    'japanese': {
        'start': "👋 Mnuverse Botへようこそ！\n\nチャットを開始する前に、プロファイルを設定する必要があります。\n\n📝 名前またはニックネームを入力してください：",
        'already_reg': "🤖 すでに登録されています！下のメニューを使用してください。",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **プロファイルとフィルター:**\n\n👤 名前: {name}\n🎂 年齢: {age}\n🗣️ 言語: {lang}\n🛡️ 認証: {status}\n🎯 パートナーの年齢範囲: {min_age} - {max_age} 歳\n\n情報を変更するには、下のボタンをクリックしてください。",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **パートナーが見つかりました！**\n👤 名前: {name}\n🎂 年齢: {age}\n🗣️ 言語: {lang}\n\nチャットを始めることができます。",
        'name_saved': "👍 名前が保存されました: {text}\n\n🎂 次に**年齢**を入力してください（数字のみ、例: 22）：",
        'select_lang': "🗣️ 以下からチャットの**言語**を選択してください：",
        'invalid_age': "⚠️ 有効な年齢を入力してください（15から99までの数字）：",
        'invalid_lang_btn': "⚠️ 上記の言語ボタンのいずれかをタップしてください。",
        'enter_min_age': "🎯 パートナーの**最低年齢**（例: 18）はいくつを希望しますか？",
        'enter_max_age': "🎯 パートナーの**最高年齢**（例: 30）を入力してください：",
        'filter_updated': "✅ パートナーの年齢フィルターが正常に更新されました！",
        'invalid_num': "⚠️ 有効な数字を入力してください：",
        'already_chat': "⚠️ すでにチャット中です！",
        'searching': "⏳ パートナーを探しています。しばらくお待ちください...",
        'search_start': "🔍 フィルターに基づいてパートナーを検索しています...",
        'search_cancel': "🛑 パートナーの検索がキャンセルされました。",
        'you_stopped': "🛑 チャットを終了しました。",
        'partner_stopped': "🛑 パートナーがチャットを終了しました。",
        'not_connected': "⚠️ 現在、どのチャットにも接続されていません。",
        'partner_left': "🛑 パートナーがチャットから退出しました。",
        'premium_txt': "💎 **Premium Features:**\n\nプレミアム機能は開発中です。性別フィルター（男性/女性）は近日中に追加されます！",
        'help_txt': "💡 **ヘルプガイド:**\n\n• チャットを開始するには「🚀 Find Partner」をタップします。\n• パートナーを変更するには「⏭️ Next Partner」をタップします。\n• 迷惑行為や不適切な行為は、アカウントの利用停止につながります。",
        'start_chat_alert': "⚠️ チャットを開始するには「🚀 Find Partner」をタップしてください。",
        'pic_verify_msg': "📸 **本人確認写真:**\n\nあなたの顔がはっきりと写っている写真、またはライブ撮影した写真を送信してください。",
        'pic_verify_success': "🎉 ありがとうございます！写真が受信され、プロファイルが認証されました。"
    },
    'russian': {
        'start': "👋 Добро пожаловать в Mnuverse Bot!\n\nПеред началом работы вам необходимо настроить свой профиль.\n\n📝 Пожалуйста, введите ваше имя или никнейм:",
        'already_reg': "🤖 Вы уже зарегистрированы! Используйте меню ниже.",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **Ваш профиль и фильтры:**\n\n👤 Имя: {name}\n🎂 Возраст: {age}\n🗣️ Язык: {lang}\n🛡️ Верификация: {status}\n🎯 Возраст партнера: {min_age} - {max_age} лет\n\nНажмите на кнопки ниже, чтобы изменить информацию.",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **Партнер найден!**\n👤 Имя: {name}\n🎂 Возраст: {age}\n🗣️ Язык: {lang}\n\nТеперь вы можете общаться.",
        'name_saved': "👍 Имя сохранено: {text}\n\n🎂 Теперь введите ваш **возраст** (только цифры, например, 22):",
        'select_lang': "🗣️ Выберите **язык** общения ниже:",
        'invalid_age': "⚠️ Пожалуйста, введите корректный возраст (число от 15 до 99):",
        'invalid_lang_btn': "⚠️ Пожалуйста, нажмите на одну из кнопок выбора языка выше.",
        'enter_min_age': "🎯 Какой **минимальный возраст** (например, 18) вы предпочитаете для партнера?",
        'enter_max_age': "🎯 Теперь введите **максимальный возраст** партнера (например, 30):",
        'filter_updated': "✅ Фильтр возраста партнера успешно обновлен!",
        'invalid_num': "⚠️ Пожалуйста, введите корректное число:",
        'already_chat': "⚠️ Вы уже находитесь в чате!",
        'searching': "⏳ Поиск партнера, пожалуйста, подождите...",
        'search_start': "🔍 Поиск партнера на основе ваших фильтров...",
        'search_cancel': "🛑 Поиск партнера отменен.",
        'you_stopped': "🛑 Вы остановили чат.",
        'partner_stopped': "🛑 Ваш партнер остановил чат.",
        'not_connected': "⚠️ В настоящее время вы не подключены к чату.",
        'partner_left': "🛑 Ваш партнер покинул чат.",
        'premium_txt': "💎 **Premium Features:**\n\nПремиум-функции находятся в разработке. Прямые гендерные фильтры (Мужчины/Женщины) будут добавлены очень скоро!",
        'help_txt': "💡 **Руководство:**\n\n• Нажмите '🚀 Find Partner', чтобы начать чат.\n• Нажмите '⏭️ Next Partner', чтобы сменить партнера.\n• Любое оскорбительное или неадекватное поведение приведет к блокировке аккаунта.",
        'start_chat_alert': "⚠️ Нажмите '🚀 Find Partner', чтобы начать чат.",
        'pic_verify_msg': "📸 **Верификация лица:**\n\nПожалуйста, отправьте четкую фотографию вашего лица или живое селфи.",
        'pic_verify_success': "🎉 Спасибо! Ваше фото получено, и ваш профиль теперь верифицирован."
    },
    'arabic': {
        'start': "👋 مرحبًا بك في Mnuverse Bot!\n\nقبل البدء، تحتاج إلى إعداد ملفك الشخصي.\n\n📝 يرجى إدخال اسمك أو اسم مستعار:",
        'already_reg': "🤖 أنت مسجل بالفعل! استخدم القائمة أدناه.",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **ملفك الشخصي والفلاتر:**\n\n👤 الاسم: {name}\n🎂 العمر: {age}\n🗣️ اللغة: {lang}\n🛡️ التوثيق: {status}\n🎯 عمر الشريك المطلوب: {min_age} - {max_age} سنة\n\nانقر فوق الأزرار أدناه لتغيير معلوماتك.",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **تم العثور على شريك!**\n👤 الاسم: {name}\n🎂 العمر: {age}\n🗣️ اللغة: {lang}\n\nيمكنك الدردشة الآن.",
        'name_saved': "👍 تم حفظ الاسم: {text}\n\n🎂 الآن أدخل **عمرك** (أرقام فقط، مثلًا: 22):",
        'select_lang': "🗣️ اختر **لغة** الدردشة من الأسفل:",
        'invalid_age': "⚠️ يرجى إدخال عمر صحيح (أرقام بين 15 و 99):",
        'invalid_lang_btn': "⚠️ يرجى الضغط على أحد أزرار اللغة أعلاه.",
        'enter_min_age': "🎯 ما هو **الحد الأدنى للعمر** (مثلًا: 18) الذي تفضله لشريكك؟",
        'enter_max_age': "🎯 الآن أدخل **الحد الأقصى للعمر** لشريكك (مثلًا: 30):",
        'filter_updated': "✅ تم تحديث فلتر عمر الشريك بنجاح!",
        'invalid_num': "⚠️ يرجى إدخال رقم صحيح:",
        'already_chat': "⚠️ أنت في دردشة بالفعل!",
        'searching': "⏳ جاري البحث عن شريك، يرجى الانتظار...",
        'search_start': "🔍 جاري البحث عن شريك بناءً على الفلاتر الخاصة بك...",
        'search_cancel': "🛑 تم إلغاء البحث عن شريك.",
        'you_stopped': "🛑 قمت بإيقاف الدردشة.",
        'partner_stopped': "🛑 قام شريكك بإيقاف الدردشة.",
        'not_connected': "⚠️ أنت غير متصل بأي دردشة حاليًا.",
        'partner_left': "🛑 غادر شريكك الدردشة.",
        'premium_txt': "💎 **Premium Features:**\n\nالميزات المميزة قيد التطوير حاليًا. سيتم إضافة فلاتر الجنس المباشرة (ذكر/أنثى) قريبًا جدًا!",
        'help_txt': "💡 **دليل المساعدة:**\n\n• اضغط على '🚀 Find Partner' لبدء الدردشة.\n• اضغط على '⏭️ Next Partner' لتغيير الشريك.\n• أي سلوك مسيء أو غير لائق سيؤدي إلى حظر الحساب.",
        'start_chat_alert': "⚠️ اضغط على '🚀 Find Partner' لبدء الدردشة.",
        'pic_verify_msg': "📸 **توثيق الوجه:**\n\nيرجى إرسال صورة واضحة لنفسك أو صورة وجه مباشرة.",
        'pic_verify_success': "🎉 شكرًا لك! تم استلام صورتك وتم توثيق ملفك الشخصي الآن."
    },
    'spanish': {
        'start': "👋 ¡Bienvenido a Mnuverse Bot!\n\nAntes de comenzar, debes configurar tu perfil.\n\n📝 Por favor, introduce tu Nombre o un Apodo:",
        'already_reg': "🤖 ¡Ya estás registrado! Usa el menú de abajo.",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **Tu Perfil y Filtros:**\n\n👤 Nombre: {name}\n🎂 Edad: {age}\n🗣️ Idioma: {lang}\n🛡️ Verificación: {status}\n🎯 Rango de edad de la pareja: {min_age} - {max_age} años\n\nHaz clic en los botones de abajo para cambiar tu información.",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **¡Pareja Encontrada!**\n👤 Nombre: {name}\n🎂 Edad: {age}\n🗣️ Idioma: {lang}\n\nYa puedes chatear.",
        'name_saved': "👍 Nombre guardado: {text}\n\n🎂 Ahora introduce tu **Edad** (Solo números, ej., 22):",
        'select_lang': "🗣️ Selecciona tu **Idioma** para chatear abajo:",
        'invalid_age': "⚠️ Por favor, introduce una edad válida (números entre 15 y 99):",
        'invalid_lang_btn': "⚠️ Por favor, toca uno de los botones de idioma de arriba.",
        'enter_min_age': "🎯 ¿Cuál es la **Edad Mínima** (ej., 18) que prefieres para tu pareja?",
        'enter_max_age': "🎯 Ahora introduce la **Edad Máxima** de tu pareja (ej., 30):",
        'filter_updated': "✅ ¡Filtro de edad de la pareja actualizado correctamente!",
        'invalid_num': "⚠️ Por favor, introduce un número válido:",
        'already_chat': "⚠️ ¡Ya estás en un chat!",
        'searching': "⏳ Buscando pareja, por favor espera...",
        'search_start': "🔍 Buscando pareja según tus filtros...",
        'search_cancel': "🛑 Búsqueda de pareja cancelada.",
        'you_stopped': "🛑 Detuviste el chat.",
        'partner_stopped': "🛑 Tu pareja detuvo el chat.",
        'not_connected': "⚠️ No estás conectado a ningún chat actualmente.",
        'partner_left': "🛑 Tu pareja salió del chat.",
        'premium_txt': "💎 **Premium Features:**\n\nLas funciones premium están en desarrollo. ¡Los filtros de género directo (Masculino/Femenino) se añadirán muy pronto!",
        'help_txt': "💡 **Guía de Ayuda:**\n\n• Toca '🚀 Find Partner' para iniciar un chat.\n• Toca '⏭️ Next Partner' para cambiar de pareja.\n• Cualquier comportamiento abusivo o inapropiado resultará en la expulsión de la cuenta.",
        'start_chat_alert': "⚠️ Toca '🚀 Find Partner' para iniciar un chat.",
        'pic_verify_msg': "📸 **Verificación de Rostro:**\n\nPor favor, envía una foto clara de ti mismo o una foto de rostro en vivo.",
        'pic_verify_success': "🎉 ¡Gracias! Tu foto ha sido recibida y tu perfil ya está Verificado."
    },
    'french': {
        'start': "👋 Bienvenue sur Mnuverse Bot !\n\nAvant de commencer, vous devez configurer votre profil.\n\n📝 Veuillez entrer votre nom ou un pseudo :",
        'already_reg': "🤖 Vous êtes déjà inscrit ! Utilisez le menu ci-dessous.",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **Votre profil & filtres :**\n\n👤 Nom : {name}\n🎂 Âge : {age}\n🗣️ Langue : {lang}\n🛡️ Vérification : {status}\n🎯 Tranche d'âge du partenaire : {min_age} - {max_age} ans\n\nCliquez sur les boutons ci-dessous pour modifier vos informations.",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **Partenaire trouvé !**\n👤 Nom : {name}\n🎂 Âge : {age}\n🗣️ Langue : {lang}\n\nVous pouvez discuter maintenant.",
        'name_saved': "👍 Nom enregistré : {text}\n\n🎂 Entrez maintenant votre **Âge** (Chiffres uniquement, ex: 22) :",
        'select_lang': "🗣️ Sélectionnez votre **Langue** de discussion ci-dessous :",
        'invalid_age': "⚠️ Veuillez entrer un âge valide (chiffres entre 15 et 99) :",
        'invalid_lang_btn': "⚠️ Veuillez appuyer sur l'un des boutons de langue ci-dessus.",
        'enter_min_age': "🎯 Quel est l'**Âge Minimum** (ex: 18) que vous préférez pour un partenaire ?",
        'enter_max_age': "🎯 Entrez maintenant l'**Âge Maximum** de votre partenaire (ex: 30) :",
        'filter_updated': "✅ Filtre d'âge du partenaire mis à jour avec succès !",
        'invalid_num': "⚠️ Veuillez entrer un nombre valide :",
        'already_chat': "⚠️ Vous êtes déjà dans un chat !",
        'searching': "⏳ Recherche d'un partenaire, veuillez patienter...",
        'search_start': "🔍 Recherche d'un partenaire selon vos filtres...",
        'search_cancel': "🛑 Recherche de partenaire annulée.",
        'you_stopped': "🛑 Vous avez arrêté le chat.",
        'partner_stopped': "🛑 Votre partenaire a arrêté le chat.",
        'not_connected': "⚠️ Vous n'êtes actuellement connecté à aucun chat.",
        'partner_left': "🛑 Votre partenaire a quitté le chat.",
        'premium_txt': "💎 **Premium Features:**\n\nLes fonctionnalités premium sont en cours de développement. Les filtres de genre direct (Homme/Femme) seront ajoutés très bientôt !",
        'help_txt': "💡 **Guide d'aide :**\n\n• Appuyez sur '🚀 Find Partner' pour démarrer un chat.\n• Appuyez sur '⏭️ Next Partner' pour changer de partenaire.\n• Tout comportement abusif ou inapproprié entraînera un bannissement du compte.",
        'start_chat_alert': "⚠️ Appuyez sur '🚀 Find Partner' pour démarrer un chat.",
        'pic_verify_msg': "📸 **Vérification du visage :**\n\nVeuillez envoyer une photo claire de vous-même ou une photo de visage en direct.",
        'pic_verify_success': "🎉 Merci ! Votre photo a été reçue et votre profil est maintenant vérifié."
    },
    'korean': {
        'start': "👋 Mnuverse Bot에 오신 것을 환영합니다!\n\n시작하기 전에 프로필을 설정해야 합니다.\n\n📝 이름이나 닉네임을 입력해 주세요:",
        'already_reg': "🤖 이미 등록되어 있습니다! 아래 메뉴를 이용해 주세요.",
        'find': "🚀 Find Partner", 'next': "⏭️ Next Partner", 'stop': "🛑 Stop Chat", 'profile': "⚙️ My Profile & Filters", 'premium': "💎 Premium", 'help_btn': "❓ Help",
        'profile_txt': "⚙️ **내 프로필 & 필터:**\n\n👤 이름: {name}\n🎂 나이: {age}\n🗣️ 언어: {lang}\n🛡️ 인증 상태: {status}\n🎯 원하는 파트너 나이대: {min_age} - {max_age} 세\n\n정보를 변경하려면 아래 버튼을 클릭하세요.",
        'edit_name': "✍️ Edit Name", 'edit_age': "✍️ Edit Age", 'edit_lang': "🗣️ Edit Language", 'verify_pic': "📸 Verify Profile Pic", 'set_filter': "🎯 Set Partner Age Filter",
        'partner_found': "🎉 **파트너를 찾았습니다!**\n👤 이름: {name}\n🎂 나이: {age}\n🗣️ 언어: {lang}\n\n이제 대화를 시작할 수 있습니다.",
        'name_saved': "👍 이름이 저장되었습니다: {text}\n\n🎂 이제 **나이**를 입력해 주세요 (숫자만 입력, 예: 22):",
        'select_lang': "🗣️ 아래에서 채팅할 **언어**를 선택해 주세요:",
        'invalid_age': "⚠️ 올바른 나이를 입력해 주세요 (15세에서 99세 사이의 숫자):",
        'invalid_lang_btn': "⚠️ 위의 언어 버튼 중 하나를 눌러주세요.",
        'enter_min_age': "🎯 파트너의 **최소 나이**(예: 18)는 몇 세를 선호하시나요?",
        'enter_max_age': "🎯 이제 파트너의 **최대 나이**(예: 30)를 입력해 주세요:",
        'filter_updated': "✅ 파트너 나이 필터가 성공적으로 업데이트되었습니다!",
        'invalid_num': "⚠️ 올바른 숫자를 입력해 주세요:",
        'already_chat': "⚠️ 이미 채팅 중입니다!",
        'searching': "⏳ 파트너를 찾는 중입니다. 잠시만 기다려 주세요...",
        'search_start': "🔍 설정하신 필터에 맞는 파트너를 찾는 중입니다...",
        'search_cancel': "🛑 파트너 매칭이 취소되었습니다.",
        'you_stopped': "🛑 채팅을 종료했습니다.",
        'partner_stopped': "🛑 파트너가 채팅을 종료했습니다.",
        'not_connected': "⚠️ 현재 연결된 채팅이 없습니다.",
        'partner_left': "🛑 파트너가 채팅을 나갔습니다.",
        'premium_txt': "💎 **Premium Features:**\n\n프리미엄 기능은 현재 개발 중입니다. 직접적인 성별 필터(남성/여성) 기능이 곧 추가될 예정입니다!",
        'help_txt': "💡 **도움말 가이드:**\n\n• '🚀 Find Partner'를 누르면 대화가 시작됩니다.\n• '⏭️ Next Partner'를 누르면 다른 파트너를 찾습니다.\n• 욕설이나 부적절한 행동을 할 경우 계정이 차단될 수 있습니다.",
        'start_chat_alert': "⚠️ 대화를 시작하려면 '🚀 Find Partner'를 눌러주세요.",
        'pic_verify_msg': "📸 **얼굴 인증:**\n\n본인의 선명한 사진이나 라이브 얼굴 사진을 보내주세요.",
        'pic_verify_success': "🎉 감사합니다! 사진이 전송되었으며 프로필 인증이 완료되었습니다."
    }
}

def get_msg(user_id, key):
    user_lang = users_profile.get(user_id, {}).get('lang', 'english')
    if not user_lang:
        user_lang = 'english'
    return MESSAGES.get(user_lang.lower(), MESSAGES['english']).get(key, MESSAGES['english'].get(key, ""))

def main_menu_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton(get_msg(user_id, 'find')), KeyboardButton(get_msg(user_id, 'next')))
    markup.row(KeyboardButton(get_msg(user_id, 'stop')), KeyboardButton(get_msg(user_id, 'profile')))
    markup.row(KeyboardButton(get_msg(user_id, 'premium')), KeyboardButton(get_msg(user_id, 'help_btn')))
    return markup

def language_keyboard(prefix="reg_lang_"):
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [InlineKeyboardButton(lang, callback_data=f"{prefix}{lang.lower()}") for lang in AVAILABLE_LANGUAGES]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.chat.id
    if user_id not in users_profile:
        users_profile[user_id] = {'name': None, 'age': None, 'lang': None, 'verified': False, 'target_age_min': 18, 'target_age_max': 50}
        bot.send_message(user_id, MESSAGES['english']['start'])
        user_states[user_id] = 'WAITING_NAME'
    else:
        bot.send_message(user_id, get_msg(user_id, 'already_reg'), reply_markup=main_menu_keyboard(user_id))

def show_profile(user_id):
    p = users_profile[user_id]
    status = "✅ Verified" if p['verified'] else "❌ Not Verified"
    text = get_msg(user_id, 'profile_txt').format(
        name=p['name'], age=p['age'], lang=p['lang'], status=status,
        min_age=p['target_age_min'], max_age=p['target_age_max']
    )
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(get_msg(user_id, 'edit_name'), callback_data="edit_name"), InlineKeyboardButton(get_msg(user_id, 'edit_age'), callback_data="edit_age"))
    markup.row(InlineKeyboardButton(get_msg(user_id, 'edit_lang'), callback_data="edit_lang"), InlineKeyboardButton(get_msg(user_id, 'verify_pic'), callback_data="verify_pic"))
    markup.row(InlineKeyboardButton(get_msg(user_id, 'set_filter'), callback_data="edit_target_age"))
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
                
                txt1 = get_msg(user_id, 'partner_found').format(name=partner_p['name'], age=partner_p['age'], lang=partner_p['lang'])
                txt2 = get_msg(potential_partner, 'partner_found').format(name=p['name'], age=p['age'], lang=p['lang'])
                
                bot.send_message(user_id, txt1, reply_markup=main_menu_keyboard(user_id))
                bot.send_message(potential_partner, txt2, reply_markup=main_menu_keyboard(potential_partner))
                return True
    return False

@bot.message_handler(content_types=['photo'])
def handle_verification_photo(message):
    user_id = message.chat.id
    if user_id in user_states and user_states[user_id] == 'WAITING_VERIFY_PIC':
        users_profile[user_id]['verified'] = True  
        del user_states[user_id]
        bot.send_message(user_id, get_msg(user_id, 'pic_verify_success'), reply_markup=main_menu_keyboard(user_id))
        return
        
    if user_id in active_chats:
        bot.send_photo(active_chats[user_id], message.photo[-1].file_id, caption=message.caption)
    else:
        bot.send_message(user_id, get_msg(user_id, 'not_connected'))

@bot.message_handler(content_types=['sticker', 'voice', 'video'])
def handle_other_media(message):
    user_id = message.chat.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        if message.content_type == 'sticker':
            bot.send_sticker(partner_id, message.sticker.file_id)
        elif message.content_type == 'voice':
            bot.send_voice(partner_id, message.voice.file_id)
        elif message.content_type == 'video':
            bot.send_video(partner_id, message.video.file_id)
    else:
        bot.send_message(user_id, get_msg(user_id, 'not_connected'))

@bot.message_handler(func=lambda message: True)
def handle_all_texts(message):
    user_id = message.chat.id
    text = message.text

    if user_id in user_states:
        state = user_states[user_id]
        if state == 'WAITING_NAME':
            users_profile[user_id]['name'] = text
            bot.send_message(user_id, get_msg(user_id, 'name_saved').format(text=text))
            user_states[user_id] = 'WAITING_AGE'
            return
        elif state == 'WAITING_AGE':
            if text.isdigit() and 15 <= int(text) <= 99:
                users_profile[user_id]['age'] = int(text)
                bot.send_message(user_id, get_msg(user_id, 'select_lang'), reply_markup=language_keyboard("reg_lang_"))
                user_states[user_id] = 'WAITING_LANG'
            else:
                bot.send_message(user_id, get_msg(user_id, 'invalid_age'))
            return
        elif state == 'WAITING_LANG':
            bot.send_message(user_id, get_msg(user_id, 'invalid_lang_btn'))
            return
        elif state == 'WAITING_TARGET_AGE_MIN':
            if text.isdigit():
                users_profile[user_id]['target_age_min'] = int(text)
                bot.send_message(user_id, get_msg(user_id, 'enter_max_age'))
                user_states[user_id] = 'WAITING_TARGET_AGE_MAX'
            else:
                bot.send_message(user_id, get_msg(user_id, 'invalid_num'))
            return
        elif state == 'WAITING_TARGET_AGE_MAX':
            if text.isdigit():
                users_profile[user_id]['target_age_max'] = int(text)
                del user_states[user_id]
                bot.send_message(user_id, get_msg(user_id, 'filter_updated'), reply_markup=main_menu_keyboard(user_id))
                show_profile(user_id)
            else:
                bot.send_message(user_id, get_msg(user_id, 'invalid_num'))
            return

    if user_id not in users_profile or users_profile[user_id]['name'] is None:
        start_cmd(message)
        return

    if text in ["🚀 Find Partner", get_msg(user_id, 'find')]:
        if user_id in active_chats:
            bot.send_message(user_id, get_msg(user_id, 'already_chat'))
            return
        if user_id in waiting_room:
            bot.send_message(user_id, get_msg(user_id, 'searching'))
            return
        waiting_room.append(user_id)
        bot.send_message(user_id, get_msg(user_id, 'search_start'))
        match_users(user_id)
    elif text in ["🛑 Stop Chat", get_msg(user_id, 'stop')]:
        if user_id in waiting_room:
            waiting_room.remove(user_id)
            bot.send_message(user_id, get_msg(user_id, 'search_cancel'))
        elif user_id in active_chats:
            partner_id = active_chats[user_id]
            del active_chats[user_id]
            del active_chats[partner_id]
            bot.send_message(user_id, get_msg(user_id, 'you_stopped'))
            bot.send_message(partner_id, get_msg(partner_id, 'partner_stopped'))
        else:
            bot.send_message(user_id, get_msg(user_id, 'not_connected'))
    elif text in ["⏭️ Next Partner", get_msg(user_id, 'next')]:
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            del active_chats[user_id]
            del active_chats[partner_id]
            bot.send_message(partner_id, get_msg(partner_id, 'partner_left'))
        if user_id in waiting_room:
            waiting_room.remove(user_id)
        bot.send_message(user_id, get_msg(user_id, 'searching'))
        waiting_room.append(user_id)
        match_users(user_id)
    elif text in ["⚙️ My Profile & Filters", get_msg(user_id, 'profile')]:
        show_profile(user_id)
    elif text in ["💎 Premium", get_msg(user_id, 'premium')]:
        bot.send_message(user_id, get_msg(user_id, 'premium_txt'))
    elif text in ["❓ Help", get_msg(user_id, 'help_btn')]:
        bot.send_message(user_id, get_msg(user_id, 'help_txt'))
    else:
        if user_id in active_chats:
            bot.send_message(active_chats[user_id], text)
        else:
            bot.send_message(user_id, get_msg(user_id, 'start_chat_alert'))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data
    
    if data.startswith("reg_lang_"):
        selected_lang = data.replace("reg_lang_", "").capitalize()
        users_profile[user_id]['lang'] = selected_lang
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(user_id, get_msg(user_id, 'pic_verify_msg'))
        user_states[user_id] = 'WAITING_VERIFY_PIC'
        return

    if data.startswith("edit_lang_"):
        selected_lang = data.replace("edit_lang_", "").capitalize()
        users_profile[user_id]['lang'] = selected_lang
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(user_id, f"✅ Language updated to: **{selected_lang}**", parse_mode="Markdown")
        show_profile(user_id)
        return

    bot.delete_message(user_id, call.message.message_id)
    
    if data == "edit_name":
        bot.send_message(user_id, "✍️ Enter your new name or nickname:")
        user_states[user_id] = 'WAITING_NAME'
    elif data == "edit_age":
        bot.send_message(user_id, "🎂 Enter your new age in numbers:")
        user_states[user_id] = 'WAITING_AGE'
    elif data == "edit_lang":
        bot.send_message(user_id, "🗣️ Choose your new language:", reply_markup=language_keyboard("edit_lang_"))
    elif data == "edit_target_age":
        bot.send_message(user_id, get_msg(user_id, 'enter_min_age'))
        user_states[user_id] = 'WAITING_TARGET_AGE_MIN'
    elif data == "verify_pic":
        bot.send_message(user_id, get_msg(user_id, 'pic_verify_msg'))
        user_states[user_id] = 'WAITING_VERIFY_PIC'

if __name__ == "__main__":
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
