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
ROOT = _SCRIPT_DIR.parents[1] if _SCRIPT_DIR.parent.name == 'src' else _SCRIPT_DIR.parent
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
ASSET_VERSION = hashlib.sha1(
    (SOURCE / 'assets/css/styles.css').read_bytes()
    + (SOURCE / 'assets/js/main.js').read_bytes()
).hexdigest()[:10]
PUBLIC = ''
ASSETS = '/assets'
LOGO = ASSETS + '/images/logo.png'
SITEMAP_PATHS = []
# Built page trees that used to live under /src and must become redirect stubs.
LEGACY_PUBLISH_DIRS = ('projects', 'apps', 'Support', 'legal', 'de')
PHOTO_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
ROOT_STUB_DIRS = ('projects',)


def phone_href():
    return 'tel:' + re.sub(r'[^\d+]', '', PHONE)


def phone_display():
    digits = re.sub(r'\D', '', PHONE)
    if digits.startswith('49') and digits[2:5] == '163':
        return f'+49 163 {digits[5:]}'
    return PHONE


def locale_root(lang):
    return '' if lang == 'en' else '/de'


def locale_home(lang):
    return '/' if lang == 'en' else '/de/'


def localized_url(path, lang):
    if path == '/':
        return '/' if lang == 'en' else '/de/'
    if path == '/error-page.html':
        return '/error-page.html' if lang == 'en' else '/de/error-page.html'
    prefix = '' if lang == 'en' else '/de'
    return prefix + path


def output_file(localized):
    if localized == '/':
        return 'index.html'
    rel = localized.lstrip('/')
    if rel.endswith('.html'):
        return rel
    if not rel.endswith('/'):
        rel += '/'
    return rel + 'index.html'


def page_source(name, lang):
    if lang == 'de':
        german = SOURCE / f'pages/de/{name}.html'
        if german.exists():
            return german
    return SOURCE / f'pages/{name}.html'


def text_for(project, lang, field):
    if lang == 'de' and project.get(field + '_de'):
        return project[field + '_de']
    return project[field]


def write(path, content):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')


def local_projects():
    return [p for p in PROJECTS if not p.get('url')]


def project_href(project, root):
    url = project.get('url')
    if url:
        return escape(url, quote=True)
    return f"{root}/apps/{escape(project['slug'])}/"


def icon(project, extra=''):
    if project['icon']:
        return f'<img class="app-icon {extra}" src="{escape(project["icon"])}" alt="" width="80" height="80">'
    return '<span class="app-icon monogram-icon" aria-hidden="true">2FA</span>'


def project_photo_files(slug):
    folder = SOURCE / 'assets' / 'images' / slug / 'photos'
    if not folder.is_dir():
        return []
    return sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in PHOTO_EXTS and not path.name.startswith('.')
    )


def fetch_feed_rows(endpoint):
    rows, page = [], 1
    while page <= 20:
        separator = '&' if '?' in endpoint else '?'
        url = f'{endpoint}{separator}page={page}&limit=100'
        key = os.environ.get('APPBACKEND_API_KEY')
        if key:
            url += '&api_key=' + quote(key)
        request = urllib.request.Request(url, headers={
            'Accept': 'application/json',
            'User-Agent': 'sgroi.ga-build',
        })
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode())
        batch = payload.get('data') or []
        rows.extend(batch)
        total = int(payload.get('count') or 0)
        if not batch or len(rows) >= total:
            break
        page += 1
    return rows


