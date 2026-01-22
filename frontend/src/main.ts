import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import * as L from 'leaflet';

// Fix Leaflet default marker icons path before any map component is created
// Images are served from /media/images/ (copied from src/assets/images via angular.json)
// Setting imagePath disables Leaflet's automatic path detection via CSS (which causes 404 errors)
L.Icon.Default.imagePath = 'media/images/';
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'marker-icon-2x.png',
  iconUrl: 'marker-icon.png',
  shadowUrl: 'marker-shadow.png'
});

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));