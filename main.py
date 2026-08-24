import asyncio
import http.server
import logging
import os
import socketserver
import threading
import requests
import html
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8862836655:AAHgueF9p3AmUdyN8BoGjEDLcMylVkHzXIw").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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").strip()

ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"
MARKET_CHECK_INTERVAL = 1800

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"خطای وب‌سرور: {e}")

def ask_ai(user_question):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    system_instruction = (
        "شما کارشناس و مشاور ارشد خرید و فروش مواد اولیه پلاستیک، پلیمر، پتروشیمی و بورس کالای ایران برای مجموعه شهنواز پلاست هستید.\n"
        "وظیفه شما:\n"
        "۱. تحلیل وضعیت خرید، انبارداری و پیش‌بینی قیمت گریدهای پلیمری (فیلم، بادی، تزریقی مانند 0209، F7000، BL3، 0075 و غیره).\n"
        "۲. پاسخ‌دهی کاملاً به زبان فارسی، روان، منظم، کاربردی و بدون حاشیه.\n"
        "۳. در صورت نیاز به اعلام قیمت، حتماً قیمت‌ها را بر اساس «تومان بر کیلوگرم» تفکیک کنید."
    )

    # مدل‌های چت اختصاصی
    target_models = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama3-70b-8192"]
    
    last_error = ""
    for model_name in target_models:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_question},
            ],
            "temperature": 0.3,
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
            last_error = res.text
        except Exception as err:
            last_error = str(err)

    return f"خطا در مدل: {last_error}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "سلام! سیستم هوشمند تحلیل بازار و مواد پلیمری شهنواز پلاست آنلاین است.\n\n"
        "تحلیل خرید انواع گریدهای پلیمری (0209، F7000، 0075، بادی، فیلم و تزریقی)، بررسی بورس کالا و پیش‌بینی بازار را بپرسید."
    )
    await update.message.reply_text(welcome)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    user_text = update.message.text

    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    status_msg = await update.message.reply_text("🔎 در حال استخراج و تحلیل تخصصی...")
    reply_text = ask_ai(user_text)
    
    try:
        await status_msg.edit_text(reply_text)
    except Exception:
        await status_msg.edit_text(html.escape(reply_text))

if __name__ == "__main__":
    web_thread = threading.Thread(target=run_dummy_server, daemon=True)
    web_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling(drop_pending_updates=True)
