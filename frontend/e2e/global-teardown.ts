/**
 * Global teardown for E2E tests.
 * Minimal cleanup — test data stays for debugging.
 */
async function globalTeardown(): Promise<void> {
  console.log('\n🧹 E2E Global Teardown (no-op)\n');
}

export default globalTeardown;
