// ============================================================
// archive-nav.js — Script partagé : barre d'archives + onglets
// Fonctionne depuis la racine (index.html, archives.html)
// ET depuis archives/ (semaine_XX.html)
//
// UTILISATION dans chaque page HTML :
//   <script>const CURRENT_WEEK_ID = "semaine_XX_mois_2026";</script>
//   <script src="archive-nav.js"></script>          ← depuis la racine
//   <script src="../archive-nav.js"></script>       ← depuis archives/
// ============================================================

// Détecte si la page est dans le dossier archives/
const _inArchives = /\/archives\//.test(window.location.pathname);
const _manifestUrl = _inArchives ? '../manifest.json' : 'manifest.json';
const _archivesPage = _inArchives ? '../archives.html' : 'archives.html';

// Détecte si on est sur la page archives.html (listing complet)
const _isArchivesPage = !!document.getElementById('weeklyContent');

// ================================================================
// FONCTIONS COMMUNES
// ================================================================

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

// ================================================================
// MODE DROPDOWN — pages d'édition (index.html, semaine_XX.html)
// ================================================================

function toggleArchive(e) {
  e.stopPropagation();
  document.getElementById('archiveBtn').classList.toggle('open');
  document.getElementById('archiveMenu').classList.toggle('open');
}

document.addEventListener('click', e => {
  const dd = document.querySelector('.archive-dropdown');
  if (dd && !dd.contains(e.target)) {
    const btn = document.getElementById('archiveBtn');
    const menu = document.getElementById('archiveMenu');
    if (btn) btn.classList.remove('open');
    if (menu) menu.classList.remove('open');
  }
});

