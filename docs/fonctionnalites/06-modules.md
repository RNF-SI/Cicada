# Modules

### Comment ça marche

Le système distingue trois "modules" qui représentent des fonctionnalités ou ensembles de données différents.

### Plans de Gestion (module principal)

C'est le cœur de l'application. Un plan de gestion est un document opérationnel pour la conservation d'un ou plusieurs sites.

**Caractéristiques :**
- Un plan peut concerner plusieurs sites (relation many-to-many via `cor_site_pg`)
- Un plan a des référents (utilisateurs responsables)
- L'accès dépend de : être référent du plan, être référent d'un site du plan, être admin de l'organisme gestionnaire, ou être super admin

### Sites (espaces protégés)

Les sites sont les territoires physiques (réserves naturelles, parcs, etc.).

**Gestion des accès :**
- `CorRoleSite` : lie un utilisateur à un site avec des flags (referent, conservateur)
- `CorOgSite` : lie un organisme à un site (gestionnaire principal ou secondaire)
- Un utilisateur peut voir un site s'il y est lié ou si son organisme le gère

### Zonages et Inventaires (modules optionnels)

Ce sont des fonctionnalités supplémentaires qui ne sont pas accessibles par défaut.

**Logique d'accès :**
1. Un utilisateur demande l'accès via une `ValidationRequest`
2. Un super admin approuve ou refuse
3. L'accès est vérifié en regardant s'il existe une demande approuvée pour cet utilisateur et ce module
4. Pas de table dédiée : c'est la `ValidationRequest` elle-même qui fait office de "permission"

### Pourquoi cette différence ?

| Modules | Type d'accès | Raison |
|---------|--------------|--------|
| Plans et Sites | Accès granulaire | C'est le cœur métier, avec des rôles (référent, conservateur, admin) |
| Zonages / Inventaires | Accès binaire (oui/non) | Données de référence consultatives |

---

---

← [Impersonnation](05-impersonnation.md) | [Index](../FONCTIONNALITES.md) | [Gestion des Sites](07-sites.md) →
