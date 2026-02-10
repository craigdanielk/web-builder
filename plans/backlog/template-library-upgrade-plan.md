# AURELIX PATTERN LIBRARY SYSTEM - MVP BUILD SPECIFICATION

## EXECUTIVE SUMMARY

We are building an **autonomous, self-updating pattern library** that continuously analyzes award-winning websites across 20+ industries to extract reusable structural patterns, visual styles, and content strategies. This database becomes the foundational knowledge base for generating high-quality websites through pattern-based composition rather than cloning.

**Core Principle:** We are NOT building a website cloner. We are building a **pattern recognition and classification system** that learns from the best websites in each industry, extracts their structural DNA, and enables systematic recombination of proven patterns.

---

## THE PROBLEM WE'RE SOLVING

**Current State:**
- Website generation relies on manually-crafted presets
- Limited pattern diversity (1 preset per industry)
- No systematic learning from industry leaders
- Patterns become stale as design trends evolve
- No way to quantify "what makes a great fashion site vs. SaaS site"

**Target State:**
- Autonomous system continuously analyzes top-performing sites
- Pattern library grows and improves automatically
- Presets are generated from aggregated patterns across 10-50 reference sites
- System learns design trends as they emerge
- Quantified confidence scores for each pattern ("95% of top coffee sites use warm earth tones")

---

## SYSTEM ARCHITECTURE

### Layer 1: Pattern Extraction Engine
**Purpose:** Analyze individual websites and extract structural patterns

**Input:** URL + Industry classification
**Output:** Structured pattern document (YAML)

**Extraction Dimensions:**
1. **Section Sequence** - Order and types of sections (HERO → PRODUCT_GRID → ABOUT → FOOTER)
2. **Visual Style System** - Colors, typography, spacing, borders, animations
3. **Layout Archetypes** - Grid patterns, image treatments, content arrangement
4. **Content Patterns** - Tone, headline formulas, CTA language
5. **Component Inventory** - Buttons, cards, forms, navigation styles
6. **Interaction Patterns** - Hover states, scroll triggers, micro-interactions

**Technology Stack:**
- Playwright (headless browser for screenshots + DOM extraction)
- Claude Vision API (pattern recognition from screenshots)
- CSS extraction (computed styles, not raw stylesheets)
- Structural analysis (section classification, hierarchy detection)

---

### Layer 2: Pattern Aggregation & Classification
**Purpose:** Combine patterns from multiple sites to identify industry norms

**Input:** 10-50 analyzed sites per industry
**Output:** Aggregated preset with confidence scores

**Process:**
```
Site 1: [HERO, PRODUCT_GRID, ABOUT, FOOTER] → Pattern A
Site 2: [HERO, CATEGORY_SPLIT, PRODUCTS, FOOTER] → Pattern B
Site 3: [HERO, PRODUCT_GRID, VALUES, FOOTER] → Pattern A variant
...
Site 10: [HERO, PRODUCT_GRID, ABOUT, NEWSLETTER, FOOTER] → Pattern A extended

Aggregation:
- 7/10 sites use Pattern A (PRODUCT_GRID)
- 3/10 sites use Pattern B (CATEGORY_SPLIT)
- Confidence: 70% for Pattern A, 30% for Pattern B
- Recommendation: Default to Pattern A, offer Pattern B as alternative
```

