# TCG World'z — Weekly Pulse Site

Site statique hébergeant la veille hebdomadaire TCG World'z (Weekly Pulse) et, à venir, les Monthly Insights.

Hébergé sur **GitHub Pages**.

---

## Structure du repo

```
tcgworldz-pulse/
├── index.html                          ← édition actuelle (page d'accueil)
├── archives.html                       ← page listant toutes les archives
├── manifest.json                       ← source de vérité des éditions disponibles
├── update_manifest.py                  ← script Python d'automatisation
├── README.md                           ← ce fichier
└── archives/
    ├── semaine_19_mai_2026.html
    ├── semaine_20_mai_2026.html
    └── semaine_21_mai_2026.html        ← copie miroir de l'édition courante
```

### Logique de fonctionnement

- **`index.html`** est TOUJOURS la dernière édition publiée. Quand une nouvelle semaine sort, son contenu est copié ici (en plus d'être archivé).
- **`archives/`** contient une copie de chaque édition jamais publiée, nommée `semaine_<XX>_<mois>_<annee>.html`. Ces fichiers sont accessibles par URL directe et restent valides indéfiniment.
- **`manifest.json`** est la liste de toutes les éditions disponibles. Le dropdown en haut de page lit ce fichier pour afficher les 6 plus récentes ; la page `archives.html` lit ce fichier pour afficher la liste complète.
- **`archives.html`** est la page "voir plus" qui affiche toutes les éditions classées par mois.

---

## Publier une nouvelle édition (manuel)

Étapes à faire à chaque publication d'un nouveau Weekly Pulse :

### 1. Générer le HTML de la nouvelle semaine
Utilise Claude / la skill `tcg-analytics-master`. Tu obtiens un fichier `index.html` (la nouvelle édition).

### 2. L'archiver
Renomme le fichier en respectant la convention `semaine_<XX>_<mois>_<annee>.html` (numéro de semaine sur 2 chiffres, mois en minuscules sans accent) et place-le dans `archives/`.

Exemple : `semaine_22_mai_2026.html`

### 3. Mettre à jour `manifest.json`
Ajoute une entrée en haut du tableau `weekly_pulses` :

```json
{
  "id": "semaine_22_mai_2026",
  "label": "S22 · Mai 2026",
  "date": "2026-05-31",
  "date_label": "Semaine du 25 au 31 mai 2026",
  "file": "archives/semaine_22_mai_2026.html",
  "highlight": "Phrase teaser de 1 ligne sur le fait marquant."
}
```

Puis change la clé `"latest"` pour pointer sur le nouvel `id`.

### 4. Mettre à jour `index.html`
Copie le contenu de `archives/semaine_22_mai_2026.html` dans `index.html`, en ajustant :
- `const CURRENT_WEEK_ID = "semaine_22_mai_2026"` dans le `<script>` du dropdown
- Les chemins `'../manifest.json'` → `'manifest.json'`
- Les chemins `href="../archives.html"` → `href="archives.html"`
- Les balises `<title>` et `<meta og:title>` / `og:description`

### 5. Commit & push
```bash
git add archives/semaine_22_mai_2026.html manifest.json index.html
git commit -m "📰 Publication S22 · Mai 2026"
git push
```

Le site se met à jour automatiquement sur GitHub Pages (compter ~1 minute).

---

## Publier une nouvelle édition (automatique via Python)

Le script `update_manifest.py` automatise toutes les étapes 2 à 4.

```bash
python update_manifest.py /chemin/vers/nouvelle_semaine.html \
    --highlight "Phrase teaser sur le fait marquant de la semaine."
```

Le script :
1. Extrait automatiquement le numéro de semaine, le mois et l'année depuis le `<title>` du HTML source
2. Génère le nom de fichier `semaine_<XX>_<mois>_<annee>.html`
3. Copie le fichier dans `archives/` (avec chemins ajustés)
4. Met à jour `manifest.json`
5. Met à jour `index.html` (CURRENT_WEEK_ID + meta tags)

Options utiles :
- `--dry-run` : simule sans rien écrire
- `--force` : écrase une édition déjà publiée
- `--repo-root <chemin>` : si tu lances le script depuis un autre dossier

Après exécution, faire le `git add / commit / push` manuellement (le script ne touche pas à git).

---

## Pipeline GitHub Actions (à venir)

Le script Python est conçu pour être appelé depuis un GitHub Actions. Workflow type :

```yaml
# .github/workflows/publish-pulse.yml (exemple)
on:
  workflow_dispatch:
    inputs:
      source_url:
        description: "URL du HTML généré par Claude (Gist ou autre)"
        required: true
      highlight:
        description: "Teaser du fait marquant"
        required: true

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: curl -L "${{ inputs.source_url }}" -o /tmp/new_pulse.html
      - run: python update_manifest.py /tmp/new_pulse.html --highlight "${{ inputs.highlight }}"
      - run: |
          git config user.name "TCG World'z Bot"
          git config user.email "bot@tcgworldz.com"
          git add archives/ manifest.json index.html
          git commit -m "📰 Publication automatique"
          git push
```

---

## Convention de nommage

- **Fichiers de semaine** : `semaine_<XX>_<mois>_<annee>.html`
  - Numéro de semaine ISO sur 2 chiffres (`01` à `53`)
  - Mois en minuscules, sans accent (`janvier`, `fevrier`, `mars`...)
  - Année sur 4 chiffres
  - Exemples : `semaine_21_mai_2026.html`, `semaine_03_janvier_2027.html`
- **Fichiers d'analyse mensuelle** (à venir) : `mois_<MM>_<mois>_<annee>.html`
  - Exemple : `mois_05_mai_2026.html`

---

## Format `manifest.json`

```json
{
  "site": { ... },                       // métadonnées générales
  "latest": "<id_dernière_édition>",     // ID de l'édition à afficher en index.html
  "weekly_pulses": [ ... ],              // liste des Weekly Pulse, triée par date desc
  "monthly_insights": [ ... ]            // liste des Monthly Insight (vide pour l'instant)
}
```

Chaque entrée a la structure :

```json
{
  "id": "semaine_21_mai_2026",            // unique, sans espace, ASCII
  "label": "S21 · Mai 2026",              // affiché dans le dropdown
  "date": "2026-05-24",                   // ISO 8601, utilisé pour tri
  "date_label": "Semaine du 18 au 24 mai 2026",  // affiché à côté du label
  "file": "archives/semaine_21_mai_2026.html",   // chemin relatif depuis la racine
  "highlight": "..."                      // teaser sur la page archives.html
}
```

---

## Limites connues

- L'aperçu Open Graph (Discord / Twitter / Slack) ne reflète que l'édition courante (`index.html`), pas les archives individuelles. Si tu partages le lien d'une vieille semaine, l'aperçu sera générique.
- La rotation à 6 éditions dans le dropdown est en dur dans le JS (`slice(0,6)`). Si tu veux changer, modifie cette valeur dans `index.html`.
- Le script Python ne gère pas encore les Monthly Insights (typedef en place mais publication non implémentée).

---

*Documentation maintenue par l'équipe TCG World'z. Dernière mise à jour : 24 mai 2026.*
