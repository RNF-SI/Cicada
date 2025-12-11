import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { NavigationTileComponent } from '../../shared/components/navigation-tile/navigation-tile.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    HeaderComponent,
    NavigationTileComponent
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
  // Generate array for data visualization waves
  dataWaveIndices = Array.from({ length: 8 }, (_, i) => i);

  // Generate wavy path for data visualization
  getDataWavePath(index: number): string {
    const baseY = 50 + (index - 4) * 8;
    const amplitude = 15 + (index % 3) * 5;
    const frequency = 0.8 + (index % 4) * 0.2;

    let path = `M0,${baseY}`;
    for (let x = 0; x <= 600; x += 20) {
      const y = baseY + Math.sin((x * frequency * Math.PI) / 180) * amplitude;
      path += ` L${x},${y.toFixed(1)}`;
    }
    return path;
  }
}
