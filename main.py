import asyncio
import http.server
import logging
import os
import socketserver
import threading
import requests
from google import genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# تنظیمات هویتی
TELEGRAM_TOKEN = "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE"
GEMINI_API_KEY = "AQ.Ab8RN6LalDK3h5kqU6R2mmoV98XS..."  # کلید کامل خود را دقیقاً اینجا قرار دهید

ADMIN_USER_ID = 6757681583
ADMIN_USERNAME = "shahnawaz_admin"

TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

MARKET_CHECK_INTERVAL = 1800  # هر ۳۰ دقیقه

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# راه‌اندازی کلاینت رسمی گوگل با کلید OAuth
client = genai.Client(api_key=GEMINI_API_KEY)

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"وب‌سرور روی پورت {port} فعال است.")
        httpd.serve_forever()

def ask_gemini(prompt_text):
    """فراخوانی استاندارد با کتابخانه رسمی گوگل"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
            config={"tools": [{"google_search": {}}]},
        )
        return response.text.strip()
    except Exception as err:
        return f"خطا در پردازش هوش مصنوعی: {str(err)}"

async def market_sentinel_loop(app):
    await asyncio.sleep(10)
    while True:
        prompt = """
        شما تحلیل‌گر ارشد و دیده‌بان بازار پلیمر، پلاستیک و پتروشیمی ایران برای کانال @shahnawazplast هستید.
        
        یک پیام بسیار شیک، منظم، تفکیک‌شده و کاربردی بر اساس آخرین تحولات و قیمت‌های بازار بنویسید (حداکثر ۱۲۰ کلمه):
        
        📌 [عنوان فوری | مثلاً: 🚨 سیگنال خرید روز | ⚡ نوسانات تالار بورس کالا]
        
        🔹 رویداد و وضعیت جاری:
        (توضیح کوتاه ۱ یا ۲ خطی درباره عرضه، دلار یا وضعیت پتروشیمی‌ها)
        
        💰 تابلوی مظنه گریدهای پرمصرف (حتماً با واحد «تومان بر هر کیلوگرم»):
        ▫️ فیلم سنگین (F7000 / 020): ... تومان
        ▫️ فیلم سبک (0075 / 2420): ... تومان
        ▫️ بادی (BL3): ... تومان
        ▫️ تزریقی / PP: ... تومان
        
        🎯 توصیه عملیاتی به تولیدکننده:
        (خرید پله‌ای / انتظار و عدم ورود به رقابت)
        
        ⏳ اعتبار تحلیل: (مثلاً تا پایان تالار امروز)
        
        قانون: ساختار منظم، ایموجی‌های تمیز و بدون علائم نگارشی خراب‌کننده.
        """
        
        try:
            market_report = ask_gemini(prompt)
            if "error" not in market_report.lower() and len(market_report) > 30:
                final_post = (
                    f"{market_report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"☎️ مشاوره و تأمین بار: {SUPPORT_PHONE}\n"
                    "📢 رسانه تخصصی: @shahnawazplast"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
                logging.info("گزارش تحلیلی با موفقیت به کانال ارسال شد.")
        except Exception as e:
            logging.error(f"خطا در ناظر بازار: {e}")

        await asyncio.sleep(MARKET_CHECK_INTERVAL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "هر سوالی درباره قیمت مواد، گریدها، فرمولاسیون یا بورس کالا دارید مستقیماً بپرسید."
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

    status_msg = await update.message.reply_text("🔎 در حال بررسی داده‌های بازار و تنظیم پاسخ...")

    user_prompt = f"""
    شما مشاور و تحلیل‌گر فنی بازار پلیمر و پتروشیمی شهنواز پلاست هستید.
    کاربر سوال زیر را پرسیده است:
    "{user_text}"
    
    پاسخ را با قواعد زیر بنویسید:
    - دقیق، صریح و به زبان فارسی روان.
    - تمام قیمت‌ها به «تومان بر کیلوگرم» تفکیک شوند.
    - بدون مقدمه‌چینی اضافه.
    - در صورت لزوم ثبت سفارش، ارجاع به شماره تماس ({SUPPORT_PHONE}) داده شود.
    """

    try:
        reply = ask_gemini(user_prompt)
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
            timeout=15,
        )
    except Exception:
        pass

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

    print("دیده‌بان شهنواز پلاست آنلاین شد...")
    application.run_polling()
