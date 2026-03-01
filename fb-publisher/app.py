"""
Facebook Auto Publisher
يعمل على Render.com مجاناً 24/7
"""

from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import anthropic, requests, json, os, logging
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ── Storage (JSON files, persists on Render disk) ─────────────
BASE = Path("data")
BASE.mkdir(exist_ok=True)

def _load(name, default):
    p = BASE / f"{name}.json"
    try:
        if p.exists(): return json.loads(p.read_text("utf-8"))
    except: pass
    return default

def _save(name, data):
    (BASE / f"{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

get_pages    = lambda: _load("pages", [])
get_logs     = lambda: _load("logs", [])
get_settings = lambda: _load("settings", {"anthropic_key":"","lang":"ar","post_type":"tip"})

save_pages    = lambda v: _save("pages", v)
save_settings = lambda v: _save("settings", v)
save_logs     = lambda v: _save("logs", v[-500:])

# ── Log helper ────────────────────────────────────────────────
def log(level, msg, page="system"):
    entry = {"time": datetime.now().isoformat(), "level": level,
             "page": page, "msg": msg}
    logs = get_logs(); logs.append(entry); save_logs(logs)
    print(f"[{level.upper()}] [{page}] {msg}")

# ── Claude AI ─────────────────────────────────────────────────
TYPES = {
    "tip": "نصيحة مفيدة وعملية",
    "fact": "معلومة أو حقيقة مثيرة للاهتمام",
    "motivational": "كلام تحفيزي ملهم",
    "question": "سؤال تفاعلي يشجع على التعليق",
    "story": "قصة قصيرة ذات معنى"
}

def generate_post(topic, post_type="tip", lang="ar"):
    key = get_settings().get("anthropic_key", "")
    if not key:
        return fallback(topic)

    lang_str = "العربية مع لمسة عامية خفيفة" if lang == "ar" else "fluent English"
    prompt = (f"اكتب {TYPES.get(post_type,'بوست')} لصفحة فيسبوك عن: \"{topic}\"\n"
              f"اللغة: {lang_str}\n"
              f"الطول: 3-5 أسطر فقط\n"
              f"أضف إيموجي وهاشتاقات مناسبة في النهاية\n"
              f"اكتب البوست مباشرة بدون أي مقدمة:")
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-opus-4-6", max_tokens=400,
            messages=[{"role":"user","content":prompt}])
        return msg.content[0].text.strip()
    except Exception as e:
        log("error", f"Claude API: {e}")
        return fallback(topic)

def fallback(topic):
    import random
    posts = [
        f"💡 نصيحة اليوم في مجال {topic}!\n\nكل خطوة صغيرة تقربك من هدفك. ابدأ الآن! 🚀\n\n#{topic.replace(' ','_')} #نصائح #تطوير",
        f"✨ هل تعلم عن {topic}؟\n\nمعلومة قيمة تستحق المشاركة! شاركها مع أصحابك 💬\n\n#{topic.replace(' ','_')} #معلومات_مفيدة",
        f"🌟 اليوم معك عن {topic}!\n\nالنجاح يبدأ بخطوة. ما رأيك؟ 👇\n\n#{topic.replace(' ','_')} #تحفيز #نجاح",
    ]
    return random.choice(posts)

# ── Facebook ──────────────────────────────────────────────────
def publish_fb(page, text):
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{page['page_id']}/feed",
            json={"message": text, "access_token": page["token"]},
            timeout=15)
        d = r.json()
        if "id" in d:
            return True, d["id"]
        return False, d.get("error",{}).get("message","Unknown error")
    except Exception as e:
        return False, str(e)

# ── Core publish job ──────────────────────────────────────────
def publish_job(page_id):
    pages = get_pages()
    page  = next((p for p in pages if p["id"] == page_id), None)
    if not page or page.get("status") != "active":
        return

    log("info", "🔄 جاري توليد البوست...", page["name"])
    text = generate_post(page["topic"], page.get("post_type","tip"), page.get("lang","ar"))

    ok, result = publish_fb(page, text)
    now = datetime.now().isoformat()
    if ok:
        page["total"]     = page.get("total", 0) + 1
        page["today"]     = page.get("today", 0) + 1
        page["last_post"] = now
        page["last_text"] = text[:200]
        log("success", f"✅ نُشر | ID: {result}", page["name"])
    else:
        page["errors"] = page.get("errors", 0) + 1
        log("error", f"❌ {result}", page["name"])

    save_pages(pages)