**Storage Schema (Supabase):**
```sql
-- Table: analyzed_sites
CREATE TABLE analyzed_sites (
  id UUID PRIMARY KEY,
  url TEXT NOT NULL,
  industry TEXT NOT NULL,
  analyzed_at TIMESTAMP DEFAULT NOW(),
  screenshot_url TEXT,
  pattern_data JSONB,  -- Full extracted pattern
  quality_score INTEGER,  -- Awwwards score, manual rating, etc.
  source TEXT  -- 'awwwards', 'manual_curated', 'trending'
);

-- Table: industry_presets
CREATE TABLE industry_presets (
  id UUID PRIMARY KEY,
  industry TEXT UNIQUE NOT NULL,
  version INTEGER DEFAULT 1,
  preset_yaml TEXT,  -- Complete preset configuration
  confidence_score FLOAT,  -- 0.0-1.0 based on # sites analyzed
  sites_analyzed INTEGER,
  last_updated TIMESTAMP,
  patterns_breakdown JSONB  -- Stats like "70% use warm colors"
);

-- Table: pattern_components
CREATE TABLE pattern_components (
  id UUID PRIMARY KEY,
  component_type TEXT,  -- 'section_sequence', 'color_palette', 'typography'
  industry TEXT,
  pattern_data JSONB,
  frequency_score FLOAT,  -- How often this pattern appears
  quality_score FLOAT,  -- Average quality of sites using this pattern
  examples JSONB  -- URLs of sites using this pattern
);
```

---

### Layer 3: Continuous Learning Pipeline
**Purpose:** Automatically update pattern library as new sites emerge

**Scheduled Jobs:**
```
Daily:
  - Scrape Awwwards "Site of the Day" (across all categories)
  - Analyze new entries
  - Update pattern_components table
  - Flag significant pattern shifts (e.g., "90% of new SaaS sites now use brutalist design")

Weekly:
  - Regenerate all industry_presets from updated pattern data
  - Increment version numbers
  - Archive old presets for comparison

Monthly:
  - Deep analysis of pattern trends
  - Generate "Design Trend Report" (e.g., "Brutalism rising in SaaS, Earth tones dominating food")
  - Identify emerging industries needing new presets
```

---

## THE 20 INDUSTRIES (MVP Scope)

### **Tier 1: E-commerce (8 industries)**
1. **artisan-food** - Coffee, chocolate, bakery, specialty foods
2. **fashion-apparel** - Clothing, accessories, streetwear, luxury
3. **beauty-cosmetics** - Skincare, makeup, wellness products
4. **home-lifestyle** - Furniture, decor, kitchenware
5. **sports-fitness** - Equipment, apparel, supplements
6. **jewelry-watches** - Luxury, handcrafted, minimalist
7. **pet-products** - Premium pet food, accessories
8. **outdoor-adventure** - Camping, hiking, surf gear

### **Tier 2: Services (6 industries)**
9. **saas-tech** - B2B software, productivity tools, dev tools
10. **professional-services** - Consulting, agencies, law firms
11. **real-estate** - Residential, commercial, luxury properties
12. **health-wellness** - Clinics, fitness studios, spas
13. **education** - Online courses, coaching, learning platforms
14. **creative-studios** - Design agencies, photography, video production

### **Tier 3: Local/Community (6 industries)**
15. **restaurants-cafes** - Fine dining, casual, specialty cuisine
16. **hotels-hospitality** - Boutique hotels, vacation rentals
17. **events-venues** - Weddings, conferences, coworking spaces
18. **nonprofits-social** - Causes, foundations, community organizations
19. **construction-trades** - Contractors, architects, home services
20. **medical-dental** - Practices, clinics, specialists

---

## DATA SOURCES (Curated Site Lists)

### Primary Sources:
1. **Awwwards.com** - Industry-leading design showcase
   - Categories: E-commerce, Portfolio, Services, etc.
   - Quality filter: "Site of the Day" or >7.0 rating
   - ~10-15 sites per industry

2. **Commerce Cream** - E-commerce specific (Tiers 1)
   - Curated Shopify/e-commerce excellence
   - ~5-10 sites per e-commerce industry

3. **SaaS Landing Pages** - SaaS/Tech specific (Tier 2)
   - saaslandingpage.com, landingfolio.com
   - ~10 sites for SaaS category

4. **Manual Curation** - Domain expert picks
   - Industry leaders (e.g., Shopify.com for e-commerce)
   - Emerging innovators
   - ~5 sites per industry

**Total per industry:** 10-30 analyzed sites for MVP

---

## MVP BUILD PLAN (3-Week Timeline)

### **Week 1: Core Extraction System**

