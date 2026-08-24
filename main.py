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

# اطلاعات اتصال
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8844207944:AAGHNr1nXX-VP1drtfBN9PMgmtwwN_V8wEE").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_ID = "@shahnawaz_admin"
PORT = int(os.environ.get("PORT", 10000))

# پرامپت اختصاصی آموزشی و تحلیلی
SYSTEM_PROMPT = """
شما یک هوش مصنوعی فوق‌العاده باهوش، تحلیل‌گر اقتصادی و متخصص صنعت پلیمر و پتروشیمی هستید که برای کانال و رسانه آموزشی شهنواز پلاست فعالیت می‌کنید.
شما فروشنده کالا نیستید و هیچ باری نمی‌فروشید؛ هدف شما صرفاً آموزش، آگاهی‌بخشی، ارائه تحلیل‌های روز، نرخ ارز و طلا، بررسی بورس کالا، و راهنمایی تکنیکال و فاندامنتال به تولیدکنندگان است.

دستورالعمل پاسخ‌دهی:
۱. به هر سوال کاربر (نرخ ارز، وضعیت دلار/یورو، خرید یا فروش گریدهای پلیمری مثل 0209، F7000، BL3، اخبار بورس کالا و فرمولاسیون) دقیق، زنده و تحلیلی پاسخ دهید.
۲. سیگنال شفاف بدهید (مثلاً: آیا الان با توجه به دلار نقطه مناسبی برای خرید 0209 هست یا بهتر است انبار خالی بماند؟).
۳. پاسخ‌ها کاملاً فارسی، روان، علمی و با لحن مشاور ارشد باشد. قیمت‌ها در صورت تحلیل مواد، بر حسب تومان بر هر کیلوگرم باشد.
۴. در انتهای پیام‌ها به هیچ عنوان عبارت «واحد فروش» یا «استعلام بار» ننویسید.
"""

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# پیکربندی هوش مصنوعی رسمی گوگل
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )
else:
    ai_model = None

# سرور داخلی برای پایداری در Render
class SimpleWebHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Shahnawaz Plast AI is Live.")

def run_web_server():
    try:
        with socketserver.TCPServer(("", PORT), SimpleWebHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"خطای وب‌سرور: {e}")

def ask_ai(prompt_text: str) -> str:
    if not ai_model:
        return "خطا: لطفاً کلید GEMINI_API_KEY را در تنظیمات Environment سرور رندر وارد کنید."
    
    try:
        response = ai_model.generate_content(prompt_text)
        if response and response.text:
            return response.text.strip()
        return "هوش مصنوعی پاسخی تولید نکرد. لطفاً مجدداً امتحان کنید."
    except Exception as e:
        return f"خطا در پردازش هوش مصنوعی: {str(e)}"

# ارسال خودکار تحلیل و اخبار روز به کانال
async def channel_broadcast_job(app):
    await asyncio.sleep(30)
    while True:
        prompt = """
        یک گزارش تحلیلی، جذاب و کاملاً آموزشی درباره وضعیت روز بازار پلیمر، تحولات بورس کالا، تاثیر نرخ ارز (دلار) بر قیمت مواد و استراتژی روز برای تولیدکنندگان برای انتشار در کانال تلگرام بنویسید.
        """
        try:
            analysis = ask_ai(prompt)
            if analysis and "خطا" not in analysis and len(analysis) > 50:
                message = (
                    f"{analysis}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"📢 کانال تحلیلی و آموزشی: {TARGET_CHAT_ID}\n"
                    f"👤 پشتیبانی: {SUPPORT_ID}"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=message)
                logging.info("تحلیل در کانال منتشر شد.")
        except Exception as e:
            logging.error(f"خطا در ارسال به کانال: {e}")

        await asyncio.sleep(1800)  # هر ۳۰ دقیقه

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "سلام! دستیار هوشمند و تحلیلی شهنواز پلاست آماده است.\n\n"
        "هر سوالی درباره نرخ ارز، تحلیل گریدهای مختلف (0209، سنگین، بادی، PP)، وضعیت بازار بورس کالا، یا اخبار روز صنعت پلاستیک دارید بپرسید تا تحلیل دقیق دریافت کنید."
    )
    await update.message.reply_text(welcome)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type

    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    wait_msg = await update.message.reply_text("🔎 در حال پردازش و استخراج تحلیل تخصصی...")
    reply_text = ask_ai(user_text)
    
    # اضافه کردن امضای انتهای پیام
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

    logging.info("ربات با موتور Gemini روشن شد.")
    application.run_polling(drop_pending_updates=True)
