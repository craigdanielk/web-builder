/**
 * Section Context Formatter
 * Formats per-section reference context from extraction data into a text
 * block that gets injected into the section generation prompt.
 */

'use strict';

/**
 * Build a reference context block for a specific section.
 *
 * @param {object} extractionData - Full extraction result from extractReference()
 * @param {number} sectionIndex - Index of the section in extractionData.sections
 * @param {object} mappedSection - Output from archetype-mapper for this section
 * @returns {string} Formatted context block for the section prompt
 */
function buildSectionContext(extractionData, sectionIndex, mappedSection) {
  const section = extractionData.sections[sectionIndex];
  if (!section) return '';

  const lines = [];
  lines.push('## Reference Section Context');
  lines.push(`Source: ${extractionData.url}`);
  lines.push(`Section ${sectionIndex + 1} of ${extractionData.sections.length}`);
  lines.push(`Mapped as: ${mappedSection.archetype} | ${mappedSection.variant} (confidence: ${(mappedSection.confidence * 100).toFixed(0)}%)`);
  lines.push('');

  // Section dimensions
  lines.push('### Layout');
  lines.push(`- Dimensions: ${section.rect.width}px wide x ${section.rect.height}px tall`);
  lines.push(`- Position: y=${section.rect.y}px from top`);
  lines.push(`- HTML tag: <${section.tag}>${section.id ? ` id="${section.id}"` : ''}`);
  if (section.label) lines.push(`- Section heading: "${section.label}"`);
  lines.push('');

  // DOM elements in this section
  const sectionElements = (extractionData.renderedDOM || []).filter(
    (el) => el.sectionIndex === sectionIndex
  );

  if (sectionElements.length > 0) {
    lines.push('### Structure');

    // Count element types
    const tagCounts = {};
    for (const el of sectionElements) {
      tagCounts[el.tag] = (tagCounts[el.tag] || 0) + 1;
    }
    const tagSummary = Object.entries(tagCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([tag, count]) => `${tag}(${count})`)
      .join(', ');
    lines.push(`- Elements: ${sectionElements.length} total — ${tagSummary}`);

    // Detect layout patterns
    const hasGrid = sectionElements.some((el) =>
      el.styles?.display === 'grid' || (el.className || '').includes('grid')
    );
    const hasFlex = sectionElements.some((el) =>
      el.styles?.display === 'flex' || (el.className || '').includes('flex')
    );
    const hasColumns = sectionElements.filter(
      (el) => el.styles?.display === 'flex' || el.styles?.display === 'grid'
    );

    if (hasGrid) lines.push('- Layout: CSS Grid detected');
    if (hasFlex) lines.push('- Layout: Flexbox detected');

    // Count images
    const images = sectionElements.filter((el) => el.tag === 'img');
    if (images.length > 0) {
      lines.push(`- Images: ${images.length} image(s)`);
    }

    // Count buttons/links
    const buttons = sectionElements.filter(
      (el) => el.tag === 'button' || el.tag === 'a'
    );
    if (buttons.length > 0) {
      lines.push(`- Interactive: ${buttons.length} button(s)/link(s)`);
    }

    // Detect card patterns (repeating similar-sized elements)
    const cards = sectionElements.filter(
      (el) => (el.tag === 'div' || el.tag === 'article' || el.tag === 'li') &&
        el.rect.width > 100 && el.rect.height > 100
    );
    if (cards.length >= 3) {
      const widths = cards.map((c) => c.rect.width);
      const allSameWidth = widths.every((w) => Math.abs(w - widths[0]) < 20);
      if (allSameWidth) {
        lines.push(`- Card pattern: ${cards.length} cards of ~${widths[0]}px width`);
      }
    }

    // Notable styles in this section
    const uniqueBgColors = new Set();
    const uniqueFonts = new Set();
    const uniqueRadii = new Set();

    for (const el of sectionElements) {
      const s = el.styles || {};
      if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'transparent') {
        uniqueBgColors.add(s.backgroundColor);
      }
      if (s.fontFamily) {
        const primary = s.fontFamily.split(',')[0].trim().replace(/['"]/g, '');
        if (primary) uniqueFonts.add(primary);
      }
      if (s.borderRadius && s.borderRadius !== '0px') {
        uniqueRadii.add(s.borderRadius);
      }
    }

    if (uniqueBgColors.size > 0) {
      lines.push(`- Background colors: ${[...uniqueBgColors].slice(0, 5).join(', ')}`);
    }
    if (uniqueFonts.size > 0) {
      lines.push(`- Fonts used: ${[...uniqueFonts].slice(0, 4).join(', ')}`);
    }
    if (uniqueRadii.size > 0) {
      lines.push(`- Border radii: ${[...uniqueRadii].slice(0, 4).join(', ')}`);
    }

    lines.push('');
  }

  // Text content in this section
  const sectionTexts = (extractionData.textContent || []).filter((t) => {
    const textY = t.rect?.y || 0;
    return textY >= section.rect.y && textY <= section.rect.y + section.rect.height;
  });

  if (sectionTexts.length > 0) {
    lines.push('### Content');

    const headings = sectionTexts.filter((t) => t.isHeading);
    const paragraphs = sectionTexts.filter((t) => t.tag === 'p');
    const ctas = sectionTexts.filter((t) => t.isInteractive);

    if (headings.length > 0) {
      lines.push('Headings:');
      for (const h of headings.slice(0, 5)) {
        lines.push(`  - <${h.tag}>: "${h.text.slice(0, 100)}"`);
      }
    }

    if (paragraphs.length > 0) {
      lines.push(`Body text: ${paragraphs.length} paragraph(s)`);
      if (paragraphs[0]) {
        lines.push(`  First: "${paragraphs[0].text.slice(0, 150)}..."`);
      }
    }

    if (ctas.length > 0) {
      lines.push('CTAs/Links:');
      for (const cta of ctas.slice(0, 5)) {
        lines.push(`  - <${cta.tag}>: "${cta.text.slice(0, 80)}"${cta.href ? ` → ${cta.href.slice(0, 60)}` : ''}`);
      }
    }

    lines.push('');
  }

  lines.push('### Instructions');
  lines.push('Use the reference context above to inform your layout and content decisions.');
  lines.push('Match the STRUCTURE and COMPOSITION of the original section while applying');
  lines.push('the style tokens from the STYLE CONTEXT header. Do NOT copy text verbatim —');
  lines.push('write equivalent content appropriate for the client brief.');

  return lines.join('\n');
}

/**
 * Build context blocks for all sections.
 *
 * @param {object} extractionData - Full extraction result
 * @param {object[]} mappedSections - Output from mapSectionsToArchetypes()
 * @returns {object} Map of section index to context string
 */
function buildAllSectionContexts(extractionData, mappedSections) {
  const contexts = {};
  for (let i = 0; i < mappedSections.length; i++) {
    const mapped = mappedSections[i];
    const originalIndex = mapped.index !== undefined ? mapped.index : i;
    contexts[i] = buildSectionContext(extractionData, originalIndex, mapped);
  }
  return contexts;
}

module.exports = { buildSectionContext, buildAllSectionContexts };
