# Design System CICADA

Ce document decrit les regles du design system de l'application CICADA, basees sur le Kit UI Biodiv (11/2025).

**Source de reference** : `KitUI/` (maquettes PNG) et Figma (voir `FIGMA_LINKS.md` - non versionné)

## Palette de couleurs

### Couleur principale

| Nom | Hex | Variable SCSS | Usage |
|-----|-----|---------------|-------|
| Bleu-vert | `#025359` | `$primary-color` | Boutons, actions, navigation, titres |

### Couleurs secondaires

| Nom | Hex | Variable SCSS | Usage |
|-----|-----|---------------|-------|
| Jaune | `#FEC180` | `$secondary-yellow` | Accent decoratif |
| Orange saumon | `#F5B399` | `$secondary-orange-salmon` | Accent decoratif |
| Terra Cotta | `#B74D5D` | `$secondary-terra-cotta` | Accent decoratif |
| Vert pale | `#C0E3CF` | `$secondary-pale-green` | Accent decoratif |

### Couleurs de statut et scores

| Nom | Hex | Variable SCSS | Usage |
|-----|-----|---------------|-------|
| Rouge clair | `#FF7579` | `$score-very-bad` | Tres mauvais score |
| Orange | `#FA9965` | `$warning-color` | Mauvais score, Avertissement |
| Jaune moutarde | `#F7D35C` | `$score-neutral` | Score neutre |
| Vert clair | `#82DB8A` | `$score-good` | Bon score |
| Bleu ciel | `#81C9D8` | `$score-very-good` | Tres bon score |
| Vert | `#04854B` | `$success-color` | Succes |
| Rouge | `#E12329` | `$error-color` | Erreur |

### Couleurs neutres

| Nom | Hex | Variable SCSS | Usage |
|-----|-----|---------------|-------|
| Noir | `#343433` | `$black` | Textes principaux |
| Gris fonce | `#746F6E` | `$gray-dark` | Textes secondaires, mentions |
| Gris | `#C6C6C6` | `$gray` | Etats inactifs |
| Gris clair | `#E4E4E4` | `$gray-light` | Filets separateurs |
| Gris tres clair | `#F6F6F6` | `$gray-lighter` | Background tableau |
| Beige | `#F8F5F1` | `$beige` | Background page |
| Blanc | `#FFFFFF` | `$white` | Background cartes |

---

## Regles d'accessibilite WCAG AA

**IMPORTANT** : Pour assurer la lisibilite et l'accessibilite, utiliser uniquement les combinaisons de couleurs testees et approuvees.

### Legende des symboles

- **AA** : Combinaison approuvee WCAG AA
- **decoratif/fond** : Utiliser uniquement pour des elements decoratifs, pas pour du texte

### Texte sur fond colore

Le tableau suivant indique quelle couleur de texte utiliser sur chaque fond colore :

| Couleur de fond | Texte Blanc | Texte Noir | Texte Primaire | Usage |
|-----------------|:-----------:|:----------:|:--------------:|-------|
| Bleu-vert `#025359` | **AA** | - | - | Boutons, chips critiques |
| Terra Cotta `#B74D5D` | **AA** | - | - | Chips, badges |
| Vert succes `#04854B` | **AA** | - | - | Badges succes |
| Rouge erreur `#E12329` | **AA** | - | - | Badges erreur |
| Jaune `#FEC180` | - | **AA** | **AA** | Decoratif |
| Orange saumon `#F5B399` | - | **AA** | **AA** | Decoratif |
| Orange warning `#FA9965` | - | **AA** | - | Badges warning |
| Vert pale `#C0E3CF` | - | **AA** | **AA** | Decoratif |
| Rouge clair `#FF7579` | - | **AA** | - | Scores |
| Jaune moutarde `#F7D35C` | - | **AA** | - | Scores |
| Vert clair `#82DB8A` | - | **AA** | - | Scores |
| Bleu ciel `#81C9D8` | - | **AA** | - | Scores |

### Texte colore sur fond blanc

| Couleur du texte | Sur fond blanc | Usage |
|------------------|:--------------:|-------|
| Bleu-vert `#025359` | **AA** | Titres, liens, actions |
| Noir `#343433` | **AA** | Texte principal |
| Gris fonce `#746F6E` | **AA** | Texte secondaire |
| Terra Cotta `#B74D5D` | **AA** | Liens, accents |
| Vert succes `#04854B` | **AA** | Messages succes |
| Rouge erreur `#E12329` | **AA** | Messages erreur |

### Couleurs a ne PAS utiliser pour du texte

Les couleurs suivantes ne doivent etre utilisees que pour des elements decoratifs (fonds, bordures, icones decoratives) :

- Jaune `#FEC180`
- Orange saumon `#F5B399`
- Vert pale `#C0E3CF`
- Rouge clair `#FF7579`
- Orange `#FA9965`
- Jaune moutarde `#F7D35C`
- Vert clair `#82DB8A`
- Bleu ciel `#81C9D8`

