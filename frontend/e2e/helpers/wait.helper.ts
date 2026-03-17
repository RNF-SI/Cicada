/**
 * Utility to wait for services to be ready before running E2E tests.
 */

const MAX_RETRIES = 60;
const RETRY_INTERVAL_MS = 2000;

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
  await waitForUrl('http://localhost:8000/api/auth/health/', 'Backend (Django)');
}

export async function waitForFrontend(): Promise<void> {
  await waitForUrl('http://localhost:4200', 'Frontend (Angular)');
}
