import asyncio
import http.server
import logging
import os
import socketserver
import threading
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# خواندن کلیدها از متغیرهای محیطی Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_ID = "@shahnawaz_admin"
PORT = int(os.environ.get("PORT", 10000))

SYSTEM_PROMPT = """
شما یک هوش مصنوعی تحلیل‌گر تخصصی بازار پلیمر، پتروشیمی، بورس کالا، دلار و طلا برای رسانه شهنواز پلاست هستید.
شما فروشنده کالا نیستید و صرفاً تحلیل، آموزش و سیگنال تکنیکال/فاندامنتال می‌دهید.
پاسخ‌ها را کامل، دقیق، کاربردی و قیمت‌ها را بر حسب تومان بر کیلوگرم ارائه دهید.
"""

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# سرور وب سبک برای بالا نگه داشتن Render
class SimpleWebHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"AI Engine is Live.")

def run_web_server():
    try:
        with socketserver.TCPServer(("", PORT), SimpleWebHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"خطای سرور وب: {e}")

# سیستم تشخیص خودکار مدل فعال کلید
AI_MODEL_INSTANCE = None

def get_configured_model():
    global AI_MODEL_INSTANCE
    if AI_MODEL_INSTANCE:
        return AI_MODEL_INSTANCE

    if not GEMINI_API_KEY:
        return None

    genai.configure(api_key=GEMINI_API_KEY)
    
    # اولویت‌های استاندارد
    priority_candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro",
        "models/gemini-1.5-flash",
        "models/gemini-pro"
    ]

    # ۱. تست سریع اولویت‌ها
    for c in priority_candidates:
        try:
            m = genai.GenerativeModel(model_name=c, system_instruction=SYSTEM_PROMPT)
            m.generate_content("ping")
            AI_MODEL_INSTANCE = m
            logging.info(f"مدل فعال پیدا شد: {c}")
            return AI_MODEL_INSTANCE
        except Exception:
            continue

    # ۲. اسکن زنده مدل‌های فعال اکانت
    try:
        for m_info in genai.list_models():
            if "generateContent" in m_info.supported_generation_methods:
                try:
                    m = genai.GenerativeModel(model_name=m_info.name, system_instruction=SYSTEM_PROMPT)
                    m.generate_content("ping")
                    AI_MODEL_INSTANCE = m
                    logging.info(f"مدل از لیست زنده انتخاب شد: {m_info.name}")
                    return AI_MODEL_INSTANCE
                except Exception:
                    continue
    except Exception as e:
        logging.error(f"خطای اسکن مدل‌ها: {e}")

    return None

def ask_ai(prompt_text: str) -> str:
    model = get_configured_model()
    if not model:
        return "خطا: کلید Gemini فعال یافت نشد یا دسترسی مسدود است."
    
    try:
        res = model.generate_content(prompt_text)
        if res and res.text:
            return res.text.strip()
        return "پاسخی از مدل دریافت نشد."
    except Exception as err:
        return f"خطا در مدل: {str(err)}"

# ارسال زمان‌بندی شده به کانال
async def channel_broadcast_job(app):
    await asyncio.sleep(25)
    while True:
        prompt = """
        یک گزارش تحلیلی کوتاه، جذاب و آموزشی درباره وضعیت روز بازار پلیمر ایران، دلار، بورس کالا و گریدهای فیلم سبک و سنگین (با مظنه تومان/کیلوگرم) و استراتژی انبارداری برای کانال تلگرام بنویسید.
        """
        try:
            report = ask_ai(prompt)
            if report and "خطا" not in report and len(report) > 40:
                final_post = (
                    f"{report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"📢 رسانه تخصصی شهنواز پلاست: {TARGET_CHAT_ID}\n"
                    f"👤 پشتیبانی: {SUPPORT_ID}"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
                logging.info("پیام در کانال منتشر شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال به کانال: {e}")

        await asyncio.sleep(1800)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "سلام! سیستم هوشمند تحلیل بازار شهنواز پلاست آنلاین است.\n\n"
        "تحلیل گریدهای پلیمری (0209، فیلم، بادی)، اخبار بورس کالا، نرخ ارز و مشاوره خرید/انبارداری را مستقیماً بپرسید."
    )
    await update.message.reply_text(welcome)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type

    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    wait_msg = await update.message.reply_text("🔎 در حال استخراج و تحلیل تخصصی...")
    reply_text = ask_ai(text)
    
    final_reply = f"{reply_text}\n\n━━━━━━━━━━━━━━━\n📢 {TARGET_CHAT_ID} | 👤 پشتیبانی: {SUPPORT_ID}"
    await wait_msg.edit_text(final_reply)

async def post_init_setup(application):
    asyncio.create_task(channel_broadcast_job(application))

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init_setup)
        .build()
    )

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_user_message))

    logging.info("Bot is starting...")
    application.run_polling(drop_pending_updates=True)
