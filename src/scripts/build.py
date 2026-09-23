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
CONTACT = json.loads((SOURCE / 'data/contact.json').read_text())
BLOG = json.loads((SOURCE / 'data/blog.json').read_text()) if (SOURCE / 'data/blog.json').exists() else []
GALLERY_FEED = SITE.get('gallery_feed', '').strip()
SUPPORT_OVERRIDES_PATH = SOURCE / 'data/support-overrides.json'
ORIGIN = SITE['origin'].rstrip('/')
PHONE = SITE.get('phone', '').strip()
ASSET_VERSION = hashlib.sha1((SOURCE / 'assets/css/styles.css').read_bytes() + (SOURCE / 'assets/js/main.js').read_bytes()).hexdigest()[:10]
ICON_VERSION = hashlib.sha1(b''.join(path.read_bytes() for path in sorted((SOURCE / 'assets/images').glob('*/*.png')) if path.is_file())).hexdigest()[:10]
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
    if project['icon']:
        src = f'{project["icon"]}?v={ICON_VERSION}' if project['icon'].startswith('/') else project['icon']
        return f'<img class="app-icon {extra}" src="{escape(src, quote=True)}" alt="" width="256" height="256" loading="eager" decoding="async">'
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
    if rows: answers = ''.join(article_html(r, lang) for r in rows)
    else: answers = f'<p class="answers-empty">{escape(copy["answers_empty"])} <a href="{locale_root(lang)}/contact/support/">{escape(copy["answers_send"])}</a> {escape(copy["answers_mention"])}</p>'
    intro = f'<section class="support-hero product-hero" aria-labelledby="support-product-title">{icon(project)}<h1 id="support-product-title">{escape(project["name"])} Support</h1></section>'
    contact_label = 'Kontakt' if lang == 'de' else 'Contact'
    search_placeholder = 'Suche' if lang == 'de' else 'Search'
    search_label = 'Support durchsuchen' if lang == 'de' else 'Search support'
    search_box = f'<div class="support-search"><label for="support-search">{escape(search_label)}</label><input id="support-search" type="search" placeholder="{search_placeholder}" autocomplete="off" data-support-search></div>'
    return f'<div class="wrap"><header class="support-page-header">{intro}</header>{search_box}<div class="support-answers"><section class="answer-group is-open" id="{escape(project["slug"])}">{answers}</section></div><div class="support-contact-link"><a class="button" href="{locale_root(lang)}/contact/support/">{contact_label}</a></div></div>'
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

def blog_image_credit(figure, lang):
    photographer = escape((figure or {}).get('photographer', '').strip())
    creator_url = public_image((figure or {}).get('creator_url', ''))
    source_url = public_image((figure or {}).get('source_url', ''))
    if not photographer: return ''
    creator = f'<a href="{escape(creator_url, quote=True)}" target="_blank" rel="noopener">{photographer}</a>' if creator_url else photographer
    source = f'<a href="{escape(source_url, quote=True)}" target="_blank" rel="noopener">Unsplash</a>' if source_url else 'Unsplash'
    prefix = 'Foto von' if lang == 'de' else 'Photo by'
    connector = 'auf' if lang == 'de' else 'on'
    return f'<p class="blog-image-credit">{prefix} {creator} {connector} {source}</p>'

def blog_preview_image(post, lang):
    """A single teaser image per card; falls back to a neutral placeholder."""
    figure = post.get('preview') or post.get('hero') or {'src': '/images/blog/placeholder-wide.svg', 'alt': 'Placeholder', 'alt_de': 'Platzhalter'}
    src = figure.get('src', '').strip()
    if not src: return ''
    return f'<div class="blog-card__thumb"><img src="{escape(ASSETS + src, quote=True)}" alt="{escape(blog_text(figure, lang, "alt"), quote=True)}" loading="lazy" width="720" height="450"></div>'
def blog_cards(lang):
    cards = []
    for post in sorted(BLOG, key=lambda item: item.get('date', ''), reverse=True):
        figure = post.get('preview') or post.get('hero') or {}
        cards.append(f'<article class="blog-card"><a class="blog-card__post" href="{escape(blog_href(post, lang), quote=True)}"><p class="blog-card__meta">{escape(blog_date(post, lang))}</p><h2>{escape(blog_text(post, lang, "title"))}</h2><p class="blog-card__preview">{escape(blog_text(post, lang, "excerpt"))}</p>{blog_preview_image(post, lang)}</a>{blog_image_credit(figure, lang)}</article>')
    return '\n'.join(cards)

