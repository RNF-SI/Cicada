import { Component, input, output, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  template: `
    @if (totalItems() > 0) {
      <div class="pagination-container">
        <div class="pagination-info">
          <span class="info-text">{{ startItem() }}-{{ endItem() }} sur {{ totalItems() }}</span>
        </div>

        @if (totalPages() > 1) {
          <nav class="pagination" [attr.aria-label]="'common.pagination.label' | translate">
            <button
              type="button"
              class="page-btn page-nav"
              [disabled]="currentPage() <= 1"
              [attr.aria-label]="'common.pagination.previous' | translate"
              [title]="'common.pagination.previous' | translate"
              (click)="goToPage(currentPage() - 1)"
            >
              <i class="fi fi-rr-angle-left"></i>
            </button>

            @for (p of visiblePages(); track $index) {
              @if (p === -1) {
                <span class="page-btn page-ellipsis" aria-hidden="true">…</span>
              } @else {
                <button
                  type="button"
                  class="page-btn"
                  [class.active]="p === currentPage()"
                  [attr.aria-current]="p === currentPage() ? 'page' : null"
                  (click)="goToPage(p)"
                >
                  {{ p }}
                </button>
              }
            }

            <button
              type="button"
              class="page-btn page-nav"
              [disabled]="currentPage() >= totalPages()"
              [attr.aria-label]="'common.pagination.next' | translate"
              [title]="'common.pagination.next' | translate"
              (click)="goToPage(currentPage() + 1)"
            >
              <i class="fi fi-rr-angle-right"></i>
            </button>
          </nav>
        }
      </div>
    }
  `,
  styleUrl: './pagination.component.scss',
})
export class PaginationComponent {
  totalItems = input.required<number>();
  pageSize = input<number>(20);
  currentPage = input<number>(1);

  pageChange = output<number>();

  totalPages = computed(() => Math.ceil(this.totalItems() / this.pageSize()));
  startItem = computed(() => (this.currentPage() - 1) * this.pageSize() + 1);
  endItem = computed(() => Math.min(this.currentPage() * this.pageSize(), this.totalItems()));

  visiblePages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) pages.push(i);
      return pages;
    }

    pages.push(1);
    if (current > 3) pages.push(-1); // ellipsis

    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);

    if (current < total - 2) pages.push(-1); // ellipsis
    pages.push(total);

    return pages;
  });

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages() && page !== this.currentPage()) {
      this.pageChange.emit(page);
    }
  }
}
