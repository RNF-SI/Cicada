import { Component } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';

/**
 * EuFundingNotice - Bloc marque UE + LIFE BIODIV'FRANCE et clause de non-responsabilité de l'UE
 *
 * Obligation contractuelle du projet LIFE BIODIV'FRANCE : tout outil de communication
 * doit porter le bloc marque officiel (non recomposé) et, dès qu'il diffuse du contenu,
 * la mention « Cofinancé par l'Union européenne… » dans un encart délimité, lisible.
 * Toute modification doit être validée par la coordination communication du LIFE.
 *
 * @example
 * <app-eu-funding-notice></app-eu-funding-notice>
 */
@Component({
  selector: 'app-eu-funding-notice',
  standalone: true,
  imports: [TranslateModule],
  templateUrl: './eu-funding-notice.component.html',
  styleUrl: './eu-funding-notice.component.scss'
})
export class EuFundingNoticeComponent {}
