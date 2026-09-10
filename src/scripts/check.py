#!/usr/bin/env python3
"""Check generated HTML structure, local assets, links, and fragment targets."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

_SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = _SCRIPT_DIR.parents[1] if _SCRIPT_DIR.parent.name == 'src' else _SCRIPT_DIR.parent
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
SKIP = {('src', 'pages'), ('src', 'templates'), ('src', 'data')}


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids = []
        self.links = []
        self.stack = []
        self.errors = []
        self.headings = 0
        self.redirect = False
        self.feed(path.read_text())
        if self.stack:
            self.errors.append('Unclosed tags: ' + ', '.join(self.stack))
        if not self.redirect and self.headings != 1:
            self.errors.append(f'Expected one h1, found {self.headings}')
        for identifier, count in Counter(self.ids).items():
            if count > 1:
                self.errors.append('Duplicate id: ' + identifier)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag not in VOID:
            self.stack.append(tag)
        if tag == 'h1':
            self.headings += 1
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'refresh':
            self.redirect = True
            if 'url=' in attrs.get('content', '').lower():
                self.links.append(attrs['content'].split('url=', 1)[1])
        if tag == 'meta' and attrs.get('name', '').lower() == 'robots' and 'noindex' in attrs.get('content', '').lower():
            self.redirect = True
        if not self.redirect:
            if tag == 'style' or 'style' in attrs or any(key.startswith('on') for key in attrs):
                self.errors.append('Inline style or event handler found')
            if tag == 'script' and not attrs.get('src'):
                self.errors.append('Inline script found')
        if tag == 'img' and 'alt' not in attrs:
            self.errors.append('Image has no alt attribute')
        for attr in ('href', 'src', 'poster'):
            if attrs.get(attr):
                self.links.append(attrs[attr])

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append('Mismatched closing tag: ' + tag)
        else:
            self.stack.pop()


def is_generated(path):
    rel = path.relative_to(ROOT)
    if rel.parts[:2] in SKIP:
        return False
    text = path.read_text(encoding='utf-8')[:24].lstrip().lower()
    return text.startswith('<!doctype')


def main():
    paths = [p for p in ROOT.rglob('*.html') if is_generated(p)]
    pages = {p: Page(p) for p in paths}
    errors = []
    links = 0
    for path, page in pages.items():
        name = '/' + path.relative_to(ROOT).as_posix()
        errors.extend(f'{name}: {error}' for error in page.errors)
        for raw in page.links:
            if urlsplit(raw).scheme or raw.startswith('//'):
                continue
            links += 1
            url = urlsplit(urljoin(name, raw))
            target = ROOT / unquote(url.path).lstrip('/')
            if target.is_dir():
                target /= 'index.html'
            if not target.is_file():
                errors.append(f'{name}: missing target {raw}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f'{name}: missing fragment {raw}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'OK: {len(pages)} HTML pages; {links} local links, assets and redirect targets; balanced HTML; separate CSS and JavaScript.')


if __name__ == '__main__':
    main()
