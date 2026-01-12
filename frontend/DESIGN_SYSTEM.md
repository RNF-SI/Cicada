# Design System - Outil Plan de Gestion

**Date de mise a jour**: 2025-12-09
**Statut**: Complet, base sur Kit UI Biodiv' France 11/2025
**Source**: Kit UI Figma + PDF

> Design system base sur **Angular Material 19** avec personnalisation **Biodiv' France**

---

## Architecture

**Approche** : Angular Material + Overrides cibles + Composants custom Kit UI

- **Angular Material** : Composants de base (boutons, forms, tables, navigation, accordeons)
- **Material Overrides** : Personnalisation complete avec couleurs Biodiv' France
- **Composants Custom** : Jauges, indicateurs, tuiles, breadcrumb (specifiques Kit UI)

---

## Table des matieres

1. [Specifications Design](#specifications-design)
2. [Implementation Technique](#implementation-technique)
3. [Guide de developpement](#guide-de-developpement)

---

# Specifications Design

## Couleurs (Kit UI 11/2025)

### Couleur Principale
- **Bleu-vert**: `#025359` (Boutons & actions, navigation, titres)
- **Bleu-vert hover**: lighten 8%
- **Bleu-vert active**: lighten 15%

### Couleurs Secondaires
- **Jaune**: `#FEC180` (decoratif/fond)
- **Orange saumon**: `#F5B399` (decoratif/fond)
- **Terra Cotta**: `#B74D5D` (AA sur fond blanc)
- **Vert pale**: `#C0E3CF` (decoratif/fond)

### Couleurs Succes / Erreurs / Scores
- **Rouge clair**: `#FF7579` (Tres mauvais score - decoratif/fond)
- **Orange**: `#FA9965` (Mauvais score - decoratif/fond)
- **Jaune moutarde**: `#F7D35C` (Score neutre - decoratif/fond)
- **Vert clair**: `#82DB8A` (Bon score - decoratif/fond)
- **Bleu ciel**: `#81C9D8` (Tres bon score - decoratif/fond)
- **Vert**: `#04854B` (Succes - AA)
- **Rouge**: `#E12329` (Erreur - AA)

### Couleurs Neutres
- **Noir**: `#343433` (Textes)
- **Gris fonce**: `#746F6E` (Textes mention - AA)
- **Gris**: `#C6C6C6` (Etats inactifs)
- **Gris clair**: `#E4E4E4` (Filets separateurs tableau, background tableau)
- **Beige**: `#F8F5F1` (Background)
- **Blanc**: `#FFFFFF`

### Accessibilite WCAG AA
Le Kit UI indique les combinaisons accessibles :
- Texte noir `#343433` sur fond colore clair (scores, secondaires)
- Texte blanc sur fond primary `#025359`, success `#04854B`, error `#E12329`
- Certaines couleurs sont decoratives uniquement (ne pas utiliser pour du texte)

---

## Typographie

**Font**: **Nunito** (Google Font)

### Hierarchie (Kit UI 11/2025)
| Style | Taille | Poids | Line-height | Letter-spacing |
|-------|--------|-------|-------------|----------------|
| H1 | 48px | Bold | 72px | 0% |
| H2 | 32px | Bold | 48px | 0% |
| H3 | 24px | Bold | 36px | 0% |
| H4 | 20px | Bold | 30px | 0% |
| Subtitle | 15px | Bold | 24px | 20% (uppercase) |
| Texte standard | 15px | Regular | 24px | 0% |
| Texte bold | 15px | Bold | 24px | 0% |
| Texte mention | 13px | Regular | 19px | 0% |

---

## Boutons (Kit UI)

### Boutons Principaux
- **Default**: Background `#025359`, texte blanc, border-radius 24px (pill)
- **Survol**: Background plus clair
- **Actif (clique)**: Background encore plus clair
- **Inactif**: Background `#C6C6C6` (gris), texte blanc

### Boutons Secondaires (outlined)
- **Default**: Background transparent, border 2px solid `#025359`, texte `#025359`
- **Survol**: Background `#025359`, texte blanc
- **Actif**: Background actif, texte blanc
- **Inactif**: Border et texte `#C6C6C6`

### Boutons Tertiaires (texte)
- **Default**: Texte `#025359`
- **Survol**: Background leger
- **Actif**: Background actif, texte blanc
- **Inactif**: Texte `#C6C6C6`

### Tailles
- **Taille M**: Default (padding 12px 24px)
- **Taille S**: Petit (padding 8px 16px, font-size 13px)

### Boutons Icone Seule
- Taille: 40x40px
- Border-radius: 50%
- Meme logique de couleurs

---

## Formulaires (Kit UI)

### Inputs - Etats
- **Vide**: Border gris `#C6C6C6`
- **Avec placeholder**: Texte placeholder gris clair
- **Rempli**: Texte noir `#343433`
- **Focus**: Border primary `#025359`
- **Erreur**: Border rouge `#E12329` + message d'erreur
- **Inactif**: Background gris clair, texte gris

### Types speciaux
- **Champ obligatoire**: Label avec asterisque rouge
- **Champ avec texte d'aide**: Texte sous le champ + lien cliquable
- **Champ avec icone info**: Icone (i) a droite
- **Dropdown**: Avec chevron a droite
- **Date picker**: Avec icone calendrier
- **Recherche dropdown**: Avec icone loupe
- **Textarea**: Zone de texte extensible

### Selection
- **Checkbox**: Cases a cocher (plusieurs choix)
- **Radio button**: Boutons radio (un seul choix)
- Couleur cochee: `#025359`

---

## Navigation (Kit UI)

### Header
- Background: `#025359`
- Logo Biodiv' France centre
- Menu hamburger a gauche
- Mon compte dropdown a droite
- Administration lien (si admin)

### Fil d'ariane (Breadcrumb)
- Fond: `#025359`
- Icone maison dans cercle blanc
- Separateurs: chevron `>`
- Niveaux en texte blanc

### Menu lateral
- Background: `#025359`
- Largeur: 250px (collapsible)
- Items: Icone + texte
- Hover: Background plus clair
- Actif: Background blanc, texte primary, coin arrondi haut-droit

### Barre d'action fixee
- Position: fixee en bas
- Background: `#025359`
- Boutons: Annuler (secondary) + Valider (primary outline blanc)

### Tabs
- Underline pour onglet actif
- Texte primary pour actif, gris pour inactif

### Controles segmentes
- Border: 2px solid `#025359`
- Option active: Background `#025359`, texte blanc
- Option inactive: Background transparent, texte `#025359`

---

## Tableaux (Kit UI)

### Header
- Background: `#025359`
- Texte blanc, bold
- Tri avec icones fleches
- Colonnes triables indiquees

### Cellules
- Alternance: ligne blanche / ligne gris tres clair
- Contour: border-radius 4px
- Filet vertical: gris clair si colonne fixee
- Types: texte, texte bold (colonne principale), texte + secondaire
- Tags avec couleurs
- Actions: boutons icones ou dropdown

### Jauge dans tableau
- Barre de progression avec indicateur de date

---

## Accordeons (Kit UI)

### Types
- **Large**: Titre principal + boutons edit/expand
- **Section**: Groupement avec titre uppercase
- **Indicateur d'etat**: Avec metriques et actions imbriquees
- **Action**: Details d'une action avec sous-sections
- **Small**: Liste simple avec puces

### Etats
- Ferme: Chevron (+) ou bas
- Ouvert: Chevron (-) ou haut
- Background ouvert: rose pale `#F8F5F1`

---

## Composants Custom (Kit UI)

### Tags
- Border-radius: 16px
- Padding: 4px 12px
- Variants: status (valide, neutre), score (5 niveaux), priority (1-3)

### Jauges de progression (4 etats)
- **Non demarree**: Barre vide grise
- **Mi-parcours**: Barre partielle + indicateur position
- **Parcours termine**: Barre pleine rouge
- **Parcours depasse**: Barre rouge pointillee + fleche

### Indicateurs d'actions (5 types)
- **Action prevue**: Drapeau plein
- **Action prevue et realisee**: Etoile pleine
- **Action prevue et partiellement realisee**: Etoile mi-pleine
- **Action realisee non prevue**: Rond plein gris
- **Action partiellement realisee non prevue**: Rond mi-plein gris

### Scores (Smileys)
- 5 niveaux avec emojis dans cercles colores
- Sans donnee: cercle gris avec "/"

### Tuiles
- Border-radius asymetrique: 0 20px 20px 0
- Image de fond avec overlay vagues
- Icone centree
- Titre + fleche en bas
- Ombre au survol

### Blocs info conseil
- Background beige
- Icone ampoule jaune
- Titre bold + texte details
- Variants avec border-left coloree

### Liste a puces
- Puces croix rouges
- Survol: texte primary + underline

### Documents
- Liste avec icones telechargement
- Bouton ajouter en bas

### Pagination
- Boutons numerotes
- Page active: background primary
- Fleches navigation
- Ellipsis "..."

---

## Composants Angular Reutilisables

Les composants standalone sont dans `frontend/src/app/shared/components/`.

### `PlanGaugeComponent`
**Selecteur**: `app-plan-gauge`
**Fichiers**: `plan-gauge/`
**Description**: Jauge de progression pour les plans de gestion.

```html
<app-plan-gauge
  status="in-progress"
  [startYear]="2020"
  [endYear]="2030"
  [currentYear]="2025"
></app-plan-gauge>
```

| Input | Type | Defaut | Description |
|-------|------|--------|-------------|
| `status` | `GaugeStatus` | `'not-started'` | Statut de la jauge |
| `startYear` | `number` | `2020` | Annee de debut du plan |
| `endYear` | `number` | `2030` | Annee de fin du plan |
| `currentYear` | `number` | Annee actuelle | Annee courante pour le calcul |

**Statuts disponibles** (`GaugeStatus`):
- `not-started`: Barre vide grise
- `in-progress`: Barre partiellement remplie avec indicateur position
- `completed`: Barre completement remplie
- `exceeded`: Barre rouge avec indicateur de depassement

### `NotificationBellComponent`
**Selecteur**: `app-notification-bell`
**Fichiers**: `notification-bell/`
**Description**: Cloche de notifications pour le header avec badge compteur.

```html
<app-notification-bell></app-notification-bell>
```

**Fonctionnalites**:
- Badge affichant le nombre total (notifications non lues + validations en attente)
- Affiche "99+" si le compte depasse 99
- Menu dropdown avec les notifications recentes
- Dialog pour voir toutes les notifications
- Marquage comme lu automatique au clic
- Navigation vers l'URL d'action de chaque notification
- Polling automatique pour les mises a jour

**Signals exposes**:
- `notifications`: Liste des notifications
- `unreadCount`: Nombre de notifications non lues
- `pendingValidations`: Nombre de validations en attente
- `totalBadgeCount`: Total pour le badge
- `hasUnread`: Boolean si notifications non lues

**Types de notifications** (icones associees):
- `welcome`: Bienvenue (fi-rr-hand-wave)
- `validation_request`: Demande de validation (fi-rr-check-circle)
- `validation_approved`: Validation approuvee (fi-rr-check)
- `validation_rejected`: Validation rejetee (fi-rr-cross)
- `user_associated_site`: Association a un site (fi-rr-marker)
- `user_associated_plan`: Association a un plan (fi-rr-document)
- `system_alert`: Alerte systeme (fi-rr-bell)

---

# Implementation Technique

## Structure des fichiers SCSS

```
frontend/src/assets/scss/
-- _variables.scss           # Variables (couleurs, espacements, tokens) - Kit UI 11/2025
-- _typography.scss          # Systeme typographique (Nunito 15px base)
-- _material-overrides.scss  # Personnalisation Angular Material
-- _filters.scss             # Filtres avances (panels, pagination, sort)
-- _components.scss          # Composants custom Kit UI (jauges, tuiles, etc.)
```

**Total**: 5 fichiers SCSS

---

## Architecture CSS

### Approche : Material + Composants Kit UI

**Composants Material (avec overrides Biodiv' France)** :
- **Boutons** -> `mat-button`, `mat-raised-button`, `mat-stroked-button`
- **Cards** -> `mat-card`
- **Chips/Tags** -> `mat-chip`, `mat-chip-set`
- **Forms** -> `mat-form-field`, `mat-input`, `mat-select`
- **Tables** -> `mat-table`, `mat-paginator`, `mat-sort`
- **Navigation** -> `mat-toolbar`, `mat-sidenav`, `mat-tab-group`
- **Accordeons** -> `mat-expansion-panel`
- **Dialogs** -> `mat-dialog`

**Composants Custom Kit UI** (`_components.scss`) :
- Jauges de progression (`.gauge`)
- Indicateurs d'actions (`.action-indicator`)
- Scores smileys (`.score-emoji`)
- Tuiles asymetriques (`.tile`)
- Blocs info conseil (`.info-block`)
- Fil d'ariane (`.breadcrumb`)
- Barre d'action fixee (`.action-bar`)
- Menu lateral custom (`.sidebar-menu`)
- Controles segmentes (`.segmented-control`)
- Liste a puces (`.list-bullets`)
- Documents (`.documents-list`)
- Pagination custom (`.pagination-custom`)

---

## Ordre d'import dans `styles.scss`

```scss
// 1. Angular Material (TOUJOURS en premier avec @use)
@use '@angular/material' as mat;
@include mat.core();

// 2. Variables & Typography
@import 'assets/scss/variables';
@import 'assets/scss/typography';

// 3. Custom Components
@import 'assets/scss/filters';
@import 'assets/scss/components';

// 4. Material 3 Theme + Color Tokens Biodiv' France
$theme: mat.define-theme(...);
html { @include mat.all-component-themes($theme); }
:root { --mat-sys-primary: #025359; ... }

// 5. Material Overrides (personnalisation Biodiv' France)
@import 'assets/scss/material-overrides';
```

---

# Guide de developpement

## Exemples d'utilisation

### Boutons (Angular Material)

```html
<!-- Primary button (raised) -->
<button mat-raised-button color="primary">Action principale</button>

<!-- Secondary button (stroked/outlined) -->
<button mat-stroked-button color="primary">Action secondaire</button>

<!-- Tertiary button (text) -->
<button mat-button color="primary">Action tertiaire</button>

<!-- Icon button -->
<button mat-icon-button color="primary">
  <mat-icon>add</mat-icon>
</button>

<!-- Button sizes -->
<button mat-raised-button color="primary" class="btn-sm">Petit (S)</button>
<button mat-raised-button color="primary">Normal (M)</button>

<!-- Disabled -->
<button mat-raised-button color="primary" [disabled]="true">Inactif</button>
```

### Tags/Chips (Angular Material)

```html
<!-- Status tags -->
<mat-chip-set>
  <mat-chip class="status-valide">valide</mat-chip>
  <mat-chip class="status-neutre">neutre</mat-chip>
</mat-chip-set>

<!-- Score tags (5 niveaux Kit UI) -->
<mat-chip class="score-very-bad">Tres mauvais</mat-chip>
<mat-chip class="score-bad">Mauvais</mat-chip>
<mat-chip class="score-neutral">Neutre</mat-chip>
<mat-chip class="score-good">Bon</mat-chip>
<mat-chip class="score-very-good">Tres bon</mat-chip>

<!-- Priority tags -->
<mat-chip class="priority-1">Priorite 1</mat-chip>
<mat-chip class="priority-2">Priorite 2</mat-chip>
<mat-chip class="priority-3">Priorite 3</mat-chip>
```

### Jauges de progression (Custom)

```html
<!-- Non demarree -->
<div class="gauge gauge-not-started">
  <span class="gauge-bar"><span class="gauge-bar-fill"></span></span>
  <span>Non demarree</span>
</div>

<!-- Mi-parcours (50%) -->
<div class="gauge gauge-mid-progress">
  <span class="gauge-bar"><span class="gauge-bar-fill" style="width: 50%"></span></span>
  <span>2026-2036</span>
</div>

<!-- Parcours termine -->
<div class="gauge gauge-completed">
  <span class="gauge-bar"><span class="gauge-bar-fill"></span></span>
  <span>Termine</span>
</div>

<!-- Parcours depasse -->
<div class="gauge gauge-exceeded">
  <span class="gauge-bar"><span class="gauge-bar-fill"></span></span>
  <span>Depasse</span>
</div>
```

### Indicateurs d'actions (Custom)

```html
<span class="action-indicator action-planned">Action prevue</span>
<span class="action-indicator action-planned-realized">Prevue et realisee</span>
<span class="action-indicator action-planned-partial">Partiellement realisee</span>
<span class="action-indicator action-realized-unplanned">Realisee non prevue</span>
<span class="action-indicator action-partial-unplanned">Partielle non prevue</span>
```

### Scores Smileys (Custom)

```html
<span class="score-emoji score-very-bad"></span>
<span class="score-emoji score-bad"></span>
<span class="score-emoji score-neutral"></span>
<span class="score-emoji score-good"></span>
<span class="score-emoji score-very-good"></span>
<span class="score-emoji score-no-data"></span>
```

### Tuiles asymetriques (Custom)

```html
<div class="tile">
  <div class="tile-image" style="background-image: url('...')">
    <span class="tile-image-icon">
      <mat-icon>description</mat-icon>
    </span>
  </div>
  <div class="tile-content">
    <h3 class="tile-title">Mes plans de gestion</h3>
    <span class="tile-arrow"></span>
  </div>
</div>
```

### Bloc info conseil (Custom)

```html
<div class="info-block">
  <span class="info-block-icon"></span>
  <div class="info-block-content">
    <h4 class="info-block-content-title">Bloc info conseil</h4>
    <p class="info-block-content-text">Texte details</p>
  </div>
</div>

<!-- Variants -->
<div class="info-block info-block-success">...</div>
<div class="info-block info-block-warning">...</div>
<div class="info-block info-block-error">...</div>
```

### Fil d'ariane (Custom)

```html
<nav class="breadcrumb">
  <span class="breadcrumb-home"><mat-icon>home</mat-icon></span>
  <span class="breadcrumb-separator"></span>
  <a class="breadcrumb-item" href="#">Niveau 1</a>
  <span class="breadcrumb-separator"></span>
  <a class="breadcrumb-item" href="#">Niveau 2</a>
  <span class="breadcrumb-separator"></span>
  <span class="breadcrumb-item active">Marais du Grosset</span>
</nav>
```

### Controles segmentes (Custom)

```html
<div class="segmented-control">
  <button class="segmented-control-option active">Global</button>
  <button class="segmented-control-option">Annuel</button>
</div>
```

---

## Bonnes pratiques

### A faire
1. **Utiliser Angular Material** pour tous les composants standards
2. **Utiliser les composants custom** (`_components.scss`) pour les elements Kit UI specifiques
3. **Respecter les contrastes** WCAG AA (noir sur fonds clairs, blanc sur fonds fonces)
4. **Utiliser les variables SCSS** plutot que des valeurs en dur
5. **Tester sur mobile** - le design est responsive

### A eviter
- Ne pas creer de classes custom pour des composants Material
- Ne pas modifier l'ordre d'import dans `styles.scss`
- Ne pas utiliser les couleurs decoratives pour du texte (accessibilite)

---

## Statistiques

- **5 fichiers SCSS**
- **Architecture 100% Material** + composants custom Kit UI
- **100% conforme** Kit UI Biodiv' France 11/2025
- **WCAG AA** compliant
- **Responsive** mobile/tablet/desktop

---

## Iconographie

Le Kit UI utilise **Uicons by Flaticon** (Rounded Corners).

A ajouter dans le footer ou page credits :
```html
Uicons by <a href="https://www.flaticon.com/uicons">Flaticon</a>
```

---

**Design System Status**: Complet
**Source**: Kit UI Biodiv' France 11/2025 + Figma
**Ready for Production**: Oui