def product_gallery_html(project, lang):
    """Empty shell; images load live from AppBackend so CMS edits show on refresh."""
    if not GALLERY_FEED:
        return ''
    name = escape(project['name'])
    slug = escape(project['slug'])
    if lang == 'de':
        section_label = f'{name} Screenshots'
        gallery_label = 'Produktbilder. Ziehen oder mit den Pfeilen zwischen den Bildern wechseln.'
        prev_label = 'Vorherige Vorschau'
        next_label = 'Nächste Vorschau'
        alt_prefix = f'{name} Screenshot'
    else:
        section_label = f'{name} screenshots'
        gallery_label = 'Product screenshots. Drag or use the arrows to move between images.'
        prev_label = 'Previous preview'
        next_label = 'Next preview'
        alt_prefix = f'{name} screenshot'
    gallery_id = f'{slug}-gallery'
    feed = escape(GALLERY_FEED, quote=True)
    return (
        f'<section class="media-section is-loading" id="preview" aria-label="{section_label}" '
        f'data-gallery-feed="{feed}" data-gallery-app="{slug}" '
        f'data-gallery-alt-prefix="{escape(alt_prefix)}">'
        f'<div class="media-frame">'
        f'<button type="button" class="gallery-nav" data-gallery-previous aria-controls="{gallery_id}" aria-label="{escape(prev_label)}">'
        f'<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M14.7 5.3a1 1 0 0 1 0 1.4L9.4 12l5.3 5.3a1 1 0 1 1-1.4 1.4l-6-6a1 1 0 0 1 0-1.4l6-6a1 1 0 0 1 1.4 0Z"/></svg>'
        f'</button>'
        f'<div class="media-gallery" id="{gallery_id}" tabindex="0" role="region" aria-label="{escape(gallery_label)}"></div>'
        f'<button type="button" class="gallery-nav" data-gallery-next aria-controls="{gallery_id}" aria-label="{escape(next_label)}">'
        f'<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M9.3 5.3a1 1 0 0 1 1.4 0l6 6a1 1 0 0 1 0 1.4l-6 6a1 1 0 1 1-1.4-1.4L14.6 12 9.3 6.7a1 1 0 0 1 0-1.4Z"/></svg>'
        f'</button>'
        f'</div></section>'
    )


def project_cards(lang, root, copy, projects=None):
    cards = []
    for p in projects if projects is not None else local_projects():
        cards.append(f'''<a class="project-card" href="{project_href(p, root)}">
          <div class="project-info"><h3>{escape(p['name'])}</h3>
          <p>{escape(text_for(p, lang, 'description'))}</p><span class="text-link">{escape(copy['learn_more'])} <span aria-hidden="true">›</span></span></div>
          <div class="project-art project-art--{escape(p['slug'])}">{icon(p)}</div></a>''')
    return '\n'.join(cards)


def latest_cards(lang, root, copy):
    return project_cards(lang, root, copy, [p for p in PROJECTS if p.get('on_home')])


def project_tiles(root):
    tiles = []
    for p in PROJECTS:
        extra = ' rel="noopener"' if p.get('url') else ''
        tiles.append(
            f'<a class="apps-tile" href="{project_href(p, root)}"{extra}>'
            f'{icon(p)}<h2>{escape(p["name"])}</h2></a>'
        )
    return '\n'.join(tiles)


def dollar(text):
    return text.replace('$', '$$')


def public_image(value):
    if not value or not isinstance(value, str):
        return ''
    parsed = urlparse(value.strip())
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        return value.strip()
    return ''


def paragraphs(text):
    chunks = [chunk.strip() for chunk in (text or '').split('\n\n') if chunk.strip()]
    return ''.join(f'<p>{escape(chunk).replace(chr(10), "<br>")}</p>' for chunk in chunks)


def section_id(label, project):
    if project:
        return project['slug']
    slug = re.sub(r'[^a-z0-9]+', '-', label.casefold()).strip('-')
    taken = {item['slug'] for item in PROJECTS}
    if not slug or slug in taken:
        slug = ('topic-' + slug) if slug else 'general'
    return slug


def match_project(label):
    key = label.casefold()
    for project in PROJECTS:
        if project['name'].casefold() == key or project['slug'].casefold() == key:
            return project
    return None


def position_key(row):
    value = row.get('age')
    if value in (None, ''):
        return (1, 0)
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, 0)


def fetch_support_rows(endpoint):
    return fetch_feed_rows(endpoint)


def article_html(row):
    title = (row.get('name') or '').strip() or 'Untitled'
    body = paragraphs(row.get('content'))
    image = public_image(row.get('attachment'))
    figure = ''
    if image:
        figure = (
            f'<figure class="answer-screenshot"><img src="{escape(image, quote=True)}" '
            f'alt="{escape(title, quote=True)}" loading="lazy"></figure>'
        )
    return f'<details name="support-answers"><summary>{escape(title)}</summary><div>{body}{figure}</div></details>'


