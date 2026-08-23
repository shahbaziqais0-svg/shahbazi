# پاسخ هوشمند به سوالات کاربران در پیوی
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
    # اجرای وب‌سرور در ترد جداگانه جهت تأیید سلامت در Render
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
