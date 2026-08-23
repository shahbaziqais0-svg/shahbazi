import asyncio
import http.server
import logging
import os
import socketserver
import threading
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# کلیدها
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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").strip()

ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"
MARKET_CHECK_INTERVAL = 1800

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"خطای وب‌سرور: {e}")

def ask_ai(prompt_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    # مدل قطعی و سبک رسمی
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "شما مشاور ارشد بازار پلیمر، بورس کالا و صنعت پلاستیک شهنواز پلاست هستید. پاسخ‌ها را دقیق، کامل، فارسی روان و با ذکر قیمت‌ها به تومان بر هر کیلوگرم بنویسید.",
            },
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.4,
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=35)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
        else:
            # نمایش صریح متن خطا برای عیب‌یابی دقیق
            return f"پاسخ سرور هوش مصنوعی ({res.status_code}): {res.text}"
    except Exception as err:
        return f"خطای اتصال به هوش مصنوعی: {str(err)}"

async def market_sentinel_loop(app):
    await asyncio.sleep(15)
    while True:
        prompt = """
        یک گزارش کوتاه و تفکیک‌شده (حداکثر ۱۰۰ کلمه) درباره آخرین وضعیت بازار پلیمر و پتروشیمی ایران برای کانال بنویسید:
        
        📌 [عنوان جذاب]
        🔹 رویداد مهم بازار
        💰 تابلوی مظنه گریدهای پرمصرف (تومان بر کیلوگرم)
        🎯 توصیه عملیاتی به تولیدکننده
        ⏳ مهلت اعتبار تحلیل
        
        اگر تحول خاصی نیست فقط بنویسید NO_UPDATE
        """
        try:
            report = ask_ai(prompt)
            if "NO_UPDATE" not in report and "خطا" not in report and len(report) > 30:
                final_post = f"{report}\n\n━━━━━━━━━━━━━━━━━━━━\n☎️ مشاوره و سفارش: {SUPPORT_PHONE}\n📢 رسانه تخصصی: {TARGET_CHAT_ID}"
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
        except Exception as e:
            logging.error(f"خطا در ارسال: {e}")
        await asyncio.sleep(MARKET_CHECK_INTERVAL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\nهر سوالی درباره قیمت روز مواد یا گریدها دارید بپرسید.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    user_text = update.message.text

    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    status_msg = await update.message.reply_text("🔎 در حال دریافت تحلیل بازار...")
    reply = ask_ai(user_text)
    await status_msg.edit_text(reply)

async def post_init(application):
    asyncio.create_task(market_sentinel_loop(application))

if __name__ == "__main__":
    web_thread = threading.Thread(target=run_dummy_server, daemon=True)
    web_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling(drop_pending_updates=True)
