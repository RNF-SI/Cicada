#!/usr/bin/env python3
"""
Auto-test des fonctions pures de extract.py (sans clé API ni réseau).

    python3 selftest.py

Vérifie la construction du prompt (à partir du schéma bundlé) et le nettoyage
de la sortie modèle (``to_payload``). L'appel à l'API Claude n'est pas testable
ici (nécessite ANTHROPIC_API_KEY) ; le contrat de format côté serveur est, lui,
couvert par la suite pytest backend (test_import_endpoints.py).
"""
import json
import sys
from pathlib import Path

import extract

HERE = Path(__file__).parent


def test_prompt_arborescence():
    schema = json.loads((HERE / "schema_arborescence.json").read_text("utf-8"))
    prompt = extract.build_system_prompt("arborescence", schema)
    assert "Onglet « Enjeux »" in prompt
    assert "[réf → enjeux]" in prompt  # les liens par code sont expliqués
    assert "Enjeu de conservation" in prompt  # valeurs de nomenclature injectées
    assert "N'invente JAMAIS" in prompt
    print("✓ prompt arborescence")


def test_prompt_actions_with_references():
    schema = {
        "sheets": [
            {"key": "actions", "name": "Actions", "columns": [
                {"key": "code", "required": True},
                {"key": "indicateur", "required": True, "ref": "indicateurs"},
                {"key": "libelle", "required": True},
            ]},
        ],
        "references": {
            "indicateurs": [
                {"code": "I1", "indicateur": "Surface des pelouses", "enjeu": "Pelouses"},
            ],
            "postes": [{"code": "Q1", "poste": "Garde technique"}],
        },
    }
    prompt = extract.build_system_prompt("actions", schema)
    assert "LISTE DE RÉFÉRENCE — INDICATEURS" in prompt
    assert "I1 — Surface des pelouses" in prompt
    assert "Q1 — Garde technique" in prompt
    print("✓ prompt actions (références injectées)")


def test_to_payload_filters():
    schema = json.loads((HERE / "schema_arborescence.json").read_text("utf-8"))
    raw = {
        "data": {
            "enjeux": [{"code": "E1", "libelle": "X", "INCONNU": "z"}],
            "feuille_bidon": [{"a": 1}],
            "olt": [{"code": "", "libelle": ""}],  # ligne vide
        },
        "meta": {"confiance_globale": "basse"},
    }
    payload = extract.to_payload(raw, schema)
    assert "INCONNU" not in payload["data"]["enjeux"][0]
    assert "feuille_bidon" not in payload["data"]
    assert "olt" not in payload["data"]  # ligne vide → feuille absente
    assert payload["meta"]["confiance_globale"] == "basse"
    # to_payload accepte aussi un modèle qui omet l'enveloppe "data".
    flat = extract.to_payload({"enjeux": [{"code": "E9", "libelle": "Y"}]}, schema)
    assert flat["data"]["enjeux"][0]["code"] == "E9"
    print("✓ to_payload (filtrage colonnes/feuilles/lignes vides)")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"\n{len(tests)} tests OK")
    sys.exit(0)
