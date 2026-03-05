from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import logging
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = '/data'
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
PAGES_FILE = os.path.join(DATA_DIR, 'pages.json')
LOGS_FILE = os.path.join(DATA_DIR, 'logs.json')
STATS_FILE = os.path.join(DATA_DIR, 'stats.json')

os.makedirs(DATA_DIR, exist_ok=True)
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Riyadh'))

POST_TYPES = {
    'tips': 'نصيحة مفيدة',
    'offer': 'عرض ومنتج مميز',
    'question': 'سؤال تفاعلي',
    'fact': 'معلومة مثيرة',
    'motivation': 'كلمة تحفيزية',
    'quran': 'آية قرآنية وتفسير',
    'quran_tafseer': 'تفسير القرآن بالترتيب',
    'prophet_story': 'قصة نبي',
    'sahabi_story': 'قصة صحابي',
    'islamic_fact': 'معلومة إسلامية',
    'hadith': 'حديث نبوي شريف',
    'video_idea': 'محتوى فيديو'
}

QURAN_FILE = os.path.join(DATA_DIR, 'quran_progress.json')

# ترتيب السور مع عدد الآيات
QURAN_SURAHS = [
    (1,'الفاتحة',7),(2,'البقرة',286),(3,'آل عمران',200),(4,'النساء',176),
    (5,'المائدة',120),(6,'الأنعام',165),(7,'الأعراف',206),(8,'الأنفال',75),
    (9,'التوبة',129),(10,'يونس',109),(11,'هود',123),(12,'يوسف',111),
    (13,'الرعد',43),(14,'إبراهيم',52),(15,'الحجر',99),(16,'النحل',128),
    (17,'الإسراء',111),(18,'الكهف',110),(19,'مريم',98),(20,'طه',135),
    (21,'الأنبياء',112),(22,'الحج',78),(23,'المؤمنون',118),(24,'النور',64),
    (25,'الفرقان',77),(26,'الشعراء',227),(27,'النمل',93),(28,'القصص',88),
    (29,'العنكبوت',69),(30,'الروم',60),(31,'لقمان',34),(32,'السجدة',30),
    (33,'الأحزاب',73),(34,'سبأ',54),(35,'فاطر',45),(36,'يس',83),
    (37,'الصافات',182),(38,'ص',88),(39,'الزمر',75),(40,'غافر',85),
    (41,'فصلت',54),(42,'الشورى',53),(43,'الزخرف',89),(44,'الدخان',59),
    (45,'الجاثية',37),(46,'الأحقاف',35),(47,'محمد',38),(48,'الفتح',29),
    (49,'الحجرات',18),(50,'ق',45),(51,'الذاريات',60),(52,'الطور',49),
    (53,'النجم',62),(54,'القمر',55),(55,'الرحمن',78),(56,'الواقعة',96),
    (57,'الحديد',29),(58,'المجادلة',22),(59,'الحشر',24),(60,'الممتحنة',13),
    (61,'الصف',14),(62,'الجمعة',11),(63,'المنافقون',11),(64,'التغابن',18),
    (65,'الطلاق',12),(66,'التحريم',12),(67,'الملك',30),(68,'القلم',52),
    (69,'الحاقة',52),(70,'المعارج',44),(71,'نوح',28),(72,'الجن',28),
    (73,'المزمل',20),(74,'المدثر',56),(75,'القيامة',40),(76,'الإنسان',31),
    (77,'المرسلات',50),(78,'النبأ',40),(79,'النازعات',46),(80,'عبس',42),
    (81,'التكوير',29),(82,'الانفطار',19),(83,'المطففين',36),(84,'الانشقاق',25),
    (85,'البروج',22),(86,'الطارق',17),(87,'الأعلى',19),(88,'الغاشية',26),
    (89,'الفجر',30),(90,'البلد',20),(91,'الشمس',15),(92,'الليل',21),
    (93,'الضحى',11),(94,'الشرح',8),(95,'التين',8),(96,'العلق',19),
    (97,'القدر',5),(98,'البينة',8),(99,'الزلزلة',8),(100,'العاديات',11),
    (101,'القارعة',11),(102,'التكاثر',8),(103,'العصر',3),(104,'الهمزة',9),
    (105,'الفيل',5),(106,'قريش',4),(107,'الماعون',7),(108,'الكوثر',3),
    (109,'الكافرون',6),(110,'النصر',3),(111,'المسد',5),(112,'الإخلاص',4),
    (113,'الفلق',5),(114,'الناس',6)
]

