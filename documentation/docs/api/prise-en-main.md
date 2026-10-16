# Prise en main

Cette page suffit pour un premier appel. Les règles détaillées sont dans [Authentification et permissions](authentification.md) ; la description de chaque endpoint est sur la page de son [domaine](index.md#les-domaines-de-lapi).

## 1. Obtenir un jeton

```bash
curl -X POST https://<instance>/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "utilisateur@exemple.fr", "password": "…"}'
```

```json
{
  "access": "eyJhbGciOi…",
  "refresh": "eyJhbGciOi…",
  "user": { "id": 12, "email": "utilisateur@exemple.fr", "niveau_role": "utilisateur", "…": "…" }
}
```

Le champ `email` accepte indifféremment l'adresse e-mail ou l'identifiant de connexion. Sur une instance reliée à GeoNature, utiliser `/api/auth/login-geonature/` ; `GET /api/auth/mode/` indique le mode de connexion de l'instance.

## 2. Appeler l'API

Le jeton d'accès se transmet dans l'en-tête `Authorization` :

```bash
curl https://<instance>/api/plans/plans/ \
  -H "Authorization: Bearer <access>"
```

Quand il expire, l'API répond `401`. Demander un nouveau jeton d'accès avec le jeton de rafraîchissement (qui est lui-même renouvelé à chaque appel) :

```bash
curl -X POST https://<instance>/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh>"}'
```

## Pagination

Les listes renvoient une enveloppe commune :

```json
{
  "links": { "next": "https://…/api/plans/plans/?page=2", "previous": null },
  "pagination": {
    "count": 44, "current_page": 1, "total_pages": 3,
    "page_size": 20, "has_next": true, "has_previous": false
  },
  "results": [ … ]
}
```

| Paramètre | Rôle |
|-----------|------|
| `page` | Numéro de page (à partir de 1) |
| `page_size` | Taille de page, 20 par défaut, 1 000 au maximum (500 sur les exports et statistiques) |

Quelques endpoints « par parent » (`…/by-plan/{id}/`, `…/by-enjeu/{id}/`…) renvoient une liste simple, non paginée : ils servent à charger une arborescence complète.

## Filtrer, chercher, trier

Trois mécanismes se combinent sur la plupart des listes :

| Paramètre | Exemple | Effet |
|-----------|---------|-------|
| champ | `?statut=valide&id_organisme=3` | Filtre exact sur un champ (la liste des champs est dans Swagger) |
| `search` | `?search=camargue` | Recherche texte sur les champs déclarés par l'endpoint |
| `ordering` | `?ordering=-annee_debut,nom_pg` | Tri, `-` pour l'ordre décroissant |

## Écrire

- `POST` crée, `PUT` remplace, `PATCH` modifie partiellement, `DELETE` supprime.
- Les réponses de création renvoient l'objet créé (`201`), les suppressions `204`.
- Les actions métier (valider un plan, lier un site, approuver une demande…) sont des `POST` sur des sous-chemins explicites, par exemple `POST /api/plans/plans/{id}/change-status/`.
- Les identifiants ont le nom de la clé primaire du modèle : `id_pg` pour un plan, `id_enjeu`, `id_operation`, `id_role` pour un utilisateur, `slug` pour un site.

## Erreurs

Les erreurs sont en JSON et portent l'identifiant de corrélation à citer dans un signalement :

```json
{ "detail": "Vous n'avez pas la permission d'effectuer cette action.", "correlation_id": "7f0c…" }
```

Les erreurs de validation (`400`) détaillent les champs en cause :

```json
{ "nom_pg": ["Ce champ est obligatoire."], "annee_fin": ["Doit être postérieure à annee_debut."], "correlation_id": "7f0c…" }
```

| Code | Signification |
|------|---------------|
| `400` | Requête invalide (le corps détaille les erreurs par champ) |
| `401` | Jeton absent, invalide ou expiré |
| `403` | Droits insuffisants, ou plan verrouillé (hors brouillon) |
| `404` | Ressource inexistante, ou hors du périmètre de l'utilisateur (l'API ne distingue pas les deux cas) |
| `409` | Conflit métier (par exemple un brouillon enfant existe déjà) |
| `502` | Exploration nationale : hub injoignable, aucun repli sur l'index local |
| `500` | Erreur interne, journalisée côté serveur avec le même `correlation_id` |

## Géométries

Les géométries de sites, de plans, d'enjeux et d'actions sont lues et écrites en **GeoJSON** (WGS 84). Les endpoints `…/geojson/` et `…/geojson_list/` renvoient directement une `Feature` ou une `FeatureCollection` exploitable dans un SIG.
