#!/usr/bin/env python3
"""
Extraction IA d'un plan de gestion (PDF) → JSON au format d'import Cicada.

Outil **hors-application** : il lit un PDF hétérogène (tome II « arborescence » /
tome III « fiches actions ») et produit le JSON attendu par les endpoints
d'import « sans fichier » de Cicada. Ce JSON est ensuite relu/corrigé dans la
grille (#9) avant import réel — l'IA produit un brouillon à 80-90 %, un
gestionnaire valide.

    PDF ──(extract.py, API Claude)──▶ payload.json
        ──▶ POST .../import-{cible}/validate-data  (dry-run, rapport d'erreurs)
        ──▶ relecture / correction (grille #9)
        ──▶ POST .../import-{cible}/import-data     (création)

Le format de sortie est **piloté par le schéma** renvoyé par Cicada
(`describe_schema`), donc une seule logique couvre les deux cibles :

- **arborescence** : schéma statique → `schema_arborescence.json` (fourni ici) ;
- **actions** : schéma **spécifique au plan** (il embarque la liste des
  indicateurs de rattachement) → à télécharger depuis
  `GET /api/plans/plans/{id}/import-actions-schema/`.

Dépendances : ``pip install "anthropic>=0.92"`` (+ ``pypdf`` pour ``--pages``).
La clé ``ANTHROPIC_API_KEY`` (console.anthropic.com) est **distincte** de
l'abonnement Claude Max. Coût indicatif : ~0,5 à 3 € par plan.

Exemples
--------
    export ANTHROPIC_API_KEY=sk-ant-...

    # 1) Arborescence (schéma statique fourni)
    python extract.py --target arborescence \
        --pdf tome_ii.pdf --pages 30-60 --out arbo.json

    # 2) Actions : récupérer d'abord le schéma du plan (codes indicateurs)
    python extract.py --target actions \
        --pdf tome_iii.pdf \
        --schema-url https://cicada.example.fr/api/plans/plans/1444/import-actions-schema/ \
        --token "$JWT" --out actions.json

    # 3) (option) valider directement le JSON produit contre le plan (dry-run)
    python extract.py ... --plan-url https://.../api/plans/plans/1444/ --token "$JWT"
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import unicodedata
import urllib.request
from pathlib import Path

MODEL = "claude-opus-4-8"  # 1M de contexte, lecture PDF native (tableaux + images)
HERE = Path(__file__).parent

TARGETS = {
    "arborescence": {
        "default_schema": HERE / "schema_arborescence.json",
        "endpoint": "import-arborescence",
        "intro": (
            "Tu extrais l'ARBORESCENCE d'un plan de gestion : enjeux, facteurs "
            "d'influence, pressions, objectifs à long terme (OLT), niveaux "
            "d'exigence (NE), objectifs opérationnels (OO), résultats attendus "
            "(RA), indicateurs et métriques."
        ),
    },
    "actions": {
        "default_schema": None,  # spécifique au plan → à télécharger
        "endpoint": "import-actions",
        "intro": (
            "Tu extrais les FICHES ACTIONS / opérations d'un plan de gestion, "
            "et tu les rattaches aux indicateurs EXISTANTS du plan (liste de "
            "référence fournie ci-dessous). Onglet « Budgets » = budget par "
            "(action, année) ; onglet « RH » = jours de travail par (action, "
            "année, poste)."
        ),
    },
}


# ---------------------------------------------------------------------------
# Fonctions pures (testables sans clé API)
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    """Normalise pour comparaison : minuscules, sans accents, espaces réduits."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def build_system_prompt(target: str, schema: dict) -> str:
    """Construit le prompt système à partir du schéma des onglets/colonnes.

    Générique : chaque colonne est décrite par sa clé, si elle est obligatoire,
    si elle référence une autre feuille par CODE (``ref``), si elle est
    multi-valeurs, et ses valeurs autorisées (``values`` pour les
    nomenclatures / vocabulaires). Les références (indicateurs, postes) d'un
    plan sont injectées telles quelles.
    """
    conf = TARGETS[target]
    lines: list[str] = [
        "Tu es un expert des plans de gestion d'espaces naturels protégés "
        "(réserves naturelles, CEN, RNF) et de leur structuration documentaire.",
        "",
        conf["intro"],
        "",
        "RÈGLES IMPÉRATIVES :",
        "1. N'invente JAMAIS une valeur. Absente du document → laisse la colonne "
        "vide (chaîne vide). Ne remplis que ce que le document dit.",
        "2. Recopie les intitulés TELS QU'ÉCRITS. Les libellés varient d'un plan "
        "à l'autre : mappe-les vers la bonne colonne par leur SENS.",
        "3. Les colonnes marquées « [réf → FEUILLE] » contiennent le CODE d'une "
        "ligne de cette autre feuille. TU inventes des codes courts et stables "
        "(ex : E1, E2 pour les enjeux ; F1 pour un facteur ; I1 pour un "
        "indicateur ; A1 pour une action) et tu les réutilises pour lier les "
        "lignes entre elles. Une colonne réf multi-valeurs prend plusieurs codes "
        "séparés par des virgules (ex : « E1,E3 »).",
        "4. Les colonnes avec une liste de valeurs autorisées ne doivent contenir "
        "QUE l'une de ces valeurs (au libellé près). En cas de doute, laisse vide.",
        "5. Pour chaque ligne dont tu n'es pas sûr, ajoute son code (ou son "
        "libellé) dans meta.champs_incertains — un humain relira en priorité.",
    ]
    if target == "actions":
        lines += [
            "6. La colonne « indicateur » de chaque action DOIT contenir le CODE "
            "d'un indicateur de la LISTE DE RÉFÉRENCE ci-dessous (colonne "
            "« code »), choisi par correspondance de sens avec l'indicateur "
            "d'état / de pression de la fiche. Si aucun ne correspond, laisse "
            "vide et signale-le dans meta.champs_incertains.",
        ]
    lines += [
        "",
        "FORMAT DE SORTIE : réponds UNIQUEMENT par un objet JSON, sans texte ni "
        "bloc markdown autour, de la forme :",
        '  {"data": { <clé_onglet>: [ { <clé_colonne>: "valeur", ... }, ... ] }, '
        '"meta": {"confiance_globale": "haute|moyenne|basse", '
        '"champs_incertains": ["..."]}}',
        "",
        "ONGLETS ET COLONNES ATTENDUS :",
    ]

    for sheet in schema.get("sheets", []):
        # Les onglets de saisie uniquement (pas les onglets de référence figés).
        lines.append(f"\n### Onglet « {sheet['name']} » (clé JSON : {sheet['key']})")
        if sheet.get("description"):
            lines.append(f"  {sheet['description']}")
        for col in sheet["columns"]:
            bits = [f"- {col['key']}"]
            if col.get("required"):
                bits.append("(OBLIGATOIRE)")
            if col.get("ref"):
                bits.append(f"[réf → {col['ref']}]")
            if col.get("multi"):
                bits.append("[multi-valeurs, séparées par des virgules]")
            desc = col.get("help") or ""
            if col.get("values"):
                desc = (desc + " ").strip() + " Valeurs autorisées : " + ", ".join(
                    col["values"]
                )
            lines.append("  " + " ".join(bits) + (f" — {desc}" if desc else ""))

    refs = schema.get("references")
    if refs:
        if refs.get("indicateurs"):
            lines.append("\nLISTE DE RÉFÉRENCE — INDICATEURS DU PLAN "
                         "(rattacher les actions à leur « code ») :")
            for r in refs["indicateurs"]:
                lines.append(
                    f"  {r['code']} — {r['indicateur']}  (enjeu : {r.get('enjeu', '')})"
                )
        if refs.get("postes"):
            lines.append("\nLISTE DE RÉFÉRENCE — POSTES DU PLAN "
                         "(colonne « poste » de l'onglet RH) :")
            for r in refs["postes"]:
                lines.append(f"  {r['code']} — {r['poste']}")

    return "\n".join(lines)


