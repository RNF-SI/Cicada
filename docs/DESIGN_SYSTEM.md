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

```scss
// Valide / Approuve
.status-success, .status-valide {
  --mdc-chip-elevated-container-color: rgba(#04854B, 0.15);
  --mdc-chip-label-text-color: #04854B;
}

// En attente
.status-warning, .status-pending {
  --mdc-chip-elevated-container-color: rgba(#FA9965, 0.15);
  --mdc-chip-label-text-color: #343433;
}

// Rejete / Erreur
.status-error, .status-rejected {
  --mdc-chip-elevated-container-color: rgba(#E12329, 0.15);
  --mdc-chip-label-text-color: #E12329;
}

// Neutre / Info
.status-neutre, .status-info {
  --mdc-chip-elevated-container-color: rgba(#81C9D8, 0.15);
  --mdc-chip-label-text-color: #025359;
}
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

## Fichiers SCSS du design system

Les styles du design system sont definis dans les fichiers suivants :

| Fichier | Description |
|---------|-------------|
| `src/assets/scss/_variables.scss` | Tokens (couleurs, spacing, typography) |
| `src/assets/scss/_typography.scss` | Styles typographiques |
| `src/assets/scss/_material-overrides.scss` | Personnalisation Angular Material |
| `src/assets/scss/_components.scss` | Composants custom (jauges, tuiles, etc.) |
| `src/assets/scss/_filters.scss` | Filtres et pagination |
| `src/styles.scss` | Styles globaux et utilitaires |

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

| Statut | Fond | Texte |
|--------|------|-------|
| Valide | `#04854B` | Blanc |
| Invalide | `#E12329` | Blanc |
| En cours | `#FEC180` | `#343433` |
| Brouillon | `#C6C6C6` | `#343433` |

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
