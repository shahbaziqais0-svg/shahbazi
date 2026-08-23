impimport asyncio
import http.server
import html
import logging
import os
import socketserver
import threading
import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# تنظیمات احراز هویت
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

# وب‌سرور سبک داخلی
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"Dummy Server active on port {port}")
        httpd.serve_forever()

def ask_gemini(system_rule, user_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "system_instruction": {
            "parts": [{"text": system_rule}]
        },
        "contents": [{
            "parts": [{"text": user_prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return "در حال حاضر دریافت اطلاعات از سامانه تحلیلی با تأخیر مواجه است. لطفاً دقایقی دیگر مجدداً تلاش فرمایید."
    except Exception as err:
        return f"خطای سیستمی: {str(err)}"

# وظیفه ارسال خودکار هر ۳۰ دقیقه
async def auto_post_loop(app):
    await asyncio.sleep(5)
    
    system_instruction = """
    شما هسته مرکزی پردازش داده و تحلیل بازار پتروشیمی برای مجموعه بازرگانی و صنعتی «شهنواز پلاست» هستید.
    
    ممنوعیت‌های قطعی:
    ۱. هرگز متنی درباره عضویت در کانال، قفل کانال یا لینک هیچ ربات/کانال خارجی مثل A_ToolsX تولید نکنید.
    ۲. تمام قیمت‌ها را بر اساس بازه واقعی و به واحد قطعی «تومان بر هر کیلوگرم» اعلام کنید.
    ۳. فرمت خروجی فقط متن تمیز و منظم همراه با تگ‌های مجاز HTML تلگرام (<b> و <i> و کد) باشد تا کاملاً شکیل و خوانا باشد.
    """

    post_types = [
        # ۱. جدول منظم قیمت‌ها
        {
            "header": "📊 <b>تابلوی رسمی نرخ و وضعیت بازار مواد پلیمری</b>",
            "prompt": """
            یک تابلوی تفکیک‌شده و منظم از قیمت‌های روز بازار مواد اولیه پلاستیک تولید کنید.
            
            دقیقاً با این قالب‌بندی و تفکیک خطوط بنویسید:
            
            🔹 <b>پلی‌اتیلن سنگین فیلم (020 / F7000):</b>
            ├ <b>قیمت:</b> [قیمت تخمینی] تومان / کیلوگرم
            └ <b>وضعیت:</b> [صعودی 🔺 / نزولی 🔻 / باثبات ⚖️]
            
            🔹 <b>پلی‌اتیلن سبک فیلم (0075 / 2420):</b>
            ├ <b>قیمت:</b> [قیمت تخمینی] تومان / کیلوگرم
            └ <b>وضعیت:</b> [روند]
            
            🔹 <b>پلی‌اتیلن سبک خطی (LLDPE 209):</b>
            ├ <b>قیمت:</b> [قیمت تخمینی] تومان / کیلوگرم
            └ <b>وضعیت:</b> [روند]
            
            🔹 <b>پلی‌اتیلن بادی (BL3):</b>
            ├ <b>قیمت:</b> [قیمت تخمینی] تومان / کیلوگرم
            └ <b>وضعیت:</b> [روند]
            
            🔹 <b>تزریقی (52518):</b>
            ├ <b>قیمت:</b> [قیمت تخمینی] تومان / کیلوگرم
            └ <b>وضعیت:</b> [روند]
            
            🔹 <b>پلی‌پروپیلن (PP نساجی و شیمیایی):</b>
            ├ <b>قیمت:</b> [قیمت تخمینی] تومان / کیلوگرم
            └ <b>وضعیت:</b> [روند]
            
            📌 <b>نبض معاملات:</b> (در ۲ خط مختصر جو خرید و عرضه در بازار آزاد را شرح دهید).
            """
        },
        # ۲. سیگنال استراتژیک
        {
            "header": "🎯 <b>سیگنال راهبردی و استراتژی خرید مواد اولیه</b>",
            "prompt": """
            یک تحلیل سیگنال خرید/فروش برای تولیدکنندگان صنایع پلاستیک آماده کنید:
            
            🔹 <b>استراتژی پیشنهادی:</b> (خرید فوری / خرید پله‌ای / انتظار برای اصلاح قیمت)
            🔹 <b>محدوده ریسک:</b> (کم / متوسط / پرریسک)
            🔹 <b>مهلت اعتبار سیگنال:</b> (مثلاً تا ۷۲ ساعت آینده)
            
            📝 <b>توصیه اختصاصی:</b>
            - برای تولیدکنندگان نایلون و نایلکس
            - برای تولیدکنندگان قطعات تزریقی و بادی
            """
        },
        # ۳. تحلیل بورس کالا
        {
            "header": "🏛 <b>تحلیل عمقی تالار پتروشیمی و بورس کالا</b>",
            "prompt": """
            یک تحلیل حرفه‌ای از متغیرهای اقتصادی مؤثر بر بازار پلیمر ارائه دهید:
            
            🔹 <b>پیش‌بینی سقف رقابت در تالار:</b> تخمین درصد رقابت روی پلی‌اتیلن‌ها و پلی‌پروپیلن.
            🔹 <b>تأثیر نرخ حواله و ارز:</b> روند قیمت‌های پایه در هفته پیش‌رو.
            🔹 <b>جمع‌بندی تحلیلی:</b> جمع‌بندی کوتاه از وضعیت توازن عرضه و تقاضا.
            """
        }
    ]
    
    current_index = 0
    
    while True:
        current_post = post_types[current_index]
        
        try:
            content = ask_gemini(system_instruction, current_post["prompt"])
            
            message = (
                f"{current_post['header']}\n"
                "🏭 <b>شهنواز پلاست</b> | تحلیل و تأمین تخصصی پلیمر\n\n"
                f"{content}\n\n"
                "─────────────────────\n"
                f"☎️ <b>مشاوره و استعلام بار:</b> <code>{SUPPORT_PHONE}</code>\n"
                "📢 <b>کانال رسمی:</b> @shahnawazplast"
            )
            
            await app.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=message,
                parse_mode=ParseMode.HTML
            )
            logging.info(f"پست تفکیک شده شماره {current_index + 1} ارسال شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال پست: {e}")

        current_index = (current_index + 1) % len(post_types)
        await asyncio.sleep(POST_INTERVAL_SECONDS)

# دستور start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 <b>سلام و درود!</b>\n\n"
        "به دستیار هوشمند <b>شهنواز پلاست</b> خوش آمدید.\n\n"
        "📌 <b>شما می‌توانید سوالات خود را در زمینه‌های زیر مطرح کنید:</b>\n"
        "• استعلام قیمت روز گریدها (تومان / کیلوگرم)\n"
        "• پیش‌بینی رقابت‌های بورس کالا و تالار پتروشیمی\n"
        "• فرمولاسیون و حل مشکلات تولید نایلون، نایلکس و تزریق\n"
        "• زمان‌بندی مناسب برای خرید عمده مواد\n\n"
        "💬 <i>سوال خود را بنویسید تا بررسی و پاسخ داده شود.</i>"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

# پاسخ مستقیم در پیوی بدون جوین اجباری
async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("⏳ <i>در حال بررسی و تنظیم پاسخ تحلیلی...</i>", parse_mode=ParseMode.HTML)

    sys_prompt = f"""
    شما مهندس ارشد پلیمر و مشاور رسمی بازرگانی «شهنواز پلاست» هستید.
    
    دستورالعمل‌ها:
    ۱. هرگز هیچ لینکی، کانال یا رباتی برای جوین اجباری ارسال نکنید.
    ۲. پاسخ را کاملاً تخصصی، محترمانه، زیبا و به زبان فارسی بنویسید.
    ۳. تمام ارقام قیمت حتماً با واحد «تومان بر هر کیلوگرم» ذکر شوند.
    ۴. اگر سوال فنی (تولید، دستگاه اکسترودر، فرمول، شفافیت، دوخت) است، راهکار دقیق و کاربردی ارائه دهید.
    ۵. در پایان پاسخ، شماره پشتیبانی {SUPPORT_PHONE} را برای هماهنگی معرفی کنید.
    """

    try:
        reply_from_ai = ask_gemini(sys_prompt, user_text)
        
        # ارسال پاسخ تمیز
        final_reply = (
            f"{reply_from_ai}\n\n"
            "─────────────────────\n"
            f"☎️ <b>پشتیبانی و سفارش:</b> <code>{SUPPORT_PHONE}</code>"
        )
        await update.message.reply_text(final_reply, parse_mode=ParseMode.HTML)
    except Exception as e:
        # در صورت بروز خطای کاراکترهای نامعتبر HTML، متن ساده ارسال شود
        try:
            await update.message.reply_text(reply_from_ai)
        except Exception:
            await update.message.reply_text(f"خطا در پردازش پیام: {e}")

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

    print("ربات تحلیلی شهنواز پلاست با ساختار مرتب و HTML فعال شد...")
    application.run_polling()
