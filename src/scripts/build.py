#!/usr/bin/env python3
"""Build dependency-free HTML pages from one layout and shared project data."""
import hashlib
import json
import os
import re
import shutil
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
BLOG = json.loads((SOURCE / 'data/blog.json').read_text()) if (SOURCE / 'data/blog.json').exists() else []
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
    if path == '/review/': return '/review/'
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
    try: return (0, float(row.get('position', row.get('age'))))
    except (TypeError, ValueError): return (1, 0)
def match_project(label):
    key = re.sub(r'[^a-z0-9]+', '', label.casefold())
    return next((p for p in local_projects() if key in {
        re.sub(r'[^a-z0-9]+', '', p['name'].casefold()),
        re.sub(r'[^a-z0-9]+', '', p['slug'].casefold()),
        re.sub(r'[^a-z0-9]+', '', p.get('name_de', '').casefold()),
    }), None)
def dollar(text): return text.replace('$', '$$')
def load_support_articles():
    return json.loads(SUPPORT_OVERRIDES_PATH.read_text(encoding='utf-8')) if SUPPORT_OVERRIDES_PATH.exists() else []
def article_html(row, lang):
    localized = row.get(lang) or row.get('en') or row
    title = (localized.get('name') or '').strip() or 'Untitled'; figure = ''
    image = public_image(row.get('attachment'))
    if image: figure = f'<figure class="answer-screenshot"><img src="{escape(image, quote=True)}" alt="{escape(title, quote=True)}" loading="lazy"></figure>'
    return f'<details name="support-answers"><summary>{escape(title)}</summary><div>{paragraphs(localized.get("content"))}{figure}</div></details>'
def support_cards(lang):
    root = locale_root(lang)
    return '\n'.join(f'<a class="apps-tile" href="{root}/Support/{escape(project["slug"])}/">{icon(project)}<h2>{escape(project["name"])}</h2></a>' for project in local_projects())
def support_page_html(project, articles, copy, lang):
    rows = []
    for row in articles:
        matched = match_project(str(row.get('application') or '').strip())
        if matched == project or str(row.get('application') or '').strip().casefold() in {project['name'].casefold(), project['slug'].casefold()}:
            rows.append(row)
    rows.sort(key=lambda r: (position_key(r), ((r.get(lang) or r.get('en') or r).get('name') or '').casefold()))
    email = escape(SITE['email'])
    if rows: answers = ''.join(article_html(r, lang) for r in rows)
    else: answers = f'<p class="answers-empty">{escape(copy["answers_empty"])} <a href="mailto:{email}?subject={quote(project["name"] + " Support")}">{escape(copy["answers_send"])}</a> {escape(copy["answers_mention"])}</p>'
    intro = f'<section class="support-hero product-hero" aria-labelledby="support-product-title">{icon(project)}<h1 id="support-product-title">{escape(project["name"])} Support</h1></section>'
    contact_label = 'Kontakt' if lang == 'de' else 'Contact'
    search_placeholder = 'Suche' if lang == 'de' else 'Search'
    search_label = 'Support durchsuchen' if lang == 'de' else 'Search support'
    search_box = f'<div class="support-search"><label for="support-search">{escape(search_label)}</label><input id="support-search" type="search" placeholder="{search_placeholder}" autocomplete="off" data-support-search></div>'
    return f'<div class="wrap"><header class="support-page-header">{intro}</header>{search_box}<div class="support-answers"><section class="answer-group is-open" id="{escape(project["slug"])}">{answers}</section></div><div class="support-contact-link"><a class="button" href="{locale_root(lang)}/contact/">{contact_label}</a></div></div>'
