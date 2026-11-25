/** @type {import('style-dictionary').Config} */
const { default: StyleDictionary } = require('style-dictionary');

// Custom transform to handle semantic tokens with light/dark value objects
StyleDictionary.registerTransform({
  name: 'semantic/light-dark',
  type: 'value',
  transitive: true,
  filter: (token) => {
    const val = token.$value ?? token.value;
    return val && typeof val === 'object' && 'light' in val && 'dark' in val;
  },
  transform: (token, config, options) => {
    const val = token.$value ?? token.value;
    // Get mode from platform options
    const mode = config.options?.mode || 'light';
    return val[mode];
  },
});

// Custom transform group
StyleDictionary.registerTransformGroup({
  name: 'css/semantic',
  transforms: [
    'attribute/cti',
    'name/kebab',
    'time/seconds',
    'html/icon',
    'size/px',
    'color/css',
    'asset/url',
    'fontFamily/css',
    'cubicBezier/css',
    'strokeStyle/css/shorthand',
    'border/css/shorthand',
    'typography/css/shorthand',
    'transition/css/shorthand',
    'shadow/css/shorthand',
    'semantic/light-dark',
  ],
});

const config = {
  source: ["src/**/*.json"],
  platforms: {
    // Light mode platform
    cssLight: {
      transformGroup: "css/semantic",
      buildPath: "dist/",
      options: {
        mode: "light",
      },
      files: [
        {
          destination: "tokens.css",
          format: "css/variables",
          options: {
            selector: ":root, .light-surface",
            format: "flat",
          },
          // Include all tokens (no filter needed since we want all tokens in light mode)
          filter: () => true,
        },
      ],
    },
    // Dark mode platform
    cssDark: {
      transformGroup: "css/semantic",
      buildPath: "dist/",
      options: {
        mode: "dark",
      },
      files: [
        {
          destination: "tokens.dark.css",
          format: "css/variables",
          options: {
            selector: ".dark",
            format: "flat",
          },
          // Include all tokens (no filter needed since we want all tokens in dark mode)
          filter: () => true,
        },
      ],
    },
    js: {
      transformGroup: "js",
      buildPath: "dist/",
      files: [
        {
          destination: "tokens.js",
          format: "javascript/es6",
        },
        {
          destination: "tokens.d.ts",
          format: "typescript/es6-declarations",
        },
      ],
    },
    json: {
      transformGroup: "js",
      buildPath: "dist/",
      files: [
        {
          destination: "tokens.json",
          format: "json/nested",
        },
      ],
    },
  },
};

module.exports = config;
