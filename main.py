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

# کلیدهای احراز هویت
GEMINI_API_KEY = "AQ.Ab8RN6KT5fQH2evb-MPZ4aGVu0mCDDZDrm_CM0e5m3pF1L9Eag"
TELEGRAM_TOKEN = "8844207944:AAGMLjxUP3ImujiWTQzA2aQ_oLI6NiuIroY"

TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

# زمان‌بندی ارسال در کانال: هر ۶ ساعت (۲۱۶۰۰ ثانیه)
POST_INTERVAL_SECONDS = 21600

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# وب‌سرور سبک برای زنده نگه‌داشتن سرویس در پلن رایگان Render
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
            return f"خطا در پردازش مدل:\n{response.text}"
    except Exception as err:
        return f"خطای ارتباطی: {str(err)}"

# وظیفه ارسال خودکار دوره‌ای به کانال
async def auto_post_loop(app):
    await asyncio.sleep(5)
    while True:
        prompt = """
        شما موتور هوشمند رصد، راستی‌آزمایی و تحلیل بازار پتروشیمی و پلیمر ایران برای کانال @shahnawazplast هستید.
        
        یک گزارش کامل، روزآمد و دقیق با بخش‌های زیر بنویسید:
        
        ۱. 🔍 راستی‌آزمایی پیش‌بینی‌های قبلی:
        - بررسی اینکه آیا روندهای قیمتی و نوساناتی که در روزهای گذشته تخمین زده شده بود محقق شدند یا خیر.
        
        ۲. 🏭 رویدادها و اخبار روز صنعت پتروشیمی:
        - تحولات مهم امروز/این هفته (تعمیرات پتروشیمی‌ها، وضعیت خوراک، نوسان نرخ دلار حواله و تصمیمات بورس کالا).
        
        ۳. 💰 تابلوی قیمت‌های تخمینی بازار و بورس (به تومان بر هر کیلوگرم):
        - پلی‌اتیلن سنگین فیلم (020 / F7000)
        - پلی‌اتیلن سبک فیلم (0075 / 2420)
        - پلی‌اتیلن بادی (BL3)
        - تزریقی و پلی‌پروپیلن (PP نساجی و شیمیایی)
        
        ۴. 🎯 سیگنال شفاف خرید/فروش + مهلت زمانی اعتبار:
        - استراتژی مشخص برای تولیدکنندگان (خرید فوری، انتظار، یا خرید پله‌ای) همراه با مشخص کردن بازه زمانی اعتبار.
        
        قوانین: استفاده از ایموجی‌های منظم، بدون کاراکترهای خراب‌کننده فرمت، و کاملاً کاربردی برای صنف پلاستیک.
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
            logging.info("گزارش خودکار در کانال درج شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال گزارش به کانال: {e}")

        await asyncio.sleep(POST_INTERVAL_SECONDS)

# پاسخ به دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "شما می‌توانید هر سوالی درباره قیمت مواد، گریدها، تحلیل بورس، زمان خرید یا فرمول‌های تولید پلاستیک دارید مستقیماً اینجا بپرسید تا پاسخ دهم."
    )
    await update.message.reply_text(welcome_text)# پاسخ هوشمند به سوالات کاربران در پیوی
async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("⏳ در حال بررسی سوال و استخراج پاسخ تخصصی...")

    user_prompt = f"""
    شما مشاور فنی و تحلیل‌گر تخصصی بازار پتروشیمی، پلیمرها و تولید پلاستیک در مجموعه شهنواز پلاست هستید.
    کاربر سوال زیر را پرسیده است:
    "{user_text}"
    
    پاسخ را با ویژگی‌های زیر بنویسید:
    - دقیق، محترمانه، کاربردی و به زبان فارسی روان.
    - در صورت نیاز به راهنمایی بیشتر، کاربر را ارجاع دهید که برای پیگیری با شماره پشتیبانی ({SUPPORT_PHONE}) در ارتباط باشد.
    - پاسخ تمیز و بدون فرمت‌های پیچیده مارک‌داون باشد.
    """

    try:
        reply_from_ai = ask_gemini(user_prompt)
        await update.message.reply_text(reply_from_ai)
    except Exception as e:
        await update.message.reply_text(f"خطا در دریافت پاسخ: {e}")

async def post_init(application):
    asyncio.create_task(auto_post_loop(application))

if name == "main":
    # اجرای وب‌سرور در ترد جداگانه
    web_thread = threading.Thread(target=run_dummy_server, daemon=True)
    web_thread.start()

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_user_question)
    )

    print("ربات دیده‌بان پتروشیمی با وب‌سرور داخلی فعال شد...")
    application.run_polling()