def product_gallery_html(project, lang):
    folder = SOURCE / 'assets/images' / project['slug'] / 'photos'
    images = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in PHOTO_EXTS]) if folder.exists() else []
    if not images:
        images = [SOURCE / 'assets' / project['icon'].lstrip('/assets/')] if project.get('icon') else []
    cards = []
    for index, image in enumerate(images):
        if image.is_absolute():
            try: relative = image.relative_to(SOURCE / 'assets')
            except ValueError: continue
            src = ASSETS + '/' + relative.as_posix()
        else:
            src = ASSETS + '/images/' + project['slug'] + '/photos/' + image.name
        cards.append(f'<figure class="media-card"><img src="{escape(src, quote=True)}" alt="{escape(project["name"] + " preview " + str(index + 1), quote=True)}" loading="{"eager" if index == 0 else "lazy"}" width="720" height="450"></figure>')
    label_previous = 'Previous preview' if lang == 'en' else 'Vorherige Vorschau'
    label_next = 'Next preview' if lang == 'en' else 'Nächste Vorschau'
    return f'<section class="product-gallery-section" aria-label="{escape(project["name"] + " previews", quote=True)}"><div class="media-frame"><button class="gallery-nav" type="button" data-gallery-prev aria-label="{label_previous}">‹</button><div class="media-gallery" data-gallery-local><div class="media-gallery__track">{"".join(cards)}</div><div class="media-gallery__dots" role="tablist" aria-label="Preview images"></div></div><button class="gallery-nav" type="button" data-gallery-next aria-label="{label_next}">›</button></div></section>'
def project_cards(lang, root, copy, projects=None):
    return '\n'.join(f'<a class="project-card" href="{project_href(p, root)}"><div class="project-info"><h3>{escape(p["name"])}</h3><p>{escape(text_for(p, lang, "description"))}</p><span class="text-link">{escape(copy["learn_more"])} <span aria-hidden="true">›</span></span></div><div class="project-art project-art--{escape(p["slug"])}">{icon(p)}</div></a>' for p in (projects if projects is not None else local_projects()))
def latest_cards(lang, root, copy): return project_cards(lang, root, copy, [p for p in PROJECTS if p.get('on_home')])
def project_tiles(root): return '\n'.join(f'<a class="apps-tile" href="{project_href(p, root)}">{icon(p)}<h2>{escape(p["name"])}</h2></a>' for p in PROJECTS)
def blog_href(post, lang): return localized_url('/blog/' + post['slug'] + '/', lang)
def blog_text(item, lang, field): return item.get(field + '_de') if lang == 'de' and item.get(field + '_de') else item.get(field, '')
def blog_date(post, lang):
    try:
        from datetime import date
        value = date.fromisoformat(post['date'])
        return value.strftime('%d.%m.%Y') if lang == 'de' else value.strftime('%B %d, %Y')
    except (KeyError, ValueError): return post.get('date', '')
def blog_preview(post, lang):
    """Use a compact opening preview; CSS clamps it visually to two lines."""
    intro = blog_text(post, lang, 'intro').strip()
    return intro

def blog_cards(lang):
    return '\n'.join(f'<a class="blog-card" href="{escape(blog_href(post, lang), quote=True)}"><p class="blog-card__meta">{escape(blog_date(post, lang))} · {escape(post.get("category", ""))}</p><h2>{escape(blog_text(post, lang, "title"))}</h2><p class="blog-card__preview">{escape(blog_preview(post, lang))}</p></a>' for post in sorted(BLOG, key=lambda item: item.get('date', ''), reverse=True))

def blog_social_html(copy):
    return f'''<nav class="about-layout__social" aria-label="{escape(copy['social_label'])}">
      <a href="https://x.com/sgroiga" rel="noopener" aria-label="X"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.74l7.73-8.835L1.254 2.25H8.08l4.253 5.622L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
      <a href="https://medium.com/@sgroiga" rel="noopener" aria-label="Medium"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M13.54 12a6.82 6.82 0 0 1-6.77 6.82A6.82 6.82 0 0 1 0 12a6.82 6.82 0 0 1 6.77-6.82A6.82 6.82 0 0 1 13.54 12Zm7.42 0c0 3.54-1.51 6.41-3.38 6.41s-3.39-2.87-3.39-6.41 1.52-6.41 3.39-6.41S20.96 8.46 20.96 12Zm3.04 0c0 3.17-.53 5.75-1.19 5.75s-1.19-2.58-1.19-5.75.53-5.75 1.19-5.75 1.19 2.58 1.19 5.75Z"/></svg></a>
      <a href="https://www.linkedin.com/in/sgroiga/" rel="noopener" aria-label="LinkedIn"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.29ZM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12Zm1.78 13.02H3.56V9h3.56v11.45ZM22.23 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45C23.2 24 24 23.23 24 22.27V1.73C24 .77 23.2 0 22.22 0h.01Z"/></svg></a>
      <a href="https://www.producthunt.com/@sgroiga" rel="noopener" aria-label="Product Hunt"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" fill-rule="evenodd" d="M12 1.5a10.5 10.5 0 1 0 0 21 10.5 10.5 0 0 0 0-21ZM9.5 7h4.1a3.1 3.1 0 0 1 0 6.2H11.3V17H9.5V7Zm1.8 4.4h2.3a1.3 1.3 0 1 0 0-2.6h-2.3v2.6Z"/></svg></a>
    </nav>'''

