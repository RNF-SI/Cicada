module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',     // Nouvelle fonctionnalite
        'fix',      // Correction de bug
        'docs',     // Documentation
        'style',    // Formatage (pas de changement de code)
        'refactor', // Refactoring
        'perf',     // Amelioration de performance
        'test',     // Ajout/modification de tests
        'build',    // Systeme de build, dependances
        'ci',       // Configuration CI/CD
        'chore',    // Taches de maintenance
        'revert',   // Revert d'un commit precedent
      ],
    ],
    'scope-enum': [
      1, // warning (pas bloquant si nouveau scope)
      'always',
      [
        'auth',
        'users',
        'plans',
        'sites',
        'organismes',
        'notifications',
        'activity',
        'core',
        'api',
        'frontend',
        'backend',
        'docker',
        'deps',
        'styles',
        'tests',
        'i18n',
        'release',
        // Scopes modules/features
        'admin',
        'e2e',
        'enjeux',
        'enjeux-list',
        'forms',
        'gauge',
        'indicateurs',
        'maps',
        'mindmap',
        'models',
        'nomenclatures',
        'operations',
        'operation-form',
        'plan-detail',
        'routing',
        'seed-data',
        'sidebar',
        'slugs',
        'ui',
        // Scopes référentiels
        'db',
        'deploy',
        'email',
        'invite',
        'logging',
        'profile',
        'rgpd',
        'security',
        'settings',
        'shared',
        'seed',
        'bulk-import',
        'home',
        'my-requests',
      ],
    ],
    'scope-empty': [1, 'never'], // warning si pas de scope
    'subject-case': [2, 'never', ['start-case', 'pascal-case', 'upper-case']],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [1, 'always', 200],
  },
};
