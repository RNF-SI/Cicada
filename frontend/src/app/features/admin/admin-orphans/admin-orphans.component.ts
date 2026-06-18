import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { AuthService } from '../../../core/services/auth.service';
import { OrphansService, OrphanSite, OrphanPlan } from '../../../core/services/orphans.service';

@Component({
  selector: 'app-admin-orphans',
  standalone: true,
  imports: [CommonModule, RouterModule, MatProgressSpinnerModule, TranslateModule],
  templateUrl: './admin-orphans.component.html',
  styleUrl: './admin-orphans.component.scss'
})
export class AdminOrphansComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly orphansService = inject(OrphansService);

  readonly hasGlobalAccess = this.authService.hasGlobalAccess;

  readonly isLoading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly sites = signal<OrphanSite[]>([]);
  readonly plans = signal<OrphanPlan[]>([]);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.orphansService.getOrphans().subscribe({
      next: (data) => {
        this.sites.set(data.sites);
        this.plans.set(data.plans);
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoading.set(false);
      }
    });
  }
}
