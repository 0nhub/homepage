/* Progressive enhancement only. Navigation, content and answers work without JS. */
document.documentElement.classList.add('js');

const toggle = document.querySelector('.menu-toggle');
const panel = document.querySelector('#header-panel');

if (toggle && panel) {
  const closeMenu = () => {
    toggle.setAttribute('aria-expanded', 'false');
    panel.classList.remove('is-open');
  };

  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(expanded));
    panel.classList.toggle('is-open', expanded);
  });

  panel.addEventListener('click', (event) => {
    if (event.target.closest('a')) closeMenu();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      closeMenu();
      toggle.focus();
    }
  });

  matchMedia('(min-width: 641px)').addEventListener('change', closeMenu);
}

const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

const publicImageUrl = (value) => {
  try {
    const url = new URL(String(value));
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : '';
  } catch {
    return '';
  }
};

const bindGalleryControls = (gallery) => {
  const section = gallery.closest('.product-gallery-section');
  const previous = section?.querySelector('[data-gallery-prev]');
  const next = section?.querySelector('[data-gallery-next]');
  const cards = () => Array.from(gallery.querySelectorAll('.media-card'));
  let index = 0;
  const render = (nextIndex, animate = true) => {
    const total = cards().length;
    if (!total) return;
    index = (nextIndex + total) % total;
    gallery.style.setProperty('--gallery-index', String(index));
    gallery.classList.toggle('is-animating', animate && !matchMedia('(prefers-reduced-motion: reduce)').matches);
  };
  previous?.addEventListener('click', () => render(index - 1));
  next?.addEventListener('click', () => render(index + 1));
  let pointerId = null;
  let startX = 0;
  let dragged = false;
  gallery.addEventListener('pointerdown', (event) => {
    if (event.pointerType !== 'mouse' || event.button !== 0) return;
    pointerId = event.pointerId;
    startX = event.clientX;
    dragged = false;
    gallery.setPointerCapture(event.pointerId);
    gallery.classList.add('is-dragging');
  });
  gallery.addEventListener('pointermove', (event) => {
    if (pointerId !== event.pointerId) return;
    if (Math.abs(event.clientX - startX) > 8) dragged = true;
  });
  const endDrag = (event) => {
    if (pointerId !== event.pointerId) return;
    const delta = event.clientX - startX;
    pointerId = null;
    gallery.classList.remove('is-dragging');
    if (Math.abs(delta) > 40) render(index + (delta < 0 ? 1 : -1));
  };
  gallery.addEventListener('pointerup', endDrag);
  gallery.addEventListener('pointercancel', endDrag);
  gallery.addEventListener('click', (event) => { if (dragged) event.preventDefault(); }, true);
  window.addEventListener('resize', () => render(index, false), { passive: true });
  render(0, false);
  return () => render(index, false);
};

const fetchFeedRows = async (endpoint) => {
  const rows = [];
  let page = 1;
  while (page <= 20) {
    const separator = endpoint.includes('?') ? '&' : '?';
    const response = await fetch(`${endpoint}${separator}page=${page}&limit=100`, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) throw new Error(`gallery feed ${response.status}`);
    const payload = await response.json();
    const batch = Array.isArray(payload.data) ? payload.data : [];
    rows.push(...batch);
    const total = Number(payload.count) || 0;
    if (!batch.length || rows.length >= total) break;
    page += 1;
  }
  return rows;
};

document.querySelectorAll('.product-gallery-section').forEach((gallerySection) => {
  const gallery = gallerySection.querySelector('.media-gallery');
  if (gallery && !gallerySection.hasAttribute('data-gallery-feed')) {
    bindGalleryControls(gallery);
  }
});

document.querySelectorAll('[data-case-carousel]').forEach((carousel) => {
  const track = carousel.querySelector('.case-carousel__track');
  const cards = Array.from(carousel.querySelectorAll('.case-card'));
  const dots = carousel.querySelector('.case-carousel__dots');
  const previous = carousel.querySelector('[data-case-prev]');
  const next = carousel.querySelector('[data-case-next]');
  let index = 0;
  const visibleCards = () => matchMedia('(min-width: 600px)').matches ? 2 : 1;
  const render = (nextIndex, animate = true) => {
    const count = Math.max(1, cards.length - visibleCards() + 1);
    index = (nextIndex + count) % count;
    track?.style.setProperty('--case-index', String(index));
    track?.classList.toggle('is-animating', animate && !matchMedia('(prefers-reduced-motion: reduce)').matches);
    dots?.querySelectorAll('button').forEach((dot, dotIndex) => {
      dot.classList.toggle('is-active', dotIndex === index);
      dot.setAttribute('aria-selected', String(dotIndex === index));
    });
  };
  const buildDots = () => {
    if (!dots) return;
    dots.innerHTML = '';
    for (let i = 0; i < Math.max(1, cards.length - visibleCards() + 1); i += 1) {
      const dot = document.createElement('button');
      dot.type = 'button'; dot.setAttribute('role', 'tab');
      dot.setAttribute('aria-label', `Show audience position ${i + 1}`);
      dot.addEventListener('click', () => render(i));
      dots.appendChild(dot);
    }
  };
  previous?.addEventListener('click', () => render(index - 1));
  next?.addEventListener('click', () => render(index + 1));
  window.addEventListener('resize', () => { buildDots(); render(index, false); }, { passive: true });
  buildDots(); render(0, false);
});

