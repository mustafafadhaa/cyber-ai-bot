import os
import threading
from flask import Flask
import telebot
from telebot import types
import google.generativeai as genai

# 1. سيرفر خلفي مجاني للتشغيل 24/7
web_app = Flask('')

@web_app.route('/')
def home():
    return "Cyber AI Bot is Alive!"

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# 2. المفاتيح والتهيئة
# اجعلها هكذا فارغة أو بنص وهمي لا يكتشفه غيت هاب:
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_KEY")

genai.configure(api_key=GEMINI_API_KEY)

system_instruction = (
    "أنت مساعد ذكي ومحترف اسمك Cyber AI. "
    "تتحدث بلغة عربية سلسة، وتساعد في البرمجة، التحليل، والأسئلة العامة. "
    "اجعل ردودك مرتبة ومباشرة."
)

model = genai.GenerativeModel("gemini-3.1-pro-preview", system_instruction=system_instruction)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ذاكرة المحادثات لكل مستخدم
user_chats = {}

def get_chat_session(chat_id):
    if chat_id not in user_chats:
        user_chats[chat_id] = model.start_chat(history=[])
    return user_chats[chat_id]

def safe_reply(message, text, reply_markup=None):
    """إرسال آمن لتجنب مشاكل تنسيق Markdown"""
    try:
        bot.reply_to(message, text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception:
        bot.reply_to(message, text, reply_markup=reply_markup)

# 3. الأزرار التفاعلية
def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_clear = types.InlineKeyboardButton("🧹 مسح الذاكرة", callback_data="clear_chat")
    btn_info = types.InlineKeyboardButton("🤖 عن البوت", callback_data="about_bot")
    btn_help = types.InlineKeyboardButton("💡 أفكار لاستخدامه", callback_data="help_ideas")
    markup.add(btn_clear, btn_info, btn_help)
    return markup

# 4. أمر الترحب /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"أهلاً بك يا **{user_name}**! ⚡️\n\n"
        "أنا بوت الذكاء الاصطناعي (**Cyber AI**).\n"
        "جاهز لمساعدتك في الأكواد، الإجابة عن الأسئلة، وتحليل الصور والأصوات!\n\n"
        "👇 اختر من الأزرار أو اكتب لي مباشره:"
    )
    safe_reply(message, welcome_text, reply_markup=main_keyboard())

# 5. أمر مسح الذاكرة /clear
@bot.message_handler(commands=['clear'])
def clear_memory(message):
    user_chats[message.chat.id] = model.start_chat(history=[])
    safe_reply(message, "🧹 تم مسح ذاكرة المحادثة وبدء محادثة جديدة!")

# 6. تفاعل الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    chat_id = call.message.chat.id
    if call.data == "clear_chat":
        user_chats[chat_id] = model.start_chat(history=[])
        bot.answer_callback_query(call.id, "تم صفر الذاكرة!")
        bot.send_message(chat_id, "🧹 تم مسح الذاكرة بنجاح.")
    elif call.data == "about_bot":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🤖 **Cyber AI**\nمساعد متكامل يعتمد على نموذج Gemini 3.1 pro.")
    elif call.data == "help_ideas":
        bot.answer_callback_query(call.id)
        ideas = (
            "💡 **أشياء يمكنك تجربتها:**\n"
            "1️⃣ أرسل صورة واطلب شرحها.\n"
            "2️⃣ أرسل بصمة صوتية واطلب تفريغها أو الإجابة عليها.\n"
            "3️⃣ اكتب كوداً برمجياً واطلب تصحيحه."
        )
        bot.send_message(chat_id, ideas)

# 7. تحليل الصور
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    print("📸 جاري معالجة صورة...")
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_info = bot.get_file(message.photo[-1].file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        image_data = [{'mime_type': 'image/jpeg', 'data': file_bytes}]
        prompt = message.caption if message.caption else "اشرح لي بالتفصيل ماذا يوجد في هذه الصورة."
        
        response = model.generate_content([prompt] + image_data)
        safe_reply(message, response.text)
        print("✅ تم الرد على الصورة بنجاح.")
    except Exception as e:
        print(f"❌ خطأ بالصورة: {e}")
        safe_reply(message, f"حدث خطأ أثناء معالجة الصورة: {e}")

# 8. تحليل الصوت والبصمات
@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    print("🎙️ جاري معالجة صوت...")
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        audio_data = [{'mime_type': 'audio/ogg', 'data': file_bytes}]
        prompt = "استمع لهذا التسجيل الصوتي وأجب على ما فيه بدقة."
        
        response = model.generate_content([prompt] + audio_data)
        safe_reply(message, response.text)
        print("✅ تم الرد على الصوت بنجاح.")
    except Exception as e:
        print(f"❌ خطأ بالصوت: {e}")
        safe_reply(message, f"حدث خطأ أثناء معالجة الصوت: {e}")

# 9. معالجة النصوص وحفظ المحادثة
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    print(f"💬 نص مستلم: {message.text}")
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        chat = get_chat_session(message.chat.id)
        response = chat.send_message(message.text)
        safe_reply(message, response.text)
        print("✅ تم الرد على النص بنجاح.")
    except Exception as e:
        print(f"❌ خطأ بالنص: {e}")
        safe_reply(message, f"حدث خطأ أثناء معالجة الطلب: {e}")

# 10. تشغيل البوت
if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    print("🚀 Cyber AI يعمل الآن بكافة ميزاته...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)