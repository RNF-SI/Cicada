#!/usr/bin/env python3
"""
Orchestrateur POC — PDF d'un plan de gestion → brouillon rempli dans CICADA.

Enchaîne les deux phases de l'import IA (décision POC : API Anthropic, une passe,
puis validation humaine dans CICADA) :

    1. Extraction de l'ARBORESCENCE   → POST import-arborescence/import-data
    2. Extraction des ACTIONS         → POST import-actions/import-data
                                         (référence les indicateurs créés en 1)

Le gestionnaire ouvre ensuite le plan dans CICADA et valide dans la grille de
correction. **L'IA ne valide jamais.**

Deux prompts séparés (Q4 du POC) : l'arborescence porte la structure, les actions
s'y rattachent — un seul appel risquerait de dépasser la fenêtre de sortie sur un
gros tome d'actions.

Prérequis
---------
- Le plan cible doit être un **brouillon vide** (l'import d'arborescence est en
  création seule : il refuse un plan qui a déjà des enjeux).
- ``ANTHROPIC_API_KEY`` (console.anthropic.com) — clé distincte de l'abonnement Max.
- Un JWT d'un gestionnaire du plan (login CICADA) pour ``--token``.
- La stack CICADA accessible (``--base-url``, défaut http://localhost:8000).

Exemples
--------
    export ANTHROPIC_API_KEY=sk-ant-...
    JWT=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
      -H 'Content-Type: application/json' \
      -d '{"username":"admin@test.fr","password":"Test123!"}' \
      | python3 -c 'import sys,json;print(json.load(sys.stdin)["access"])')

    # Pipeline complet sur un plan brouillon vide (id 1444)
    python run_poc.py plan.pdf --plan 1444 --token "$JWT"

    # Dry-run : extrait et VALIDE sans rien écrire (rapport d'erreurs)
    python run_poc.py plan.pdf --plan 1444 --token "$JWT" --dry-run

    # Comparer un modèle, ne traiter que l'arborescence, cibler des pages
    python run_poc.py plan.pdf --plan 1444 --token "$JWT" \
        --model claude-sonnet-5 --only arbo --arbo-pages 30-60
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import extract  # noqa: E402  (voisin : PDF → JSON via l'API Claude)

HERE = Path(__file__).parent


# ---------------------------------------------------------------------------
# HTTP (stdlib) vers les endpoints d'import CICADA
# ---------------------------------------------------------------------------

def _api(base: str, path: str) -> str:
    return base.rstrip("/") + "/api/plans/plans/" + path.lstrip("/")


def _get_json(url: str, token: str | None) -> dict:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:  # noqa: S310 (URL maîtrisée)
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, token: str | None, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"error": raw[:500]}


def _print_report(report: dict) -> None:
    """Affiche les anomalies d'un rapport de validation (import-data / validate-data)."""
    issues = report.get("issues") or []
    errs = [i for i in issues if i.get("level") == "error"]
    warns = [i for i in issues if i.get("level") == "warning"]
    print(f"    importable={report.get('can_import')} · "
          f"{len(errs)} erreur(s), {len(warns)} avertissement(s)", file=sys.stderr)
    for i in errs[:25]:
        print(f"      ✗ [{i.get('sheet')}:{i.get('row')}·{i.get('column')}] "
              f"{i.get('message')}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------

def _extract_payload(target: str, schema: dict, pdf: Path, pages: str | None,
                     model: str, max_tokens: int, out_dir: Path | None) -> dict:
    prompt = extract.build_system_prompt(target, schema)
    raw = extract.extract(pdf, pages, prompt, model, max_tokens)
    payload = extract.to_payload(raw, schema)
    counts = {k: len(v) for k, v in payload["data"].items()}
    print(f"  ✓ {target} : {sum(counts.values())} ligne(s) extraite(s) {counts}",
          file=sys.stderr)
    if out_dir:
        p = out_dir / f"{pdf.stem}.{target}.json"
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    JSON → {p}", file=sys.stderr)
    return payload


def _import(base: str, plan: int, token: str, endpoint: str, payload: dict,
            dry_run: bool) -> bool:
    """POST le payload sur import-data (ou validate-data si dry_run). Renvoie True si OK."""
    verb = "validate-data" if dry_run else "import-data"
    url = _api(base, f"{plan}/{endpoint}/{verb}/")
    status, body = _post_json(url, token, {"data": payload["data"]})

    if dry_run:
        print(f"  {endpoint} · dry-run :", file=sys.stderr)
        _print_report(body)
        return bool(body.get("can_import"))

    if status == 201:
        created = body.get("created", {})
        print(f"  ✓ {endpoint} importé : {created} (total {body.get('total')})",
              file=sys.stderr)
        return True
    # 400 → rapport de validation ; 403 → plan pas en brouillon ; autre → erreur brute
    print(f"  ✗ {endpoint} refusé (HTTP {status})", file=sys.stderr)
    if "issues" in body:
        _print_report(body)
    elif body.get("error"):
        print(f"      {body['error']}", file=sys.stderr)
    return False


def run_arbo(base, plan, token, pdf, pages, model, max_tokens, out_dir, dry_run) -> bool:
    print("\n=== Phase 1 : arborescence ===", file=sys.stderr)
    # Schéma bundlé (enrichi des valeurs de nomenclature autorisées → meilleur prompt).
    schema = json.loads((HERE / "schema_arborescence.json").read_text("utf-8"))
    payload = _extract_payload("arborescence", schema, pdf, pages, model, max_tokens, out_dir)
    return _import(base, plan, token, "import-arborescence", payload, dry_run)


def run_actions(base, plan, token, pdf, pages, model, max_tokens, out_dir, dry_run) -> bool:
    print("\n=== Phase 2 : actions ===", file=sys.stderr)
    # Schéma spécifique au plan : il embarque les indicateurs (codes de rattachement)
    # créés en phase 1. On le récupère depuis le serveur.
    url = _api(base, f"{plan}/import-actions-schema/")
    try:
        schema = _get_json(url, token)
    except urllib.error.HTTPError as exc:
        print(f"  ✗ Schéma actions inaccessible (HTTP {exc.code}). "
              f"Le plan a-t-il bien des indicateurs (phase 1) ?", file=sys.stderr)
        return False
    refs = (schema.get("references") or {}).get("indicateurs") or []
    print(f"  {len(refs)} indicateur(s) de rattachement disponibles", file=sys.stderr)
    if not refs:
        print("  ⚠ Aucun indicateur : importez d'abord l'arborescence.", file=sys.stderr)
        return False
    payload = _extract_payload("actions", schema, pdf, pages, model, max_tokens, out_dir)
    return _import(base, plan, token, "import-actions", payload, dry_run)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pdf", type=Path, help="PDF du plan de gestion")
    p.add_argument("--plan", type=int, required=True, help="ID du plan (brouillon vide)")
    p.add_argument("--token", required=True, help="JWT d'un gestionnaire du plan")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--model", default=extract.MODEL)
    p.add_argument("--max-tokens", type=int, default=64000)
    p.add_argument("--only", choices=["arbo", "actions", "both"], default="both")
    p.add_argument("--pages", help="Plage de pages commune (ex : 20-90)")
    p.add_argument("--arbo-pages", help="Pages de l'arborescence (défaut : --pages)")
    p.add_argument("--actions-pages", help="Pages des actions (défaut : --pages)")
    p.add_argument("--dry-run", action="store_true",
                   help="Extrait et VALIDE sans rien écrire (rapport d'erreurs).")
    p.add_argument("--out-dir", type=Path, help="Dossier où sauver les JSON extraits.")
    args = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Définis ANTHROPIC_API_KEY (console.anthropic.com).")
    if not args.pdf.exists():
        sys.exit(f"Introuvable : {args.pdf}")
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)

    arbo_pages = args.arbo_pages or args.pages
    actions_pages = args.actions_pages or args.pages
    common = (args.base_url, args.plan, args.token, args.pdf)

    print(f"POC import IA — plan {args.plan} · modèle {args.model}"
          f"{' · DRY-RUN' if args.dry_run else ''}", file=sys.stderr)

    ok_arbo = True
    if args.only in ("arbo", "both"):
        ok_arbo = run_arbo(*common, arbo_pages, args.model, args.max_tokens,
                           args.out_dir, args.dry_run)

    if args.only in ("actions", "both"):
        if args.only == "both" and not ok_arbo and not args.dry_run:
            print("\n⚠ Arborescence non importée : phase actions ignorée "
                  "(les actions ont besoin des indicateurs).", file=sys.stderr)
        else:
            run_actions(*common, actions_pages, args.model, args.max_tokens,
                        args.out_dir, args.dry_run)

    if not args.dry_run:
        print(f"\n→ Ouvrez le plan dans CICADA pour relire et valider le brouillon "
              f"(plan {args.plan}).", file=sys.stderr)


if __name__ == "__main__":
    main()