def blog_social_html(copy):
    return f'''<nav class="about-layout__social" aria-label="{escape(copy['social_label'])}">
      <a href="https://x.com/sgroiga" rel="noopener" aria-label="X"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.74l7.73-8.835L1.254 2.25H8.08l4.253 5.622L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
      <a href="https://medium.com/@sgroiga" rel="noopener" aria-label="Medium"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M13.54 12a6.82 6.82 0 0 1-6.77 6.82A6.82 6.82 0 0 1 0 12a6.82 6.82 0 0 1 6.77-6.82A6.82 6.82 0 0 1 13.54 12Zm7.42 0c0 3.54-1.51 6.41-3.38 6.41s-3.39-2.87-3.39-6.41 1.52-6.41 3.39-6.41S20.96 8.46 20.96 12Zm3.04 0c0 3.17-.53 5.75-1.19 5.75s-1.19-2.58-1.19-5.75.53-5.75 1.19-5.75 1.19 2.58 1.19 5.75Z"/></svg></a>
      <a href="https://www.linkedin.com/in/sgroiga/" rel="noopener" aria-label="LinkedIn"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.29ZM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12Zm1.78 13.02H3.56V9h3.56v11.45ZM22.23 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45C23.2 24 24 23.23 24 22.27V1.73C24 .77 23.2 0 22.22 0h.01Z"/></svg></a>
      <a href="https://www.producthunt.com/@sgroiga" rel="noopener" aria-label="Product Hunt"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" fill-rule="evenodd" d="M12 1.5a10.5 10.5 0 1 0 0 21 10.5 10.5 0 0 0 0-21ZM9.5 7h4.1a3.1 3.1 0 0 1 0 6.2H11.3V17H9.5V7Zm1.8 4.4h2.3a1.3 1.3 0 1 0 0-2.6h-2.3v2.6Z"/></svg></a>
    </nav>'''

def blog_figure_html(figure, lang):
    src = (figure or {}).get('src', '').strip()
    if not src: return ''
    alt = escape(blog_text(figure, lang, 'alt'), quote=True)
    caption = escape(blog_text(figure, lang, 'caption'))
    width = escape(str(figure.get('width', 720)), quote=True)
    height = escape(str(figure.get('height', 450)), quote=True)
    caption_html = f'<figcaption>{caption}</figcaption>' if caption else ''
    loading = 'eager' if figure.get('eager') else 'lazy'
    return f'<figure class="blog-figure blog-figure--{escape(figure.get("variant", "wide"), quote=True)}"><img src="{escape(ASSETS + src, quote=True)}" alt="{alt}" loading="{loading}" width="{width}" height="{height}">{caption_html}</figure>'
def blog_section_media(section, lang):
    """One image per block, never a gallery."""
    return blog_figure_html(section.get('figure'), lang)
