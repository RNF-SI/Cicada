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
  AfterViewInit
} from '@angular/core';
import { CommonModule } from '@angular/common';
import * as L from 'leaflet';
import 'leaflet-draw';

/**
 * Composant carte Leaflet avec outils de dessin (leaflet-draw).
 * Permet de créer et éditer des géométries (polygones, points).
 */
@Component({
  selector: 'app-leaflet-map-edit',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './leaflet-map-edit.component.html',
  styleUrl: './leaflet-map-edit.component.scss'
})
export class LeafletMapEditComponent implements OnInit, AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('mapContainer') mapContainer!: ElementRef;

  /** Géométrie existante à éditer (GeoJSON) */
  @Input() existingGeometry: any = null;

  /** Hauteur du conteneur */
  @Input() height: string = '400px';

  /** Type de géométrie à dessiner */
  @Input() geometryType: 'polygon' | 'point' = 'polygon';

  /** Niveau de zoom par défaut */
  @Input() zoom: number = 6;

  /** Coordonnées du centre [lat, lng] */
  @Input() center: [number, number] = [46.227638, 2.213749];

  /** Événement émis quand la géométrie change */
  @Output() geometryChange = new EventEmitter<any>();

  private map: L.Map | null = null;
  private drawnItems: L.FeatureGroup | null = null;
  private drawControl: L.Control.Draw | null = null;

  // Couleurs du design system
  private readonly primaryColor = '#025359';
  private readonly secondaryColor = '#FEC180';
  private readonly fillColor = 'rgba(2, 83, 89, 0.3)';

  ngOnInit(): void {
    this.fixLeafletIcons();
  }

  ngAfterViewInit(): void {
    this.initMap();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['existingGeometry'] && !changes['existingGeometry'].firstChange) {
      this.loadExistingGeometry();
    }
    if (changes['geometryType'] && !changes['geometryType'].firstChange) {
      this.updateDrawControl();
    }
  }

  ngOnDestroy(): void {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  /**
   * Corrige le chemin des icônes Leaflet
   */
  private fixLeafletIcons(): void {
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'assets/leaflet/marker-icon-2x.png',
      iconUrl: 'assets/leaflet/marker-icon.png',
      shadowUrl: 'assets/leaflet/marker-shadow.png'
    });
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
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19
    }).addTo(this.map);

    // Groupe pour les formes dessinées
    this.drawnItems = new L.FeatureGroup();
    this.map.addLayer(this.drawnItems);

    // Configurer les outils de dessin
    this.setupDrawControl();

    // Charger la géométrie existante si présente
    if (this.existingGeometry) {
      this.loadExistingGeometry();
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
    }

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

    // Options de style pour le rectangle
    const rectangleOptions: L.DrawOptions.RectangleOptions = {
      shapeOptions: {
        color: this.primaryColor,
        weight: 2,
        fillColor: this.fillColor,
        fillOpacity: 0.3
      }
    };

    // Options selon le type de géométrie
    const drawOptions: L.Control.DrawConstructorOptions = {
      position: 'topleft',
      draw: {
        polygon: this.geometryType === 'polygon' ? polygonOptions : false,
        rectangle: this.geometryType === 'polygon' ? rectangleOptions : false,
        circle: false,
        circlemarker: false,
        marker: this.geometryType === 'point' ? {} : false,
        polyline: false
      },
      edit: {
        featureGroup: this.drawnItems,
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

      // Pour les polygones, on n'autorise qu'une seule forme
      if (this.geometryType === 'polygon') {
        this.drawnItems?.clearLayers();
      }
      // Pour les points, on n'autorise qu'un seul marker
      if (this.geometryType === 'point') {
        this.drawnItems?.clearLayers();
      }

      this.drawnItems?.addLayer(layer);
      console.log('draw:created - layer ajouté, total:', this.drawnItems?.getLayers().length);
      this.emitGeometry();
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

      // Créer un layer GeoJSON
      const geoJsonLayer = L.geoJSON(geojsonData, {
        style: {
          color: this.primaryColor,
          weight: 2,
          fillColor: this.fillColor,
          fillOpacity: 0.3
        },
        pointToLayer: (feature, latlng) => {
          return L.marker(latlng);
        }
      });

      // Ajouter chaque layer au groupe éditable
      let layerCount = 0;
      geoJsonLayer.eachLayer((layer) => {
        this.drawnItems?.addLayer(layer);
        layerCount++;
      });

      console.log('loadExistingGeometry:', layerCount, 'layers ajoutés');

      // Ajuster la vue
      if (this.drawnItems.getBounds().isValid()) {
        this.map.fitBounds(this.drawnItems.getBounds(), {
          padding: [50, 50],
          maxZoom: 15
        });
      }
    } catch (error) {
      console.error('Erreur lors du chargement de la géométrie:', error);
    }
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

    // Pour un point
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

    // Pour un polygone - convertir en MultiPolygon si nécessaire
    if (this.geometryType === 'polygon' && layers.length > 0) {
      const layer = layers[0] as L.Polygon;
      const geojson = layer.toGeoJSON();

      // Convertir Polygon en MultiPolygon pour le backend
      if (geojson.geometry.type === 'Polygon') {
        const multiPolygon = {
          type: 'MultiPolygon',
          coordinates: [geojson.geometry.coordinates]
        };
        this.geometryChange.emit(multiPolygon);
      } else {
        this.geometryChange.emit(geojson.geometry);
      }
      return;
    }
  }

  /**
   * Efface toutes les formes dessinées
   */
  clearAll(): void {
    this.drawnItems?.clearLayers();
    this.geometryChange.emit(null);
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
}
