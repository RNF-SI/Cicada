#!/usr/bin/env python3
"""
Prototype d'extraction de fiches actions depuis un plan de gestion (PDF) vers JSON,
aligné sur le schéma cible Cicada (cicada_fiche_action_schema.json).

Patron B : outil découplé. PDF en entrée -> JSON normalisé en sortie -> à importer
ensuite dans Cicada (via l'endpoint d'import à construire) ou à convertir en Excel.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python extract_fiches.py "pg_val_suzon_tome_iii_fa1_pelouses.pdf"
    python extract_fiches.py "mepieu_tome3.pdf" --pages 17-40 --out mepieu.json

Dépendances:
    pip install "anthropic>=0.92" jsonschema

Coût indicatif : ~0,5 à 3 € par plan (lecture PDF multimodale incluse).
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import anthropic

try:
    import jsonschema
except ImportError:
    jsonschema = None  # validation optionnelle

MODEL = "claude-opus-4-8"  # 1M de contexte, lecture PDF native (tableaux + images)
SCHEMA_PATH = Path(__file__).with_name("cicada_fiche_action_schema.json")

# ---------------------------------------------------------------------------
# Prompt d'extraction — c'est ICI que se joue la qualité. Règles anti-hallucination.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Tu es un expert des plans de gestion d'espaces naturels protégés \
(réserves naturelles, CEN, RNF) et de leur structuration documentaire.

Ta mission : extraire TOUTES les fiches actions / fiches opérations du document PDF \
fourni, et produire pour chacune un objet JSON conforme au schéma cible Cicada donné \
par l'utilisateur.

RÈGLES IMPÉRATIVES :
1. N'invente JAMAIS une valeur. Si une information n'est pas présente dans le document, \
mets `null` (ou liste vide pour les tableaux).
2. Recopie les intitulés d'enjeu, d'OLT, d'indicateur TELS QU'ÉCRITS dans le document. \
Le rapprochement avec les entités Cicada se fera à l'import, pas par toi.
3. Les libellés varient d'un plan à l'autre (« Indicateurs d'état » vs « Indicateur \
d'état suivi / Pression à gérer » ; « Etat visé sur le long terme » vs « Niveau \
d'exigence à atteindre ») : mappe-les vers les bons champs du schéma par leur SENS.
4. type_action : « CS » pour les suivis scientifiques / connaissance (codes CS, PR), \
« hors_CS » pour les interventions/gestion/administration (codes SP, EI, IP, CI, MS, PA, CC).
5. Pour chaque fiche, renseigne extraction_meta.confiance_globale (haute/moyenne/basse) \
et liste dans champs_incertains les chemins de champs dont tu n'es pas sûr — ce sont \
ceux qu'un humain relira en priorité.
6. N'extrais PAS les métriques chiffrées de suivi (hors périmètre) : laisse cadre.metriques \
vide sauf si une métrique est explicitement nommée dans la fiche.

Réponds UNIQUEMENT avec un objet JSON de la forme {"fiches": [ ...objets fiche... ]}, \
sans texte avant ni après, sans bloc de code markdown."""

USER_INSTRUCTION = """Voici le schéma JSON cible (une entrée du tableau "fiches" par \
fiche action) :

{schema}

Extrais maintenant toutes les fiches actions du PDF ci-dessus selon ce schéma. \
Renvoie {{"fiches": [...]}} et rien d'autre."""


def pdf_to_block(pdf_path: Path, page_range: str | None):
    """Construit le content block 'document'. Optionnellement découpe par pages (pypdf)."""
    if page_range:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            sys.exit("Pour --pages, installe pypdf : pip install pypdf")
        start, end = (int(x) for x in page_range.split("-"))
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        for i in range(start - 1, min(end, len(reader.pages))):
            writer.add_page(reader.pages[i])
        import io
        buf = io.BytesIO()
        writer.write(buf)
        data = buf.getvalue()
    else:
        data = pdf_path.read_bytes()

    return {
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": base64.standard_b64encode(data).decode("ascii"),
        },
    }


def extract(pdf_path: Path, page_range: str | None) -> dict:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement

    messages = [{
        "role": "user",
        "content": [
            pdf_to_block(pdf_path, page_range),
            {"type": "text", "text": USER_INSTRUCTION.format(schema=schema)},
        ],
    }]

    # Streaming + max_tokens élevé : un tome III peut contenir des dizaines de fiches.
    print(f"→ Extraction de {pdf_path.name}"
          f"{f' (pages {page_range})' if page_range else ''} via {MODEL}…",
          file=sys.stderr)
    with client.messages.stream(
        model=MODEL,
        max_tokens=64000,
        thinking={"type": "adaptive"},      # le raisonnement améliore le mapping
        output_config={"effort": "high"},
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        final = stream.get_final_message()

    raw = "".join(b.text for b in final.content if b.type == "text").strip()
    # Garde-fou si le modèle entoure malgré tout d'un bloc markdown
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        Path("extraction_brute.txt").write_text(raw, encoding="utf-8")
        sys.exit(f"JSON invalide ({e}). Sortie brute écrite dans extraction_brute.txt")

    # Tokens consommés -> coût réel (input ~5$/Mtok, output ~25$/Mtok pour Opus 4.8)
    u = final.usage
    print(f"  tokens: {u.input_tokens} in / {u.output_tokens} out", file=sys.stderr)
    return result


def validate(result: dict):
    """Validation locale optionnelle de chaque fiche contre le schéma."""
    if jsonschema is None:
        print("  (jsonschema non installé — validation ignorée)", file=sys.stderr)
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    ok, ko = 0, 0
    for i, fiche in enumerate(result.get("fiches", [])):
        try:
            jsonschema.validate(fiche, schema)
            ok += 1
        except jsonschema.ValidationError as e:
            ko += 1
            code = fiche.get("code_action", f"#{i}")
            print(f"  ⚠ fiche {code} non conforme : {e.message}", file=sys.stderr)
    print(f"  validation : {ok} conformes, {ko} à corriger", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="Extraction fiches actions PDF -> JSON Cicada")
    p.add_argument("pdf", type=Path)
    p.add_argument("--pages", help="Plage de pages, ex 17-40 (nécessite pypdf)")
    p.add_argument("--out", type=Path, help="Fichier JSON de sortie (défaut: <pdf>.json)")
    args = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Définis ANTHROPIC_API_KEY (clé depuis console.anthropic.com).")
    if not args.pdf.exists():
        sys.exit(f"Introuvable : {args.pdf}")

    result = extract(args.pdf, args.pages)
    validate(result)

    out = args.out or args.pdf.with_suffix(".fiches.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(result.get("fiches", []))
    print(f"✓ {n} fiche(s) extraite(s) -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
