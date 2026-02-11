'use strict';

/**
 * Animation Detection Module
 * Detects animation libraries, CSS animations, scroll-triggered animations,
 * and animation assets on web pages during Playwright extraction.
 * Uses browser-injected scripts and network interception to gather evidence,
 * then scores animation intensity and infers the animation engine.
 */

/**
 * Returns a JS string for page.addInitScript() that monkey-patches
 * IntersectionObserver to track registrations before any page code runs.
 * @returns {string} Script source to inject pre-navigation
 */
function getPreNavigationScript() {
  return `
    window.__wb_animation_data = { intersectionObservers: [] };
    const OriginalIO = window.IntersectionObserver;
    window.__wb_animation_data.originalIO = OriginalIO;
    window.IntersectionObserver = function(callback, options) {
      const entry = {
        threshold: options?.threshold || 0,
        rootMargin: options?.rootMargin || '0px',
        targetCount: 0
      };
      window.__wb_animation_data.intersectionObservers.push(entry);
      const observer = new OriginalIO(callback, options);
      const origObserve = observer.observe.bind(observer);
      observer.observe = function(target) {
        entry.targetCount++;
        return origObserve(target);
      };
      return observer;
    };
    window.IntersectionObserver.prototype = OriginalIO.prototype;

    // GSAP Runtime Interception
    window.__wb_gsap_calls = [];
    window.__wb_gsap_timeline_id = 0;

    function __wb_captureTarget(target) {
      if (typeof target === 'string') return target;
      if (target instanceof Element) {
        return target.className ? '.' + target.className.split(' ')[0] : target.tagName.toLowerCase();
      }
      if (target instanceof NodeList || Array.isArray(target)) {
        const first = target[0];
        if (first instanceof Element) {
          return first.className ? '.' + first.className.split(' ')[0] : first.tagName.toLowerCase();
        }
      }
      return null;
    }

    function __wb_captureVars(vars) {
      if (!vars || typeof vars !== 'object') return {};
      const keep = ['y','x','opacity','scale','scaleX','scaleY','rotation','rotateX','rotateY',
                    'duration','ease','stagger','delay','transformOrigin'];
      const result = {};
      for (const k of keep) {
        if (vars[k] !== undefined) result[k] = vars[k];
      }
      return result;
    }

    function __wb_captureScrollTrigger(vars) {
      if (!vars || !vars.scrollTrigger) return null;
      const st = typeof vars.scrollTrigger === 'object' ? vars.scrollTrigger : {};
      return {
        trigger: typeof st.trigger === 'string' ? st.trigger : null,
        start: st.start || null,
        end: st.end || null,
        scrub: st.scrub || false,
        pin: st.pin || false,
        once: st.once !== undefined ? st.once : null
      };
    }

    function __wb_getElementY(target) {
      try {
        const el = typeof target === 'string' ? document.querySelector(target) :
                   (target instanceof Element ? target : null);
        if (el) {
          const rect = el.getBoundingClientRect();
          return rect.top + window.scrollY + rect.height / 2;
        }
      } catch(e) {}
      return null;
    }

    function __wb_wrapGsap(gsapInstance) {
      const methods = ['from', 'to', 'fromTo'];
      for (const method of methods) {
        const orig = gsapInstance[method].bind(gsapInstance);
        gsapInstance[method] = function(target, vars, vars2) {
          if (window.__wb_gsap_calls.length < 200) {
            const record = {
              method: method,
              targetSelector: __wb_captureTarget(target),
              vars: __wb_captureVars(method === 'fromTo' ? vars2 : vars),
              duration: (method === 'fromTo' ? vars2 : vars)?.duration || null,
              ease: (method === 'fromTo' ? vars2 : vars)?.ease || null,
              stagger: (method === 'fromTo' ? vars2 : vars)?.stagger || null,
              delay: (method === 'fromTo' ? vars2 : vars)?.delay || null,
              scrollTrigger: __wb_captureScrollTrigger(method === 'fromTo' ? vars2 : vars),
              timelineId: null,
              elementY: __wb_getElementY(target),
              source: 'runtime'
            };
            window.__wb_gsap_calls.push(record);
          }
          return orig(target, vars, vars2);
        };
      }

      // Wrap timeline creation
      const origTimeline = gsapInstance.timeline.bind(gsapInstance);
      gsapInstance.timeline = function(defaults) {
        const tl = origTimeline(defaults);
        const tlId = 'tl_' + (window.__wb_gsap_timeline_id++);
        const scrollTrigger = __wb_captureScrollTrigger(defaults || {});

        for (const method of ['from', 'to', 'fromTo']) {
          const origMethod = tl[method].bind(tl);
          tl[method] = function(target, vars, vars2, position) {
            if (window.__wb_gsap_calls.length < 200) {
              const actualVars = method === 'fromTo' ? vars2 : vars;
              window.__wb_gsap_calls.push({
                method: 'timeline.' + method,
                targetSelector: __wb_captureTarget(target),
                vars: __wb_captureVars(actualVars),
                duration: actualVars?.duration || (defaults?.defaults?.duration) || null,
                ease: actualVars?.ease || (defaults?.defaults?.ease) || null,
                stagger: actualVars?.stagger || null,
                delay: typeof (method === 'fromTo' ? position : (vars2 || position)) === 'string' ?
                       (method === 'fromTo' ? position : (vars2 || position)) : null,
                scrollTrigger: scrollTrigger,
                timelineId: tlId,
                elementY: __wb_getElementY(target),
                source: 'runtime'
              });
            }
            return origMethod(target, vars, vars2, position);
          };
        }

        return tl;
      };

      return gsapInstance;
    }

    // Use Object.defineProperty to intercept GSAP assignment (handles late/async loading)
    Object.defineProperty(window, 'gsap', {
      configurable: true,
      enumerable: true,
      set: function(val) {
        window.__wb_gsap_real = __wb_wrapGsap(val);
      },
      get: function() {
        return window.__wb_gsap_real;
      }
    });
  `;
}

