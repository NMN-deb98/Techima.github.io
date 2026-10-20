from __future__ import annotations
import datetime as dt, hmac, json, os, re, secrets, base64, html
from functools import wraps
from urllib.parse import quote
import requests
from flask import Flask, abort, flash, redirect, render_template_string, request, session, url_for, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from markdown import markdown as render_markdown
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///techima_cms.sqlite3").replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
db = SQLAlchemy(app)
OWNER_USERNAME = os.environ.get("CMS_USERNAME", "")
OWNER_PASSWORD_HASH = os.environ.get("CMS_PASSWORD_HASH", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "NMN-deb98/Techima.github.io")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
BASE_URL = "https://nmn-deb98.github.io/Techima.github.io"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(180), nullable=False, default="")
    description = db.Column(db.String(300), nullable=False, default="")
    body = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(20), nullable=False, default="draft")
    tags = db.Column(db.Text, nullable=False, default="[]")
    image = db.Column(db.String(1000), nullable=False, default="")
    image_alt = db.Column(db.String(180), nullable=False, default="")
    updated_at = db.Column(db.DateTime, nullable=False, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    published_at = db.Column(db.Date, nullable=True)

with app.app_context():
    db.create_all()

SHELL = r"""
<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} | پنل تکیما</title><style>
:root{color-scheme:light;--navy:#0b1d3a;--teal:#14b8a6;--ink:#182338;--muted:#6b7890;--line:#e4e9f1;--bg:#f4f7fb;--white:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Vazirmatn,Tahoma,Arial,sans-serif;line-height:1.8}a{color:inherit;text-decoration:none}button,input,textarea,select{font:inherit}button,.btn{cursor:pointer;border:0;border-radius:11px;padding:10px 16px;background:var(--navy);color:white;display:inline-block}.btn.secondary{background:#e9eef5;color:var(--navy)}.btn.teal{background:var(--teal);color:#062c30}.layout{display:grid;grid-template-columns:245px minmax(0,1fr);min-height:100vh}.side{background:var(--navy);color:white;padding:26px 18px}.brand{font-size:22px;font-weight:800;padding:5px 12px 25px}.brand small{display:block;color:#9db0ce;font-size:11px;letter-spacing:3px}.nav a{display:block;padding:11px 13px;border-radius:10px;color:#dbe5f5;margin:4px 0}.nav a:hover,.nav a.active{background:#203657;color:white}.side-note{font-size:12px;color:#a8bad5;margin:30px 12px}.main{min-width:0;padding:28px clamp(16px,4vw,46px)}.top{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:24px}.top h1{margin:0;font-size:25px}.muted{color:var(--muted);font-size:13px}.card{background:white;border:1px solid var(--line);border-radius:17px;padding:22px;margin-bottom:18px;box-shadow:0 5px 20px #152b4810}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.stat strong{display:block;font-size:28px;color:var(--navy)}.stat span{color:var(--muted);font-size:13px}.row{display:flex;align-items:center;justify-content:space-between;gap:14px}.actions{display:flex;gap:8px;flex-wrap:wrap}.field{margin-bottom:17px}.field label{display:block;font-weight:700;margin-bottom:6px}.field input,.field textarea,.field select{width:100%;border:1px solid #d9e1ed;border-radius:10px;padding:11px 12px;background:white;color:var(--ink)}.field textarea{min-height:240px;resize:vertical}.field small{color:var(--muted)}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;min-width:650px}th,td{text-align:right;padding:13px 10px;border-bottom:1px solid var(--line)}th{font-size:13px;color:var(--muted);font-weight:700}.pill{font-size:12px;border-radius:999px;padding:4px 9px;background:#eef2f7}.pill.published{background:#d9f7ef;color:#087f68}.pill.draft{background:#fff0cf;color:#8a5700}.flash{padding:11px 14px;border-radius:10px;background:#e5f7ef;margin-bottom:14px}.flash.error{background:#fff0f0;color:#9c2525}.login{max-width:460px;margin:8vh auto;padding:30px}.login h1{margin-top:0}.preview{background:#fff;border:1px dashed #cbd5e1;border-radius:12px;padding:15px;overflow-wrap:anywhere}.danger{color:#b42318}.empty{text-align:center;padding:36px;color:var(--muted)}
@media(max-width:800px){.layout{grid-template-columns:1fr}.side{padding:12px 15px}.brand{padding:3px 8px 8px}.nav{display:flex;overflow:auto;gap:5px}.nav a{white-space:nowrap;padding:7px 10px}.side-note{display:none}.main{padding:18px 13px}.grid{grid-template-columns:1fr}.two{grid-template-columns:1fr}.top{align-items:flex-start;flex-direction:column}.card{padding:16px}}
</style></head><body>
{% if logged_in %}
<div class="layout"><aside class="side"><a class="brand" href="{{ url_for('dashboard') }}">تکیما <small>TECHIMA CMS</small></a><nav class="nav">
<a class="{{ 'active' if active=='dashboard' else '' }}" href="{{ url_for('dashboard') }}">نمای کلی</a><a class="{{ 'active' if active=='articles' else '' }}" href="{{ url_for('articles') }}">مقاله‌ها</a><a class="{{ 'active' if active=='new' else '' }}" href="{{ url_for('edit_article') }}">نوشتن مقاله</a><a href="{{ url_for('site_status') }}">وضعیت اتصال سایت</a><a href="https://github.com/NMN-deb98/Techima.github.io/pull/2" target="_blank" rel="noopener">زیرساخت انتشار ↗</a></nav><div class="side-note">پنل خصوصی مدیریت محتوای تکیما<br>انتشار فقط با اقدام مدیر</div></aside>
<main class="main"><header class="top"><div><h1>{{ title }}</h1><div class="muted">مدیریت محتوای سایت شخصی تکیما</div></div><div class="actions"><a class="btn secondary" href="{{ site_url }}" target="_blank" rel="noopener">مشاهده سایت ↗</a><form method="post" action="{{ url_for('logout') }}"><input type="hidden" name="csrf" value="{{ csrf }}"><button class="btn secondary">خروج</button></form></div></header>
{% for category,message in get_flashed_messages(with_categories=true) %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{{ content|safe }}</main></div>
{% else %}<main class="card login"><div class="brand" style="color:#0b1d3a;padding:0 0 12px">تکیما <small style="color:#6b7890">TECHIMA CMS</small></div><h1>{{ title }}</h1><p class="muted">ورود فقط برای مدیر مجاز است.</p>{% for category,message in get_flashed_messages(with_categories=true) %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{{ content|safe }}</main>{% endif %}
</body></html>
"""

def csrf_token():
    if "csrf" not in session: session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]

