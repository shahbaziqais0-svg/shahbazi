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

# دریافت امن کلیدها از پنل Render یا تعریف مستقیم
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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").strip()

ADMIN_USER_ID = 6757681583
ADMIN_USERNAME = "shahnawaz_admin"

TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

MARKET_CHECK_INTERVAL = 1800  # هر ۳۰ دقیقه

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# وب‌سرور داخلی سبک سازگار با Render
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            logging.info(f"وب‌سرور داخلی روی پورت {port} فعال شد.")
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"خطای وب‌سرور: {e}")

def ask_ai(prompt_text):
    """تست خودکار مدل‌های فعال Groq برای جلوگیری از هرگونه خطای نام مدل"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # لیست تمام مدل‌های معتبر و فعال Groq
    candidate_models = [
        "llama-3.3-70b-versatile",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]

    last_error = ""
    for model_name in candidate_models:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "شما دستیار و مشاور تخصصی بازار پلیمر، بورس کالا و صنعت پلاستیک شهنواز پلاست هستید. "
                        "پاسخ‌ها را دقیق، کامل، فارسی روان، بدون زیاده‌گویی و با ذکر قیمت‌ها به تومان بر هر کیلوگرم بنویسید."
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
            else:
                last_error = res.text
        except Exception as err:
            last_error = str(err)
            
    return f"خطا در مدل: {last_error}"

async def market_sentinel_loop(app):
    await asyncio.sleep(15)
    while True:
        prompt = """
        یک پیام کوتاه و تفکیک‌شده (حداکثر ۱۰۰ کلمه) درباره آخرین وضعیت بازار پلیمر و پتروشیمی ایران برای کانال بنویسید:
        
        📌 [عنوان جذاب | مثل: 🚨 سیگنال خرید روز | ⚡ نوسانات تالار پتروشیمی]
        
        🔹 رویداد مهم بازار:
        (توضیح بسیار کوتاه وضعیت بورس کالا، عرضه یا ارز)
        
        💰 تابلوی مظنه گریدهای پرمصرف (حتماً با واحد «تومان بر هر کیلوگرم»):
        ▫️ فیلم سنگین (F7000 / 020): ... تومان
        ▫️ فیلم سبک (0075 / 2420): ... تومان
        ▫️ بادی (BL3): ... تومان
        ▫️ تزریقی / PP: ... تومان
        
        🎯 توصیه عملیاتی به تولیدکننده:
        (خرید پله‌ای / دست نگه‌داشتن)
        
        ⏳ مهلت اعتبار تحلیل: ...
        
        قانون: اگر در بازار هیچ نوسان و تحولی نیست فقط بنویسید NO_UPDATE
        """

        try:
            report = ask_ai(prompt)
            if "NO_UPDATE" not in report and "خطا" not in report and len(report) > 30:
                final_post = (
                    f"{report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"☎️ مشاوره و سفارش: {SUPPORT_PHONE}\n"
                    "📢 رسانه تخصصی: @shahnawazplast"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
                logging.info("گزارش تحلیلی به کانال ارسال شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال گزارش: {e}")

        await asyncio.sleep(MARKET_CHECK_INTERVAL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "هر سوالی درباره قیمت روز مواد، گریدها، فرمولاسیون یا خرید بورس کالا دارید بپرسید."
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    user_text = update.message.text

    if chat_type in ["group", "supergroup"]:
        if user_id != ADMIN_USER_ID:
            return

    status_msg = await update.message.reply_text("🔎 در حال استخراج و تحلیل داده‌ها...")

    user_prompt = f"""
    کاربر سوال زیر را پرسیده است:
    "{user_text}"
    
    پاسخ را دقیق، کاربردی و با ذکر قیمت‌ها به «تومان بر کیلوگرم» بدهید. در صورت نیاز به خرید به شماره ({SUPPORT_PHONE}) ارجاع دهید.
    """

    try:
        reply = ask_ai(user_prompt)
        await status_msg.edit_text(reply)
    except Exception as e:
        await status_msg.edit_text(f"خطا در پردازش: {e}")

async def post_init(application):
    asyncio.create_task(market_sentinel_loop(application))

if __name__ == "__main__":
    web_thread = threading.Thread(target=run_dummy_server, daemon=True)
    web_thread.start()

    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10,
        )
    except Exception:
        pass

    try:
        application = (
            ApplicationBuilder()
            .token(TELEGRAM_TOKEN)
            .post_init(post_init)
            .build()
        )

        application.add_handler(CommandHandler("start", start))
        application.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        )

        print("ربات شهنواز پلاست فعال شد...")
        application.run_polling(drop_pending_updates=True)
    except Exception as err:
        logging.critical(f"خطای کلی در اجرای ربات: {err}")
