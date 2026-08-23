import asyncio
import http.server
import logging
import os
import random
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

# اطلاعات هویتی و دسترسی
TELEGRAM_TOKEN = "8844207944:AAHo15EbaQkdg8XK-w2FkGXb-TA7TvvRXqw"
GEMINI_API_KEY = "AQ.Ab8RN6LalDK3h5kqU6R2mmoV98XS..."  # کلید کامل Gemini خود را اینجا قرار دهید

ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# تعریف کلاینت Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"وب‌سرور روی پورت {port} فعال شد.")
        httpd.serve_forever()

def ask_gemini(prompt_text):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
        )
        return response.text.strip()
    except Exception as err:
        return f"خطا در مدل جمینای: {str(err)}"

async def send_market_update(app):
    prompt = """
    شما تحلیل‌گر ارشد بازار پلیمر و پتروشیمی ایران برای کانال @shahnawazplast هستید.
    یک گزارش تحلیلی کوتاه و بسیار شیک بنویسید:
    
    📌 [عنوان داغ و فوری بازار]
    
    🔹 وضعیت معاملات و بورس کالا:
    (۱ الی ۲ خط تحلیل صریح)
    
    💰 مظنه گریدهای پرمصرف (تومان بر کیلوگرم):
    ▫️ فیلم سنگین (F7000 / 020): ... تومان
    ▫️ فیلم سبک (0075 / 2420): ... تومان
    ▫️ بادی (BL3): ... تومان
    ▫️ تزریقی و PP: ... تومان
    
    🎯 پیشنهاد به کارگاه‌ها:
    (سیگنال شفاف خرید یا انتظار)
    """
    try:
        report = ask_gemini(prompt)
        if "خطا" not in report and len(report) > 30:
            final_post = (
                f"{report}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"☎️ مشاوره و سفارش: {SUPPORT_PHONE}\n"
                "📢 رسانه تخصصی: @shahnawazplast"
            )
            await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
            logging.info("پست تحلیلی جمینای در کانال منتشر شد.")
    except Exception as e:
        logging.error(f"خطا در ارسال تحلیل: {e}")

async def autonomous_market_sentinel(app):
    # ۱۰ ثانیه بعد از روشن شدن یک پیام تستی می‌فرستد
    await asyncio.sleep(10)
    await send_market_update(app)

    # زمان‌بندی شناور و غیرثابت (بین ۳۰ تا ۹۰ دقیقه)
    while True:
        wait_seconds = random.randint(1800, 5400)
        await asyncio.sleep(wait_seconds)
        await send_market_update(app)

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
    user_text = update.message.text
    user_id = update.effective_user.id

    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    status_msg = await update.message.reply_text("🔎 در حال استخراج و تحلیل داده‌ها...")

    user_prompt = f"""
    کاربر سوال زیر را پرسیده است:
    "{user_text}"
    
    پاسخ را صریح، کاربردی و به فارسی روان بنویسید.
    قیمت‌ها تفکیک‌شده به «تومان بر کیلوگرم» باشد. در صورت نیاز به خرید عمده به شماره ({SUPPORT_PHONE}) ارجاع دهید.
    """

    try:
        reply = ask_gemini(user_prompt)
        await status_msg.edit_text(reply)
    except Exception as e:
        await status_msg.edit_text(f"خطا در ارتباط: {str(e)}")

async def post_init(application):
    startup_msg = "🤖 ربات شهنواز پلاست با جمینای فعال شد."
    try:
        await application.bot.send_message(chat_id=ADMIN_USER_ID, text=startup_msg)
    except Exception:
        pass

    asyncio.create_task(autonomous_market_sentinel(application))

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

    print("دیده‌بان شهنواز پلاست با هوش مصنوعی جمینای فعال شد...")
    application.run_polling()
