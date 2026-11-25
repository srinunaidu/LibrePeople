const fs = require('fs');
const path = require('path');

// Read both generated files
const lightCss = fs.readFileSync(path.join(__dirname, 'dist/tokens.css'), 'utf8');
const darkCss = fs.readFileSync(path.join(__dirname, 'dist/tokens.dark.css'), 'utf8');

// Extract the content inside the selectors
function extractContent(css) {
  const match = css.match(/\{(.*)\}/s);
  return match ? match[1].trim() : '';
}

const lightContent = extractContent(lightCss);
const darkContent = extractContent(darkCss);

// Combine into a single file with both :root and .dark blocks
const combined = `/**
 * Do not edit directly, this file was auto-generated.
 */

:root {
${lightContent}
}

.dark {
${darkContent}
}
`;

// Write to frontend/src/tokens.css (relative to Karmathy root)
const outputPath = path.join(__dirname, '../../frontend/src/tokens.css');
fs.writeFileSync(outputPath, combined);
console.log('Combined tokens.css written to', outputPath);
