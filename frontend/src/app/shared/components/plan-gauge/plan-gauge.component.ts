import { Component, Input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

export type GaugeStatus = 'not-started' | 'first-half' | 'second-half' | 'exceeded';

@Component({
  selector: 'app-plan-gauge',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './plan-gauge.component.html',
  styleUrl: './plan-gauge.component.scss'
})
export class PlanGaugeComponent {
  @Input() status: GaugeStatus = 'not-started';
  @Input() startYear: number = 2020;
  @Input() endYear: number = 2030;
  @Input() currentYear: number = new Date().getFullYear();

  fillPercentage = computed(() => {
    if (this.status === 'not-started') return 0;
    if (this.status === 'exceeded') return 100;

    const totalDuration = this.endYear - this.startYear;
    if (totalDuration <= 0) return 0;

    const elapsed = this.currentYear - this.startYear;
    const percentage = (elapsed / totalDuration) * 100;
    return Math.max(0, Math.min(100, percentage));
  });

  pointerPosition = computed(() => {
    return this.fillPercentage();
  });

  colorTheme = computed(() => {
    if (this.status === 'second-half' || this.status === 'exceeded') {
      return 'terra-cotta';
    }
    return 'primary';
  });

  showMidpointMarker = computed(() => {
    return this.status !== 'not-started';
  });
}