# ── Scheduler ─────────────────────────────────────────────────
scheduler = BackgroundScheduler(timezone="Africa/Cairo")

def rebuild():
    scheduler.remove_all_jobs()
    for page in get_pages():
        if page.get("status") != "active":
            continue
        for t in page.get("times", []):
            try:
                h, m = t.split(":")
                scheduler.add_job(
                    publish_job, CronTrigger(hour=int(h), minute=int(m)),
                    args=[page["id"]], id=f"{page['id']}_{t}", replace_existing=True)
            except Exception as e:
                log("error", f"جدولة: {e}", page.get("name","?"))

scheduler.start()
rebuild()

# daily reset of "today" counters
def reset_daily():
    pages = get_pages()
    for p in pages: p["today"] = 0
    save_pages(pages)

scheduler.add_job(reset_daily, CronTrigger(hour=0, minute=0), id="daily_reset")

# ── Routes ────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# Pages
@app.route("/api/pages")
def api_pages():
    return jsonify(get_pages())

@app.route("/api/pages", methods=["POST"])
def api_add_page():
    d = request.json
    page = {
        "id": str(int(datetime.now().timestamp()*1000)),
        "name": d["name"], "topic": d["topic"],
        "page_id": d["page_id"], "token": d["token"],
        "times": d.get("times", ["09:00"]),
        "post_type": d.get("post_type","tip"),
        "lang": d.get("lang","ar"),
        "status": "active",
        "total": 0, "today": 0, "errors": 0,
        "last_post": None, "last_text": None
    }
    pages = get_pages(); pages.append(page); save_pages(pages)
    rebuild()
    log("info", "تم إضافة الصفحة", page["name"])
    return jsonify({"ok": True, "page": page})

@app.route("/api/pages/<pid>", methods=["DELETE"])
def api_del_page(pid):
    pages = [p for p in get_pages() if p["id"] != pid]
    save_pages(pages); rebuild()
    return jsonify({"ok": True})

@app.route("/api/pages/<pid>/toggle", methods=["POST"])
def api_toggle(pid):
    pages = get_pages()
    p = next((x for x in pages if x["id"] == pid), None)
    if p:
        p["status"] = "paused" if p["status"]=="active" else "active"
        save_pages(pages); rebuild()
    return jsonify({"ok": True, "status": p["status"] if p else None})

@app.route("/api/pages/<pid>/publish", methods=["POST"])
def api_publish(pid):
    publish_job(pid)
    return jsonify({"ok": True})

# Settings
@app.route("/api/settings")
def api_get_settings():
    s = get_settings()
    return jsonify({**{k:v for k,v in s.items() if k!="anthropic_key"},
                    "has_key": bool(s.get("anthropic_key"))})

@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    d = request.json
    s = get_settings()
    for k, v in d.items():
        if v: s[k] = v
    save_settings(s)
    return jsonify({"ok": True})

# Logs
@app.route("/api/logs")
def api_logs():
    lvl  = request.args.get("level","all")
    logs = get_logs()
    if lvl != "all": logs = [l for l in logs if l["level"]==lvl]
    return jsonify(list(reversed(logs[-200:])))

@app.route("/api/logs", methods=["DELETE"])
def api_clear_logs():
    save_logs([]); return jsonify({"ok": True})

# Stats
@app.route("/api/stats")
def api_stats():
    pages = get_pages()
    return jsonify({
        "pages":  len(pages),
        "active": sum(1 for p in pages if p["status"]=="active"),
        "today":  sum(p.get("today",0) for p in pages),
        "total":  sum(p.get("total",0) for p in pages),
        "errors": sum(p.get("errors",0) for p in pages),
    })

# Generate preview
@app.route("/api/generate", methods=["POST"])
def api_generate():
    d = request.json
    text = generate_post(d.get("topic",""), d.get("post_type","tip"), d.get("lang","ar"))
    return jsonify({"ok": True, "text": text})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 يعمل على http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
