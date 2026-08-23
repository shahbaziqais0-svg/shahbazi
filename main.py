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

# تنظیمات هویتی و دسترسی
TELEGRAM_TOKEN = "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE"
GEMINI_API_KEY = "AQ.Ab8RN6KT5fQH2evb-MPZ4aGVu0mCDDZDrm_CM0e5m3pF1L9Eag"

ADMIN_USER_ID = 6757681583
ADMIN_USERNAME = "shahnawaz_admin"

TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

# بازه بررسی هوشمند بازار: هر ۳۰ دقیقه (۱۸۰۰ ثانیه)
MARKET_CHECK_INTERVAL = 1800

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# وب‌سرور داخلی برای تأیید سلامت در Render
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"وب‌سرور سبک روی پورت {port} فعال شد.")
        httpd.serve_forever()

def ask_gemini_with_search(prompt_text):
    """ارسال درخواست به جمینای با قابلیت سرچ زنده وب جهت دریافت قیمت‌ها و اخبار واقعی"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }],
        "tools": [
            {"googleSearch": {}}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            return f"خطا در مدل هوش مصنوعی:\n{response.text}"
    except Exception as err:
        return f"خطای ارتباطی: {str(err)}"

# ناظر هوشمند بازار پتروشیمی (ارسال هدفمند و مقطعی بدون پیام‌های اسپم)
async def market_sentinel_loop(app):
    await asyncio.sleep(10)
    while True:
        prompt = """
        شما تحلیل‌گر ارشد و دیده‌بان لحظه‌ای بازار پلیمر و پتروشیمی ایران (شهنواز پلاست) هستید.
        
        با جستجو در اخبار و نرخ‌های اخیر بورس کالا، دلار و بازار آزاد پلیمر:
        اگر در ساعات اخیر تحول مهمی رخ داده است (نوسان نرخ ارز، اعلام قیمت پایه بورس کالا، رقابت سنگین روی یک گرید خاص، اخبار تعمیرات پتروشیمی یا فرصت طلایی خرید مواد اولیه):
        
        یک پیام بسیار شیک، مرتب، خلاصه و تفکیک‌شده (حداکثر ۱۰۰ تا ۱۵۰ کلمه) تولید کنید که ساختار زیر را داشته باشد:
        
        📌 [عنوان جذاب و فوری | مثلاً: 🚨 سیگنال فوری خرید | ⚡ نوسان تالار پتروشیمی | 📊 تابلوی مظنه روز]
        
        🔹 موضوع / خبر کلیدی:
        (توضیح بسیار خلاصه در ۱ یا ۲ خط)
        
        💰 مظنه تقریبی گریدهای پرمصرف (حتماً با درج واحد «تومان بر هر کیلوگرم»):
        ▫️ فیلم سنگین (F7000 / 020): ... تومان
        ▫️ فیلم سبک (0075 / 2420): ... تومان
        ▫️ بادی (BL3): ... تومان
        ▫️ تزریقی / PP: ... تومان
        
        🎯 توصیه عملیاتی به تولیدکننده:
        (سیگنال شفاف: مثلاً خرید فوری پله‌ای / دست نگه‌داشتن و عدم ورود به رقابت بورس)
        
        ⏳ اعتبار تحلیل: (مثلاً تا پایان تالار امروز / ۲۴ ساعت آینده)
        
        قوانین اکید:
        - کلی‌گویی نکنید؛ داده‌ها متمرکز و خوانا باشند.
        - اگر هیچ نوسان یا رویداد مهمی در بازار وجود ندارد و تغییر خاصی رخ نداده، فقط و فقط کلمه «NO_UPDATE» را برگردانید و چیز دیگری ننویسید.
        """
        
        try:
            market_report = ask_gemini_with_search(prompt)
            
            # اگر بازار تغییری نکرده باشد، پیامی ارسال نمی‌شود تا کانال شلوغ نشود
            if "NO_UPDATE" not in market_report and len(market_report) > 30:
                final_post = (
                    f"{market_report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"☎️ مشاوره و تأمین بار: {SUPPORT_PHONE}\n"
                    "📢 رسانه تخصصی: @shahnawazplast"
                )
                
                await app.bot.send_message(
                    chat_id=TARGET_CHAT_ID,
                    text=final_post
                )
                logging.info("پیام تحلیلی هدفمند در کانال منتشر شد.")
        except Exception as e:
            logging.error(f"خطا در بررسی ناظر بازار: {e}")

        await asyncio.sleep(MARKET_CHECK_INTERVAL)

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "اینجا می‌توانید درباره قیمت روز مواد، ترکیب فرمولاسیون نایلون و تزریق، جایگزینی گریدها و زمان‌بندی ورود به تالار بورس کالا سوالات خود را بپرسید."
    )
    await update.message.reply_text(welcome_text)

# پردازش پیام‌ها و اعمال محدودیت در گروه‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    user_text = update.message.text

    # محدودیت پاسخ‌گویی در گروه‌ها (صرفاً برای ادمین)
    if chat_type in ["group", "supergroup"]:
        if user_id != ADMIN_USER_ID:
            return

    status_msg = await update.message.reply_text("🔎 در حال استخراج جدیدترین داده‌های بازار و تنظیم تحلیل...")

    user_prompt = f"""
    شما مشاور ارشد و تحلیل‌گر فنی پتروشیمی، فرمولاسیون پلاستیک و بورس کالای شهنواز پلاست هستید.
    کاربر سوال زیر را پرسیده است:
    "{user_text}"
    
    پاسخ را با قواعد زیر بنویسید:
    - بررسی دقیق داده‌ها و قیمت‌های به‌روز.
    - کلیه قیمت‌ها به «تومان بر کیلوگرم» با تفکیک روشن آورده شوند.
    - پاسخ تمیز، پاراگراف‌بندی‌شده، صریح و بدون مقدمه‌چینی اضافه باشد.
    - در انتها برای ثبت سفارش یا خرید عمده، کاربر را به شماره ({SUPPORT_PHONE}) راهنمایی کنید.
    """

    try:
        reply = ask_gemini_with_search(user_prompt)
        await status_msg.edit_text(reply)
    except Exception as e:
        await status_msg.edit_text(f"خطا در پردازش تحلیل: {e}")

async def post_init(application):
    asyncio.create_task(market_sentinel_loop(application))

if __name__ == "__main__":
    # وب‌سرور داخلی برای Render
    web_thread = threading.Thread(target=run_dummy_server, daemon=True)
    web_thread.start()

    # پاک‌سازی وب‌هوک‌های قبلی
    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=15,
        )
        logging.info("وب‌هوک با موفقیت آزاد شد.")
    except Exception as e:
        logging.error(f"خطا در بررسی وب‌هوک: {e}")

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

    print("دیده‌بان هوشمند شهنواز پلاست آنلاین شد...")
    application.run_polling()
