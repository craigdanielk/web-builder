# Image Extraction from Reference URLs

When a brief contains a **Reference URL**, extract and categorize images from
the source website for use in section generation. This replaces gradient
placeholders with actual imagery, producing more realistic visual output.

**This step is optional.** If no Reference URL is present, skip entirely —
sections fall back to gradient placeholders.

---

## Extraction Process

### 1. Fetch images with WebFetch

Use WebFetch on the Reference URL with this prompt:

```
Extract ALL image URLs from this page. For each image found, provide:
1. The full absolute URL (not relative paths)
2. The alt text or nearest heading/caption text
3. A one-sentence description of what the image likely shows (based on context)
4. Where it appears on the page (hero/header area, product grid, about section, footer, etc.)
5. Whether it appears to be large (hero/banner), medium (card/feature), or small (icon/logo)

Include images from:
- <img> tags (src attribute)
- CSS background-image URLs
- <source> tags in <picture> elements
- Open Graph / meta tags (og:image)

Exclude:
- Tracking pixels (1x1 images)
- Base64 data URIs
- SVG icons smaller than 50px
- Placeholder/skeleton images

Return as a structured list, one image per entry.
```

### 2. Categorize each image

Assign one or more categories based on:

| Signal | Weight | Example |
|--------|--------|---------|
| URL path segments | High | `/hero/`, `/products/`, `/team/` |
| Alt text keywords | High | "Our team", "Coffee beans", "Store front" |
| Page position | Medium | First large image = likely hero |
| Surrounding text | Medium | Near "About Us" heading = about category |
| Image dimensions | Low | Large landscape = hero, square = product |

### 3. Categories

10 categories aligned with section archetypes:

| Category | Description | Typical signals |
|----------|-------------|-----------------|
| `hero` | Main banner/hero images | First large image, full-width, near site name |
| `product` | Product photos, items for sale | In grids, near prices, product names in alt |
| `about` | Brand story, process, behind-the-scenes | Near "about", "story", "process" text |
| `team` | People, staff, founders | Portraits, near names/titles |
| `location` | Storefronts, interiors, maps | Near addresses, "visit us", map markers |
| `testimonial` | Customer photos, review avatars | Small, near quotes, star ratings |
| `logo` | Brand logos, partner logos | Small, in header/footer, grayscale |
| `icon` | UI icons, badges, certifications | Very small, decorative |
| `background` | Textures, patterns, ambiance | Large, low detail, atmospheric |
| `other` | Unclassified | Doesn't fit other categories |

### 4. Section-to-Category Mapping

When providing images to section generation, use this lookup:

| Section Archetype | Primary Categories | Fallback Categories |
|-------------------|-------------------|---------------------|
| HERO | `hero`, `background` | `product`, `about` |
| ABOUT | `about`, `team` | `location`, `background` |
| PRODUCT-SHOWCASE | `product` | `background`, `about` |
| PRICING | `product` | `background` |
| HOW-IT-WORKS | `about`, `product` | `background` |
| TEAM | `team` | `about`, `background` |
| TESTIMONIALS | `testimonial` | `team`, `about` |
| CTA | `hero`, `location` | `background`, `about` |
| CONTACT | `location` | `background` |
| GALLERY | `product`, `about`, `location` | `background` |
| NAV | `logo` | — |
| FOOTER | `logo` | — |
| *(any other)* | `background` | `other` |

**Lookup logic:**
1. Check primary categories first — use the first match
2. If no primary match, check fallback categories
3. If still no match, section uses gradient placeholder (no image)
4. Prefer higher-resolution images when multiple match

---

## Image Manifest Format

Save to `output/{project}/image-manifest.json`:

```json
{
  "sourceUrl": "https://www.example.com",
  "extractedAt": "2026-02-09T12:00:00Z",
  "images": [
    {
      "url": "https://cdn.example.com/hero-banner.jpg",
      "alt": "Freshly roasted coffee beans on a wooden table",
      "description": "Dark moody hero photo of coffee beans with warm lighting",
      "pagePosition": "hero",
      "size": "large",
      "categories": ["hero", "background"]
    },
    {
      "url": "https://cdn.example.com/ethiopia-yirgacheffe.jpg",
      "alt": "Ethiopia Yirgacheffe single origin coffee",
      "description": "Product photo of a coffee bag with Ethiopian origin label",
      "pagePosition": "product grid",
      "size": "medium",
      "categories": ["product"]
    }
  ],
  "byCategory": {
    "hero": ["https://cdn.example.com/hero-banner.jpg"],
    "product": [
      "https://cdn.example.com/ethiopia-yirgacheffe.jpg",
      "https://cdn.example.com/kenya-aa.jpg"
    ],
    "about": ["https://cdn.example.com/roasting-process.jpg"],
    "location": ["https://cdn.example.com/cafe-interior.jpg"],
    "logo": ["https://cdn.example.com/logo.png"]
  }
}
```

---

## Providing Images to Section Agents

When generating a section, format the relevant images like this:

```
## Reference Images
Found 2 relevant images for this HERO section:

1. https://cdn.example.com/hero-banner.jpg
   Alt: "Freshly roasted coffee beans on a wooden table"
   Size: large (landscape)

2. https://cdn.example.com/roasting-bg.jpg
   Alt: "Coffee roasting process"
   Size: large (landscape)

Use these URLs in your component with CSS backgroundImage. See image rendering
instructions in the section prompt for the exact pattern.
```

If no images match a section's categories, omit the Reference Images block
entirely — the section agent will use gradient fallbacks automatically.

---

## Edge Cases

- **WebFetch returns no images**: Skip manifest creation, all sections use gradients
- **Very few images (< 3)**: Assign to highest-priority sections (hero first, then about)
- **Duplicate URLs**: Deduplicate by URL before categorizing
- **Relative URLs**: Convert to absolute using the Reference URL's domain
- **CDN query params**: Keep full URL including query params (often needed for access)
- **Lazy-loaded images**: WebFetch may miss images loaded via JavaScript — accept this limitation

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-09 | Initial skill created | bluebird-coffee-roastery planning |
