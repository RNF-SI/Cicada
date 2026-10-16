---
hide:
  - toc
---

# Référence complète

L'ensemble des endpoints de l'API d'une instance CICADA, dans une seule interface Swagger : utilisez le champ de filtre pour retrouver un chemin ou un mot. Les pages par [domaine](index.md#les-domaines-de-lapi) présentent les mêmes endpoints avec leur contexte d'usage.

Cette référence est **générée automatiquement depuis le code** (schéma OpenAPI 3 produit par `drf-spectacular`). Sur une instance en fonctionnement, le schéma à jour est servi, pour un utilisateur authentifié, à `/api/schema/`, et l'interface interactive à `/api/docs/`.

!!! warning "« Try it out » : lectures seulement"

    Le bouton « Try it out » exécute une vraie requête depuis votre navigateur, vers l'instance qui sert cette documentation. Il n'est proposé ici que sur les `GET` ; les écritures (`POST`, `PUT`, `PATCH`, `DELETE`) modifieraient les données réelles et s'essaient sur `/api/docs/` de l'instance, avec un jeton.

<swagger-ui src="openapi.json"/>
