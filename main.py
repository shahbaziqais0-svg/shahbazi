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

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE").strip()
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

def get_account_models():
    """دریافت نام دقیق مدل‌های فعال در اکانت شما"""
    try:
        res = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=15,
        )
        if res.status_code == 200:
            data = res.json()
            return [m["id"] for m in data.get("data", [])]
        return [f"خطای لیست مدل: {res.text}"]
    except Exception as e:
        return [f"خطای شبکه: {str(e)}"]

def ask_ai(prompt_text):
    if prompt_text.strip() == "لیست":
        models = get_account_models()
        return "📋 مدل‌های فعال اکانت شما:\n\n" + "\n".join(f"▫️ `{m}`" for m in models)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # تست با مدل‌های رسمی Groq
    target_models = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama3-70b-8192"]
    
    for m in target_models:
        payload = {
            "model": m,
            "messages": [
                {"role": "system", "content": "شما دستیار بازار پلیمر و پلاستیک شهنواز پلاست هستید. پاسخ‌ها را دقیق به تومان بر کیلوگرم بدهید."},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": 0.4
        }
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()

    return f"پاسخ سرور ({res.status_code}): {res.text}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات آنلاین است. کلمه «لیست» را بفرستید تا مدل‌های فعال را ببینید.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    status_msg = await update.message.reply_text("🔎 در حال پردازش...")
    reply = ask_ai(update.message.text)
    await status_msg.edit_text(reply, parse_mode="Markdown")

if __name__ == "__main__":
    web_thread = threading.Thread(target=run_dummy_server, daemon=True)
    web_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling(drop_pending_updates=True)
