FROM python:3.12-slim

# تثبيت FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# تحديد مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات وتثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات البوت
COPY . .

# تشغيل البوت
CMD ["python", "bot.py"]
