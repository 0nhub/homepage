#!/usr/bin/env python3
"""Build dependency-free HTML pages from one layout and shared project data."""
import hashlib
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import quote, urlparse

_SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = _SCRIPT_DIR.parents[1]
SOURCE = ROOT / 'src'
SITE = json.loads((SOURCE / 'data/site.json').read_text())
PROJECTS = json.loads((SOURCE / 'data/projects.json').read_text())
LAYOUT = Template((SOURCE / 'templates/layout.html').read_text())
I18N = json.loads((SOURCE / 'data/i18n.json').read_text())
SUPPORT_FEED = SITE.get('support_feed', '').strip()
GALLERY_FEED = SITE.get('gallery_feed', '').strip()
SUPPORT_OVERRIDES_PATH = SOURCE / 'data/support-overrides.json'
ORIGIN = SITE['origin'].rstrip('/')
PHONE = SITE.get('phone', '').strip()
ASSET_VERSION = hashlib.sha1((SOURCE / 'assets/css/styles.css').read_bytes() + (SOURCE / 'assets/js/main.js').read_bytes()).hexdigest()[:10]
ASSETS = '/assets'
LOGO = ASSETS + '/images/logo.png'
SITEMAP_PATHS = []
LEGACY_PUBLISH_DIRS = ('projects', 'apps', 'Support', 'legal', 'de')
PHOTO_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
ROOT_STUB_DIRS = ('projects',)

def phone_href(): return 'tel:' + re.sub(r'[^\d+]', '', PHONE)
def phone_display(): return PHONE
def locale_root(lang): return '' if lang == 'en' else '/de'
def locale_home(lang): return '/' if lang == 'en' else '/de/'
def localized_url(path, lang):
    if path == '/': return '/' if lang == 'en' else '/de/'
    if path == '/error-page.html': return '/error-page.html' if lang == 'en' else '/de/error-page.html'
    return ('' if lang == 'en' else '/de') + path
def output_file(localized):
    if localized == '/': return 'index.html'
    rel = localized.lstrip('/')
    if rel.endswith('.html'): return rel
    return (rel if rel.endswith('/') else rel + '/') + 'index.html'
def page_source(name, lang):
    german = SOURCE / f'pages/de/{name}.html'
    return german if lang == 'de' and german.exists() else SOURCE / f'pages/{name}.html'
def text_for(project, lang, field): return project.get(field + '_de') if lang == 'de' and project.get(field + '_de') else project[field]
def write(path, content):
    target = ROOT / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content, encoding='utf-8')
def local_projects(): return [p for p in PROJECTS if not p.get('url')]
def project_href(project, root): return escape(project.get('url') or f"{root}/apps/{project['slug']}/", quote=True)
def icon(project, extra=''):
    if project['icon']: return f'<img class="app-icon {extra}" src="{escape(project["icon"])}" alt="" width="80" height="80">'
    return '<span class="app-icon monogram-icon" aria-hidden="true">2FA</span>'
def public_image(value):
    if not isinstance(value, str): return ''
    parsed = urlparse(value.strip())
    return value.strip() if parsed.scheme in ('http', 'https') and parsed.netloc else ''
def paragraphs(text): return ''.join(f'<p>{escape(chunk.strip()).replace(chr(10), "<br>")}</p>' for chunk in (text or '').split('\n\n') if chunk.strip())
def position_key(row):
    try: return (0, float(row.get('age')))
    except (TypeError, ValueError): return (1, 0)
def match_project(label):
    key = label.casefold().strip()
    return next((p for p in local_projects() if p['name'].casefold() == key or p['slug'].casefold() == key or p.get('name_de', '').casefold() == key), None)