def check_csrf():
    expected, supplied = session.get("csrf", ""), request.form.get("csrf", "")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied): abort(400, "Invalid CSRF token")

@app.before_request
def require_configuration():
    if request.endpoint in {"login", "static", "health", "configuration_error"}: return
    if not app.config["SECRET_KEY"] or not OWNER_USERNAME or not OWNER_PASSWORD_HASH: return redirect(url_for("configuration_error"))

def owner_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("owner_authenticated"): return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def shell(title, content, active="dashboard", logged_in=True):
    return render_template_string(SHELL, title=title, content=content, active=active, logged_in=logged_in,
        csrf=csrf_token(), site_url=BASE_URL + "/", get_flashed_messages=get_flashed_messages)

@app.route("/health")
def health(): return {"status":"ok","service":"techima-cms"}, 200

@app.route("/configuration")
def configuration_error():
    content = '<div class="flash error">پنل هنوز پیکربندی نشده است. متغیرهای FLASK_SECRET_KEY، CMS_USERNAME و CMS_PASSWORD_HASH را در محیط میزبانی تنظیم کن. توکن GitHub فقط باید به‌صورت Secret سمت سرور ذخیره شود.</div>'
    return render_template_string(SHELL, title="راه‌اندازی لازم است", content=content, logged_in=False)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        check_csrf()
        username, password = request.form.get("username",""), request.form.get("password","")
        if OWNER_USERNAME and OWNER_PASSWORD_HASH and hmac.compare_digest(username, OWNER_USERNAME) and check_password_hash(OWNER_PASSWORD_HASH, password):
            session.clear(); session["owner_authenticated"] = True; session["csrf"] = secrets.token_urlsafe(32)
            return redirect(url_for("dashboard"))
        flash("نام کاربری یا رمز عبور اشتباه است.", "error")
    content = f'<form method="post"><input type="hidden" name="csrf" value="{esc(csrf_token())}"><div class="field"><label>نام کاربری</label><input name="username" autocomplete="username" required maxlength="80"></div><div class="field"><label>رمز عبور</label><input type="password" name="password" autocomplete="current-password" required></div><button class="btn teal" style="width:100%">ورود امن</button></form>'
    return shell("ورود مدیر", content, logged_in=False)