const gallerySection = document.querySelector('[data-gallery-feed]');
if (gallerySection) {
  const gallery = gallerySection.querySelector('.media-gallery');
  const feed = gallerySection.getAttribute('data-gallery-feed') || '';
  const appSlug = (gallerySection.getAttribute('data-gallery-app') || '').trim().toLowerCase();
  const altPrefix = gallerySection.getAttribute('data-gallery-alt-prefix') || 'Screenshot';
  const finishEmpty = () => {
    gallerySection.classList.remove('is-loading');
    gallerySection.classList.add('is-empty');
  };

  if (gallery && feed && appSlug) {
    const updateControls = bindGalleryControls(gallery);
    fetchFeedRows(feed)
      .then((rows) => {
        const items = rows
          .filter((row) => String(row.app || '').trim().toLowerCase() === appSlug)
          .map((row) => ({
            image: publicImageUrl(row.image),
            position: row.position,
          }))
          .filter((item) => item.image)
          .sort((a, b) => {
            const aPos = a.position === null || a.position === '' || Number.isNaN(Number(a.position))
              ? Number.POSITIVE_INFINITY
              : Number(a.position);
            const bPos = b.position === null || b.position === '' || Number.isNaN(Number(b.position))
              ? Number.POSITIVE_INFINITY
              : Number(b.position);
            return aPos - bPos;
          });

        if (!items.length) {
          finishEmpty();
          return;
        }

        gallery.innerHTML = items.map((item, index) => {
          const alt = escapeHtml(`${altPrefix} ${index + 1}`);
          const lazy = index === 0 ? '' : ' loading="lazy"';
          return `<figure class="media-card"><img src="${escapeHtml(item.image)}" alt="${alt}" draggable="false"${lazy} width="720" height="450"></figure>`;
        }).join('');

        gallerySection.classList.remove('is-loading', 'is-empty');
        updateControls();
      })
      .catch(() => finishEmpty());
  } else {
    finishEmpty();
  }
}

const supportFeed = document.querySelector('[data-support-feed]');

const showSupportApp = () => {
  const id = decodeURIComponent((location.hash || '').replace('#', ''));
  document.querySelectorAll('.answer-group').forEach((el) => {
    el.classList.toggle('is-open', Boolean(id) && el.id === id);
  });
  document.querySelectorAll('[data-support-app]').forEach((el) => {
    const selected = el.getAttribute('data-support-app') === id;
    el.classList.toggle('is-selected', selected);
    if (selected) el.setAttribute('aria-current', 'true');
    else el.removeAttribute('aria-current');
  });
};

window.addEventListener('hashchange', showSupportApp);
showSupportApp();

const supportAnswers = document.querySelector('.support-answers');
if (supportAnswers) {
  supportAnswers.addEventListener('toggle', (event) => {
    const opened = event.target;
    if (!(opened instanceof HTMLDetailsElement) || !opened.open) return;
    supportAnswers.querySelectorAll('details[open]').forEach((item) => {
      if (item !== opened) item.open = false;
    });
  }, true);
}

const supportSearch = document.querySelector('[data-support-search]');
if (supportSearch && supportAnswers) {
  supportSearch.addEventListener('input', () => {
    const query = supportSearch.value.trim().toLocaleLowerCase();
    supportAnswers.querySelectorAll('.answer-group details').forEach((article) => {
      article.hidden = Boolean(query) && !article.textContent.toLocaleLowerCase().includes(query);
    });
  });
}

