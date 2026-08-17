# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CICADA** - Web application for managing conservation area management plans, developed for CEN (Conservatoire d'Espaces Naturels) and RNF (Réserves Naturelles de France).

- **Current Status**: Plans de Gestion models implemented, Django admin configured
- **Architecture Documentation**: See `claude.md` for detailed specifications
- **Repository**: https://github.com/RNF-SI/Cicada

## ⚠️ RÈGLE OBLIGATOIRE : Design System

**Pour TOUTE tâche impliquant le frontend (Angular/SCSS), tu DOIS :**

1. **Consulter le Design System** : [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) avant de coder
2. **Respecter les couleurs** : Utiliser UNIQUEMENT les variables SCSS définies, jamais de valeurs hex directes
3. **Respecter la typographie** : Font Nunito, tailles et poids définis dans `_typography.scss`
4. **Respecter les composants** : Boutons, formulaires, chips selon les spécifications Figma
5. **Respecter l'accessibilité WCAG AA** : Combinaisons texte/fond approuvées uniquement

**Liens Figma de référence :** Voir `FIGMA_LINKS.md` (non versionné) ou contacter l'équipe design pour accéder aux maquettes (Couleurs, Boutons, Formulaires, Tableaux, Accordéons, Autres composants, Iconographie).

**Combinaisons texte/fond autorisées (WCAG AA) :**

| Fond | Texte autorisé |
|------|----------------|
| `#025359` (Primary) | Blanc uniquement |
| `#B74D5D` (Terra Cotta) | Blanc uniquement |
| `#04854B` (Succès) | Blanc uniquement |
| `#E12329` (Erreur) | Blanc uniquement |
| `#FEC180` (Jaune) | Noir `#343433` ou Primary `#025359` |
| `#F5B399` (Orange saumon) | Noir `#343433` ou Primary `#025359` |
| `#C0E3CF` (Vert pâle) | Noir `#343433` ou Primary `#025359` |
| Scores (`#FF7579`, `#FA9965`, `#F7D35C`, `#82DB8A`, `#81C9D8`) | Noir `#343433` uniquement |
| Tags (`#CFF1D3`, `#C1E5EC`, `#FFE6CC`, `#FFC7C9`, `#F9CFBE`, `#E4E4E4`) | Noir `#343433` uniquement |
| Blanc | Primary `#025359`, Noir `#343433`, Gris foncé `#746F6E` |

**NE JAMAIS utiliser :**
- Texte blanc sur fonds clairs (jaune, orange, vert pâle, scores)
- Texte couleur score sur fond blanc (pas assez de contraste)
- `mat.$blue-palette` - utiliser `mat.$cyan-palette`
- Couleurs hex directement - utiliser les variables SCSS

## Technology Stack

### Backend
- Django 5.0+ with Django REST Framework 3.14+
- PostgreSQL 17+ with PostGIS 3.5+ for spatial data
- Python 3.11+
- Celery + Redis for async tasks (email notifications)

### Frontend
- Angular 19+ with TypeScript 5+
- Angular Material for UI components
- Leaflet for interactive maps
- **Design System**: Custom SCSS based on Kit UI CICADA (11/2025)
  - **Source de référence**: `KitUI/` (PNG des maquettes)
  - **Status**: ⚠️ 95% complet
  - **Fichiers SCSS**: 6 fichiers (~3500 lignes)
    - `_variables.scss` - Tokens (couleurs, spacing, typography, breakpoints)
    - `_typography.scss` - Styles typographiques + responsive
    - `_responsive.scss` - **Mixins responsive** (breakpoints, containers, grids)
    - `_material-overrides.scss` - Personnalisation Angular Material
    - `_components.scss` - Composants custom (jauges, tuiles, breadcrumb, etc.)
    - `_filters.scss` - Filtres et pagination
  - **Couleurs**: Conformes Kit UI 11/2025
    - Primary: #025359 (Bleu-vert)
    - Secondary: #FEC180 (Jaune), #F5B399 (Orange saumon), #B74D5D (Terra Cotta), #C0E3CF (Vert pâle)
    - Scores: #FF7579, #FA9965, #F7D35C, #82DB8A, #81C9D8
    - Status: #04854B (Succès), #E12329 (Erreur), #FA9965 (Warning), #81C9D8 (Info)
  - **Font**: Nunito (Google Font)
  - **Accessibilité**: WCAG AA compliant - voir [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) pour les règles détaillées
  - **Responsive**: Mobile, Tablet, Desktop
  - **Icônes**:
    - **Uicons by Flaticon**: CDN intégré (Rounded Regular - `fi-rr-*`)
    - **ScoreIconComponent**: Smileys SVG pour scores (very-bad, bad, neutral, good, very-good, no-data)
    - **ActionIconComponent**: Indicateurs d'actions SVG (planned, planned-realized, planned-partial, realized-unplanned, partial-unplanned)
    - Classes utilitaires: `.icon-xs` à `.icon-xxl`, `.icon-primary`, `.icon-btn`, `.icon-circle`
  - **À compléter**:
    - Zebra striping pour tableaux
    - Badge compteur filtres actifs
    - Composant input +/- (fréquence)

### Règles d'utilisation du Design System (IMPORTANT)

**Ces règles doivent être suivies automatiquement pour tout code Angular/SCSS :**