**Day 1-2: Pattern Extraction Engine**
```python
# scripts/extract-pattern.py

Deliverables:
✅ Playwright integration (screenshot + DOM capture)
✅ Claude Vision API integration (pattern recognition)
✅ CSS computed styles extraction
✅ Section classifier (HERO, PRODUCT_GRID, etc.)
✅ Output: pattern.yaml per analyzed site

Test: Analyze 5 sites (Shopify, Allbirds, Aesop, Stripe, Notion)
Validate: Manual review of extracted patterns for accuracy
```

**Day 3-4: Supabase Schema + Integration**
```sql
Deliverables:
✅ Database schema (analyzed_sites, industry_presets, pattern_components)
✅ Storage API wrapper (Python client)
✅ Pattern upload function (save analyzed site to DB)
✅ Query functions (get patterns by industry)

Test: Store 10 analyzed sites across 3 industries
Validate: Query aggregation works correctly
```

**Day 5-7: Aggregation Logic**
```python
# scripts/aggregate-patterns.py

Deliverables:
✅ Pattern frequency calculator (70% use PRODUCT_GRID)
✅ Confidence scoring (based on # sites + agreement)
✅ Preset YAML generator (from aggregated patterns)
✅ Comparison reports (Pattern A vs Pattern B performance)

Test: Generate preset for "artisan-food" from 10 analyzed sites
Validate: Preset matches manual expectations, high confidence score
```

---

### **Week 2: Data Collection + Initial Presets**

**Day 1-3: Bulk Site Analysis**
```bash
# Analyze 200 sites total (10 per industry × 20 industries)

python scripts/bulk-analyze.py --source awwwards --industries all --limit 10

Deliverables:
✅ 200 analyzed sites in database
✅ Screenshots + patterns stored
✅ Quality scores captured (Awwwards ratings)

Automated process:
1. Scrape Awwwards category pages
2. For each site: extract pattern → store to DB
3. Progress tracking + error handling
4. Rate limiting (respect Awwwards ToS)
```

**Day 4-5: Preset Generation**
```bash
# Generate initial 20 industry presets

python scripts/generate-presets.py --industries all --min-sites 8

Deliverables:
✅ 20 industry preset YAMLs (presets/fashion.yaml, presets/saas.yaml, etc.)
✅ Confidence scores per preset (0.6-0.9 range for MVP)
✅ Pattern breakdown reports (what % use each pattern)

Output structure:
presets/
  ├── artisan-food.yaml (confidence: 0.85, 12 sites analyzed)
  ├── fashion-apparel.yaml (confidence: 0.78, 10 sites analyzed)
  ├── saas-tech.yaml (confidence: 0.82, 11 sites analyzed)
  └── ...
```

**Day 6-7: Validation + Refinement**
```bash
# Test-generate sites using new presets

python scripts/orchestrate.py test-brand --preset fashion --validate
python scripts/orchestrate.py test-brand --preset saas --validate

Deliverables:
✅ Visual comparison: generated vs. reference sites
✅ Refinement of presets where confidence < 0.75
✅ Manual override system (preserve artisan-food manual preset if better)
```

---

### **Week 3: Automation + Continuous Learning**

**Day 1-3: Scheduled Analysis Jobs**
```python
# scripts/scheduled-jobs.py

Deliverables:
✅ Daily job: Scrape Awwwards "Site of the Day"
✅ Weekly job: Regenerate presets from updated patterns
✅ Trend detection: Identify emerging patterns (e.g., brutalism surge)
✅ Notification system: Alert when preset confidence drops

Deployment:
- GitHub Actions workflow (runs daily at 2am UTC)
- OR Vercel Cron (serverless function)
- OR Railway scheduled job
```

**Day 4-5: Pattern Recommendation Engine**
```python
# scripts/recommend-preset.py

Input: User description ("I need a site for my coffee roastery")
Output: Matched preset + confidence + alternatives

Deliverables:
✅ Intent matcher (coffee roastery → artisan-food)
✅ Confidence scorer (how well input matches preset)
✅ Alternative suggestions (also consider: specialty-food, restaurants-cafes)

Integration point: Frontend UI for preset selection
```

