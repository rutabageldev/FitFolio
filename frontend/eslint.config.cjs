const js = require('@eslint/js');
const tseslint = require('typescript-eslint'); // provides .parser and .plugin
const react = require('eslint-plugin-react');
const reactHooks = require('eslint-plugin-react-hooks');
const jsxA11y = require('eslint-plugin-jsx-a11y');
const importPlugin = require('eslint-plugin-import');
const globals = require('globals');

// helper: merge rules from flat/legacy configs
const mergeRules = (cfg) =>
  Array.isArray(cfg)
    ? cfg.reduce((acc, c) => Object.assign(acc, c?.rules || {}), {})
    : (cfg?.rules || {});

const jsRules       = mergeRules(js.configs.recommended);
const tsRules       = mergeRules(tseslint.configs.recommended);
const reactRules    = mergeRules(react.configs.recommended);
const hooksRules    = mergeRules(reactHooks.configs.recommended);
const a11yRules     = mergeRules(jsxA11y.configs.recommended);
const importRules   = mergeRules(importPlugin.configs.recommended);

module.exports = [
  // ignore build outputs
  { ignores: ['dist', 'build', 'node_modules'] },

  // JS / JSX
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: globals.browser,
    },
    plugins: {
      react,
      'react-hooks': reactHooks,
      import: importPlugin,
      'jsx-a11y': jsxA11y,
    },
    settings: { react: { version: 'detect' } },
    rules: {
      ...jsRules,
      ...reactRules,
      ...hooksRules,
      ...a11yRules,
      ...importRules,
      'import/no-unresolved': ['error', { ignore: ['^/vite\\.svg$'] }],
      'react/react-in-jsx-scope': 'off',
    },
  },

  // TS / TSX
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tseslint.parser,
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: globals.browser,
    },
    plugins: {
      '@typescript-eslint': tseslint.plugin, // <-- define the plugin object here
      react,
      'react-hooks': reactHooks,
      import: importPlugin,
      'jsx-a11y': jsxA11y,
    },
    settings: { react: { version: 'detect' } },
    rules: {
      ...jsRules,
      ...tsRules,
      ...reactRules,
      ...hooksRules,
      ...a11yRules,
      ...importRules,
      'react/react-in-jsx-scope': 'off',
    },
  },
];
