/**
 * Shared API helpers for plan/enjeux E2E tests.
 *
 * These helpers extract the JWT access token from the page's localStorage
 * and include it in API calls to the Django backend.
 *
 * IMPORTANT: The page must have navigated to a page on the Angular app
 * before calling any of these functions, so that localStorage is populated
 * with auth tokens (set during login via the auth fixture's storageState).
 */
import { type Page } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api';

/**
 * Extract the JWT access token from the page's localStorage.
 * The Angular app stores tokens as JSON under the key 'auth_tokens'.
 */
async function getAuthToken(page: Page): Promise<string> {
  // Ensure the page is on the app origin so localStorage is accessible.
  // If we're still on about:blank, navigate to the app root first.
  const currentUrl = page.url();
  if (currentUrl === 'about:blank' || !currentUrl.startsWith('http://localhost')) {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
  }
  const tokensStr = await page.evaluate(() => localStorage.getItem('auth_tokens'));
  if (!tokensStr) throw new Error('No auth tokens in localStorage — make sure auth setup has run');
  const tokens = JSON.parse(tokensStr);
  return tokens.access;
}

// ── Generic API helpers ─────────────────────────────────────────

/**
 * Perform an authenticated GET request.
 * @param page - Playwright Page (must have localStorage with auth tokens)
 * @param path - API path WITHOUT '/api/' prefix (e.g. 'plans/plans/')
 * @param params - Optional query parameters
 */
export async function apiGet(
  page: Page,
  path: string,
  params?: Record<string, string>,
): Promise<{ ok: boolean; status: number; data: any }> {
  const token = await getAuthToken(page);
  const url = new URL(`${API_BASE}/${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, value);
    }
  }
  const response = await page.request.get(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });
  const status = response.status();
  let data: any;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  return { ok: response.ok(), status, data };
}

/**
 * Perform an authenticated POST request.
 * @param page - Playwright Page
 * @param path - API path WITHOUT '/api/' prefix
 * @param body - Request body
 */
export async function apiPost(
  page: Page,
  path: string,
  body?: Record<string, unknown>,
): Promise<{ ok: boolean; status: number; data: any }> {
  const token = await getAuthToken(page);
  const response = await page.request.post(`${API_BASE}/${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    data: body,
  });
  const status = response.status();
  let data: any;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  return { ok: response.ok(), status, data };
}

/**
 * Perform an authenticated PATCH request.
 * @param page - Playwright Page
 * @param path - API path WITHOUT '/api/' prefix
 * @param body - Request body
 */
