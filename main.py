import asyncio
import http.server
import logging
import os
import random
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
TELEGRAM_TOKEN = "8844207944:AAHo15EbaQkdg8XK-w2FkGXb-TA7TvvRXqw"
GROQ_API_KEY = "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"

ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        logging.info(f"وب‌سرور روی پورت {port} فعال شد.")
        httpd.serve_forever()

def ask_ai(prompt_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gemma2-9b-it",
        "messages": [
            {
                "role": "system",
                "content": "شما دستیار و تحلیل‌گر ارشد بازار پلیمر، بورس کالا و صنعت پتروشیمی شهنواز پلاست هستید. تمام پاسخ‌ها منظم، تخصصی، به فارسی روان و قیمت‌ها تفکیک‌شده به «تومان بر کیلوگرم» باشد.",
            },
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.4,
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=40)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
        else:
            return f"خطا در مدل: {res.text}"
    except Exception as err:
        return f"خطای ارتباطی: {str(err)}"

async def autonomous_market_sentinel(app):
    """ناظر کاملاً خودکار و منعطف بازار"""
    await asyncio.sleep(15)
    while True:
        prompt = """
        شما ناظر هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست هستید.
        وضعیت کلی، نوسانات یا سیگنال‌های احتمالی بازار را ارزیابی کنید.
        
        اگر یک فرصت خرید، سیگنال مهم یا تحول قیمتی قابل‌توجه در بازار وجود دارد، یک پست تحلیلی کوتاه و جذاب (حداکثر ۱۱۰ کلمه) با قالب زیر بنویسید:
        
        📌 [عنوان فوری | مثل: 🚨 سیگنال خرید روز | ⚡ نبض بازار پتروشیمی]
        
        🔹 وضعیت و محرک بازار:
        (توضیح کوتاه ۱ یا ۲ خطی)
        
        💰 تابلوی مظنه گریدهای پرمصرف (حتماً با درج «تومان بر هر کیلوگرم»):
        ▫️ فیلم سنگین (F7000 / 020): ... تومان
        ▫️ فیلم سبک (0075 / 2420): ... تومان
        ▫️ بادی (BL3): ... تومان
        ▫️ تزریقی / PP: ... تومان
        
        🎯 تصمیم پیشنهادی به کارگاه‌ها:
        (خرید پله‌ای / دست نگه‌داشتن)
        
        ⏳ مهلت اعتبار: ...
        
        اگر بازار در آرامش کامل است و هیچ سیگنال ارزشمندی وجود ندارد، فقط و فقط بنویسید: NO_UPDATE
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
                logging.info("پست تحلیلی هوشمند در کانال منتشر شد.")
        except Exception as e:
            logging.error(f"خطا در ناظر بازار: {e}")

        wait_seconds = random.randint(1200, 5400)
        await asyncio.sleep(wait_seconds)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "هر سوالی در مورد تحلیل قیمت، گریدها، فرمولاسیون نایلون یا شرایط بازار دارید در خدمتیم."
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ‌گویی آنی در پیوی به همه کاربران"""
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_text = update.message.text
    user_id = update.effective_user.id

    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    status_msg = await update.message.reply_text("🔎 در حال بررسی و آماده‌سازی پاسخ...")

    user_prompt = f"""
    کاربر سوال زیر را پرسیده است:
    "{user_text}"
    
    پاسخ را صریح، کاربردی و به زبان فارسی روان بدهید.
    قیمت‌ها حتماً به «تومان بر کیلوگرم» باشد. در صورت نیاز به خرید عمده یا هماهنگی به شماره تماس ({SUPPORT_PHONE}) ارجاع دهید.
    """

    try:
        reply = ask_ai(user_prompt)
        await status_msg.edit_text(reply)
    except Exception as e:
        await status_msg.edit_text(f"خطا در دریافت پاسخ: {e}")

async def post_init(application):
    # ارسال پیام اطلاع‌رسانی روشن شدن ربات
    startup_msg = "🤖 ربات شهنواز پلاست با موفقیت فعال و آنلاین شد."
    try:
        await application.bot.send_message(chat_id=ADMIN_USER_ID, text=startup_msg)
    except Exception as e:
        logging.warning(f"عدم ارسال پیام استارت به ادمین: {e}")

    try:
        await application.bot.send_message(chat_id=TARGET_CHAT_ID, text=startup_msg)
    except Exception as e:
        logging.warning(f"عدم ارسال پیام استارت به کانال: {e}")

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

    print("دیده‌بان شهنواز پلاست فعال و آنلاین شد...")
    application.run_polling()
