import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="home-container">
      <h1>Outil Plan de Gestion</h1>
      <p>Bienvenue sur l'outil de gestion des plans de conservation</p>
      <div class="info-block info-primary">
        <h4 class="info-title">
          <span class="info-icon">ℹ️</span>
          Application en développement
        </h4>
        <p class="info-content">
          Le design system Biodiv' France est intégré et prêt à l'emploi.
        </p>
      </div>
    </div>
  `,
  styles: [`
    .home-container {
      padding: 2rem;
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      color: var(--primary-color, #022F39);
      margin-bottom: 1rem;
    }
  `]
})
export class HomeComponent {}
