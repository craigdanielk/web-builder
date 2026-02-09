# Image Rendering Patterns

Standard patterns for rendering images across all sections. Use these
consistently to maintain visual cohesion and accessibility.

---

## When to Use Each Pattern

| Pattern | Use For | Image Source |
|---------|---------|-------------|
| Hero Background | Hero sections, full-bleed CTAs | Reference manifest or gradient |
| Card Image | Product cards, team cards, portfolio | Reference manifest or gradient |
| Split Section | About sections, CTA with side image | Reference manifest or gradient |
| Logo/Icon | Nav logos, footer logos, partner logos | Reference manifest `<img>` tag |
| Gradient Fallback | Any section when no image available | Generated gradient |

---

## Hero / Large Background

Full-viewport or full-width background image with overlay for text readability.

```tsx
<div className="relative min-h-screen overflow-hidden">
  {/* Background image */}
  <div
    className="absolute inset-0 z-0"
    style={{
      backgroundImage: `url('https://cdn.example.com/hero.jpg')`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }}
    role="img"
    aria-label="Freshly roasted coffee beans"
  />
  {/* Gradient overlay for text readability */}
  <div className="absolute inset-0 z-[1] bg-gradient-to-b from-black/60 via-black/40 to-transparent" />
  {/* Content */}
  <div className="relative z-10">
    {/* text content here */}
  </div>
</div>
```

**Rules:**
- Always use gradient overlay (from-black/60 to-transparent) over hero images
- `backgroundSize: 'cover'` and `backgroundPosition: 'center'` always
- z-index layering: image (0) → overlay (1) → content (10)

---

## Card Image

Product cards, team members, portfolio items — medium-sized contained images.

```tsx
<div className="rounded-xl overflow-hidden border border-stone-300">
  {/* Card image */}
  <div
    className="relative aspect-[4/3] w-full"
    style={{
      backgroundImage: `url('https://cdn.example.com/product.jpg')`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }}
    role="img"
    aria-label="Ethiopia Yirgacheffe coffee"
  />
  {/* Card body */}
  <div className="p-6">
    {/* text content here */}
  </div>
</div>
```

**Rules:**
- Use `aspect-[4/3]` for landscape cards, `aspect-square` for square, `aspect-[3/4]` for portrait
- `rounded-xl` on the card container clips the image corners
- Image div has `overflow-hidden` via parent

---

## Split Section Image

About sections, CTA sections — image alongside text in a two-column layout.

```tsx
<div className="grid lg:grid-cols-2 gap-8 items-center">
  {/* Text column */}
  <div>
    {/* text content here */}
  </div>
  {/* Image column */}
  <div
    className="aspect-[3/4] w-full rounded-xl overflow-hidden shadow-lg"
    style={{
      backgroundImage: `url('https://cdn.example.com/about.jpg')`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }}
    role="img"
    aria-label="Coffee roasting process at Bluebird"
  />
</div>
```

**Rules:**
- Use `aspect-[3/4]` or `aspect-[4/5]` for portrait orientation
- Include `shadow-lg` for depth against the page background
- On mobile, image stacks below text (natural grid flow)

---

## Logo / Icon

Navigation logos, footer logos, partner logos — use actual `<img>` tags.

```tsx
<img
  src="https://cdn.example.com/logo.png"
  alt="Bluebird Coffee Roastery"
  className="h-8 w-auto"
  loading="lazy"
/>
```

**Rules:**
- This is the ONLY pattern that uses `<img>` tags
- Always include descriptive `alt` text
- Always include `loading="lazy"` (except nav logo which should be eager)
- Size with height (`h-8`, `h-10`) and `w-auto` to maintain aspect ratio

---

## Gradient Fallback

When no reference image is available for a section. Use brand-relevant gradient
colors that approximate the mood of the intended image.

```tsx
<div
  className="absolute inset-0 z-0"
  style={{
    background: 'linear-gradient(135deg, #1a120b 0%, #2c1e14 30%, #3b2a1c 55%, #1a120b 100%)',
  }}
  role="img"
  aria-label="Decorative coffee-toned gradient"
/>
```

**Rules:**
- Gradient colors should relate to the industry (warm browns for coffee, cool blues for tech, etc.)
- Still include `role="img"` and `aria-label`
- Use multi-stop gradients (3-4 stops) for visual richness

---

## Accessibility Requirements

All image patterns MUST include:

| Element | Attribute | Required | Notes |
|---------|-----------|----------|-------|
| Background div | `role="img"` | Always | Tells screen readers this div is an image |
| Background div | `aria-label` | Always | Descriptive text of image content |
| `<img>` tag | `alt` | Always | Descriptive text, not "image of..." |
| `<img>` tag | `loading="lazy"` | Recommended | Except above-the-fold images |

---

## DO NOT

- Use `/api/placeholder/800/600` or similar placeholder service URLs
- Use `<img>` tags for decorative/background images
- Omit `role="img"` on background-image divs
- Use `object-fit` on divs (that's for `<img>` tags — use `backgroundSize` instead)
- Hardcode image dimensions that break responsiveness

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-09 | Initial patterns created | bluebird-coffee-roastery planning |
