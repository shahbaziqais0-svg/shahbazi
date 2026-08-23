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

# توکن تلگرام
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE").strip()

ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"

MARKET_CHECK_INTERVAL = 1800  # هر ۳۰ دقیقه

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# سرور داخلی پایدار برای Render
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            logging.info(f"وب‌سرور روی پورت {port} فعال شد.")
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"خطای وب‌سرور: {e}")

def ask_ai(prompt_text):
    """هوش مصنوعی کاملاً آزاد و بدون نیاز به کلید و ثبت‌نام"""
    url = "https://text.pollinations.ai/"
    
    system_instruction = (
        "شما تحلیل‌گر ارشد بازار پلیمر، بورس کالا و صنعت پتروشیمی ایران برای مجموعه شهنواز پلاست هستید. "
        "پاسخ‌ها را کامل، دقیق، کاربردی و بدون مقدمه‌چینی بنویسید. "
        "تمام قیمت‌ها را تفکیک‌شده و با واحد «تومان بر کیلوگرم» اعلام کنید."
    )
    
    payload = {
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt_text}
        ],
        "model": "openai",
        "seed": 42
    }

    try:
        res = requests.post(url, json=payload, timeout=40)
        if res.status_code == 200:
            return res.text.strip()
        else:
            return f"پاسخ دریافت نشد (کد {res.status_code})"
    except Exception as err:
        return f"خطای ارتباط با سرور: {str(err)}"

async def market_sentinel_loop(app):
    await asyncio.sleep(15)
    while True:
        prompt = """
        یک گزارش کوتاه و منظم (حداکثر ۱۰۰ تا ۱۲۰ کلمه) درباره آخرین وضعیت بازار پلیمر و پتروشیمی ایران برای کانال بنویسید:
        
        📌 [عنوان فوری و جذاب | مثل: 🚨 سیگنال خرید روز | ⚡ وضعیت تالار بورس کالا]
        
        🔹 رویداد مهم بازار:
        (توضیح کوتاه ۱ یا ۲ خطی وضعیت عرضه پتروشیمی‌ها، نوسان نرخ پایه یا دلار)
        
        💰 تابلوی مظنه گریدهای پرمصرف (حتماً با واحد «تومان بر هر کیلوگرم»):
        ▫️ فیلم سنگین (F7000 / 020): ... تومان
        ▫️ فیلم سبک (0075 / 2420): ... تومان
        ▫️ بادی (BL3): ... تومان
        ▫️ تزریقی / PP: ... تومان
        
        🎯 توصیه عملیاتی به تولیدکننده:
        (خرید پله‌ای / دست نگه‌داشتن)
        
        ⏳ مهلت اعتبار تحلیل: ...
        
        قانون: اگر در بازار تحول خاصی نیست فقط بنویسید NO_UPDATE
        """

        try:
            report = ask_ai(prompt)
            if "NO_UPDATE" not in report and "خطا" not in report and len(report) > 30:
                final_post = (
                    f"{report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"☎️ مشاوره و سفارش: {SUPPORT_PHONE}\n"
                    f"📢 رسانه تخصصی: {TARGET_CHAT_ID}"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
                logging.info("تحلیل بازار به کانال ارسال شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال: {e}")

        await asyncio.sleep(MARKET_CHECK_INTERVAL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "سلام! به دستیار هوشمند بازار پلیمر و پتروشیمی شهنواز پلاست خوش آمدید.\n\n"
        "هر سوالی درباره قیمت مواد، گریدها، بورس کالا یا فرمولاسیون دارید مستقیماً بپرسید."
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

    status_msg = await update.message.reply_text("🔎 در حال دریافت تحلیل بازار...")

    user_prompt = f"""
    کاربر سوال زیر را پرسیده است:
    "{user_text}"
    
    پاسخ را دقیق، کاربردی و با قیمت‌ها به «تومان بر کیلوگرم» بدهید. در صورت نیاز به خرید یا مشاوره به شماره ({SUPPORT_PHONE}) ارجاع دهید.
    """

    reply = ask_ai(user_prompt)
    await status_msg.edit_text(reply)

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

        print("ربات شهنواز پلاست با سیستم جدید متصل شد...")
        application.run_polling(drop_pending_updates=True)
    except Exception as err:
        logging.critical(f"خطای اجرای ربات: {err}")
