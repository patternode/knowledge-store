/**
 * Wrapped DocItem/Content: every page whose front matter is a catalogue element gets its banner,
 * placed directly under the title as page metadata (kind, identifier, status, version, owner, and
 * the slides and PDF where the page is also a published deck).
 */
import React, {useEffect, useRef} from 'react';
import Content from '@theme-init/DocItem/Content';
import ArchitectureBanner from '@site/site/src/components/ArchitectureBanner';

export default function DocItemContentWrapper(props) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const h1 = ref.current.querySelector('h1');
    const banner = ref.current.querySelector('.arch-banner');
    if (h1 && banner && h1.nextSibling !== banner) {
      h1.insertAdjacentElement('afterend', banner);
    }
  }, []);

  return (
    <div ref={ref}>
      <ArchitectureBanner />
      <Content {...props} />
    </div>
  );
}
