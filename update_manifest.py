#!/usr/bin/env python3
"""
TCG World'z — Publication d'une nouvelle édition du Weekly Pulse.

Ce script automatise la publication d'une nouvelle semaine sur le site
(typiquement via GitHub Actions).

USAGE
-----
    python update_manifest.py <chemin_html_source> [--type weekly|monthly]
                              [--highlight "phrase teaser"]
                              [--repo-root .]
                              [--dry-run]

EXEMPLES
--------
    # Publication d'une nouvelle semaine
    python update_manifest.py /tmp/nouvelle_semaine.html --highlight "Banlist Konami : 3 cartes interdites le 18 mai."

    # Simulation (n'écrit rien)
    python update_manifest.py /tmp/nouvelle_semaine.html --dry-run

CE QUE FAIT LE SCRIPT
---------------------
1. Lit le HTML source et extrait : titre, semaine ISO, mois, année.
2. Génère le nom de fichier `semaine_XX_<mois>_<annee>.html`.
3. Copie le fichier dans `archives/`.
4. Met à jour `manifest.json` (ajoute l'entrée + change `latest`).
5. Met à jour `index.html` :
   - Remplace `CURRENT_WEEK_ID` dans le JS.
   - Met à jour la balise `og:title`, `og:description` et le `<title>`.
6. Recopie le contenu du HTML source dans `index.html`.

MODE BACKFILL (--backfill)
--------------------------
Pour ajouter une ancienne édition aux archives sans toucher index.html ni
modifier le champ `latest` du manifest. Utile pour intégrer des semaines
passées après coup.

    python update_manifest.py ancienne_semaine.html --backfill
    python update_manifest.py ancienne_semaine.html --backfill --highlight "Résumé de l'époque."

Les erreurs de validation sont des avertissements (pas bloquants) en mode
--backfill, car les anciens fichiers peuvent ne pas avoir la structure actuelle.

RÈGLE IMPORTANTE
----------------
Le script ne touche PAS aux semaines déjà présentes dans archives/.
Si une semaine est déjà publiée, le script échoue (sécurité anti-écrasement).
Utiliser --force pour écraser.

DÉPENDANCES
-----------
Aucune (stdlib uniquement). Python 3.8+.
"""

import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]
MONTHS_FR_ASCII = [
    "janvier", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
]


def extract_metadata_from_html(html_path: Path) -> dict:
    """
    Extrait les métadonnées d'un fichier HTML source du Weekly Pulse.

    Cherche dans cet ordre :
    1. Une balise <title> contenant "S<num>" et un mois
    2. Une balise <meta property="og:title"> idem
    3. Si introuvable → erreur explicite
    """
    content = html_path.read_text(encoding="utf-8")

    # Cherche dans <title>
    title_match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""

    # Cherche dans og:title si <title> n'aide pas
    og_match = re.search(
        r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        content, re.IGNORECASE,
    )
    og_title = og_match.group(1).strip() if og_match else ""

    text = f"{title} {og_title}"

    # Extraire le numéro de semaine (S21, S07, etc.)
    week_match = re.search(r"\bS(\d{1,2})\b", text)
    if not week_match:
        raise ValueError(
            f"Impossible d'extraire le numéro de semaine depuis {html_path}.\n"
            f"Le titre doit contenir un motif 'S<num>' (ex: 'S21'). Trouvé: {text!r}"
        )
    week_num = int(week_match.group(1))

    # Extraire le mois
    month_idx = None
    text_lower = text.lower()
    for idx, name in enumerate(MONTHS_FR):
        if name in text_lower:
            month_idx = idx
            break
    if month_idx is None:
        for idx, name in enumerate(MONTHS_FR_ASCII):
            if name in text_lower:
                month_idx = idx
                break
    if month_idx is None:
        raise ValueError(
            f"Impossible d'extraire le mois depuis {html_path}.\n"
            f"Le titre doit contenir un nom de mois français. Trouvé: {text!r}"
        )

    # Extraire l'année
    year_match = re.search(r"\b(20\d{2})\b", text)
    if not year_match:
        raise ValueError(
            f"Impossible d'extraire l'année depuis {html_path}.\n"
            f"Trouvé: {text!r}"
        )
    year = int(year_match.group(1))

    return {
        "week_num": week_num,
        "month_idx": month_idx,
        "month_fr": MONTHS_FR[month_idx],
        "month_fr_ascii": MONTHS_FR_ASCII[month_idx],
        "year": year,
    }


def iso_week_end_date(year: int, week_num: int) -> date:
    """
    Retourne la date du dimanche (fin de semaine ISO) pour une année + numéro de semaine.
    Convention ISO 8601 : la semaine commence un lundi.
    """
    # %G %V %u : année ISO, semaine ISO, jour 1-7 (1=lundi)
    return datetime.strptime(f"{year}-W{week_num:02d}-7", "%G-W%V-%u").date()