/**
 * Attaches a response handler to a Playwright page that collects animation-
 * related network assets: Lottie JSON, Rive files, 3D assets, and CSS files.
 * @param {import('playwright').Page} page - Playwright page instance
 * @returns {Promise<Function>} Getter that returns collected network results
 */
async function setupNetworkInterception(page) {
  const networkResults = { lottieFiles: [], riveFiles: [], threeDFiles: [], cssFiles: [], jsFiles: [] };

  page.on('response', async (response) => {
    try {
      const url = response.url();
      const contentType = response.headers()['content-type'] || '';

      if (url.endsWith('.riv')) {
        networkResults.riveFiles.push(url);
      } else if (url.endsWith('.glb') || url.endsWith('.gltf')) {
        networkResults.threeDFiles.push(url);
      } else if (url.endsWith('.css') || contentType.includes('text/css')) {
        networkResults.cssFiles.push(url);
      } else if ((url.endsWith('.js') || contentType.includes('javascript')) &&
                 !url.includes('analytics') && !url.includes('gtag') && !url.includes('gtm')) {
        const contentLength = parseInt(response.headers()['content-length'] || '0', 10);
        if (contentLength === 0 || contentLength <= 2 * 1024 * 1024) {
          networkResults.jsFiles.push(url);
        }
      } else if (contentType.includes('application/json') || url.endsWith('.json')) {
        try {
          const body = await response.text();
          if (body.length < 5_000_000) {
            const parsed = JSON.parse(body);
            if (parsed.v !== undefined && parsed.fr !== undefined && parsed.layers) {
              networkResults.lottieFiles.push({ url, name: parsed.nm || '' });
            }
          }
        } catch (_) { /* not JSON or too large */ }
      }
    } catch (_) { /* response may have been aborted */ }
  });

  return () => networkResults;
}

