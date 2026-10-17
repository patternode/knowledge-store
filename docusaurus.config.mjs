// @ts-check
// Docusaurus configuration for the Knowledge Store documentation site.
//
// The repository's Markdown is the site. README.md is the home page; the guides under docs/,
// the example READMEs, the chat page's README and the project files (quick start, contributing,
// security, changelog) are its pages. Nothing is copied into a second tree: a page is published
// by being written. The exclusion list in site/src/remark-repo-links.cjs names what is not a
// page, and the same plugin turns links to code and other files into links to GitHub.

import fs from 'node:fs';
import {themes} from 'prism-react-renderer';
import {createRequire} from 'node:module';

// Docusaurus transpiles this file to CommonJS, where import.meta is unavailable, and always
// runs from the site root, so paths resolve from there.
const siteDir = process.cwd();
const require = createRequire(`${siteDir}/`);
const remarkRepoLinks = require('./site/src/remark-repo-links.cjs');

const repoUrl = 'https://github.com/patternode/knowledge-store';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Knowledge Store',
  tagline: 'Documents in, an ontology-typed knowledge graph and a grounded chat out, for any domain',

  // Origin and base path, overridable at build time: the Deploy site workflow passes what the
  // repository's Pages settings report, and a preview host or a local build can pass its own.
  url: process.env.SITE_URL || 'https://patternode.github.io',
  baseUrl: process.env.SITE_BASE_URL || '/knowledge-store/',

  organizationName: 'patternode',
  projectName: 'knowledge-store',

  trailingSlash: true,

  favicon: 'img/favicon.svg',

  // The build is strict: everything Docusaurus can check is a build failure, not a warning.
  // A documentation site whose cross-references rot is worse than no site, and two pages at
  // one route would publish one of them silently.
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  onDuplicateRoutes: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    // .md files are CommonMark, as GitHub renders them; only .mdx files are MDX.
    format: 'detect',
    hooks: {
      onBrokenMarkdownLinks: 'throw',
      onBrokenMarkdownImages: 'throw',
    },
  },

  staticDirectories: ['site/static'],

  // The decks published under site/static/decks (npm run publish:decks), by deck_id, for the banner
  // each catalogue page carries: a page whose deck is not there shows no link.
  customFields: {
    publishedDecks: Object.fromEntries(
      (fs.existsSync(`${siteDir}/site/static/decks`) ? fs.readdirSync(`${siteDir}/site/static/decks`) : [])
        .filter((id) => fs.existsSync(`${siteDir}/site/static/decks/${id}/index.html`))
        .map((id) => [id, {pdf: fs.readdirSync(`${siteDir}/site/static/decks/${id}`).find((f) => f.endsWith('.pdf')) ?? null}]),
    ),
  },

  plugins: [
    // site/src/theme wraps the classic theme's components (the page banner).
    './site/plugins/theme.cjs',
    [
      '@docusaurus/plugin-client-redirects',
      {
        // The design notes moved out of docs/architecture, which now holds only the catalogue.
        redirects: [
          {from: '/docs/architecture/aws/', to: '/docs/design/aws/'},
          {from: '/docs/architecture/aws/backends/', to: '/docs/design/aws/backends/'},
          {from: '/docs/architecture/aws/structured/', to: '/docs/design/aws/structured/'},
          {from: '/docs/architecture/aws/scalability/', to: '/docs/design/aws/scalability/'},
          {from: '/docs/architecture/security/', to: '/docs/design/security/'},
          {from: '/docs/architecture/source-controls/', to: '/docs/design/source-controls/'},
        ],
      },
    ],
  ],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          // The whole repository is the docs tree.
          path: '.',
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          editUrl: `${repoUrl}/edit/main/`,
          // No page declares tags, so one that did would be a mistake.
          onInlineTags: 'throw',
          // Before the defaults, so Docusaurus resolves and checks only the links that stay.
          beforeDefaultRemarkPlugins: [[remarkRepoLinks, {root: siteDir, repoUrl, branch: 'main'}]],
          include: ['**/*.md', '**/*.mdx'],
          exclude: remarkRepoLinks.excludeGlobs,
        },
        blog: false,
        pages: false,
        theme: {
          customCss: ['./site/src/css/custom.css'],
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'light',
        disableSwitch: false,
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'Knowledge Store',
        logo: {
          alt: 'Patternode',
          src: 'img/logo.svg',
          srcDark: 'img/logo-reverse.svg',
        },
        items: [
          {to: '/QUICKSTART/', label: 'Quick start', position: 'left'},
          {to: '/docs/architecture/', label: 'Architecture', position: 'left'},
          {to: '/docs/deploy/aws/', label: 'Deploy', position: 'left'},
          {to: '/CHANGELOG/', label: 'Changelog', position: 'left'},
          {href: repoUrl, label: 'GitHub', position: 'right'},
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Patternode',
            items: [
              {label: 'patternode.com', href: 'https://patternode.com/'},
              {label: 'Briefings', href: 'https://patternode.com/briefings/knowledge-store/'},
            ],
          },
          {
            title: 'Project',
            items: [
              {label: 'Contributing', to: '/CONTRIBUTING/'},
              {label: 'Security', to: '/SECURITY/'},
              {label: 'Permanent identifiers', to: '/docs/w3id/'},
            ],
          },
        ],
        copyright: `Copyright © 2026 Dermot O'Brien. Licensed under the Apache License 2.0.`,
      },
      prism: {
        theme: themes.github,
        darkTheme: themes.dracula,
        additionalLanguages: ['bash', 'json', 'yaml', 'toml', 'hcl', 'python', 'turtle', 'sparql'],
      },
    }),
};

export default config;
