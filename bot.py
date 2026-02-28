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

# استبدل هذا بالتوكن الخاص ببوتك
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# تأكد من وجود مجلد للتحميلات
DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رسالة الترحيب عند بدء البوت"""
    await update.message.reply_text(
        "مرحباً! أرسل رابط فيديو من انستغرام وسأقوم بتحميله لك بأعلى جودة بدون علامة مائية مع إرسال الوصف."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تعليمات استخدام البوت"""
    await update.message.reply_text(
        "ما عليك سوى إرسال رابط الفيديو من انستغرام (مثل: https://www.instagram.com/reel/XXXXX/ أو https://www.instagram.com/p/XXXXX/)"
    )

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
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج المعلومات أولاً للتحقق والوصف
            info = ydl.extract_info(url, download=False)
            
            # التأكد أن الرابط هو فيديو انستغرام (وليس صورة أو كاروسيل)
            if info.get('extractor', '').lower() != 'instagram':
                raise ValueError("الرابط ليس من انستغرام أو غير مدعوم.")
            
            # إذا كان المحتوى ليس فيديو، نرفض
            if info.get('_type') == 'playlist' or not info.get('entries'):
                # قد يكون منشوراً متعدد الوسائط
                # هنا يمكنك إضافة معالجة للمنشورات المتعددة لكن نكتفي بالفيديو الأول
                # سنحاول تنزيل أول عنصر في القائمة إذا كان موجوداً
                if info.get('entries') and len(info['entries']) > 0:
                    first_entry = info['entries'][0]
                    if first_entry.get('ext') in ['mp4', 'mov']:
                        video_id = first_entry.get('id')
                        description = first_entry.get('description') or info.get('description', 'لا يوجد وصف')
                        # تنزيل الفيديو المحدد
                        ydl.download([url])  # التحميل قد يحمل كل شيء، لكننا حددنا outtmpl باستخدام id
                        # نحتاج لمعرفة الاسم الصحيح
                        filename = f"{DOWNLOADS_DIR}/{video_id}.mp4"
                        if not os.path.exists(filename):
                            # حاول البحث عن أي ملف mp4 في المجلد
                            files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith('.mp4')]
                            if files:
                                filename = os.path.join(DOWNLOADS_DIR, files[-1])
                            else:
                                raise Exception("لم يتم العثور على ملف الفيديو بعد التحميل.")
                        return filename, description
                    else:
                        raise ValueError("الرابط لا يحتوي على فيديو صالح.")
                else:
                    raise ValueError("الرابط لا يحتوي على فيديو.")
            else:
                # فيديو واحد
                # التحقق من أنه فيديو
                if info.get('ext') not in ['mp4', 'mov'] and not any(f.get('vcodec') != 'none' for f in info.get('formats', [])):
                    raise ValueError("الرابط لا يشير إلى فيديو.")
                
                description = info.get('description', 'لا يوجد وصف')
                # تحميل الفيديو
                ydl.download([url])
                # اسم الملف المتوقع
                filename = f"{DOWNLOADS_DIR}/{info['id']}.mp4"
                return filename, description

    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}")
        raise

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرسائل النصية (الروابط)"""
    url = update.message.text.strip()

    # التحقق السريع من أن الرابط يحتوي على انستغرام
    if "instagram.com" not in url:
        await update.message.reply_text("❌ الرجاء إرسال رابط انستغرام صالح (يحتوي على instagram.com).")
        return

    # إشعار المستخدم ببدء المعالجة
    await update.message.reply_text("⏳ جاري تحميل الفيديو، يرجى الانتظار...")

    try:
        # تشغيل التحميل في thread منفصل حتى لا يحجب البوت
        file_path, description = await asyncio.to_thread(download_instagram_video_sync, url)

        # إرسال الفيديو (كملف فيديو)
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(
                video=InputFile(video_file),
                caption="✅ تم التحميل بنجاح!",
                supports_streaming=True
            )

        # إرسال الوصف
        await update.message.reply_text(f"📝 **الوصف:**\n{description}", parse_mode='Markdown')

    except ValueError as ve:
        await update.message.reply_text(f"⚠️ خطأ: {ve}")
    except Exception as e:
        logger.exception("خطأ غير متوقع")
        await update.message.reply_text("❌ حدث خطأ أثناء التحميل. تأكد من الرابط أو حاول لاحقاً.")
    finally:
        # حذف الملف بعد الإرسال لتوفير المساحة
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

def main() -> None:
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # بدء البوت
    print("✅ البوت يعمل...")
    application.run_polling()

if __name__ == "__main__":
    main()
