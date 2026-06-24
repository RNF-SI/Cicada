import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

interface LogFile { name: string; size: number; }
interface LogContent { file: string; lines: string[]; returned: number; total: number; truncated: boolean; }

/**
 * #456 — Consultation des FICHIERS de logs serveur (django.log / error.log /
 * audit.log) par le super_admin, depuis l'interface (complément de #384 qui les
 * expose sur l'hôte). Distinct de la page « Logs erreurs » (qui liste les
 * ErrorLog enregistrés en base). Lecture seule.
 */
@Component({
  selector: 'app-admin-server-logs',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatButtonModule,
    MatProgressSpinnerModule, MatSnackBarModule, TranslateModule,
  ],
  templateUrl: './admin-server-logs.component.html',
  styleUrl: './admin-server-logs.component.scss',
})
export class AdminServerLogsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly apiUrl = '/api/admin/logs/';

  readonly files = signal<LogFile[]>([]);
  readonly logDir = signal<string>('');
  readonly selectedFile = signal<string | null>(null);
  readonly content = signal<LogContent | null>(null);
  readonly isLoading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  level = signal<string>('');
  lines = signal<number>(300);
  readonly levelOptions = ['', 'ERROR', 'WARNING', 'INFO'];

  ngOnInit(): void {
    this.loadFiles();
  }

  loadFiles(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.http.get<{ log_dir: string; files: LogFile[] }>(this.apiUrl).subscribe({
      next: (res) => {
        this.files.set(res.files);
        this.logDir.set(res.log_dir);
        this.isLoading.set(false);
        if (!this.selectedFile() && res.files.length) {
          const def = res.files.find(f => f.name === 'error.log') ?? res.files[0];
          this.selectFile(def.name);
        }
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('admin.serverLogs.loadError'));
        this.isLoading.set(false);
      },
    });
  }

  selectFile(name: string): void {
    this.selectedFile.set(name);
    this.loadContent();
  }

  loadContent(): void {
    const file = this.selectedFile();
    if (!file) return;
    this.isLoading.set(true);
    this.errorMessage.set(null);
    let params = `?file=${encodeURIComponent(file)}&lines=${this.lines()}`;
    if (this.level()) params += `&level=${encodeURIComponent(this.level())}`;
    this.http.get<LogContent>(`${this.apiUrl}${params}`).subscribe({
      next: (res) => {
        this.content.set(res);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('admin.serverLogs.loadError'));
        this.isLoading.set(false);
      },
    });
  }

  onLevelChange(value: string): void {
    this.level.set(value);
    this.loadContent();
  }

  onLinesChange(value: number): void {
    this.lines.set(Number(value) || 300);
    this.loadContent();
  }

  download(): void {
    const file = this.selectedFile();
    if (!file) return;
    this.http.get(`${this.apiUrl}?file=${encodeURIComponent(file)}&download=1`, { responseType: 'blob' })
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = file;
          a.click();
          URL.revokeObjectURL(url);
        },
        error: () => {
          this.snackBar.open(
            this.translate.instant('admin.serverLogs.downloadError'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
        },
      });
  }

  /** Classe CSS d'une ligne selon le niveau détecté (coloration). */
  lineClass(line: string): string {
    if (/\bERROR\b|\bCRITICAL\b/.test(line)) return 'log-line--error';
    if (/\bWARNING\b/.test(line)) return 'log-line--warning';
    return '';
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} o`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  }
}
