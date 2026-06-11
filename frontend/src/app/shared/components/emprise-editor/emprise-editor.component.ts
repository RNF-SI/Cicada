import { Component, input, model, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { LeafletMapEditComponent } from '../leaflet-map-edit/leaflet-map-edit.component';

/**
 * Éditeur d'emprise spatiale réutilisable (carte + dessin Leaflet-Draw + import
 * de fichier GeoJSON / Shapefile). Factorise la logique dupliquée entre la
 * saisie d'un suivi et le formulaire d'opération (et cohérent avec le module
 * des sites).
 *
 * - `geometry`            : géométrie principale à afficher / éditer (GeoJSON).
 * - `backgroundGeometry`  : géométrie de repère affichée en arrière-plan
 *                           (ex. emprise prévue derrière l'emprise réalisée).
 * - `disabled`            : masque les outils d'édition (lecture seule).
 * - `editing`             : mode dessin/import (two-way bindable : le parent
 *                           peut le réinitialiser après enregistrement).
 *
 * La légende (prévu / réalisé) est projetée par le parent via `[empriseLegend]`.
 */
@Component({
  selector: 'app-emprise-editor',
  standalone: true,
  imports: [CommonModule, TranslateModule, LeafletMapEditComponent],
  templateUrl: './emprise-editor.component.html',
  styleUrl: './emprise-editor.component.scss',
})
export class EmpriseEditorComponent {
  geometry = input<any>(null);
  backgroundGeometry = input<any>(null);
  disabled = input<boolean>(false);
  height = input<string>('320px');

  // Libellés (clés i18n) surchargeables selon le contexte.
  emptyLabel = input<string>('common.emprise.empty');
  startDrawLabel = input<string>('common.emprise.startDraw');
  stopDrawLabel = input<string>('common.emprise.stopDraw');
  drawHintLabel = input<string>('common.emprise.drawHint');

  /** Mode édition (dessin/import) — bindable two-way (`[(editing)]`). */
  editing = model<boolean>(false);

  /** Émis à chaque modification de la géométrie (GeoJSON ou null). */
  geometryChange = output<any>();

  toggle(): void {
    if (this.disabled()) return;
    this.editing.update(v => !v);
  }

  onChange(geom: any): void {
    this.geometryChange.emit(geom);
  }
}
