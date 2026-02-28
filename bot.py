import os
import asyncio
import logging
import subprocess
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN غير موجود في المتغيرات البيئية!")

DEVELOPER_ID = 5860391324
DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# التحقق من وجود FFmpeg في النظام
def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        logger.info("FFmpeg مثبت ✅")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg غير مثبت ❌")
        return False

# تحديث yt-dlp إلى آخر إصدار
def update_ytdlp():
    try:
        subprocess.run(["pip", "install", "--upgrade", "yt-dlp"], check=True)
        logger.info("yt-dlp تم تحديثه ✅")
    except Exception as e:
        logger.warning(f"فشل تحديث yt-dlp: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    msg = (
        "🎥 **بوت تحميل فيديوهات انستغرام**\n"
        "أرسل رابط الفيديو وسأحضره لك مع الصوت.\n"
        "/help للمساعدة"
    )
    if user_id == DEVELOPER_ID:
        ffmpeg_status = "✅ موجود" if check_ffmpeg() else "❌ غير موجود"
        msg += f"\n\n🔧 FFmpeg: {ffmpeg_status}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "أرسل رابط انستغرام مثل:\n"
        "`https://www.instagram.com/reel/XXXXX/`\n"
        "`https://www.instagram.com/p/XXXXX/`",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("❌ غير مصرح")
        return
    ffmpeg = "✅ موجود" if check_ffmpeg() else "❌ غير موجود"
    await update.message.reply_text(f"📊 **الحالة**\nFFmpeg: {ffmpeg}\nالمطور: `{DEVELOPER_ID}`", parse_mode='Markdown')

def download_instagram_video_sync(url: str):
    """
    تحميل الفيديو مع الصوت، وإرجاع مسار الملف والوصف.
    في حالة الفشل، يتم رفع استثناء مع تفاصيل واضحة.
    """
    # تأكد من وجود FFmpeg
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg غير مثبت على الخادم. يرجى تثبيته عبر apt.txt")

    # خيارات yt-dlp محسنة
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # فيديو + صوت
        'merge_output_format': 'mp4',
        'outtmpl': f'{DOWNLOADS_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        # إذا كان هناك ملف كوكيز (يمكن وضعه في المستودع)
        # 'cookiefile': 'cookies.txt',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج المعلومات أولاً للتحقق
            info = ydl.extract_info(url, download=False)
            extractor = info.get('extractor', '').lower()
            if 'instagram' not in extractor:
                raise ValueError("الرابط ليس من انستغرام")

            # تحميل الفيديو
            ydl.download([url])

            # البحث عن الملف الناتج
            video_id = info.get('id')
            if video_id:
                filename = f"{DOWNLOADS_DIR}/{video_id}.mp4"
                if os.path.exists(filename):
                    return filename, info.get('description', 'لا يوجد وصف')

            # البحث عن أي ملف mp4 جديد
            files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith('.mp4')]
            if files:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(DOWNLOADS_DIR, x)), reverse=True)
                return os.path.join(DOWNLOADS_DIR, files[0]), info.get('description', 'لا يوجد وصف')

            raise FileNotFoundError("لم يتم العثور على ملف الفيديو بعد التحميل")

    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}")
        raise  # نرفع الاستثناء ليلتقطه المتصل

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    user_id = update.effective_user.id

    if "instagram.com" not in url:
        await update.message.reply_text("❌ هذا ليس رابط انستغرام")
        return

    # إعلام المستخدم بالبدء
    status_msg = await update.message.reply_text("⏳ جاري التحميل...")

    try:
        # تحديث yt-dlp (مرة واحدة عند بدء التشغيل، لكن هنا للتأكد)
        # يمكن وضعه في بداية main بدلاً من ذلك
        # update_ytdlp()  # قد يستغرق وقتاً

        # تشغيل التحميل في thread
        file_path, description = await asyncio.to_thread(download_instagram_video_sync, url)

        await status_msg.delete()

        # إرسال الفيديو
        with open(file_path, 'rb') as f:
            await update.message.reply_video(
                video=InputFile(f, filename=os.path.basename(file_path)),
                caption="✅ تم التحميل!",
                supports_streaming=True
            )

        # إرسال الوصف
        desc_short = description if len(description) <= 1000 else description[:997] + "..."
        await update.message.reply_text(f"📝 **الوصف:**\n{desc_short}", parse_mode='Markdown')

        # إبلاغ المطور باستخدام البوت
        if user_id != DEVELOPER_ID:
            try:
                await context.bot.send_message(
                    chat_id=DEVELOPER_ID,
                    text=f"👤 مستخدم: `{user_id}`\nرابط: {url[:50]}..."
                )
            except:
                pass

    except Exception as e:
        # إرسال تفاصيل الخطأ للمطور فقط
        error_details = f"❌ خطأ: {type(e).__name__}: {e}"
        logger.exception("خطأ في معالجة الرابط")
        if user_id == DEVELOPER_ID:
            await status_msg.edit_text(error_details)
        else:
            await status_msg.edit_text("❌ فشل التحميل. حاول مرة أخرى لاحقاً.")

        # إرسال التفاصيل للمطور أيضاً
        try:
            await context.bot.send_message(
                chat_id=DEVELOPER_ID,
                text=f"⚠️ خطأ من مستخدم {user_id}:\n{error_details}"
            )
        except:
            pass
    finally:
        # حذف الملف المؤقت
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

def main():
    # تحقق من FFmpeg عند بدء التشغيل
    ffmpeg_ok = check_ffmpeg()
    if not ffmpeg_ok:
        logger.error("FFmpeg غير مثبت! البوت لن يعمل بشكل صحيح.")

    # تحديث yt-dlp عند بدء التشغيل (اختياري)
    try:
        update_ytdlp()
    except Exception as e:
        logger.warning(f"فشل تحديث yt-dlp: {e}")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(lambda u, c: logger.error(f"Unhandled error: {c.error}"))

    logger.info("✅ البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
