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
  signal,
  Renderer2,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import * as L from 'leaflet';

/**
 * Composant carte Leaflet en lecture seule.
 * Affiche des données GeoJSON (polygones, points) avec style personnalisé.
 */
@Component({
  selector: 'app-leaflet-map',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './leaflet-map.component.html',
  styleUrl: './leaflet-map.component.scss'
})
export class LeafletMapComponent implements OnInit, AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('mapContainer') mapContainer!: ElementRef;

  /** Données GeoJSON (Feature ou FeatureCollection) */
  @Input() geojsonData: any = null;

  /** Hauteur du conteneur de la carte */
  @Input() height: string = '400px';

  /** Niveau de zoom par défaut */
  @Input() zoom: number = 6;

  /** Coordonnées du centre [lat, lng] - France par défaut */
  @Input() center: [number, number] = [46.227638, 2.213749];

  /** Activer les interactions (zoom, pan) */
  @Input() interactive: boolean = true;

  /** Afficher les contrôles de zoom */
  @Input() showControls: boolean = true;

  /** Auto-ajuster la vue aux features */
  @Input() fitBounds: boolean = true;

  /** Afficher le bouton plein écran */
  @Input() showFullscreen: boolean = false;

  /** Événement émis au clic sur une feature */
  @Output() featureClick = new EventEmitter<any>();

  private map: L.Map | null = null;
  private geoJsonLayer: L.GeoJSON | null = null;
  readonly isFullscreen = signal(false);
  // Suivi du déplacement utilisateur pour afficher le bouton "Recentrer" (revue design #310)
  readonly userHasMoved = signal(false);
  private readonly renderer = inject(Renderer2);

  // Couleurs du design system
  private readonly primaryColor = '#025359';
  private readonly secondaryColor = '#FEC180';
  private readonly fillColor = 'rgba(2, 83, 89, 0.2)';

  ngOnInit(): void {
    // Note: Leaflet icons fix is applied in main.ts at app startup
  }

  ngAfterViewInit(): void {
    this.initMap();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['geojsonData'] && !changes['geojsonData'].firstChange) {
      this.updateGeoJSON();
    }
  }

  ngOnDestroy(): void {
    this.renderer.removeClass(document.body, 'leaflet-map-fullscreen-active');
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  /**
   * Initialise la carte Leaflet
   */
  private initMap(): void {
    if (!this.mapContainer?.nativeElement) return;

    // Options de la carte
    const mapOptions: L.MapOptions = {
      center: this.center,
      zoom: this.zoom,
      zoomControl: this.showControls,
      dragging: this.interactive,
      scrollWheelZoom: this.interactive,
      doubleClickZoom: this.interactive,
      boxZoom: this.interactive,
      keyboard: this.interactive,
      touchZoom: this.interactive
    };

    // Créer la carte
    this.map = L.map(this.mapContainer.nativeElement, mapOptions);

    // Ajouter le fond de carte OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(this.map);

    // Suivre les déplacements utilisateur pour afficher le bouton "Recentrer" (revue design #310)
    this.map.on('movestart zoomstart', () => {
      this.userHasMoved.set(true);
    });

    // Ajouter les données GeoJSON si présentes
    if (this.geojsonData) {
      this.updateGeoJSON();
    }

    // Forcer le rafraîchissement de la carte après le rendu
    setTimeout(() => {
      this.map?.invalidateSize();
      // Reset le flag : les `setView`/`fitBounds` initiaux ne comptent pas comme déplacement utilisateur
      this.userHasMoved.set(false);
    }, 100);
  }

  /**
   * Met à jour les données GeoJSON sur la carte
   */
  private updateGeoJSON(): void {
    if (!this.map) return;

    // Supprimer l'ancien layer
    if (this.geoJsonLayer) {
      this.map.removeLayer(this.geoJsonLayer);
      this.geoJsonLayer = null;
    }

    // Si pas de données, ne rien faire
    if (!this.geojsonData) return;

    // Style pour les polygones et lignes
    const defaultStyle: L.PathOptions = {
      color: this.primaryColor,
      weight: 2,
      opacity: 1,
      fillColor: this.fillColor,
      fillOpacity: 0.3
    };

    // Options pour les points (cercles)
    const pointToLayer = (feature: any, latlng: L.LatLng): L.Layer => {
      return L.circleMarker(latlng, {
        radius: 8,
        fillColor: this.primaryColor,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
      });
    };

    // Créer le layer GeoJSON
    this.geoJsonLayer = L.geoJSON(this.geojsonData, {
      style: defaultStyle,
      pointToLayer,
      onEachFeature: (feature, layer) => {
        // Popup avec le nom si disponible
        const name = feature.properties?.nom_site || feature.properties?.name || feature.properties?.nom;
        if (name) {
          layer.bindPopup(`<strong>${name}</strong>`);
        }

        // Événement au clic
        layer.on('click', () => {
          this.featureClick.emit(feature);
        });

        // Effet hover
        layer.on('mouseover', () => {
          if (layer instanceof L.Path) {
            layer.setStyle({
              weight: 3,
              fillOpacity: 0.5
            });
          }
        });

        layer.on('mouseout', () => {
          if (layer instanceof L.Path) {
            layer.setStyle(defaultStyle);
          }
        });
      }
    }).addTo(this.map);

    // Ajuster la vue aux features
    if (this.fitBounds && this.geoJsonLayer.getBounds().isValid()) {
      this.map.fitBounds(this.geoJsonLayer.getBounds(), {
        padding: [20, 20],
        maxZoom: 15
      });
    }
  }

  /**
   * Recentre la carte sur les données
   */
  recenter(): void {
    if (this.map && this.geoJsonLayer && this.geoJsonLayer.getBounds().isValid()) {
      this.map.fitBounds(this.geoJsonLayer.getBounds(), {
        padding: [20, 20],
        maxZoom: 15
      });
    } else if (this.map) {
      this.map.setView(this.center, this.zoom);
    }
    // Reset l'état "déplacé" pour cacher le bouton (revue design #310)
    this.userHasMoved.set(false);
  }

  /**
   * Basculer le mode plein écran
   */
  toggleFullscreen(): void {
    this.isFullscreen.update(v => !v);
    // Toggle body class to hide other content when map is fullscreen
    if (this.isFullscreen()) {
      this.renderer.addClass(document.body, 'leaflet-map-fullscreen-active');
    } else {
      this.renderer.removeClass(document.body, 'leaflet-map-fullscreen-active');
    }
    // Rafraîchir la carte après le changement de taille
    setTimeout(() => {
      this.map?.invalidateSize();
      if (this.fitBounds && this.geoJsonLayer?.getBounds().isValid()) {
        this.map?.fitBounds(this.geoJsonLayer.getBounds(), { padding: [20, 20] });
      }
    }, 100);
  }

  /**
   * Rafraîchir manuellement la carte
   */
  refresh(): void {
    this.map?.invalidateSize();
  }
}
