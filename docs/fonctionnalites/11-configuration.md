# 11. Configuration de l'instance

Chaque instance règle elle-même son apparence et ses engagements, sans redéploiement : un super admin le fait depuis **Administration › Paramètres**.

> Usage pas à pas : [administration de l'instance › Paramètres](../../documentation/docs/admin-instance/parametres.md).

## Un singleton

`SiteConfiguration` (`backend/apps/core/models.py`) n'a qu'une ligne (id 1). On la lit avec `SiteConfiguration.get_instance()` ou par l'API.

| Endpoint | Méthode | Permission |
|----------|---------|------------|
| `/api/settings/` | GET | public (champs d'affichage) |
| `/api/settings/` | PATCH | super admin |
| `/api/settings/homepage-image/`, `/api/settings/structure-logo/` | POST / DELETE | super admin |

## Ce qui se règle

| Thème | Champs | Effet |
|-------|--------|-------|
| **Apparence** | `homepage_image` (+ position), `structure_logo`, `header_color`, `accueil_titre`, `accueil_sous_titre`, `export_color` | Accueil, bandeau, couleur des exports Excel |
| **Inscription** | `inscription_url_externe` | Renvoie l'inscription vers un formulaire externe |
| **CGU** (#746) | `cgu_texte` (Markdown), `cgu_version` | Chaque utilisateur accepte la version en vigueur ; changer le texte renouvelle la version |
| **Documents** (#745) | `taille_max_document_mo` (20 Mo par défaut) | Taille maximale d'un document du plan ou d'un enjeu |
| **Mesure d'audience** (#670) | `matomo_enabled`, `matomo_url`, `matomo_site_id` | Matomo sans cookie, désactivé par défaut |
| **API publique** (#645) | `api_publique_plans` | Ouvre `/api/public/plans/` (métadonnées des plans validés), coupée par défaut |
| **Fédération** (#636) | `federation_partage` | Consentement à publier vers le hub, faux par défaut — voir [21. Fédération](21-federation.md) |
| **Doc'Gestion FCEN** | `enable_docgestion_fcen` | Affiche le champ d'identifiant Doc'Gestion sur les plans |

`updated_at` et `updated_by` gardent la trace de la dernière modification.

## Autres écrans de réglage

- **Connexion GeoNature / UsersHub** (#769) : *Administration › Paramètres › Connexion*, réglages dans un singleton dédié (`ConnexionGeoNature`), lus par `apps/authentication/reglages.py`. Voir [administration › Connexion GeoNature](../../documentation/docs/administration/connexion-geonature.md).
- **Raccordement au hub** (#695) : URL et jetons du hub, saisis dans *Paramètres › Raccordement manuel*.

## Variables d'environnement

Le `.env` garde la main sur ce qui touche à l'infrastructure (base, hub, identité de l'instance). Quand une valeur y est renseignée, l'écran correspondant l'affiche verrouillée. Liste : `.env.example` et [administration › Installation](../../documentation/docs/administration/installation.md).

---

← [Tests](10-tests.md) | [Index](../FONCTIONNALITES.md) | [Exploration des données](12-exploration.md) →
