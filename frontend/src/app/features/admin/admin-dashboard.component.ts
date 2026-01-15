import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../core/services/auth.service';
import { AdminService, DashboardStats } from '../../core/services/admin.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule],
  templateUrl: './admin-dashboard.component.html',
  styleUrl: './admin-dashboard.component.scss'
})
export class AdminDashboardComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;

  isLoading = signal(false);
  errorMessage = signal<string | null>(null);

  stats = signal<DashboardStats>({
    totalPlans: 0,
    plansActifs: 0,
    totalUtilisateurs: 0,
    totalSites: 0,
    totalOrganismes: 0
  });

  userDisplayName = computed(() => {
    return this.authService.getUserDisplayName();
  });

  organismeName = computed(() => {
    const user = this.currentUser();
    return user?.organisme?.nom_organisme || 'Organisme inconnu';
  });

  ngOnInit(): void {
    this.loadDashboardData();
  }

  loadDashboardData(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.getDashboardStats().subscribe({
      next: (data) => {
        this.stats.set(data);
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoading.set(false);
      }
    });
  }
}