**Day 6-7: Documentation + Handoff**
```markdown
Deliverables:
✅ PATTERN_LIBRARY.md (how the system works)
✅ PRESET_SCHEMA.md (YAML structure documentation)
✅ API_REFERENCE.md (Supabase queries, Python functions)
✅ MAINTENANCE.md (how to add new industries, update patterns)

Final test: Generate 5 sites across 5 industries, validate quality
```

---

## SUCCESS METRICS

### **MVP Launch Criteria (End of Week 3):**
- ✅ 200+ sites analyzed and stored
- ✅ 20 industry presets generated (confidence > 0.70)
- ✅ Automated daily analysis running
- ✅ 95%+ pattern extraction accuracy (manual validation)
- ✅ Generated sites visually comparable to reference sites

### **Quality Gates:**
- Pattern extraction must correctly identify section types (90% accuracy)
- Color palette extraction must match visual inspection (±10% hue tolerance)
- Typography detection must identify font families correctly (85% accuracy)
- Section sequence must match actual site structure (95% accuracy)

### **Performance Targets:**
- Site analysis: <60 seconds per site
- Preset generation: <5 minutes for all 20 industries
- Database query: <500ms for preset retrieval
- Bulk analysis: 100 sites in <2 hours

---

## INTEGRATION WITH CURRENT SYSTEM (Zero Breaking Changes)

### **Current Flow (Preserved):**
```
User input → Select preset → Generate sections → Assemble → Deploy
```

### **Enhanced Flow (Additive):**
```
User input → Match to industry → Query pattern library → Get preset
                                      ↓
                            (Auto-generated from 10-30 analyzed sites)
                                      ↓
                             Final preset (YAML)
                                      ↓
                          Generate sections → Assemble → Deploy
```

**Critical Constraint:** Orchestrator receives the SAME preset YAML format. It doesn't know or care if preset was hand-crafted or auto-generated.

**Fallback Strategy:** If pattern library fails, use manually-crafted presets (artisan-food.yaml still works).

---

## FILE STRUCTURE (New Components)

```
website-builder/
├── scripts/
│   ├── extract-pattern.py          # NEW: Analyze single URL
│   ├── bulk-analyze.py              # NEW: Analyze batch of URLs
│   ├── aggregate-patterns.py        # NEW: Generate presets from patterns
│   ├── scheduled-jobs.py            # NEW: Daily/weekly automation
│   ├── recommend-preset.py          # NEW: Match user intent to preset
│   └── orchestrate.py               # EXISTING: Unchanged
│
├── lib/
│   ├── pattern-extractor.py         # NEW: Core extraction logic
│   ├── supabase-client.py           # NEW: Database integration
│   ├── preset-generator.py          # NEW: YAML generation from patterns
│   └── claude-vision.py             # NEW: Vision API wrapper
│
├── presets/
│   ├── artisan-food.yaml            # EXISTING: Manual (preserved)
│   ├── fashion.yaml                 # NEW: Auto-generated
│   ├── saas.yaml                    # NEW: Auto-generated
│   └── ...                          # NEW: 19 more industries
│
├── data/
│   ├── analyzed-sites/              # NEW: Stored pattern YAMLs
│   │   ├── shopify-com.yaml
│   │   ├── allbirds-com.yaml
│   │   └── ...
│   └── reports/                     # NEW: Trend analysis reports
│
└── docs/
    ├── PATTERN_LIBRARY.md           # NEW: System documentation
    ├── PRESET_SCHEMA.md             # NEW: YAML format spec
    └── MAINTENANCE.md               # NEW: Operations guide
```

---

## DEPENDENCIES (New Packages Required)

