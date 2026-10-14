import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';

/**
 * Référence d'un plan distant dans une URL de page (#683, #636).
 *
 * Un plan de cette instance a un slug (« camargue ») ; un plan reçu d'une
 * autre instance par le hub est désigné par « instance:slug » (« rnf:camargue »).
 * Les deux vivent sous les mêmes routes `/plans/<ref>/…` : c'est ce qui
 * permet aux écrans réels — et à tous leurs liens, construits sur le slug —
 * de servir sans rien savoir de la provenance.
 */
const PLAN_DISTANT = /^\/plans\/([^/?#:]+:[^/?#]+)(?:[/?#]|$)/;

/** Référence du plan distant de la page courante, ou `null`. */
export function referenceDistante(url: string): string | null {
  const correspondance = PLAN_DISTANT.exec(url);
  return correspondance ? decodeURIComponent(correspondance[1]) : null;
}

/**
 * Redirige les appels de l'API des plans vers l'instantané d'un plan distant.
 *
 * Sur `/plans/rnf:camargue/…`, les écrans réels appellent `/api/plans/…`
 * comme d'habitude ; or ce plan n'est pas dans cette base. L'intercepteur
 * réécrit ces appels en `/api/exploration/distant/rnf:camargue/…`, où le
 * backend ressert les réponses publiées par l'instance d'origine (déjà
 * élaguées des données sensibles). Les écrans, eux, ne changent pas.
 *
 * Les autres API (`/api/validations`, `/api/notifications`…) ne sont pas
 * touchées : elles concernent l'utilisateur, pas le plan.
 */
export const planDistantInterceptor: HttpInterceptorFn = (req, next) => {
  const prefixe = '/api/plans/';
  const position = req.url.indexOf(prefixe);
  if (position === -1) {
    return next(req);
  }
  const reference = referenceDistante(inject(Router).url);
  if (!reference) {
    return next(req);
  }
  const reste = req.url.slice(position + prefixe.length);
  const url =
    req.url.slice(0, position) +
    `/api/exploration/distant/${encodeURIComponent(reference)}/` +
    reste;
  return next(req.clone({ url }));
};