@app.route("/logout", methods=["POST"])
@owner_required
def logout():
    check_csrf(); session.clear(); return redirect(url_for("login"))

def esc(value): return html.escape(str(value or ""), quote=True)

@app.route("/")
@owner_required
def dashboard():
    total = Article.query.count(); published = Article.query.filter_by(status="published").count(); drafts = total - published
    recent = Article.query.order_by(Article.updated_at.desc()).limit(6).all()
    rows = "".join(f'<tr><td><strong>{esc(a.title or "بدون عنوان")}</strong><div class="muted">/{esc(a.slug)}/</div></td><td><span class="pill {a.status}">{"منتشرشده" if a.status=="published" else "پیش‌نویس"}</span></td><td>{a.updated_at.strftime("%Y-%m-%d")}</td><td><a class="btn secondary" href="{url_for("edit_article", article_id=a.id)}">ویرایش</a></td></tr>' for a in recent)
    if not rows:
        rows = '<tr><td colspan="4" class="empty">هنوز مقاله‌ای ایجاد نشده است.</td></tr>'
    content = f'<div class="grid"><section class="card stat"><span>همه مقاله‌ها</span><strong>{total}</strong></section><section class="card stat"><span>منتشرشده</span><strong>{published}</strong></section><section class="card stat"><span>پیش‌نویس‌ها</span><strong>{drafts}</strong></section></div><section class="card"><div class="row"><h2>آخرین مقاله‌ها</h2><a class="btn teal" href="{url_for("edit_article")}">+ مقاله جدید</a></div><div class="table-wrap"><table><thead><tr><th>عنوان</th><th>وضعیت</th><th>آخرین ویرایش</th><th>عملیات</th></tr></thead><tbody>{rows}</tbody></table></div></section><section class="card"><h2>وضعیت انتشار</h2><p>مقاله‌ها ابتدا در پایگاه داده پنل ذخیره می‌شوند. برای انتشار عمومی، «انتشار در سایت» را انتخاب کن تا محتوای منتشرشده به GitHub ارسال شود.</p><a class="btn secondary" href="{url_for("site_status")}">بررسی اتصال</a></section>'
    return shell("نمای کلی", content)

@app.route("/articles")
@owner_required
def articles():
    items = Article.query.order_by(Article.updated_at.desc()).all()
    rowlist=[]
    for a in items:
        extra = f'<a class="btn secondary" target="_blank" rel="noopener" href="{BASE_URL}/articles/{quote(a.slug)}/">مشاهده</a>' if a.status=="published" else ""
        rowlist.append(f'<tr><td><strong>{esc(a.title or "بدون عنوان")}</strong><div class="muted">/{esc(a.slug)}/</div></td><td><span class="pill {a.status}">{"منتشرشده" if a.status=="published" else "پیش‌نویس"}</span></td><td>{a.updated_at.strftime("%Y-%m-%d %H:%M")}</td><td><div class="actions"><a class="btn secondary" href="{url_for("edit_article",article_id=a.id)}">ویرایش</a>{extra}<form method="post" action="{url_for("delete_article",article_id=a.id)}" onsubmit="return confirm(&quot;مقاله حذف شود؟&quot;)"><input type="hidden" name="csrf" value="{esc(csrf_token())}"><button class="btn secondary">حذف</button></form></div></td></tr>')
    content = '<section class="card"><div class="row"><p class="muted">محتواهای ذخیره‌شده در CMS</p><a class="btn teal" href="'+url_for("edit_article")+'">+ مقاله جدید</a></div><div class="table-wrap"><table><thead><tr><th>عنوان</th><th>وضعیت</th><th>آخرین ویرایش</th><th>عملیات</th></tr></thead><tbody>'+("".join(rowlist) or '<tr><td colspan="4" class="empty">مقاله‌ای وجود ندارد.</td></tr>')+'</tbody></table></div></section>'
    return shell("مدیریت مقاله‌ها", content, "articles")

