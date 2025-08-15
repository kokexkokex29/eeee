# 🚀 Deploy Football Bot to Render

## خطوات النشر على Render (Arabic Instructions)

### الخطوة 1: تحضير الكود
1. ارفع كودك إلى GitHub repository
2. تأكد من وجود الملفات التالية:
   - `main.py` (الملف الرئيسي)
   - `bot.py` (كود البوت)
   - `render.yaml` (إعدادات Render)

### الخطوة 2: إعداد Render
1. اذهب إلى [render.com](https://render.com) وسجل حساب جديد
2. اضغط على "New +" واختر "Web Service"
3. اربط حسابك بـ GitHub واختر المستودع

### الخطوة 3: إعدادات النشر
```yaml
# استخدم هذه الإعدادات:
Name: football-bot
Environment: Python 3
Build Command: pip install discord.py flask flask-sqlalchemy gunicorn pillow aiosqlite
Start Command: python main.py
```

### الخطوة 4: متغيرات البيئة
أضف المتغيرات التالية في تبويب Environment:
```
DISCORD_TOKEN = your_discord_bot_token_here
SESSION_SECRET = any_random_secret_string
```

### الخطوة 5: النشر
1. اضغط على "Create Web Service"
2. انتظر حتى يكتمل النشر (5-10 دقائق)
3. ستحصل على رابط `.onrender.com`

## 🔧 إعدادات إضافية

### إبقاء البوت نشط (Keep Alive)
البوت يحتوي على نظام Keep-Alive تلقائي يمنعه من النوم.

### قاعدة البيانات
- البوت يستخدم SQLite تلقائياً
- البيانات تُحفظ في ملف `bot.db`
- في Render، البيانات محفوظة على القرص المؤقت

### الصلاحيات المطلوبة
تأكد أن البوت لديه هذه الصلاحيات في Discord:
- Manage Roles ✅
- Send Messages ✅  
- Use Slash Commands ✅

## 🚨 استكشاف الأخطاء

### البوت لا يعمل؟
1. تحقق من صحة الـ Discord Token
2. تأكد أن البوت مُضاف للسيرفر
3. تحقق من الصلاحيات
4. راجع السجلات في Render Dashboard

### الأدوار لا تُنشأ؟
- تأكد أن البوت له صلاحية "Manage Roles"
- تأكد أن دور البوت أعلى من الأدوار التي يحاول إنشاؤها

### الأوامر لا تظهر؟
- انتظر 5 دقائق بعد إضافة البوت
- استخدم `/` في Discord لرؤية الأوامر