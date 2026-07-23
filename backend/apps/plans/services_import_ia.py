"""
Extraction IA d'un plan de gestion (PDF) → données prêtes pour la grille de
correction (#9). Version **in-app** : l'appel à l'API Anthropic se fait côté
serveur (via une tâche Celery), là où le module ``tools/import-ia/`` le faisait
hors-app.

Contrat POC : une passe → données pré-remplies → **le gestionnaire valide** dans
la grille. L'IA n'importe jamais rien elle-même. Deux cibles distinctes :
``arborescence`` (structure) puis ``actions`` (rattachées aux indicateurs créés).

La sortie a la même forme que les endpoints ``…/validate-data`` : ``{data, report}``
où ``data`` alimente la grille et ``report`` liste les anomalies à corriger.

NB : ``build_system_prompt`` / ``to_payload`` sont volontairement identiques à
ceux de ``tools/import-ia/extract.py`` (chemin hors-app) — même format de sortie.
"""

from __future__ import annotations

import base64
import json

from .services_import import (
    TYPES_ECOLOGIQUES,
    TYPES_SOCIOECO,
    _load_nomenclature_values,
    describe_schema,
    public_parsed,
    sanitize_parsed,
    validate_import,
)
from .services_import_actions import (
    describe_actions_schema,
    public_actions_parsed,
    sanitize_actions_parsed,
    validate_actions_import,
)

DEFAULT_MODEL = "claude-opus-4-8"  # lecture PDF native (texte + image)
DEFAULT_MAX_TOKENS = 64000

_INTROS = {
    "arborescence": (
        "Tu extrais l'ARBORESCENCE d'un plan de gestion : enjeux, facteurs "
        "d'influence, pressions, objectifs à long terme (OLT), niveaux d'exigence "
        "(NE), objectifs opérationnels (OO), résultats attendus (RA), indicateurs "
        "et métriques."
    ),
    "actions": (
        "Tu extrais les FICHES ACTIONS / opérations d'un plan de gestion, et tu "
        "les rattaches aux indicateurs EXISTANTS du plan (liste de référence "
        "fournie ci-dessous). Onglet « Budgets » = budget par (action, année) ; "
        "onglet « RH » = jours de travail par (action, année, poste)."
    ),
}


# ---------------------------------------------------------------------------
# Schémas (avec valeurs de nomenclature autorisées pour un meilleur prompt)
# ---------------------------------------------------------------------------

def _enriched_arbo_schema() -> dict:
    """Schéma arborescence + valeurs autorisées injectées par colonne."""
    nomen = _load_nomenclature_values()
    vocab = {"ecolo": list(TYPES_ECOLOGIQUES), "socio": list(TYPES_SOCIOECO)}
    sheets = describe_schema()
    for sheet in sheets:
        for col in sheet["columns"]:
            if col.get("nomenclature"):
                col["values"] = nomen.get(col["nomenclature"], [])
            elif col.get("vocab"):
                col["values"] = vocab.get(col["vocab"], [])
    return {"sheets": sheets}


def _schema_for(target: str, plan) -> dict:
    if target == "arborescence":
        return _enriched_arbo_schema()
    if target == "actions":
        return describe_actions_schema(plan)
    raise ValueError(f"Cible inconnue : {target}")


# ---------------------------------------------------------------------------
# Prompt + nettoyage (identiques à tools/import-ia/extract.py)
# ---------------------------------------------------------------------------

def build_system_prompt(target: str, schema: dict) -> str:
    lines: list[str] = [
        "Tu es un expert des plans de gestion d'espaces naturels protégés "
        "(réserves naturelles, CEN, RNF) et de leur structuration documentaire.",
        "",
        _INTROS[target],
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
        lines.append(
            "6. La colonne « indicateur » de chaque action DOIT contenir le CODE "
            "d'un indicateur de la LISTE DE RÉFÉRENCE ci-dessous (colonne "
            "« code »), choisi par correspondance de sens. Si aucun ne correspond, "
            "laisse vide et signale-le dans meta.champs_incertains."
        )
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
            lines.append(
                "\nLISTE DE RÉFÉRENCE — INDICATEURS DU PLAN "
                "(rattacher les actions à leur « code ») :"
            )
            for r in refs["indicateurs"]:
                lines.append(
                    f"  {r['code']} — {r['indicateur']}  (enjeu : {r.get('enjeu', '')})"
                )
        if refs.get("postes"):
            lines.append(
                "\nLISTE DE RÉFÉRENCE — POSTES DU PLAN "
                "(colonne « poste » de l'onglet RH) :"
            )
            for r in refs["postes"]:
                lines.append(f"  {r['code']} — {r['poste']}")

    return "\n".join(lines)


def to_payload(raw: dict, schema: dict) -> dict:
    """Sortie brute du modèle → ``{"data": {...}, "meta": {...}}`` (colonnes connues)."""
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
# Appel à l'API Anthropic (isolé pour être stubbable dans les tests)
# ---------------------------------------------------------------------------

def call_anthropic(system_prompt: str, pdf_b64_list: list[str], model: str,
                   max_tokens: int) -> dict:
    """Envoie le(s) PDF + le prompt, renvoie l'objet JSON brut du modèle."""
    import anthropic  # import tardif : la clé n'est utile qu'ici

    client = anthropic.Anthropic()
    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64,
            },
        }
        for b64 in pdf_b64_list
    ]
    content.append({
        "type": "text",
        "text": "Extrais maintenant le document ci-dessus selon les onglets et "
                "colonnes décrits. Renvoie l'objet JSON {\"data\": ..., \"meta\": ...} "
                "et rien d'autre.",
    })
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        final = stream.get_final_message()

    text = "".join(b.text for b in final.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].lstrip("json").strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Orchestration : PDF(s) → {data, report, meta}
# ---------------------------------------------------------------------------

def extract(target: str, plan, pdf_bytes_list: list[bytes],
            model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS) -> dict:
    """Extrait ``target`` depuis le(s) PDF et renvoie de quoi alimenter la grille.

    Renvoie ``{"data": <lignes par onglet, _row inclus>, "report": <anomalies>,
    "meta": <confiance/champs incertains>}`` — même forme que ``validate-data``.
    """
    schema = _schema_for(target, plan)
    prompt = build_system_prompt(target, schema)
    b64 = [base64.standard_b64encode(b).decode("ascii") for b in pdf_bytes_list]
    raw = call_anthropic(prompt, b64, model, max_tokens)
    payload = to_payload(raw, schema)

    if target == "arborescence":
        parsed = sanitize_parsed(payload["data"])
        report = validate_import(plan, parsed).as_dict()
        data = public_parsed(parsed)
    else:  # actions
        parsed = sanitize_actions_parsed(plan, payload["data"])
        report = validate_actions_import(plan, parsed).as_dict()
        data = public_actions_parsed(parsed)

    return {"data": data, "report": report, "meta": payload.get("meta", {})}