def get_quran_progress():
    return load_json(QURAN_FILE, {'surah': 1, 'ayah': 1})

def save_quran_progress(surah, ayah):
    save_json(QURAN_FILE, {'surah': surah, 'ayah': ayah})

def get_next_ayah():
    progress = get_quran_progress()
    s = progress['surah']
    a = progress['ayah']
    surah_info = next((x for x in QURAN_SURAHS if x[0]==s), QURAN_SURAHS[0])
    max_ayah = surah_info[2]
    # advance to next
    next_a = a + 1
    next_s = s
    if next_a > max_ayah:
        next_a = 1
        next_s = s + 1
        if next_s > 114:
            next_s = 1
    save_quran_progress(next_s, next_a)
    return s, a, surah_info[1]

DAYS_AR = {
    'mon': 'الإثنين', 'tue': 'الثلاثاء', 'wed': 'الأربعاء',
    'thu': 'الخميس', 'fri': 'الجمعة', 'sat': 'السبت', 'sun': 'الأحد'
}

def load_json(filepath, default):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return default

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_log(page_name, status, message):
    logs = load_json(LOGS_FILE, [])
    logs.insert(0, {'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'page': page_name, 'status': status, 'message': message})
    save_json(LOGS_FILE, logs[:200])

def update_stats(success=True):
    stats = load_json(STATS_FILE, {'total': 0, 'today': 0, 'errors': 0, 'last_reset': ''})
    today = datetime.now().strftime('%Y-%m-%d')
    if stats.get('last_reset') != today:
        stats['today'] = 0
        stats['last_reset'] = today
    stats['total'] += 1
    if success: stats['today'] += 1
    else: stats['errors'] += 1
    save_json(STATS_FILE, stats)

def get_prompt_for_type(post_type, topic):
    if post_type == 'quran_tafseer':
        s, a, sname = get_next_ayah()
        return f'''أنت مفسر قرآن كريم متخصص. اكتب منشور فيسبوك كامل عن الآية رقم {a} من سورة {sname} (السورة رقم {s}).
المنشور يجب أن يحتوي على:
- عنوان: 📖 تفسير سورة {sname} - الآية {a}
- نص الآية الكريمة كاملاً
- تفسير الآية بأسلوب واضح وبسيط
- الفوائد والدروس المستفادة من الآية
- دعاء أو ذكر مناسب في الختام
اكتب كل شيء باللغة العربية فقط بدون أي كلمة أجنبية.'''

    prompts = {
        'tips': f'اكتب نصيحة مفيدة وعملية عن موضوع: {topic}',
        'offer': f'اكتب بوست جذاب لعرض أو منتج متعلق بـ: {topic}',
        'question': f'اكتب سؤالاً تفاعلياً يشجع المتابعين على التعليق عن موضوع: {topic}',
        'fact': f'اكتب معلومة مثيرة ومفيدة عن موضوع: {topic}',
        'motivation': f'اكتب منشوراً تحفيزياً قوياً ومؤثراً عن موضوع: {topic}. استخدم كلمات من القرآن والسنة إذا كان مناسباً.',
        'quran': f'''اختر آية قرآنية عشوائية مناسبة لموضوع: {topic}
اكتب: الآية الكريمة كاملة مع رقمها واسم السورة، ثم تفسيرها بأسلوب بسيط ومؤثر، ثم الدروس المستفادة منها.''',
        'prophet_story': f'''اكتب قصة مؤثرة وملهمة من قصص الأنبياء عليهم السلام (اختر نبياً عشوائياً مناسباً لموضوع: {topic})
اذكر: اسم النبي، موقف من حياته، الدرس المستفاد، وختمها بآية أو دعاء مناسب.''',
        'sahabi_story': f'''اكتب قصة مؤثرة من قصص الصحابة الكرام رضي الله عنهم (اختر صحابياً عشوائياً مناسباً لموضوع: {topic})
اذكر: اسم الصحابي، موقفه البطولي أو الإيماني، الدرس المستفاد.''',
        'islamic_fact': f'''اكتب معلومة إسلامية مثيرة ومفيدة عن موضوع: {topic}
يمكن أن تكون عن: الإعجاز العلمي في القرآن، أسرار العبادات، فضائل الأعمال، أسماء الله الحسنى وفوائدها.''',
        'hadith': f'''اذكر حديثاً نبوياً شريفاً صحيحاً مناسباً لموضوع: {topic}
اكتب: الحديث كاملاً مع راويه، شرحه بأسلوب بسيط، وكيف نطبقه في حياتنا اليومية.''',
        'video_idea': f'اكتب نص بوست جذاب يقدم فيديو عن موضوع: {topic}. اجعله مشوقاً ويحفز المشاهدة.'
    }
    return prompts.get(post_type, f'اكتب بوست مناسب عن: {topic}')

def generate_content(topic, post_type, page_name):
    settings = load_json(SETTINGS_FILE, {})
    api_key = settings.get('groq_api_key', '')
    if not api_key:
        return generate_fallback_content(topic, post_type)
    try:
        angles = [
            'بأسلوب قصصي شيق يجذب القارئ من البداية',
            'بطريقة مباشرة وعملية مع أمثلة من الحياة',
            'بأسلوب يثير الفضول والتساؤل',
            'بطريقة عاطفية ومؤثرة تلامس القلوب',
            'بأسلوب المحاضر الخبير مع معلومات حصرية',
            'بطريقة مرحة وخفيفة مع حكمة عميقة',
            'بأسلوب الحوار والتساؤلات المتتالية',
            'بطريقة تربط الماضي بالحاضر وتستشرف المستقبل'
        ]
        angle = random.choice(angles)
        seed = datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(1000, 9999))
        prompt_text = get_prompt_for_type(post_type, topic)
        system_prompt = """أنت كاتب محتوى عربي متخصص لصفحات فيسبوك.
قواعد صارمة يجب اتباعها دائماً:
1. اكتب باللغة العربية فقط بدون أي كلمة أجنبية إطلاقاً
2. لا تكتب أي كلمة بالإنجليزية أو أي لغة أخرى غير العربية
3. لا تكتب عنواناً أو مقدمة - ابدأ مباشرة بالمحتوى
4. استخدم الإيموجي المناسبة بشكل طبيعي
5. اختم دائماً بدعوة للتفاعل"""

        full_prompt = f"""اكتب منشور فيسبوك عربي متكامل.
{prompt_text}
الأسلوب المطلوب: {angle}
رقم التنويع: {seed}
الطول: بين 150 و 300 كلمة
تذكر: اللغة العربية فقط، ولا تبدأ بعنوان أو مقدمة."""

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 700,
            "temperature": 0.85
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        data = r.json()
        logger.info(f"Groq status: {r.status_code}")
        if 'choices' in data and data['choices']:
            return data['choices'][0]['message']['content']
        elif 'error' in data:
            logger.error(f"Groq API error: {data['error'].get('message','unknown')}")
            return generate_fallback_content(topic, post_type)
        else:
            logger.error(f"Unexpected Groq response: {str(data)[:200]}")
            return generate_fallback_content(topic, post_type)
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return generate_fallback_content(topic, post_type)

def generate_fallback_content(topic, post_type):
    templates = {
        'tips': f'💡 نصيحة اليوم عن {topic}\n\nشاركنا رأيك! 👇',
        'offer': f'🛍️ عرض مميز في {topic}\n\nاضغط لايك! ❤️',
        'question': f'🤔 سؤال اليوم عن {topic}\n\nشاركنا إجابتك! 💬',
        'fact': f'📚 هل تعلم عن {topic}؟\n\nشاركها! 🔄',
        'motivation': f'✨ {topic}\n\nشاركها مع من تحب! ❤️',
        'quran': f'🌟 آية كريمة\n\nاللهم اجعل القرآن ربيع قلوبنا 🤲',
        'prophet_story': f'🕌 من قصص الأنبياء\n\nاللهم صلِّ على نبينا محمد ﷺ',
        'sahabi_story': f'⭐ من قصص الصحابة\n\nرضي الله عنهم أجمعين',
        'islamic_fact': f'📖 معلومة إسلامية عن {topic}\n\nشاركها! 🔄',
        'hadith': f'🌹 حديث شريف\n\nاللهم صلِّ على نبينا ﷺ',
        'video_idea': f'🎥 فيديو جديد عن {topic}\n\nشاركوا! 🔄'
    }
    return templates.get(post_type, f'منشور عن {topic} ✨')

def post_to_facebook(page_id, access_token, content):
    try:
        url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
        r = requests.post(url, data={'message': content, 'access_token': access_token}, timeout=30)
        result = r.json()
        if 'id' in result:
            return True, result['id']
        return False, result.get('error', {}).get('message', 'خطأ غير معروف')
    except Exception as e:
        return False, str(e)

def should_post_today(schedule):
    days = schedule.get('days', ['mon','tue','wed','thu','fri','sat','sun'])
    if not days:
        return True
    day_map = {'mon':0,'tue':1,'wed':2,'thu':3,'fri':4,'sat':5,'sun':6}
    today = datetime.now(pytz.timezone('Asia/Riyadh')).weekday()
    return any(day_map.get(d) == today for d in days)

def publish_scheduled_post(page_id_str, schedule_id):
    pages = load_json(PAGES_FILE, [])
    page = next((p for p in pages if p['id'] == page_id_str), None)
    if not page or not page.get('active', True):
        return
    schedule = next((s for s in page.get('schedules', []) if s['id'] == schedule_id), None)
    if not schedule:
        return
    if not should_post_today(schedule):
        logger.info(f"Skipping {page['name']} - not scheduled today")
        return
    post_type = schedule.get('post_type', 'tips')
    topic = page.get('topic', 'عام')
    content = generate_content(topic, post_type, page['name'])
    success, result = post_to_facebook(page['page_id'], page['access_token'], content)
    type_name = POST_TYPES.get(post_type, post_type)
    message = f"✅ نُشر ({type_name}): {content[:60]}..." if success else f"❌ فشل: {result}"
    add_log(page['name'], 'success' if success else 'error', message)
    update_stats(success)

def setup_scheduler():
    scheduler.remove_all_jobs()
    pages = load_json(PAGES_FILE, [])
    tz = pytz.timezone('Asia/Riyadh')
    for page in pages:
        if not page.get('active', True):
            continue
        for schedule in page.get('schedules', []):
            try:
                h, m = map(int, schedule['time'].split(':'))
                days = schedule.get('days', [])
                day_of_week = ','.join(days) if days else 'mon,tue,wed,thu,fri,sat,sun'
                scheduler.add_job(
                    publish_scheduled_post,
                    CronTrigger(hour=h, minute=m, day_of_week=day_of_week, timezone=tz),
                    args=[page['id'], schedule['id']],
                    id=f"{page['id']}_{schedule['id']}",
                    replace_existing=True
                )
            except Exception as e:
                logger.error(f"Schedule error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    settings = load_json(SETTINGS_FILE, {})
    safe = {k: v for k, v in settings.items() if k != 'groq_api_key'}
    safe['has_api_key'] = bool(settings.get('groq_api_key'))
    return jsonify(safe)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    settings = load_json(SETTINGS_FILE, {})
    settings.update(request.json)
    save_json(SETTINGS_FILE, settings)
    return jsonify({'success': True})

@app.route('/api/pages', methods=['GET'])
def get_pages():
    return jsonify(load_json(PAGES_FILE, []))

@app.route('/api/pages', methods=['POST'])
def add_page():
    data = request.json
    pages = load_json(PAGES_FILE, [])
    if not data.get('schedules'):
        data['schedules'] = [{'id': f"s_{datetime.now().strftime('%f')}", 'time': '09:00', 'post_type': 'tips', 'days': ['mon','tue','wed','thu','fri','sat','sun']}]
    data['id'] = f"page_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    data['active'] = True
    data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pages.append(data)
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True, 'id': data['id']})

