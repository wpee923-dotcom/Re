import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asmi)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

OWNER_ID = 7076215547  # ايدي المطور

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        await update.message.reply_text("مرحباً بك أيها المطور، البوت يعمل.")
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
    # التأكد أن الرد صادر من المطور على رسالة سابقة
    if update.effective_user.id != OWNER_ID or not update.message.reply_to_message:
        return

    replied = update.message.reply_to_message

    # استخراج ايدي المستخدم الأصلي من الرسالة المُعاد توجيهها
    original_user_id = None

    if replied.forward_origin:
        # إذا كانت الرسالة مُعاد توجيهها من مستخدم
        if replied.forward_origin.type == 'user':
            original_user_id = replied.forward_origin.sender_user.id
        # يمكن إضافة حالات أخرى مثل القنوات إذا لزم الأمر
    else:
        # إذا لم تكن الرسالة مُعاد توجيهها (مثلاً المطور يرد على رسالة داخل المجموعة)
        # نأخذ ايدي المرسل العادي
        original_user_id = replied.from_user.id

    if not original_user_id:
        await update.message.reply_text("لم أتمكن من تحديد المستخدم الأصلي لهذه الرسالة.")
        return

    # إعادة توجيه رد المطور إلى المستخدم الأصلي
    try:
        await update.message.forward(chat_id=original_user_id)
        logger.info(f"تم إرسال رد المطور إلى {original_user_id}")
    except Exception as e:
        logger.error(f"خطأ في إرسال الرد: {e}")
        await update.message.reply_text("حدث خطأ أثناء إرسال الرد. تأكد أن المستخدم لم يحظر البوت.")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN غير موجود")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Chat(OWNER_ID) & filters.REPLY, handle_owner_reply))
    app.add_handler(MessageHandler(~filters.Chat(OWNER_ID) & ~filters.COMMAND, forward_to_owner))

    app.run_polling()

if __name__ == "__main__":
    main()
