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
      ],
    ],
    'scope-empty': [1, 'never'], // warning si pas de scope
    'subject-case': [2, 'never', ['start-case', 'pascal-case', 'upper-case']],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [1, 'always', 200],
  },
};
