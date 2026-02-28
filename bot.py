import os
import asyncio
import logging
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN غير موجود!")

DEVELOPER_ID = 5860391324
DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = "🎥 أرسل رابط فيديو انستغرام وسأحضره لك."
    await update.message.reply_text(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("أرسل رابط انستغرام مثل:\nhttps://www.instagram.com/reel/XXXXX/")

def download_video_sync(url: str):
    """تحميل الفيديو بدون الحاجة لـ FFmpeg"""
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # يأخذ أفضل تنسيق mp4 (مع صوت غالباً)
        'outtmpl': f'{DOWNLOADS_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id')
        filename = f"{DOWNLOADS_DIR}/{video_id}.mp4"
        if os.path.exists(filename):
            return filename, info.get('description', 'لا يوجد وصف')
        # لو ما لقينا بالمعرف، نبحث عن أحدث ملف
        files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith('.mp4')]
        if files:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(DOWNLOADS_DIR, x)), reverse=True)
            return os.path.join(DOWNLOADS_DIR, files[0]), info.get('description', '')
        raise Exception("ما لقينا الفيديو!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    if "instagram.com" not in url:
        await update.message.reply_text("❌ هذا مو رابط انستغرام")
        return

    msg = await update.message.reply_text("⏳ جاري التحميل...")
    try:
        file_path, desc = await asyncio.to_thread(download_video_sync, url)
        await msg.delete()
        with open(file_path, 'rb') as f:
            await update.message.reply_video(video=InputFile(f), caption="✅ تم")
        if desc:
            await update.message.reply_text(f"📝 {desc[:1000]}")
    except Exception as e:
        await msg.edit_text(f"❌ فشل: {str(e)[:50]}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ البوت شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
