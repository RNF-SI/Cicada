import {
  LOG_LEVEL_TAG,
  NEUTRAL_TAG,
  PLAN_STATUS_TAG,
  USER_ROLE_TAG,
  USER_STATUS_TAG,
  VALIDATION_STATUS_TAG,
  getPlanStatusTag,
  getPrioriteTag,
  getUserRoleTag,
  getValidationStatusTag,
} from './tag-icons';

/**
 * Verrouille le contrat de la maquette Figma « 🧩 Tags » (node 4487:30877).
 * Deux règles y sont explicites et faciles à casser par inadvertance :
 *  - le texte des tags est toujours noir, donc les fonds sont pastel (côté SCSS) ;
 *  - une icône UNIQUEMENT sur les statuts principaux, sinon tag neutre sans icône.
 */
describe('tag-icons (contrat Figma)', () => {
  describe('statut de plan', () => {
    it('associe couleur et icône aux statuts principaux', () => {
      expect(PLAN_STATUS_TAG['draft']).toEqual({ variant: 'draft', icon: 'fi-rr-edit' });
      expect(PLAN_STATUS_TAG['valide']).toEqual({ variant: 'success', icon: 'fi-rr-check' });
      expect(PLAN_STATUS_TAG['archive']).toEqual({ variant: 'muted', icon: 'fi-rr-box' });
      expect(PLAN_STATUS_TAG['modifie'].variant).toBe('info');
      expect(PLAN_STATUS_TAG['modifie'].icon).toBeTruthy();
    });

    it('laisse les étapes CSRPN en tag neutre sans icône', () => {
      for (const statut of ['avis_csrpn', 'comite_consultatif', 'arrete_pref']) {
        expect(PLAN_STATUS_TAG[statut].variant).toBe('neutral');
        expect(PLAN_STATUS_TAG[statut].icon).toBeUndefined();
      }
    });

    it('retombe sur un tag neutre sans icône pour un statut inconnu', () => {
      expect(getPlanStatusTag('n-importe-quoi')).toEqual(NEUTRAL_TAG);
      expect(getPlanStatusTag(null)).toEqual(NEUTRAL_TAG);
      expect(getPlanStatusTag(undefined)).toEqual(NEUTRAL_TAG);
    });
  });

  describe('priorité d\'action (#566)', () => {
    it('mappe les priorités 1/2/3 sur la palette scores (rouge/orange/jaune), sans icône', () => {
      expect(getPrioriteTag('Priorité 1')).toEqual({ variant: 'score-very-bad' });
      expect(getPrioriteTag('Priorité 2')).toEqual({ variant: 'score-bad' });
      expect(getPrioriteTag('Priorité 3')).toEqual({ variant: 'score-neutral' });
    });

    it('renvoie null quand aucune priorité n\'est renseignée', () => {
      expect(getPrioriteTag(null)).toBeNull();
      expect(getPrioriteTag(undefined)).toBeNull();
      expect(getPrioriteTag('')).toBeNull();
    });

    it('retombe sur un tag neutre pour un libellé de priorité non reconnu', () => {
      expect(getPrioriteTag('Priorité haute')).toEqual(NEUTRAL_TAG);
    });
  });

  describe('statut de demande de validation', () => {
    it('approuvé en vert, refus/annulation/expiration en rouge, attente en orange', () => {
      expect(VALIDATION_STATUS_TAG['approved']).toEqual({ variant: 'success', icon: 'fi-rr-check' });
      for (const statut of ['rejected', 'cancelled', 'expired']) {
        expect(VALIDATION_STATUS_TAG[statut]).toEqual({ variant: 'error', icon: 'fi-rr-cross' });
      }
      expect(VALIDATION_STATUS_TAG['pending']).toEqual({ variant: 'warning', icon: 'fi-rr-edit' });
    });

    it('retombe sur un tag neutre pour un statut inconnu', () => {
      expect(getValidationStatusTag('inconnu')).toEqual(NEUTRAL_TAG);
    });
  });

  describe('rôle et statut utilisateur', () => {
    it('distingue les rôles administrateurs des autres', () => {
      expect(USER_ROLE_TAG['super_admin'].variant).toBe('error');
      expect(USER_ROLE_TAG['admin_og'].variant).toBe('error');
      expect(USER_ROLE_TAG['referent']).toEqual({ variant: 'warning', icon: 'fi-rr-star' });
      expect(USER_ROLE_TAG['user']).toEqual({ variant: 'info', icon: 'fi-rr-user' });
    });

    it('laisse « anonymisé » en tag neutre sans icône', () => {
      expect(USER_STATUS_TAG['anonymized'].variant).toBe('neutral');
      expect(USER_STATUS_TAG['anonymized'].icon).toBeUndefined();
    });

    // La maquette ne connaît qu'un seul tag « Utilisateur » : les libellés
    // d'accès équivalents renvoyés par l'API doivent tous y aboutir, sinon un
    // même membre s'affiche différemment d'un écran à l'autre.
    it('aliase « utilisateur » et « membre » sur le tag Utilisateur', () => {
      const user = USER_ROLE_TAG['user'];
      expect(getUserRoleTag('user')).toEqual(user);
      expect(getUserRoleTag('utilisateur')).toEqual(user);
      expect(getUserRoleTag('membre')).toEqual(user);
    });

    it('donne la priorité au référent sur le rôle de base', () => {
      expect(getUserRoleTag('utilisateur', true)).toEqual(USER_ROLE_TAG['referent']);
      expect(getUserRoleTag('membre', true)).toEqual(USER_ROLE_TAG['referent']);
      // Un admin reste un admin même s'il est référent d'un site
      expect(getUserRoleTag('admin_og', true)).toEqual(USER_ROLE_TAG['admin_og']);
    });

    it('laisse en neutre les niveaux d\'accès qui ne sont pas un rôle', () => {
      for (const level of ['conservateur', 'organisme', 'plan', '']) {
        expect(getUserRoleTag(level)).toEqual(NEUTRAL_TAG);
      }
      expect(getUserRoleTag(null)).toEqual(NEUTRAL_TAG);
    });
  });

  describe('niveau de log', () => {
    it('mappe critique / erreur / avertissement', () => {
      expect(LOG_LEVEL_TAG['critical']).toEqual({ variant: 'neutral', icon: 'fi-rr-megaphone' });
      expect(LOG_LEVEL_TAG['error']).toEqual({ variant: 'error', icon: 'fi-rr-cross' });
      expect(LOG_LEVEL_TAG['warning']).toEqual({
        variant: 'warning',
        icon: 'fi-rr-shield-exclamation',
      });
    });
  });

  describe('règle transverse « pas d\'icône hors statuts principaux »', () => {
    it('n\'utilise que des variantes de la palette pastel', () => {
      const allowed = [
        'success', 'error', 'info', 'primary', 'warning', 'draft', 'neutral', 'muted',
        'score-very-bad', 'score-bad', 'score-neutral', 'score-good', 'score-very-good',
      ];
      const all = [
        ...Object.values(PLAN_STATUS_TAG),
        ...Object.values(VALIDATION_STATUS_TAG),
        ...Object.values(USER_ROLE_TAG),
        ...Object.values(USER_STATUS_TAG),
        ...Object.values(LOG_LEVEL_TAG),
      ];
      for (const tag of all) {
        expect(allowed).toContain(tag.variant);
      }
    });

    it('n\'utilise que des classes Flaticon `fi-rr-*`', () => {
      const all = [
        ...Object.values(PLAN_STATUS_TAG),
        ...Object.values(VALIDATION_STATUS_TAG),
        ...Object.values(USER_ROLE_TAG),
        ...Object.values(USER_STATUS_TAG),
        ...Object.values(LOG_LEVEL_TAG),
      ];
      for (const tag of all) {
        if (tag.icon) {
          expect(tag.icon).toMatch(/^fi-rr-[a-z0-9-]+$/);
        }
      }
    });
  });
});