def github_request(path, method="GET", payload=None):
    if not GITHUB_TOKEN: raise RuntimeError("توکن GitHub در محیط میزبانی تنظیم نشده است.")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization":f"Bearer {GITHUB_TOKEN}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    response = requests.request(method,url,headers=headers,json=payload,timeout=20)
    if response.status_code not in (200,201):
        raise RuntimeError(f"GitHub درخواست را نپذیرفت (HTTP {response.status_code}). مجوز Contents و شاخه را بررسی کن.")
    return response.json()

def sync_article(article):
    data = {"slug":article.slug,"title":article.title,"description":article.description,"status":article.status,
        "datePublished":(article.published_at or dt.date.today()).isoformat(),"dateModified":dt.date.today().isoformat(),
        "tags":json.loads(article.tags or "[]"),"body":article.body}
    if article.image.startswith("https://"): data.update({"image":article.image,"imageAlt":article.image_alt})
    path=f"content/articles/{article.slug}.json"; sha=None
    try: sha=github_request(path).get("sha")
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc): raise
    payload={"message":f"CMS article {article.status}: {article.slug}","content":base64.b64encode(json.dumps(data,ensure_ascii=False,indent=2).encode()).decode(),"branch":GITHUB_BRANCH}
    if sha: payload["sha"]=sha
    github_request(path,"PUT",payload)

@app.route("/articles/new", methods=["GET","POST"])
@app.route("/articles/<int:article_id>/edit", methods=["GET","POST"])
@owner_required
def edit_article(article_id=None):
    article=db.session.get(Article,article_id) if article_id else Article()
    if article_id and article is None: abort(404)
    if request.method=="POST":
        check_csrf()
        title=request.form.get("title","").strip()[:180]; slug=request.form.get("slug","").strip().lower()[:100]
        description=request.form.get("description","").strip()[:300]; body=request.form.get("body","")
        tags=[x.strip()[:60] for x in request.form.get("tags","").split(",") if x.strip()][:12]
        image=request.form.get("image","").strip()[:1000]; image_alt=request.form.get("image_alt","").strip()[:180]
        status=request.form.get("status","draft")
        if article_id and article.status == "published" and status == "draft":
            flash("تبدیل مقالهٔ منتشرشده به پیش‌نویس هنوز پشتیبانی نمی‌شود؛ برای جلوگیری از صفحهٔ زندهٔ ناخواسته وضعیت را تغییر ندادیم.", "error")
        elif not SLUG_RE.fullmatch(slug): flash("نامک باید انگلیسی و شامل حروف کوچک، عدد و خط تیره باشد.","error")
        elif not title or not description or not body.strip(): flash("عنوان، توضیح سئو و متن مقاله ضروری هستند.","error")
        elif Article.query.filter(Article.slug==slug,Article.id!=article.id).first(): flash("این نامک قبلاً استفاده شده است.","error")
        elif image and not image.startswith("https://"): flash("آدرس تصویر باید با https:// شروع شود.","error")
        elif status not in {"draft","published"}: flash("وضعیت مقاله معتبر نیست.","error")
        else:
            article.slug,article.title,article.description,article.body=slug,title,description,body
            article.tags,article.image,article.image_alt=json.dumps(tags,ensure_ascii=False),image,image_alt
            article.status=status
            if status=="published" and not article.published_at: article.published_at=dt.date.today()
            db.session.add(article); db.session.commit()
            if status=="published":
                try: sync_article(article); flash("مقاله در GitHub ثبت شد؛ پس از اجرای GitHub Actions صفحه عمومی به‌روز می‌شود.")
                except Exception as exc:
                    app.logger.exception("Publishing failed"); flash(f"مقاله ذخیره شد، اما انتشار GitHub ناموفق بود: {exc}","error")
            else: flash("پیش‌نویس در پایگاه داده پنل ذخیره شد و به سایت عمومی ارسال نشد.")
            return redirect(url_for("articles"))
    tags_value=", ".join(json.loads(article.tags or "[]"))
    statuses=f'<option value="draft" {"selected" if article.status=="draft" else ""}>پیش‌نویس</option><option value="published" {"selected" if article.status=="published" else ""}>منتشرشده</option>'
    content=f'<form class="card" method="post"><input type="hidden" name="csrf" value="{esc(csrf_token())}"><div class="field"><label>عنوان مقاله</label><input name="title" value="{esc(article.title)}" maxlength="180" required></div><div class="two"><div class="field"><label>نامک (Slug)</label><input name="slug" value="{esc(article.slug)}" pattern="[a-z0-9]+(-[a-z0-9]+)*" maxlength="100" required><small>مثال: python-basics</small></div><div class="field"><label>وضعیت</label><select name="status">{statuses}</select></div></div><div class="field"><label>توضیحات متا</label><textarea name="description" style="min-height:90px" maxlength="300" required>{esc(article.description)}</textarea></div><div class="field"><label>متن مقاله (Markdown)</label><textarea name="body" required>{esc(article.body)}</textarea><small>برای تیترها از # و ##، برای فهرست از - و برای لینک از [متن](https://example.com) استفاده کن.</small></div><div class="two"><div class="field"><label>برچسب‌ها</label><input name="tags" value="{esc(tags_value)}" placeholder="آموزش، پایتون"></div><div class="field"><label>آدرس تصویر شاخص (HTTPS)</label><input name="image" value="{esc(article.image)}" placeholder="https://..."></div></div><div class="field"><label>متن جایگزین تصویر</label><input name="image_alt" value="{esc(article.image_alt)}" maxlength="180"></div><div class="actions"><button class="btn teal">ذخیره</button><a class="btn secondary" href="{url_for("articles")}">انصراف</a></div></form>'
    return shell("ویرایش مقاله" if article_id else "نوشتن مقاله",content,"articles" if article_id else "new")