@app.route('/api/pages/<page_id>', methods=['PUT'])
def update_page(page_id):
    pages = load_json(PAGES_FILE, [])
    for i, p in enumerate(pages):
        if p['id'] == page_id:
            pages[i].update(request.json)
            break
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/pages/<page_id>', methods=['DELETE'])
def delete_page(page_id):
    pages = [p for p in load_json(PAGES_FILE, []) if p['id'] != page_id]
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/pages/<page_id>/schedules', methods=['POST'])
def add_schedule(page_id):
    data = request.json
    pages = load_json(PAGES_FILE, [])
    for page in pages:
        if page['id'] == page_id:
            if 'schedules' not in page:
                page['schedules'] = []
            data['id'] = f"s_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            if 'days' not in data:
                data['days'] = ['mon','tue','wed','thu','fri','sat','sun']
            page['schedules'].append(data)
            break
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/pages/<page_id>/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(page_id, schedule_id):
    pages = load_json(PAGES_FILE, [])
    for page in pages:
        if page['id'] == page_id:
            page['schedules'] = [s for s in page.get('schedules', []) if s['id'] != schedule_id]
            break
    save_json(PAGES_FILE, pages)
    setup_scheduler()
    return jsonify({'success': True})

@app.route('/api/publish/page/<page_id>', methods=['POST'])
def publish_page(page_id):
    data = request.json or {}
    pages = load_json(PAGES_FILE, [])
    page = next((p for p in pages if p['id'] == page_id), None)
    if not page:
        return jsonify({'success': False, 'error': 'الصفحة غير موجودة'})
    post_type = data.get('post_type', 'tips')
    content = generate_content(page.get('topic', 'عام'), post_type, page['name'])
    success, result = post_to_facebook(page['page_id'], page['access_token'], content)
    type_name = POST_TYPES.get(post_type, post_type)
    add_log(page['name'], 'success' if success else 'error', f"{'✅' if success else '❌'} ({type_name}): {content[:60]}...")
    update_stats(success)
    return jsonify({'success': success, 'result': result, 'content': content})