def support_cards(lang):
    cards = []
    for project in local_projects():
        slug = escape(project['slug'])
        cards.append(
            f'<a class="support-card" href="#{slug}" data-support-app="{slug}">'
            f'{icon(project)}'
            f'<h2>{escape(project["name"])}</h2>'
            f'<p>{escape(text_for(project, lang, "description"))}</p></a>'
        )
    return '\n'.join(cards)


def support_articles_html(articles, copy):
    grouped = {}
    for row in articles:
        raw = (row.get('application') or '').strip() or 'General'
        project = match_project(raw)
        label = project['name'] if project else raw
        grouped.setdefault(label, []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: (position_key(row), (row.get('name') or '').casefold()))

    sections = []
    seen = set()
    ordered = []
    for project in local_projects():
        ordered.append((project['name'], project))
        seen.add(project['name'].casefold())
        seen.add(project['slug'].casefold())
    for label in grouped:
        if label.casefold() not in seen:
            ordered.append((label, match_project(label)))

    if not ordered:
        return f'<p class="answers-empty">{escape(copy["answers_none"])}</p>'

    email = escape(SITE['email'])
    for label, project in ordered:
        rows = grouped.get(label, [])
        identifier = section_id(label, project)
        title_id = f'answers-title-{identifier}'
        heading = escape(project['name'] if project else label)
        if rows:
            items = ''.join(article_html(row) for row in rows)
        else:
            subject = quote(f'{project["name"] if project else label} Support')
            items = (
                f'<p class="answers-empty">{escape(copy["answers_empty"])} '
                f'<a href="mailto:{email}?subject={subject}">{escape(copy["answers_send"])}</a> '
                f'{escape(copy["answers_mention"])}</p>'
            )
        sections.append(
            f'<section class="answer-group" id="{escape(identifier)}" aria-labelledby="{title_id}">'
            f'<h2 id="{title_id}">{heading}</h2>{items}</section>'
        )
    return '\n'.join(sections)


def page(path, title, description, content, lang, image=None):
    copy = I18N[lang]
    root = locale_root(lang)
    home = locale_home(lang)
    localized = localized_url(path, lang)
    en_url = localized_url(path, 'en')
    de_url = localized_url(path, 'de')
    url = ORIGIN + localized
    store = SITE['app_store_url'] or (root + '/apps/')
    social = ''
    if image:
        image_url = escape(ORIGIN + image, quote=True)
        social = f'<meta property="og:image" content="{image_url}"><meta name="twitter:image" content="{image_url}"><meta property="og:image:alt" content="{escape(title)}">'
    output = LAYOUT.substitute(
        html_lang=lang,
        title=escape(title), description=escape(description), canonical=escape(url),
        hreflang_en=escape(ORIGIN + (en_url if en_url != '/' else '/')),
        hreflang_de=escape(ORIGIN + de_url),
        year=escape(SITE['year']),
        app_store_url=escape(store, quote=True),
        content=content, social_image=social, twitter_card='summary',
        projects_current='aria-current="page"' if path == '/apps/' else ('aria-current="true"' if path.startswith('/apps/') else ''),
        support_current='aria-current="page"' if path == '/Support/' else '',
        about_current='aria-current="page"' if path == '/about/' else '',
        blog_url=escape(SITE.get('blog_url') or 'https://medium.com/@sgroiga', quote=True),
        home=home, root=root or '',
        assets=ASSETS,
        asset_version=ASSET_VERSION,
        lang_switch_href=escape(de_url if lang == 'en' else en_url, quote=True),
        lang_switch_label='DE' if lang == 'en' else 'EN',
        lang_switch_code='de' if lang == 'en' else 'en',
        lang_switch_aria=escape(
            'Auf Deutsch wechseln' if lang == 'en' else 'Switch to English'
        ),
        skip=escape(copy['skip']), home_label=escape(copy['home_label']),
        nav_about=escape(copy['nav_about']), nav_projects=escape(copy['nav_projects']),
        nav_support=escape(copy['nav_support']), nav_blog=escape(copy['nav_blog']),
        nav_main=escape(copy['nav_main']), nav_legal=escape(copy['nav_legal']),
        menu=escape(copy['menu']),
        follow_me=escape(copy['follow_me']), social_label=escape(copy['social_label']),
        footer_tag=escape(copy['footer_tag']),
        footer_tag_url=escape(copy['footer_tag_url'], quote=True),
        back_top=escape(copy['back_top']),
        imprint=escape(copy['imprint']), privacy=escape(copy['privacy']), terms=escape(copy['terms']),
    )
    write(output_file(localized), output)
    if localized not in SITEMAP_PATHS and not localized.endswith('error-page.html'):
        SITEMAP_PATHS.append(localized)


