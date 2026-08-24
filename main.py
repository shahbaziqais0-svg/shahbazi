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

def ask_ai(user_question):
    model_name = get_clean_model()
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # تفهیم صریح وظیفه برای جلوگیری از پاسخ‌های نامربوط
    system_instruction = (
        "شما کارشناس و مشاور ارشد خرید و فروش مواد اولیه پلاستیک، پلیمر، پتروشیمی و بورس کالای ایران برای مجموعه شهنواز پلاست هستید.\n"
        "وظیفه شما:\n"
        "۱. تحلیل وضعیت خرید، انبارداری و قیمت گریدهای پلیمری (فیلم، بادی، تزریقی مانند 0209، F7000، BL3، 0075 و غیره).\n"
        "۲. پاسخ‌دهی کاملاً به زبان فارسی، منظم، خلاصه و تخصصی صنعت پلاستیک.\n"
        "۳. اگر کاربر کلمه ربات یا سلام فرستاد، خود را معرفی کرده و بپرسید چه گریدی مدنظر دارند.\n"
        "۴. هرگز درباره ربات‌های مکانیکی یا مباحث غیرمرتبط با مواد اولیه پلیمر صحبت نکنید."
    )

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
        return f"خطا در مدل ({model_name}): {res.text}"
    except Exception as err:
        return f"خطای ارتباط: {str(err)}"

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

    # در گروه‌ها تنها به پیام‌هایی که ریپلای شوند یا توسط ادمین باشد پاسخ می‌دهد
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