@app.route('/api/publish/all', methods=['POST'])
def publish_all():
    pages = load_json(PAGES_FILE, [])
    results = []
    for page in pages:
        if not page.get('active', True):
            continue
        post_type = page.get('schedules', [{'post_type': 'tips'}])[0].get('post_type', 'tips')
        content = generate_content(page.get('topic', 'عام'), post_type, page['name'])
        success, result = post_to_facebook(page['page_id'], page['access_token'], content)
        add_log(page['name'], 'success' if success else 'error', f"{'✅' if success else '❌'} {content[:60]}...")
        update_stats(success)
        results.append({'page': page['name'], 'success': success})
    return jsonify({'success': True, 'results': results})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(load_json(LOGS_FILE, []))

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = load_json(STATS_FILE, {'total': 0, 'today': 0, 'errors': 0})
    pages = load_json(PAGES_FILE, [])
    stats['pages'] = len(pages)
    stats['active_pages'] = sum(1 for p in pages if p.get('active', True))
    stats['total_schedules'] = sum(len(p.get('schedules', [])) for p in pages)
    return jsonify(stats)

@app.route('/api/post_types', methods=['GET'])
def get_post_types():
    return jsonify(POST_TYPES)

@app.route('/api/test_token', methods=['POST'])
def test_token():
    data = request.json
    try:
        url = f"https://graph.facebook.com/v19.0/me?access_token={data['access_token']}"
        r = requests.get(url, timeout=10)
        result = r.json()
        if 'id' in result:
            return jsonify({'success': True, 'name': result.get('name', 'الصفحة')})
        return jsonify({'success': False, 'error': result.get('error', {}).get('message', 'خطأ')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if not scheduler.running:
    scheduler.start()
setup_scheduler()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
