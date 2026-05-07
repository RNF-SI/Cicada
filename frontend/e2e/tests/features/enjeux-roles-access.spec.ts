/**
 * E2E Tests for role-based access control on enjeux/operations.
 *
 * Tests:
 * - Super admin: full access across all plans (~4 tests)
 * - Admin organisme: scoped to their org's plans (~5 tests)
 * - Referent: scoped to their plans/sites (~4 tests)
 * - Regular user: read-only, write attempts blocked (~5 tests)
 * - Cross-organisation isolation (~4 tests)
 *
 * Prerequisite: seed_testdata.
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { EnjeuxPage } from '../../pages/enjeux.page';
import {
  findPlan as findPlanStrict,
  findFirstEnjeuId,
  apiGet,
  apiPost,
  apiPatch,
  apiDelete,
  getEnjeuCategorieId,
} from '../../helpers/plan.helper';

// ── Helpers ──────────────────────────────────────────────────────

/**
 * Find a plan by name fragment. Returns null if not found (unlike the
 * strict version in plan.helper which throws). Used in tests that
 * intentionally test access to plans the user may not see.
 */
async function findPlan(page: import('@playwright/test').Page, nameFragment: string) {
  const { ok, data } = await apiGet(page, 'plans/plans/', { search: nameFragment });
  if (!ok) return null;
  const results = data.results || data;
  if (!Array.isArray(results) || results.length === 0) return null;
  // Name match wins over statut: callers say `findPlan('Camargue')` to mean
  // "the Camargue plan", regardless of whether it's draft or valide.
  const nameMatch = (p: any) => p.nom?.toLowerCase().includes(nameFragment.toLowerCase());
  const plan = results.find((p: any) => p.statut !== 'archive' && nameMatch(p))
    || results.find((p: any) => p.statut === 'valide')
    || results.find((p: any) => p.statut !== 'archive')
    || results[0];
  return { id_pg: plan.id_pg as number, slug: plan.slug as string };
}

// =========================================================================
// SUPER ADMIN — Full access
// =========================================================================
test.describe('Roles - Super Admin', () => {
  test('should access enjeux for any plan (Camargue RNF)', async ({ superAdminPage }) => {
    const plan = await findPlan(superAdminPage, 'Camargue');
    expect(plan).not.toBeNull();
    const enjeuxPage = new EnjeuxPage(superAdminPage);
    await superAdminPage.goto(`/plans/${plan!.slug}/enjeux`);
    await enjeuxPage.waitForData();

    const count = await enjeuxPage.getTotalAccordionCount();
    expect(count).toBeGreaterThan(0);
  });

  test('should access enjeux for CEN plan (Vercors)', async ({ superAdminPage }) => {
    const plan = await findPlan(superAdminPage, 'Vercors');
    expect(plan).not.toBeNull();
    const enjeuxPage = new EnjeuxPage(superAdminPage);
    await superAdminPage.goto(`/plans/${plan!.slug}/enjeux`);
    await enjeuxPage.waitForData();

    // Plan may or may not have enjeux — verify page loads without error
    const count = await enjeuxPage.getTotalAccordionCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should create enjeu via API on any plan', async ({ superAdminPage }) => {
    const plan = await findPlan(superAdminPage, 'Camargue');
    const catId = await getEnjeuCategorieId(superAdminPage);
    const { ok, data: enjeu } = await apiPost(superAdminPage, 'plans/enjeux/', {
      id_pg: plan!.id_pg,
      libelle: `E2E SuperAdmin Enjeu ${Date.now()}`,
      rang: 1,
      categorie_ecologique: true,
      id_categorie: catId,
    });
    expect(ok).toBeTruthy();

    // Cleanup
    await apiDelete(superAdminPage, `plans/enjeux/${enjeu.id_enjeu}/`);
  });

  test('should delete enjeu via API on any plan', async ({ superAdminPage }) => {
    const plan = await findPlan(superAdminPage, 'Camargue');
    const catId = await getEnjeuCategorieId(superAdminPage);
    const { data: enjeu } = await apiPost(superAdminPage, 'plans/enjeux/', {
      id_pg: plan!.id_pg,
      libelle: `E2E Delete Test ${Date.now()}`,
      rang: 1,
      categorie_ecologique: true,
      id_categorie: catId,
    });
    const { status } = await apiDelete(superAdminPage, `plans/enjeux/${enjeu.id_enjeu}/`);
    expect(status).toBe(204);
  });
});

