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

# اطلاعات دسترسی
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE").strip()
ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
PORT = int(os.environ.get("PORT", 10000))

# پرامپت اختصاصی مشاور و تحلیل‌گر تخصصی بازار
SYSTEM_PROMPT = """
شما مغز متفکر و تحلیل‌گر ارشد بازار پلیمر، بورس کالا، ارز و صنایع پلاستیک شهنواز پلاست هستید.
وظایف اصلی شما:
۱. پاسخ تخصصی و تحلیلی درباره تمام گریدهای پلیمری (فیلم سنگین F7000/020، فیلم سبک 0209/0075/2420، بادی BL3، تزریقی، PP و ...).
۲. تحلیل وضعیت خرید یا فروش: ارائه سیگنال صریح (نقطه ورود به معامله، زمان خرید پله‌ای، خالی نگه داشتن انبار یا پر کردن انبار).
۳. تحلیل تاثیر نرخ ارز (دلار و یورو)، رقابت‌های تالار پتروشیمی در بورس کالا و عرضه هفتگی.
۴. زبان پاسخ: کاملاً فارسی، روان، محترمانه، دقیق، تحلیلی و قیمتی بر پایه تومان بر هر کیلوگرم.
هیچ‌وقت پیام تکراری ندهید و برای هر پرسش یک تحلیل زنده و منطقی بنویسید.
"""

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# سرور داخلی پایدار
class WebHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Shahnawaz Plast AI Sentinel Online.")

def run_server():
    try:
        with socketserver.TCPServer(("", PORT), WebHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"خطای سرور داخلی: {e}")

# موتور پردازش با چند هوش مصنوعی هوشمند جایگزین
def ask_ai(prompt: str) -> str:
    # موتور ۱: اتصال مستقیم به پردازشگر ابری
    try:
        url = "https://text.pollinations.ai/"
        payload = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "model": "mistral",
            "seed": 101
        }
        res = requests.post(url, json=payload, timeout=25)
        if res.status_code == 200 and len(res.text.strip()) > 20:
            return res.text.strip()
    except Exception:
        pass

    # موتور ۲: پشتیبان تحلیلی سریع
    try:
        url2 = "https://text.pollinations.ai/"
        payload2 = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "model": "searchgpt"
        }
        res2 = requests.post(url2, json=payload2, timeout=25)
        if res2.status_code == 200 and len(res2.text.strip()) > 20:
            return res2.text.strip()
    except Exception:
        pass

    # موتور ۳: پشتیبان متنی زنده
    try:
        clean_p = prompt.replace(" ", "%20")
        url3 = f"https://text.pollinations.ai/{clean_p}?system=شما_تحلیلگر_بازار_پلیمر_و_پلاستیک_هستید"
        res3 = requests.get(url3, timeout=20)
        if res3.status_code == 200 and len(res3.text.strip()) > 10:
            return res3.text.strip()
    except Exception as e:
        return f"خطا در دریافت تحلیل: {str(e)}"

    return "در پردازش تحلیل اختلالی پیش آمد. لطفاً مجدداً سوال خود را بپرسید."

# حلقه ارسال خودکار سیگنال و تحلیل به کانال
async def channel_sentinel_worker(app):
    await asyncio.sleep(20)
    while True:
        prompt = """
        یک گزارش تحلیلی جامع، فوری و بسیار جذاب برای کانال تلگرامی تخصصی بازار پلیمر بنویسید شامل بخش‌های زیر:
        
        📊 نبض بازار پلیمر و پتروشیمی
        🔹 وضعیت تالار بورس کالا، رقابت‌ها و نوسان نرخ ارز
        💰 مظنه روز گریدهای پرمصرف (فیلم سبک، سنگین، تزریقی، بادی) به تومان بر کیلوگرم
        🎯 استراتژی عملیاتی برای تولیدکننده (آیا الان وقت خرید است؟ انبارداری یا فروش؟)
        ⏳ پیش‌بینی روند بازار برای روزهای آینده
        """
        try:
            report = ask_ai(prompt)
            if report and len(report) > 40 and "خطا" not in report:
                msg = (
                    f"{report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"📢 رسانه تخصصی تحلیل بازار: {TARGET_CHAT_ID}"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=msg)
                logging.info("گزارش به کانال فرستاده شد.")
        except Exception as err:
            logging.error(f"خطا در ارسال کانال: {err}")

        await asyncio.sleep(1800)  # هر ۳۰ دقیقه

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🤖 ربات هوشمند شهنواز پلاست با حداکثر توان فعال شد.\n\n"
        "تحلیل‌گر تخصصی انواع گریدهای پلیمری (۰۲۰۹، F7000، BL3 و ...)، بررسی نوسانات بورس کالا، نرخ ارز و نقاط ورود/خروج و خرید مواد اولیه در خدمت شماست.\n\n"
        "هر سوال یا تحلیلی می‌خواهید بپرسید."
    )
    await update.message.reply_text(welcome)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type

    # در گروه‌ها فقط به دستورات مدیر پاسخ می‌دهد
    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    waiting = await update.message.reply_text("🔎 در حال پردازش و استخراج تحلیل تخصصی...")
    response = ask_ai(text)
    await waiting.edit_text(response)

async def post_init(application):
    asyncio.create_task(channel_sentinel_worker(application))

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()

    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=8)
    except Exception:
        pass

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    logging.info("ربات آنلاین شد...")
    app.run_polling(drop_pending_updates=True)