def dollar(text): return text.replace('$', '$$')
def fetch_feed_rows(endpoint):
    rows = []; page = 1
    while page <= 20:
        separator = '&' if '?' in endpoint else '?'; url = f'{endpoint}{separator}page={page}&limit=100'
        key = os.environ.get('APPBACKEND_API_KEY')
        if key: url += '&api_key=' + quote(key)
        request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'sgroi.ga-build'})
        with urllib.request.urlopen(request, timeout=20) as response: payload = json.loads(response.read().decode())
        batch = payload.get('data') or []; rows.extend(batch); total = int(payload.get('count') or 0)
        if not batch or len(rows) >= total: break
        page += 1
    return rows
def load_support_articles():
    remote = []
    if SUPPORT_FEED:
        try: remote = fetch_feed_rows(SUPPORT_FEED); print(f'Loaded {len(remote)} support article(s) from AppBackend.')
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as error: print('Warning: support feed unavailable:', error)
    overrides = json.loads(SUPPORT_OVERRIDES_PATH.read_text()) if SUPPORT_OVERRIDES_PATH.exists() else []
    overridden = {str(r.get('application') or '').strip().casefold() for r in overrides}
    return [r for r in remote if str(r.get('application') or '').strip().casefold() not in overridden] + overrides
def article_html(row):
    title = (row.get('name') or '').strip() or 'Untitled'; figure = ''
    image = public_image(row.get('attachment'))
    if image: figure = f'<figure class="answer-screenshot"><img src="{escape(image, quote=True)}" alt="{escape(title, quote=True)}" loading="lazy"></figure>'
    return f'<details name="support-answers"><summary>{escape(title)}</summary><div>{paragraphs(row.get("content"))}{figure}</div></details>'
def support_cards(lang):
    root = locale_root(lang); cards = []
    for project in local_projects():
        cards.append(f'<a class="support-card" href="{root}/Support/{escape(project["slug"])}/">{icon(project)}<h2>{escape(project["name"])}</h2></a>')
    return '\n'.join(cards)
def support_page_html(project, articles, copy, lang):
    rows = [r for r in articles if match_project(str(r.get('application') or '').strip()) == project]
    rows.sort(key=lambda r: (position_key(r), (r.get('name') or '').casefold()))
    email = escape(SITE['email'])
    if rows: answers = ''.join(article_html(r) for r in rows)
    else: answers = f'<p class="answers-empty">{escape(copy["answers_empty"])} <a href="mailto:{email}?subject={quote(project["name"] + " Support")}">{escape(copy["answers_send"])}</a> {escape(copy["answers_mention"])}</p>'
    if lang == 'de':
        intro = f'<p class="eyebrow">Support</p><h1>{escape(project["name"])}</h1><p>Hilfe und Antworten für diese App.</p>'
        contact = f'<p class="eyebrow">Mit einer Person sprechen</p><h2>Noch Hilfe nötig?</h2><p>Schreib mir mit App-Name, App-Version, macOS-Version und einer kurzen Beschreibung, was passiert ist. Schritte zum Nachstellen sind besonders hilfreich.</p><p>Bitte entferne persönliche Angaben aus Screenshots und sende niemals Passwörter, Authentisierungsgeheimnisse oder Wiederherstellungscodes.</p><div class="actions"><a class="button" href="mailto:{email}?subject=App%20Support">Kontakt</a><a class="text-link" href="{locale_root(lang)}/legal/privacy/#support">Wie Support-Daten behandelt werden</a></div>'
    else:
        intro = f'<p class="eyebrow">Support</p><h1>{escape(project["name"])}</h1><p>Help and answers for this app.</p>'
        contact = f'<p class="eyebrow">Talk to a person</p><h2>Still need a hand?</h2><p>Email me with the app name, app version, macOS version, and a short description of what happened. Steps to reproduce an issue are especially helpful.</p><p>Please remove personal information from screenshots and never include passwords, authentication secrets, or recovery codes.</p><div class="actions"><a class="button" href="mailto:{email}?subject=App%20Support">Contact</a><a class="text-link" href="{locale_root(lang)}/legal/privacy/#support">How support data is handled</a></div>'
    return f'<div class="wrap"><header class="page-intro">{intro}</header><div class="support-answers"><section class="answer-group is-open" id="{escape(project["slug"])}"><h2>{escape(project["name"])}</h2>{answers}</section></div><section class="contact-panel" id="contact">{contact}</section></div>'