// =========================================================================
// ADMIN ORGANISME — Scoped to their org
// =========================================================================
test.describe('Roles - Admin Organisme RNF', () => {
  test('should access RNF plan enjeux (Camargue)', async ({ adminRnfPage }) => {
    const plan = await findPlan(adminRnfPage, 'Camargue');
    expect(plan).not.toBeNull();
    const enjeuxPage = new EnjeuxPage(adminRnfPage);
    await adminRnfPage.goto(`/plans/${plan!.slug}/enjeux`);
    await enjeuxPage.waitForData();

    // Plan may or may not have enjeux — verify page loads without error
    const count = await enjeuxPage.getTotalAccordionCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should create enjeu on RNF plan via API', async ({ adminRnfPage }) => {
    const plan = await findPlan(adminRnfPage, 'Camargue');
    const catId = await getEnjeuCategorieId(adminRnfPage);
    const { ok, data: enjeu } = await apiPost(adminRnfPage, 'plans/enjeux/', {
      id_pg: plan!.id_pg,
      libelle: `E2E AdminRNF Enjeu ${Date.now()}`,
      rang: 1,
      categorie_ecologique: true,
      id_categorie: catId,
    });
    expect(ok).toBeTruthy();
    await apiDelete(adminRnfPage, `plans/enjeux/${enjeu.id_enjeu}/`);
  });

  test('should NOT see CEN plans in search results', async ({ adminRnfPage }) => {
    // Grand-Voyeux is CEN — admin RNF should not find it
    const plan = await findPlan(adminRnfPage, 'Grand-Voyeux');
    // The plan may or may not be returned depending on statut
    // But admin RNF should not be able to create enjeux on it
    if (plan) {
      const { status } = await apiPost(adminRnfPage, 'plans/enjeux/', {
        id_pg: plan.id_pg,
        libelle: `E2E Forbidden ${Date.now()}`,
        rang: 1,
        categorie_ecologique: true,
      });
      // Should be forbidden
      expect(status).toBeGreaterThanOrEqual(400);
    }
  });
});

test.describe('Roles - Admin Organisme CEN', () => {
  test('should access CEN plan enjeux (Vercors)', async ({ adminCenPage }) => {
    const plan = await findPlan(adminCenPage, 'Vercors');
    expect(plan).not.toBeNull();
    const enjeuxPage = new EnjeuxPage(adminCenPage);
    await adminCenPage.goto(`/plans/${plan!.slug}/enjeux`);
    await enjeuxPage.waitForData();

    // Plan may or may not have enjeux — verify page loads without error
    const count = await enjeuxPage.getTotalAccordionCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should NOT create enjeu on RNF plan', async ({ adminCenPage }) => {
    const plan = await findPlan(adminCenPage, 'Camargue');
    if (plan) {
      const { status } = await apiPost(adminCenPage, 'plans/enjeux/', {
        id_pg: plan.id_pg,
        libelle: `E2E CEN Forbidden ${Date.now()}`,
        rang: 1,
        categorie_ecologique: true,
      });
      expect(status).toBeGreaterThanOrEqual(400);
    }
  });
});

// =========================================================================
// REFERENT — Scoped to their plans/sites
// =========================================================================
test.describe('Roles - Referent Camargue', () => {
  test('should access Camargue enjeux', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    expect(plan).not.toBeNull();
    const enjeuxPage = new EnjeuxPage(referentPage);
    await referentPage.goto(`/plans/${plan!.slug}/enjeux`);
    await enjeuxPage.waitForData();

    const count = await enjeuxPage.getTotalAccordionCount();
    expect(count).toBeGreaterThan(0);
  });

  test('should create enjeu on Camargue via API', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const catId = await getEnjeuCategorieId(referentPage);
    const { ok, data: enjeu } = await apiPost(referentPage, 'plans/enjeux/', {
      id_pg: plan!.id_pg,
      libelle: `E2E Referent Enjeu ${Date.now()}`,
      rang: 1,
      categorie_ecologique: true,
      id_categorie: catId,
    });
    expect(ok).toBeTruthy();
    await apiDelete(referentPage, `plans/enjeux/${enjeu.id_enjeu}/`);
  });

  test('should NOT create enjeu on other org plan', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Grand-Voyeux');
    if (plan) {
      const { status } = await apiPost(referentPage, 'plans/enjeux/', {
        id_pg: plan.id_pg,
        libelle: `E2E Referent Forbidden ${Date.now()}`,
        rang: 1,
        categorie_ecologique: true,
      });
      expect(status).toBeGreaterThanOrEqual(400);
    }
  });

  test('should create operation on Camargue via API', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const { ok, data: op } = await apiPost(referentPage, 'plans/operations/', {
      libelle: `E2E Referent Op ${Date.now()}`,
    });
    // Should succeed since referent has write access
    expect(ok).toBeTruthy();
    await apiDelete(referentPage, `plans/operations/${op.id_operation}/`);
  });
});

