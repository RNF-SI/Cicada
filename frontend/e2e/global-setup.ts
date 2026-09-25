import { execSync } from 'child_process';
import { waitForBackend, waitForFrontend } from './helpers/wait.helper';

/**
 * Global setup for E2E tests.
 * Waits for backend/frontend to be ready and seeds test data.
 */
async function globalSetup(): Promise<void> {
  console.log('\n🚀 E2E Global Setup\n');

  // Fédération (#636) : le banc à trois briques est déjà debout et **déjà
  // publié** sur le hub. Reseeder ici réinitialiserait les bases des instances
  // et rendrait l'index du hub obsolète sans le dire — les tests chercheraient
  // alors des plans qui n'existent plus, en accusant la fédération.
  if (process.env['E2E_FEDERATION'] === '1') {
    console.log('🌐 Mode fédération : banc supposé lancé, aucun seeding.');
    console.log('   (scripts/federation.sh up && scripts/federation.sh push)\n');
    return;
  }

  // 1. Wait for backend
  await waitForBackend();

  // 2. Wait for frontend
  await waitForFrontend();

  // 3. Seed test data (unless explicitly disabled)
  if (process.env['E2E_SEED_DATA'] !== 'false') {
    console.log('🌱 Seeding test data...');
    try {
      execSync('docker compose exec -T web python manage.py seed_testdata --reset', {
        cwd: process.cwd().replace(/\/frontend(\/e2e)?$/, ''),
        stdio: 'pipe',
      });
      execSync('docker compose exec -T web python manage.py seed_testdata', {
        cwd: process.cwd().replace(/\/frontend(\/e2e)?$/, ''),
        stdio: 'pipe',
      });
      console.log('✓ Test data seeded');
    } catch (error) {
      console.warn('⚠ Failed to seed test data (may already exist):', (error as Error).message);
    }
  } else {
    console.log('⏭ Skipping data seeding (E2E_SEED_DATA=false)');
  }

  console.log('\n✅ Global setup complete\n');
}

export default globalSetup;
