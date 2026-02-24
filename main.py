import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

OWNER_ID = 7076215547  # ايدي المطور

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        await update.message.reply_text("• مرحباً بك أيها المطور، البوت يعمل بشكل طبيعي.")
    else:
        welcome_text = (
            f"• أهلاً بك عزيزي ({user.full_name}) [‏{user.id}] "
            f"في بوت التواصل الخاص بي \n\n"
            f"- أرسل رسالتك الآن ليتم إرسالها إلى مدير البوت وسيقوم بالرد عليك في أقرب وقت ممكن 📢"
        )
        await update.message.reply_text(welcome_text)

async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ترحيل رسائل المستخدمين إلى المطور"""
    try:
        await update.message.forward(chat_id=OWNER_ID)
        logger.info(f"تم توجيه رسالة من {update.effective_user.id}")
    except Exception as e:
        logger.error(f"خطأ في التوجيه: {e}")

async def handle_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود المطور وإرسالها للمستخدم الأصلي"""
    # 1. التأكد أن الرسالة من المطور نفسه
    if update.effective_user.id != OWNER_ID:
        return

    # 2. التأكد أن المطور يرد على رسالة معينة
    if not update.message.reply_to_message:
        logger.info("المطور أرسل رسالة بدون رد - يتم تجاهلها")
        return

    replied_msg = update.message.reply_to_message

    # 3. محاولة استخراج ايدي المستخدم الأصلي
    original_user_id = None

    # الطريقة الأولى: إذا كانت الرسالة المُردود عليها مُعاد توجيهها من مستخدم
    if replied_msg.forward_origin:
        if replied_msg.forward_origin.type == 'user':
            original_user_id = replied_msg.forward_origin.sender_user.id
            logger.info(f"تم استخراج ايدي المستخدم من forward_origin: {original_user_id}")
    else:
        # الطريقة الثانية: إذا لم تكن مُعاد توجيهها، قد يكون الرد على رسالة عادية (للمجموعات)
        original_user_id = replied_msg.from_user.id
        logger.info(f"تم استخراج ايدي المستخدم من from_user: {original_user_id}")

    if not original_user_id:
        await update.message.reply_text("❌ لم أتمكن من تحديد المستخدم الأصلي لهذه الرسالة.")
        logger.warning("لم يتم العثور على ايدي المستخدم الأصلي")
        return

    # 4. إرسال رد المطور إلى المستخدم
    try:
        # استخدم forward للحفاظ على اسم وصورة المطور
        await update.message.forward(chat_id=original_user_id)
        logger.info(f"✅ تم إعادة توجيه رد المطور إلى {original_user_id}")

        # إعلام المطور بأن الرد وصل (اختياري)
        await update.message.reply_text("✅ تم إرسال ردك إلى المستخدم.")
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الرد: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ أثناء إرسال الرد. قد يكون المستخدم حظر البوت أو لم يعد موجوداً."
        )

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN غير موجود في المتغيرات البيئية")

    app = Application.builder().token(token).build()

    # أوامر البوت
    app.add_handler(CommandHandler("start", start))

    # معالجة ردود المطور فقط (على الرسائل التي يرد عليها)
    app.add_handler(MessageHandler(filters.Chat(OWNER_ID) & filters.REPLY, handle_owner_reply))

    # معالجة جميع الرسائل الأخرى (من المستخدمين العاديين)
    app.add_handler(MessageHandler(~filters.Chat(OWNER_ID) & ~filters.COMMAND, forward_to_owner))

    # تشغيل البوت
    logger.info("البوت بدأ العمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