#### Boutons Angular Material
- **Bouton primaire (action principale)**: `mat-flat-button color="primary"`
  - Fond: `$primary-color` (#025359)
  - Texte: blanc
  - Exemple: `<button mat-flat-button color="primary">Créer</button>`

- **Bouton secondaire (action alternative)**: `mat-stroked-button`
  - Bordure: `$primary-color` (#025359)
  - Texte: `$primary-color` (#025359)
  - Au hover: fond `$primary-color`, texte blanc
  - Exemple: `<button mat-stroked-button>Annuler</button>`

- **Bouton tertiaire (action discrète)**: `mat-button`
  - Texte: `$primary-color` (#025359)
  - Sans bordure ni fond
  - Exemple: `<button mat-button>En savoir plus</button>`

- **Tailles**: Ajouter `.btn-sm` ou `.btn-lg` pour les variantes

#### Couleurs à utiliser
| Usage | Variable SCSS | Hex | Ne pas utiliser |
|-------|---------------|-----|-----------------|
| Actions, titres, liens | `$primary-color` | #025359 | Bleu Material (#3f51b5), autres bleus |
| Accent décoratif | `$secondary-yellow` | #FEC180 | - |
| Warnings visuels | `$secondary-orange-salmon` | #F5B399 | - |
| Erreurs bloquantes | `$error-color` | #E12329 | - |
| Succès | `$success-color` | #04854B | - |
| Texte principal | `$black` | #343433 | #000000 |
| Texte secondaire | `$gray-dark` | #746F6E | - |

#### Modales (MatDialog)
- **Largeur standard**: `width: '1300px', maxWidth: '95vw', maxHeight: '90vh'`
- **Éviter**: `width: '600px'` (trop étroit pour les layouts complexes)

#### Configuration du thème Material (CRITIQUE)
Le thème Angular Material est configuré dans `src/styles.scss`:
- **Palette de base**: `mat.$cyan-palette` (la plus proche de #025359)
- **Tokens CSS personnalisés**: Définis dans `:root` pour forcer #025359
- **NE JAMAIS** utiliser `mat.$blue-palette` ou d'autres palettes bleues
- Les tokens spécifiques aux composants (boutons, checkboxes, etc.) sont définis dans `styles.scss` et `_material-overrides.scss`

**Si les boutons/checkboxes affichent une couleur bleue au lieu de #025359:**
1. Vérifier que le thème utilise `mat.$cyan-palette` (pas `mat.$blue-palette`)
2. Vérifier les tokens CSS dans `:root` de `styles.scss`
3. Les overrides sont dans `_material-overrides.scss`

#### Dans les fichiers SCSS de composants
- Toujours importer: `@import 'variables';`
- Utiliser les variables SCSS, jamais les valeurs hex directement
- **Les couleurs sont gérées globalement** - éviter les overrides `!important` dans les composants
- Si absolument nécessaire, utiliser les tokens CSS Material:
```scss
.my-component {
  --mdc-filled-button-container-color: #{$primary-color};
  --mdc-checkbox-selected-icon-color: #{$primary-color};
}
```

### Composants Angular Réutilisables

Les composants standalone sont dans `frontend/src/app/shared/components/`.

#### `NavigationTileComponent`
**Sélecteur**: `app-navigation-tile`
**Fichiers**: `navigation-tile/`
**Description**: Tuile de navigation avec image de fond, forme de coin arrondi et icône.

```html
<app-navigation-tile
  title="Mes plans de gestion"
  uicon="fi-rr-document"
  link="/plans"
  color="primary"
></app-navigation-tile>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `title` | `string` | `''` | Titre affiché en bas de la tuile |
| `uicon` | `string` | `'fi-rr-folder'` | Icône Flaticon (`fi-rr-*`) ou custom (`custom:icon-name`) |
| `link` | `string` | `'/'` | Route de navigation |
| `color` | `'primary' \| 'salmon' \| 'terra-cotta' \| 'yellow'` | `'primary'` | Couleur de la tuile |

**Assets requis** (dans `assets/images/`):
- `tile-backgrounds/bg-{color}.png` - Fond coloré avec vagues
- `corner-shapes/corner-{color}.png` - Forme de coin avec icône
- `icons/{icon-name}.svg` - Icônes custom (si `uicon` commence par `custom:`)

#### `EllipseIconButtonComponent`
**Sélecteur**: `app-ellipse-icon-button`
**Fichiers**: `ellipse-icon-button/`
**Description**: Bouton ellipse avec icône, configurable en couleur et taille.

```html
<!-- Ellipse primaire avec icône blanche -->
<app-ellipse-icon-button icon="fi-rr-document"></app-ellipse-icon-button>

<!-- Ellipse blanche avec icône primaire, grande -->
<app-ellipse-icon-button
  icon="fi-rr-search"
  ellipseColor="white"
  iconColor="primary"
  size="lg"
></app-ellipse-icon-button>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `icon` | `string` | `'fi-rr-document'` | Classe d'icône Flaticon |
| `ellipseColor` | `EllipseColor` | `'primary'` | Couleur de fond (`primary`, `salmon`, `terra-cotta`, `yellow`, `pale-green`, `white`, `beige`, `gray`, `gray-light`) |
| `iconColor` | `'white' \| 'primary'` | `'white'` | Couleur de l'icône |
| `size` | `'xs' \| 'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | Taille de l'ellipse |
| `showBorder` | `boolean` | `true` | Afficher la bordure blanche |
| `showShadow` | `boolean` | `true` | Afficher l'ombre |

#### `ScoreIconComponent`
**Sélecteur**: `app-score-icon`
**Fichiers**: `icons/score-icon.component.*`
**Description**: Icône smiley SVG pour afficher les scores/évaluations.

```html
<app-score-icon level="good" [size]="24"></app-score-icon>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `level` | `'very-bad' \| 'bad' \| 'neutral' \| 'good' \| 'very-good' \| 'no-data'` | `'neutral'` | Niveau de score |
| `size` | `number` | `20` | Taille en pixels |

**Couleurs associées**:
- `very-bad`: #FF7579 (rouge)
- `bad`: #FA9965 (orange)
- `neutral`: #F7D35C (jaune)
- `good`: #82DB8A (vert)
- `very-good`: #81C9D8 (bleu)
- `no-data`: #DADADA (gris)

#### `ActionIconComponent`
**Sélecteur**: `app-action-icon`
**Fichiers**: `icons/action-icon.component.*`
**Description**: Indicateur SVG pour le statut des actions dans les plans de gestion.

```html
<app-action-icon status="planned-realized" [size]="28"></app-action-icon>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `status` | `ActionStatus` | `'planned'` | Statut de l'action |
| `size` | `number` | `28` | Taille en pixels |

**Statuts disponibles**:
- `planned`: Cercle pointillé (action prévue)
- `planned-realized`: Cercle plein + ✓ (prévue et réalisée)
- `planned-partial`: Demi-cercle + ✓ (prévue et partiellement réalisée)
- `realized-unplanned`: Cercle + ✗ (réalisée non prévue)
- `partial-unplanned`: Demi-cercle + ✗ (partiellement réalisée non prévue)

#### `TagComponent` (#296)
**Sélecteur**: `app-tag`
**Fichiers**: `tag/`
**Description**: Tag unifié (pill, sans bordure, padding compact). Remplace `.status-*`, `.score-*`, et les `<mat-chip>` pour les statuts. Issue #296.

```html
<!-- Statut simple -->
<app-tag variant="success" label="Validé"></app-tag>

<!-- Avec icône -->
<app-tag variant="warning" label="En attente" icon="fi-rr-clock"></app-tag>

<!-- Cliquable -->
<app-tag variant="draft" label="Brouillon" [clickable]="true" (click)="onEdit()"></app-tag>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `variant` | `TagVariant` | `'neutral'` | Voir liste ci-dessous |
| `label` | `string` | `''` | Texte du tag |
| `icon` | `string?` | — | Classe Flaticon optionnelle (ex: `'fi-rr-check'`) |
| `size` | `'sm' \| 'md'` | `'md'` | Taille (sm pour tableaux denses) |
| `clickable` | `boolean` | `false` | Active curseur pointer + effet hover |

**Variantes disponibles** (palette pastel Figma « 🧩 Tags » — **texte toujours noir `#343433`**) :

| Variante | Fond | Variable SCSS | Usage |
|----------|------|---------------|-------|
| `success` | #CFF1D3 (vert) | `$tag-green` | Validé, Approuvé, Actif |
| `error` | #FFC7C9 (rouge) | `$tag-red` | Rejeté, Annulé, Expiré, Inactif, Erreur |
| `info` / `primary` | #C1E5EC (cyan) | `$tag-cyan` | Modifié, Utilisateur |
| `warning` / `draft` | #FFE6CC (orange) | `$tag-orange` | Brouillon, En attente, Référent |
| `neutral` | #F9CFBE (saumon) | `$tag-salmon` | Libellé neutre **sans icône** |
| `muted` | #E4E4E4 (gris) | `$tag-gray` | Archivé |
| `score-*` | palette scores | `$score-*` | Scores / priorités |

**Règles** :
- **Texte toujours noir** : les fonds sont pastel pour rester AA avec `$black`. Ne jamais réutiliser `$success-color` / `$error-color` (couleurs pleines, texte blanc) pour un tag.
- **Icône uniquement sur les statuts principaux** où couleur + icône font sens. Sinon → `neutral` sans icône, « afin de ne pas multiplier les icônes et les couleurs » (annotation Figma).
- **Source de vérité des couleurs + icônes** : `shared/utils/tag-icons.ts` (`PLAN_STATUS_TAG`, `VALIDATION_STATUS_TAG`, `USER_ROLE_TAG`, `USER_STATUS_TAG`, `LOG_LEVEL_TAG` + helpers `getPlanStatusTag()`…). Ne pas redéfinir un mapping statut→couleur dans un composant : importer depuis ce fichier.
- **Deux catégories sans tag du tout** (annotation Figma « ne pas utiliser de composant tag/chips, mettre simplement le libellé en texte normal ») : le **type d'aire protégée** (RNN, RNR, PNR, ENS…) et la **référence d'un site / d'un organisme** (code INPN).
- Vérifier qu'une icône existe bien dans le set Uicons Rounded Regular **2.6.0** (chargé par `index.html`) avant de l'utiliser : le nom de la maquette ne correspond pas toujours à un glyphe réel (ex. `fi-rr-file-check` n'existe pas → `fi-rr-memo-circle-check`).
- Pas de bordure par défaut ; pas de hover si `clickable=false`
- Combinaisons WCAG AA respectées — voir [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md)

#### `HeaderComponent`
**Sélecteur**: `app-header`
**Fichiers**: `header/`
**Description**: Barre de navigation principale de l'application.

```html
<app-header></app-header>
```

### Kit UI Components (issues #298-#304)

Composants issus de la revue design 05/2026, à utiliser à la place des composants Material équivalents pour respecter le kit UI.

#### `SearchBarComponent` (#298)
**Sélecteur**: `app-search-bar` — **Fichiers**: `search-bar/`

Barre de recherche unifiée avec 2 variantes. Texte d'aide AVANT le champ (accessibilité).

```html
<!-- Auto-filtre (défaut) -->
<app-search-bar [(value)]="query" placeholder="Rechercher un site..."></app-search-bar>

<!-- Manuel avec bouton -->
<app-search-bar
  mode="manual"
  helpText="Entrez au moins 2 caractères"
  placeholder="Rechercher un plan..."
  (search)="onSearch($event)">
</app-search-bar>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `mode` | `'auto' \| 'manual'` | `'auto'` | `auto` filtre instantané, `manual` avec bouton |
| `value` | `string` | `''` | Two-way binding |
| `placeholder` | `string` | `''` | Placeholder du champ |
| `helpText` | `string?` | — | Texte d'aide AVANT le champ |
| `ariaLabel` | `string` | `'Rechercher'` | Label lecteur d'écran |
| `disabled` | `boolean` | `false` | — |

Outputs : `valueChange`, `search` (manuel), `cleared`.

#### `CheckboxComponent` (#299)
**Sélecteur**: `app-checkbox` — **Fichiers**: `checkbox/`

Checkbox custom (carré arrondi, **sans cercle Material**). Compatible Reactive Forms.

```html
<app-checkbox [(checked)]="agreed" label="J'accepte"></app-checkbox>
<app-checkbox [(checked)]="copy" label="Sites associés" mention="Copie les associations site-plan"></app-checkbox>
<app-checkbox formControlName="active" label="Site actif"></app-checkbox>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `checked` | `boolean` | `false` | Two-way binding |
| `label` | `string` | `''` | Label principal |
| `mention` | `string?` | — | Texte mention sous le label |
| `disabled` | `boolean` | `false` | — |

#### `FormFieldComponent` (#300)
**Sélecteur**: `app-form-field` — **Fichiers**: `form-field/`

Wrapper pour champs compacts : label **au-dessus** du champ, asterisque rouge si requis, état erreur. Plus dense que Material.

```html
<app-form-field label="Nom du site" required>
  <input type="text" formControlName="name" />
</app-form-field>

<app-form-field
  label="Surface (ha)"
  helpText="Saisissez un nombre entier"
  suffix="ha"
  [error]="form.controls.surface.touched && form.controls.surface.errors?.['min'] ? 'La surface doit être ≥ 0' : null">
  <input type="number" formControlName="surface" />
</app-form-field>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `label` | `string` | `''` | Label au-dessus du champ |
| `required` | `boolean` | `false` | Ajoute astérisque rouge |
| `helpText` | `string?` | — | Aide ENTRE label et champ |
| `error` | `string \| null` | — | Message d'erreur (active l'état erreur) |
| `suffix` | `string?` | — | Suffixe (ex: 'ha', '€') |

Le `<input>`/`<select>`/`<textarea>` est projeté dans le composant — utiliser `formControlName` ou `ngModel` directement sur l'élément projeté.

#### `StepperComponent` (#301)
**Sélecteur**: `app-stepper` — **Fichiers**: `stepper/`

Stepper pour processus multi-étapes (import en masse, etc.).

```html
<app-stepper
  [steps]="[
    { id: 1, label: 'Fichier', completed: true },
    { id: 2, label: 'Correspondance', completed: true },
    { id: 3, label: 'Vérification' },
    { id: 4, label: 'Résultats' }
  ]"
  [currentStep]="3"
  (stepClick)="goToStep($event)">
</app-stepper>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `steps` | `StepperStep[]` | `[]` | `{ id, label, completed? }` |
| `currentStep` | `string \| number` | `1` | Étape active (ID ou index 1-based) |
| `allowGoBack` | `boolean` | `true` | Étapes complétées cliquables |

#### `EntityTileComponent` (#302)
**Sélecteur**: `app-entity-tile` — **Fichiers**: `entity-tile/`

Tuile compacte pour site / utilisateur / organisme (vue d'ensemble plan, modales).

```html
<app-entity-tile
  icon="fi-rr-marker"
  name="Réserve Naturelle du Lac de Remoray"
  subtitle="Réserves Naturelles de France">
  <button tileAction class="link-default">Demander l'accès</button>
</app-entity-tile>

<app-entity-tile icon="fi-rr-user" name="Marie Dupont" subtitle="marie@test.fr" [clickable]="true" (tileClick)="open()">
  <app-tag tileAction variant="warning" label="Référent" />
</app-entity-tile>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `icon` | `string` | `'fi-rr-document'` | Classe Flaticon |
| `name` | `string` | `''` | Nom principal (bold) |
| `subtitle` | `string?` | — | Sous-info (gris foncé) |
| `clickable` | `boolean` | `false` | Active hover + cursor + tileClick |

Action à droite via `<element tileAction>` (slot).

#### `AccordionComponent` (#303)
**Sélecteur**: `app-accordion` — **Fichiers**: `accordion/`

Accordéon générique avec chevron haut/bas conforme #297. 4 variantes (default, enjeu, fcr, subtle), 3 tailles (sm, md, lg).

```html
<app-accordion title="Détails du protocole">
  <p>Contenu déplié...</p>
</app-accordion>

<app-accordion variant="enjeu" title="Enjeu 3 : Préservation" [(expanded)]="isOpen">
  <i accordionIcon class="fi fi-rr-mountains"></i>
  <button accordionActions class="icon-btn-flat" (click)="onEdit($event)">
    <i class="fi fi-rr-pencil"></i>
  </button>
  <p>Détails…</p>
</app-accordion>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `title` | `string` | `''` | Titre header |
| `variant` | `'default' \| 'enjeu' \| 'fcr' \| 'subtle'` | `'default'` | Style visuel |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | Espacement |
| `expanded` | `boolean` | `false` | État (two-way binding via expandedChange) |
| `disabled` | `boolean` | `false` | — |

Slots : `[accordionIcon]` (icône à gauche du titre), `[accordionActions]` (boutons à droite, à côté du chevron), corps par défaut.

#### `AnchorNavComponent` (#304)
**Sélecteur**: `app-anchor-nav` — **Fichiers**: `anchor-nav/`

Navigation interne par ancres : boutons tertiaires bleu-vert séparés par `/`. Scroll smooth automatique vers la section.

```html
<app-anchor-nav
  [items]="[
    { id: 'overview', label: 'Vue d\'ensemble' },
    { id: 'info', label: 'Informations' },
    { id: 'organismes', label: 'Organismes' },
    { id: 'users', label: 'Utilisateurs' },
    { id: 'plans', label: 'Plans de gestion' }
  ]"
  [activeId]="currentSection">
</app-anchor-nav>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `items` | `AnchorNavItem[]` | `[]` | `{ id, label, icon? }` |
| `activeId` | `string?` | — | ID de l'item actif (mise en évidence) |
| `scrollOnClick` | `boolean` | `true` | Scroll smooth automatique vers `#id` |

Les sections cibles doivent avoir un `id` correspondant (ex: `<section id="overview">...`).

### Bibliothèque de graphiques (`shared/components/charts/`)

Composants graphiques **standalone, data-driven, sans dépendance externe** (SVG maison), issus de la page Figma « Graphiques » (kit UI). Palette du design system uniquement. Importer via le barrel `shared/components/charts`. Utilisés par la page **Bilan de la gestion** (`features/plans/suivis/plan-bilan.component`).

| Composant | Sélecteur | Rôle |
|-----------|-----------|------|
| `ChartCardComponent` | `app-chart-card` | Tuile graphique (titre capitales + sous-titre + slot `[cardActions]`). `[accent]="true"` = fond vert pâle. |
| `ChartLegendComponent` | `app-chart-legend` | Légende (pastille aplat/motif + libellé + valeur). `[inline]` pour disposition horizontale. |
| `DonutChartComponent` | `app-donut-chart` | Donut évidé : `[slices]` (`DonutSlice[]`), infobulle au survol, légende, motifs hachurés. |
| `BarChartComponent` | `app-bar-chart` | Barres `mode="simple\|stacked\|grouped"`, grille Y « propre », motifs par segment. |
| `LineChartComponent` | `app-line-chart` | Courbes + bande de confiance (min–max pointillé + écart-type ombré). |
| `RadarChartComponent` | `app-radar-chart` | Radar avec fond dégradé arc-en-ciel, grille graduée, points colorés par score. |

**Motifs (hachures / croix / points)** : chaque `DonutSlice`/`BarSegment` accepte `pattern?: 'solid'\|'hatch'\|'cross'\|'dots'` (aplat blanc + traits de la couleur). `ChartDefsComponent` (`<svg:g ccdChartDefs [defs]="…">`) génère les `<pattern>` uniques par instance via `PatternRegistry`.

**Helpers** (`chart.types.ts`) : `SCORE_PALETTE` (0..5), `scoreColor(v)` (couleur du score le plus proche), `nextChartUid()`.

**Séries par année du Bilan** : les graphiques « évolution » sont alimentés par `GET /api/plans/realisations/bilan-series/{plan_id}/` (`RealisationService.bilanSeries()`), aligné sur `years` (plan.annee_debut..annee_fin), filtrable par `?enjeu_id=` :
- `indicateurs_evolution` : `mean`/`min`/`max`/`std` des scores d'indicateurs par année (dernière mesure de chaque métrique dans l'année) → `LineChartComponent` + bande de confiance
- `rh_par_annee` : `previsionnel`/`realise` (jours) par année → `BarChartComponent` mode `grouped` (cohérent avec les totaux RH de `/bilan/`)
- `actions_par_annee.niveaux` : counts par niveau × année → `BarChartComponent` mode `stacked`
Ces tuiles ne s'affichent qu'en portée **Global / Mi-parcours** (masquées en Annuel).

## Common Development Commands

### Project Setup (Current Implementation)

```bash
# 1. Copier le fichier d'environnement (optionnel, des valeurs par défaut existent)
cp .env.example .env

# 2. Lancer tous les services
docker compose up -d

# 3. (Optionnel) Créer les données de test
docker compose exec web python manage.py seed_testdata
```

**Ce qui est lancé automatiquement :**
- PostgreSQL avec PostGIS + création des schémas (dont `taxonomie` et `ref_habitats`)
- Redis (cache + broker Celery)
- Django : migrations, import nomenclatures, **import HabRef**, **import TaxRef**, création superuser, collectstatic, runserver
- Frontend Angular : npm install + serveur de développement
- Celery worker + beat (tâches asynchrones)
- Mailpit (capture des emails en dev)

**Pour accélérer le démarrage en dev/tests**, ajouter `TAXREF_IMPORT_OPTS=--lite` dans `.env` (~8k taxons au lieu de ~700k). Voir [docs/NOMENCLATURES.md](docs/NOMENCLATURES.md).

**⚠️ Conflit de ports :** Si un service tourne déjà sur votre machine, modifiez le port externe correspondant dans `.env` :
```bash
# Serveur web (Apache, Nginx) déjà sur le port 80
FRONTEND_PORT=8080

# Port 8000 déjà utilisé
DJANGO_PORT=8001

# PostgreSQL local déjà sur 5432
POSTGRES_EXTERNAL_PORT=5433

# Redis local déjà sur 6379
REDIS_EXTERNAL_PORT=6380
```
Ces variables ne changent que le port exposé sur la machine hôte. Les conteneurs Docker communiquent entre eux sur les ports internes par défaut.

### Development

```bash
# Backend (via Docker)
docker compose exec web python manage.py runserver

# Database migrations
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python create_superuser.py

# Create test data (Django management command)
docker compose exec web python manage.py seed_testdata          # Create all test data
docker compose exec web python manage.py seed_testdata --reset  # Remove test data
docker compose exec web python manage.py seed_testdata --dry-run # Preview changes
docker compose exec web python manage.py seed_testdata --only=users,plans  # Selective seeding

# Import/Update nomenclatures (reference data - lancé automatiquement au démarrage)
docker compose exec web python manage.py import_nomenclatures                 # Import (skip si déjà fait)
docker compose exec web python manage.py import_nomenclatures --force         # Upsert (ajouter + mettre à jour)
docker compose exec web python manage.py import_nomenclatures --force --prune # Upsert + supprimer les obsolètes

# Import référentiels INPN (voir docs/NOMENCLATURES.md pour le détail)
docker compose exec web python manage.py import_habref                 # HabRef (auto au démarrage)
docker compose exec web python manage.py import_taxref                 # TaxRef v18 complet (~700k taxons)
docker compose exec web python manage.py import_taxref --lite          # TaxRef allégé (~8k taxons, pour dev/tests)
docker compose exec web python manage.py import_taxref --version 17    # Version spécifique
docker compose exec web python manage.py import_taxref --force         # Forcer le rechargement
docker compose exec web python manage.py refresh_taxref_views          # Rafraîchir vues matérialisées

# Test nomenclatures import
docker compose exec web python test_nomenclatures.py

# Access Django shell
docker compose exec web python manage.py shell
```

### Logging

```bash
# Logs en temps réel (filtrés sur les requêtes et erreurs)
docker compose logs -f web | grep -E "(Request|AUDIT|ERROR)"

# Tous les logs en temps réel
docker compose logs -f web
```

**Configuration des logs** (variables d'environnement) :
- `LOG_LEVEL` : Niveau de log (DEBUG, INFO, WARNING, ERROR) - défaut: INFO
- `LOG_DIR` : Répertoire des logs - défaut: /app/logs
- `LOG_SQL` : Activer les logs SQL (true/false) - défaut: false

**Fichiers de logs** (production uniquement) :
- `django.log` : Logs généraux (rotation 10x10MB)
- `error.log` : Erreurs uniquement
- `audit.log` : Actions utilisateur (POST/PUT/DELETE)

**Correlation ID** : Chaque requête HTTP reçoit un UUID unique (`X-Correlation-ID`) propagé dans tous les logs pour faciliter le debugging.

### ⚠️ Architecture Seeders (Pour Développeurs)

> **Attention** : Cette section concerne l'architecture interne du système de données de test. Réservé aux développeurs.

La commande `seed_testdata` utilise une architecture modulaire avec des seeders indépendants :

```
backend/apps/core/management/commands/
├── seed_testdata.py              # Orchestrateur (~300 lignes)
└── seeders/
    ├── __init__.py               # Registry + validation des dépendances
    ├── base.py                   # Classe abstraite BaseSeeder
    ├── context.py                # SeederContext (partage de données)
    ├── signals.py                # Gestion centralisée des signaux (28)
    ├── modules_seeder.py         # 4 modules
    ├── groups_seeder.py          # 4 groupes Django
    ├── organismes_seeder.py      # 5 organismes
    ├── sites_seeder.py           # 7 sites avec géométries PostGIS
    ├── users_seeder.py           # 14 utilisateurs
    ├── plans_seeder.py           # 9 plans de gestion + chaînes de versions
├── ventilation_plans_seeder.py  # 6 plans « Ventilation — … » (1 par mode de ventilation)
    ├── pending_users_seeder.py   # 3 PendingUser
    ├── validation_requests_seeder.py  # 22 demandes de validation
    ├── notifications_seeder.py   # 21+ notifications
    ├── error_logs_seeder.py      # 8 logs d'erreur
    └── activity_logs_seeder.py   # 25+ logs d'activité
```

**Composants clés :**

| Composant | Description |
|-----------|-------------|
| `BaseSeeder` | Classe abstraite avec `seed()`, `reset()`, `get_dry_run_summary()` |
| `SeederContext` | Partage de données entre seeders (`set()`, `get()`, `require()`) |
| `signals_disabled()` | Context manager pour désactiver les 28 signaux pendant le seeding |
| `SEEDER_CLASSES` | Liste ordonnée par dépendances (tri topologique) |

**Graphe de dépendances :**
```
modules, groups, organismes (indépendants)
    │  (Note: les nomenclatures sont importées séparément via `python manage.py import_nomenclatures`)
    │
    ├── sites (deps: organismes)
    ├── users (deps: organismes, sites, groups)
    ├── pending_users (deps: organismes)
    ├── plans (deps: users, sites)
    ├── validation_requests (deps: users, sites, plans, organismes)
    ├── notifications (deps: users, sites, plans, organismes, validation_requests)
    ├── error_logs (deps: users)
    └── activity_logs (deps: users, sites, plans, organismes, validation_requests)
```

**Option `--only` :** Permet un seeding sélectif avec résolution automatique des dépendances.
```bash
# Crée uniquement users et plans (+ leurs dépendances automatiquement)
docker compose exec web python manage.py seed_testdata --only=users,plans
```

**Ajouter un nouveau seeder :**
1. Créer `seeders/mon_seeder.py` héritant de `BaseSeeder`
2. Définir `name` et `dependencies`
3. Implémenter `seed()`, `reset()`, `get_dry_run_summary()`
4. Ajouter la classe dans `SEEDER_CLASSES` de `__init__.py`

### Testing

> **Documentation complète** : Voir [`docs/TESTING.md`](docs/TESTING.md) pour le guide détaillé des tests.

#### Résumé de la couverture

| Stack | Framework | Tests | Couverture |
|-------|-----------|-------|------------|
| Backend | pytest + pytest-django + Factory Boy | 356 | 56% |
| Frontend (unitaires) | Jest + jest-preset-angular | 132 | 7% |
| **Frontend (E2E)** | **Playwright** | **431** | **Admin + Features + Enjeux + Plans + Access** |
| **Total** | | **~919** | |

#### Backend (pytest)

```bash
# Via Docker (recommandé)
docker compose exec web pytest tests/

# Avec couverture HTML
docker compose exec web pytest tests/ --cov=apps --cov-report=html

# Tests unitaires uniquement
docker compose exec web pytest tests/ -m unit

# Tests d'intégration uniquement
docker compose exec web pytest tests/ -m integration

# Un fichier spécifique
docker compose exec web pytest tests/integration/test_api_users.py -v

# Un test spécifique
docker compose exec web pytest tests/integration/test_api_users.py::TestUsersListEndpoint -v
```

**Structure des tests backend :**
```
backend/tests/
├── factories/           # Factory Boy (UserFactory, PlanGestionFactory, ActivityLogFactory, etc.)
├── apps/               # Tests unitaires
│   ├── users/          # test_models.py, test_permissions.py, test_middleware.py
│   ├── plans/          # test_views.py, test_filters.py
│   ├── core/           # test_activity.py (45 tests - model, service, API, signals)
│   └── notifications/  # test_email_integration.py (tests envoi email réel)
└── integration/        # Tests API
    ├── test_api_auth.py
    ├── test_api_users.py
    ├── test_api_org_sites.py
    ├── test_api_plans.py
    └── test_site_duplicates.py  # Détection doublons INPN et noms similaires
```

#### Tests d'intégration email (Mailpit)

> **Documentation complète** : Voir [`docs/EMAIL_CONFIGURATION.md`](docs/EMAIL_CONFIGURATION.md)

En développement, **Mailpit** capture tous les emails (interface web : http://localhost:8025).

```bash
# Démarrer les services (inclut Mailpit)
docker compose up -d

# Lancer les tests d'intégration email (utilisent Mailpit automatiquement)
docker compose exec web pytest tests/apps/notifications/test_email_integration.py -m email_integration -v

# Tester manuellement l'envoi d'un email
docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Message de test', 'noreply@cicada.fr', ['test@example.com'])
print('Email envoyé! Voir http://localhost:8025')
"
```

**Tests disponibles (27 tests) :**
- `TestNotificationEmailIntegration` : welcome, validation_request, account_deactivated, site_association
- `TestRegistrationEmailIntegration` : pending, approved, rejected
- `TestFullWorkflowEmailIntegration` : workflow complet inscription, accès site
- `TestEmailTemplatesIntegration` : test des 15 types de notifications

#### Frontend (Jest)

```bash
cd frontend

# Tous les tests
npm test

# Mode watch (développement)
npm run test:watch

# Avec couverture
npm run test:coverage
```

**Tests frontend disponibles :**
- `auth.service.spec.ts` - Login, logout, tokens, rôles, impersonation (27 tests)
- `auth.guard.spec.ts` - authGuard, roleGuard, adminGuard, guestGuard (15 tests)
- `auth.interceptor.spec.ts` - Injection token, refresh 401 (13 tests)
- `deactivate-user-modal.component.spec.ts` - Modal de désactivation utilisateur (21 tests)
- `score-icon.component.spec.ts` - Composant ScoreIcon (22 tests)
- `action-icon.component.spec.ts` - Composant ActionIcon (10 tests)
- `navigation-tile.component.spec.ts` - Composant NavigationTile (24 tests)

#### Frontend E2E (Playwright)

```bash
cd frontend

# Tous les tests E2E (headless)
npm run e2e

# Interface visuelle Playwright
npm run e2e:ui

# Tests visibles dans le navigateur
npm run e2e:headed

# Mode debug
npm run e2e:debug
```

**Prérequis** : Stack Docker en cours (`docker compose up -d`) + données de test (`seed_testdata`).

**Tests E2E disponibles (431 tests) :**

*Authentication & Access (26 tests) :*
- `auth/login.spec.ts` - Login valide/invalide, champs vides, returnUrl (5 tests)
- `auth/logout.spec.ts` - Déconnexion, suppression tokens (3 tests)
- `auth/register.spec.ts` - Inscription, validation, email doublon (5 tests)
- `access/role-access.spec.ts` - Contrôle d'accès par rôle, redirection referent/user (8 tests)
- `access/data-scope.spec.ts` - Scope données par organisme, isolation users/sites (5 tests)

*Admin (51 tests) :*
- `admin/users-list.spec.ts` - Liste utilisateurs, recherche, filtres (6 tests)
- `admin/users-actions.spec.ts` - Activation/désactivation, assign site (5 tests)
- `admin/users-sites.spec.ts` - Associations sites/plans (4 tests)
- `admin/sites-list.spec.ts` - Liste sites, recherche, filtres (5 tests)
- `admin/sites-crud.spec.ts` - Création site, validation formulaire (5 tests)
- `admin/sites-orgs.spec.ts` - Liens organismes/sites (3 tests)
- `admin/validations.spec.ts` - Liste, filtres, approbation (6 tests)
- `admin/validation-workflow.spec.ts` - Workflow multi-utilisateurs : demande → vue admin → approbation/rejet → vérification (10 tests)
- `admin/organismes.spec.ts` - Grille, détail, recherche (4 tests)
- `admin/dashboard.spec.ts` - Statistiques, accès (3 tests)

*Enjeux & Arborescence (152 tests) :*
- `features/enjeux.spec.ts` - Navigation, détail, CRUD facteurs/pressions, onglets OLT/Opérations, CRUD OLT/NE (58 tests)
- `features/enjeu-forms.spec.ts` - Formulaires enjeu/FCR : création, édition, validation, champs conditionnels (28 tests)
- `features/enjeux-roles-access.spec.ts` - Accès par rôle : super admin, admin_og, referent, user, isolation cross-org (22 tests)
- `features/enjeux-olt-hierarchy.spec.ts` - Hiérarchie OLT : état actuel → OLT → NE, affichage, CRUD imbriqué (17 tests)
- `features/enjeux-operations-hierarchy.spec.ts` - Hiérarchie opérations : métriques, opérations, CRUD, liens (21 tests)
- `features/enjeux-cascade-delete.spec.ts` - Suppression en cascade : enjeu, facteur, pression avec confirmation (6 tests)

*Plans (71 tests) :*
- `features/plan-create.spec.ts` - Création plan : formulaire, sélection sites, rédacteurs, permissions (31 tests)
- `features/plan-views.spec.ts` - Vues plan : tableau de bord, timeline, bilan, suivi actions (28 tests)
- `features/plans-list.spec.ts` - Liste plans, recherche, filtres, tri (12 tests)

*Opérations & Suivis (53 tests) :*
- `features/operations.spec.ts` - CRUD opérations, lien métriques, filtres, tri (30 tests)
- `features/inventaires.spec.ts` - CRUD suivis/inventaires, formulaires, listes (23 tests)

*Autres Features (68 tests) :*
- `features/profile.spec.ts` - Page profil, infos utilisateur, RGPD, mes demandes (18 tests)
- `features/activity.spec.ts` - Timeline activité, onglets par rôle, filtres, pagination (15 tests)
- `features/bulk-import.spec.ts` - Import en masse sites, stepper, upload, mapping (11 tests)
- `features/impersonation.spec.ts` - Impersonation admin, bannière, navigation (9 tests)
- `features/duplicate-detection.spec.ts` - Détection doublons INPN et noms similaires (8 tests)
- `features/notifications.spec.ts` - Liste notifications, marquer lu, état vide (7 tests)

*Navigation (4 tests) :*
- `navigation/navigation.spec.ts` - Header, sidebar, liens (4 tests)

**Helpers E2E :**
- `helpers/plan.helper.ts` - Helpers API authentifiés (findPlan, findFirstEnjeu, apiGet/Post/Patch/Delete)
- `pages/*.page.ts` - Page objects (EnjeuxPage, AdminUsersPage, PlanCreatePage, etc.)
- `fixtures/auth.fixture.ts` - Fixtures Playwright avec sessions pré-authentifiées par rôle

#### CI/CD

Les tests s'exécutent automatiquement via GitHub Actions sur chaque push/PR vers `main` ou `develop`, et sur les tags de release `v*`.
Configuration : `.github/workflows/tests.yml`

#### Tests de packaging (avant release, local uniquement)

Des tests spécifiques valident l'installation et la mise à jour du package Debian `.deb`. Ils ne sont **pas en CI** car ils nécessitent un hyperviseur (Multipass/VM) incompatible avec GitHub Actions.

```bash
cd packaging

# Tests rapides en conteneurs Docker (fichiers, services, interface web)
./test-install-quick.sh     # ~30s  - fichiers installés
./test-install.sh           # ~5min - fichiers + services systemd
./test-install-web.sh       # ~5min - interface web Flask

# Test complet en VM Multipass (upgrade v1→v2, systemd réel, Docker réel)
./test-upgrade-vm.sh --from 0.1.12 --to 0.1.13   # ~15min première fois, ~3min ensuite
./test-upgrade-vm.sh --cleanup                     # Supprimer la VM
```

**Quand les lancer** : avant de publier un nouveau package `.deb` (release). Voir [`packaging/TESTING.md`](packaging/TESTING.md).

### Frontend Development

```bash
# Install dependencies
cd frontend && npm install

# Development server
npm start  # http://localhost:4200

# Build for production
npm run build:prod

# Generate component
ng generate component components/my-component

# Generate service
ng generate service services/my-service
```

### Code Quality

```bash
# Backend
black backend/  # Format code
isort backend/  # Sort imports
flake8 backend/  # Lint code

# Frontend
npm run lint
npm run format
```

## High-Level Architecture

### Frontend Architecture

The Angular application follows a modular structure:

- **core module**: Singleton services (auth, API client, interceptors)
- **shared module**: Reusable components, pipes, directives, design system components
- **feature modules**: Plans, users, auth (lazy loaded)
- **State management**: RxJS-based with services as stores
- **Design System**: Voir section "Technology Stack > Frontend" et [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md)

#### Composants SCSS disponibles

**`_variables.scss`** - Tokens de design
- Couleurs: `$primary-color`, `$secondary-yellow`, `$secondary-orange-salmon`, `$secondary-terra-cotta`, `$secondary-pale-green`
- Scores: `$score-very-bad`, `$score-bad`, `$score-neutral`, `$score-good`, `$score-very-good`
- Status: `$success-color`, `$error-color`, `$warning-color`, `$info-color`
- Neutres: `$black`, `$gray-dark`, `$gray`, `$gray-light`, `$gray-lighter`, `$beige`, `$white`
- Spacing: `$spacing-xxs` (4px) → `$spacing-xxl` (48px)
- Border radius: `$border-radius-sm` (4px), `$border-radius-pill` (24px), `$border-radius-round` (50%)

**`_typography.scss`** - Classes typographiques
- Headings: `h1`-`h4`, `.h1`-`.h4`
- Texte: `.subtitle`, `.text-regular`, `.text-bold`, `.text-small`, `.text-mention`
- Liens: `.link-default`, `.link-survol`, `.link-inactif`
- Listes: `.list-custom` (puces personnalisées)
- Couleurs: `.text-primary`, `.text-success`, `.text-error`, `.text-muted`, etc.

**`_material-overrides.scss`** - Angular Material personnalisé
- Boutons: `.btn-sm`, `.btn-lg` (tailles)
- Chips/Tags: `.status-success`, `.status-valide`, `.status-error`, `.status-warning`, `.status-info`, `.status-neutre`
- Chips scores: `.score-very-bad`, `.score-bad`, `.score-neutral`, `.score-good`, `.score-very-good`
- Chips priorité: `.priority-1`, `.priority-2`, `.priority-3`
- Accordéons: `.border-primary`, `.border-secondary`, `.border-success`, `.border-error`

**`_components.scss`** - Composants custom (non Material)
- Jauges: `.gauge`, `.gauge-not-started`, `.gauge-mid-progress`, `.gauge-completed`, `.gauge-exceeded`
- Actions: `.action-indicator`, `.action-planned`, `.action-planned-realized`, `.action-planned-partial`, `.action-realized-unplanned`, `.action-partial-unplanned`
- Scores emoji: `.score-emoji` avec variantes
- Tuiles: `.tile`, `.tile-image`, `.tile-content`, `.tile-title`
- Info blocks: `.info-block`, `.info-block-success`, `.info-block-warning`, `.info-block-error`
- Breadcrumb: `.breadcrumb`, `.breadcrumb-home`, `.breadcrumb-item`
- Barre action: `.action-bar`, `.action-bar.with-sidebar`
- Menu latéral: `.sidebar-menu`, `.sidebar-menu-item`, `.sidebar-menu-item.active`, `.sidebar-menu-item.submenu`
- Listes: `.list-bullets`, `.documents-list`
- Pagination: `.pagination-custom`, `.pagination-custom-btn`
- Contrôles: `.segmented-control`

**`_filters.scss`** - Filtres et recherche
- Panneau filtres: `.filter-panel`, `.filter-panel-horizontal`, `.filter-panel-collapsible`
- Filtres actifs: `.active-filters`, `.filter-chip`
- Sidebar filtres: `.sidebar-filters`
- Barre recherche: `.search-filter-bar`
- Quick filters: `.quick-filters`, `.quick-filter-btn`
- Pagination: `.pagination-container`, `.pagination`, `.page-btn`
- Tri: `.sort-controls`, `.view-switcher`
- Mobile: `.filter-drawer`

**`styles.scss`** - Utilitaires globaux
- Spacing: `.m-{size}`, `.p-{size}`, `.mx-{size}`, `.my-{size}`, `.px-{size}`, `.py-{size}`
- Display: `.d-none`, `.d-flex`, `.d-block`, `.d-grid`
- Flex: `.flex-row`, `.flex-column`, `.justify-content-*`, `.align-items-*`
- Background: `.bg-primary`, `.bg-success`, `.bg-error`, `.bg-score-*`
- Border: `.rounded`, `.rounded-sm`, `.rounded-lg`, `.rounded-circle`
- Shadow: `.shadow-sm`, `.shadow`, `.shadow-lg`

### Django Apps Structure

The backend follows a modular architecture with distinct Django apps:

- **authentication**: JWT auth with djangorestframework-simplejwt, login/logout/refresh endpoints, public registration
- **users**: User management, organizations (bib_organismes), role-based permissions system
- **plans**: Management plans CRUD, multi-site support, file attachments *(API REST complète)*
- **notifications**: Validation requests system, email notifications, Celery async tasks
- **taxonomy**: Référentiel taxonomique TaxRef (INPN) — schemas `taxonomie`, autocomplete trigramme, import via COPY
- **habitats**: Référentiel des habitats HabRef (INPN) — schema `ref_habitats`, autocomplete, correspondances
- **campanule**: Catalogue des protocoles CAMPanule (INPN/PatriNat) — schema `ref_campanule`, protocoles/méthodes/techniques, autocomplete. **Côté UI on parle de « protocole standardisé » (plus de « Campanule »).** Inclut aussi les 5 protocoles standardisés **MhéO** (#565, zones humides) chargés dans les mêmes tables via `data_mheo.py` (codes `>= 900000`, cf. `MHEO_BASE`)
- **geo**: Découpage administratif (régions/départements) — schema `ref_geo`, structure GeoNature (`bib_areas_types` + `l_areas`), rattachement des sites calculé par intersection PostGIS (`cor_site_area`). Voir [docs/NOMENCLATURES.md](docs/NOMENCLATURES.md#découpage-administratif-ref_geo)
- **search**: Index de recherche du contenu des plans — schema `ccd_search`, table dénormalisée + `tsvector`/`pg_trgm`. Alimente l'**exploration des données**. Voir [docs/RECHERCHE.md](docs/RECHERCHE.md)
- **api**: Public API endpoints with token auth *(à venir)*
- **core**: Shared utilities, base models (nomenclatures), common middleware
  - See [docs/NOMENCLATURES.md](docs/NOMENCLATURES.md) for reference data management (nomenclatures, TaxRef, HabRef, CAMPanule)

### Database Schema Design

The application uses PostgreSQL with PostGIS and follows a multi-schema approach compatible with GeoNature and ODASE.
The application is named **Cicada** (`ccd_` prefix for custom schemas).

1. **utilisateurs schema** (GeoNature compatible): User management
   - `t_roles`: User accounts with email as unique identifier
   - `bib_organismes`: Management organizations
   - `cor_role_ep`: User-Site relationships with permissions
   - Django auth tables (auth_group, auth_permission, etc.)

2. **referentiels schema** (ODASE compatible): Protected areas
   - `t_espace_protege`: Protected areas with PostGIS geometries
   - `cor_ep_og`: Organization-Site relationships

3. **ref_nomenclatures schema** (GeoNature compatible): Reference data
   - `bib_nomenclatures_types`: Nomenclature type definitions
   - `t_nomenclatures`: Reference lists and categories

4. **ref_geo schema** (GeoNature compatible): Geographic references
   - Reserved for future use (administrative boundaries, communes, etc.)

5. **general schema** (ODASE compatible): Management plans
   - `t_plan_gestion`: Management plans
     - `plan_parent_id` FK self → chaîne de versions (plan initial → évaluation → plan révisé)
     - `id_type_document` FK nomenclature → type de document (PLAN_INITIAL, EVAL_MI_PARCOURS, PLAN_REVISE)
   - `cor_ep_pg`: Many-to-many between plans and sites
   - `t_plan_gestion_referents`: Plan referents relationships

6. **fichiers schema** (ODASE compatible): File attachments
   - `t_fichiers`: File attachments for management plans

7. **ccd_commons schema** (Cicada): Common utilities
   - `t_modules`: Application modules
   - `t_impersonation_log`: Admin impersonation audit

8. **ccd_notifications schema** (Cicada): Notifications system
   - `t_notifications`: User notifications
   - `t_validation_requests`: Validation workflow
   - `t_pending_users`: Registration requests

9. **taxonomie schema** (GeoNature compatible): Taxonomic reference (TaxRef)
   - `taxref`: Main taxonomy table (~700k taxa, PK: cd_nom)
   - `bib_taxref_rangs`: Taxonomic ranks
   - `bib_taxref_habitats`: Habitat types
   - `bib_taxref_statuts`: Taxonomic statuses
   - `t_meta_taxref`: Referential versioning
   - `vm_taxref_list_forautocomplete`: Materialized view with trigram index

10. **ref_habitats schema** (GeoNature compatible): Habitat reference (HabRef)
    - `habref`: Main habitat table (PK: cd_hab)
    - `typoref`: Habitat typologies (EUNIS, Corine Biotope, etc.)
    - `habref_corresp_hab`: Cross-typology correspondences
    - `habref_corresp_taxon`: Habitat-taxon correspondences
    - `autocomplete_habitat`: Denormalized table with trigram index

11. **ref_campanule schema** (Cicada/INPN): Catalogue des protocoles CAMPanule
    - `protocoles`: Protocoles de collecte (~224, PK: cd_protocole)
    - `methodes`: Méthodes de collecte (~15, PK: cd_methode)
    - `techniques`: Techniques de collecte (~178, PK: cd_technique)
    - `attributs`: Vocabulaire contrôlé (domaine, objectif, cible, matériel)
    - `prot_echantillonnage`: Plans d'échantillonnage
    - `docs_web`: Références bibliographiques
    - `prot_*_rel`, `meth_*_rel`, `tech_*_rel`: Tables de correspondance N-N
    - `autocomplete_protocole`: Table dénormalisée avec index trigramme

12. **ref_geo schema** (GeoNature compatible): Découpage administratif
    - `bib_areas_types`: Types de zones (`REG`, `DEP`)
    - `l_areas`: 109 départements + 26 régions (géométrie 4326, `id_area_parent` = région du département)
    - `cor_site_area`: Rattachement site ↔ zone, calculé par intersection PostGIS (`source` : `intersect` / `nearest` / `manual`)

13. **ccd_search schema** (Cicada): Index de recherche de l'exploration des données
    - `t_recherche_contenu`: une ligne par objet explorable (enjeu, facteur, pression, objectif LT/OP, indicateur, action) d'un plan **validé/modifié/archivé**, avec facettes dénormalisées et deux `tsvector` **générés** (`search_titre` pour le mode « titres uniquement », `search_full` pour le mode élargi)

**Database Configuration**:
```python
# search_path configured in settings/base.py
OPTIONS = {
    'options': '-c search_path=utilisateurs,referentiels,ref_nomenclatures,ref_geo,general,fichiers,ccd_commons,ccd_notifications,ccd_search,taxonomie,ref_habitats,ref_inpg,ref_campanule,public'
}
```

## Key Implementation Patterns

### Authentication & Permissions

- **User Roles**: Super Admin > Rédacteur Principal > Admin Organisme > Utilisateur
- **Rédacteur Principal** : Rôle intermédiaire entre super_admin et admin_og. Accès global en lecture/écriture à tous les plans, enjeux, opérations, indicateurs, fichiers, **sites et organismes** (cross-organisme). Peut lier directement un site à un plan (sans validation). **Peut gérer le cycle de vie des plans** (valider/archiver/évaluation), au même titre que l'admin organisme, le super admin et le référent du plan (#346). Seul le super_admin peut attribuer ce rôle (endpoints `set-redacteur-principal` / `remove-redacteur-principal`). Méthodes : `user.is_redacteur_principal()`, `user.can_manage_plan_lifecycle()`. Frontend : `authService.isRedacteurPrincipal()`, `authService.hasGlobalAccess()`, `canEditPlan` et `canManageLifecycle` dans plan-detail. Page admin dédiée : `/administration/redacteurs-principaux`.
  - **Pattern backend (IMPORTANT)** : `is_admin_organisme()` retourne `True` pour le RP. Dans tout `get_queryset()`, toujours vérifier `is_redacteur_principal()` **AVANT** `is_admin_organisme()` pour éviter un scoping incorrect à l'organisme. Pattern : `if user.is_super_admin() or user.is_redacteur_principal(): return queryset_global`.
  - **Pattern frontend (IMPORTANT)** : Ne jamais utiliser `!isSuperAdmin() && isAdminOrganisme()` pour scoper par organisme — le RP serait inclus. Utiliser `!hasGlobalAccess() && isAdminOrganisme()` via le signal `authService.hasGlobalAccess` (= `isSuperAdmin() || isRedacteurPrincipal()`).
- **Référent** (access level, not a role): User is "referent" if assigned as site referent (`CorRoleSite.referent=True`) or plan referent (`PlanGestion.referents`)
- **Permissions cycle de vie des plans** : Les actions de changement de statut et création d'évaluation sont réservées aux **référents du plan spécifique** (vérifié via `plan.referents.filter(pk=user.pk)`), aux admin_og, super_admin **et au rédacteur principal** (#346 — `can_manage_plan_lifecycle()` retourne `True` pour le RP). Permission DRF `IsReferent` + vérification objet dans la vue.
- **Permission Model**: Role-based with hierarchical access and Django groups
- **JWT Implementation**: djangorestframework-simplejwt with 60min access + 7-day refresh tokens
- **Security Middleware**: 3 custom middleware for headers, permissions, and audit
- **API Protection**: All endpoints protected by default except `/api/auth/`
- **Permission check methods**: `user.is_super_admin()`, `user.is_redacteur_principal()`, `user.can_manage_plan_lifecycle()`, `user.is_referent()`, `user.can_manage_site(site)`
- **DRF classes**: `IsSuperAdmin`, `IsAdminOrganisme`, `IsReferent`
- **Decorators**: `@require_super_admin`, `@require_admin_organisme`

### Geospatial Handling

- Always use PostGIS for spatial operations
- Store geometries in EPSG:4326, display in EPSG:2154 (Lambert-93)
- Use GeoJSON format for API responses
- Implement spatial indexes for performance

### Multi-tenancy & Relationships

- Management plans can span multiple protected areas
- Users belong to organizations with scoped permissions
- Soft delete for critical data (plans, sites)
- Audit trail for all plan modifications

## Critical Implementation Notes

1. **Database Migrations**: Always create reversible migrations
2. **API Design**: RESTful with consistent naming, pagination for lists > 20 items
3. **Frontend State**: Services as stores pattern, avoid NgRx for V0
4. **Testing**: Voir section "Testing" pour les détails. CI/CD via GitHub Actions.
5. **Security**: Input validation, output escaping, rate limiting
6. **Performance**: Redis caching for frequent queries, lazy loading for Angular modules
7. **Déploiement production** : Voir [docs/RELEASE_PROCEDURE.md](docs/RELEASE_PROCEDURE.md) pour la procédure complète (tag, build .deb, publication APT, déploiement serveur, pièges courants). Voir [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md) pour l'installation initiale et l'import des référentiels (TaxRef, HabRef, nomenclatures) sur base PostgreSQL externe.

## Django Administration Interface

### Access
- **URL**: http://localhost:8000/admin/
- **Login**: `admin` / `admin` (superuser)

### Features Implemented

#### Models Management
- **Users (Role)**: Complete user management with custom forms
  - Email-based authentication
  - Organization assignment
  - Staff/superuser permissions
  - User-Site relationships inline

- **Organizations (BibOrganismes)**: 
  - CRUD operations for managing organizations
  - Hierarchical structure support (parent organizations)
  - Contact information management

- **Sites**:
  - Geospatial support with interactive maps (PostGIS)
  - Site classification (RNN, RNR, PNR, ENS, etc.)
  - Surface area and geographic coordinates
  - Organization-Site relationships inline
  - **Contrainte unicité INPN** : Le champ `id_inpn` est unique en base de données
  - **Détection de doublons** lors de la création :
    - Si le code INPN saisi existe déjà → **alerte bloquante** avec message "Ce code INPN est déjà utilisé par un site existant"
    - Si le nom est similaire à un site existant → **suggestions non bloquantes** de sites similaires
    - L'utilisateur peut demander l'accès au site existant ou lier son organisme

- **Nomenclatures**: 
  - Reference data management
  - Hierarchical nomenclatures support
  - Type-based classification

#### Advanced Features
- **Autocomplete fields** for Foreign Keys
- **Inline editing** for relationships
- **Geographic interface** with maps for site geometry
- **Search and filtering** optimized for each model
- **Custom forms** for user creation/modification

### Test Data Available (via `python manage.py seed_testdata`)

Run `docker compose exec web python manage.py seed_testdata` to create:

- **5 Organizations**: RNF, CEN AURA, DREAL Nouvelle-Aquitaine, Parc Ecrins, OFB
- **7 Sites**: Camargue, Aiguilles Rouges, Grand-Voyeux, Vercors, Marais de Brouage, Scandola, Lac de Remoray
- **8 Users** with different roles:
  | Email | Role | Organization | Sites | Notes |
  |-------|------|--------------|-------|-------|
  | admin@test.fr | Super Admin | RNF | Referent: Camargue | |
  | admin.rnf@test.fr | Admin Organisme | RNF | Referent: Camargue, Aiguilles Rouges | |
  | admin.cen@test.fr | Admin Organisme | CEN AURA | Referent: Grand-Voyeux, Vercors | |
  | referent.camargue@test.fr | Utilisateur | RNF | Referent: Camargue | |
  | referent.vercors@test.fr | Utilisateur | CEN AURA | Referent: Vercors | |
  | user.rnf@test.fr | Utilisateur | RNF | Membre: Camargue, Aiguilles Rouges | Voit automatiquement les plans liés |
  | user.cen@test.fr | Utilisateur | CEN AURA | Membre: Grand-Voyeux, Vercors | Voit automatiquement les plans liés |
  | **test@example.com** | Utilisateur | RNF | Referent: Camargue | **Email pour tests SMTP** |

  **Password for all test users**: `Test123!`
- **Plans de Gestion (≥14)**: divers statuts (draft, valide, modifie, archive, avis_csrpn, comite_consultatif) avec associations sites/référents. Les chaînes Aiguilles Rouges et Vercors-Écrins exposent le statut `modifie` (plan révisé). Le plan *Grand-Voyeux 2022-2032* est seedé en `avis_csrpn` (workflow non-RNN) et le plan *Aiguilles Rouges 2027-2037* en `comite_consultatif` (workflow RNN, étape arrêté à venir) pour tester #277. Chaînes d'extension (#250 — prolongation = nouvelle version : v1 archivée → v2 étendue `modifie`) : *Scandola rang 2 2016-2025* (archive → étendu +2 ans, cumul max), *Grand-Voyeux RNR 2015-2024* (archive → RNR étendu +1 an, reconductible, #281), *Marais de Brouage ENS 2014-2023* (archive → ENS étendu +2 ans, #281). *Vercors 2014-2024* (validé + en_revision, `next_rang_plan` pointant sur *Vercors 2026-2036* draft, #278). Panel évaluation mi-parcours (#276, 6 variantes) : *Camargue eval 2005* (archive historique), *Camargue eval 2025* (draft), *Vercors-Écrins eval 2026* (draft), *Lac de Remoray eval 2022* (avis_csrpn), *Vercors eval 2020* (comite_consultatif), *Aiguilles Rouges eval 2023* (modifie + is_mi_parcours=True).
  - Chaînes de versions : plan archivé → plan actif (via `plan_parent`)
  - 1 plan d'évaluation mi-parcours (brouillon, version 1.2, lié au plan Aiguilles Rouges)
- **Plans « Ventilation — … » (6)** : un plan de gestion **par mode de ventilation budgétaire** (`Operation.ventilation_mode`), pour la recette de la programmation — *aucune ventilation*, *par organisme*, *par type de budget*, *par organisme et type de budget*, *par type de budget et type de poste*, *par organisme, type de budget et type de poste*. Seeder : `seeders/ventilation_plans_seeder.py` (`--only=ventilation_plans`).
  - Tous en **brouillon** (donc éditables), sur le site Camargue (2 organismes gestionnaires : RNF + OFB), années `année courante −2 → +2` (2 années de suivi réalisé, l'année en cours, 2 années de prévisionnel pur).
  - Contenu **identique** dans les 6 plans (1 enjeu → OLT → NE → indicateur → métrique, 3 actions CS/IP/PA, 5 postes dont bénévoles et prestataire, mêmes jours et mêmes composants de coût) : **seul le stockage de la donnée budgétaire change**. Les totaux affichés doivent donc être les mêmes d'un plan à l'autre (139 800 € prévus, 269 j dont 94 j de bénévolat) — toute différence est un bug de la vue.
  - Les modes « + type de poste » ne stockent **pas** `budget_fonctionnement` / `budget_investissement` (dérivés de leurs composants, cf. #624/#602) ; le coût salarial se recalcule via jours × `Poste.cout_jour`.
  - **Réglages du tableau budgétaire (#600)** : dès que le mode intègre le type de budget (les 4 derniers), deux cases s'affichent au-dessus du tableau de programmation — `Operation.declinaison_par_type_cout` (détail coût salarial / stage / prestataire / autres, **cochée par défaut** ; décochée → seules les enveloppes fonctionnement et investissement sont saisies à la main) et `Operation.cout_salarial_auto` (**cochée par défaut** = jours × coût jour ; décochée → coût salarial saisi, stocké dans `cout_salarial` / `cout_salarial_invest` sur l'année ou l'organisme). ⚠️ La 2e case n'est proposée que par les **deux modes « + type de poste »** : eux seuls déclinent le temps par poste, donc disposent d'un coût jour à multiplier. Dans `by_type` / `by_org_type` avec détail des coûts, le coût salarial est **toujours saisi** (le calcul n'aurait aucune donnée et figerait la ligne à 0) ; les modes sans détail des coûts restent en « calculé », leur enveloppe contenant déjà tout. Règle centralisée dans `shared/utils/operation-budget.ts` (`salaryOptionAvailable()` / `salaryIsComputed()`), utilisée par la fiche action ET le suivi. Le layout de saisie (fiche action **et** suivi) découle donc du mode **et** de la 1re case, plus du seul « type de poste ». Source de vérité des totaux : `shared/utils/operation-budget.ts` (front) et `services_export_finance.py` (back). Dans le jeu d'essai, les modes sans « type de poste » ont `declinaison_par_type_cout=False` (ils stockent des enveloppes), et le seul plan **« par organisme, type de budget et type de poste »** a `cout_salarial_auto=False` : il stocke un coût salarial « saisi » égal au calcul automatique (jours × coût jour), de sorte que les totaux des 6 plans restent identiques tout en couvrant ce réglage. C'est aussi le support de recette de la reprise du paramétrage d'une action à l'autre (#641).
  - `RealisationsSeeder` **ignore** ces actions (préfixe de code `CAM-VENT-`) : leur suivi est posé par le seeder lui-même, cohérent avec chaque mode.
  - **Suivi et protocoles (#642)** : l'action CS de chaque plan porte un `SuiviInventaire` (statut, objectif, cible, fréquence, outils) et **2 protocoles** — un standardisé (CAMPanule) et un libre non respecté avec justification. Sans eux, la section « Protocole & objectifs » de la fiche action et son export Excel seraient vides.
- **Django Groups**: Super Administrateurs, Administrateurs Organisme, Utilisateurs
- **Nomenclatures**: Importées automatiquement au démarrage via `import_nomenclatures` (types de sites, évaluations, rédacteurs, documents plan, suivis, enjeux, etc.)
- **Validation Requests (27)**: Demandes de test avec différents statuts
  - 5 demandes `plan_access` en attente (pour tester la section "Plans en attente")
  - Demandes `site_access`, `referent_validation`, `module_access`, etc.

### Authentication System (JWT)

JWT authentication is fully implemented and operational:

**Endpoints:**
- `POST /api/auth/login/` - Login with email/password → JWT tokens
- `POST /api/auth/refresh/` - Refresh access token
- `POST /api/auth/logout/` - Logout (blacklist refresh token)
- `GET /api/auth/me/` - Get current user info
- `GET /api/auth/health/` - Public health check
- `POST /api/auth/register/` - Public user registration (requires admin approval)
- `GET /api/auth/registration-status/` - Check registration request status

**Test credentials:** Voir section "Test Data Available" pour la liste complète des utilisateurs de test.

**Example usage:**
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}'

# Use token
curl -X GET http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer {access_token}"
```

## Django Development Guide

### Understanding Migrations

Django migrations track database schema changes automatically. Voir les commandes dans la section "Development" ci-dessus.

**Migration Structure:**
- Each app has its own `migrations/` folder
- `apps/users/migrations/` → User, Site, Organization models
- `apps/core/migrations/` → Nomenclature models
- Dependencies between apps are managed automatically

**Example Workflow:**
1. Add field to `Site` model in `apps/users/models.py`
2. Run `makemigrations` → creates `0003_site_new_field.py`
3. Run `migrate` → adds column to database
4. Update `admin.py` to show new field (optional)

### Django Admin System

The admin interface is automatically generated from your models with minimal setup:

**Basic Registration:**
```python
# In admin.py - Basic interface
from django.contrib import admin
from .models import Site

admin.site.register(Site)  # Instant CRUD interface!
```

**Advanced Customization:**
```python
# Custom admin with enhanced features
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('nom_site', 'surf_off', 'active')  # Columns
    list_filter = ('active', 'marin')                  # Filters
    search_fields = ('nom_site', 'id_local')          # Search
```

### Key Files Structure

**`admin.py`** - Admin interface customization
- Form layouts and validation
- List display configuration
- Search and filtering options
- Inline editing for relationships

**`apps.py`** - App configuration
```python
class UsersConfig(AppConfig):
    name = 'apps.users'           # Python import path
    verbose_name = 'Utilisateurs' # Admin display name
    # Can include initialization logic in ready() method
```

**`models.py`** - Database structure
- Model definitions become database tables
- Field changes trigger migration generation
- Relationships define foreign keys

**`migrations/`** - Database version control
- Auto-generated when models change
- Applied in sequence to update database
- Should never be edited manually

### Development Best Practices

**Model Changes:**
1. Always backup database before major migrations
2. Test migrations on development data first
3. Use `--fake` only when you know what you're doing

**Admin Customization:**
1. Start with basic `admin.site.register(Model)`
2. Add custom `ModelAdmin` class when needed
3. Use `readonly_fields` for calculated fields
4. Leverage `autocomplete_fields` for better UX

**Apps Organization:**
- Keep related models in the same app
- Use `core` app for shared models (like nomenclatures)
- Each app should have a clear, single responsibility

**Permissions Testing:**
- Always run `docker compose exec web python test_permissions.py` after changes
- Test API endpoints with `docker compose exec web python test_permissions_api.py`
- Use `/api/users/permissions/` to debug user permissions
- Validate middleware headers in browser developer tools

**Security Best Practices:**
- All middleware are order-dependent in `settings/base.py`
- Custom permissions inherit from `BasePermission` 
- Decorators provide function-based permission checks
- Object-level permissions via model methods (`can_manage_organisme()`)

**API REST Users:**
- Complete REST API for user management at `/api/users/`
- Full CRUD with pagination, filtering, and search
- Role-based permissions and automatic data filtering
- Comprehensive documentation in `docs/API_USERS_GUIDE.md`

**API REST Organismes and Sites:**
- Complete REST API for organizations and sites management
- GeoJSON support for PostGIS geometries (import/export)
- Nested routes `/organismes/{id}/sites/` and bulk operations
- Advanced geospatial filtering and search capabilities
- Comprehensive documentation in `docs/API_ORGANISMES_SITES_GUIDE.md`

**API REST Plans de Gestion:**
- Complete REST API for management plans at `/api/plans/plans/`
- Full CRUD with multi-site support and file attachments
- 20+ endpoints including GeoJSON, statistics, bulk operations
- Advanced filtering (25+ filters) and search capabilities
- Upload/download system for plan files (documents, maps, reports)
- **Cycle de vie des plans** :
  - `POST /api/plans/plans/{id}/change-status/` - Changement de statut (référent du plan, admin_og+)
    - Body : `{ "new_status": "valide" | "draft" | "archive" | "en_revision" | "avis_csrpn" | "comite_consultatif" | "arrete_pref", "is_mi_parcours"?: boolean, "date_avis_csrpn"?: "YYYY-MM-DD", "date_validation_comite"?: "YYYY-MM-DD", "date_arrete_pref"?: "YYYY-MM-DD", "numero_arrete_pref"?: string }`
    - Transitions : `draft↔valide`, `valide→archive`, `archive→valide`, `valide↔draft`, etc. (cf. `change_status` dans `views.py`). Les attributs orthogonaux `annees_extension` (#250) et `en_revision` (#278) sont gérés par des endpoints dédiés (`extend-duration` / `remove-extension`, `start-revision` / `end-revision`) et ne changent pas le statut.
    - **Routage automatique `draft → valide` (#275 / #276)** : si le plan a un `plan_parent` déjà validé, la cible devient `modifie` (ou `mi_parcours` si `is_mi_parcours=true`). Sinon (plan original, `plan_parent IS NULL`), reste `valide`. Le flag `is_mi_parcours` n'est applicable qu'à cette transition et **rejette** s'il existe déjà un `mi_parcours` dans la chaîne (unicité).
    - **Pop-up d'archivage automatique (#246)** : à la transition vers un statut validé (`valide`/`modifie`/`mi_parcours`), le frontend détecte les plans encore `valide` dans la `version_chain` (lien `plan_parent`) et propose d'archiver le plan précédent. Helper `findPreviousValidatedPlan(currentId, version_chain)` exporté depuis `shared/components/modals/archive-previous-plan-dialog/`. Si confirmé, un second `change-status` (`new_status: 'archive'`) est émis.
    - **Pop-up mi-parcours (#276)** : sur clic « Valider le plan » d'un brouillon enfant d'un plan validé, si **aucun** `mi_parcours` n'existe encore dans la chaîne, on affiche `MiParcoursPromptDialogComponent` (oui / non / annuler). Le choix alimente `is_mi_parcours`. Sinon (mi-parcours déjà présent), validation directe → `modifie`. Helper `shouldPromptMiParcours()` dans `plan-detail.component.ts`.
  - `POST /api/plans/plans/{id}/create-evaluation/` - Création d'une évaluation mi-parcours (référent du plan, admin_og+). Plan source doit être `valide` et de type plan (pas évaluation). Copie sites/référents, version incrémentée. **Copie aussi le contenu et les métadonnées** (#377).
  - `POST /api/plans/plans/{id}/duplicate/` - Duplication d'un plan avec options sélectives
  - **Copie complète d'une nouvelle version (#377)** : `duplicate`, `create-evaluation` et `create-next-rang` clonent **tout le contenu** (enjeux → hiérarchie → indicateurs → métriques + `MetriqueScoreBlock`, **suivis/inventaires**, **opérations** re-reliées aux nouveaux indicateurs/métriques avec années/financements/sites) **et toutes les métadonnées** du plan (dont validations administratives CSRPN), pour que la nouvelle version soit éditable sans impacter les anciennes. Seul le `statut` n'est pas copié (→ `draft`) ; les attributs de cycle de vie (`is_mi_parcours`, `en_revision`, `annees_extension`, `next_rang_plan`) ne sont pas hérités. Données empiriques exclues (mesures, réalisations). Service : `PlanDuplicationService` (`copy_content()`, `build_version_plan()`, clone générique `_dup`).
  - `POST /api/plans/plans/{id}/delete-version/` - Suppression d'une version de la chaîne (#348 ; référent du plan, admin_og+). CASCADE des liens + contenu, re-rattache les enfants au parent, **renumérote les versions du rang**. Exposé via la page « Paramètres du plan de gestion » (sous-entrée dépliable « Vue d'ensemble » de la sidebar, gestionnaires uniquement).
  - `GET /api/plans/plans/for-sites/?site_ids=1,2` - **Plans associés à un/des site(s)**, groupés par site et triés par rang. **Tous les statuts sont renvoyés, brouillons compris** (anti-prolifération : voir tout plan déjà existant sur le site, y compris non validé, pour éviter les doublons). Scopé aux permissions de l'utilisateur (`get_queryset`). Sert à la **création standard d'un PG** (page « Créer un plan ») pour : (1) alerter si un PG du même rang existe déjà sur le site, (2) proposer le rattachement au plan du rang précédent, (3) afficher le détail des PG déjà rattachés.
  - **Rattachement automatique du rang à la création standard (fil entre rangs)** : `POST /api/plans/plans/` accepte un `plan_parent_id` optionnel. `perform_create` ne le pose **qu'après validation serveur** via `PlanGestionViewSet._is_valid_rang_parent(parent, plan)` — **rang strictement inférieur** et **au moins un site en commun**. **Le statut du parent n'est PAS contraint : un parent en brouillon est autorisé** (anti-prolifération — permet de chaîner un nouveau rang à un plan existant non encore validé). Sinon le lien est ignoré (`plan_parent` reste NULL). Permet de conserver la chaîne de versions quand un nouveau rang est créé depuis la page d'accueil (et pas seulement via `create-next-rang`). Le front (page de création) propose une **case « Rattacher ce plan à la suite de … »** cochée par défaut ; le parent suggéré est le plan de rang le plus élevé strictement inférieur au rang saisi (à rang égal : un plan validé est préféré à un brouillon, puis version max) parmi les sites sélectionnés. Décocher la case → plan indépendant.
  - Chaîne de versions via `plan_parent` FK et `id_type_document` (nomenclature). Numérotation `version` en **entiers** (1, 2, 3…) par chaîne — `get_next_version()` calcule `max(versions de la chaîne) + 1` (#279).
  - Le serializer détail expose `version_chain` pour la timeline frontend (inclut `rang` et `type_site_mnemonique` du site principal).
  - **Statuts** :
    - `draft` — brouillon (éditable)
    - `avis_csrpn` — envoyé pour avis CSRPN (workflow #277, lecture seule)
    - `comite_consultatif` — avis CSRPN rendu, en attente de validation comité (workflow #277)
    - `arrete_pref` — validé par comité, en attente d'arrêté préfectoral (RNN uniquement, #277)
    - `valide` — plan original validé
    - `modifie` — plan validé puis modifié au moins une fois au sein du **même rang** (plan_parent validé ET `plan_parent.rang == self.rang`, #275). La première version d'un nouveau rang reste `valide` même si elle succède à un plan archivé/validé du rang précédent.
    - `archive` — terminé
    - **Attributs orthogonaux au statut** (un plan validé peut les cumuler) :
      - **Extension (#250)** : `annees_extension` (0, 1 ou 2). Helper `is_extended()`, badge contextualisé via `getExtensionBadgeKey()`. **Refonte (extension = nouvelle version)** : `POST extend-duration` (`{years: 1|2}`) ne pose plus l'attribut en place mais **crée un brouillon de version étendue** (`build_version_plan` + `copy_content`, #377) — même rang que le plan source, `plan_parent` = source, `annees_extension` = cumul (max 2 ans), copie sites/référents/membres/contenu/suivis. Le gestionnaire complète ce brouillon (actions + suivi des années ajoutées) puis le valide (→ `modifie`, même rang) ; la pop-up #246 propose alors d'archiver le plan d'origine. Une 1re extension de 1 an est **reconductible** d'1 an supplémentaire (cumul ≤ 2) depuis la version étendue validée. Conditions : plan source `valide`/`modifie`, pas de brouillon enfant en cours, fenêtre `[échéance effective − 1, +2]`. `peut_etre_etendu` (serializer) reflète ces règles. Endpoint legacy `remove-extension` conservé (efface l'attribut sur le plan courant). Frontend : `ExtendDurationDialogComponent` (choix limité au cumul restant), `applyExtension()` navigue vers le brouillon créé, le pop-up mi-parcours est inhibé sur une version étendue.
      - **En cours de révision (#278)** : champ `en_revision: bool`. Indique qu'un nouveau plan (rang suivant) est en cours d'élaboration. **La révision peut être lancée avant ou après le dépassement de `annee_fin`** — pas de contrainte temporelle. Le plan reste fonctionnellement validé. FK `next_rang_plan` (self-FK, `related_name=previous_rang_plans`) lie explicitement le brouillon du rang suivant. Endpoints : `start-revision` (payload optionnel `next_rang_plan_id`) / `end-revision`. Helper `is_in_revision()`. Modale `StartRevisionDialogComponent` au clic.
      - **Évaluation mi-parcours (#276)** : champ `is_mi_parcours: bool`. Indique qu'une modification est l'évaluation mi-parcours du plan. **Unique par chaîne** (un seul plan dans la chaîne peut porter le drapeau). Le statut de base est alors `modifie`. Au clic « Lancer l'évaluation mi-parcours » (bouton terra cotta dans la barre d'actions du plan-detail, visible quand `statut ∈ {valide, modifie}` et aucune mi-parcours déjà dans la chaîne), une modale `StartMiParcoursDialogComponent` propose 2 modes : (1) **créer** un brouillon de type EVAL_MI_PARCOURS via `create-evaluation` (existant), (2) **lier** à un brouillon existant. À la validation du brouillon, le popup `MiParcoursPromptDialogComponent` (#276) demande confirmation → `change-status` avec `is_mi_parcours=true` pose le drapeau (route `statut=modifie`). Helpers `is_mid_term()`, `chain_has_mi_parcours()`. Badge terra cotta dans l'UI.
      - Ces attributs **ne débloquent PAS l'édition** : seul `statut='draft'` autorise les modifications (#248).
    - Helpers modèle : `is_modification()`, `chain_has_mi_parcours()`, `is_rnn()`, `get_principal_site()`, `is_extended()`, `is_in_revision()`, `is_mid_term()`, constantes `VALIDATED_STATUSES`, `EXTENDABLE_STATUSES`, `CSRPN_WORKFLOW_STATUSES`.
  - **Workflow CSRPN (#277)** :
    - Chemin RNN : `draft → avis_csrpn → comite_consultatif → arrete_pref → valide` (ou `modifie`/`mi_parcours` selon `plan_parent` et flag).
    - Chemin non-RNN : `draft → avis_csrpn → comite_consultatif → valide` direct (l'étape `arrete_pref` est rejetée par le backend).
    - Annulation : tout statut CSRPN peut revenir en `draft`.
    - Champ `date_validation_cspn` renommé en `date_avis_csrpn`. Nouveaux champs `date_validation_comite`, `date_arrete_pref`, `numero_arrete_pref` (renseignés au passage de chaque étape).
    - Backend route automatiquement la transition finale (`comite_consultatif → valide` ou `arrete_pref → valide`) vers `modifie`/`mi_parcours` si le plan a un `plan_parent` validé (#275/#276).
    - Notifications email + in-app (`plan_csrpn_transition`, priorité high) envoyées aux référents du plan à chaque transition CSRPN, excluant le déclencheur.
    - Frontend : modale `CsrpnStepDialogComponent` (3 variantes : `csrpn` / `comite` / `arrete`) pour saisir date(s) et numéro d'arrêté. Boutons cycle de vie dédiés par statut.
  - **Badge d'extension contextualisé (#281)** : helper frontend `getExtensionBadgeKey(mnemonique)` route vers `plans.extension.badge_rnn` (RNN/RNR → « Prolongé »), `plans.extension.badge_pnr` (PNR → « En renouvellement »), `plans.extension.badge_ens` (ENS/ENSD → « Étendu ») ou `plans.extension.badge` par défaut. Affiché à côté du chip de statut quand `annees_extension > 0` (cf. `isPlanExtended()` dans `plan-detail.component.ts`).
  - **Permissions lifecycle** : référent du plan (`PlanGestion.referents`), admin_og, super_admin. Vérification spécifique au plan dans la vue (pas juste le rôle global).
- **Verrouillage des modifications hors brouillon (#248)** :
  - Permission DRF `CanModifyOnlyDraftPlan` (`apps/plans/permissions.py`) appliquée aux ViewSets : `PlanGestionViewSet`, `CorPgFichierViewSet`, `EnjeuViewSet`, `FacteurInfluenceViewSet`, `PressionViewSet`, `ObjectifLongTermeViewSet`, `NiveauExigenceViewSet`, `ObjectifOperationnelViewSet`, `ResultatAttenduViewSet`, `IndicateurViewSet`, `MetriqueViewSet`, `MesureViewSet`, `OperationViewSet`, `SuiviInventaireViewSet`. (`ResponsabiliteViewSet` exclue : rattachée à un site.)
  - Toute écriture (POST/PUT/PATCH/DELETE) sur le plan ou ses entités enfants → **403** quand `plan.statut != 'draft'`, indépendamment du rôle.
  - **Actions exemptées** : `change_status`, `duplicate`, `create_evaluation`, `assign_site/remove_site/replace_site`, `assign_referent/remove_referent`, `assign_member/remove_member`, et tout endpoint de consultation (GET).
  - **Mécanisme** : méthode `get_plan_de_gestion()` ajoutée sur tous les modèles concernés (`Enjeu`, `FacteurInfluence`, `Pression`, `OLT`, `NE`, `OO`, `RA`, `Indicateur`, `Métrique`, `Mesure`, `Operation`, `SuiviInventaire`, `CorPgFichier`) pour remonter au plan via la chaîne FK. Les ViewSets racines exposent `get_plan_for_payload(data)` pour bloquer les créations en amont.
  - **Frontend** : `canEditPlan()` inclut un check `isPlanDraft()` côté `plan-detail.component.ts` et `enjeux-list.component.ts`. Bannière `.lock-banner` (« Plan verrouillé en lecture seule ») affichée en haut des deux pages dès que `statut !== 'draft'`. L'endpoint `enjeux/by-plan/` retourne `plan_statut` pour alimenter la bannière. Les actions de cycle de vie (`canManageLifecycle()`) restent **inchangées** (accessibles hors brouillon).
  - **Statuts verrouillés en lecture seule** : tous sauf `draft` (`valide`, `modifie`, `mi_parcours`, `archive`, statuts CSRPN). Les attributs orthogonaux `annees_extension` (#250) et `en_revision` (#278) ne débloquent PAS l'édition. Cf. `EDITABLE_STATUSES = {"draft"}` dans `permissions.py`.
  - Pour modifier un plan validé / modifié / mi-parcours : repasser en brouillon (cycle de vie) ou créer une nouvelle version (duplicate / create-evaluation).
- **Lecture seule pour tout utilisateur lié au plan (#610)** :
  - **Règle** : *voir le plan implique voir son contenu*. Un utilisateur lié à un plan sans être « référent » (membre `CorRolePlan`, utilisateur rattaché à un site du plan, membre d'un organisme rédacteur ou gestionnaire d'un site) consulte **toute** l'arborescence en lecture seule, que le plan soit en brouillon ou validé.
  - **Permission DRF `IsReferentOrReadOnly`** (`apps/plans/permissions.py`) remplace `IsReferent` au niveau des ViewSets de contenu : les méthodes SAFE sont ouvertes à tout authentifié, les écritures restent réservées aux référents (`Role.is_referent()`) et au brouillon (`CanModifyOnlyDraftPlan`). `IsReferent` reste utilisé tel quel sur les `@action` POST de cycle de vie.
  - **Périmètre de lecture centralisé dans `apps/plans/access.py`** : `plan_scope_q(user)`, `accessible_plan_ids(user)`, `scope_by_plan(queryset, user, paths, extra=None)`, `user_can_access_plan(user, plan)`, constante `INDICATEUR_TO_PG_PATHS` + helper `prefix_paths()`. Tous les `get_queryset()` de l'arborescence (enjeux → RA, indicateurs, métriques, mesures, opérations, réalisations, postes, suivis) passent par `scope_by_plan()` — ne **pas** réécrire un filtrage à la main dans un nouveau ViewSet.
  - **Ne plus utiliser `Q(id_pg__statut='valide')` comme critère de visibilité** : ce filtre historique ouvrait le contenu de tout plan validé à n'importe quel compte authentifié (y compris hors organisme). Il a été supprimé de tous les ViewSets.
  - Frontend inchangé : `canEditPlan()` / `isPlanManager()` masquent déjà les actions d'édition pour un consultant non référent.
- **Exports réservés aux référents du plan** :
  - **Règle** : la lecture seule (#610) s'arrête à la consultation dans l'application. Les **exports** (`export-*`) extraient l'intégralité du contenu du plan (documents rédigés, arborescence, fiches action, budget, RH) : ils sont réservés aux **référents du plan** et aux gestionnaires (**admin organisme**, **rédacteur principal**, **super admin**) — même audience que « Paramétrage » et « Suivis ».
  - **Backend** : `PlanGestionViewSet._can_export_plan(user, plan)` (= `can_manage_plan_lifecycle()` ou `plan.referents`) + `_get_plan_for_export()` (403 sinon), appliqué aux 9 actions détail `export-arborescence-xlsx`, `export-arborescence-presentation-xlsx`, `export-fiches-actions-xlsx`, `export-rh-previsionnel-xlsx`, `export-rh-suivi-xlsx`, `export-budget-previsionnel-xlsx`, `export-budget-suivi-xlsx`, `export-plan-docx`, `export-actions-xlsx`. Les classeurs **exemples** (`example-*-xlsx`, `detail=False`, indépendants d'un plan) restent ouverts à tout authentifié.
  - **Export d'UNE fiche action (#642)** : `GET /api/plans/operations/{id}/export-fiche-xlsx/` produit le classeur de cette seule action (`build_fiche_action_workbook(plan, operation_ids=[…])`, rendu identique à l'export du plan). Même règle de droits, revérifiée dans `OperationViewSet.export_fiche_xlsx` (le plan est résolu via `operation.get_plan_de_gestion()`). Côté UI, la barre de la fiche action expose un bouton unique **« Exporter ou imprimer »** → `ExportFicheActionDialogComponent` (format impression/PDF ou Excel ; le choix des sections #532 vit dans cette modale et ne vaut que pour l'impression).
  - **Frontend** : `canViewExports()` dans `plan-sidebar` (= `effectiveCanManage()`) masque l'entrée « Exports » ; `PlanExportsComponent.canManage()` affiche `plans.exports.noPermission` et bloque `download()` à la place des boutons.
- Comprehensive documentation in `docs/API_PLANS_GUIDE.md`

**API REST Notifications & Validations:**
- Validation requests API at `/api/validations/`
- Request types: `user_registration`, `site_access`, `plan_access`, `referent_validation`, `plan_site_link`
- Status workflow: `pending` → `approved` / `rejected` / `cancelled` / `expired`
- Endpoints:
  - `GET /api/validations/` - List validation requests (filtered by user role)
  - `GET /api/validations/pending/` - Pending requests for current validator
  - `GET /api/validations/my-requests/` - Current user's own requests
  - `POST /api/validations/{id}/approve/` - Approve a request
  - `POST /api/validations/{id}/reject/` - Reject a request
  - `POST /api/validations/request_plan_site_link/` - Demande de lien plan-site (body: `{plan_id, site_id}`)
  - `GET /api/notifications/` - User notifications
  - `POST /api/notifications/{id}/read/` - Mark notification as read
  - `POST /api/notifications/read-all/` - Mark all as read

**Validation plan-site link** (`plan_site_link`) :
- **Droits** : référent du plan, membre du plan, référent/membre du site, admin_og+
- **Lien direct** (sans validation) : super_admin, admin_og+référent site, référent plan+référent site
- **Validation requise** : dans tous les autres cas
  - Si le demandeur est **référent du plan** → validateurs = référents du site + admin_og du site
  - Sinon (membre du plan, référent/membre du site) → validateurs = référents du plan
- **Approbation** : crée `CorSitePg` + notifie le demandeur + notifie les référents du plan

**Types de notifications disponibles:**
| Type | Description | Déclencheur |
|------|-------------|-------------|
| `welcome` | Bienvenue | Activation du compte après validation |
| `validation_request` | Demande de validation | Nouvelle demande reçue (pour validateurs) |
| `validation_approved` | Validation approuvée | Demande approuvée |
| `validation_rejected` | Validation rejetée | Demande rejetée |
| `user_associated_site` | Associé à un site | Ajout comme membre d'un site |
| `user_associated_plan` | Associé à un plan | Ajout comme référent d'un plan |
| `user_removed_site` | Retiré d'un site | Retrait d'un site |
| `user_removed_plan` | Retiré d'un plan | Retrait d'un plan |
| `account_deactivated` | Compte désactivé | Désactivation par un admin |
| `account_activated` | Compte activé | Réactivation par un admin |
| `organisme_changed` | Organisme modifié | Changement d'organisme par un admin |
| `site_orphaned` | Site sans utilisateurs | Plus aucun utilisateur sur le site |
| `organisme_no_admin` | Organisme sans admin | Plus d'administrateur pour l'organisme |
| `system_alert` | Alerte système | Notifications système (maintenance, etc.) |
| `info` | Information | Informations générales |

**Signaux de notifications automatiques** (`apps/notifications/signals.py`):
- `notify_user_site_association`: Notifie lors de l'ajout à un site
- `notify_user_removed_from_site`: Notifie lors du retrait d'un site
- `notify_user_deactivation`: Notifie lors de la désactivation
- `notify_user_organisme_changed`: Notifie lors du changement d'organisme
- `notify_plan_referents_new_member`: Notifie les référents d'un plan lors de l'ajout d'un membre/référent

**Notifications liées aux validations plan-site** :
- Lors de l'approbation d'un lien plan-site (`approve_plan_site_link`), les référents du plan sont notifiés que le site a été lié
- Lors d'un lien direct plan-site (sans validation), les référents du plan sont également notifiés

**API REST Activity (Historique d'activité):**
- Unified activity timeline API at `/api/activity/`
- Entity types: `site`, `plan`, `user`, `organisme`, `validation`
- Action types: `create`, `update`, `delete`, `add_member`, `remove_member`, `add_referent`, `remove_referent`, `status_change`, `activate`, `deactivate`, `rgpd_request`, `rgpd_cancelled`, `rgpd_anonymized`, etc.
- Visibility levels: `public`, `admin`, `system`
- Filtering by user role:
  | Rôle | Accès |
  |------|-------|
  | super_admin | Tout (y compris RGPD et système) |
  | admin_og | Activité de son organisme |
  | référent | Activité de ses sites/plans |
  | utilisateur | Ses notifications + sites où il est membre |

- Endpoints:
  - `GET /api/activity/` - List activities (paginated, filtered by role)
  - `GET /api/activity/{id}/` - Single activity detail
  - `GET /api/activity/my_sites/` - Activities for user's sites
  - `GET /api/activity/my_plans/` - Activities for user's plans
  - `GET /api/activity/validations/` - Validation-related activities (admin_og+)
  - `GET /api/activity/rgpd/` - RGPD activities (super_admin only)
  - `GET /api/activity/system/` - System activities (super_admin only)
  - `GET /api/activity/stats/` - Activity statistics
  - `GET /api/activity/tabs_counts/` - Counts per tab/category

- Filters:
  - `entity_type` - Filter by entity type (site, plan, user, etc.)
  - `action` - Filter by action type
  - `site_id` - Filter by related site
  - `plan_id` - Filter by related plan
  - `since` - Filter by date (ISO format)
  - `search` - Text search in description/entity_name

- Backend components:
  - Model: `apps/core/models.py` → `ActivityLog`
  - Service: `apps/core/services.py` → `ActivityService`
  - Signals: `apps/core/activity_signals.py` (auto-logging on model changes)
  - API: `apps/core/views.py` → `ActivityViewSet`

- Tests: `tests/apps/core/test_activity.py` (45 tests)

### Frontend Features

**Page Profil (`/profile`):**
- Informations personnelles de l'utilisateur
- Onglet "Mes demandes" : suivi des demandes de validation en cours
- Accessible à tous les utilisateurs authentifiés

**Administration Validations (`/admin/validations`):**
- Tableau des demandes de validation à traiter
- Filtres par statut et type de demande
- Actions rapides : approuver/rejeter en un clic
- Dialog de détail avec informations complètes
- Accessible aux admin_og et super_admin

**Administration Orphelins (`/administration/orphelins`):**
- Page listant les **sites sans utilisateur** et les **plans sans site** (état persistant, consulté à la demande).
- **Remplace l'ancien audit hebdomadaire par email** : les tâches Celery beat `check_orphaned_sites` / `check_orphaned_plans` (et leurs résumés email `notify_orphaned_sites_summary` / `notify_orphaned_plans_summary`) ont été supprimées. L'état orphelin n'est pas un événement récurrent ; l'envoyer chaque semaine saturait la boîte mail des admins.
- La détection temps réel d'un site qui devient orphelin reste assurée par les signaux Django, mais **in-app uniquement** (`notify_site_orphaned`, `send_email=False`, priorité `medium`). Pas de notification temps réel pour les plans.
- **Scope par rôle** : super_admin / rédacteur général voient tous les sites + tous les plans orphelins ; admin_og voit uniquement les sites orphelins de son organisme (pas les plans, non rattachables à un organisme sans site).
- **Badge de navigation** dans la sidebar admin (compteur sites + plans), rafraîchi via `OrphansService.startAutoRefresh()` (toutes les 5 min) pour admin_og+.
- Backend : `GET /api/admin/orphans/` (liste) et `GET /api/admin/orphans/counts/` (compteur léger pour le badge), permission `IsAdminOrganisme`. Frontend : `OrphansService`, `AdminOrphansComponent`, clés i18n `admin.orphans.*`.

**Inscription Publique (`/auth/register`):**
- Formulaire d'inscription avec sélection d'organisme
- Page d'attente de validation (`/auth/registration-pending`)
- Workflow : inscription → validation admin → activation compte

**Cloche de Notifications:**
- Composant `NotificationBellComponent` dans le header
- Compteur de notifications non lues
- Dialog avec liste des notifications et marquage comme lu
- Lien "Voir tout" vers `/activite`

**Page Activité (`/activite`):**
- Timeline unifiée des activités, notifications et validations
- Onglets dynamiques selon le rôle de l'utilisateur:
  - **Tous les utilisateurs**: "Tout", "Mes sites", "Mes plans", "Mes droits", "Notifications"
  - **Admin organisme+**: + "Validations"
  - **Super admin**: + "RGPD", "Système"
- **Onglet "Mes droits"**: Historique des changements de droits de l'utilisateur (ajout/retrait membre, référent, activation compte, validation demandes)
- Filtres par type d'entité, action, recherche textuelle
- Groupement chronologique ("Aujourd'hui", "Hier", "Cette semaine", etc.)
- Icônes et couleurs par type d'action (création=vert, modification=bleu, suppression=rouge)
- Pagination avec scroll infini
- Liens vers les entités concernées

Fichiers frontend:
- Route: `frontend/src/app/features/activity/activity.routes.ts`
- Composant principal: `frontend/src/app/features/activity/activity.component.ts`
- Service: `frontend/src/app/core/services/activity.service.ts`
- Modèles: `frontend/src/app/core/models/activity.model.ts`
- Traductions: `frontend/src/assets/i18n/fr.json` (clés `activity.*`)

**Cycle de vie des Plans (`/plans/:slug`):**
- **Statuts** : `draft` (brouillon), `valide` (original validé), `modifie` (#275), `archive` (terminé). Trois **attributs orthogonaux** s'ajoutent au statut (un plan validé peut les cumuler) : `annees_extension` (#250), `en_revision` (#278), `is_mi_parcours` (#276 — unique par chaîne). Cf. note interne *Cycle de vie d'un plan de gestion*.
- **Règles de chaîne** :
  - **Un seul brouillon enfant par parent** (`has_draft_child`). Bloque `duplicate`, `create-evaluation`, `create-next-rang` si un brouillon enfant existe déjà.
  - **Parents éligibles à un nouveau brouillon** : `DRAFTABLE_PARENT_STATUSES = {valide, modifie, archive}` — un brouillon ne peut être créé que sur un plan qui a été validé à un moment donné (actif ou archivé).
  - **toDraft uniquement sur la feuille de chaîne** : `valide/modifie → draft` refusé si le plan a au moins un enfant. Pour modifier un plan déjà étendu par des versions, passer par « Créer une nouvelle version » (bouton dédié dans `plan-detail`, ouvre `DuplicatePlanDialogComponent`).
  - **Cascade de validation vers l'amont** : valider un brouillon (`draft → valide/modifie`) entraîne la validation automatique de tous les parents en draft de la chaîne (filet de sécurité, devrait être un no-op sous les autres règles).
  - **Version scopée au rang** : la `version` repart à `1` à chaque changement de rang (un nouveau rang = un nouveau plan de gestion, pas une nouvelle version du même plan). `get_next_version()` calcule `max(versions du même rang)+1` ; `create-next-rang` utilise `'1'` pour le nouveau plan. Migration `0074_renumber_versions_per_rang` normalise les données existantes.
  - **Timeline cycle de vie groupée par rang** : `PlanVersionTimelineComponent` affiche les versions regroupées par rang (sections), avec en-tête « Rang N précédent / actuel / à venir ». Les rangs précédents/suivants sont visuellement distincts (opacity réduite, séparateur pointillé pour le rang suivant).
- **Droits** : Actions de cycle de vie accessibles uniquement aux **référents du plan**, **admin organisme** et **super admin**. Calculé via `canManageLifecycle` computed dans `plan-detail.component.ts` (vérifie `plan.referents`, `authService.isAdminOrganisme()`, `authService.isSuperAdmin()`).
- **PlanVersionTimelineComponent** : Timeline verticale des versions dans la colonne latérale (section "Cycle de vie")
  - Nœuds cliquables (cercles avec icône type document), connectés par une ligne verticale
  - Nœud courant mis en avant : fond coloré, bordure gauche terra-cotta, badge "actuel"
  - Masqué si `version_chain.length <= 1`
  - **Actions contextuelles** intégrées sous la timeline (si `canManage`) :
    - Brouillon → "Valider le plan"
    - Validé → "Remettre en brouillon" + "Lancer évaluation mi-parcours" (seulement plans, pas évaluations) + "Archiver (rend inactif)"
    - Archivé → "Réactiver (rend actif)"
  - Fichiers : `shared/components/plan-version-timeline/`
- **StatusChangeDialogComponent** : Modale de changement de statut (alternative aux actions timeline, utilisée depuis la liste)
  - Fichiers : `shared/components/modals/status-change-dialog/`
- **DuplicatePlanDialogComponent** : Modale de duplication de plan avec options sélectives
  - Fichiers : `shared/components/modals/duplicate-plan-dialog/`
- **ArchivePreviousPlanDialogComponent (#246)** : Modale d'archivage automatique du plan précédent à la validation d'un nouveau plan dans la même chaîne de versions. Helper `findPreviousValidatedPlan(currentId, version_chain)` exporté.
  - Fichiers : `shared/components/modals/archive-previous-plan-dialog/`
- **Verrouillage hors brouillon (#248)** : `canEditPlan()` côté `plan-detail.component.ts` et `enjeux-list.component.ts` inclut un check `isPlanDraft()`. Bannière `.lock-banner` (style global dans `assets/scss/_components.scss`) affichée en haut des pages quand le plan n'est pas en brouillon. Backend : permission DRF `CanModifyOnlyDraftPlan`.
- Traductions : `frontend/src/assets/i18n/fr.json` (clés `plans.lifecycle.*`, `plans.duplicate.*`, `plans.lifecycle.archivePrevious.*`, `plans.lifecycle.lockedBanner.*`)

**Création d'un plan de gestion (`/plans/nouveau`, `PlanCreateComponent`) — fil entre rangs :**
- À la sélection d'un/des site(s), un `effect()` appelle `adminService.getPlansForSites(siteIds)` (endpoint `for-sites`) et stocke **tous** les PG du site (tous statuts, brouillons compris) dans le signal `existingPlansBySite`.
- **Détail des PG existants** : bloc dépliable listant, par site et par rang, les plans du/des site(s) sélectionné(s) (statut affiché).
- **Alerte même rang (non bloquante)** : computed `sameRangConflicts()` → bandeau `info-block-warning` si un PG validé du rang saisi existe déjà sur le site. La création reste autorisée.
- **Rattachement au rang précédent (chaîne de versions)** : computed `suggestedParent()` (rang le plus élevé < rang saisi ; à rang égal, plan validé préféré à un brouillon ; puis version max, parmi les sites — brouillons inclus). Case `app-checkbox` « Rattacher ce plan à la suite de … » (signal `linkToParentEnabled`, cochée par défaut) ; si cochée, `plan_parent_id` est ajouté au payload `createPlan`. Le backend revalide le parent (cf. `_is_valid_rang_parent`, qui autorise un parent brouillon).
- Le champ `rang` est mirroré dans le signal `rangSignal` (via `valueChanges`) pour alimenter les computeds (`currentRang()` exposé au template).
- Modèles : `SitePlanSummary`, `SitePlansEntry`, `SitePlansResponse` (`core/models/admin.model.ts`). Service : `AdminService.getPlansForSites()`. Traductions : clés `modals.planForm.versionChain.*`.
- Tests : `plan-create.component.spec.ts` (describe « version chain — fil entre rangs ») + `tests/integration/test_api_plans.py` (`TestPlansForSitesEndpoint`, `TestPlansAutoLinkParent`).

**Formulaire d'action / opération (`/plans/:slug/enjeux/operations/...`) :**
- **Paramétrage de ventilation repris d'une action à l'autre (#641)** : à la **création** d'une action, le formulaire pré-remplit le mode de ventilation et les deux cases du tableau budgétaire (#600) avec ceux de la **dernière action saisie du plan**, via `GET /api/plans/operations/ventilation-defaults/{plan_id}/` (`EnjeuService.getVentilationDefaults()` → `applyVentilationDefaults()`, qui passe par `onModeToggle` pour réaligner la déclinaison par poste et le tableau RH). Sans action existante, on retombe sur les valeurs par défaut du modèle. En édition ou en lecture seule, aucun appel n'est fait.
- **Bouton « Enregistrer » sans validation (#251)** dans le formulaire d'opération (`features/plans/enjeux/operation-form/operation-form.component.*`) :
  - Sauvegarde sans déclencher les validators required, **maintient l'utilisateur sur le formulaire**.
  - En création, redirige silencieusement (`router.navigate(..., { replaceUrl: true })`) vers `/operations/{id}/modifier` pour que les enregistrements suivants soient des `PATCH`.
  - En édition, reste sur la page (URL inchangée) avec snackbar « Modifications enregistrées ».
  - Méthodes : `saveDraft()` + extraction de `buildPayload()` et `submitToApi(payload, { stayOnForm })`. Le bouton « Valider » conserve son comportement strict (validation + navigation).
  - Bouton CSS : `.btn-action-save` (outline blanc, distinct du « Valider » plein).

## Internationalisation (i18n)

**IMPORTANT : Toutes les chaînes de texte visibles par l'utilisateur doivent être traduites.**

### Frontend (Angular avec ngx-translate)

**Configuration :**
- Fichier de traductions : `frontend/src/assets/i18n/fr.json`
- Service : `frontend/src/app/core/services/translation.service.ts`
- Langue par défaut : Français (`fr`)

**Usage dans les templates HTML :**
```html
<!-- Texte simple -->
<h1>{{ 'admin.users.title' | translate }}</h1>

<!-- Avec paramètres -->
<p>{{ 'common.itemsCount' | translate:{ count: items.length } }}</p>

<!-- Dans les attributs -->
<input [placeholder]="'common.actions.search' | translate">
<button [title]="'common.actions.delete' | translate">
```

**Usage dans le TypeScript :**
```typescript
import { TranslateService } from '@ngx-translate/core';

// Dans le composant
private readonly translate = inject(TranslateService);

// Utilisation
this.snackBar.open(
  this.translate.instant('admin.users.messages.success'),
  this.translate.instant('common.actions.close'),
  { duration: 3000 }
);
```

**Structure des clés de traduction :**
```
common.actions.*      - Actions (save, cancel, delete, close, search...)
common.status.*       - Statuts (active, inactive, pending...)
common.validation.*   - Messages de validation
auth.*                - Authentification (login, register)
header.*              - Navigation et header
admin.users.*         - Gestion des utilisateurs
admin.plans.*         - Gestion des plans
admin.sites.*         - Gestion des sites
admin.organismes.*    - Gestion des organismes
admin.validations.*   - Gestion des validations
modals.*              - Dialogues modaux
plans.*               - Module plans
profile.*             - Page profil
home.*                - Page d'accueil
scores.*              - Labels des scores
actionStatus.*        - Statuts des actions
```

**Ajouter TranslateModule aux composants standalone :**
```typescript
import { TranslateModule } from '@ngx-translate/core';

@Component({
  // ...
  imports: [CommonModule, TranslateModule, /* autres imports */],
})
```

### Backend (Django avec gettext)

**Configuration :**
- Répertoire locale : `backend/locale/fr/LC_MESSAGES/`
- Import : `from django.utils.translation import gettext_lazy as _`

**Fichiers de traduction Django :**

| Fichier | Type | Description |
|---------|------|-------------|
| `.po` (Portable Object) | Texte | Fichier éditable contenant les chaînes source et leurs traductions |
| `.mo` (Machine Object) | Binaire | Fichier compilé utilisé par Django à l'exécution |

**Workflow de traduction :**
1. `makemessages` → Scanne le code Python/templates et génère/met à jour les `.po`
2. Édition manuelle → Traduire les chaînes dans le fichier `.po`
3. `compilemessages` → Compile les `.po` en `.mo` pour la production

**Note importante :** Avec `gettext_lazy`, les chaînes françaises sont directement dans le code Python. Les fichiers `.po`/`.mo` ne sont nécessaires que si vous ajoutez une **autre langue** (ex: anglais). Pour le français uniquement, l'infrastructure actuelle suffit.

**Usage dans les models :**
```python
from django.utils.translation import gettext_lazy as _

class MonModel(models.Model):
    nom = models.CharField(_("Nom"), max_length=100)
    description = models.TextField(_("Description"), help_text=_("Description détaillée"))

    class Meta:
        verbose_name = _("Mon modèle")
        verbose_name_plural = _("Mes modèles")
```

**Usage dans les serializers/views :**
```python
from django.utils.translation import gettext_lazy as _

raise serializers.ValidationError(_("Les mots de passe ne correspondent pas."))
```

**Usage dans les templates email :**
```html
{% load i18n %}

<h1>{% trans "Bienvenue" %}</h1>
<p>{% blocktrans %}Bonjour {{ nom }},{% endblocktrans %}</p>
```

**Commandes de traduction (uniquement si ajout d'une nouvelle langue) :**
```bash
# Installer gettext dans le container (requis une seule fois)
docker compose exec web apk add gettext

# Extraire les chaînes traduisibles vers backend/locale/fr/LC_MESSAGES/django.po
docker compose exec web python manage.py makemessages -l fr

# Pour ajouter l'anglais
docker compose exec web python manage.py makemessages -l en

# Compiler les .po en .mo (après traduction manuelle du .po)
docker compose exec web python manage.py compilemessages
```

**Contenu d'un fichier .po :**
```po
#: apps/users/models.py:42
msgid "Adresse email"
msgstr "Adresse email"  # FR: identique car source en français

#: apps/users/models.py:42 (dans en/django.po)
msgid "Adresse email"
msgstr "Email address"  # EN: traduction anglaise
```

### Bonnes pratiques

1. **Ne jamais coder en dur** les textes visibles par l'utilisateur
2. **Utiliser des clés descriptives** : `admin.users.messages.deleteSuccess` plutôt que `msg1`
3. **Grouper les clés** par fonctionnalité/module
4. **Ajouter les traductions** dans `fr.json` AVANT de les utiliser
5. **Vérifier** que TranslateModule est importé dans les composants standalone

For detailed specifications, model definitions, and full documentation, refer to `claude.md`.