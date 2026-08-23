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

# احراز هویت و دسترسی‌ها
TELEGRAM_TOKEN = "8844207944:AAHo15EbaQkdg8XK-w2FkGXb-TA7TvvRXqw"
GROQ_API_KEY = "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"

ADMIN_USER_ID = 6757681583
ADMIN_USERNAME = "shahnawaz_admin"

TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

MARKET_CHECK_INTERVAL = 1800  # هر ۳۰ دقیقه بررسی هوشمند وضعیت بازار

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
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "شما مشاور ارشد بازار پلیمر، بورس کالا و صنعت پتروشیمی شهنواز پلاست هستید. کلیه قیمت‌ها را دقیق و با واحد «تومان بر کیلوگرم» بنویسید. پاسخ‌ها بسیار شکیل، خلاصه، تفکیک‌شده و کاربردی باشد.",
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

async def market_sentinel_loop(app):
    await asyncio.sleep(10)
    while True:
        prompt = """
        یک گزارش کوتاه و منظم (حداکثر ۱۲۰ کلمه) درباره وضعیت بازار پلیمر و پتروشیمی ایران بنویسید:
        
        📌 [عنوان جذاب | مثل: 🚨 سیگنال خرید روز | ⚡ نوسانات تالار پتروشیمی]
        
        🔹 رویداد مهم:
        (توضیح کوتاه ۱ یا ۲ خطی وضعیت بورس کالا، عرضه یا ارز)
        
        💰 تابلوی مظنه گریدهای پرمصرف (حتماً با درج «تومان بر هر کیلوگرم»):
        ▫️ فیلم سنگین (F7000 / 020): ... تومان
        ▫️ فیلم سبک (0075 / 2420): ... تومان
        ▫️ بادی (BL3): ... تومان
        ▫️ تزریقی / PP: ... تومان
        
        🎯 توصیه عملیاتی به تولیدکننده:
        (سیگنال شفاف: خرید پله‌ای / دست نگه‌داشتن)
        
        ⏳ مهلت اعتبار تحلیل: ...
        
        قانون: اگر تحول خاصی در بازار نیست فقط بنویسید NO_UPDATE
        """

        try:
            report = ask_ai(prompt)
            if "NO_UPDATE" not in report and "خطا" not in report and len(report) > 30:
                final_post = (
                    f"{report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"☎️ مشاوره و سفارش: {SUPPORT_PHONE}\n"
                    "📢 کانال رسمی: @shahnawazplast"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
                logging.info("گزارش تحلیلی به کانال ارسال شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال: {e}")

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
        await status_msg.edit_text(f"خطا در ارتباط: {e}")

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

    print("ربات شهنواز پلاست با هوش مصنوعی Groq فعال شد...")
    application.run_polling()
