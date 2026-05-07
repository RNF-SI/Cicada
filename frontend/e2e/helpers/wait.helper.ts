/**
 * Utility to wait for services to be ready before running E2E tests.
 *
 * URLs default to localhost (host-side execution) but can be overridden
 * via env vars to support container-side runs (where backend is reached
 * by service name, e.g. `http://web:8000/...`).
 */

const MAX_RETRIES = 60;
const RETRY_INTERVAL_MS = 2000;

const BACKEND_HEALTH_URL = process.env['E2E_BACKEND_URL'] || 'http://localhost:8000/api/auth/health/';
const FRONTEND_URL = process.env['E2E_FRONTEND_URL'] || 'http://localhost:4200';

export async function waitForUrl(url: string, label: string, maxRetries = MAX_RETRIES): Promise<void> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        console.log(`✓ ${label} is ready at ${url}`);
        return;
      }
    } catch {
      // Service not ready yet
    }
    if (i % 10 === 0 && i > 0) {
      console.log(`  Waiting for ${label}... (${i * RETRY_INTERVAL_MS / 1000}s)`);
    }
    await new Promise(resolve => setTimeout(resolve, RETRY_INTERVAL_MS));
  }
  throw new Error(`${label} not ready after ${maxRetries * RETRY_INTERVAL_MS / 1000}s at ${url}`);
}

export async function waitForBackend(): Promise<void> {
  await waitForUrl(BACKEND_HEALTH_URL, 'Backend (Django)');
}

export async function waitForFrontend(): Promise<void> {
  await waitForUrl(FRONTEND_URL, 'Frontend (Angular)');
}
