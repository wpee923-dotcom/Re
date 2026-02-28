import os
import asyncio
import logging
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# إعداد التسجيل لتتبع الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قراءة التوكن من المتغيرات البيئية (ضروري لـ Railway)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("لم يتم العثور على BOT_TOKEN في المتغيرات البيئية!")

# معرف المطور الذي أعطيته لي
DEVELOPER_ID = 5860391324

# تأكد من وجود مجلد للتحميلات
DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رسالة الترحيب عند بدء البوت"""
    user_id = update.effective_user.id
    welcome_message = (
        "مرحباً! أرسل رابط فيديو من انستغرام وسأقوم بتحميله لك بأعلى جودة بدون علامة مائية مع إرسال الوصف.\n\n"
        "أرسل /help للمساعدة"
    )
    
    # إذا كان المستخدم هو المطور، أضف رسالة خاصة
    if user_id == DEVELOPER_ID:
        welcome_message += "\n\n👑 مرحباً بك أيها المطور!"
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تعليمات استخدام البوت"""
    help_text = (
        "📱 **كيفية استخدام البوت:**\n\n"
        "ما عليك سوى إرسال رابط الفيديو من انستغرام:\n"
        "• روابط الريلز: https://www.instagram.com/reel/XXXXX/\n"
        "• روابط المنشورات: https://www.instagram.com/p/XXXXX/\n\n"
        "سأقوم بـ:\n"
        "✅ تحميل الفيديو بأعلى جودة\n"
        "✅ إزالة العلامة المائية\n"
        "✅ إرسال الوصف\n\n"
        "⚠️ ملاحظة: قد لا تعمل مع الحسابات الخاصة."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إحصائيات البوت (للمطور فقط)"""
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو المطور
    if user_id != DEVELOPER_ID:
        await update.message.reply_text("❌ هذه الميزة متاحة فقط للمطور.")
        return
    
    # إحصائيات بسيطة
    stats_text = (
        "📊 **إحصائيات البوت**\n\n"
        f"🔧 حالة البوت: 🟢 يعمل\n"
        f"📂 مجلد التحميلات: موجود\n"
        f"🆔 معرف المطور: {DEVELOPER_ID}\n"
        f"🤖 التوكن: تم تحميله بنجاح"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

def download_instagram_video_sync(url: str):
    """
    دالة متزامنة لتحميل الفيديو باستخدام yt-dlp.
    يتم استدعاؤها داخل thread منفصل حتى لا تحجب الحدث.
    تُرجع (مسار الملف, الوصف) أو ترفع استثناء.
    """
    # خيارات yt-dlp
    ydl_opts = {
        'format': 'best[ext=mp4]',          # أفضل جودة بصيغة mp4
        'outtmpl': f'{DOWNLOADS_DIR}/%(id)s.%(ext)s',  # مسار الحفظ
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        # إضافة User-Agent لتجنب الحظر
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج المعلومات أولاً للتحقق والوصف
            info = ydl.extract_info(url, download=False)
            
            # التأكد أن الرابط هو فيديو انستغرام
            extractor = info.get('extractor', '').lower()
            if 'instagram' not in extractor:
                raise ValueError("الرابط ليس من انستغرام أو غير مدعوم.")
            
            # استخراج الوصف
            description = info.get('description', 'لا يوجد وصف')
            
            # تحميل الفيديو
            ydl.download([url])
            
            # البحث عن الملف المحمل
            video_id = info.get('id')
            if video_id:
                filename = f"{DOWNLOADS_DIR}/{video_id}.mp4"
                # التحقق من وجود الملف
                if os.path.exists(filename):
                    return filename, description
            
            # إذا لم نجد بالمعرف، نبحث عن أي ملف mp4 جديد
            files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith('.mp4')]
            if files:
                # ترتيب حسب وقت التعديل (الأحدث أولاً)
                files.sort(key=lambda x: os.path.getmtime(os.path.join(DOWNLOADS_DIR, x)), reverse=True)
                filename = os.path.join(DOWNLOADS_DIR, files[0])
                return filename, description
            
            raise Exception("لم يتم العثور على ملف الفيديو بعد التحميل.")

    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}")
        raise

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرسائل النصية (الروابط)"""
    url = update.message.text.strip()
    user_id = update.effective_user.id

    # التحقق السريع من أن الرابط يحتوي على انستغرام
    if "instagram.com" not in url:
        await update.message.reply_text("❌ الرجاء إرسال رابط انستغرام صالح (يحتوي على instagram.com).")
        return

    # إشعار المستخدم ببدء المعالجة
    processing_msg = await update.message.reply_text("⏳ جاري تحميل الفيديو، يرجى الانتظار...")

    try:
        # تشغيل التحميل في thread منفصل
        file_path, description = await asyncio.to_thread(download_instagram_video_sync, url)

        # حذف رسالة "جاري التحميل"
        await processing_msg.delete()

        # إرسال الفيديو
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(
                video=InputFile(video_file, filename=os.path.basename(file_path)),
                caption="✅ تم التحميل بنجاح!",
                supports_streaming=True
            )

        # إرسال الوصف (مع تقصيره إذا كان طويلاً جداً)
        if len(description) > 1000:
            description = description[:997] + "..."
        
        await update.message.reply_text(
            f"📝 **الوصف:**\n{description}",
            parse_mode='Markdown'
        )

        # إرسال إشعار للمطور إذا كان المستخدم غير المطور (اختياري)
        if user_id != DEVELOPER_ID:
            try:
                await context.bot.send_message(
                    chat_id=DEVELOPER_ID,
                    text=f"👤 مستخدم جديد استخدم البوت!\n🆔 المعرف: {user_id}\n🔗 الرابط: {url[:50]}..."
                )
            except:
                pass  # تجاهل الأخطاء في إرسال الإشعار

    except ValueError as ve:
        await processing_msg.edit_text(f"⚠️ خطأ: {ve}")
    except Exception as e:
        logger.exception("خطأ غير متوقع")
        await processing_msg.edit_text("❌ حدث خطأ أثناء التحميل. تأكد من الرابط أو حاول لاحقاً.")
    finally:
        # حذف الملف بعد الإرسال لتوفير المساحة
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"تم حذف الملف: {file_path}")
            except:
                pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء العام"""
    logger.error(f"حدث خطأ: {context.error}")

def main() -> None:
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)

    # بدء البوت
    print(f"✅ البوت يعمل... (معرف المطور: {DEVELOPER_ID})")
    application.run_polling()

if __name__ == "__main__":
    main()
