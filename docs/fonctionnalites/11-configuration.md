# Configuration du site

### Comment ça marche

La configuration du site permet aux super administrateurs de personnaliser certains aspects de l'application, notamment l'image affichée sur la page d'accueil pour les visiteurs non connectés.

### Modèle Singleton

La configuration du site utilise un **pattern singleton** : il n'existe qu'une seule instance de configuration en base de données (toujours l'ID 1). Cette approche garantit qu'il n'y a jamais de confusion sur quelle configuration utiliser.

### API de configuration

| Endpoint | Méthode | Permission | Description |
|----------|---------|------------|-------------|
| `/api/settings/` | GET | Public | Récupère la configuration actuelle |
| `/api/settings/` | PATCH | super_admin | Met à jour la configuration |

### Flux de modification de l'image

1. Le super admin accède à **Administration > Paramètres**
2. Il clique sur "Choisir une image" ou glisse-dépose un fichier
3. Une prévisualisation s'affiche
4. Il clique sur "Enregistrer"
5. L'image est uploadée en `multipart/form-data`
6. Le backend :
   - Valide le type de fichier (image uniquement)
   - Supprime l'ancienne image si elle existe
   - Stocke la nouvelle dans `media/settings/homepage/`
   - Met à jour `updated_at` et `updated_by`
7. L'URL de l'image est retournée et utilisée sur la page d'accueil

### Réinitialisation

Pour revenir à l'image par défaut :
- Envoyer `reset_image=true` ou `homepage_image=''` via PATCH
- Le backend supprime l'image personnalisée
- La page d'accueil affiche alors l'image par défaut (`assets/images/homepage-default.jpg`)

### Structure des données

| Champ | Type | Description |
|-------|------|-------------|
| `homepage_image` | ImageField | Chemin relatif de l'image uploadée |
| `homepage_image_url` | URL (généré) | URL complète pour affichage |
| `updated_at` | DateTime | Date de dernière modification |
| `updated_by` | ForeignKey | Super admin ayant modifié |

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `backend/apps/core/models.py` | Modèle `SiteConfiguration` |
| `backend/apps/core/views.py` | Vue `SiteConfigurationView` |
| `backend/apps/core/serializers.py` | Sérialiseur |
| `frontend/.../settings.service.ts` | Service Angular |
| `frontend/.../admin-settings/` | Composant d'administration |

---

---

← [Tests](10-tests.md) | [Index](../FONCTIONNALITES.md) | [Page Exploration](12-exploration.md) →
