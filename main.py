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

# زمان‌بندی ارسال به کانال: هر ۳۰ دقیقه (۱۸۰۰ ثانیه)
POST_INTERVAL_SECONDS = 1800

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# وب‌سرور داخلی برای Render
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

# وظیفه ارسال خودکار هر ۳۰ دقیقه به صورت تفکیک‌شده و نوبتی
async def auto_post_loop(app):
    await asyncio.sleep(5)
    
    post_types = [
        # نوبت ۱: تابلوی قیمت‌ها
        {
            "header": "💰 تابلوی قیمت روز و برآورد بازار پلیمر",
            "prompt": """
            شما سیستم مرجع اعلام نرخ پلیمر و مواد اولیه پلاستیک ایران هستید.
            یک جدول قیمتی بسیار دقیق و خوانا برای گریدهای اصلی بنویسید.
            
            دقت کنید:
            - تمام قیمت‌ها حتماً و موکداً به «تومان برای هر کیلوگرم» نوشته شوند.
            - حتماً قیمت گریدهای زیر تفکیک شوند:
              ۱. سنگین فیلم (020 و F7000)
              ۲. سبک فیلم (0075 و 2420)
              ۳. سبک خطی (209)
              ۴. بادی (BL3)
              ۵. تزریقی (52518)
              ۶. پلی‌پروپیلن نساجی و شیمیایی (PP)
            - جلوی هر گرید وضعیت روند (صعودی 🔺 / نزولی 🔻 / باثبات ⚖️) را با ایموجی مشخص کنید.
            - در ۲ خط پایانی، وضعیت کلی جو خرید و فروش بازار آزاد را بنویسید.
            - بدون کاراکترهای به هم ریخته یا متون غیرمرتبط باشد.
            """
        },
        # نوبت ۲: سیگنال و استراتژی خرید
        {
            "header": "🎯 سیگنال معاملاتی و استراتژی خرید پلیمر",
            "prompt": """
            شما تحلیل‌گر ارشد استراتژی خرید مواد اولیه پلاستیک و بورس کالا هستید.
            یک سیگنال عملیاتی و کاملاً شفاف برای خریداران و تولیدکنندگان بنویسید شامل:
            
            ۱. وضعیت فعلی کف‌سازی قیمت‌ها
            ۲. تعیین دقیق استراتژی: (خرید فوری / خرید پله‌ای / صبر برای اصلاح قیمت)
            ۳. مهلت زمانی اعتبار این سیگنال (مثلاً اعتبار تا ۴۸ ساعت آینده یا تا تالار بعدی بورس کالا)
            ۴. توصیه‌های اختصاصی به تولیدکنندگان نایلون، نایلکس و قطعات تزریقی.
            
            لحن جدی، صنعتی و بدون حاشیه باشد.
            """
        },
        # نوبت ۳: تحلیل جامع و بورس کالا
        {
            "header": "📊 تحلیل تخصصی بورس کالا و تالار پتروشیمی",
            "prompt": """
            شما کارشناس رسمی بورس کالا در صنعت پتروشیمی هستید.
            یک تحلیل دقیق، فنی و عمیق درباره بازار مواد اولیه بنویسید شامل:
            
            ۱. پیش‌بینی میزان رقابت در تالار پتروشیمی (درصد رقابت احتمالی روی پلی‌اتیلن‌ها و PP).
            ۲. بررسی اثر نرخ دلار حواله نیما و دلار آزاد روی قیمت پایه بعدی.
            ۳. راستی‌آزمایی روند روزهای گذشته (آیا اصلاح قیمت ادامه دارد یا بازار آماده جهش است؟).
            
            متن باید دارای پاراگراف‌های مرتب و بولت‌پوینت‌های خوانا باشد.
            """
        },
        # نوبت ۴: اخبار، عرضه و تقاضا
        {
            "header": "🏭 نبض تولید، اورهال پتروشیمی‌ها و اخبار مهم",
            "prompt": """
            شما رصدکننده تحولات صنایع بالادستی و پتروشیمی‌های ایران هستید.
            گزارش کوتاه و فوری از وضعیت عرضه و رخدادهای مهم بنویسید:
            
            ۱. وضعیت تولید و تعمیرات دوره‌ای (اورهال) مجتمع‌های پتروشیمی (جم، مارون، تبریز، شازند، امیرکبیر و...).
            ۲. تغییرات در میزان عرضه‌های هفتگی و سهمیه‌های بهین‌یاب.
            ۳. نکات کلیدی که تولیدکننده کارگاهی قبل از عقد قرارداد باید بداند.
            
            لحن بسیار حرفه‌ای و مختصر و مفید باشد.
            """
        }
    ]
    
    current_index = 0
    
    while True:
        current_post = post_types[current_index]
        
        try:
            analysis_text = ask_gemini(current_post["prompt"])
            message = (
                f"{current_post['header']}\n"
                "🏭 مجموعه تخصصی شهنواز پلاست\n\n"
                f"{analysis_text}\n\n"
                "─────────────────────\n"
                f"☎️ مشاوره و تأمین بار: {SUPPORT_PHONE}\n"
                "📢 کانال رسمی: @shahnawazplast"
            )
            
            await app.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=message
            )
            logging.info(f"پست شماره {current_index + 1} با موفقیت به کانال ارسال شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال پست به کانال: {e}")

        current_index = (current_index + 1) % len(post_types)
        await asyncio.sleep(POST_INTERVAL_SECONDS)

# دستور start در ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "هر سوالی درباره:\n"
        "🔹 قیمت روز گریدها (تومان بر کیلوگرم)\n"
        "🔹 تحلیل و پیش‌بینی درصد رقابت بورس کالا\n"
        "🔹 فرمولاسیون، ترکیب مواد و رفع عیوب تولید نایلون و تزریق\n"
        "🔹 زمان مناسب برای خرید بار\n\n"
        "دارید مستقیماً بنویسید تا پاسخ دقیق و تخصصی دریافت کنید."
    )
    await update.message.reply_text(welcome_text)

# پاسخ مستقیم و بدون جوین اجباری در پیوی
async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("⏳ در حال استخراج پاسخ تخصصی و تحلیل بازار...")

    user_prompt = f"""
    شما مهندس ارشد پلیمر و مشاور خرید بازار پتروشیمی شهنواز پلاست هستید.
    کاربر سوال زیر را پرسیده است:
    "{user_text}"
    
    دستورالعمل پاسخ:
    - مستقیماً به اصل سوال پاسخ دهید.
    - از درخواست عضویت در کانال یا پیام‌های تبلیغاتی خودداری کنید.
    - اگر درباره قیمت پرسیده است، حتماً واحد قیمت را به «تومان بر هر کیلوگرم» اعلام کنید.
    - اگر سوال فنی درباره دستگاه تولید نایلون، فرمولاسیون یا گریدهاست، با ذکر جزئیات تجربی و عملی پاسخ دهید.
    - در انتهای پاسخ، صرفاً شماره ارتباطی ({SUPPORT_PHONE}) را برای هماهنگی و خرید قید کنید.
    """

    try:
        reply_from_ai = ask_gemini(user_prompt)
        await update.message.reply_text(reply_from_ai)
    except Exception as e:
        await update.message.reply_text(f"خطا در دریافت پاسخ: {e}")

async def post_init(application):
    asyncio.create_task(auto_post_loop(application))

if __name__ == "__main__":
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

    print("ربات دیده‌بان پتروشیمی شهنواز پلاست فعال شد...")
    application.run_polling()
