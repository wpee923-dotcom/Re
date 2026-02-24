import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ايدي المطور (غيّره حسب المطلوب)
OWNER_ID = 7076215547

# رسالة الترحيب
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"• أهلاً بك عزيزي ({user.full_name}) [‏{user.id}] "
        f"في بوت التواصل الخاص بي \n\n"
        f"- أرسل رسالتك الآن ليتم إرسالها إلى مدير البوت وسيقوم بالرد عليك في أقرب وقت ممكن 📢"
    )
    await update.message.reply_text(welcome_text)

# توجيه رسائل المستخدمين إلى المطور
async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.forward(chat_id=OWNER_ID)
        logger.info(f"تم توجيه رسالة من {update.effective_user.id}")
    except Exception as e:
        logger.error(f"خطأ في التوجيه: {e}")

# معالجة ردود المطور وإرسالها للمستخدم الأصلي
async def handle_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    replied = update.message.reply_to_message
    if not replied.forward_origin or replied.forward_origin.type != 'user':
        return

    original_user_id = replied.forward_origin.sender_user.id
    try:
        await update.message.forward(chat_id=original_user_id)
        logger.info(f"تم إرسال رد المطور إلى {original_user_id}")
    except Exception as e:
        logger.error(f"خطأ في إرسال الرد: {e}")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN غير موجود في المتغيرات البيئية")

    app = Application.builder().token(token).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))

    # ردود المطور فقط
    app.add_handler(MessageHandler(filters.Chat(OWNER_ID) & filters.REPLY, handle_owner_reply))

    # رسائل الآخرين (عدا المطور والأوامر)
    app.add_handler(MessageHandler(~filters.Chat(OWNER_ID) & ~filters.COMMAND, forward_to_owner))

    app.run_polling()

if __name__ == "__main__":
    main()