/**
 * Returns a JS string to inject via page.evaluate() after page load but
 * before scrolling. Sets up a MutationObserver that tracks class and style
 * attribute changes on document.body subtree during scroll.
 * @returns {string} Script source to inject post-load
 */
function getMutationObserverScript() {
  return `
    window.__wb_scroll_mutations = { classChanges: [], styleChanges: 0 };
    const seenClasses = new Set();
    const mutObs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === 'attributes') {
          if (m.attributeName === 'class') {
            const newClasses = m.target.className?.toString?.() || '';
            const oldClasses = m.oldValue || '';
            const added = newClasses.split(/\\s+/).filter(c => c && !oldClasses.includes(c));
            for (const c of added) {
              if (!seenClasses.has(c)) {
                seenClasses.add(c);
                window.__wb_scroll_mutations.classChanges.push(c);
              }
            }
          } else if (m.attributeName === 'style') {
            window.__wb_scroll_mutations.styleChanges++;
          }
        }
      }
    });
    mutObs.observe(document.body, {
      attributes: true,
      attributeOldValue: true,
      subtree: true,
      attributeFilter: ['class', 'style']
    });
  `;
}

/**
 * Collects animation evidence from the page via page.evaluate(). Detects
 * global animation libraries, CSS keyframes, scroll attributes,
 * IntersectionObserver data, and MutationObserver data.
 * @param {import('playwright').Page} page - Playwright page instance
 * @returns {Promise<Object>} Raw animation evidence from the page
 */
