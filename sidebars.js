// @ts-check
// The sidebar lists the repository's pages in reading order: what it is, how to install it, the
// architecture, the design notes behind it, how to deploy it, the examples, then the project
// files. Ids are file paths without the extension, or the id a page's front matter declares.
//
// The architecture category mirrors docs/architecture as it is on disk, which is the layout every
// repository on the architecture continuum uses: the platform and where it sits, then the demand
// space, the solution space, the runtime and the decisions, each kind with its register and a
// page per element. Nothing is listed that is not a folder or a page there. Each register folder
// is read from disk by pages(): its README is the category's own page, and every other page under
// it is a child, so no page is listed twice.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));

/** The id a page's front matter declares, or null. Docusaurus prefixes it with the folder. */
function declaredId(file) {
  const m = fs.readFileSync(file, 'utf8').match(/^---\n([\s\S]*?)\n---/);
  const id = m && m[1].match(/^id:\s*["']?([^"'\n]+)["']?\s*$/m);
  return id ? id[1].trim() : null;
}

/**
 * Every page in a folder except its README, as sidebar doc items in file order: a sub-folder's
 * index.md, or a Markdown file. The README is the category's link, so it is not a child too.
 */
function pages(dir) {
  const items = [];
  for (const entry of fs.readdirSync(path.join(root, dir), {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name))) {
    if (entry.name === 'README.md') continue;
    const file = entry.isDirectory() ? path.join(root, dir, entry.name, 'index.md') : path.join(root, dir, entry.name);
    if (entry.isDirectory() ? !fs.existsSync(file) : !entry.name.endsWith('.md')) continue;
    // Docusaurus prefixes a declared id with the page's own folder: CN-001/index.md with id CN-001
    // is decisions/CN-001-…/CN-001, and ADR-001-….md with id ADR-001 is decisions/ADR-001.
    const id = entry.isDirectory()
      ? `${dir}/${entry.name}/${declaredId(file) ?? 'index'}`
      : `${dir}/${declaredId(file) ?? entry.name.slice(0, -3)}`;
    items.push({type: 'doc', id});
  }
  return items;
}

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    {type: 'doc', id: 'README', label: 'Overview'},
    {type: 'doc', id: 'QUICKSTART', label: 'Quick start on AWS'},
    {
      type: 'category',
      label: 'Architecture',
      link: {type: 'doc', id: 'docs/architecture/README'},
      items: [
        {type: 'doc', id: 'docs/architecture/PL-001', label: 'PL-001 Knowledge Store'},
        {type: 'doc', id: 'docs/architecture/landscape', label: 'Landscape'},
        {type: 'doc', id: 'docs/architecture/target-state', label: 'Target state by subdomain'},
        {
          type: 'category',
          label: 'Demand',
          link: {
            type: 'generated-index',
            title: 'Demand',
            description: 'What must be possible and for whom: the domain and its subdomains, the outcomes the platform owns, the use cases that realise them, the capabilities they require, and the product with its features.',
            slug: '/docs/architecture/demand',
          },
          items: [
            {type: 'doc', id: 'docs/architecture/demand/domains', label: 'Domain and subdomains'},
            {type: 'category', label: 'Outcomes', items: pages('docs/architecture/demand/outcomes')},
            {type: 'category', label: 'Use cases', link: {type: 'doc', id: 'docs/architecture/demand/use-cases/README'}, items: pages('docs/architecture/demand/use-cases')},
            {type: 'category', label: 'Capabilities', link: {type: 'doc', id: 'docs/architecture/demand/capabilities/README'}, items: pages('docs/architecture/demand/capabilities')},
            {type: 'doc', id: 'docs/architecture/demand/PRD-001', label: 'PRD-001 and its features'},
          ],
        },
        {
          type: 'category',
          label: 'Solution',
          link: {
            type: 'generated-index',
            title: 'Solution',
            description: 'What realises the demand: the bounded contexts, the architecture building blocks inside them, the solution building blocks that realise those with named technologies, and the architecture pattern and reference architecture that compose them.',
            slug: '/docs/architecture/solution',
          },
          items: [
            {type: 'category', label: 'Bounded contexts', link: {type: 'doc', id: 'docs/architecture/solution/contexts/README'}, items: pages('docs/architecture/solution/contexts')},
            {type: 'category', label: 'Architecture building blocks', link: {type: 'doc', id: 'docs/architecture/solution/abbs/README'}, items: pages('docs/architecture/solution/abbs')},
            {type: 'category', label: 'Solution building blocks', link: {type: 'doc', id: 'docs/architecture/solution/sbbs/README'}, items: pages('docs/architecture/solution/sbbs')},
            {type: 'category', label: 'Architecture patterns and reference architectures', link: {type: 'doc', id: 'docs/architecture/solution/patterns/README'}, items: pages('docs/architecture/solution/patterns')},
          ],
        },
        {
          type: 'category',
          label: 'Runtime',
          link: {type: 'doc', id: 'docs/architecture/runtime/README'},
          items: [
            {type: 'doc', id: 'docs/architecture/runtime/deployable-units', label: 'Deployable units'},
            {type: 'category', label: 'Services', items: pages('docs/architecture/runtime/services')},
          ],
        },
        {type: 'category', label: 'Decisions', link: {type: 'doc', id: 'docs/architecture/decisions/README'}, items: pages('docs/architecture/decisions')},
      ],
    },
    {
      type: 'category',
      label: 'Design notes',
      link: {type: 'doc', id: 'docs/design/README'},
      items: [
        'docs/design/aws/aws',
        'docs/design/aws/backends',
        'docs/design/aws/structured',
        'docs/design/aws/scalability',
        'docs/design/security',
        'docs/design/source-controls',
        'docs/design/target-state-view',
        'docs/design/evaluation-false-positives',
      ],
    },
    {
      type: 'category',
      label: 'Deploy on AWS',
      link: {type: 'doc', id: 'docs/deploy/aws/README'},
      items: ['docs/deploy/aws/components', 'docs/deploy/aws/parameters'],
    },
    {type: 'doc', id: 'docs/core-vocabulary', label: 'Core vocabulary'},
    {type: 'doc', id: 'docs/workbench', label: 'The workbench'},
    {type: 'doc', id: 'docs/w3id/README', label: 'Permanent identifiers'},
    {type: 'doc', id: 'chat/README', label: 'Chat page'},
    {type: 'doc', id: 'docs/branding', label: 'Branding'},
    {
      type: 'category',
      label: 'Examples',
      items: [
        {type: 'doc', id: 'examples/space-missions/README', label: 'Space missions corpus'},
        {type: 'doc', id: 'examples/deployment/README', label: 'Deployment template'},
        {type: 'doc', id: 'examples/deployment/ontology/README', label: 'Deployment ontology'},
      ],
    },
    {
      type: 'category',
      label: 'Project',
      items: [
        {type: 'doc', id: 'CONTRIBUTING', label: 'Contributing'},
        {type: 'doc', id: 'SECURITY', label: 'Security'},
        {type: 'doc', id: 'CODE_OF_CONDUCT', label: 'Code of conduct'},
        {type: 'doc', id: 'THIRD_PARTY_NOTICES', label: 'Third-party notices'},
        {type: 'doc', id: 'CHANGELOG', label: 'Changelog'},
      ],
    },
  ],
};

export default sidebars;