def blog_article_html(post, lang):
    sections = ''.join(f'<section class="blog-article__section"><h2>{escape(blog_text(section, lang, "title"))}</h2>{paragraphs(blog_text(section, lang, "body"))}</section>' for section in post.get('sections', []))
    date_label = escape(blog_date(post, lang))
    category = escape(post.get('category', ''))
    title = escape(blog_text(post, lang, 'title'))
    intro = escape(blog_text(post, lang, 'intro'))
    back_url = escape(localized_url('/blog/', lang), quote=True)
    back_label = escape(I18N[lang]['back_to_blog'])
    copy = I18N[lang]
    return f'''<div class="wrap about-layout">
  <aside class="about-layout__profile">
    <img class="about-layout__photo" src="{ASSETS}/images/aboutme.jpg" alt="Gabriel Sgroi" width="280" height="280">
    <p class="about-layout__name">Gabriel Sgroi</p>
    {blog_social_html(copy)}
  </aside>
  <article class="about-layout__body prose blog-article" aria-labelledby="blog-heading">
    <header class="blog-article__header"><p class="eyebrow">{date_label} · {category}</p><h1 id="blog-heading">{title}</h1></header>
    <p class="blog-article__intro">{intro}</p>{sections}
    <div class="blog-article__back actions"><a class="button" href="{back_url}">{back_label}</a></div>
  </article>
</div>'''
def page(path, title, description, content, lang, image=None):
    copy = I18N[lang]; root = locale_root(lang); home = locale_home(lang); localized = localized_url(path, lang); en_url = localized_url(path, 'en'); de_url = localized_url(path, 'de'); url = ORIGIN + localized
    social = ''
    if image: social = f'<meta property="og:image" content="{escape(ORIGIN + image, quote=True)}"><meta name="twitter:image" content="{escape(ORIGIN + image, quote=True)}">'
    output = LAYOUT.substitute(html_lang=lang, title=escape(title), description=escape(description), canonical=escape(url), hreflang_en=escape(ORIGIN + en_url), hreflang_de=escape(ORIGIN + de_url), year=escape(SITE['year']), app_store_url=escape(SITE['app_store_url'] or root + '/apps/', quote=True), content=content, social_image=social, twitter_card='summary', projects_current='aria-current="page"' if path == '/apps/' else '', support_current='aria-current="page"' if path == '/Support/' else '', about_current='aria-current="page"' if path == '/about/' else '', blog_url=escape(localized_url('/blog/', lang), quote=True), home=home, root=root, assets=ASSETS, asset_version=ASSET_VERSION, lang_switch_href=escape(de_url if lang == 'en' else en_url, quote=True), lang_switch_label='EN' if lang == 'en' else 'DE', lang_switch_code=lang, lang_switch_aria='Auf Deutsch wechseln' if lang == 'en' else 'Switch to English', skip=escape(copy['skip']), home_label=escape(copy['home_label']), nav_about=escape(copy['nav_about']), nav_projects=escape(copy['nav_projects']), nav_support=escape(copy['nav_support']), nav_blog=escape(copy['nav_blog']), nav_main=escape(copy['nav_main']), nav_legal=escape(copy['nav_legal']), menu=escape(copy['menu']), follow_me=escape(copy['follow_me']), social_label=escape(copy['social_label']), footer_tag=escape(copy['footer_tag']), footer_tag_url=escape(copy['footer_tag_url'], quote=True), back_top=escape(copy['back_top']), imprint=escape(copy['imprint']), privacy=escape(copy['privacy']), terms=escape(copy['terms']))
    write(output_file(localized), output)
    if localized not in SITEMAP_PATHS and not localized.endswith('error-page.html') and localized != '/review/': SITEMAP_PATHS.append(localized)
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
    routes = [('about','/about/','about_title','about_desc'),('legal','/legal/','legal_title','legal_desc'),('imprint','/legal/imprint/','imprint_title','imprint_desc'),('privacy','/legal/privacy/','privacy_title','privacy_desc'),('terms','/legal/terms/','terms_title','terms_desc'),('support','/Support/','support_title','support_desc'),('apps','/apps/','apps_title','apps_desc'),('contact','/contact/','contact_title','contact_desc'),('send-confirmation','/send-confirmation/','confirmation_title','confirmation_desc')]
    for lang in ('en','de'):
        copy = I18N[lang]; root = locale_root(lang); home = locale_home(lang); values = {'latest_cards': latest_cards(lang, root, copy), 'project_cards': project_cards(lang, root, copy, PROJECTS), 'project_tiles': project_tiles(root), 'contact_email': escape(SITE['email']), 'contact_phone': escape(phone_display()), 'contact_phone_href': escape(phone_href(), quote=True), 'support_cards': dollar(support_cards(lang)), 'support_articles': '', 'root': root, 'home': home, 'assets': ASSETS, 'error_home': escape(copy['error_home']), 'nav_projects': escape(copy['nav_projects']), 'social_label': escape(copy['social_label']), 'price_free': '$0' if lang == 'en' else '0 €'}
        source = page_source('home', lang); page('/', copy['home_title'], copy['home_desc'], Template(source.read_text()).substitute(values), lang, LOGO)
        blog_content = f'<section class="wrap blog-index"><header class="page-intro page-intro-plain"><h1>{escape(copy["blog_title"])}</h1></header><div class="blog-grid">{blog_cards(lang)}</div></section>'
        page('/blog/', copy['blog_title'] + ' — Gabriel Sgroi', copy['blog_desc'], blog_content, lang)
        for post in BLOG:
            article = blog_article_html(post, lang)
            page('/blog/' + post['slug'] + '/', blog_text(post, lang, 'title') + ' — Gabriel Sgroi', blog_text(post, lang, 'excerpt'), article, lang)
        for name, path, title_key, desc_key in routes:
            source = page_source(name, lang)
            if source.exists(): page(path, copy[title_key] + ' — Gabriel Sgroi', copy[desc_key], Template(source.read_text()).substitute(values), lang, '/assets/images/aboutme.jpg' if name == 'about' else None)
        if lang == 'en':
            review_source = page_source('review', lang)
            if review_source.exists():
                page('/review/', copy['review_title'] + ' — Gabriel Sgroi', copy['review_desc'], Template(review_source.read_text()).substitute(values), lang)
        error_source = page_source('404', lang)
        if error_source.exists(): page('/404.html', '404 — Gabriel Sgroi', copy['error_desc'], Template(error_source.read_text()).substitute(values), lang)
        for project in local_projects():
            source = page_source(project['slug'], lang)
            if source.exists():
                store_url = (project.get('app_store_url') or '').strip()
                if store_url:
                    badge = f'<a class="app-store-badge" href="{escape(store_url, quote=True)}" rel="noopener" aria-label="{("Download " + project["name"] + " on the Mac App Store") if lang == "en" else (project["name"] + " im Mac App Store laden")}"><span class="app-store-badge__apple" aria-hidden="true"></span><span class="app-store-badge__copy"><span>{("Download on the" if lang == "en" else "Laden im")}</span><strong>Mac App Store</strong></span></a>'
                else:
                    badge = f'<p class="product-coming-soon">{escape("Coming soon" if lang == "en" else "Demnächst")}</p>'
                project_values = dict(values, product_icon=icon(project), product_gallery=product_gallery_html(project, lang), app_store_badge=badge, learn_more_href='#features', app_store_url=escape(store_url or (root + '/apps/'), quote=True), store_download=escape(copy['store_download']))
                project_values['store_action'] = badge
                page('/apps/' + project['slug'] + '/', project['name'] + ' — Gabriel Sgroi', text_for(project, lang, 'description'), Template(source.read_text()).substitute(project_values), lang, project['icon'])
            page('/Support/' + project['slug'] + '/', project['name'] + ' Support — Gabriel Sgroi', text_for(project, lang, 'description'), support_page_html(project, articles, copy, lang), lang, project['icon'])
    write_legacy_stubs(legacy_stub_paths()); redirects(); write_seo_files(); print('Static pages built.')
if __name__ == '__main__': build()
