import { Pipe, PipeTransform } from '@angular/core';

/**
 * Interface for objects that have site type information.
 */
interface SiteTypeInfo {
  type_site_label?: string | null;
  type_site_precision?: string | null;
}

/**
 * Pipe to display site type with precision when the type is "Autre".
 *
 * Usage:
 *   {{ site | siteTypeDisplay }}
 *
 * Examples:
 *   - Site with type "RNN" -> "RNN"
 *   - Site with type "Autre" and precision "Zone humide" -> "Autre (Zone humide)"
 *   - Site with type "Autre" and no precision -> "Autre"
 *   - Site with no type -> "-"
 */
@Pipe({
  name: 'siteTypeDisplay',
  standalone: true
})
export class SiteTypeDisplayPipe implements PipeTransform {
  transform(site: SiteTypeInfo | null | undefined): string {
    if (!site || !site.type_site_label) {
      return '-';
    }

    // If the type is "Autre" and there's a precision, show both
    if (site.type_site_label === 'Autre' && site.type_site_precision) {
      return `Autre (${site.type_site_precision})`;
    }

    return site.type_site_label;
  }
}
