/**
 * The banner a catalogue page carries under its title, generated from its front matter: what
 * kind of element it is, its identifier, status, version and owner, and where its slides and PDF
 * are when the page is also a published deck.
 *
 * The decks that exist are the ones docusaurus.config.mjs found under site/static/decks at build
 * time (customFields.publishedDecks), so a page whose deck is not published shows no link, and the
 * site builds the same with or without the decks.
 */
import React from 'react';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';

const KIND_LABEL = {
  platform: 'Platform',
  outcome: 'Outcome',
  'use-case': 'Use case',
  capability: 'Capability',
  product: 'Product',
  'bounded-context': 'Bounded context',
  abb: 'Architecture building block',
  sbb: 'Solution building block',
  pattern: 'Pattern document',
  service: 'Service',
  'decision-record': 'Decision record',
  consideration: 'Consideration',
  'deployment-node': 'Deployment node',
};
const PATTERN_TYPE_LABEL = {
  'architecture-pattern': 'Architecture pattern',
  'reference-architecture': 'Reference architecture',
};

function DeckLinks({deckId}) {
  const {siteConfig} = useDocusaurusContext();
  const decks = siteConfig.customFields?.publishedDecks ?? {};
  const deck = decks[deckId];
  const slides = useBaseUrl(`decks/${deckId}/index.html`);
  const pdf = useBaseUrl(`decks/${deckId}/${deck?.pdf ?? ''}`);
  if (!deck) return null;
  return (
    <span className="arch-banner__decks">
      <a href={slides}>Slides</a>
      {deck.pdf ? <> · <a href={pdf}>PDF</a></> : null}
    </span>
  );
}

export default function ArchitectureBanner() {
  const {frontMatter} = useDoc();
  const kind = frontMatter.kind;
  const deckId = frontMatter.deck_publish === true ? frontMatter.deck_id : null;
  if (!kind && !deckId) return null;
  const kindLabel = kind === 'pattern' && PATTERN_TYPE_LABEL[frontMatter.pattern_type]
    ? PATTERN_TYPE_LABEL[frontMatter.pattern_type]
    : KIND_LABEL[kind] ?? kind;
  const id = frontMatter.numeric_id ?? frontMatter.id;
  const owner = typeof frontMatter.owner === 'string' ? frontMatter.owner.replace(/\s*\(.*\)\s*$/, '') : null;
  return (
    <div className="arch-banner" role="note" aria-label="Page metadata">
      {kind ? <span className="arch-banner__chip arch-banner__kind">{kindLabel}</span> : null}
      {id ? <span className="arch-banner__chip">{id}</span> : null}
      {frontMatter.status ? <span className={`arch-banner__chip arch-banner__status arch-banner__status--${frontMatter.status}`}>{frontMatter.status}</span> : null}
      {frontMatter.version ? <span className="arch-banner__item">v{frontMatter.version}</span> : null}
      {owner ? <span className="arch-banner__item">{owner}</span> : null}
      {deckId ? <DeckLinks deckId={deckId} /> : null}
    </div>
  );
}