async function extractAnimationData(page) {
  return page.evaluate(() => {
    const result = {
      libraries: [],
      cssKeyframes: [],
      animatedElementCount: 0,
      transitionElementCount: 0,
      scrollAttributes: { aos: 0, scroll: 0, parallax: 0 },
      intersectionObservers: [],
      scrollMutations: { classChanges: [], styleChanges: 0 },
      scriptPatterns: [],
      gsapCalls: [],
      lottieElements: [],
      gsapPlugins: [],
    };

    // --- A) GSAP core + all plugins (window globals) ---
    const GSAP_PLUGINS = [
      { name: 'GSAP',            test: () => !!window.gsap, via: 'window.gsap' },
      { name: 'ScrollTrigger',   test: () => !!window.ScrollTrigger, via: 'window.ScrollTrigger' },
      { name: 'ScrollSmoother',  test: () => !!window.ScrollSmoother, via: 'window.ScrollSmoother' },
      { name: 'ScrollTo',       test: () => !!(window.gsap && window.gsap.plugins && window.gsap.plugins.scrollTo), via: 'window.gsap.plugins.scrollTo' },
      { name: 'SplitText',      test: () => !!window.SplitText, via: 'window.SplitText' },
      { name: 'ScrambleText',   test: () => !!window.ScrambleTextPlugin, via: 'window.ScrambleTextPlugin' },
      { name: 'TextPlugin',     test: () => !!window.TextPlugin, via: 'window.TextPlugin' },
      { name: 'DrawSVG',        test: () => !!window.DrawSVGPlugin, via: 'window.DrawSVGPlugin' },
      { name: 'MorphSVG',       test: () => !!window.MorphSVGPlugin, via: 'window.MorphSVGPlugin' },
      { name: 'MotionPath',     test: () => !!window.MotionPathPlugin, via: 'window.MotionPathPlugin' },
      { name: 'Flip',           test: () => !!window.Flip, via: 'window.Flip' },
      { name: 'Draggable',      test: () => !!window.Draggable, via: 'window.Draggable' },
      { name: 'Inertia',        test: () => !!window.InertiaPlugin, via: 'window.InertiaPlugin' },
      { name: 'Observer',       test: () => !!window.Observer, via: 'window.Observer' },
      { name: 'Physics2D',      test: () => !!window.Physics2DPlugin, via: 'window.Physics2DPlugin' },
      { name: 'PhysicsProps',   test: () => !!window.PhysicsPropsPlugin, via: 'window.PhysicsPropsPlugin' },
      { name: 'CustomEase',     test: () => !!window.CustomEase, via: 'window.CustomEase' },
      { name: 'CustomWiggle',   test: () => !!window.CustomWiggle, via: 'window.CustomWiggle' },
      { name: 'CustomBounce',   test: () => !!window.CustomBounce, via: 'window.CustomBounce' },
      { name: 'GSDevTools',     test: () => !!window.GSDevTools, via: 'window.GSDevTools' },
    ];

    for (const p of GSAP_PLUGINS) {
      try {
        if (p.test()) {
          result.libraries.push({
            name: p.name,
            confidence: 0.9,
            detectedVia: p.via,
          });
          result.gsapPlugins.push(p.name);
        }
      } catch (_) { /* skip failed checks */ }
    }

    // --- A2) Other global library detection (non-GSAP) ---
    const libraryChecks = [
      {
        name: 'Framer Motion',
        test: () => !!document.querySelector('[data-projection-id]'),
        via: 'DOM [data-projection-id]',
      },
      {
        name: 'Lottie',
        test: () => !!window.lottie || !!window.bodymovin ||
          !!document.querySelector('lottie-player, dotlottie-player'),
        via: window.lottie || window.bodymovin ? 'window.lottie/bodymovin' : 'DOM lottie-player',
      },
      {
        name: 'Three.js',
        test: () => !!window.THREE ||
          !!document.querySelector('canvas')?.getContext?.('webgl'),
        via: window.THREE ? 'window.THREE' : 'canvas WebGL',
      },
      {
        name: 'Spline',
        test: () => !!document.querySelector('spline-viewer, [data-spline]'),
        via: 'DOM spline-viewer/[data-spline]',
      },
      {
        name: 'AOS',
        test: () => !!window.AOS || !!document.querySelector('[data-aos]'),
        via: window.AOS ? 'window.AOS' : 'DOM [data-aos]',
      },
      {
        name: 'Locomotive Scroll',
        test: () => !!window.LocomotiveScroll || !!document.querySelector('[data-scroll]'),
        via: window.LocomotiveScroll ? 'window.LocomotiveScroll' : 'DOM [data-scroll]',
      },
      {
        name: 'Anime.js',
        test: () => !!window.anime,
        via: 'window.anime',
      },
      {
        name: 'Rive',
        test: () => !!document.querySelector('rive-canvas, canvas[data-rive]'),
        via: 'DOM rive-canvas/canvas[data-rive]',
      },
    ];

    for (const check of libraryChecks) {
      try {
        if (check.test()) {
          result.libraries.push({
            name: check.name,
            confidence: 0.9,
            detectedVia: check.via,
          });
        }
      } catch (_) { /* skip failed checks */ }
    }

    // --- B) CSS animation data from CSSOM ---
    try {
      for (const sheet of document.styleSheets) {
        try {
          const rules = sheet.cssRules || sheet.rules;
          if (!rules) continue;
          for (const rule of rules) {
            if (rule instanceof CSSKeyframesRule) {
              result.cssKeyframes.push({
                name: rule.name,
                body: rule.cssText.slice(0, 500)
              });
            }
          }
        } catch (_) { /* cross-origin stylesheet, skip */ }
      }
    } catch (_) { /* no stylesheets */ }

    // Count elements with active animations or transitions
    try {
      const allElements = document.querySelectorAll('*');
      for (const el of allElements) {
        const style = window.getComputedStyle(el);
        if (style.animationName && style.animationName !== 'none') {
          result.animatedElementCount++;
        }
        if (style.transitionProperty && style.transitionProperty !== 'all' &&
            style.transitionProperty !== 'none') {
          result.transitionElementCount++;
        }
      }
    } catch (_) { /* skip */ }

    // --- C) Scroll-related attributes ---
    result.scrollAttributes.aos = document.querySelectorAll('[data-aos]').length;
    result.scrollAttributes.scroll =
      document.querySelectorAll('[data-scroll], [data-scroll-speed]').length;
    result.scrollAttributes.parallax = document.querySelectorAll('[data-parallax]').length;

    // --- D) IntersectionObserver data ---
    if (window.__wb_animation_data?.intersectionObservers) {
      result.intersectionObservers = window.__wb_animation_data.intersectionObservers;
    }

    // --- E) MutationObserver data ---
    if (window.__wb_scroll_mutations) {
      result.scrollMutations = {
        classChanges: window.__wb_scroll_mutations.classChanges || [],
        styleChanges: window.__wb_scroll_mutations.styleChanges || 0,
      };
    }

    // --- F) Script tag pattern matching ---
    const scriptPatterns = [
      { library: 'GSAP', pattern: /gsap|GreenSock/i },
      { library: 'Framer Motion', pattern: /framer-motion/i },
      { library: 'Lottie', pattern: /lottie-web|bodymovin/i },
      { library: 'Three.js', pattern: /THREE\.REVISION/i },
      { library: 'Spline', pattern: /splinetool/i },
      { library: 'Anime.js', pattern: /anime/i },
      { library: 'Rive', pattern: /@rive-app/i },
    ];

    const gsapPluginPatterns = [
      { plugin: 'SplitText',     pattern: /SplitText/i },
      { plugin: 'MorphSVG',     pattern: /MorphSVG/i },
      { plugin: 'DrawSVG',      pattern: /DrawSVG/i },
      { plugin: 'Flip',         pattern: /\bFlip\b/ },
      { plugin: 'Draggable',    pattern: /\bDraggable\b/ },
      { plugin: 'MotionPath',   pattern: /MotionPath/i },
      { plugin: 'CustomEase',   pattern: /CustomEase/i },
      { plugin: 'ScrollSmoother', pattern: /ScrollSmoother/i },
      { plugin: 'Observer',     pattern: /\bObserver\b/ },
      { plugin: 'ScrambleText', pattern: /ScrambleText/i },
      { plugin: 'Inertia',      pattern: /InertiaPlugin/i },
      { plugin: 'Physics2D',    pattern: /Physics2DPlugin/i },
    ];

    const gsapPluginsSeen = new Set(result.gsapPlugins);

    for (const script of document.scripts) {
      const src = script.src || '';
      const content = (script.textContent || script.innerHTML || '');
      for (const sp of scriptPatterns) {
        if (sp.pattern.test(src)) {
          result.scriptPatterns.push({ library: sp.library, src: src || 'inline' });
        }
      }
      for (const gp of gsapPluginPatterns) {
        if (gp.pattern.test(src) || gp.pattern.test(content)) {
          result.scriptPatterns.push({ library: gp.plugin, src: src || 'inline' });
          if (!gsapPluginsSeen.has(gp.plugin)) {
            gsapPluginsSeen.add(gp.plugin);
            result.gsapPlugins.push(gp.plugin);
          }
        }
      }
    }

    // --- G) Runtime-captured GSAP calls ---
    if (window.__wb_gsap_calls && window.__wb_gsap_calls.length > 0) {
      result.gsapCalls = window.__wb_gsap_calls;
    }

    // --- H) Lottie element positions ---
    result.lottieElements = [];
    try {
      const lottieSelectors = 'lottie-player, dotlottie-player, [data-lottie], canvas[data-animation-url]';
      const lottiePlayers = document.querySelectorAll(lottieSelectors);
      for (const el of lottiePlayers) {
        const rect = el.getBoundingClientRect();
        const src = el.src || el.getAttribute('src') || el.getAttribute('data-src') ||
                    el.getAttribute('data-animation-url') || '';
        result.lottieElements.push({
          url: src,
          elementY: rect.top + window.scrollY + rect.height / 2,
          width: rect.width,
          height: rect.height
        });
      }
    } catch(_) {}

    return result;
  });
}

