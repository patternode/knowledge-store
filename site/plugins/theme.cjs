/**
 * Registers site/src/theme as a theme path, so the components there wrap the classic theme's
 * (@theme-original) the way a swizzle under src/theme would. The repository's src/ is the Python
 * package, so the site's components live under site/ with the rest of the site's own files.
 */
const path = require('node:path');

module.exports = function siteTheme() {
  return {
    name: 'knowledge-store-site-theme',
    getThemePath() {
      return path.resolve(__dirname, '..', 'src', 'theme');
    },
  };
};