def to_payload(raw: dict, schema: dict) -> dict:
    """Nettoie la sortie brute du modèle → ``{"data": {...}, "meta": {...}}``.

    Ne conserve que les onglets/colonnes connus du schéma (les ``_row`` et les
    maps de référence sont ajoutés côté serveur par ``sanitize``). Robuste à un
    modèle qui renverrait des clés en trop ou des lignes non-dict.
    """
    allowed = {s["key"]: [c["key"] for c in s["columns"]] for s in schema["sheets"]}
    src = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    data: dict[str, list[dict]] = {}
    for sheet_key, cols in allowed.items():
        rows = src.get(sheet_key) if isinstance(src, dict) else None
        clean = []
        for r in rows or []:
            if not isinstance(r, dict):
                continue
            row = {c: r.get(c, "") for c in cols}
            if any(str(v or "").strip() for v in row.values()):
                clean.append(row)
        if clean:
            data[sheet_key] = clean
    meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    return {"data": data, "meta": meta}


# ---------------------------------------------------------------------------
# I/O : schéma, PDF, API, POST
# ---------------------------------------------------------------------------

def load_schema(source: str, token: str | None) -> dict:
    """Charge le schéma depuis un fichier local ou une URL (endpoint Cicada)."""
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:  # noqa: S310 (URL maîtrisée)
            return json.loads(resp.read().decode("utf-8"))
    return json.loads(Path(source).read_text(encoding="utf-8"))


