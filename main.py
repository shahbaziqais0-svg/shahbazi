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

# ۱. توکن ربات جدید تلگرام
TELEGRAM_TOKEN = "8862836655:AAHgueF9p3AmUdyN8BoGjEDLcMyLVkHzXIw"

# ۲. کلید هوش مصنوعی Groq
GROQ_API_KEY = "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"

# ۳. مشخصات ادمین و رسانه
ADMIN_USER_ID = 6757681583
ADMIN_USERNAME = "shahnawaz_admin"

TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

MARKET_CHECK_INTERVAL = 1800  # بررسی وضعیت هر ۳۰ دقیقه بدون ارسال اسپم

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# وب‌سرور داخلی سبک جهت حفظ پایداری در رندر
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
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "شما تحلیل‌گر ارشد بازار پلیمر، بورس کالا و صنعت پتروشیمی شهنواز پلاست هستید. "
                    "پاسخ‌ها دقیق، خوش‌فرم، بدون مقدمه‌چینی اضافه و تمام قیمت‌ها الزماً به «تومان بر کیلوگرم» تفکیک شوند."
                ),
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
            return f"خطای مدل: {res.text}"
    except Exception as err:
        return f"خطای ارتباط با سرور: {str(err)}"

async def market_sentinel_loop(app):
    await asyncio.sleep(15)
    while True:
        prompt = """
        یک گزارش کوتاه و تفکیک‌شده (حداکثر ۱۰۰ تا ۱۲۰ کلمه) درباره آخرین تحولات بازار پلیمر و پتروشیمی ایران برای کانال بنویسید:
        
        📌 [عنوان جذاب | مثلاً: 🚨 سیگنال خرید روز | ⚡ نوسانات تالار بورس کالا]
        
        🔹 تحول بازار:
        (توضیح کوتاه ۱ یا ۲ خطی درباره وضعیت عرضه، بورس یا ارز)
        
        💰 تابلوی مظنه گریدهای پرمصرف (حتماً با واحد «تومان بر هر کیلوگرم»):
        ▫️ فیلم سنگین (F7000 / 020): ... تومان
        ▫️ فیلم سبک (0075 / 2420): ... تومان
        ▫️ بادی (BL3): ... تومان
        ▫️ تزریقی / PP: ... تومان
        
        🎯 توصیه عملیاتی به تولیدکننده:
        (خرید پله‌ای / دست نگه‌داشتن)
        
        ⏳ مهلت اعتبار تحلیل: ...
        
        قانون: اگر در ساعات گذشته هیچ نوسان و رویدادی نبوده، فقط کلمه NO_UPDATE را بنویسید.
        """

        try:
            report = ask_ai(prompt)
            if "NO_UPDATE" not in report and "خطا" not in report and len(report) > 30:
                final_post = (
                    f"{report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"☎️ مشاوره و سفارش: {SUPPORT_PHONE}\n"
                    "📢 کانال تخصصی: @shahnawazplast"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
                logging.info("تحلیل جدید در کانال ثبت شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال به کانال: {e}")

        await asyncio.sleep(MARKET_CHECK_INTERVAL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "هر سوالی درباره قیمت مواد، گریدها، فرمولاسیون یا خرید بورس کالا دارید مستقیماً بپرسید."
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    user_text = update.message.text

    # محدودیت پاسخ در گروه‌ها (فقط برای ادمین)
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
        await status_msg.edit_text(f"خطا در ارتباط: {e}")

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

        print("ربات شهنواز پلاست با موفقیت فعال شد...")
        application.run_polling(drop_pending_updates=True)
    except Exception as err:
        logging.critical(f"خطا در راه‌اندازی ربات: {err}")