def absolute_url(path):
    if path.startswith(('http://', 'https://')):
        return path
    if path.startswith('#'):
        return ORIGIN + path
    return ORIGIN + path


def redirect_document(target, lang='en'):
    """HTML stub for hosts without rewrite rules (e.g. GitHub Pages + App Store links)."""
    dest = absolute_url(target)
    escaped = escape(dest, quote=True)
    display = escape(dest)
    if lang == 'de':
        title = 'Weiterleitung…'
        heading = 'Diese Seite wurde verschoben'
        body = f'Falls die Weiterleitung nicht klappt: <a href="{escaped}">hier klicken</a>.'
    else:
        title = 'Redirecting…'
        heading = 'This page has moved'
        body = f'If you are not redirected automatically, <a href="{escaped}">continue here</a>.'
    return f'''<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="robots" content="noindex">
  <meta http-equiv="refresh" content="0; url={escaped}">
  <link rel="canonical" href="{escaped}">
  <script>window.location.replace({json.dumps(dest)});</script>
</head>
<body>
  <main>
    <h1>{escape(heading)}</h1>
    <p>{body}</p>
  </main>
</body>
</html>
'''


def sync_assets():
    """Publish assets at /assets while keeping /src/assets for older App Store links."""
    source_assets = SOURCE / 'assets'
    target_assets = ROOT / 'assets'
    if target_assets.exists():
        shutil.rmtree(target_assets)
    shutil.copytree(source_assets, target_assets)


def clean_legacy_publish_trees():
    for name in LEGACY_PUBLISH_DIRS:
        path = SOURCE / name
        if path.exists():
            shutil.rmtree(path)
    for name in ROOT_STUB_DIRS:
        path = ROOT / name
        if path.exists():
            shutil.rmtree(path)


def ensure_photo_folders():
    for project in PROJECTS:
        folder = SOURCE / 'assets' / 'images' / project['slug'] / 'photos'
        folder.mkdir(parents=True, exist_ok=True)
        keep = folder / '.gitkeep'
        if not any(folder.iterdir()) and not keep.exists():
            keep.write_text('', encoding='utf-8')


def write_legacy_stubs(paths):
    for old, new, lang in paths:
        write(output_file(old), redirect_document(new, lang))


def legacy_stub_paths():
    stubs = []
    for lang in ('en', 'de'):
        stubs.append(('/src/' if lang == 'en' else '/src/de/', localized_url('/', lang), lang))
        stubs.append((
            '/src/error-page.html' if lang == 'en' else '/src/de/error-page.html',
            localized_url('/error-page.html', lang),
            lang,
        ))
        for path in (
            '/about/', '/legal/', '/legal/imprint/', '/legal/privacy/', '/legal/terms/',
            '/Support/', '/apps/',
        ):
            new = localized_url(path, lang)
            stubs.append(('/src' + new, new, lang))
        # Old /projects URLs and their /src copies point at /apps.
        stubs.append((localized_url('/projects/', lang), localized_url('/apps/', lang), lang))
        stubs.append(('/src' + localized_url('/projects/', lang), localized_url('/apps/', lang), lang))
        for project in local_projects():
            new = localized_url('/apps/' + project['slug'] + '/', lang)
            old_projects = localized_url('/projects/' + project['slug'] + '/', lang)
            stubs.append(('/src' + new, new, lang))
            stubs.append((old_projects, new, lang))
            stubs.append(('/src' + old_projects, new, lang))
    for project in local_projects():
        slug = project['slug']
        stubs.append((f'/soft/{slug}/', f'/apps/{slug}/', 'en'))
        stubs.append((f'/soft/privacy-{slug}/', '/legal/privacy/', 'en'))
        stubs.append((f'/soft/terms-{slug}/', '/legal/terms/', 'en'))
        stubs.append((f'/soft/support-{slug}/', f'/Support/#{slug}', 'en'))
    return stubs


