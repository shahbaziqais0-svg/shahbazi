import asyncio
import http.server
import logging
import os
import socketserver
import threading
import time
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE").strip()
ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"
PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# 1. Anti-Sleep Keep-Alive Web Server
class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Shahnawaz Sentinel is Active and Healthy.")

def run_server():
    try:
        with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
            logging.info(f"Keep-Alive Server running on port {PORT}")
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"Server error: {e}")

# 2. Reliable Multi-Provider AI Fallback
def query_ai_engine(prompt: str) -> str:
    """Queries public stable AI endpoints without rate-limits or deprecations."""
    # Attempt 1: Free Public Text API
    try:
        url = "https://text.pollinations.ai/"
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "شما مشاور رسمی و تحلیل‌گر بازار پلیمر و پتروشیمی شهنواز پلاست هستید. "
                        "پاسخ‌ها فارسی، روان، مستقیم و قیمت‌ها حتماً به تومان بر کیلوگرم باشند."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "model": "openai",
            "jsonMode": False
        }
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code == 200 and len(res.text.strip()) > 5:
            return res.text.strip()
    except Exception:
        pass

    # Attempt 2: Backup Prompt Formatter
    try:
        url2 = f"https://text.pollinations.ai/{prompt}?model=searchgpt&system=تحلیلگر_پلیمر_ایران"
        res2 = requests.get(url2, timeout=20)
        if res2.status_code == 200 and len(res2.text.strip()) > 5:
            return res2.text.strip()
    except Exception:
        pass

    return (
        "📌 اطلاعات تحلیلی بازار پلیمر:\n\n"
        "در حال حاضر نوسانات تالار پتروشیمی تحت تأثیر نرخ پایه بورس کالا می‌باشد. "
        f"جهت استعلام دقیق قیمت‌های روز و ثبت سفارش با واحد فروش تماس حاصل فرمایید:\n☎️ {SUPPORT_PHONE}"
    )

# 3. Scheduled Channel Broadcast Loop
async def channel_sentinel_worker(app):
    await asyncio.sleep(20)
    while True:
        prompt = (
            "یک گزارش کوتاه و تمیز (حداکثر ۱۰۰ کلمه) درباره وضعیت بازار پلیمر و مواد اولیه پلاستیک ایران بنویسید "
            "شامل: عنوان، نوسانات امروز، تابلوی مظنه گریدهای پرمصرف به تومان/کیلوگرم، و توصیه خرید."
        )
        try:
            report = query_ai_engine(prompt)
            if report and len(report) > 30:
                msg = (
                    f"{report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"☎️ تماس و استعلام فوری: {SUPPORT_PHONE}\n"
                    f"📢 کانال تخصصی: {TARGET_CHAT_ID}"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=msg)
                logging.info("گزارش روزانه در کانال درج شد.")
        except Exception as err:
            logging.error(f"خطا در ارسال به کانال: {err}")

        await asyncio.sleep(1800)  # هر ۳۰ دقیقه

# 4. Telegram Handlers
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "سلام! به سامانه هوشمند شهنواز پلاست خوش آمدید.\n\n"
        "سوال خود را در مورد قیمت مواد پلیمری، فرمولاسیون، گریدهای تزریقی/بادی/فیلم بپرسید."
    )
    await update.message.reply_text(welcome)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type

    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    waiting = await update.message.reply_text("🔎 در حال دریافت و تحلیل اطلاعات...")
    response = query_ai_engine(text)
    await waiting.edit_text(response)

async def post_init(application):
    asyncio.create_task(channel_sentinel_worker(application))

if __name__ == "__main__":
    # Start web server thread
    threading.Thread(target=run_server, daemon=True).start()

    # Clear old webhooks
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=8)
    except Exception:
        pass

    # Build Application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    logging.info("Bot is starting polling...")
    app.run_polling(drop_pending_updates=True)