/**
 * Pure analysis function (no browser access). Scores animation intensity,
 * infers the animation engine, and produces section-level overrides from
 * the raw evidence gathered by extractAnimationData and setupNetworkInterception.
 * @param {Object} evidence - Output from extractAnimationData
 * @param {Object} networkResults - Output from the setupNetworkInterception getter
 * @param {Array} sections - Extracted sections array
 * @param {Array} renderedDOM - Rendered DOM elements array
 * @returns {Object} Analyzed animation profile
 */
function analyzeAnimationEvidence(evidence, networkResults, sections, renderedDOM) {
  const libs = evidence.libraries || [];
  const gsapPlugins = evidence.gsapPlugins || [];
  const keyframes = evidence.cssKeyframes || [];
  const animatedEls = evidence.animatedElementCount || 0;
  const transitionEls = evidence.transitionElementCount || 0;
  const scrollAttrs = evidence.scrollAttributes || { aos: 0, scroll: 0, parallax: 0 };
  const ioData = evidence.intersectionObservers || [];
  const scrollMuts = evidence.scrollMutations || { classChanges: [], styleChanges: 0 };
  const scriptPats = evidence.scriptPatterns || [];
  const defaultNet = { lottieFiles: [], riveFiles: [], threeDFiles: [], cssFiles: [], jsFiles: [] };
  const net = Object.assign(defaultNet, networkResults || {});

  // --- Intensity scoring ---
  let score = 0;

  // +2 per detected library
  score += libs.length * 2;

  // +3 additional for GSAP or Framer Motion
  const hasGSAP = libs.some(l => l.name === 'GSAP');
  const hasFramer = libs.some(l => l.name === 'Framer Motion');
  if (hasGSAP) score += 3;
  if (hasFramer) score += 3;

  // +4 for rich animation assets (Lottie, Rive, 3D)
  const hasRichAssets = net.lottieFiles.length > 0 ||
    net.riveFiles.length > 0 || net.threeDFiles.length > 0;
  if (hasRichAssets) score += 4;

  // +0.5 per CSS keyframes rule
  score += keyframes.length * 0.5;

  // +0.2 per animated element
  score += animatedEls * 0.2;

  // +0.1 per transition element
  score += transitionEls * 0.1;

  // +1 per IntersectionObserver registration
  score += ioData.length * 1;

  // +0.3 per unique scroll mutation class
  score += (scrollMuts.classChanges?.length || 0) * 0.3;

  // +2 if any scroll-trigger attributes found
  const hasScrollAttrs = scrollAttrs.aos > 0 || scrollAttrs.scroll > 0 || scrollAttrs.parallax > 0;
  if (hasScrollAttrs) score += 2;

  // Map score to intensity level
  let level;
  if (score <= 2) level = 'none';
  else if (score <= 6) level = 'subtle';
  else if (score <= 14) level = 'moderate';
  else level = 'expressive';

  // --- Confidence based on distinct evidence types ---
  let distinctTypes = 0;
  if (libs.length > 0) distinctTypes++;
  if (keyframes.length > 0) distinctTypes++;
  if (animatedEls > 0) distinctTypes++;
  if (scrollAttrs.aos + scrollAttrs.scroll + scrollAttrs.parallax > 0) distinctTypes++;
  if (ioData.length > 0) distinctTypes++;
  if (net.lottieFiles.length + net.riveFiles.length + net.threeDFiles.length > 0) distinctTypes++;
  if ((scrollMuts.classChanges?.length || 0) > 0) distinctTypes++;

  const confidence = Math.min(1.0, distinctTypes / 5);

  // --- Engine inference ---
  let engine = 'css';
  if (hasGSAP) engine = 'gsap';
  else if (hasFramer) engine = 'framer-motion';

  // --- Section overrides ---
  const sectionOverrides = {};
  const safeSections = sections || [];
  const safeDOM = renderedDOM || [];

  for (const section of safeSections) {
    const sectionType = (section.type || section.sectionType || '').toUpperCase();
    const sectionId = section.id || section.sectionId || sectionType;

    // Find rendered DOM elements that belong to this section
    const sectionElements = safeDOM.filter(el => {
      const elSection = (el.section || el.sectionType || '').toUpperCase();
      return elSection === sectionType;
    });

    for (const el of sectionElements) {
      const classes = (el.className || el.classes || '').toLowerCase();
      const attrs = el.attributes || {};
      const dataAttrs = Object.keys(attrs).filter(k => k.startsWith('data-'));

      // Count-up / counter detection for STATS sections
      if (sectionType.includes('STAT') || sectionType.includes('NUMBER') ||
          sectionType.includes('METRIC')) {
        if (/count[-_]?up|counter|odometer/i.test(classes)) {
          sectionOverrides[sectionId] = sectionOverrides[sectionId] || {};
          sectionOverrides[sectionId].animation = 'count-up';
        }
      }

      // Character reveal for HERO sections
      if (sectionType.includes('HERO')) {
        if (/reveal|char[-_]?reveal|split[-_]?text|fade[-_]?in/i.test(classes)) {
          sectionOverrides[sectionId] = sectionOverrides[sectionId] || {};
          sectionOverrides[sectionId].animation = 'character-reveal';
        }
      }

      // Parallax detection for any section
      if (dataAttrs.includes('data-parallax') || /parallax/i.test(classes)) {
        sectionOverrides[sectionId] = sectionOverrides[sectionId] || {};
        sectionOverrides[sectionId].animation = 'parallax';
      }
    }
  }

  // --- Merge script patterns into library list for completeness ---
  const libNames = new Set(libs.map(l => l.name));
  const mergedLibraries = [...libs];
  for (const sp of scriptPats) {
    if (!libNames.has(sp.library)) {
      libNames.add(sp.library);
      mergedLibraries.push({
        name: sp.library,
        version: null,
        confidence: 0.7,
      });
    }
  }

  // --- Per-section animation grouping ---
  const gsapCalls = evidence.gsapCalls || [];
  const lottieElements = evidence.lottieElements || [];
  const perSection = groupAnimationsBySection(gsapCalls, lottieElements, keyframes, safeSections);

  return {
    libraries: mergedLibraries.map(l => ({
      name: l.name,
      version: l.version || null,
      confidence: l.confidence,
    })),
    intensity: { level, score: Math.round(score * 10) / 10, confidence },
    engine,
    cssAnimations: {
      keyframes: keyframes.map(k => k.name),
      keyframeDetails: keyframes,
      animatedElements: animatedEls,
      transitionElements: transitionEls,
    },
    scrollAnimations: {
      triggerCount: scrollAttrs.aos + scrollAttrs.scroll + scrollAttrs.parallax,
      patterns: [
        ...(scrollAttrs.aos > 0 ? ['aos'] : []),
        ...(scrollAttrs.scroll > 0 ? ['data-scroll'] : []),
        ...(scrollAttrs.parallax > 0 ? ['data-parallax'] : []),
      ],
      observerCount: ioData.length,
    },
    assets: {
      lottie: net.lottieFiles,
      rive: net.riveFiles,
      threeD: net.threeDFiles,
    },
    sectionOverrides,
    perSection,
    gsapCallCount: gsapCalls.length,
    lottieElementCount: lottieElements.length,
    gsapPlugins,
  };
}

