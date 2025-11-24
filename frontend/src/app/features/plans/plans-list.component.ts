import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-plans-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="plans-container">
      <h2>Plans de Gestion</h2>
      <p>Liste des plans de gestion - À implémenter</p>
    </div>
  `,
  styles: [`
    .plans-container {
      padding: 2rem;
    }
  `]
})
export class PlansListComponent {}
