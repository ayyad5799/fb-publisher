# 🚀 دليل الرفع على Render — خطوة بخطوة

---

## الخطوة 1: إنشاء حساب GitHub
1. اذهب إلى **github.com**
2. اضغط **Sign up** وأنشئ حساباً مجانياً

---

## الخطوة 2: رفع الكود على GitHub
1. اضغط على **+** (أعلى يمين) ← **New repository**
2. اسم الـ repository: `fb-publisher`
3. اختر **Private** (مهم عشان التوكنات سرية)
4. اضغط **Create repository**
5. اضغط **uploading an existing file**
6. ارفع جميع الملفات الموجودة في المجلد:
   - `app.py`
   - `requirements.txt`
   - `render.yaml`
   - `.gitignore`
   - مجلد `templates` (فيه `index.html`)
7. اضغط **Commit changes**

---

## الخطوة 3: إنشاء حساب Render
1. اذهب إلى **render.com**
2. اضغط **Get Started for Free**
3. سجل بحساب GitHub الجديد (أسرع طريقة)

---

## الخطوة 4: ربط GitHub بـ Render ونشر التطبيق
1. في Render، اضغط **+ New** ← **Web Service**
2. اختر **Connect a repository**
3. اختر `fb-publisher` من القائمة
4. الإعدادات (تُملأ تلقائياً من render.yaml):
   - **Name:** fb-publisher
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
5. اضغط **Create Web Service**
6. انتظر 2-3 دقائق للـ Deploy ✅

---

## الخطوة 5: الوصول للموقع
- بعد انتهاء الـ Deploy، ستحصل على رابط مثل:
  `https://fb-publisher-xxxx.onrender.com`
- **افتح الرابط ده على هاتفك** 📱
- احفظه على الشاشة الرئيسية كتطبيق!

---

## الخطوة 6: الإعداد الأول
1. اذهب إلى **⚙️ الإعدادات**
2. أدخل مفتاح Claude من `console.anthropic.com`
3. اذهب إلى **📄 الصفحات** ← **إضافة**
4. أدخل بيانات كل صفحة فيسبوك

---

## ⚠️ تنبيهات مهمة

### الخطة المجانية على Render:
- ✅ مجانية تماماً
- ✅ تشتغل 24/7 لو فيه طلبات
- ⚠️ بينام بعد 15 دقيقة بدون استخدام (Free plan)
- 💡 الحل: استخدم **UptimeRobot** (مجاني) يعمل ping للموقع كل 10 دقائق
  - اذهب إلى uptimerobot.com
  - أضف monitor جديد من نوع HTTP
  - أدخل رابط موقعك
  - فترة الفحص: 5 دقائق

### للخطة الأفضل (مدفوعة $7/شهر):
- لا ينام أبداً
- أسرع في الاستجابة

---

## ✅ الملخص
```
GitHub (كود) ← Render (سيرفر) ← هاتفك (إدارة)
     ↑                ↓
   مرة واحدة     يشتغل 24/7
```
