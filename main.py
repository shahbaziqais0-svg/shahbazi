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

def get_clean_model():
    """یافتن مدل چت استاندارد و بدون پیشوند اضافی"""
    try:
        res = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=10,
        )
        if res.status_code == 200:
            models = [m["id"].replace("models/", "") for m in res.json().get("data", []) if "whisper" not in m["id"] and "guard" not in m["id"]]
            for m in models:
                if "llama-3" in m or "llama3" in m:
                    return m
            if models:
                return models[0]
    except Exception:
        pass
    return "llama-3.3-70b-versatile"

def ask_ai(prompt_text):
    model_name = get_clean_model()
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "شما دستیار و تحلیل‌گر تخصصی بازار پلیمر، بورس کالا و صنعت پلاستیک شهنواز پلاست هستید. "
                    "پاسخ‌ها را کامل، دقیق، کاربردی و قیمت‌ها را به تومان بر کیلوگرم ارائه دهید."
                ),
            },
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.4,
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
        return f"خطا در مدل ({model_name}): {res.text}"
    except Exception as err:
        return f"خطای ارتباط: {str(err)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! سیستم هوشمند تحلیل بازار شهنواز پلاست آنلاین است.\n\nسوال خود را درباره مواد، گریدها یا تحلیل بازار بپرسید.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    status_msg = await update.message.reply_text("🔎 در حال استخراج و تحلیل تخصصی...")
    reply_text = ask_ai(update.message.text)
    
    # ارسال امن بدون باگ Markdown
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
