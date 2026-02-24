import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

OWNER_ID = 7076215547  # ايدي المطور (ثبته)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        await update.message.reply_text("• مرحباً بك أيها المطور، البوت يعمل.")
    else:
        welcome = (
            f"• أهلاً بك عزيزي ({user.full_name}) [‏{user.id}] "
            f"في بوت التواصل الخاص بي \n\n"
            f"- أرسل رسالتك الآن ليتم إرسالها إلى مدير البوت وسيقوم بالرد عليك في أقرب وقت ممكن 📢"
        )
        await update.message.reply_text(welcome)

async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """توجيه رسالة المستخدم إلى المطور"""
    try:
        await update.message.forward(chat_id=OWNER_ID)
        logger.info(f"تم توجيه رسالة من {update.effective_user.id}")
    except Exception as e:
        logger.error(f"خطأ في التوجيه: {e}")

async def handle_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رد المطور وإرساله للمستخدم الأصلي"""
    # تأكد من أن المرسل هو المطور
    if update.effective_user.id != OWNER_ID:
        logger.info("الرسالة ليست من المطور - تجاهل")
        return

    # تأكد من أن الرسالة هي رد على رسالة سابقة
    if not update.message.reply_to_message:
        logger.info("المطور أرسل رسالة بدون رد - تجاهل")
        return

    logger.info("تم استلام رد من المطور على رسالة سابقة")

    replied = update.message.reply_to_message

    # سجل معلومات عن الرسالة المُردود عليها
    logger.info(f"الرسالة المُردود عليها: ID={replied.message_id}, من={replied.from_user.id if replied.from_user else 'لا يوجد'}")

    # حاول استخراج ايدي المستخدم الأصلي بعدة طرق
    original_user_id = None

    # الطريقة الأولى: من forward_origin
    if replied.forward_origin:
        logger.info(f"forward_origin موجود، نوعه: {replied.forward_origin.type}")
        if replied.forward_origin.type == 'user':
            original_user_id = replied.forward_origin.sender_user.id
            logger.info(f"تم العثور على ايدي المستخدم من forward_origin: {original_user_id}")

    # الطريقة الثانية: إذا لم تنجح الأولى، قد تكون الرسالة المُردود عليها هي نفس رسالة المستخدم (بدون توجيه) - هذا وارد إذا كان المطور في مجموعة
    if not original_user_id and replied.from_user:
        if replied.from_user.id != OWNER_ID:  # نتجنب أن يكون المطور نفسه
            original_user_id = replied.from_user.id
            logger.info(f"تم العثور على ايدي المستخدم من from_user: {original_user_id}")

    # الطريقة الثالثة: البحث عن ايدي في نص الرسالة الترحيبية (إذا كان المستخدم قد أرسل /start مؤخراً)
    if not original_user_id and replied.text:
        import re
        match = re.search(r'\[‏(\d+)\]', replied.text)
        if match:
            original_user_id = int(match.group(1))
            logger.info(f"تم العثور على ايدي المستخدم من النص: {original_user_id}")

    if not original_user_id:
        await update.message.reply_text("❌ لم أتمكن من تحديد المستخدم الأصلي. تأكد من أنك ترد على رسالة مُعاد توجيهها من المستخدم.")
        logger.warning("فشل استخراج ايدي المستخدم بجميع الطرق")
        return

    # محاولة إعادة توجيه رد المطور إلى المستخدم
    try:
        await update.message.forward(chat_id=original_user_id)
        logger.info(f"✅ تم إعادة توجيه رد المطور إلى {original_user_id}")
        await update.message.reply_text("✅ تم إرسال ردك إلى المستخدم.")
    except Exception as e:
        logger.error(f"❌ فشل إرسال الرد: {e}")
        await update.message.reply_text("❌ فشل الإرسال. المستخدم ربما حظر البوت.")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN غير موجود")

    app = Application.builder().token(token).build()

    # ترتيب المعالجات مهم: نضع معالج ردود المطور أولاً
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Chat(OWNER_ID) & filters.REPLY, handle_owner_reply))
    app.add_handler(MessageHandler(~filters.Chat(OWNER_ID) & ~filters.COMMAND, forward_to_owner))

    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
