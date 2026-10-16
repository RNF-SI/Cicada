# API de CICADA

CICADA expose une **API REST** (Django REST Framework) consommée par l'application web. Elle est documentée ici pour les intégrations tierces et les développements.

<div class="tiles">

<a href="authentification/" class="tile--green">
<strong>Authentification et permissions</strong>
Jetons JWT, rafraîchissement, rôles et niveaux d'accès.
</a>

<a href="api-publique-plans/" class="tile--yellow">
<strong>API publique des métadonnées des plans</strong>
Lecture ouverte, sans authentification, des métadonnées des plans validés pour une application documentaire tierce.
</a>

<a href="reference/" class="tile--salmon">
<strong>Référence des endpoints</strong>
Tous les endpoints, générés automatiquement depuis le code (OpenAPI).
</a>

</div>

## Principes généraux

- **Base d'URL** : `https://<instance>/api/`. Chaque instance CICADA expose sa propre API ; il n'existe pas d'API centrale.
- **Format** : JSON en entrée comme en sortie (`Content-Type: application/json`). Les géométries sont échangées en **GeoJSON** (EPSG:4326).
- **Authentification** : tous les endpoints exigent un jeton JWT, sauf `/api/auth/` (connexion, inscription), `/api/health/` et, lorsque l'instance l'a ouverte, l'[API publique des métadonnées des plans](api-publique-plans.md).
- **Pagination** : les listes sont paginées (`page`, `page_size`, 20 éléments par défaut).
- **Filtrage et recherche** : paramètres de requête `?champ=valeur`, `?search=` et `?ordering=` sur la plupart des listes.
- **Droits** : l'API applique les mêmes règles que l'application (voir [Authentification et permissions](authentification.md)). Un plan non brouillon est en lecture seule pour tout le monde ; seuls ses référents et les gestionnaires peuvent agir sur son cycle de vie et ses exports.
- **Traçabilité** : chaque requête reçoit un identifiant `X-Correlation-ID` propagé dans les journaux du serveur.