def iso_week_start_date(year: int, week_num: int) -> date:
    return datetime.strptime(f"{year}-W{week_num:02d}-1", "%G-W%V-%u").date()


def build_entry(meta: dict, file_name: str, highlight: str) -> dict:
    start = iso_week_start_date(meta["year"], meta["week_num"])
    end = iso_week_end_date(meta["year"], meta["week_num"])
    # Format date_label : "Semaine du 18 au 24 mai 2026"
    if start.month == end.month:
        date_label = f"Semaine du {start.day} au {end.day} {meta['month_fr']} {meta['year']}"
    else:
        date_label = (
            f"Semaine du {start.day} {MONTHS_FR[start.month-1]} "
            f"au {end.day} {meta['month_fr']} {meta['year']}"
        )

    entry_id = f"semaine_{meta['week_num']:02d}_{meta['month_fr_ascii']}_{meta['year']}"
    return {
        "id": entry_id,
        "label": f"S{meta['week_num']:02d} · {meta['month_fr'].capitalize()} {meta['year']}",
        "date": end.isoformat(),
        "date_label": date_label,
        "file": f"archives/{file_name}",
        "highlight": highlight or "",
    }


def update_index_html(index_path: Path, archive_html: str, new_week_id: str,
                       new_label: str, new_highlight: str) -> None:
    """
    Remplace le contenu de index.html par le HTML d'archive, en :
    - mettant à jour CURRENT_WEEK_ID dans le JS
    - mettant à jour <title>, og:title, og:description
    """
    content = archive_html

    # 1. CURRENT_WEEK_ID
    content = re.sub(
        r'(const\s+CURRENT_WEEK_ID\s*=\s*")[^"]*(")',
        rf'\1{new_week_id}\2',
        content,
        count=1,
    )
    

    # 2. <title>
    content = re.sub(
        r"(<title>).*?(</title>)",
        rf"\1TW News — Weekly Pulse {new_label} · TCG World'z\2",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # 3. og:title
    content = re.sub(
        r'(<meta\s+property=["\']og:title["\']\s+content=["\'])[^"\']*(["\'])',
        rf'\1TW News — Weekly Pulse {new_label}\2',
        content,
        count=1,
        flags=re.IGNORECASE,
    )

    # 4. og:description (seulement si highlight fourni)
    if new_highlight:
        content = re.sub(
            r'(<meta\s+property=["\']og:description["\']\s+content=["\'])[^"\']*(["\'])',
            rf'\1{new_highlight}\2',
            content,
            count=1,
            flags=re.IGNORECASE,
        )

    # 5. Ajuster les chemins de la version archives/ vers la racine
    # (../manifest.json → manifest.json, ../archives.html → archives.html)
    content = content.replace("'../manifest.json'", "'manifest.json'")
    content = content.replace('"../manifest.json"', '"manifest.json"')
    content = content.replace('href="../archives.html"', 'href="archives.html"')
    content = content.replace('src="../archive-nav.js"', 'src="archive-nav.js"')
    content = content.replace('href="../archive-nav.css"', 'href="archive-nav.css"')

    index_path.write_text(content, encoding="utf-8")


def prepare_archive_html(source_html: str) -> str:
    """
    Transforme un index.html (chemins racine) en version archives/ (chemins ../).
    """
    content = source_html
    # manifest.json → ../manifest.json
    content = content.replace("'manifest.json'", "'../manifest.json'")
    content = content.replace('"manifest.json"', '"../manifest.json"')
    # archives.html → ../archives.html
    content = content.replace('href="archives.html"', 'href="../archives.html"')
    # archive-nav.js → ../archive-nav.js
    content = content.replace('src="archive-nav.js"', 'src="../archive-nav.js"')
    content = content.replace('href="archive-nav.css"', 'href="../archive-nav.css"')
    return content


def main():
    parser = argparse.ArgumentParser(
        description="Publie une nouvelle édition du Weekly Pulse TCG World'z.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("source", type=Path, help="Fichier HTML source à publier.")
    parser.add_argument("--type", choices=["weekly", "monthly"], default="weekly",
                        help="Type de publication (défaut: weekly).")
    parser.add_argument("--highlight", default="",
                        help="Phrase teaser pour l'aperçu (fait marquant de la semaine).")
    parser.add_argument("--repo-root", type=Path, default=Path("."),
                        help="Racine du dépôt (défaut: dossier courant).")
    parser.add_argument("--backfill", action="store_true",
                        help="Ajoute une ancienne édition aux archives sans modifier index.html ni 'latest'.")
    parser.add_argument("--force", action="store_true",
                        help="Écrase une édition déjà publiée avec le même ID.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche ce qui serait fait sans rien écrire.")
    args = parser.parse_args()

    if args.type == "monthly":
        print("⚠️  Le type 'monthly' n'est pas encore implémenté.", file=sys.stderr)
        sys.exit(2)

    if not args.source.exists():
        print(f"❌ Fichier source introuvable: {args.source}", file=sys.stderr)
        sys.exit(1)

    repo_root = args.repo_root.resolve()
    archives_dir = repo_root / "archives"
    manifest_path = repo_root / "manifest.json"
    index_path = repo_root / "index.html"

    if not archives_dir.exists():
        print(f"❌ Dossier {archives_dir} introuvable. Cible incorrecte ?", file=sys.stderr)
        sys.exit(1)
    if not manifest_path.exists():
        print(f"❌ Fichier {manifest_path} introuvable.", file=sys.stderr)
        sys.exit(1)

    # 1. Extraction métadonnées
    meta = extract_metadata_from_html(args.source)
    print(f"📋 Métadonnées extraites:")
    print(f"   - Semaine: S{meta['week_num']:02d}")
    print(f"   - Mois: {meta['month_fr']} ({meta['year']})")

    # 2. Nom de fichier
    file_name = f"semaine_{meta['week_num']:02d}_{meta['month_fr_ascii']}_{meta['year']}.html"
    target_archive = archives_dir / file_name
    print(f"   - Fichier cible: archives/{file_name}")

    if target_archive.exists() and not args.force:
        print(f"❌ Le fichier {target_archive} existe déjà. Utilise --force pour écraser.",
              file=sys.stderr)
        sys.exit(1)

    # 3. Charger manifest et construire entrée
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = build_entry(meta, file_name, args.highlight)
    print(f"   - ID: {entry['id']}")
    print(f"   - Label: {entry['label']}")

    # 4. Lire source HTML
    source_html = args.source.read_text(encoding="utf-8")

    # Valider la structure du HTML source
    _errors = []
    if 'class="archive-banner"' not in source_html and "class='archive-banner'" not in source_html:
        _errors.append('Bannière d\'archives manquante (class="archive-banner")')
    if 'CURRENT_WEEK_ID' not in source_html:
        _errors.append('Déclaration CURRENT_WEEK_ID manquante dans le HTML source')
    if 'archive-nav.js' not in source_html:
        _errors.append('Référence à archive-nav.js manquante (script partagé)')
    if 'archive-nav.css' not in source_html:
        _errors.append('Lien vers archive-nav.css manquant (feuille de style)')
    if _errors:
        if args.backfill:
            print('⚠️  Structure non conforme (avertissement ignoré en mode --backfill) :', file=sys.stderr)
            for e in _errors:
                print(f'   • {e}', file=sys.stderr)
        else:
            print('❌ Le fichier source ne respecte pas la structure requise :', file=sys.stderr)
            for e in _errors:
                print(f'   • {e}', file=sys.stderr)
            print('   → Utilise actualitees/TEMPLATE.html comme base.', file=sys.stderr)
            sys.exit(1)

    # 5. Préparer version archives/ (chemins relatifs ajustés)
    archive_html = prepare_archive_html(source_html)

    if args.dry_run:
        print("\n🔍 DRY-RUN : aucune modification effective.")
        print(f"   - Aurait écrit : {target_archive}")
        print(f"   - Aurait mis à jour : {manifest_path}")
        if not args.backfill:
            print(f"   - Aurait copié vers : {index_path}")
        else:
            print(f"   - Mode backfill : index.html NON modifié, 'latest' NON changé")
        return

    # 6. Écrire fichier archive
    target_archive.write_text(archive_html, encoding="utf-8")
    print(f"✅ Archive écrite: {target_archive}")

    # 7. Mettre à jour manifest
    weekly_pulses = manifest.get("weekly_pulses", [])
    # Retirer une éventuelle entrée existante avec le même ID
    weekly_pulses = [w for w in weekly_pulses if w.get("id") != entry["id"]]
    weekly_pulses.append(entry)
    # Trier par date desc
    weekly_pulses.sort(key=lambda w: w.get("date", ""), reverse=True)
    manifest["weekly_pulses"] = weekly_pulses
    if not args.backfill:
        manifest["latest"] = entry["id"]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"✅ Manifest mis à jour ({len(weekly_pulses)} éditions au total)")

    # 8. Mettre à jour index.html (sauf en mode backfill)
    if not args.backfill:
        update_index_html(
            index_path,
            archive_html,
            entry["id"],
            entry["label"],
            entry.get("highlight", ""),
        )
        print(f"✅ Index.html mis à jour avec l'édition courante")
        print(f"\n🎉 Publication terminée. N'oublie pas de commit + push.")
        print(f"   git add archives/{file_name} manifest.json index.html")
        print(f"   git commit -m \"📰 Publication {entry['label']}\"")
        print(f"   git push")
    else:
        print(f"ℹ️  Mode backfill : index.html et 'latest' non modifiés.")
        print(f"\n🎉 Archive ajoutée. N'oublie pas de commit + push.")
        print(f"   git add archives/{file_name} manifest.json")
        print(f"   git commit -m \"📦 Backfill {entry['label']}\"")
        print(f"   git push")


if __name__ == "__main__":
    main()