def blog_editorial_html(post, lang):
    """Newsletter-style single column: centered date and title, text blocks separated by figures."""
    date_label = escape(blog_date(post, lang))
    category = escape(post.get('category', ''))
    title = escape(blog_text(post, lang, 'title'))
    back_url = escape(localized_url('/blog/', lang), quote=True)
    back_label = escape(I18N[lang]['back_to_blog'])
    blocks = []
    for section in post.get('sections', []):
        heading = escape(blog_text(section, lang, 'title'))
        body = paragraphs(blog_text(section, lang, 'body'))
        if section.get('style') == 'chapter':
            chapter_date = escape(blog_text(section, lang, 'date') or blog_date(post, lang))
            blocks.append(f'<section class="blog-editorial__chapter"><p class="blog-editorial__meta">{chapter_date}</p><h2>{heading}</h2>{body}{blog_section_media(section, lang)}</section>')
        else:
            blocks.append(f'<section class="blog-editorial__section"><h3>{heading}</h3>{body}{blog_section_media(section, lang)}</section>')
    return f'''<div class="blog-editorial">
  <header class="blog-editorial__header">
    <p class="blog-editorial__meta">{date_label}{(" · " + category) if category else ""}</p>
    <h1 id="blog-heading">{title}</h1>
  </header>
  <p class="blog-editorial__intro">{escape(blog_text(post, lang, 'intro'))}</p>
  {blog_figure_html(post.get('hero'), lang)}
  {''.join(blocks)}
  <div class="blog-editorial__footer"><a class="button" href="{back_url}">{back_label}</a></div>
</div>'''
def blog_article_html(post, lang):
    if post.get('layout') == 'editorial': return blog_editorial_html(post, lang)
    sections = ''.join(f'<section class="blog-article__section"><h2>{escape(blog_text(section, lang, "title"))}</h2>{paragraphs(blog_text(section, lang, "body"))}</section>' for section in post.get('sections', []))
    date_label = escape(blog_date(post, lang))
    category = escape(post.get('category', ''))
    title = escape(blog_text(post, lang, 'title'))
    intro = escape(blog_text(post, lang, 'intro'))
    back_url = escape(localized_url('/blog/', lang), quote=True)
    back_label = escape(I18N[lang]['back_to_blog'])
    copy = I18N[lang]
    preview = post.get('preview') or {}
    preview_src = preview.get('src', '').strip()
    article_image = ''
    if preview_src:
        article_image = f'<figure class="blog-article__hero"><img src="{escape(ASSETS + preview_src, quote=True)}" alt="{escape(blog_text(preview, lang, "alt"), quote=True)}" loading="eager" width="1600" height="900"><figcaption>{blog_image_credit(preview, lang)}</figcaption></figure>'
    return f'''<div class="wrap about-layout">
  <aside class="about-layout__profile">
    <img class="about-layout__photo" src="{ASSETS}/images/aboutme.jpg" alt="Gabriel Sgroi" width="280" height="280">
    <p class="about-layout__name">Gabriel Sgroi</p>
    {blog_social_html(copy)}
  </aside>
  <article class="about-layout__body prose blog-article" aria-labelledby="blog-heading">
    <header class="blog-article__header"><p class="eyebrow">{date_label} · {category}</p><h1 id="blog-heading">{title}</h1></header>
    {article_image}
    <p class="blog-article__intro">{intro}</p>{sections}
    <div class="blog-article__back actions"><a class="button" href="{back_url}">{back_label}</a></div>
  </article>
</div>'''
def contact_topic_cards(lang):
    return '\n'.join(f'    <a class="contact-topic" href="{locale_root(lang)}{t.get("href") or "/contact/" + t["slug"] + "/"}"><span class="contact-topic__name">{escape(text_for(t, lang, "name"))}</span><span class="contact-topic__desc">{escape(text_for(t, lang, "description"))}</span></a>' for t in CONTACT['topics'])
def contact_topic_page_html(topic, lang):
    form_id = escape(CONTACT['forms'][topic['form']], quote=True)
    return f'<div class="wrap contact-page"><header class="page-intro"><h1>{escape(text_for(topic, lang, "name"))}</h1></header><section class="contact-form" aria-label="{escape(text_for(topic, lang, "name"), quote=True)}"><div class="deftform" data-form-id="{form_id}" data-form-width="100%" data-form-align="center" data-form-auto-height="1"></div><script src="https://cdn.deftform.com/embed.js"></script></section></div>'
EMAIL_SCOPES = {
    'privacy': ('This address is <strong>only for privacy and data protection requests</strong>.', 'Diese Adresse gilt <strong>ausschließlich für Anfragen zum Datenschutz</strong>.'),
    'terms': ('This address is <strong>only for questions about these Terms</strong>.', 'Diese Adresse gilt <strong>ausschließlich für Fragen zu diesen Nutzungsbedingungen</strong>.'),
    'legal': ('This address is <strong>only for legal inquiries</strong>.', 'Diese Adresse gilt <strong>ausschließlich für rechtliche Anfragen</strong>.'),
}
def protected_email(lang, scope):
    de = lang == 'de'; root = locale_root(lang)
    scope_text = EMAIL_SCOPES[scope][1 if de else 0]
    if de:
        rest = f'Für alle anderen Anliegen – insbesondere Support, Fehlerberichte, Feedback, Marketing, Partnerschaften oder Kooperationen – nutze bitte die <a href="{root}/contact/">Kontaktseite</a>. Anfragen dieser Art an die E-Mail-Adresse werden nicht bearbeitet.'
        label, important, hint, nojs = 'E-Mail-Adresse als Bild', 'Wichtig:', 'Die Adresse bitte abtippen.', 'Bitte JavaScript aktivieren, um die E-Mail-Adresse zu sehen.'
    else:
        rest = f'For everything else – in particular support, bug reports, feedback, marketing, partnerships or collaborations – please use the <a href="{root}/contact/">contact page</a>. Such requests sent to this email address will not be handled.'
        label, important, hint, nojs = 'Email address as image', 'Important:', 'Please type the address manually.', 'Please enable JavaScript to see the email address.'
    return f'<span class="protected-email" data-protected-email><canvas class="protected-email__canvas" role="img" aria-label="{label}" width="0" height="0"></canvas><noscript>{nojs}</noscript></span><span class="email-notice" role="note"><strong>{important}</strong> {scope_text} {rest} <span class="email-notice__hint">{hint}</span></span>'
