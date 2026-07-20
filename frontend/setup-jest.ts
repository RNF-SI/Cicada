import { setupZoneTestEnv } from 'jest-preset-angular/setup-env/zone';

setupZoneTestEnv();

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => Object.keys(store)[index] || null
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Reset localStorage before each test
beforeEach(() => {
  localStorage.clear();
});

/**
 * Filtre le bruit « Could not parse CSS stylesheet » de jsdom (#592).
 *
 * jsdom ne sait pas analyser la règle `@layer` utilisée par la feuille structurelle du CDK
 * Overlay : chaque ouverture de dropdown dans un test produit une longue trace, sans qu'aucune
 * assertion ne soit affectée. On ne masque que ce cas précis, les autres `console.error`
 * restent visibles.
 */
const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  const first = args[0];
  if (first instanceof Error && first.message.includes('Could not parse CSS stylesheet')) {
    return;
  }
  originalConsoleError(...args);
};