async function loadArchives() {
  // Sur une page archive, corriger le label "Édition en cours"
  if (_inArchives) {
    const labelEl = document.querySelector('.archive-banner-current .label');
    if (labelEl) labelEl.textContent = 'Édition consultée';
  }

  // Corriger le lien "Voir toutes les archives" selon la position
  const footerLink = document.querySelector('.dropdown-footer a');
  if (footerLink) footerLink.href = _archivesPage;

  try {
    const res = await fetch(_manifestUrl, { cache: 'no-cache' });
    if (!res.ok) throw new Error('manifest.json introuvable');
    const data = await res.json();

    // Identifier l'édition courante (CURRENT_WEEK_ID défini dans la page)
    const currentId = typeof CURRENT_WEEK_ID !== 'undefined' ? CURRENT_WEEK_ID : '';

    // Mettre à jour le label "édition consultée"
    const currentEntry = (data.weekly_pulses || []).find(w => w.id === currentId)
                      || (data.weekly_pulses || [])[0];
    if (currentEntry) {
      const el = document.getElementById('currentEditionLabel');
      if (el) el.textContent = currentEntry.label;
    }

    // Weekly Pulse — 6 plus récents
    const weekly = (data.weekly_pulses || [])
      .slice()
      .sort((a, b) => (b.date || '').localeCompare(a.date || ''))
      .slice(0, 6);

    const wList = document.getElementById('weeklyList');
    if (weekly.length === 0) {
      wList.innerHTML = '<div class="dropdown-empty">Aucune édition disponible</div>';
    } else {
      wList.innerHTML = weekly.map(w => {
        if (w.id === currentId) {
          return `<div class="dropdown-item current">${escapeHtml(w.label)}</div>`;
        }
        // Chemin relatif selon la position :
        //   depuis archives/ → on retire le préfixe archives/
        //   depuis la racine → on garde le chemin complet (archives/semaine_XX.html)
        const f = _inArchives
          ? String(w.file || '').replace(/^archives\//, '')
          : String(w.file || '');
        return `<a class="dropdown-item" href="${escapeAttr(f)}">${escapeHtml(w.label)}<div class="dropdown-item-date">${escapeHtml(w.date_label || '')}</div></a>`;
      }).join('');
    }

    // Monthly Insight
    const monthly = (data.monthly_insights || [])
      .slice()
      .sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    const mList = document.getElementById('monthlyList');
    if (monthly.length === 0) {
      mList.innerHTML = '<div class="dropdown-empty">Bientôt disponible</div>';
    } else {
      mList.innerHTML = monthly.map(m => {
        const f = _inArchives
          ? String(m.file || '').replace(/^archives\//, '')
          : String(m.file || '');
        return `<a class="dropdown-item" href="${escapeAttr(f)}">${escapeHtml(m.label)}<div class="dropdown-item-date">${escapeHtml(m.date_label || '')}</div></a>`;
      }).join('');
    }
  } catch (err) {
    console.warn('Archive loading failed:', err);
    const wList = document.getElementById('weeklyList');
    if (wList) wList.innerHTML = '<div class="dropdown-empty">Manifest non disponible</div>';
  }
}

// ---- Navigation par onglets (pages d'édition) ----

function go(i) {
  const pages = document.querySelectorAll('.page');
  const tabs = document.querySelectorAll('.tab');
  pages.forEach(p => p.classList.remove('active'));
  tabs.forEach(t => t.classList.remove('active'));
  if (pages[i] && tabs[i]) {
    pages[i].classList.add('active');
    tabs[i].classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

document.addEventListener('keydown', e => {
  if (_isArchivesPage) return;
  const pages = document.querySelectorAll('.page');
  const active = document.querySelector('.page.active');
  const idx = Array.from(pages).indexOf(active);
  if (e.key === 'ArrowRight' && idx < pages.length - 1) go(idx + 1);
  if (e.key === 'ArrowLeft' && idx > 0) go(idx - 1);
});

// ================================================================
// MODE LISTING — page archives.html
// ================================================================

const _MONTHS_FR = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];

function switchTab(name, btn) {
  document.querySelectorAll('.archive-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.archive-section').forEach(s => s.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(name + 'Section').classList.add('active');
}

function _groupByMonth(items) {
  const groups = {};
  items.forEach(it => {
    const d = it.date || '';
    const m = d.match(/^(\d{4})-(\d{2})/);
    if (!m) {
      (groups['__autres__'] = groups['__autres__'] || []).push(it);
      return;
    }
    const key = `${m[1]}-${m[2]}`;
    (groups[key] = groups[key] || []).push(it);
  });
  const sortedKeys = Object.keys(groups).sort((a, b) => b.localeCompare(a));
  return sortedKeys.map(k => {
    const [year, month] = k.split('-');
    const label = k === '__autres__' ? 'Autres' : `${_MONTHS_FR[parseInt(month, 10) - 1]} ${year}`;
    const list = groups[k].sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    return { key: k, label, items: list };
  });
}

function _renderArchiveList(containerId, items, kind) {
  const c = document.getElementById(containerId);
  if (!items || items.length === 0) {
    c.innerHTML = `<div class="empty-state"><div class="icon">${kind === 'weekly' ? '📅' : '📊'}</div><div class="title">${kind === 'weekly' ? 'Aucune édition pour le moment' : 'Bientôt disponible'}</div><div class="sub">${kind === 'weekly' ? 'Les éditions seront affichées ici une fois publiées.' : 'Les analyses mensuelles arriveront prochainement.'}</div></div>`;
    return;
  }
  const groups = _groupByMonth(items);
  c.innerHTML = groups.map(g => {
    const itemsHtml = g.items.map(it => `
      <a class="archive-item" href="${escapeAttr(it.file)}">
        <div class="archive-item-left">
          <div class="archive-item-label">${escapeHtml(it.label)}</div>
          <div class="archive-item-date">${escapeHtml(it.date_label || it.date || '')}</div>
          ${it.highlight ? `<div class="archive-item-highlight">${escapeHtml(it.highlight)}</div>` : ''}
        </div>
        <span class="archive-item-arrow">→</span>
      </a>`).join('');
    return `
      <div class="month-group">
        <h2 class="month-title">${escapeHtml(g.label)}<span class="count">${g.items.length} édition${g.items.length > 1 ? 's' : ''}</span></h2>
        <div class="archive-list">${itemsHtml}</div>
      </div>`;
  }).join('');
}

async function _loadArchivesPage() {
  try {
    const res = await fetch('manifest.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error('manifest.json introuvable');
    const data = await res.json();

    const weekly = data.weekly_pulses || [];
    const monthly = data.monthly_insights || [];
    document.getElementById('weeklyCount').textContent = weekly.length;
    document.getElementById('monthlyCount').textContent = monthly.length;

    _renderArchiveList('weeklyContent', weekly, 'weekly');
    _renderArchiveList('monthlyContent', monthly, 'monthly');
  } catch (err) {
    console.error('Archive loading failed:', err);
    document.getElementById('weeklyContent').innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><div class="title">Manifest non disponible</div><div class="sub">Le fichier manifest.json est introuvable. Vérifie qu\'il est bien à la racine du site.</div></div>';
  }
}

// ================================================================
// INITIALISATION — détecte le mode et lance le bon chargement
// ================================================================

if (_isArchivesPage) {
  _loadArchivesPage();
} else {
  loadArchives();
}