```json
{
  "dependencies": {
    "playwright": "^1.41.0",           // Headless browser
    "anthropic": "^0.29.0",            // Claude Vision API
    "@supabase/supabase-js": "^2.39.0", // Database client
    "js-yaml": "^4.1.0",               // YAML parsing
    "sharp": "^0.33.0",                // Image processing
    "cheerio": "^1.0.0-rc.12",         // HTML parsing
    "axios": "^1.6.5"                  // HTTP requests
  }
}
```

**Infrastructure:**
- Supabase (free tier: 500MB database, 2GB bandwidth) - Pattern storage
- GitHub Actions (free tier: 2000 min/month) - Scheduled jobs
- Cloudinary (free tier: 25GB bandwidth) - Screenshot storage

**Total added cost:** $0/month (within free tiers for MVP)

---

## RISK MITIGATION

### **Risk 1: Pattern Extraction Accuracy**
- **Mitigation:** Manual validation sample (10% of analyzed sites)
- **Fallback:** Human-in-the-loop correction for low-confidence patterns
- **Threshold:** Reject patterns with <70% confidence, flag for manual review

### **Risk 2: Awwwards Rate Limiting / Blocking**
- **Mitigation:** Respectful scraping (1 request per 5 seconds, robots.txt compliant)
- **Fallback:** Manual curation of site lists if scraping blocked
- **Alternative:** Partner with Awwwards (API access request)

### **Risk 3: Design Trends Shift Too Fast**
- **Mitigation:** Weekly preset regeneration, version tracking
- **Fallback:** Preserve high-confidence presets even if trends shift
- **Strategy:** Offer "classic" vs. "trending" preset variants

### **Risk 4: Industry Classification Ambiguity**
- **Example:** Is a coffee subscription service "artisan-food" or "saas-tech"?
- **Mitigation:** Multi-tag system (site can be in 2 industries)
- **Fallback:** User can manually override preset selection

---

## POST-MVP EXPANSION (Month 2-3)

### **Phase 2 Features:**
1. **Component-level extraction** - Not just sections, but reusable components (buttons, cards, forms)
2. **A/B variant generation** - Generate 3 style variants per industry for testing
3. **Performance scoring** - Track which patterns correlate with better Lighthouse scores
4. **User feedback loop** - "This preset worked well" → Boost confidence score
5. **Custom pattern upload** - Users can submit their own reference sites

### **Phase 3 Features:**
1. **Cross-industry pattern migration** - "SaaS hero style applied to e-commerce"
2. **AI-suggested innovations** - "Most coffee sites use warm tones, but cool minimal is trending in luxury coffee"
3. **Real-time trend alerts** - "Brutalism just hit 40% adoption in SaaS"
4. **Pattern marketplace** - Sell premium analyzed patterns to other users

---

## BUILD AGENT DIRECTIVE

**To the Claude agent building this system:**

Your task is to implement the **Pattern Library System MVP** as specified above. Follow this directive:

1. **Read the specification completely** before writing any code
2. **Start with Week 1, Day 1-2** (pattern extraction engine) - this is the foundation
3. **Test each component** before moving to the next (don't build everything then debug)
4. **Preserve the current orchestration system** - your changes are ADDITIVE only
5. **Use the exact file structure** specified above
6. **Follow the YAML schema** from existing artisan-food.yaml
7. **Prioritize accuracy over speed** - a slow, correct system beats a fast, wrong one
8. **Document as you build** - future maintainers need to understand this

**Your first output should be:**
```python
# scripts/extract-pattern.py
# COMPLETE, WORKING implementation of pattern extraction
# Include: Playwright setup, Claude Vision integration, YAML output
# Test it on: https://www.shopify.com before proceeding
```

**Do not proceed to Day 3-4 until Day 1-2 is validated working.**

Build autonomously. Ask for human review only when:
- Accuracy falls below 85% on test sites
- External API fails repeatedly (Playwright, Claude, Supabase)
- YAML schema needs adjustment from original artisan-food.yaml

**Build with the lazy principle:** Work hard now on this system so pattern extraction is autonomous forever.

---

**END OF SPECIFICATION**