/**
 * Groups captured GSAP calls, Lottie elements, and CSS keyframes by section.
 * Uses element Y positions to map each animation to its containing section.
 *
 * @param {Array} gsapCalls - Merged GSAP calls (runtime + static)
 * @param {Array} lottieElements - Lottie player positions from extractAnimationData
 * @param {Array} cssKeyframes - CSS keyframe rules with bodies
 * @param {Array} sections - Section boundary rects from page extraction
 * @returns {Object} Per-section animation data keyed by section index
 */
function groupAnimationsBySection(gsapCalls, lottieElements, cssKeyframes, sections) {
  const perSection = {};
  const safeSections = sections || [];

  // Helper: find which section an element Y position belongs to
  function findSectionIndex(elementY) {
    if (elementY == null) return -1;
    for (const sec of safeSections) {
      const secTop = sec.rect.y;
      const secBottom = sec.rect.y + sec.rect.height;
      // Use tolerance of ±100px
      if (elementY >= secTop - 100 && elementY <= secBottom + 100) {
        return sec.index;
      }
    }
    return -1;
  }

  // Initialize each section
  for (const sec of safeSections) {
    perSection[sec.index] = {
      animations: [],
      lottie: [],
      cssKeyframes: [],
    };
  }
  // Global bucket for unmatched animations
  perSection['global'] = { animations: [], lottie: [], cssKeyframes: [] };

  // Group GSAP calls by section
  // First, group timeline steps together
  const timelineGroups = new Map();
  const standaloneCalls = [];

  for (const call of (gsapCalls || [])) {
    if (call.timelineId) {
      if (!timelineGroups.has(call.timelineId)) {
        timelineGroups.set(call.timelineId, []);
      }
      timelineGroups.get(call.timelineId).push(call);
    } else {
      standaloneCalls.push(call);
    }
  }

  // Place standalone calls into sections
  for (const call of standaloneCalls) {
    // Prefer scrollTrigger.trigger element position, then elementY
    let y = call.elementY;
    const secIdx = findSectionIndex(y);
    const bucket = secIdx >= 0 ? perSection[secIdx] : perSection['global'];
    bucket.animations.push({
      method: call.method,
      targetSelector: call.targetSelector,
      vars: call.vars,
      duration: call.duration,
      ease: call.ease,
      stagger: call.stagger,
      delay: call.delay,
      scrollTrigger: call.scrollTrigger,
      source: call.source,
    });
  }

  // Place timeline groups into sections (use first target's Y position)
  for (const [tlId, steps] of timelineGroups) {
    const firstY = steps.find(s => s.elementY != null)?.elementY ?? null;
    const secIdx = findSectionIndex(firstY);
    const bucket = secIdx >= 0 ? perSection[secIdx] : perSection['global'];

    bucket.animations.push({
      method: 'timeline',
      steps: steps.map(s => ({
        method: s.method,
        targetSelector: s.targetSelector,
        vars: s.vars,
        duration: s.duration,
        ease: s.ease,
        stagger: s.stagger,
        delay: s.delay,
      })),
      scrollTrigger: steps[0]?.scrollTrigger || null,
      source: steps[0]?.source || 'unknown',
    });
  }

  // Place Lottie elements into sections
  for (const lottie of (lottieElements || [])) {
    const secIdx = findSectionIndex(lottie.elementY);
    const bucket = secIdx >= 0 ? perSection[secIdx] : perSection['global'];
    bucket.lottie.push({
      url: lottie.url,
      width: lottie.width,
      height: lottie.height,
    });
  }

  // CSS keyframes go to global (they apply page-wide)
  perSection['global'].cssKeyframes = (cssKeyframes || []).map(k => ({
    name: k.name,
    body: k.body || null,
  }));

  // Clean up empty sections
  for (const key of Object.keys(perSection)) {
    const data = perSection[key];
    if (data.animations.length === 0 && data.lottie.length === 0 && data.cssKeyframes.length === 0) {
      if (key !== 'global') delete perSection[key];
    }
  }

  return perSection;
}

module.exports = {
  getPreNavigationScript,
  setupNetworkInterception,
  getMutationObserverScript,
  extractAnimationData,
  analyzeAnimationEvidence,
  groupAnimationsBySection,
};
