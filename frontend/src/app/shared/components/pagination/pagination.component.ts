import { Component, input, output, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  styleUrl: './pagination.component.scss',
  template: `
    @if (totalItems() > 0) {
      <div class="pagination-bar">
        <span class="pagination-info">
          {{ startItem() }}-{{ endItem() }} sur {{ totalItems() }}
        </span>

        @if (totalPages() > 1) {
          <div class="pagination-controls">
            <button
              class="page-btn"
              [disabled]="currentPage() <= 1"
              (click)="goToPage(currentPage() - 1)"
            >
              <i class="fi fi-rr-angle-left"></i>
            </button>

            @for (p of visiblePages(); track p) {
              @if (p === -1) {
                <span class="page-ellipsis">...</span>
              } @else {
                <button
                  class="page-btn"
                  [class.active]="p === currentPage()"
                  (click)="goToPage(p)"
                >
                  {{ p }}
                </button>
              }
            }

            <button
              class="page-btn"
              [disabled]="currentPage() >= totalPages()"
              (click)="goToPage(currentPage() + 1)"
            >
              <i class="fi fi-rr-angle-right"></i>
            </button>
          </div>
        }
      </div>
    }
  `,
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
