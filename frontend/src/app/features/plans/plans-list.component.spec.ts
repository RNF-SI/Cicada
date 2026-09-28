/**
 * Tests du filtre par statut de la liste des plans (#635).
 *
 * Le point sensible : un plan est archivé PARCE QU'une version plus récente l'a
 * remplacé. Si les plans remplacés sont masqués inconditionnellement, cocher
 * « Terminé » n'affiche rien et la puce paraît morte — c'est le retour de recette
 * « rien ne se passe quand on clique sur les boutons ».
 */
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';
import { signal } from '@angular/core';
import { of } from 'rxjs';

import { PlansListComponent } from './plans-list.component';
import { AdminService } from '../../core/services/admin.service';
import { ValidationService } from '../../core/services/validation.service';
import { AuthService } from '../../core/services/auth.service';
import { PlanStatut } from '../../core/models/admin.model';

const CURRENT_USER = { id: 1, email: 'referent@test.fr' };

/** Plan minimal tel que le composant le manipule (PlanWithAccess). */
function plan(
  id: number,
  nom: string,
  statut: PlanStatut,
  extra: Partial<Record<string, unknown>> = {},
): any {
  return {
    id_pg: id,
    nom,
    statut,
    annee_debut: 2020,
    annee_fin: 2030,
    children_count: 0,
    plan_parent_id: null,
    referents: [{ id_role: CURRENT_USER.id }],
    membres: [],
    sites: [],
    accessStatus: 'granted',
    isReferent: true,
    isMember: false,
    hasAccessViaSite: false,
    isOrgPlan: false,
    gaugeStatus: 'in-progress',
    ...extra,
  };
}

describe('PlansListComponent — filtre par statut (#635)', () => {
  let component: PlansListComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        PlansListComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {
          provide: AdminService,
          useValue: {
            getPlans: () => of({ results: [] }),
            getSites: () => of({ results: [] }),
          },
        },
        { provide: ValidationService, useValue: { getMyRequests: () => of([]) } },
        {
          provide: AuthService,
          useValue: {
            currentUser: signal(CURRENT_USER),
            isSuperAdmin: signal(false),
            isRedacteurPrincipal: signal(false),
            isAdminOrganisme: signal(false),
          },
        },
      ],
    }).compileComponents();

    // Pas de detectChanges : ngOnInit (et son chargement HTTP) n'a rien à faire ici,
    // on alimente directement le signal source des plans.
    component = TestBed.createComponent(PlansListComponent).componentInstance;
  });

  /** v1 archivée, remplacée par v2 validée, plus un brouillon indépendant. */
  function seedChain(): void {
    component.allPlans.set([
      plan(1, 'Camargue v1', 'archive', { children_count: 1 }),
      plan(2, 'Camargue v2', 'valide', { plan_parent_id: 1 }),
      plan(3, 'Vercors brouillon', 'draft'),
    ] as any);
  }

  function displayed(): string[] {
    return component.myPlans().map(p => p.nom);
  }

  it('masque les plans terminés par défaut', () => {
    seedChain();
    expect(displayed()).toEqual(['Camargue v2', 'Vercors brouillon']);
  });

  it('affiche le plan terminé quand on coche « Terminé », même s\'il a été remplacé', () => {
    seedChain();
    component.toggleStatus('archive');
    expect(displayed()).toContain('Camargue v1');
  });

  it('retire un statut décoché de la liste', () => {
    seedChain();
    component.toggleStatus('draft');
    expect(displayed()).not.toContain('Vercors brouillon');
  });

  it('remet la pagination à la première page à chaque changement de filtre', () => {
    seedChain();
    component.currentPage.set(3);
    component.toggleStatus('archive');
    expect(component.currentPage()).toBe(1);
  });

  it('ne montre pas deux fois un plan déjà affiché en ligne de version sous son brouillon', () => {
    // v2 est un brouillon : son parent v1 est déjà rendu en ligne de version
    // sous lui (toggle « anciennes versions » éteint), il ne doit donc pas
    // apparaître en plus comme ligne principale.
    component.allPlans.set([
      plan(1, 'Camargue v1', 'archive', { children_count: 1 }),
      plan(2, 'Camargue v2', 'draft', { plan_parent_id: 1 }),
    ] as any);
    component.toggleStatus('archive');

    expect(displayed()).toEqual(['Camargue v2']);
    expect(component.linkedPlansById().get(2)?.map(p => p.nom)).toEqual(['Camargue v1']);
  });

  it('propose les quatre statuts du modèle', () => {
    expect(component.statusOptions).toEqual(['draft', 'valide', 'modifie', 'archive']);
  });
});

/**
 * #657 — Un gestionnaire (admin d'organisme, rédacteur principal, super admin)
 * a déjà accès aux plans de son périmètre : la section « Demander l'accès » n'a
 * aucun destinataire et ne doit pas lui être proposée.
 */
describe('PlansListComponent — pas de demande d\'accès pour un gestionnaire (#657)', () => {
  const roles = {
    isSuperAdmin: signal(false),
    isRedacteurPrincipal: signal(false),
    isAdminOrganisme: signal(false),
  };

  async function setup(): Promise<PlansListComponent> {
    roles.isSuperAdmin.set(false);
    roles.isRedacteurPrincipal.set(false);
    roles.isAdminOrganisme.set(false);

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        PlansListComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {
          provide: AdminService,
          useValue: { getPlans: () => of({ results: [] }), getSites: () => of({ results: [] }) },
        },
        { provide: ValidationService, useValue: { getMyRequests: () => of([]) } },
        {
          provide: AuthService,
          useValue: { currentUser: signal(CURRENT_USER), ...roles },
        },
      ],
    }).compileComponents();

    const component = TestBed.createComponent(PlansListComponent).componentInstance;
    component.allPlans.set([
      plan(10, 'Plan de mon organisme', 'valide', {
        isOrgPlan: true,
        accessStatus: 'none',
        referents: [],
      }),
    ] as any);
    return component;
  }

  it('propose la demande d\'accès à un utilisateur simple', async () => {
    const component = await setup();
    expect(component.hasOrgWidePlanAccess()).toBe(false);
    expect(component.otherPlans().map(p => p.nom)).toEqual(['Plan de mon organisme']);
  });

  it('ne propose rien à un admin d\'organisme', async () => {
    const component = await setup();
    roles.isAdminOrganisme.set(true);
    expect(component.hasOrgWidePlanAccess()).toBe(true);
    expect(component.otherPlans()).toEqual([]);
  });

  it('ne propose rien à un super admin ni à un rédacteur principal', async () => {
    const component = await setup();

    roles.isSuperAdmin.set(true);
    expect(component.otherPlans()).toEqual([]);

    roles.isSuperAdmin.set(false);
    roles.isRedacteurPrincipal.set(true);
    expect(component.otherPlans()).toEqual([]);
  });
});
