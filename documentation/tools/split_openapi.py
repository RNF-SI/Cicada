#!/usr/bin/env python3
"""Range le schéma OpenAPI complet et le découpe par domaine pour la documentation.

Entrée : le fichier produit par `manage.py spectacular` (documentation/docs/api/openapi.json).
Sorties :
  - le même fichier, compacté (servi tel quel par « Référence complète ») ;
  - documentation/docs/api/openapi/<domaine>.json : un sous-schéma par page de la
    documentation, avec uniquement les composants qu'il référence.

Le découpage se fait sur le chemin (préfixe /api/…), pas sur les tags : les tags de
drf-spectacular reprennent le premier segment d'URL, trop grossier pour `plans`
(245 opérations). Un chemin qui ne correspond à aucun domaine est signalé et rangé
dans `autres.json`, pour qu'un nouvel endpoint ne disparaisse pas en silence.
"""
import json
import re
import sys
from pathlib import Path

# Ordre = priorité (le premier motif qui matche gagne).
DOMAINES = [
    ("auth", r"^/api/auth/"),
    ("public", r"^/api/public/"),
    ("exploration", r"^/api/(exploration|federation)/"),
    ("organismes-sites", r"^/api/(users/(organismes|sites)|geo)/"),
    ("users", r"^/api/users/"),
    ("arborescence", r"^/api/plans/(enjeux|enjeux-fichiers|facteurs-influence|pressions|"
                     r"objectifs-long-terme|niveaux-exigence|objectifs-operationnels|"
                     r"resultats-attendus|indicateurs|metriques|mesures|indicateur-mesures)/"),
    ("actions-suivi", r"^/api/(plans/(operations|realisations|realisations-organismes|postes|fonctions)|inventaires)/"),
    ("plans", r"^/api/plans/"),
    ("referentiels", r"^/api/(taxref|habref|inpg|campanule|nomenclatures)/"),
    ("notifications", r"^/api/(notifications|validations|activity|modules)/"),
    ("administration", r"^/api/(admin|settings|system)/"),
]


def collect_refs(node, found):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/"):
            found.add(ref)
        for v in node.values():
            collect_refs(v, found)
    elif isinstance(node, list):
        for v in node:
            collect_refs(v, found)


def components_for(schema, paths):
    """Composants (schemas, securitySchemes…) atteignables depuis `paths`, fermeture transitive."""
    comps = schema.get("components", {})
    wanted, todo = set(), set()
    collect_refs(paths, todo)
    while todo:
        ref = todo.pop()
        if ref in wanted:
            continue
        wanted.add(ref)
        _, _, kind, name = ref.split("/", 3)
        node = comps.get(kind, {}).get(name)
        if node is not None:
            collect_refs(node, todo)
    out = {}
    for ref in wanted:
        _, _, kind, name = ref.split("/", 3)
        if name in comps.get(kind, {}):
            out.setdefault(kind, {})[name] = comps[kind][name]
    # Les schémas de sécurité ne sont pas référencés par $ref mais par nom.
    if "securitySchemes" in comps:
        out["securitySchemes"] = comps["securitySchemes"]
    return out


def main(path):
    path = Path(path)
    schema = json.load(open(path))
    dump = dict(ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    json.dump(schema, open(path, "w"), **dump)

    groupes = {nom: {} for nom, _ in DOMAINES}
    groupes["autres"] = {}
    for p, ops in schema["paths"].items():
        for nom, motif in DOMAINES:
            if re.match(motif, p):
                groupes[nom][p] = ops
                break
        else:
            groupes["autres"][p] = ops

    out_dir = path.parent / "openapi"
    out_dir.mkdir(exist_ok=True)
    for f in out_dir.glob("*.json"):
        f.unlink()
    for nom, paths in groupes.items():
        if not paths:
            continue
        sub = {k: v for k, v in schema.items() if k not in ("paths", "components")}
        sub["paths"] = dict(sorted(paths.items()))
        sub["components"] = components_for(schema, paths)
        # Ne garder que les tags réellement portés par ces opérations : Swagger UI
        # affiche sinon tous les groupes de l'API, vides, au-dessus du domaine.
        utilises = {t for ops in paths.values() for op in ops.values()
                    if isinstance(op, dict) for t in op.get("tags", [])}
        sub["tags"] = [t for t in schema.get("tags", []) if t.get("name") in utilises]
        json.dump(sub, open(out_dir / f"{nom}.json", "w"), **dump)
        n_ops = sum(len(ops) for ops in paths.values())
        print(f"  {nom:18s} {len(paths):4d} chemins {n_ops:4d} opérations")
    if groupes["autres"]:
        print("⚠ chemins hors domaine (à ranger dans DOMAINES) :", *groupes["autres"], sep="\n    ")
    print(f"{path}: {len(schema['paths'])} chemins, OpenAPI {schema.get('openapi')}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "documentation/docs/api/openapi.json")
