import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { PublicStatsService } from '../../core/services/public-stats.service';

@Component({
  selector: 'app-exploration',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    TranslateModule,
    HeaderComponent
  ],
  templateUrl: './exploration.component.html',
  styleUrl: './exploration.component.scss'
})
export class ExplorationComponent implements OnInit {
  private readonly publicStatsService = inject(PublicStatsService);

  // Public stats
  readonly stats = this.publicStatsService.stats;
  readonly statsLoading = this.publicStatsService.isLoading;

  ngOnInit(): void {
    // Load stats if not already loaded
    if (!this.stats()) {
      this.publicStatsService.loadStats().subscribe();
    }
  }
}
