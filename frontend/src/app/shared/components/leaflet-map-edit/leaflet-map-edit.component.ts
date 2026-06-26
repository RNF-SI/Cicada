import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnInit,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ElementRef,
  ViewChild,
  AfterViewInit,
  inject,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import * as L from 'leaflet';
import 'leaflet-draw';
import shp from 'shpjs';

/**
 * Composant carte Leaflet avec outils de dessin (leaflet-draw).
 * Permet de créer et éditer des géométries (polygones, points).
 */
@Component({
  selector: 'app-leaflet-map-edit',
  standalone: true,
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatSnackBarModule,
    TranslateModule
  ],
  templateUrl: './leaflet-map-edit.component.html',
  styleUrl: './leaflet-map-edit.component.scss'
})
export class LeafletMapEditComponent implements OnInit, AfterViewInit, OnChanges, OnDestroy {
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  @ViewChild('mapContainer') mapContainer!: ElementRef;
  @ViewChild('geometryFileInput') geometryFileInput!: ElementRef<HTMLInputElement>;

  /** Géométrie existante à éditer (GeoJSON) - polygone */
  @Input() existingGeometry: any = null;

  /**
   * Géométrie d'arrière-plan affichée en lecture seule (style pointillé,
   * couleur secondaire). Utile pour garder visible l'emprise précédente
   * pendant qu'on dessine une nouvelle emprise par-dessus (ex. saisie de
   * l'emprise réalisée pour un suivi d'opération : la dernière emprise
   * prévue reste visible comme repère).
   */
  @Input() backgroundGeometry: any = null;

  /** Géométrie point existante (pour mode 'both') */
  @Input() existingPointGeometry: any = null;

  /** Hauteur du conteneur */
  @Input() height: string = '400px';

  /** Type de géométrie à dessiner: 'polygon', 'point', ou 'both' */
  @Input() geometryType: 'polygon' | 'point' | 'both' = 'polygon';

  /** Niveau de zoom par défaut */
  @Input() zoom: number = 6;

  /** Coordonnées du centre [lat, lng] */
  @Input() center: [number, number] = [46.227638, 2.213749];

  /** Activer l'import de fichiers géographiques (GeoJSON, Shapefile) */
  @Input() enableGeometryImport: boolean = false;

  /**
   * Afficher le bouton d'import dans la barre d'outils de la carte.
   * Permet de garder l'import actif (input fichier caché + handler) tout en
   * masquant le bouton in-map lorsqu'un bouton d'import existe déjà ailleurs
   * (ex. formulaire site, #390). Sans effet si `enableGeometryImport` est faux.
   */
  @Input() showImportButton: boolean = true;

  /**
   * Mode lecture seule : la carte affiche `existingGeometry` (et
   * éventuellement `backgroundGeometry`) sans afficher la barre d'outils
   * de dessin. Pratique pour partager le même composant entre prévisualisation
   * et édition tout en gardant un rendu visuel cohérent (notamment
   * l'arrière-plan terra-cotta pointillé).
   */
  @Input() readOnly: boolean = false;

  /** État de l'import shapefile */
  readonly isImporting = signal(false);

  /** Événement émis quand la géométrie polygone change */
  @Output() geometryChange = new EventEmitter<any>();

  /** Événement émis quand la géométrie point change (pour mode 'both') */
  @Output() pointGeometryChange = new EventEmitter<any>();

  private map: L.Map | null = null;
  private drawnItems: L.FeatureGroup | null = null;
  private pointItems: L.FeatureGroup | null = null; // Groupe séparé pour les points en mode 'both'
  /** Calque non éditable pour `backgroundGeometry` (style pointillé). */
  private backgroundLayer: L.GeoJSON | null = null;
  private drawControl: L.Control.Draw | null = null;