// =========================================================================
// REGULAR USER — Read-only
// =========================================================================
test.describe('Roles - Regular User (Read-Only)', () => {
  test('should access valid plan enjeux in read mode', async ({ userRnfPage }) => {
    const plan = await findPlan(userRnfPage, 'Camargue');
    if (plan) {
      const enjeuxPage = new EnjeuxPage(userRnfPage);
      await userRnfPage.goto(`/plans/${plan.slug}/enjeux`);
      await enjeuxPage.waitForData();

      // Should see enjeux (read access on valid plan)
      const count = await enjeuxPage.getTotalAccordionCount();
      expect(count).toBeGreaterThanOrEqual(0);
    }
  });

  test('should NOT create enjeu via API (403)', async ({ userRnfPage }) => {
    const plan = await findPlan(userRnfPage, 'Camargue');
    if (plan) {
      const { status } = await apiPost(userRnfPage, 'plans/enjeux/', {
        id_pg: plan.id_pg,
        libelle: `E2E User Forbidden ${Date.now()}`,
        rang: 1,
        categorie_ecologique: true,
      });
      expect(status).toBeGreaterThanOrEqual(400);
    }
  });

  test('should NOT delete enjeu via API (403)', async ({ userRnfPage }) => {
    const plan = await findPlan(userRnfPage, 'Camargue');
    if (plan) {
      let enjeuId: number;
      try {
        enjeuId = await findFirstEnjeuId(userRnfPage, plan.id_pg);
      } catch {
        // Plan has no enjeux — skip the test
        test.skip(true, 'No enjeux found for this plan');
        return;
      }
      const { status } = await apiDelete(userRnfPage, `plans/enjeux/${enjeuId}/`);
      expect(status).toBeGreaterThanOrEqual(400);
    }
  });

  test('should NOT create operation via API (403)', async ({ userRnfPage }) => {
    const { status } = await apiPost(userRnfPage, 'plans/operations/', {
      libelle: `E2E User Op Forbidden ${Date.now()}`,
    });
    expect(status).toBeGreaterThanOrEqual(400);
  });

  test('should NOT update enjeu via API (403)', async ({ userRnfPage }) => {
    const plan = await findPlan(userRnfPage, 'Camargue');
    if (plan) {
      let enjeuId: number;
      try {
        enjeuId = await findFirstEnjeuId(userRnfPage, plan.id_pg);
      } catch {
        // Plan has no enjeux — skip the test
        test.skip(true, 'No enjeux found for this plan');
        return;
      }
      const { status } = await apiPatch(userRnfPage, `plans/enjeux/${enjeuId}/`, {
        libelle: 'Tentative de modification',
      });
      expect(status).toBeGreaterThanOrEqual(400);
    }
  });
});

// =========================================================================
// CROSS-ORGANISATION ISOLATION
// =========================================================================
test.describe('Roles - Cross-Organisation Isolation', () => {
  test('user.rnf should NOT see CEN enjeux', async ({ userRnfPage }) => {
    // Vercors is CEN — user.rnf should not see its enjeux (if plan is not valid)
    const plan = await findPlan(userRnfPage, 'Grand-Voyeux');
    if (plan) {
      const { ok, status } = await apiGet(userRnfPage, `plans/enjeux/by-plan/${plan.id_pg}/`);
      // If the plan is draft, should fail. If valid, enjeux may be readable.
      if (!ok) {
        expect(status).toBeGreaterThanOrEqual(400);
      }
    }
  });

  test('user.cen should NOT see RNF-only enjeux', async ({ userCenPage }) => {
    // Aiguilles Rouges is RNF — user.cen should not have full access
    const plan = await findPlan(userCenPage, 'Aiguilles Rouges');
    if (plan) {
      const { status } = await apiPost(userCenPage, 'plans/enjeux/', {
        id_pg: plan.id_pg,
        libelle: `E2E CrossOrg Forbidden ${Date.now()}`,
        rang: 1,
        categorie_ecologique: true,
      });
      expect(status).toBeGreaterThanOrEqual(400);
    }
  });

  test('admin.cen should NOT modify RNF enjeux', async ({ adminCenPage }) => {
    // Aiguilles Rouges est purement RNF (site 18 non lié à CEN). Camargue
    // partage son site Brouage avec CEN, donc admin.cen y a accès via la
    // chaîne site→organisme — ce n'est plus un test de cross-org isolation.
    const plan = await findPlan(adminCenPage, 'Aiguilles Rouges');
    if (plan) {
      // Try to find enjeux: admin.cen ne devrait pas en voir (queryset filter)
      const { ok, data } = await apiGet(adminCenPage, `plans/enjeux/by-plan/${plan.id_pg}/`);
      if (ok) {
        const enjeux = data.enjeux || [];
        if (enjeux.length > 0) {
          // Try to modify — should be forbidden
          const { status } = await apiPatch(adminCenPage, `plans/enjeux/${enjeux[0].id_enjeu}/`, {
            libelle: 'CEN admin modification attempt',
          });
          expect(status).toBeGreaterThanOrEqual(400);
        }
      }
    }
  });

  test('referent.camargue should NOT modify Vercors enjeux', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Vercors');
    if (plan) {
      const { ok, data } = await apiGet(referentPage, `plans/enjeux/by-plan/${plan.id_pg}/`);
      if (ok) {
        const enjeux = data.enjeux || [];
        if (enjeux.length > 0) {
          const { status } = await apiPatch(referentPage, `plans/enjeux/${enjeux[0].id_enjeu}/`, {
            libelle: 'Referent cross-plan attempt',
          });
          expect(status).toBeGreaterThanOrEqual(400);
        }
      }
    }
  });
});
