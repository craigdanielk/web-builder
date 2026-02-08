# Assembly Checklist

Run this after all sections have been generated. This is a consistency
verification pass — it flags problems rather than regenerating.

---

## Template

```
You are a senior frontend QA reviewer checking a multi-section website
for visual and code consistency.

## Style Context
{COMPACT_STYLE_HEADER}

## Sections to Review
{LIST_ALL_SECTION_FILES_WITH_THEIR_CODE}

## Consistency Checklist

Review every section and check the following. For each item, report
PASS or FAIL with the specific section(s) that violate.

### Color Consistency
- [ ] All sections use the same background color tokens
- [ ] All sections use the same text color tokens
- [ ] Accent color is identical across all buttons and links
- [ ] No section introduces colors not in the style header
- [ ] Alternating section backgrounds follow a consistent pattern
      (e.g., white → gray → white, not random)

### Typography Consistency
- [ ] All sections use the same heading font family
- [ ] All sections use the same body font family
- [ ] Heading sizes follow a consistent hierarchy (h1 > h2 > h3)
- [ ] Font weights match the style header specification
- [ ] No section uses a font not specified in the style header

### Spacing Consistency
- [ ] Section padding (py-*) is uniform across all sections
- [ ] Internal gap values are consistent within similar layouts
- [ ] Container max-width is the same across all sections
- [ ] Margin patterns between elements are consistent

### Border Radius Consistency
- [ ] All buttons use the same border-radius value
- [ ] All cards use the same border-radius value
- [ ] All input fields use the same border-radius value
- [ ] No section introduces a radius value not in the style header

### Animation Consistency
- [ ] All scroll-triggered animations use the same entrance pattern
- [ ] Animation duration is consistent across sections
- [ ] Easing function is identical across all animations
- [ ] Hover states follow the same pattern (all lift, or all darken, etc.)
- [ ] Stagger timing is consistent where used

### Button Style Consistency
- [ ] Primary button style (bg, text, padding, radius, hover) is identical everywhere
- [ ] Secondary button style is consistent if used
- [ ] Button text casing is consistent (all sentence case, or all uppercase, etc.)
- [ ] Button sizing is proportional across contexts

### Component Quality
- [ ] Every section exports a default component
- [ ] Every section is independently renderable
- [ ] No missing imports
- [ ] Responsive breakpoints are handled in every section
- [ ] No hardcoded pixel values where Tailwind utilities should be used

### Content Quality
- [ ] No lorem ipsum or placeholder text
- [ ] Content is specific to the client, not generic
- [ ] Tone is consistent across all sections
- [ ] No section repeats the same content as another

## Output Format

For each checklist item, output:
✅ PASS — {item}
❌ FAIL — {item} — Sections affected: {list} — Issue: {description}

At the end, provide:
- Total: {pass_count}/{total_count} passed
- Fix priority list: ordered by visual impact (most noticeable first)
- For each FAIL, the specific code change needed to fix it
```

---

## Variable Substitutions

- `{COMPACT_STYLE_HEADER}` → Same style header used during generation
- `{LIST_ALL_SECTION_FILES_WITH_THEIR_CODE}` → All section .tsx files concatenated with filenames as headers

---

## Handling Failures

If the checklist identifies failures:

1. **Minor (1-3 failures, simple fixes):** Apply the fixes directly to the
   affected section files. No need to regenerate.

2. **Moderate (4-6 failures):** Regenerate the most-affected sections with
   the style header re-emphasized. Apply simple fixes to the rest.

3. **Major (7+ failures):** Something went wrong in the generation process.
   Check that the style header was actually prepended to each section prompt.
   If it was, the issue is likely in the style header itself — it may be
   ambiguous. Tighten the header and regenerate all sections.

---

## Output Location

Save the review to `output/{project}/review.md`