def product_gallery_html(project, lang): return ''
def project_cards(lang, root, copy, projects=None):
    return '\n'.join(f'<a class="project-card" href="{project_href(p, root)}"><div class="project-info"><h3>{escape(p["name"])}</h3><p>{escape(text_for(p, lang, "description"))}</p><span class="text-link">{escape(copy["learn_more"])} <span aria-hidden="true">›</span></span></div><div class="project-art project-art--{escape(p["slug"])}">{icon(p)}</div></a>' for p in (projects if projects is not None else local_projects()))
def latest_cards(lang, root, copy): return project_cards(lang, root, copy, [p for p in PROJECTS if p.get('on_home')])
def project_tiles(root): return '\n'.join(f'<a class="apps-tile" href="{project_href(p, root)}">{icon(p)}<h2>{escape(p["name"])}</h2></a>' for p in PROJECTS)
def page(path, title, description, content, lang, image=None):
    copy = I18N[lang]; root = locale_root(lang); home = locale_home(lang); localized = localized_url(path, lang); en_url = localized_url(path, 'en'); de_url = localized_url(path, 'de'); url = ORIGIN + localized
    social = ''
    if image: social = f'<meta property="og:image" content="{escape(ORIGIN + image, quote=True)}"><meta name="twitter:image" content="{escape(ORIGIN + image, quote=True)}">'
    output = LAYOUT.substitute(html_lang=lang, title=escape(title), description=escape(description), canonical=escape(url), hreflang_en=escape(ORIGIN + en_url), hreflang_de=escape(ORIGIN + de_url), year=escape(SITE['year']), app_store_url=escape(SITE['app_store_url'] or root + '/apps/', quote=True), content=content, social_image=social, twitter_card='summary', projects_current='aria-current="page"' if path == '/apps/' else '', support_current='aria-current="page"' if path == '/Support/' else '', about_current='aria-current="page"' if path == '/about/' else '', blog_url=escape(SITE.get('blog_url') or '', quote=True), home=home, root=root, assets=ASSETS, asset_version=ASSET_VERSION, lang_switch_href=escape(de_url if lang == 'en' else en_url, quote=True), lang_switch_label='DE' if lang == 'en' else 'EN', lang_switch_code='de' if lang == 'en' else 'en', lang_switch_aria='Auf Deutsch wechseln' if lang == 'en' else 'Switch to English', skip=escape(copy['skip']), home_label=escape(copy['home_label']), nav_about=escape(copy['nav_about']), nav_projects=escape(copy['nav_projects']), nav_support=escape(copy['nav_support']), nav_blog=escape(copy['nav_blog']), nav_main=escape(copy['nav_main']), nav_legal=escape(copy['nav_legal']), menu=escape(copy['menu']), follow_me=escape(copy['follow_me']), social_label=escape(copy['social_label']), footer_tag=escape(copy['footer_tag']), footer_tag_url=escape(copy['footer_tag_url'], quote=True), back_top=escape(copy['back_top']), imprint=escape(copy['imprint']), privacy=escape(copy['privacy']), terms=escape(copy['terms']))
    write(output_file(localized), output)
    if localized not in SITEMAP_PATHS and not localized.endswith('error-page.html'): SITEMAP_PATHS.append(localized)
def sync_assets():
    target = ROOT / 'assets'
    if target.exists(): shutil.rmtree(target)
    shutil.copytree(SOURCE / 'assets', target)
def clean_legacy_publish_trees():
    for name in LEGACY_PUBLISH_DIRS:
        path = SOURCE / name
        if path.exists(): shutil.rmtree(path)
    for name in ROOT_STUB_DIRS:
        path = ROOT / name
        if path.exists(): shutil.rmtree(path)