def redirects():
    """Keep old /src, /soft, /projects and legal links working on Apache and Netlify."""
    mapping = {
        '/Impressum': '/legal/imprint/',
        '/Privacy': '/legal/privacy/',
        '/Terms': '/legal/terms/',
        '/legal/impressum': '/legal/imprint/',
        '/blog': SITE.get('blog_url') or 'https://medium.com/@sgroiga',
    }
    for project in local_projects():
        slug = project['slug']
        mapping[f'/soft/{slug}'] = f'/apps/{slug}/'
        mapping[f'/soft/privacy-{slug}'] = '/legal/privacy/'
        mapping[f'/soft/terms-{slug}'] = '/legal/terms/'
        mapping[f'/soft/support-{slug}'] = f'/Support/#{slug}'

    apache = [
        '# Generated by scripts/build.py. Permanent redirects for legacy and /src URLs.',
        '<IfModule mod_alias.c>',
    ]
    netlify = ['# Generated by scripts/build.py. Legacy and /src redirects.']
    for old, target in mapping.items():
        apache.append(f'RedirectMatch 301 ^{re.escape(old)}(?:\\.html|/)?$ {target}')
        for suffix in ('', '.html', '/'):
            netlify.append(f'{old}{suffix} {target} 301')

    # Former /projects collection now lives under /apps.
    apache.append(r'RedirectMatch 301 ^/projects(/.*)?$ /apps$1')
    netlify.append('/projects /apps/ 301')
    netlify.append('/projects/* /apps/:splat 301')

    # Strip the historical /src prefix for pages and assets.
    apache.append(r'RedirectMatch 301 ^/src/(.*)$ /$1')
    netlify.append('/src/* /:splat 301')
    netlify.append('/src / 301')

    apache.append('</IfModule>')
    apache.append('ErrorDocument 404 /error-page.html')
    netlify.append('/* /error-page.html 404')
    write('.htaccess', '\n'.join(apache) + '\n')
    write('_redirects', '\n'.join(netlify) + '\n')


def write_seo_files():
    write('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n')
    urls = []
    for path in SITEMAP_PATHS:
        loc = ORIGIN + (path if path != '/' else '/')
        urls.append(
            '  <url>\n'
            f'    <loc>{escape(loc)}</loc>\n'
            '  </url>'
        )
    write(
        'sitemap.xml',
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(urls)
        + '\n</urlset>\n',
    )


