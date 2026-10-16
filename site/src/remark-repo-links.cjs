/**
 * Links to files in the repository that are not pages become links to GitHub.
 *
 * The Markdown is written to read on GitHub, where a relative link can point at anything in the
 * tree: a Python module, a Turtle file, a Terraform directory, a sample corpus document. On the
 * site only the pages exist, so this plugin rewrites every relative link whose target is not a
 * page into a link to the same path on GitHub (blob for a file, tree for a directory), keeping
 * the anchor. It runs before Docusaurus's own link handling, so what Docusaurus then resolves
 * is pages, images and the few files it serves as assets.
 *
 * The same exclusion list decides which Markdown files are pages, here and in
 * docusaurus.config.mjs (excludeGlobs), so the two never disagree.
 */
const fs = require('node:fs');
const path = require('node:path');

// Directories whose Markdown is not a page: code, infrastructure, tests, tooling, the vendored
// chat library and the sample corpora. The sample documents under examples/space-missions/<set>/
// are the corpus the example ingests, not documentation of it; the README beside them is a page.
const excludedDirs = [
  '.github/', 'node_modules/', 'build/', '.docusaurus/', 'site/', 'chat/vendor/', 'infra/',
  'src/', 'tests/', 'portal/', 'scripts/', 'examples/sherlock-holmes/', '.venv/', '.build/',
  '.ci-deployment/',
];
const excludedFiles = ['AGENTS.md'];
const corpusDocument = /^examples\/space-missions\/[^/]+\//;

// The globs docusaurus.config.mjs passes to the docs plugin, from the same lists.
const excludeGlobs = [
  ...excludedDirs.map((d) => `${d}**`),
  ...excludedFiles,
  'examples/space-missions/*/**',
  '**/_*.{js,jsx,ts,tsx,md,mdx}',
  '**/_*/**',
  '**/*.test.{js,jsx,ts,tsx}',
  '**/__tests__/**',
];

function isExcludedPage(rel) {
  return excludedFiles.includes(rel) || excludedDirs.some((d) => rel.startsWith(d)) || corpusDocument.test(rel);
}

// What Docusaurus itself handles: pages, and files it bundles as assets when linked.
const pageExt = new Set(['.md', '.mdx']);
const assetExt = new Set(['.png', '.svg', '.jpg', '.jpeg', '.gif', '.webp', '.pdf']);

function isRelative(url) {
  return url && !/^[a-z][a-z0-9+.-]*:/i.test(url) && !url.startsWith('/') && !url.startsWith('#');
}

function walk(node, fn) {
  fn(node);
  if (node.children) for (const child of node.children) walk(child, fn);
}

/**
 * @param {{root: string, repoUrl: string, branch?: string}} options
 */
function remarkRepoLinks(options) {
  const root = path.resolve(options.root);
  const branch = options.branch || 'main';
  return (tree, file) => {
    const from = path.dirname(file.path);
    walk(tree, (node) => {
      if (node.type !== 'link' && node.type !== 'definition') return;
      if (!isRelative(node.url)) return;
      const [target, hash] = node.url.split('#');
      const bare = target.split('?')[0];
      if (!bare) return;
      const abs = path.resolve(from, decodeURI(bare));
      const rel = path.relative(root, abs).split(path.sep).join('/');
      if (rel.startsWith('..') || !fs.existsSync(abs)) return;
      const anchor = hash ? `#${hash}` : '';
      if (fs.statSync(abs).isDirectory()) {
        node.url = `${options.repoUrl}/tree/${branch}/${rel}`;
        return;
      }
      const ext = path.extname(abs).toLowerCase();
      if (assetExt.has(ext)) return;
      if (pageExt.has(ext) && !isExcludedPage(rel)) return;
      node.url = `${options.repoUrl}/blob/${branch}/${rel}${anchor}`;
    });
  };
}

module.exports = remarkRepoLinks;
module.exports.excludeGlobs = excludeGlobs;
module.exports.isExcludedPage = isExcludedPage;