**Exception pour les textes larges** :
- Textes non gras > 18pt (24px)
- Textes gras > 14pt (18.5px)

---

## Chips et badges de statut

### Niveaux d'erreur (logs, alertes)

```scss
// WARNING: Orange avec texte noir
.status-warning {
  --mdc-chip-elevated-container-color: #FA9965;  // $warning-color
  --mdc-chip-label-text-color: #343433;          // $black
  color: #343433;
}

// ERROR: Rouge avec texte blanc
.status-error {
  --mdc-chip-elevated-container-color: #E12329;  // $error-color
  --mdc-chip-label-text-color: #FFFFFF;          // $white
  color: #FFFFFF;
}

// CRITICAL: Bleu-vert primaire avec texte blanc
.status-critical {
  --mdc-chip-elevated-container-color: #025359;  // $primary-color
  --mdc-chip-label-text-color: #FFFFFF;          // $white
  color: #FFFFFF;
}
```

### Statuts de validation

> ⚠️ **Obsolete** : ne plus ecrire de `mat-chip` + `.status-*` pour un statut.
> Utiliser `<app-tag>` (ou `<app-status-chip>` pour un statut de plan) — voir
> « Tags/Chips de statut » plus bas. Les classes `.status-*` restent definies
> dans `_material-overrides.scss`, realignees sur la palette pastel des tags,
> uniquement comme filet de securite pour le code non encore migre.

```scss
// Valide / Approuve       → <app-tag variant="success" icon="fi-rr-check">
// En attente / Brouillon  → <app-tag variant="warning" icon="fi-rr-edit">
// Rejete / Erreur         → <app-tag variant="error" icon="fi-rr-cross">
// Neutre                  → <app-tag variant="neutral">  (sans icone)
```

### Scores (jauges, evaluations)

```scss
.score-very-bad {
  --mdc-chip-elevated-container-color: #FF7579;
  --mdc-chip-label-text-color: #343433;  // Texte noir
}

.score-bad {
  --mdc-chip-elevated-container-color: #FA9965;
  --mdc-chip-label-text-color: #343433;  // Texte noir
}

.score-neutral {
  --mdc-chip-elevated-container-color: #F7D35C;
  --mdc-chip-label-text-color: #343433;  // Texte noir
}

.score-good {
  --mdc-chip-elevated-container-color: #82DB8A;
  --mdc-chip-label-text-color: #343433;  // Texte noir
}

.score-very-good {
  --mdc-chip-elevated-container-color: #81C9D8;
  --mdc-chip-label-text-color: #343433;  // Texte noir
}
```

---

## Graphiques (page Bilan de la gestion)

Releve exhaustif des maquettes Figma « CICADA modifie RNF-CEN v4 » :
`4488-35860` (bilan des indicateurs), `4488-36358` (bilan des actions).
Toute couleur d'un graphique doit venir de ce tableau — aucune valeur libre.

### Ce que chaque couleur veut dire

| Couleur | Hex | Ce qu'elle designe dans un graphique |
|---------|-----|--------------------------------------|
| Bleu-vert (principale) | `#025359` | Action **planifiee** ; trace et graduations du radar |
| Terra Cotta | `#B74D5D` | Action **non planifiee** ; RH **reelle** |
| Jaune | `#FEC180` | RH **previsionnelle** ; avancement des actions et des indicateurs (donuts) |
| Palette de scores | `#FF7579` `#FA9965` `#F7D35C` `#82DB8A` `#81C9D8` | Niveau d'evaluation d'un indicateur (1..5) |
| Vert pale | `#C0E3CF` | Fond des tuiles de chiffres cles (budget, RH) |
| Gris tres clair | `#E4E4E4` | Grille des axes (ligne de base en 2 px) |
| Noir | `#343433` | Libelles de legende et d'axes |
| Blanc | `#FFFFFF` | Fond de carte **et separateur entre segments** |

La couleur porte le **sujet** (qui ? planifie ou non, previsionnel ou reel),
jamais l'issue. C'est le motif qui porte l'issue.

### Motifs : plein / hachure / croix

Un graphique n'utilise que **deux couleurs au plus**, declinees en trois
motifs. Une serie = une couleur + un motif ; les six combinaisons se lisent
sans avoir a distinguer six teintes, y compris en impression noir et blanc.

| Motif | Sens | Rendu |
|-------|------|-------|
| Plein | Realise | aplat de la couleur |
| Hachures diagonales | Partiellement realise | fond couleur a **8 %** + traits a 45°, ~0,9 px, espaces de ~5,3 px |
| Croix | Non realise | fond couleur a **8 %** + croix de 4,5 px au pas de 9 px, 1 px |

Les traits d'un motif sont **toujours de la couleur de la serie**. La maquette
dessine les croix des donuts en noir `#343433` et celles des barres en couleur
de serie : c'est une incoherence du fichier, tranchee ici en faveur de la
couleur de serie — une seule regle pour les deux motifs, et la croix reste
rattachee visuellement a sa serie.

