# Design System CICADA

Ce document decrit les regles du design system de l'application CICADA, basees sur le Kit UI Biodiv (11/2025).

**Source de reference** : `KitUI/` (maquettes PNG) et Figma [Biodiv - livrable 2025](https://www.figma.com/design/Q55BtQrWL8VHV8YOWlynlY/Biodiv---livrable-2025-Antoine)

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

## References

- [Kit UI Figma](https://www.figma.com/design/Q55BtQrWL8VHV8YOWlynlY/Biodiv---livrable-2025-Antoine)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Contrast Checker](https://webaim.org/resources/contrastchecker/)