def page(path, title, description, content, lang, image=None):
    copy = I18N[lang]; root = locale_root(lang); home = locale_home(lang); localized = localized_url(path, lang); en_url = localized_url(path, 'en'); de_url = localized_url(path, 'de'); url = ORIGIN + localized
    social = ''
    if image: social = f'<meta property="og:image" content="{escape(ORIGIN + image, quote=True)}"><meta name="twitter:image" content="{escape(ORIGIN + image, quote=True)}">'
    output = LAYOUT.substitute(html_lang=lang, title=escape(title), description=escape(description), canonical=escape(url), hreflang_en=escape(ORIGIN + en_url), hreflang_de=escape(ORIGIN + de_url), year=escape(SITE['year']), app_store_url=escape(SITE['app_store_url'] or root + '/apps/', quote=True), content=content, social_image=social, twitter_card='summary', projects_current='aria-current="page"' if path == '/apps/' else '', support_current='aria-current="page"' if path == '/Support/' else '', about_current='aria-current="page"' if path == '/about/' else '', contact_current='aria-current="page"' if path.startswith('/contact/') else '', nav_contact=escape(copy['nav_contact']), blog_url=escape(localized_url('/blog/', lang), quote=True), home=home, root=root, assets=ASSETS, asset_version=ASSET_VERSION, lang_switch_href=escape(de_url if lang == 'en' else en_url, quote=True), lang_switch_label='EN' if lang == 'en' else 'DE', lang_switch_code=lang, lang_switch_aria='Auf Deutsch wechseln' if lang == 'en' else 'Switch to English', skip=escape(copy['skip']), home_label=escape(copy['home_label']), nav_about=escape(copy['nav_about']), nav_projects=escape(copy['nav_projects']), nav_support=escape(copy['nav_support']), nav_blog=escape(copy['nav_blog']), nav_main=escape(copy['nav_main']), nav_legal=escape(copy['nav_legal']), menu=escape(copy['menu']), follow_me=escape(copy['follow_me']), social_label=escape(copy['social_label']), footer_tag=escape(copy['footer_tag']), footer_tag_url=escape(copy['footer_tag_url'], quote=True), back_top=escape(copy['back_top']), imprint=escape(copy['imprint']), privacy=escape(copy['privacy']), terms=escape(copy['terms']))
    write(output_file(localized), output)
    hidden = localized.endswith('error-page.html') or localized in ('/review/', '/kanboa-project/', '/de/kanboa-project/', '/request-confirmation/', '/de/request-confirmation/')
    if localized not in SITEMAP_PATHS and not hidden: SITEMAP_PATHS.append(localized)
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
    routes = [('about','/about/','about_title','about_desc'),('legal','/legal/','legal_title','legal_desc'),('imprint','/legal/imprint/','imprint_title','imprint_desc'),('privacy','/legal/privacy/','privacy_title','privacy_desc'),('terms','/legal/terms/','terms_title','terms_desc'),('support','/Support/','support_title','support_desc'),('apps','/apps/','apps_title','apps_desc'),('contact','/contact/','contact_title','contact_desc'),('send-confirmation','/send-confirmation/','confirmation_title','confirmation_desc'),('request-confirmation','/request-confirmation/','request_confirmation_title','request_confirmation_desc'),('kanboa','/kanboa/','kanboa_title','kanboa_desc'),('kanboa-project','/kanboa-project/','kanboa_project_title','kanboa_project_desc')]
    for lang in ('en','de'):
        copy = I18N[lang]; root = locale_root(lang); home = locale_home(lang); values = {'latest_cards': latest_cards(lang, root, copy), 'project_cards': project_cards(lang, root, copy, PROJECTS), 'project_tiles': project_tiles(root), 'email_privacy': protected_email(lang, 'privacy'), 'email_terms': protected_email(lang, 'terms'), 'email_legal': protected_email(lang, 'legal'), 'contact_phone': escape(phone_display()), 'contact_phone_href': escape(phone_href(), quote=True), 'support_cards': dollar(support_cards(lang)), 'support_articles': '', 'root': root, 'home': home, 'assets': ASSETS, 'error_home': escape(copy['error_home']), 'nav_projects': escape(copy['nav_projects']), 'social_label': escape(copy['social_label']), 'contact_topics': contact_topic_cards(lang)}
        source = page_source('home', lang); page('/', copy['home_title'], copy['home_desc'], Template(source.read_text()).substitute(values), lang, LOGO)
        blog_content = f'<section class="wrap blog-index"><header class="page-intro page-intro-plain"><h1>{escape(copy["blog_title"])}</h1></header><div class="blog-grid">{blog_cards(lang)}</div></section>'
        page('/blog/', copy['blog_title'] + ' — Gabriel Sgroi', copy['blog_desc'], blog_content, lang)
        for post in BLOG:
            article = blog_article_html(post, lang)
            preview_src = (post.get('preview') or {}).get('src', '').strip()
            page('/blog/' + post['slug'] + '/', blog_text(post, lang, 'title') + ' — Gabriel Sgroi', blog_text(post, lang, 'excerpt'), article, lang, ASSETS + preview_src if preview_src else None)
        for name, path, title_key, desc_key in routes:
            source = page_source(name, lang)
            if source.exists(): page(path, copy[title_key] + ' — Gabriel Sgroi', copy[desc_key], Template(source.read_text()).substitute(values), lang, '/assets/images/aboutme.jpg' if name == 'about' else None)
        for topic in CONTACT['topics']:
            page('/contact/' + topic['slug'] + '/', text_for(topic, lang, 'name') + ' — ' + copy['contact_title'] + ' — Gabriel Sgroi', text_for(topic, lang, 'description'), contact_topic_page_html(topic, lang), lang)
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
                    badge = f'<a class="app-store-badge" href="{escape(store_url, quote=True)}" rel="noopener" aria-label="{("Download " + project["name"] + " on the Mac App Store") if lang == "en" else (project["name"] + " im Mac App Store laden")}"><svg class="app-store-badge__apple" width="29" height="36" viewBox="0 0 32 40" aria-hidden="true" focusable="false"><path fill="#fff" d="M24.76888 20.30068a4.94881 4.94881 0 0 1 2.35656-4.15206 5.06566 5.06566 0 0 0-3.99116-2.15768c-1.67924-.17626-3.30719 1.00483-4.1629 1.00483-.87227 0-2.18977-.98733-3.6085-.95814a5.31529 5.31529 0 0 0-4.47292 2.72787c-1.934 3.34842-.49141 8.26947 1.3612 10.97608.9269 1.32535 2.01018 2.8058 3.42763 2.7533 1.38706-.05753 1.9051-.88448 3.5794-.88448 1.65876 0 2.14479.88448 3.591.8511 1.48838-.02416 2.42613-1.33124 3.32051-2.66914a10.962 10.962 0 0 0 1.51842-3.09251 4.78205 4.78205 0 0 1-2.91958-4.39917ZM22.03725 12.21089a4.87248 4.87248 0 0 0 1.11452-3.49062 4.95746 4.95746 0 0 0-3.20758 1.65961 4.63634 4.63634 0 0 0-1.14371 3.36139 4.09905 4.09905 0 0 0 3.23677-1.53038Z"/></svg><span class="app-store-badge__copy"><span>{("Download on the" if lang == "en" else "Laden im")}</span><strong>Mac App Store</strong></span></a>'
                else:
                    badge = f'<p class="product-coming-soon">{escape("Coming soon" if lang == "en" else "Demnächst")}</p>'
                project_values = dict(values, product_icon=icon(project), product_gallery=product_gallery_html(project, lang), app_store_badge=badge, learn_more_href='#features', app_store_url=escape(store_url or (root + '/apps/'), quote=True), store_download=escape(copy['store_download']))
                project_values['store_action'] = badge
                page('/apps/' + project['slug'] + '/', project['name'] + ' — Gabriel Sgroi', text_for(project, lang, 'description'), Template(source.read_text()).substitute(project_values), lang, project['icon'])
            page('/Support/' + project['slug'] + '/', project['name'] + ' Support — Gabriel Sgroi', text_for(project, lang, 'description'), support_page_html(project, articles, copy, lang), lang, project['icon'])
    write_legacy_stubs(legacy_stub_paths()); redirects(); write_seo_files(); print('Static pages built.')
if __name__ == '__main__': build()
