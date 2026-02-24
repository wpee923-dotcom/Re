import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد التسجيل بشكل مفصل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

OWNER_ID = 7076215547  # ضع ايدي المطور هنا

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
    """معالجة رد المطور على إحدى الرسائل المُعاد توجيهها"""
    # تأكد أن المرسل هو المطور
    if update.effective_user.id != OWNER_ID:
        logger.info("رسالة من غير المطور - يتم تجاهلها")
        return

    # تأكد أن الرسالة هي رد على رسالة سابقة
    if not update.message.reply_to_message:
        logger.info("المطور أرسل رسالة بدون رد - يتم تجاهلها")
        return

    replied_msg = update.message.reply_to_message
    logger.info(f"تم استلام رد من المطور على رسالة: {replied_msg.message_id}")

    # محاولة استخراج ايدي المستخدم الأصلي بعدة طرق
    original_user_id = None

    # الطريقة 1: إذا كانت الرسالة المُردود عليها مُعاد توجيهها من مستخدم
    if replied_msg.forward_origin:
        if replied_msg.forward_origin.type == 'user':
            original_user_id = replied_msg.forward_origin.sender_user.id
            logger.info(f"الطريقة 1: استخراج الايدي من forward_origin: {original_user_id}")

    # الطريقة 2: إذا لم تنجح الطريقة 1، نحاول من خلال معرف المرسل للرسالة المُعاد توجيهها
    if not original_user_id and replied_msg.from_user:
        original_user_id = replied_msg.from_user.id
        logger.info(f"الطريقة 2: استخراج الايدي من from_user: {original_user_id}")

    # الطريقة 3: البحث عن ايدي المستخدم في نص الرسالة (إذا كان مضمنًا بالصيغة [ايدي])
    if not original_user_id and replied_msg.text:
        import re
        match = re.search(r'\[‏(\d+)\]', replied_msg.text)
        if match:
            original_user_id = int(match.group(1))
            logger.info(f"الطريقة 3: استخراج الايدي من النص: {original_user_id}")

    if not original_user_id:
        await update.message.reply_text("❌ لم أتمكن من تحديد المستخدم الأصلي لهذه الرسالة.")
        logger.warning("فشل استخراج ايدي المستخدم بجميع الطرق")
        return

    # إرسال رد المطور إلى المستخدم الأصلي
    try:
        await update.message.forward(chat_id=original_user_id)
        logger.info(f"✅ تم إعادة توجيه رد المطور إلى {original_user_id}")

        # إعلام المطور بالنجاح
        await update.message.reply_text("✅ تم إرسال ردك إلى المستخدم.")
    except Exception as e:
        logger.error(f"❌ فشل إرسال الرد: {e}")
        await update.message.reply_text(
            "❌ حدث خطأ أثناء الإرسال. قد يكون المستخدم حظر البوت أو أن الايدي غير صحيح."
        )

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN غير موجود")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Chat(OWNER_ID) & filters.REPLY, handle_owner_reply))
    app.add_handler(MessageHandler(~filters.Chat(OWNER_ID) & ~filters.COMMAND, forward_to_owner))

    logger.info("البوت بدأ العمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
