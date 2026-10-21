---
hide:
  - toc
---

# Référence complète

L'ensemble des endpoints de l'API d'une instance CICADA, dans une seule interface Swagger : utilisez le champ de filtre pour retrouver un chemin ou un mot. Les pages par [domaine](index.md#les-domaines-de-lapi) présentent les mêmes endpoints avec leur contexte d'usage.

Cette référence est **générée automatiquement depuis le code** (schéma OpenAPI 3 produit par `drf-spectacular`). Sur une instance en fonctionnement, le schéma à jour est servi à `/api/schema/`, et l'interface interactive à `/api/docs/` (sans connexion : ce sont les appels qui exigent un jeton).

!!! warning "« Try it out » : lectures seulement"

    Le bouton « Try it out » exécute une vraie requête depuis votre navigateur, vers l'instance qui sert cette documentation. Il n'est proposé ici que sur les `GET` ; les écritures (`POST`, `PUT`, `PATCH`, `DELETE`) modifieraient les données réelles et s'essaient sur `/api/docs/` de l'instance, avec un jeton.

!!! tip "Essayer toute l'API sur `/api/docs/`"

    1. Ouvrir `/api/docs/` sur l'instance (par exemple `https://<instance>/api/docs/`).
    2. Déplier `POST /api/auth/login/`, « Try it out », saisir identifiant (ou e-mail) et mot de passe, « Execute » : copier la valeur `access` de la réponse.
    3. Bouton **Authorize** en haut de page : coller le jeton (sans le préfixe `Bearer`), « Authorize ». Le cadenas des endpoints se ferme ; le jeton est conservé si la page est rechargée, et vaut 60 minutes.

    Les requêtes partent avec **vos** droits, sur les données réelles de l'instance.

<swagger-ui src="openapi.json"/>
