/**
 * Dialog de consultation d'un protocole CAMPanule.
 */
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { CampanuleService } from '../../../../core/services/campanule.service';
import { CampanuleProtocoleDetail } from '../../../../core/models/campanule.model';

export interface ProtocoleCampanuleDialogData {
  cdProtocole: number;
}

@Component({
  selector: 'app-protocole-campanule-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    TranslateModule,
  ],
  templateUrl: './protocole-campanule-dialog.component.html',
  styleUrl: './protocole-campanule-dialog.component.scss',
})
export class ProtocoleCampanuleDialogComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<ProtocoleCampanuleDialogComponent>);
  private readonly data: ProtocoleCampanuleDialogData = inject(MAT_DIALOG_DATA);
  private readonly campanuleService = inject(CampanuleService);
  private readonly translate = inject(TranslateService);

  protocole = signal<CampanuleProtocoleDetail | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.campanuleService.getProtocole(this.data.cdProtocole).subscribe({
      next: (p) => {
        this.protocole.set(p);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('campanule.errors.loadFailed'));
        this.isLoading.set(false);
      },
    });
  }

  close(): void {
    this.dialogRef.close();
  }

  openUrl(url: string | undefined): void {
    if (url) {
      window.open(url, '_blank', 'noopener');
    }
  }
}