def pdf_to_block(pdf_path: Path, page_range: str | None) -> dict:
    """Construit le content block « document » (optionnellement découpé)."""
    if page_range:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            sys.exit("Pour --pages, installe pypdf : pip install pypdf")
        import io

        start, end = (int(x) for x in page_range.split("-"))
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        for i in range(start - 1, min(end, len(reader.pages))):
            writer.add_page(reader.pages[i])
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


def extract(pdf_path: Path, page_range: str | None, system_prompt: str,
            model: str, max_tokens: int) -> dict:
    import anthropic  # import tardif : la clé n'est utile qu'ici

    client = anthropic.Anthropic()
    messages = [{
        "role": "user",
        "content": [
            pdf_to_block(pdf_path, page_range),
            {"type": "text", "text": "Extrais maintenant le document ci-dessus "
             "selon les onglets et colonnes décrits. Renvoie l'objet JSON "
             "{\"data\": ..., \"meta\": ...} et rien d'autre."},
        ],
    }]
    print(f"→ Extraction de {pdf_path.name}"
          f"{f' (pages {page_range})' if page_range else ''} via {model}…",
          file=sys.stderr)
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system_prompt,
        messages=messages,
    ) as stream:
        final = stream.get_final_message()

    text = "".join(b.text for b in final.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].lstrip("json").strip()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        Path("extraction_brute.txt").write_text(text, encoding="utf-8")
        sys.exit(f"JSON invalide ({exc}). Sortie brute → extraction_brute.txt")
    u = final.usage
    print(f"  tokens : {u.input_tokens} in / {u.output_tokens} out", file=sys.stderr)
    return raw


def post_validate(base_plan_url: str, endpoint: str, token: str, payload: dict) -> None:
    """POST du payload sur .../import-{cible}/validate-data (dry-run) et affiche
    le rapport (erreurs / avertissements)."""
    url = base_plan_url.rstrip("/") + f"/{endpoint}/validate-data/"
    body = json.dumps({"data": payload["data"]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            report = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"  validate-data → HTTP {exc.code}\n{exc.read().decode('utf-8')}",
              file=sys.stderr)
        return
    can = report.get("can_import")
    errs = [e for e in report.get("issues", []) if e.get("level") == "error"]
    warns = [e for e in report.get("issues", []) if e.get("level") == "warning"]
    print(f"  validate-data → importable={can} ; {len(errs)} erreur(s), "
          f"{len(warns)} avertissement(s)", file=sys.stderr)
    for e in errs[:20]:
        print(f"    ✗ [{e.get('sheet')}:{e.get('row')}] {e.get('message')}",
              file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", required=True, choices=sorted(TARGETS),
                   help="arborescence | actions")
    p.add_argument("--pdf", type=Path, required=True, help="PDF source")
    p.add_argument("--pages", help="Plage de pages, ex 30-60 (nécessite pypdf)")
    p.add_argument("--schema", help="Fichier schéma local (défaut : bundlé pour "
                   "l'arborescence)")
    p.add_argument("--schema-url", help="URL de l'endpoint import-{cible}-schema "
                   "(obligatoire pour les actions : embarque les indicateurs)")
    p.add_argument("--token", help="JWT pour --schema-url / --plan-url")
    p.add_argument("--out", type=Path, help="JSON de sortie (défaut : <pdf>.<cible>.json)")
    p.add_argument("--model", default=MODEL)
    p.add_argument("--max-tokens", type=int, default=64000)
    p.add_argument("--plan-url", help="URL du plan (…/api/plans/plans/{id}/) pour "
                   "valider le JSON produit en dry-run")
    p.add_argument("--dry-run-prompt", action="store_true",
                   help="N'appelle pas l'API : imprime seulement le prompt système "
                   "(debug du format).")
    args = p.parse_args()

    conf = TARGETS[args.target]
    schema_src = args.schema or args.schema_url or (
        str(conf["default_schema"]) if conf["default_schema"] else None
    )
    if not schema_src:
        sys.exit("Pour --target actions, fournis --schema-url (ou --schema) : le "
                 "schéma embarque les indicateurs du plan pour le rattachement.")
    schema = load_schema(schema_src, args.token)
    system_prompt = build_system_prompt(args.target, schema)

    if args.dry_run_prompt:
        print(system_prompt)
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Définis ANTHROPIC_API_KEY (console.anthropic.com).")
    if not args.pdf.exists():
        sys.exit(f"Introuvable : {args.pdf}")

    raw = extract(args.pdf, args.pages, system_prompt, args.model, args.max_tokens)
    payload = to_payload(raw, schema)

    out = args.out or args.pdf.with_suffix(f".{args.target}.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {k: len(v) for k, v in payload["data"].items()}
    print(f"✓ {sum(counts.values())} ligne(s) extraite(s) {counts} → {out}",
          file=sys.stderr)

    if args.plan_url:
        post_validate(args.plan_url, conf["endpoint"], args.token, payload)


if __name__ == "__main__":
    main()
