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

# توکن جدید تلگرام و کلید هوش مصنوعی
TELEGRAM_TOKEN = "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE"
GEMINI_API_KEY = "AQ.Ab8RN6KT5fQH2evb-MPZ4aGVu0mCDDZDrm_CM0e5m3pF1L9Eag"

# آیدی عددی و مشخصات ادمین
ADMIN_USER_ID = 6757681583
ADMIN_USERNAME = "shahnawaz_admin"

TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

# زمان‌بندی ارسال خودکار در کانال: هر ۶ ساعت (۲۱۶۰۰ ثانیه)
POST_INTERVAL_SECONDS = 21600

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# وب‌سرور داخلی جهت تأیید سلامت در رندر
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"وب‌سرور داخلی روی پورت {port} فعال شد.")
        httpd.serve_forever()

def ask_gemini(prompt_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"خطا در پردازش هوش مصنوعی:\n{response.text}"
    except Exception as err:
        return f"خطای ارتباطی: {str(err)}"

# وظیفه ارسال خودکار دوره‌ای به کانال
async def auto_post_loop(app):
    await asyncio.sleep(5)
    while True:
        prompt = """
        شما موتور هوشمند رصد، راستی‌آزمایی و تحلیل بازار پتروشیمی و پلیمر ایران برای کانال @shahnawazplast هستید.
        
        یک گزارش جامع، روزآمد و دقیق با بخش‌های زیر تولید کنید:
        
        ۱. 🔍 راستی‌آزمایی پیش‌بینی‌های قبلی:
        - ارزیابی تحقق نوسانات و روندهای تخمین‌زده‌شده اخیر.
        
        ۲. 🏭 رویدادها و اخبار روز پتروشیمی:
        - آخرین وضعیت پتروشیمی‌ها، نرخ خوراک، وضعیت ارز و تصمیمات بورس کالا.
        
        ۳. 💰 تابلوی قیمت‌های تخمینی بازار و بورس (به تومان/کیلوگرم):
        - پلی‌اتیلن سنگین فیلم (020 / F7000)
        - پلی‌اتیلن سبک فیلم (0075 / 2420)
        - پلی‌اتیلن بادی (BL3)
        - انواع پلی‌پروپیلن (PP نساجی و شیمیایی)
        
        ۴. 🎯 سیگنال مشخص خرید/فروش + زمان اعتبار:
        - استراتژی مشخص برای تولیدکنندگان (خرید فوری، انتظار، یا خرید پله‌ای).
        
        قوانین: نگارش تمیز، استفاده از ایموجی‌های منظم و بدون ساختارهای مارک‌داون پیچیده.
        """
        
        try:
            analysis_text = ask_gemini(prompt)
            message = (
                "📊 دیده‌بان جامع، قیمت‌ها و تحلیل تخصصی پتروشیمی\n"
                "🏭 شهنواز پلاست\n\n"
                f"{analysis_text}\n\n"
                "─────────────────────\n"
                f"☎️ پشتیبانی: {SUPPORT_PHONE}\n"
                "📢 کانال اطلاع‌رسانی: @shahnawazplast"
            )
            
            await app.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=message
            )
            logging.info("گزارش خودکار در کانال ثبت شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال گزارش به کانال: {e}")

        await asyncio.sleep(POST_INTERVAL_SECONDS)

# پاسخ به دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "شما می‌توانید هر سوالی درباره قیمت مواد، گریدها، تحلیل بورس یا فرمول‌های تولید پلاستیک دارید مستقیماً بپرسید."
    )
    await update.message.reply_text(welcome_text)

# بررسی و پردازش پیام‌ها با اعمال محدودیت دسترسی در گروه
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    user_text = update.message.text

    # اگر پیام داخل گروه یا سوپرگروه ارسال شده باشد
    if chat_type in ["group", "supergroup"]:
        # فقط در صورتی که پیام از طرف خودتان باشد پاسخ می‌دهد
        if user_id != ADMIN_USER_ID:
            return  # پیام سایر افراد نادیده گرفته می‌شود

    # اگر در پیوی بود یا توسط ادمین در گروه ارسال شده بود:
    status_msg = await update.message.reply_text("⏳ در حال پردازش و استخراج تحلیل تخصصی...")

    user_prompt = f"""
    شما مشاور فنی و تحلیل‌گر تخصصی بازار پتروشیمی، پلیمرها و تولید پلاستیک در مجموعه شهنواز پلاست هستید.
    کاربر سوال زیر را مطرح کرده است:
    "{user_text}"
    
    پاسخ را با ویژگی‌های زیر بنویسید:
    - دقیق، محترمانه و به زبان فارسی روان.
    - در صورت نیاز به پیگیری خرید یا مشاوره اختصاصی، شماره تماس پشتیبانی ({SUPPORT_PHONE}) ذکر شود.
    - متن خروجی ساده و بدون تگ‌های خراب‌کننده باشد.
    """

    try:
        reply_from_ai = ask_gemini(user_prompt)
        await status_msg.edit_text(reply_from_ai)
    except Exception as e:
        await status_msg.edit_text(f"خطا در دریافت تحلیل: {e}")

async def post_init(application):
    asyncio.create_task(auto_post_loop(application))

if __name__ == "__main__":
    # اجرای وب‌سرور در ترد مجزا
    web_thread = threading.Thread(target=run_dummy_server, daemon=True)
    web_thread.start()

    # پاک‌سازی خودکار اتصالات و وب‌هوک‌های قبلی
    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=15,
        )
        logging.info("اتصال سرور قبلی و وب‌هوک با موفقیت ریست شد.")
    except Exception as e:
        logging.error(f"خطا در ریست وب‌هوک: {e}")

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

    print("ربات دیده‌بان پتروشیمی فعال شد...")
    application.run_polling()