def load_support_overrides():
    if not SUPPORT_OVERRIDES_PATH.exists():
        return []
    try:
        rows = json.loads(SUPPORT_OVERRIDES_PATH.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print('Warning: support overrides unreadable:', error)
        return []
    return rows if isinstance(rows, list) else []


def merge_support_articles(remote_rows, overrides):
    if not overrides:
        return remote_rows
    overridden = {
        str(row.get('application') or '').strip().casefold()
        for row in overrides
        if str(row.get('application') or '').strip()
    }
    merged = [
        row for row in remote_rows
        if str(row.get('application') or '').strip().casefold() not in overridden
    ]
    merged.extend(overrides)
    print(f'Applied {len(overrides)} local support override(s) for: {", ".join(sorted(overridden)) or "none"}')
    return merged


def load_support_articles():
    remote = []
    if not SUPPORT_FEED:
        print('Warning: no support_feed in site.json; support articles skipped.')
    else:
        try:
            remote = fetch_support_rows(SUPPORT_FEED)
            print(f'Loaded {len(remote)} support article(s) from AppBackend.')
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
            print('Warning: support feed unavailable:', error)
    return merge_support_articles(remote, load_support_overrides())


def build():
    SITEMAP_PATHS.clear()
    ensure_photo_folders()
    sync_assets()
    clean_legacy_publish_trees()
    articles = load_support_articles()
    routes = [
        ('about', '/about/', 'about_title', 'about_desc'),
        ('legal', '/legal/', 'legal_title', 'legal_desc'),
        ('imprint', '/legal/imprint/', 'imprint_title', 'imprint_desc'),
        ('privacy', '/legal/privacy/', 'privacy_title', 'privacy_desc'),
        ('terms', '/legal/terms/', 'terms_title', 'terms_desc'),
        ('support', '/Support/', 'support_title', 'support_desc'),
        ('apps', '/apps/', 'apps_title', 'apps_desc'),
    ]
    for lang in ('en', 'de'):
        copy = I18N[lang]
        root = locale_root(lang)
        home = locale_home(lang)
        support_ui = escape(json.dumps({
            'answers_empty': copy['answers_empty'],
            'answers_send': copy['answers_send'],
            'answers_mention': copy['answers_mention'],
        }, ensure_ascii=False, separators=(',', ':')), quote=True)
        values = {
            'latest_cards': latest_cards(lang, root, copy),
            'project_cards': project_cards(lang, root, copy),
            'project_tiles': project_tiles(root),
            'contact_email': escape(SITE['email']),
            'contact_phone': escape(phone_display()),
            'contact_phone_href': escape(phone_href(), quote=True),
            'support_cards': dollar(support_cards(lang)),
            'support_articles': dollar(support_articles_html(articles, copy)),
            'support_feed': escape(SUPPORT_FEED, quote=True),
            'support_apps': escape(json.dumps(
                [{'slug': p['slug'], 'name': p['name']} for p in local_projects()],
                separators=(',', ':'),
            ), quote=True),
            'support_overrides': escape(json.dumps(
                load_support_overrides(),
                ensure_ascii=False,
                separators=(',', ':'),
            ), quote=True),
            'support_ui': dollar(support_ui),
            'root': root, 'home': home,
            'assets': ASSETS,
            'error_home': escape(copy['error_home']),
            'nav_projects': escape(copy['nav_projects']),
            'social_label': escape(copy['social_label']),
        }
        home_html = Template(page_source('home', lang).read_text()).substitute(values)
        page('/', copy['home_title'], copy['home_desc'], home_html, lang, LOGO)
        error_source = page_source('error', lang)
        if error_source.exists():
            page(
                '/error-page.html',
                copy['error_title'] + ' — Gabriel Sgroi',
                copy['error_desc'],
                Template(error_source.read_text()).substitute(values),
                lang,
                LOGO,
            )
        for name, path, title_key, desc_key in routes:
            source = page_source(name, lang)
            if source.exists():
                image = '/assets/images/aboutme.jpg' if name == 'about' else None
                page(
                    path,
                    copy[title_key] + ' — Gabriel Sgroi',
                    copy[desc_key],
                    Template(source.read_text()).substitute(values),
                    lang,
                    image,
                )
        for project in local_projects():
            source = page_source(project['slug'], lang)
            if source.exists():
                gallery = product_gallery_html(project, lang)
                project_values = dict(
                    values,
                    product_icon=icon(project),
                    product_gallery=dollar(gallery),
                    learn_more_href='#preview' if gallery else '#features',
                )
                store_url = project['app_store_url']
                project_values['store_action'] = (
                    f'<a class="button" href="{escape(store_url, quote=True)}" rel="noopener">{escape(copy["store_download"])}</a>'
                    if store_url else
                    f'<a class="button" href="{root}/apps/">{escape(copy["store_available"])} <span aria-hidden="true">↗</span></a>'
                )
                page(
                    '/apps/' + project['slug'] + '/',
                    project['name'] + ' — Gabriel Sgroi',
                    text_for(project, lang, 'description'),
                    Template(source.read_text()).substitute(project_values),
                    lang,
                    project['icon'],
                )
    write_legacy_stubs(legacy_stub_paths())
    redirects()
    write_seo_files()
    print('Static pages, /src stubs, assets and SEO files built.')


if __name__ == '__main__':
    build()