@app.route("/articles/<int:article_id>/delete",methods=["POST"])
@owner_required
def delete_article(article_id):
    check_csrf(); article=db.session.get(Article,article_id)
    if not article: abort(404)
    if article.status=="published": flash("برای جلوگیری از حذف ناخواسته صفحه زنده، حذف مقاله منتشرشده فعلاً مسدود است.","error")
    else: db.session.delete(article); db.session.commit(); flash("پیش‌نویس حذف شد.")
    return redirect(url_for("articles"))

@app.route("/site-status")
@owner_required
def site_status():
    content=f'<section class="card"><h2>اتصال GitHub</h2><p>مخزن مقصد: <code>{esc(GITHUB_REPO)}</code></p><p>شاخه انتشار: <code>{esc(GITHUB_BRANCH)}</code></p><p>توکن سمت سرور: <span class="pill {"published" if GITHUB_TOKEN else "draft"}">{"تنظیم شده" if GITHUB_TOKEN else "تنظیم نشده"}</span></p><p>آدرس سایت: <a href="{BASE_URL}/" target="_blank" rel="noopener">{BASE_URL}/</a></p><p class="muted">توکن Fine-grained باید فقط مجوز Contents: Read and write روی مخزن سایت داشته باشد.</p></section><section class="card"><h2>امکانات باقی‌مانده</h2><ul><li>مدیریت دیدگاه‌ها و پاسخ‌ها</li><li>کتابخانه رسانه و آپلود امن تصویر</li><li>نسخه‌بندی مقاله و زمان‌بندی انتشار</li><li>محدودیت نرخ ورود، پایش و پشتیبان‌گیری</li></ul></section>'
    return shell("وضعیت اتصال سایت",content)

if __name__=="__main__":
    if not app.config["SECRET_KEY"]: raise SystemExit("Set FLASK_SECRET_KEY before starting the CMS.")
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","8000")),debug=False)