def ensure_photo_folders():
    for p in PROJECTS:
        folder = SOURCE / 'assets/images' / p['slug'] / 'photos'; folder.mkdir(parents=True, exist_ok=True)
def redirect_document(target, lang='en'): return f'<meta http-equiv="refresh" content="0; url={escape(ORIGIN + target, quote=True)}"><script>window.location.replace({json.dumps(ORIGIN + target)});</script>'
def write_legacy_stubs(paths):
    for old, new, lang in paths: write(output_file(old), redirect_document(new, lang))
def legacy_stub_paths():
    stubs = []
    for lang in ('en', 'de'):
        for path in ('/about/', '/legal/', '/legal/imprint/', '/legal/privacy/', '/legal/terms/', '/Support/', '/apps/'):
            new = localized_url(path, lang); stubs.append(('/src' + new, new, lang))
        for p in local_projects():
            new = localized_url('/apps/' + p['slug'] + '/', lang); stubs += [('/src' + new, new, lang)]
    return stubs
def redirects():
    write('_redirects', '/src/* /:splat 301\n/projects/* /apps/:splat 301\n')
def write_seo_files():
    write('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n'); write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{escape(ORIGIN + p)}</loc></url>' for p in SITEMAP_PATHS) + '</urlset>')
def build():
    SITEMAP_PATHS.clear(); ensure_photo_folders(); sync_assets(); clean_legacy_publish_trees(); articles = load_support_articles()
    routes = [('about','/about/','about_title','about_desc'),('legal','/legal/','legal_title','legal_desc'),('imprint','/legal/imprint/','imprint_title','imprint_desc'),('privacy','/legal/privacy/','privacy_title','privacy_desc'),('terms','/legal/terms/','terms_title','terms_desc'),('support','/Support/','support_title','support_desc'),('apps','/apps/','apps_title','apps_desc')]
    for lang in ('en','de'):
        copy = I18N[lang]; root = locale_root(lang); home = locale_home(lang); values = {'latest_cards': latest_cards(lang, root, copy), 'project_cards': project_cards(lang, root, copy), 'project_tiles': project_tiles(root), 'contact_email': escape(SITE['email']), 'contact_phone': escape(phone_display()), 'contact_phone_href': escape(phone_href(), quote=True), 'support_cards': dollar(support_cards(lang)), 'support_articles': '', 'support_feed': '', 'support_apps': '', 'support_overrides': '', 'support_ui': '', 'root': root, 'home': home, 'assets': ASSETS, 'error_home': escape(copy['error_home']), 'nav_projects': escape(copy['nav_projects']), 'social_label': escape(copy['social_label'])}
        source = page_source('home', lang); page('/', copy['home_title'], copy['home_desc'], Template(source.read_text()).substitute(values), lang, LOGO)
        for name, path, title_key, desc_key in routes:
            source = page_source(name, lang)
            if source.exists(): page(path, copy[title_key] + ' — Gabriel Sgroi', copy[desc_key], Template(source.read_text()).substitute(values), lang, '/assets/images/aboutme.jpg' if name == 'about' else None)
        for project in local_projects():
            source = page_source(project['slug'], lang)
            if source.exists():
                project_values = dict(values, product_icon=icon(project), product_gallery='', learn_more_href='#features')
                project_values['store_action'] = f'<a class="button" href="{escape(project["app_store_url"], quote=True)}" rel="noopener">{escape(copy["store_download"])}</a>'
                page('/apps/' + project['slug'] + '/', project['name'] + ' — Gabriel Sgroi', text_for(project, lang, 'description'), Template(source.read_text()).substitute(project_values), lang, project['icon'])
            page('/Support/' + project['slug'] + '/', project['name'] + ' Support — Gabriel Sgroi', text_for(project, lang, 'description'), support_page_html(project, articles, copy, lang), lang, project['icon'])
    write_legacy_stubs(legacy_stub_paths()); redirects(); write_seo_files(); print('Static pages built.')
if __name__ == '__main__': build()
