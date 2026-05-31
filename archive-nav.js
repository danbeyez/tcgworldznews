// ============================================================
// archive-nav.js — Script partagé : barre d'archives + onglets
// Fonctionne depuis la racine (index.html) ET depuis archives/
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

// ---- Dropdown archives ----

function toggleArchive(e) {
  e.stopPropagation();
  document.getElementById('archiveBtn').classList.toggle('open');
  document.getElementById('archiveMenu').classList.toggle('open');
}

document.addEventListener('click', e => {
  const dd = document.querySelector('.archive-dropdown');
  if (dd && !dd.contains(e.target)) {
    document.getElementById('archiveBtn').classList.remove('open');
    document.getElementById('archiveMenu').classList.remove('open');
  }
});

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

async function loadArchives() {
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
    document.getElementById('weeklyList').innerHTML = '<div class="dropdown-empty">Manifest non disponible</div>';
  }
}

// ---- Navigation par onglets ----

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
  const pages = document.querySelectorAll('.page');
  const active = document.querySelector('.page.active');
  const idx = Array.from(pages).indexOf(active);
  if (e.key === 'ArrowRight' && idx < pages.length - 1) go(idx + 1);
  if (e.key === 'ArrowLeft' && idx > 0) go(idx - 1);
});

loadArchives();