if (supportFeed && supportFeed.getAttribute('data-support-feed')) {
  const paragraphs = (text) => String(text || '')
    .split(/\n{2,}/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => `<p>${escapeHtml(chunk).replace(/\n/g, '<br>')}</p>`)
    .join('');

  const matchApp = (label, apps) => {
    const key = String(label || '').trim().toLowerCase();
    return apps.find((app) => app.name.toLowerCase() === key || app.slug.toLowerCase() === key) || null;
  };

  const sectionId = (label, app, taken) => {
    if (app) return app.slug;
    const slug = String(label || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    if (!slug || taken.has(slug)) return slug ? `topic-${slug}` : 'general';
    return slug;
  };

  const articleHtml = (row) => {
    const title = String(row.name || '').trim() || 'Untitled';
    const image = publicImageUrl(row.attachment);
    const figure = image
      ? `<figure class="answer-screenshot"><img src="${escapeHtml(image)}" alt="${escapeHtml(title)}" loading="lazy"></figure>`
      : '';
    return `<details name="support-answers"><summary>${escapeHtml(title)}</summary><div>${paragraphs(row.content)}${figure}</div></details>`;
  };

  const ui = JSON.parse(supportFeed.getAttribute('data-support-ui') || '{}');
  const emptyLead = ui.answers_empty || 'No answers yet.';
  const send = ui.answers_send || 'Send a question';
  const mention = ui.answers_mention || 'and mention the app name.';

  const render = (rows, apps, email) => {
    const grouped = new Map();
    rows.forEach((row) => {
      const app = matchApp(row.application, apps);
      const label = app ? app.name : (String(row.application || '').trim() || 'General');
      if (!grouped.has(label)) grouped.set(label, []);
      grouped.get(label).push(row);
    });
    grouped.forEach((items) => {
      items.sort((a, b) => {
        const aPos = a.age === null || a.age === '' || Number.isNaN(Number(a.age)) ? Number.POSITIVE_INFINITY : Number(a.age);
        const bPos = b.age === null || b.age === '' || Number.isNaN(Number(b.age)) ? Number.POSITIVE_INFINITY : Number(b.age);
        return aPos - bPos || String(a.name || '').localeCompare(String(b.name || ''), undefined, { sensitivity: 'base' });
      });
    });

    const taken = new Set(apps.map((app) => app.slug));
    const ordered = apps.map((app) => [app.name, app]);
    grouped.forEach((_items, label) => {
      if (!apps.some((app) => app.name.toLowerCase() === label.toLowerCase() || app.slug.toLowerCase() === label.toLowerCase())) {
        ordered.push([label, matchApp(label, apps)]);
      }
    });

    const safeEmail = escapeHtml(email);
    return ordered.map(([label, app]) => {
      const items = grouped.get(label) || [];
      const identifier = sectionId(label, app, taken);
      const titleId = `answers-title-${identifier}`;
      const heading = escapeHtml(app ? app.name : label);
      if (items.length) {
        return `<section class="answer-group" id="${escapeHtml(identifier)}" aria-labelledby="${titleId}"><h2 id="${titleId}">${heading}</h2>${items.map(articleHtml).join('')}</section>`;
      }
      const subject = encodeURIComponent(`${app ? app.name : label} Support`);
      return `<section class="answer-group" id="${escapeHtml(identifier)}" aria-labelledby="${titleId}"><h2 id="${titleId}">${heading}</h2><p class="answers-empty">${escapeHtml(emptyLead)} <a href="mailto:${safeEmail}?subject=${subject}">${escapeHtml(send)}</a> ${escapeHtml(mention)}</p></section>`;
    }).join('');
  };

  if (supportFeed.hasAttribute('data-static-support')) {
    fetch(`${supportFeed.getAttribute('data-support-feed')}${supportFeed.getAttribute('data-support-feed').includes('?') ? '&' : '?'}limit=100`)
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((payload) => {
        let rows = Array.isArray(payload.data) ? payload.data : [];
      try {
        const overrides = JSON.parse(supportFeed.getAttribute('data-support-overrides') || '[]');
        if (Array.isArray(overrides) && overrides.length) {
          const overridden = new Set(
            overrides
              .map((row) => String(row.application || '').trim().toLowerCase())
              .filter(Boolean),
          );
          rows = rows.filter((row) => !overridden.has(String(row.application || '').trim().toLowerCase()));
          rows = rows.concat(overrides);
        }
      } catch {
        // Keep remote rows if overrides cannot be parsed.
      }
      const apps = JSON.parse(supportFeed.getAttribute('data-support-apps') || '[]');
      supportFeed.innerHTML = render(rows, apps, supportFeed.getAttribute('data-support-email') || '');
        showSupportApp();
      })
      .catch(() => {});
  }
}
