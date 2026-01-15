import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type ScoreLevel = 'very-bad' | 'bad' | 'neutral' | 'good' | 'very-good' | 'no-data';

@Component({
  selector: 'app-score-icon',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './score-icon.component.html',
  styleUrl: './score-icon.component.scss'
})
export class ScoreIconComponent {
  @Input() level: ScoreLevel = 'neutral';
  @Input() size: number = 20;

  getBackgroundColor(): string {
    const colors: Record<ScoreLevel, string> = {
      'very-bad': '#FF7579',    // $score-very-bad
      'bad': '#FA9965',         // $score-bad
      'neutral': '#F7D35C',     // $score-neutral
      'good': '#82DB8A',        // $score-good
      'very-good': '#81C9D8',   // $score-very-good
      'no-data': '#DADADA'      // Gray for no data
    };
    return colors[this.level];
  }

  getElementColor(): string {
    // Use white for dark backgrounds, dark for light backgrounds
    const darkElements: ScoreLevel[] = ['neutral', 'no-data'];
    return darkElements.includes(this.level) ? '#333333' : '#FFFFFF';
  }

  getLabel(): string {
    const labels: Record<ScoreLevel, string> = {
      'very-bad': 'Très mauvais',
      'bad': 'Mauvais',
      'neutral': 'Moyen',
      'good': 'Bon',
      'very-good': 'Très bon',
      'no-data': 'Sans donnée'
    };
    return labels[this.level];
  }
}
