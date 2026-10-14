# Mesure d'audience Matomo (#670)

CICADA peut envoyer ses statistiques de fréquentation vers un serveur **Matomo**. Le réglage est **propre à chaque instance** et **désactivé par défaut**.

## Activer

Aucune variable d'environnement : un super admin règle tout depuis l'interface.

1. **Administration > Paramètres > Mesure d'audience**.
2. Renseigner l'**URL du serveur Matomo** (ex. `https://matomo.example.org`, sans `matomo.php`) et l'**identifiant du site** (`idSite`, entier) créé pour cette instance dans Matomo.
3. Cocher « Activer la mesure d'audience » puis **Enregistrer**.

Le serveur refuse l'activation sans URL ou sans identifiant, une URL qui n'est pas en `http(s)` et un identifiant non numérique. Décocher puis enregistrer arrête la mesure ; l'URL et l'identifiant sont conservés.

Réglages stockés dans `SiteConfiguration` (`matomo_enabled`, `matomo_url`, `matomo_site_id`), exposés en lecture par `GET /api/settings/` (public : le traceur doit aussi fonctionner sur les pages non connectées).

## Ce qui est envoyé

| Type | Déclencheur | Catégorie / action Matomo |
|------|-------------|---------------------------|
| Page vue | chaque fin de navigation Angular (SPA) | URL réelle de la page, titre du document |
| Événement | création d'un plan | `Plans` / `Création` |
| Événement | changement de statut | `Plans` / `Changement de statut` / nouveau statut |
| Événement | nouvelle version, évaluation mi-parcours, nouveau rang, prolongation, révision | `Plans` / libellé de l'opération |
| Événement | tout export (`export-*`) du plan ou d'une fiche action | `Exports` / nom de l'export |
| Événement | approbation / rejet d'une demande | `Validations` / `Approbation` · `Rejet` |
| Recherche interne | recherche dans l'exploration (1re page seulement) | mot-clé, `Contenus` · `Plans`, nombre de résultats |

Les événements sont déduits des **réponses HTTP réussies** par `matomoInterceptor` (`core/interceptors/matomo.interceptor.ts`) : une même action déclenchée depuis plusieurs écrans n'est décrite qu'une fois. Pour suivre une nouvelle action, ajouter une règle dans `matomoTrackingFor()` et son test.

## Confidentialité

- **Sans cookie** (`disableCookies`, envoyé avant toute page vue) → exemption de consentement CNIL, pas de bandeau.
- **Aucun identifiant utilisateur** : `setUserId` n'est jamais appelé.
- Les **URL réelles** sont transmises (choix produit) : elles peuvent contenir le slug d'un plan.
- À la charge de la structure : **anonymiser les IP** côté serveur Matomo et **mentionner la mesure** dans ses mentions légales. Voir [PRIVACY_POLICY.md](PRIVACY_POLICY.md).

## CSP

CICADA ne pose pas d'en-tête `Content-Security-Policy` (ni Apache du conteneur frontend, ni Django). Si un reverse proxy en ajoute une, y autoriser le serveur Matomo dans `script-src` (chargement de `matomo.js`) et `connect-src` / `img-src` (envoi des hits).