export async function apiPatch(
  page: Page,
  path: string,
  body?: Record<string, unknown>,
): Promise<{ ok: boolean; status: number; data: any }> {
  const token = await getAuthToken(page);
  const response = await page.request.patch(`${API_BASE}/${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    data: body,
  });
  const status = response.status();
  let data: any;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  return { ok: response.ok(), status, data };
}

/**
 * Perform an authenticated DELETE request.
 * @param page - Playwright Page
 * @param path - API path WITHOUT '/api/' prefix
 */
export async function apiDelete(
  page: Page,
  path: string,
): Promise<{ ok: boolean; status: number; data: any }> {
  const token = await getAuthToken(page);
  const response = await page.request.delete(`${API_BASE}/${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const status = response.status();
  let data: any;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  return { ok: response.ok(), status, data };
}

// ── Domain-specific helpers ─────────────────────────────────────

/**
 * Find a plan by name fragment. Selection priority:
 * 1. Valide plan whose name contains the fragment
 * 2. Valide plan with referents (has active members, more likely to have data)
 * 3. Valide plan (from search results — may match sites/description)
 * 4. Non-archive plan whose name contains the fragment
 * 5. First search result
 *
 * Archive plans are deprioritized because they often lack enjeux data.
 * Plans without referents are deprioritized because they're often access-test plans.
 */
export async function findPlan(page: Page, nameFragment: string) {
  const { data } = await apiGet(page, 'plans/plans/', { search: nameFragment });
  const results: any[] = data.results || data;
  if (!Array.isArray(results) || results.length === 0) {
    throw new Error(`Plan "${nameFragment}" not found`);
  }
  const nameMatch = (p: any) => p.nom?.toLowerCase().includes(nameFragment.toLowerCase());
  const notArchive = (p: any) => p.statut !== 'archive';
  const hasReferents = (p: any) => (p.referents?.length > 0) || (p.nb_referents > 0);
  // Priority 1: valide + name match
  const best = results.find((p: any) => p.statut === 'valide' && nameMatch(p))
    // Priority 2: valide + has referents (active plan with members)
    || results.find((p: any) => p.statut === 'valide' && hasReferents(p))
    // Priority 3: valide (returned by search, may match via sites)
    || results.find((p: any) => p.statut === 'valide')
    // Priority 4: non-archive + name match (draft is acceptable)
    || results.find((p: any) => notArchive(p) && nameMatch(p))
    // Priority 5: first result
    || results[0];
  return { id_pg: best.id_pg as number, slug: best.slug as string };
}

/** Find the first enjeu for a plan. Prefers seeded enjeux (non-E2E) that have data. */
export async function findFirstEnjeu(page: Page, planId: number) {
  const { data } = await apiGet(page, `plans/enjeux/by-plan/${planId}/`);
  const enjeux = data.enjeux || [];
  if (enjeux.length === 0) throw new Error(`No enjeux for plan ${planId}`);
  // Prefer enjeux with etats_actuels (seeded data) over E2E-created ones
  const withData = enjeux.find((e: any) =>
    (e.etats_actuels?.length > 0 || e.facteurs_influence?.length > 0) && !e.libelle?.startsWith('E2E')
  );
  const picked = withData || enjeux.find((e: any) => !e.libelle?.startsWith('E2E')) || enjeux[0];
  return { id_enjeu: picked.id_enjeu as number, slug: (picked.slug || picked.id_enjeu) as string };
}

/** Find the first enjeu ID for a plan (convenience). */
export async function findFirstEnjeuId(page: Page, planId: number): Promise<number> {
  const enjeu = await findFirstEnjeu(page, planId);
  return enjeu.id_enjeu;
}

/** Find the first operation for a plan (flattens grouped response). */
export async function findFirstOperation(page: Page, planId: number) {
  const { data } = await apiGet(page, `plans/operations/by-plan/${planId}/`);
  const allOps: any[] = [];
  // Response structure: { groups: [{ type_action, operations: [...], count }] }
  const groups = data.groups || [];
  for (const group of groups) {
    if (Array.isArray(group.operations)) allOps.push(...group.operations);
  }
  // Fallback: try flat array values
  if (allOps.length === 0) {
    for (const val of Object.values(data) as any[]) {
      if (Array.isArray(val)) {
        for (const item of val) {
          if (item.id_operation) allOps.push(item);
          else if (Array.isArray(item.operations)) allOps.push(...item.operations);
        }
      }
    }
  }
  if (allOps.length === 0) throw new Error(`No operations found for plan ${planId}`);
  return allOps[0];
}

/** Find the first metrique for a plan by walking the enjeux hierarchy. */
export async function findFirstMetrique(page: Page, planId: number) {
  const { data } = await apiGet(page, `plans/enjeux/by-plan/${planId}/`);
  const allEnjeux = [...(data.enjeux || []), ...(data.fcr || [])];
  for (const enjeu of allEnjeux) {
    for (const ea of enjeu.etats_actuels || []) {
      for (const olt of ea.objectifs_long_terme || []) {
        for (const ne of olt.niveaux_exigence || []) {
          for (const ind of ne.indicateurs || []) {
            for (const met of ind.metriques || []) {
              return { id_metrique: met.id_metrique as number, nom: met.nom_metrique as string };
            }
          }
        }
      }
    }
  }
  throw new Error(`No metriques found for plan ${planId}`);
}

/** Get the id_categorie for creating enjeux (fetches from an existing enjeu). */
export async function getEnjeuCategorieId(page: Page): Promise<number> {
  const { ok, data } = await apiGet(page, 'plans/enjeux/', { page_size: '1' });
  if (ok && data.results?.length > 0) {
    return data.results[0].id_categorie;
  }
  // Fallback: try nomenclature API
  const { data: nomData } = await apiGet(page, 'nomenclatures/', { type: 'CATEGORIE_ENJEU' });
  const noms = nomData?.results || nomData || [];
  if (noms.length > 0) return noms[0].id_nomenclature;
  throw new Error('Cannot find id_categorie for enjeu creation');
}

/** Find the first FCR (Facteur Clef de Reussite) for a plan. */
export async function findFirstFcr(page: Page, planId: number) {
  const { data } = await apiGet(page, `plans/enjeux/by-plan/${planId}/`);
  const fcrs = data.fcr || [];
  if (fcrs.length === 0) throw new Error(`No FCR for plan ${planId}`);
  return fcrs[0];
}