  // Couleurs du design system
  private readonly primaryColor = '#025359';
  private readonly secondaryColor = '#FEC180';
  private readonly fillColor = 'rgba(2, 83, 89, 0.3)';
  // Style d'arrière-plan : terra-cotta pointillé (utilisé pour distinguer
  // l'emprise précédente de celle qu'on est en train d'éditer).
  private readonly backgroundColor = '#B74D5D';
  private readonly backgroundFillColor = 'rgba(183, 77, 93, 0.12)';

  ngOnInit(): void {
    // Note: Leaflet icons fix is applied in main.ts at app startup
  }

  ngAfterViewInit(): void {
    this.initMap();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['existingGeometry'] && !changes['existingGeometry'].firstChange) {
      this.loadExistingGeometry();
    }
    if (changes['backgroundGeometry'] && !changes['backgroundGeometry'].firstChange) {
      this.loadBackgroundGeometry();
    }
    if (changes['geometryType'] && !changes['geometryType'].firstChange) {
      this.updateDrawControl();
    }
    // Basculer entre lecture seule et édition doit ajouter/retirer les outils
    // de dessin Leaflet-Draw. Sans ça, le bouton « Dessiner » changeait bien
    // `readOnly` mais la barre d'outils crayon n'apparaissait jamais (elle
    // n'était configurée qu'à l'init, où readOnly valait true).
    if (changes['readOnly'] && !changes['readOnly'].firstChange) {
      this.setupDrawControl();
    }
  }

  ngOnDestroy(): void {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  /**
   * Initialise la carte avec les outils de dessin
   */
  private initMap(): void {
    if (!this.mapContainer?.nativeElement) {
      console.warn('initMap: mapContainer non disponible');
      return;
    }

    console.log('initMap: initialisation de la carte');

    // Créer la carte
    this.map = L.map(this.mapContainer.nativeElement, {
      center: this.center,
      zoom: this.zoom,
      zoomControl: true
    });

    // Fond de carte
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(this.map);

    // Groupe pour les formes dessinées (polygones)
    this.drawnItems = new L.FeatureGroup();
    this.map.addLayer(this.drawnItems);

    // Groupe séparé pour les points en mode 'both'
    if (this.geometryType === 'both') {
      this.pointItems = new L.FeatureGroup();
      this.map.addLayer(this.pointItems);
    }

    // Configurer les outils de dessin
    this.setupDrawControl();

    // Charger les géométries existantes
    if (this.backgroundGeometry) {
      this.loadBackgroundGeometry();
    }
    if (this.existingGeometry) {
      this.loadExistingGeometry();
    }
    if (this.geometryType === 'both' && this.existingPointGeometry) {
      this.loadExistingPointGeometry();
    }

    // Événements de dessin
    this.setupDrawEvents();

    // Rafraîchir après le rendu - plusieurs fois pour les modals
    setTimeout(() => {
      this.map?.invalidateSize();
      console.log('initMap: invalidateSize (100ms)');
    }, 100);

    setTimeout(() => {
      this.map?.invalidateSize();
      // Recharger la géométrie si elle n'a pas été affichée correctement
      if (this.existingGeometry && this.drawnItems && this.drawnItems.getLayers().length === 0) {
        console.log('initMap: rechargement de la géométrie (300ms)');
        this.loadExistingGeometry();
      }
    }, 300);

    setTimeout(() => {
      this.map?.invalidateSize();
    }, 500);
  }

  /**
   * Configure les outils de dessin selon le type de géométrie
   */
  private setupDrawControl(): void {
    if (!this.map || !this.drawnItems) return;

    // Supprimer l'ancien contrôle si présent
    if (this.drawControl) {
      this.map.removeControl(this.drawControl);
      this.drawControl = null;
    }
    // En lecture seule on n'ajoute simplement aucun contrôle de dessin.
    if (this.readOnly) return;

    // Configuration des textes en français pour leaflet-draw
    this.configureDrawLocale();

    // Options de style pour le dessin de polygones
    const polygonOptions: L.DrawOptions.PolygonOptions = {
      allowIntersection: true, // Permettre les intersections pour éviter les rejets
      shapeOptions: {
        color: this.primaryColor,
        weight: 2,
        fillColor: this.fillColor,
        fillOpacity: 0.3
      }
    };

    // Options selon le type de géométrie
    const showPolygonTools = this.geometryType === 'polygon' || this.geometryType === 'both';
    const showPointTools = this.geometryType === 'point' || this.geometryType === 'both';

    const drawOptions: L.Control.DrawConstructorOptions = {
      position: 'topleft',
      draw: {
        polygon: showPolygonTools ? polygonOptions : false,
        rectangle: false,  // Désactivé - seuls les polygones et points sont autorisés
        circle: false,
        circlemarker: false,
        marker: showPointTools ? {} : false,
        polyline: false
      },
      edit: {
        featureGroup: this.drawnItems,
        // #431 : on conserve l'outil de suppression leaflet-draw (poubelle de
        // gauche) car c'est lui qui permet de supprimer UNE seule entité
        // (cliquer une forme/un marqueur pour la retirer). Le bouton « Tout
        // effacer » custom (poubelle de droite) a été retiré du template pour
        // éviter le doublon. On conserve l'outil d'édition (crayon).
        remove: true
      }
    };

    this.drawControl = new L.Control.Draw(drawOptions);
    this.map.addControl(this.drawControl);
  }

  /**
   * Configure les textes en français pour leaflet-draw (optionnel, ne doit pas bloquer l'init)
   */
  private configureDrawLocale(): void {
    try {
      const drawLocal = (L as any).drawLocal;
      if (!drawLocal) return;

      // Toolbar draw
      if (drawLocal.draw?.toolbar) {
        if (drawLocal.draw.toolbar.actions) {
          drawLocal.draw.toolbar.actions.title = 'Annuler le dessin';
          drawLocal.draw.toolbar.actions.text = 'Annuler';
        }
        if (drawLocal.draw.toolbar.finish) {
          drawLocal.draw.toolbar.finish.title = 'Terminer le dessin';
          drawLocal.draw.toolbar.finish.text = 'Terminer';
        }
        if (drawLocal.draw.toolbar.undo) {
          drawLocal.draw.toolbar.undo.title = 'Supprimer le dernier point';
          drawLocal.draw.toolbar.undo.text = 'Supprimer le dernier point';
        }
        if (drawLocal.draw.toolbar.buttons) {
          drawLocal.draw.toolbar.buttons.polygon = 'Dessiner un polygone';
          drawLocal.draw.toolbar.buttons.rectangle = 'Dessiner un rectangle';
          drawLocal.draw.toolbar.buttons.marker = 'Placer un marqueur';
        }
      }

      // Handlers draw
      if (drawLocal.draw?.handlers) {
        if (drawLocal.draw.handlers.marker?.tooltip) {
          drawLocal.draw.handlers.marker.tooltip.start = 'Cliquez sur la carte pour placer le marqueur.';
        }
        if (drawLocal.draw.handlers.polygon?.tooltip) {
          drawLocal.draw.handlers.polygon.tooltip.start = 'Cliquez pour commencer le polygone.';
          drawLocal.draw.handlers.polygon.tooltip.cont = 'Continuez à cliquer. Double-cliquez ou cliquez sur le 1er point pour fermer.';
          drawLocal.draw.handlers.polygon.tooltip.end = 'Cliquez sur le premier point pour fermer.';
        }
        if (drawLocal.draw.handlers.rectangle?.tooltip) {
          drawLocal.draw.handlers.rectangle.tooltip.start = 'Cliquez et glissez pour dessiner un rectangle.';
        }
        if (drawLocal.draw.handlers.simpleshape?.tooltip) {
          drawLocal.draw.handlers.simpleshape.tooltip.end = 'Relâchez pour terminer.';
        }
      }

      // Toolbar edit
      if (drawLocal.edit?.toolbar) {
        if (drawLocal.edit.toolbar.actions?.save) {
          drawLocal.edit.toolbar.actions.save.title = 'Enregistrer les modifications';
          drawLocal.edit.toolbar.actions.save.text = 'Enregistrer';
        }
        if (drawLocal.edit.toolbar.actions?.cancel) {
          drawLocal.edit.toolbar.actions.cancel.title = 'Annuler les modifications';
          drawLocal.edit.toolbar.actions.cancel.text = 'Annuler';
        }
        if (drawLocal.edit.toolbar.actions?.clearAll) {
          drawLocal.edit.toolbar.actions.clearAll.title = 'Tout effacer';
          drawLocal.edit.toolbar.actions.clearAll.text = 'Tout effacer';
        }
        if (drawLocal.edit.toolbar.buttons) {
          drawLocal.edit.toolbar.buttons.edit = 'Modifier les formes';
          drawLocal.edit.toolbar.buttons.editDisabled = 'Aucune forme à modifier';
          drawLocal.edit.toolbar.buttons.remove = 'Supprimer les formes';
          drawLocal.edit.toolbar.buttons.removeDisabled = 'Aucune forme à supprimer';
        }
      }

      // Handlers edit
      if (drawLocal.edit?.handlers) {
        if (drawLocal.edit.handlers.edit?.tooltip) {
          drawLocal.edit.handlers.edit.tooltip.text = 'Glissez les points pour modifier.';
          drawLocal.edit.handlers.edit.tooltip.subtext = 'Cliquez sur Annuler pour annuler.';
        }
        if (drawLocal.edit.handlers.remove?.tooltip) {
          drawLocal.edit.handlers.remove.tooltip.text = 'Cliquez sur une forme pour la supprimer.';
        }
      }
    } catch (e) {
      console.warn('Impossible de configurer les textes leaflet-draw en français:', e);
    }
  }

  /**
   * Met à jour le contrôle de dessin
   */
  private updateDrawControl(): void {
    this.setupDrawControl();
  }

  /**
   * Configure les événements de dessin
   */
  private setupDrawEvents(): void {
    if (!this.map) return;

    // Utiliser les chaînes d'événements directement (plus fiable)
    // Nouvelle forme créée
    this.map.on('draw:created', (e: any) => {
      console.log('draw:created - type:', e.layerType);
      const layer = e.layer;
      const isMarker = e.layerType === 'marker';

      if (this.geometryType === 'both') {
        // En mode 'both', markers et polygones sont mutuellement exclusifs
        // On peut avoir UN marker OU un ou plusieurs polygones, mais pas les deux
        if (isMarker) {
          // Dessiner un marker supprime tous les polygones
          this.drawnItems?.clearLayers();
          this.pointItems?.clearLayers(); // Un seul marker
          this.pointItems?.addLayer(layer);
          this.emitGeometry(); // Émet null car plus de polygones
          this.emitPointGeometry();
        } else {
          // Dessiner un polygone supprime le marker, mais permet plusieurs polygones
          this.pointItems?.clearLayers();
          this.drawnItems?.addLayer(layer);
          this.emitPointGeometry(); // Émet null car plus de marker
          this.emitGeometry();
        }
      } else if (this.geometryType === 'polygon') {
        // Mode polygone: permet plusieurs polygones
        this.drawnItems?.addLayer(layer);
        this.emitGeometry();
      } else {
        // Mode point: un seul marker
        this.drawnItems?.clearLayers();
        this.drawnItems?.addLayer(layer);
        this.emitGeometry();
      }
      console.log('draw:created - layer ajouté');
    });

    // Forme éditée
    this.map.on('draw:edited', () => {
      console.log('draw:edited');
      this.emitGeometry();
    });

    // Forme supprimée
    this.map.on('draw:deleted', () => {
      console.log('draw:deleted');
      this.emitGeometry();
    });

    // Événements de debug
    this.map.on('draw:drawstart', (e: any) => {
      console.log('draw:drawstart - type:', e.layerType);
    });

    this.map.on('draw:drawstop', () => {
      console.log('draw:drawstop');
    });

    this.map.on('draw:drawvertex', (e: any) => {
      console.log('draw:drawvertex');
    });
  }

  /**
   * Charge une géométrie existante sur la carte
   */
  private loadExistingGeometry(): void {
    if (!this.drawnItems || !this.map) {
      console.warn('loadExistingGeometry: drawnItems ou map non initialisé');
      return;
    }

    // Vider les formes existantes
    this.drawnItems.clearLayers();

    if (!this.existingGeometry) {
      console.log('loadExistingGeometry: pas de géométrie existante');
      return;
    }

    console.log('loadExistingGeometry: chargement de', this.existingGeometry);

    try {
      // La géométrie peut être un objet geometry direct ou une Feature GeoJSON
      let geojsonData = this.existingGeometry;

      // Si c'est une géométrie simple (pas une Feature), la wrapper
      if (geojsonData.type && !geojsonData.geometry && geojsonData.coordinates) {
        geojsonData = {
          type: 'Feature',
          properties: {},
          geometry: geojsonData
        };
      }

      console.log('loadExistingGeometry: données à charger', geojsonData);

      const style = {
        color: this.primaryColor,
        weight: 2,
        fillColor: this.fillColor,
        fillOpacity: 0.3
      };

      // #435 — Un MultiPolygon chargé en un seul layer n'est pas correctement
      // éditable par leaflet-draw (Edit.Poly ne génère pas de poignées de
      // sommets exploitables). On l'éclate donc en polygones individuels
      // éditables ; `emitGeometry()` les recombine en MultiPolygon à la
      // sauvegarde. Cela rend notamment éditable l'emprise copiée d'un site (#410).
      const geom = geojsonData.geometry;
      let layerCount = 0;
      if (geom && geom.type === 'MultiPolygon' && Array.isArray(geom.coordinates)) {
        geom.coordinates.forEach((polygonCoords: any) => {
          const polyFeature: any = { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: polygonCoords } };
          const polyLayer = L.geoJSON(polyFeature, { style });
          polyLayer.eachLayer((layer) => {
            this.drawnItems?.addLayer(layer);
            layerCount++;
          });
        });
      } else {
        const geoJsonLayer = L.geoJSON(geojsonData, {
          style,
          pointToLayer: (feature, latlng) => {
            return L.marker(latlng);
          }
        });
        geoJsonLayer.eachLayer((layer) => {
          this.drawnItems?.addLayer(layer);
          layerCount++;
        });
      }

      console.log('loadExistingGeometry:', layerCount, 'layers ajoutés');

      // Ajuster la vue : on inclut aussi l'éventuelle géométrie d'arrière-plan
      // pour ne pas la cadrer hors-écran.
      const bounds = this.drawnItems.getBounds();
      if (this.backgroundLayer && this.backgroundLayer.getBounds().isValid()) {
        bounds.extend(this.backgroundLayer.getBounds());
      }
      if (bounds.isValid()) {
        this.map.fitBounds(bounds, {
          padding: [50, 50],
          maxZoom: 15
        });
      }
    } catch (error) {
      console.error('Erreur lors du chargement de la géométrie:', error);
    }
  }

  /**
   * Charge la géométrie d'arrière-plan (non éditable, style pointillé).
   * Sert à conserver une empreinte de référence visible (par exemple
   * l'emprise prévue) pendant qu'on dessine une nouvelle emprise réalisée.
   */
  private loadBackgroundGeometry(): void {
    if (!this.map) return;

    // Retirer l'ancien layer s'il existe
    if (this.backgroundLayer) {
      this.map.removeLayer(this.backgroundLayer);
      this.backgroundLayer = null;
    }
    if (!this.backgroundGeometry) return;

    try {
      let geojsonData = this.backgroundGeometry;
      if (geojsonData.type && !geojsonData.geometry && geojsonData.coordinates) {
        geojsonData = { type: 'Feature', properties: {}, geometry: geojsonData };
      }
      this.backgroundLayer = L.geoJSON(geojsonData, {
        interactive: false, // non cliquable, juste un repère visuel
        style: {
          color: this.backgroundColor,
          weight: 2,
          dashArray: '6,4',
          fillColor: this.backgroundFillColor,
          fillOpacity: 0.4,
        },
      });
      // Le layer d'arrière-plan est ajouté DERRIÈRE le drawnItems (Leaflet
      // empile dans l'ordre d'ajout — comme drawnItems est ajouté plus tôt,
      // on utilise bringToBack() pour s'assurer du z-order).
      this.backgroundLayer.addTo(this.map);
      this.backgroundLayer.bringToBack();

      // Si rien n'est encore dessiné, on cadre sur le repère.
      if ((!this.drawnItems || this.drawnItems.getLayers().length === 0)
          && this.backgroundLayer.getBounds().isValid()) {
        this.map.fitBounds(this.backgroundLayer.getBounds(), {
          padding: [50, 50],
          maxZoom: 15,
        });
      }
    } catch (error) {
      console.error('Erreur lors du chargement de la géométrie d\'arrière-plan:', error);
    }
  }

  /**
   * Force la lecture de la géométrie actuellement dessinée sur la carte et la
   * (ré)émet vers le parent. À appeler avant une sauvegarde : leaflet-draw ne
   * déclenche `draw:edited` que si l'utilisateur valide son édition via la coche
   * de la barre d'outils. Sans ce flush, des sommets déplacés mais non
   * « validés » ne seraient jamais remontés et l'ancienne trace serait
   * enregistrée (#440).
   */
  flushGeometry(): void {
    this.emitGeometry();
    this.emitPointGeometry();
  }

  /**
   * Émet la géométrie actuelle au format GeoJSON
   */
  private emitGeometry(): void {
    if (!this.drawnItems) {
      this.geometryChange.emit(null);
      return;
    }

    const layers = this.drawnItems.getLayers();

    if (layers.length === 0) {
      this.geometryChange.emit(null);
      return;
    }

    // Pour un point (mode 'point' uniquement)
    if (this.geometryType === 'point' && layers.length > 0) {
      const layer = layers[0] as L.Marker;
      const latlng = layer.getLatLng();
      const geojson = {
        type: 'Point',
        coordinates: [latlng.lng, latlng.lat]
      };
      this.geometryChange.emit(geojson);
      return;
    }

    // Pour les polygones (mode 'polygon' ou 'both')
    // Combiner tous les polygones en un MultiPolygon
    if ((this.geometryType === 'polygon' || this.geometryType === 'both') && layers.length > 0) {
      const allCoordinates: any[] = [];

      layers.forEach((layer) => {
        if (layer instanceof L.Polygon) {
          const geojson = (layer as L.Polygon).toGeoJSON();
          if (geojson.geometry.type === 'Polygon') {
            allCoordinates.push(geojson.geometry.coordinates);
          } else if (geojson.geometry.type === 'MultiPolygon') {
            allCoordinates.push(...geojson.geometry.coordinates);
          }
        }
      });

      if (allCoordinates.length === 0) {
        this.geometryChange.emit(null);
        return;
      }

      const multiPolygon = {
        type: 'MultiPolygon',
        coordinates: allCoordinates
      };
      this.geometryChange.emit(multiPolygon);
      return;
    }
  }

  /**
   * Charge une géométrie point existante (mode 'both')
   */
  private loadExistingPointGeometry(): void {
    if (!this.pointItems || !this.map) return;

    this.pointItems.clearLayers();

    if (!this.existingPointGeometry) return;

    try {
      let geojsonData = this.existingPointGeometry;

      // Si c'est une géométrie simple, la wrapper
      if (geojsonData.type && !geojsonData.geometry && geojsonData.coordinates) {
        geojsonData = {
          type: 'Feature',
          properties: {},
          geometry: geojsonData
        };
      }

      const geoJsonLayer = L.geoJSON(geojsonData, {
        pointToLayer: (feature, latlng) => {
          return L.marker(latlng);
        }
      });

      geoJsonLayer.eachLayer((layer) => {
        this.pointItems?.addLayer(layer);
      });
    } catch (error) {
      console.error('Erreur chargement point:', error);
    }
  }

  /**
   * Émet la géométrie point (mode 'both')
   */
  private emitPointGeometry(): void {
    if (!this.pointItems) {
      this.pointGeometryChange.emit(null);
      return;
    }

    const layers = this.pointItems.getLayers();
    if (layers.length === 0) {
      this.pointGeometryChange.emit(null);
      return;
    }

    const layer = layers[0] as L.Marker;
    const latlng = layer.getLatLng();
    const geojson = {
      type: 'Point',
      coordinates: [latlng.lng, latlng.lat]
    };
    this.pointGeometryChange.emit(geojson);
  }

  /**
   * Efface toutes les formes dessinées
   */
  clearAll(): void {
    this.drawnItems?.clearLayers();
    this.pointItems?.clearLayers();
    this.geometryChange.emit(null);
    this.pointGeometryChange.emit(null);
  }

  /**
   * Recentre la carte sur la France
   */
  recenter(): void {
    if (this.map) {
      if (this.drawnItems && this.drawnItems.getBounds().isValid()) {
        this.map.fitBounds(this.drawnItems.getBounds(), { padding: [50, 50] });
      } else {
        this.map.setView(this.center, this.zoom);
      }
    }
  }

  /**
   * Rafraîchir la carte
   */
  refresh(): void {
    this.map?.invalidateSize();
  }

  // ===================
  // Import de fichiers géographiques (GeoJSON, Shapefile)
  // ===================

  /**
   * Déclenche le sélecteur de fichier.
   */
  triggerGeometryImport(): void {
    this.geometryFileInput?.nativeElement?.click();
  }

  /**
   * Gère la sélection d'un fichier géographique.
   * Supporte les fichiers :
   * - GeoJSON : .geojson, .json
   * - Shapefile : .zip (contenant .shp, .dbf, .prj) ou .shp direct
   */
  async onGeometryFileSelected(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) return;

    // Vérifier l'extension
    const extension = file.name.split('.').pop()?.toLowerCase();
    const supportedExtensions = ['geojson', 'json', 'zip', 'shp'];

    if (!extension || !supportedExtensions.includes(extension)) {
      this.snackBar.open(
        this.translate.instant('sites.form.geometry.import.invalidFormat'),
        this.translate.instant('common.actions.close'),
        { duration: 5000 }
      );
      return;
    }

    this.isImporting.set(true);

    try {
      let geojson: any;

      // Traitement selon le type de fichier
      if (extension === 'geojson' || extension === 'json') {
        // Fichier GeoJSON - lire comme texte et parser
        const text = await file.text();
        geojson = JSON.parse(text);
      } else if (extension === 'zip') {
        // Fichier ZIP contenant tous les fichiers shapefile.
        // ⚠️ shpjs v6 : NE PAS appeler `shp.parseZip`. Dans le build ESM utilisé
        // par Angular, `parseZip`/`parseShp` sont des exports *nommés* et ne sont
        // PAS attachés au default → `shp.parseZip` vaut `undefined` et lève
        // « shp.parseZip is not a function », ce qui faisait échouer TOUT import
        // shapefile avec le message générique « vérifier le format » (#88 / #24).
        // Le default export est lui-même appelable et gère le buffer .zip, avec
        // reprojection automatique vers WGS84 d'après le .prj (testé EPSG:2154).
        const arrayBuffer = await file.arrayBuffer();
        geojson = await shp(arrayBuffer);
      } else if (extension === 'shp') {
        // Fichier .shp seul - parser les géométries via l'export nommé `parseShp`
        // (absent du default en build ESM, cf. ci-dessus).
        const arrayBuffer = await file.arrayBuffer();
        const shpjs: any = await import('shpjs');
        const parseShp = shpjs.parseShp ?? shpjs.default?.parseShp;
        const geometries = parseShp ? parseShp(arrayBuffer) : [];
        if (geometries && geometries.length > 0) {
          geojson = {
            type: 'FeatureCollection',
            features: geometries.map((geom: any) => ({
              type: 'Feature',
              properties: {},
              geometry: geom
            }))
          };
        }
      }

      // shpjs peut renvoyer un tableau de FeatureCollection (zip multi-couches) :
      // on fusionne alors en une seule FeatureCollection.
      if (Array.isArray(geojson)) {
        geojson = {
          type: 'FeatureCollection',
          features: geojson.flatMap((fc: any) => fc?.features ?? [])
        };
      }

      if (!geojson) {
        throw new Error('Format de fichier invalide');
      }

      // Traiter et afficher la géométrie importée
      this.processImportedGeometry(geojson);

      this.snackBar.open(
        this.translate.instant('sites.form.geometry.import.success'),
        this.translate.instant('common.actions.close'),
        { duration: 3000 }
      );
    } catch (error) {
      console.error('Erreur import géométrie:', error);
      this.snackBar.open(
        this.translate.instant('sites.form.geometry.import.error'),
        this.translate.instant('common.actions.close'),
        { duration: 5000 }
      );
    } finally {
      this.isImporting.set(false);
      // Reset l'input pour permettre de réimporter le même fichier
      input.value = '';
    }
  }

  /**
   * Traite la géométrie importée depuis un shapefile.
   * Extrait les polygones et les affiche sur la carte.
   */
  private processImportedGeometry(geojson: any): void {
    if (!this.drawnItems || !this.map) return;

    // Extraire la géométrie
    let geometry: any = null;

    if (geojson.type === 'FeatureCollection' && geojson.features?.length > 0) {
      // Filtrer les polygones uniquement
      const features = geojson.features.filter((f: any) =>
        f.geometry?.type === 'Polygon' || f.geometry?.type === 'MultiPolygon'
      );

      if (features.length === 1) {
        geometry = features[0].geometry;
      } else if (features.length > 1) {
        // Combiner en MultiPolygon
        const coordinates: any[] = [];
        features.forEach((f: any) => {
          if (f.geometry.type === 'Polygon') {
            coordinates.push(f.geometry.coordinates);
          } else if (f.geometry.type === 'MultiPolygon') {
            coordinates.push(...f.geometry.coordinates);
          }
        });
        geometry = {
          type: 'MultiPolygon',
          coordinates
        };
      }
    } else if (geojson.type === 'Feature') {
      geometry = geojson.geometry;
    } else if (geojson.type === 'Polygon' || geojson.type === 'MultiPolygon') {
      geometry = geojson;
    }

    if (!geometry) {
      this.snackBar.open(
        this.translate.instant('sites.form.geometry.import.noGeometry'),
        this.translate.instant('common.actions.close'),
        { duration: 5000 }
      );
      return;
    }

    // Convertir en MultiPolygon si c'est un Polygon
    if (geometry.type === 'Polygon') {
      geometry = {
        type: 'MultiPolygon',
        coordinates: [geometry.coordinates]
      };
    }

    // Effacer les formes existantes
    this.drawnItems.clearLayers();

    // Créer et ajouter le layer GeoJSON
    const geoJsonLayer = L.geoJSON({
      type: 'Feature',
      properties: {},
      geometry: geometry
    } as any, {
      style: {
        color: this.primaryColor,
        weight: 2,
        fillColor: this.fillColor,
        fillOpacity: 0.3
      }
    });

    geoJsonLayer.eachLayer((layer) => {
      this.drawnItems?.addLayer(layer);
    });

    // Ajuster la vue
    if (this.drawnItems.getBounds().isValid()) {
      this.map.fitBounds(this.drawnItems.getBounds(), {
        padding: [50, 50],
        maxZoom: 15
      });
    }

    // Émettre la géométrie
    this.geometryChange.emit(geometry);
  }
}