Les croix ne doivent pas se toucher (#640) : des diagonales pleine largeur
produisent un treillis continu, pas une grille de croix.

**Regle centrale — le fond d'un motif est la couleur de serie a 8 %
d'opacite, pas du blanc.** Un aplat blanc surcharge de traits colores donne
la teinte inverse de la maquette : c'est le defaut releve en recette.
Sur fond blanc, `rgba(2,83,89,.08)` s'aplatit en `#EBF1F2` — c'est la valeur
que porte la pastille de legende « Planifiee non realisee » dans Figma.

Les segments d'un empilement ou d'un donut sont **separes par un filet blanc**
(3 px sur un donut, 1 px sur une barre). Sans lui, deux segments de meme
couleur mais de motifs differents se confondent.

### Correspondance par graphique

| Graphique | Serie | Couleur | Motif |
|-----------|-------|---------|-------|
| Taux de realisation des indicateurs (donut) | 5 niveaux d'evaluation | palette de scores | plein |
| Evaluation des indicateurs (donut) | Fait / Pas fait | `#FEC180` | plein / croix |
| Taux de realisation des actions (donut) | Realisee / Partielle / Non realisee | `#FEC180` | plein / hachures / croix |
| Evolution jours RH par annee (barres groupees) | Previsionnel / Reel | `#FEC180` / `#B74D5D` | plein |
| Niveau de realisation des actions (barres empilees) | Planifiee realisee / partielle / non realisee | `#025359` | plein / hachures / croix |
| — suite | Non planifiee realisee / partielle | `#B74D5D` | plein / hachures |

Il n'existe pas de sixieme serie : une action ni prevue ni realisee n'a rien a
montrer. Le croise vient de `RealisationOperationAnneeViewSet._statut_key`,
aligne sur les icones du tableau de suivi (#379).

Les libelles d'axes restent a 13 px quelle que soit la largeur de la carte :
les composants bornent la largeur de leur `viewBox` (`maxWidth`) au lieu de
laisser le navigateur mettre le dessin — typographie comprise — a l'echelle.

### Radar des moyennes par enjeu/FCR

| Element | Specification |
|---------|---------------|
| Disque de fond | degrade radial, opacite **0.5** ; arrets `0 #FF7579`, `0.35 #FA9965`, `0.6 #F7D35C`, `0.85 #82DB8A`, `1 #81C9D8` |
| Anneaux de graduation | blanc, opacite **0.4** |
| Axes | blanc **opaque** |
| Polygone des valeurs | contour `#025359` 1.5 px, **sans remplissage** |
| Points | rayon 6, remplissage = couleur du score, contour `#025359` 1.5 px |
| Graduations 1..5 | `#025359`, 13 px regular |
| Libelles d'axes | `#343433`, 13 px regular |

Le degrade porte deja la lecture « rouge au centre, bleu au bord » : remplir le
polygone par-dessus le voile et fausse la couleur lue sous chaque point.

### Legende

Pastille **16 x 16 px**, rayon 4 px, ecart de 8 px avec le libelle.
Libelle en Nunito Regular 13 px `#343433`, valeur en Nunito Bold 13 px `#343433`.
Une pastille de serie a motif reprend **exactement** le remplissage du segment
(fond a 8 % + motif), sans bordure ajoutee.

---

## Fichiers SCSS du design system

Les styles du design system sont definis dans les fichiers suivants :

| Fichier | Description |
|---------|-------------|
| `src/assets/scss/_variables.scss` | Tokens (couleurs, spacing, typography, breakpoints) |
| `src/assets/scss/_typography.scss` | Styles typographiques + responsive typography |
| `src/assets/scss/_responsive.scss` | **Mixins responsive** (breakpoints, containers, grids) |
| `src/assets/scss/_material-overrides.scss` | Personnalisation Angular Material |
| `src/assets/scss/_components.scss` | Composants custom (jauges, tuiles, etc.) |
| `src/assets/scss/_filters.scss` | Filtres et pagination |
| `src/styles.scss` | Styles globaux et utilitaires responsive |

### Import dans les composants

```scss
// Dans un fichier .scss de composant
@import 'variables';

.mon-composant {
  color: $primary-color;
  background: $beige;
  padding: $spacing-md;
}
```

---

## Typographie

**Police principale** : Nunito (Google Font)

| Style | Font | Size | Weight | Line Height | Usage |
|-------|------|------|--------|-------------|-------|
| H1 | Nunito | 34px | Bold (700) | 1.165 | Titres de page |
| H2 | Nunito | 24px | Bold (700) | 1.2 | Titres de section |
| H3 | Nunito | 18px | Bold (700) | 1.3 | Sous-titres |
| Body | Nunito | 15px | Regular (400) | 24px | Texte courant |
| Small | Nunito | 12px | Regular (400) | 1.4 | Mentions, labels |

---

## Icones

### Flaticon Uicons (Rounded Regular)

```html
<!-- Utilisation -->
<i class="fi fi-rr-document"></i>
<i class="fi fi-rr-check"></i>
<i class="fi fi-rr-cross-circle"></i>
```

### Classes utilitaires pour les icones

```scss
.icon-xs   { font-size: 0.75rem; }
.icon-sm   { font-size: 0.875rem; }
.icon-md   { font-size: 1rem; }     // Defaut
.icon-lg   { font-size: 1.25rem; }
.icon-xl   { font-size: 1.5rem; }
.icon-xxl  { font-size: 2rem; }

.icon-primary { color: $primary-color; }
.icon-success { color: $success-color; }
.icon-error   { color: $error-color; }
.icon-warning { color: $warning-color; }
```

---

## Bonnes pratiques

1. **Toujours utiliser les variables SCSS** - Ne jamais coder en dur les valeurs hex
2. **Verifier l'accessibilite** - Utiliser uniquement les combinaisons approuvees AA
3. **Importer `variables`** - Dans chaque fichier SCSS de composant
4. **Consulter Figma** - Pour toute question sur le design, verifier la source de verite
5. **Penser mobile-first** - Tester sur petits ecrans, utiliser les mixins responsive

---

## Responsive Design

Le design system inclut un systeme complet de breakpoints et utilitaires responsive pour assurer la lisibilite sur tous les ecrans.

### Breakpoints

| Nom | Variable SCSS | Largeur max | Usage |
|-----|---------------|-------------|-------|
| Mobile | `$breakpoint-mobile` | 576px | Smartphones |
| Tablet | `$breakpoint-tablet` | 768px | Tablettes, petits laptops |
| Desktop | `$breakpoint-desktop` | 1024px | Laptops, ecrans moyens |
| Wide | `$breakpoint-wide` | 1440px | Grands ecrans |

### Mixins responsive (`_responsive.scss`)

Importer le fichier pour utiliser les mixins :

```scss
@import 'responsive';

.mon-composant {
  padding: $spacing-lg;

  @include tablet {
    padding: $spacing-md;
  }

  @include mobile {
    padding: $spacing-sm;
  }
}
```

**Mixins de breakpoints :**

| Mixin | Description |
|-------|-------------|
| `@include mobile { }` | 576px et moins |
| `@include tablet { }` | 768px et moins |
| `@include tablet-only { }` | Entre 577px et 768px |
| `@include desktop { }` | 1024px et moins |
| `@include wide { }` | 1025px et plus |

**Mixins de layout :**

| Mixin | Description |
|-------|-------------|
| `@include container-padding` | Padding adaptatif (48px > 32px > 24px > 16px) |
| `@include responsive-grid(4, 2, 1)` | Grille 4 > 2 > 1 colonnes |
| `@include responsive-flex-row` | Row > column sur mobile |
| `@include responsive-sidebar-layout(300px)` | Sidebar + content adaptatif |
| `@include responsive-table` | Table scrollable sur mobile |

**Mixins de typographie :**

| Mixin | Description |
|-------|-------------|
| `@include responsive-page-title` | H1 adaptatif (48px > 36px > 28px) |
| `@include responsive-section-title` | H2 adaptatif (32px > 28px > 22px) |
| `@include responsive-font(18px, 16px, 14px)` | Taille custom par breakpoint |

### Classes utilitaires responsive

**Affichage/masquage :**

```html
<!-- Masquer sur mobile -->
<div class="d-mobile-none">Visible sauf sur mobile</div>

<!-- Afficher uniquement sur tablette et moins -->
<div class="d-wide-none">Masque sur grands ecrans</div>
```

| Classe | Description |
|--------|-------------|
| `.d-mobile-none` | Masque sur mobile (576px-) |
| `.d-mobile-block/flex` | Affiche block/flex sur mobile |
| `.d-tablet-none` | Masque sur tablette (768px-) |
| `.d-small-desktop-none` | Masque sur petit desktop (1024px-) |
| `.d-wide-none` | Masque sur grand ecran (1025px+) |

**Espacements adaptatifs :**

```html
<div class="mb-lg mb-tablet-md mb-mobile-sm">
  Marge-bottom: 24px > 16px > 12px
</div>
```

| Suffixe | Mobile | Tablette |
|---------|--------|----------|
| `-mobile-xs/sm/md` | 8px / 12px / 16px | - |
| `-tablet-sm/md` | - | 12px / 16px |

**Flex responsive :**

```html
<div class="d-flex flex-tablet-column gap-lg gap-mobile-sm">
  <!-- Row sur desktop, column sur tablette -->
</div>
```

| Classe | Description |
|--------|-------------|
| `.flex-mobile-column` | Column sur mobile |
| `.flex-tablet-column` | Column sur tablette |
| `.gap-mobile-xs/sm/md` | Gap reduit sur mobile |

**Grilles responsives :**

```html
<div class="grid-responsive-4">
  <!-- 4 colonnes > 3 > 2 > 1 -->
</div>
```

| Classe | Desktop | Tablette | Mobile |
|--------|---------|----------|--------|
| `.grid-responsive-4` | 4 cols | 2 cols | 1 col |
| `.grid-responsive-3` | 3 cols | 2 cols | 1 col |
| `.grid-responsive-2` | 2 cols | 2 cols | 1 col |

**Containers :**

```html
<div class="container-responsive">
  <!-- Padding: 48px > 32px > 24px > 16px -->
</div>

<div class="container-responsive-compact">
  <!-- Padding: 24px > 16px > 12px -->
</div>
```

**Tables :**

```html
<div class="table-responsive">
  <table>...</table>
</div>
```

**Largeur :**

| Classe | Description |
|--------|-------------|
| `.w-mobile-100` | width: 100% sur mobile |
| `.w-tablet-100` | width: 100% sur tablette |

### Typographie responsive

Les titres s'adaptent automatiquement :

| Element | Desktop | Tablette | Mobile |
|---------|---------|----------|--------|
| H1 | 48px | 36px | 28px |
| H2 | 32px | 28px | 24px |
| H3 | 24px | 20px | 18px |
| H4 | 20px | 18px | 16px |
| Body | 15px | 14px | 14px |
| Small | 13px | 13px | 12px |

**Classes de taille par breakpoint :**

```html
<p class="text-mobile-lg">
  Texte plus grand sur mobile pour lisibilite
</p>
```

| Classe | Taille |
|--------|--------|
| `.text-mobile-lg` | 16px sur mobile |
| `.text-mobile-md` | 14px sur mobile |
| `.text-mobile-sm` | 12px sur mobile |
| `.text-tablet-lg/md/sm` | Idem pour tablette |

### Exemple complet

```html
<!-- Layout responsive -->
<div class="container-responsive">
  <h1>Titre de page</h1>

  <!-- Sidebar + content -->
  <div class="d-flex gap-lg flex-tablet-column">
    <aside class="d-tablet-none">
      Sidebar (masquee sur tablette)
    </aside>

    <main class="w-tablet-100">
      <!-- Grille de cartes -->
      <div class="grid-responsive-3">
        <div class="p-lg p-mobile-md">Carte 1</div>
        <div class="p-lg p-mobile-md">Carte 2</div>
        <div class="p-lg p-mobile-md">Carte 3</div>
      </div>

      <!-- Table scrollable -->
      <div class="table-responsive">
        <table>...</table>
      </div>
    </main>
  </div>
</div>
```

---

## Boutons

> **Source Figma** : Boutons et liens (voir `FIGMA_LINKS.md`)

### Boutons principaux (Primary)

Action principale, fond plein.

| Etat | Fond | Texte | Bordure |
|------|------|-------|---------|
| Defaut | `#025359` | Blanc | - |
| Survol | `#025359` (plus fonce) | Blanc | - |
| Actif (clique) | `#025359` | Blanc | - |
| Inactif | `#C6C6C6` | `#746F6E` | - |

```html
<!-- Angular Material -->
<button mat-flat-button color="primary">Defaut</button>
<button mat-flat-button color="primary" disabled>Inactif</button>
```

### Boutons secondaires (Secondary)

Action alternative, fond transparent avec bordure.

| Etat | Fond | Texte | Bordure |
|------|------|-------|---------|
| Defaut | Blanc | `#025359` | `#025359` |
| Survol | `#025359` | Blanc | `#025359` |
| Actif (clique) | `#025359` | Blanc | `#025359` |
| Inactif | Blanc | `#C6C6C6` | `#C6C6C6` |

```html
<!-- Angular Material -->
<button mat-stroked-button>Defaut</button>
<button mat-stroked-button disabled>Inactif</button>
```

### Boutons tertiaires (Text only)

Action discrete, texte seul sans fond ni bordure.

| Etat | Texte |
|------|-------|
| Defaut | `#025359` |
| Survol | `#025359` (fond leger) |
| Inactif | `#C6C6C6` |

```html
<!-- Angular Material -->
<button mat-button>Bouton tertiaire</button>
```

### Tailles de boutons

| Taille | Classe | Usage |
|--------|--------|-------|
| Medium (M) | - | Defaut, actions principales |
| Small (S) | `.btn-sm` | Actions secondaires, tableaux |

### Variantes de boutons

- **Dropdown** : Bouton avec chevron pour menu deroulant
- **Icone a gauche** : Bouton avec icone avant le texte
- **Icone + dropdown** : Combinaison des deux

### Boutons icone seule

Boutons circulaires ou carres avec icone uniquement.

| Etat | Fond | Icone |
|------|------|-------|
| Defaut | Transparent | `#025359` |
| Survol | `#025359` | Blanc |
| Clique | `#025359` (plus fonce) | Blanc |
| Inactif | Transparent | `#C6C6C6` |

---

## Formulaires

> **Source Figma** : Formulaires (voir `FIGMA_LINKS.md`)

### Champs de texte - Etats

| Etat | Bordure | Fond | Texte label | Texte input |
|------|---------|------|-------------|-------------|
| Vide | `#C6C6C6` | Blanc | `#343433` | - |
| Placeholder | `#C6C6C6` | Blanc | `#343433` | `#746F6E` (italic) |
| Rempli | `#C6C6C6` | Blanc | `#343433` | `#343433` |
| Focus | `#025359` + shadow | Blanc | `#343433` | `#343433` |
| Inactif | `#C6C6C6` | `#F6F6F6` | `#746F6E` | `#746F6E` |
| Erreur | `#E12329` | Blanc | `#343433` | `#343433` |

### Style du champ focus

```scss
// Shadow pour etat focus
box-shadow: 0px 0px 0px 2px rgba(2, 83, 89, 0.2);
border-color: $primary-color; // #025359
```

### Champ obligatoire

Le label est suivi d'un asterisque rouge.

```html
<label>Champ obligatoire <span class="text-error">*</span></label>
```

### Champ erreur

- Bordure rouge `#E12329`
- Icone d'exclamation rouge dans le champ
- Message d'erreur en rouge sous le champ

```html
<mat-form-field>
  <input matInput [class.error]="hasError">
  <mat-error>Message d'erreur</mat-error>
</mat-form-field>
```

### Texte d'aide

Deux formats possibles :
1. Texte d'aide sous le label (peut contenir un lien cliquable)
2. Icone info (i) a cote du label avec tooltip

### Types de champs speciaux

| Type | Description |
|------|-------------|
| Dropdown | Chevron a droite pour selection |
| Date | Format JJ/MM/AAAA avec icone calendrier |
| Recherche dropdown | Icone loupe + chevron |
| Textarea | Champ multiligne avec resize |
| Frequence | Input numerique avec boutons +/- |

### Checkbox et Radio

| Element | Bordure selectionnee | Bordure non selectionnee | Coche/Point |
|---------|---------------------|-------------------------|-------------|
| Checkbox | `#025359` | `#025359` | `#025359` |
| Radio | `#025359` | `#025359` | `#025359` |
| Inactif | `#C6C6C6` | `#C6C6C6` | `#C6C6C6` |

```scss
// Checkbox selectionnee
border-color: $primary-color;
.check-icon { color: $primary-color; }

// Radio selectionnee
border-color: $primary-color;
.radio-dot { background: $primary-color; }
```

---

## Tableaux

> **Source Figma** : Tableaux (voir `FIGMA_LINKS.md`)

### Header du tableau

| Element | Fond | Texte | Icone tri |
|---------|------|-------|-----------|
| Header | `#025359` | Blanc | Blanc (fleche) |
| Colonne triable active | `#025359` | Blanc | Blanc + fleche pleine |
| Colonne triable non triee | `#025359` | Blanc | Blanc + fleche vide |

```scss
.table-header {
  background: $primary-color;
  color: white;
  border-radius: 4px 4px 0 0;
}
```

### Lignes du tableau

| Element | Fond | Bordure |
|---------|------|---------|
| Ligne impaire | Blanc | - |
| Ligne paire | `#F6F6F6` (gris tres clair) | - |
| Filet separateur vertical | - | `#E4E4E4` (fin) |
| Contour tableau | - | `#E4E4E4`, border-radius 4px |

```scss
// Zebra striping
.table-row:nth-child(even) {
  background: $gray-lighter; // #F6F6F6
}
```

### Types de cellules

| Type | Description |
|------|-------------|
| Texte | Texte simple `#343433` |
| Texte bold col. principale | Font-weight bold, `#025359` |
| Texte + secondaire | Texte principal + texte gris `#746F6E` |
| Tag/Chip | Badge colore (voir section Chips) |
| Action | Boutons icone (voir section Boutons) |
| Cellule accordeon | Chevron pour deplier/replier |
| Input Min/Max | Deux champs numeriques |
| Checkbox | Case a cocher |
| Radio | Bouton radio |
| Jauge | Barre de progression coloree |

### Colonne fixee (scroll horizontal)

Si une colonne est fixee a gauche lors du scroll horizontal :
- Filet epais vertical a droite de la colonne fixee
- Ombre portee pour indiquer la separation

---

## Accordeons

> **Source Figma** : Accordeons (voir `FIGMA_LINKS.md`)

### Accordeon Large

Utilise pour les sections principales.

| Etat | Fond | Bordure gauche | Icones |
|------|------|----------------|--------|
| Ferme | `#F5B399` (saumon clair) | - | + (expand) |
| Ouvert | `#F5B399` | - | Crayon (edit) + - (collapse) |

```scss
.accordion-large {
  background: rgba($secondary-orange-salmon, 0.2);
  border-radius: 8px;

  &.open {
    .accordion-header { border-radius: 8px 8px 0 0; }
  }
}
```

### Accordeon Indicateur d'etat

Contient un indicateur et des sous-elements.

| Element | Style |
|---------|-------|
| Header | Fond blanc, bordure grise |
| Indicateur | Texte "non" ou valeur |
| Sous-accordeon | Fond vert pale `#C0E3CF`, bordure gauche `#025359` |

### Accordeon Action

Affiche les details d'une action avec metadonnees.

| Element | Style |
|---------|-------|
| Header | Fond blanc, icone Terra Cotta |
| Type d'action | Badge/tag |
| Priorite | Numerote |
| Details | Labels uppercase + valeurs |

### Accordeon Section

Style simple pour sections de contenu.

| Etat | Style |
|------|-------|
| Ferme | Texte uppercase, chevron bas |
| Ouvert | Texte uppercase, chevron haut |

### Accordeon Small

Liste compacte avec puces colorees.

| Element | Style |
|---------|-------|
| Header | Texte simple, chevron |
| Items | Puce coloree (vert `#04854B` ou rouge `#E12329`) + texte |

---

## Autres composants

> **Source Figma** : Autres composants (voir `FIGMA_LINKS.md`)

### Tags/Chips de statut

> **Source Figma** : « 🧩 Tags » (node `4487-30877`). Composant : `<app-tag>`
> (`shared/components/tag/`). Mapping statut → couleur + icone :
> `shared/utils/tag-icons.ts` (source de verite unique).

Palette pastel, **texte toujours noir `#343433`** (les fonds sont desatures
pour rester AA avec du noir). Pill `border-radius: 40px`, hauteur 24px,
padding `2px 10px`, libelle Nunito Regular 13px, icone 12px.

| Variante | Fond | Variable SCSS | Icone | Usage |
|----------|------|---------------|-------|-------|
| `success` | `#CFF1D3` | `$tag-green` | `fi-rr-check` | Valide, Approuve, Actif |
| `error` | `#FFC7C9` | `$tag-red` | `fi-rr-cross` | Rejete, Annule, Expire, Inactif, Erreur |
| `info` / `primary` | `#C1E5EC` | `$tag-cyan` | `fi-rr-memo-circle-check` / `fi-rr-user` | Modifie, Utilisateur |
| `warning` / `draft` | `#FFE6CC` | `$tag-orange` | `fi-rr-edit` / `fi-rr-star` | Brouillon, En attente, Referent |
| `neutral` | `#F9CFBE` | `$tag-salmon` | **aucune** | Libelle neutre |
| `muted` | `#E4E4E4` | `$tag-gray` | `fi-rr-box` | Archive |

**Regles issues des annotations de la maquette :**

1. « Tag avec icone pour les statuts principaux ou la couleur et l'icone font
   sens. Pour les autres, une couleur unique de tag, sans icone, afin de ne pas
   multiplier les icones et les couleurs. » → tout libelle qui n'est pas un
   statut connu utilise `variant="neutral"` **sans icone**.
2. « Ne pas utiliser de composant tag/chips, mettre simplement le libelle en
   texte normal » pour deux categories : le **type d'aire protegee**
   (RNN, RNR, PNR, ENS…) et la **reference d'un site / d'un organisme**
   (code INPN). La valeur ajoutee du tag y est jugee limitee et il prend trop
   de place dans les tableaux.
3. Ne jamais reutiliser `$success-color` (#04854B) / `$error-color` (#E12329)
   pour un tag : ce sont des couleurs pleines qui exigent du texte blanc.
   Elles restent valables pour les messages et les puces, pas pour les tags.
4. Verifier qu'une icone existe dans le set **Uicons Rounded Regular 2.6.0**
   avant usage : le nom de la maquette ne correspond pas toujours a un glyphe
   reel (ex. `fi-rr-file-check` n'existe pas → `fi-rr-memo-circle-check`).

### Separateur

Ligne horizontale simple.

```scss
.separator {
  border-bottom: 1px solid $gray-light; // #E4E4E4
  margin: $spacing-md 0;
}
```

### Liste a puces colorees

Puces carrees avec couleur semantique.

| Type | Couleur puce |
|------|--------------|
| Positif/Fait | `#04854B` (vert) |
| Negatif/A faire | `#E12329` (rouge) |
| Neutre | `#025359` (primary) |

```scss
.list-colored-bullets {
  li::before {
    content: '';
    width: 8px;
    height: 8px;
    background: $success-color; // ou $error-color
    margin-right: $spacing-sm;
  }
}
```

### Jauges de progression

| Etat | Couleur barre | Description |
|------|---------------|-------------|
| Non demarre | `#81C9D8` (bleu clair) | Barre vide ou tres courte |
| Mi-parcours | `#82DB8A` (vert clair) | Barre a ~50% |
| Parcours termine | `#FA9965` (orange) | Barre complete |
| Parcours depasse | `#E12329` (rouge) | Barre complete + indicateur depassement |

```scss
.gauge {
  height: 8px;
  border-radius: 4px;
  background: $gray-light;

  .gauge-fill {
    border-radius: 4px;
    &.not-started { background: $score-very-good; width: 10%; }
    &.mid-progress { background: $score-good; width: 50%; }
    &.completed { background: $warning-color; width: 100%; }
    &.exceeded { background: $error-color; width: 100%; }
  }
}
```

### Bloc info/conseil

Encadre avec fond colore pour informations importantes.

| Type | Fond | Bordure gauche |
|------|------|----------------|
| Info/Conseil | `#C0E3CF` (vert pale) | - |
| Warning | `#FEC180` (jaune) | - |
| Erreur | `rgba(#E12329, 0.1)` | `#E12329` |

```scss
.info-block {
  background: $secondary-pale-green;
  padding: $spacing-md;
  border-radius: 8px;

  .info-title { font-weight: bold; }
}
```

### Filtres

| Element | Style |
|---------|-------|
| Bouton FILTRER | Primary filled |
| Dropdowns | Fond blanc, bordure grise, chevron |
| Dropdown ouvert | Liste checkbox avec labels |
| Badge compteur | Cercle primary avec nombre |

### Tuiles de navigation

| Element | Style |
|---------|-------|
| Image | Coins arrondis 20px en haut |
| Titre | Texte + fleche, fond blanc |
| Contour | Ombre portee legere |

### Liste de documents

| Element | Style |
|---------|-------|
| Icone dossier | Primary `#025359` |
| Nom fichier | Puce carree primary + texte |
| Action telechargement | Icone download primary |
| Bouton Ajouter | Secondary stroked |

### Pagination

| Element | Style |
|---------|-------|
| Page active | Fond primary `#025359`, texte blanc |
| Page inactive | Fond blanc, texte `#343433` |
| Ellipsis | "..." |
| Fleches | Chevrons primary |

```scss
.pagination {
  .page-btn {
    min-width: 32px;
    height: 32px;
    border-radius: 4px;

    &.active {
      background: $primary-color;
      color: white;
    }
  }
}
```

---

## Iconographie

> **Source Figma** : Iconographie (voir `FIGMA_LINKS.md`)

### Bibliotheque principale : UICONS by Flaticon

**Style** : Rounded Corners (`fi-rr-*`)

**Integration CDN** : Ajouter dans le `<head>` ou via `angular.json` :
```html
<link rel="stylesheet" href="https://cdn-uicons.flaticon.com/uicons-regular-rounded/css/uicons-regular-rounded.css">
```

**Usage** :
```html
<i class="fi fi-rr-home"></i>
<i class="fi fi-rr-document"></i>
<i class="fi fi-rr-user"></i>
<i class="fi fi-rr-search"></i>
<i class="fi fi-rr-settings"></i>
```

### Icones personnalisees

Icones creees specifiquement pour le projet.

#### Indicateurs de realisation d'actions

| Statut | Description | Fichier |
|--------|-------------|---------|
| Action prevue | Cercle pointille | `action-planned.svg` |
| Prevue et realisee | Cercle plein + check | `action-planned-realized.svg` |
| Prevue partiellement realisee | Demi-cercle + check | `action-planned-partial.svg` |
| Realisee non prevue | Cercle + X | `action-realized-unplanned.svg` |
| Partiellement realisee non prevue | Demi-cercle + X | `action-partial-unplanned.svg` |

#### Icones de jauges

Icones colorees pour les etats de progression (voir section Jauges).

### Scores (Smileys)

Icones SVG pour l'evaluation.

| Score | Couleur | Description |
|-------|---------|-------------|
| Tres mauvais | `#FF7579` | Smiley tres mecontent |
| Mauvais | `#FA9965` | Smiley mecontent |
| Moyen | `#F7D35C` | Smiley neutre |
| Bon | `#82DB8A` | Smiley content |
| Tres bon | `#81C9D8` | Smiley tres content |
| Sans donnee | `#DADADA` | Smiley gris |

**Composant Angular** : `ScoreIconComponent`
```html
<app-score-icon level="good" [size]="24"></app-score-icon>
```

### Classes utilitaires pour icones

```scss
// Tailles
.icon-xs   { font-size: 0.75rem; }   // 12px
.icon-sm   { font-size: 0.875rem; }  // 14px
.icon-md   { font-size: 1rem; }      // 16px (defaut)
.icon-lg   { font-size: 1.25rem; }   // 20px
.icon-xl   { font-size: 1.5rem; }    // 24px
.icon-xxl  { font-size: 2rem; }      // 32px

// Couleurs
.icon-primary { color: $primary-color; }
.icon-success { color: $success-color; }
.icon-error   { color: $error-color; }
.icon-warning { color: $warning-color; }
.icon-muted   { color: $gray; }

// Bouton icone
.icon-btn {
  cursor: pointer;
  &:hover { color: darken($primary-color, 10%); }
}

// Icone circulaire
.icon-circle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: $primary-color;
  color: white;
}
```

### Images et textures

Le kit inclut des formes decoratives :
- **Forme arriere** : Texture de feuille (PNG ou SVG modifiable)
- **Forme fluidon** : Forme abstraite pour fonds

Usage recommande : fonds de tuiles, headers de sections.

---

## References

- **Kit UI Figma** : Voir `FIGMA_LINKS.md` (non versionne) - contient les liens vers toutes les sections (Couleurs, Boutons, Formulaires, Tableaux, Accordeons, Autres composants, Iconographie)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Contrast Checker](https://webaim.org/resources/contrastchecker/)
