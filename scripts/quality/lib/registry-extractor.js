/**
 * registry-extractor.js
 *
 * Feature extraction and classification engine for animation components.
 * Parses .tsx source code via regex to extract animation signals, triggers,
 * capabilities, and content patterns for classification.
 */

const path = require("path");

// Regex pattern library
const P = {
  framerMotion: /from\s+['"](?:framer-motion|motion\/react)['"]/,
  gsap: /from\s+['"]gsap['"]/,
  scrollTrigger: /ScrollTrigger/,
  lucide: /from\s+['"]lucide-react['"]/,
  shadcnUI: /from\s+['"]@\/components\/ui\//g,
  radixUI: /from\s+['"]@radix-ui\//,
  threeJS: /from\s+['"]three['"]/,
  lottie: /from\s+['"]lottie/,
  motionElements: /motion\.(div|span|section|p|h[1-6]|button|a|img|svg|path|li|ul|nav|footer|header|main|article|figure|aside|tr|td)/g,
  motionCreate: /motion\.create/,
  useScroll: /useScroll\b/,
  useTransform: /useTransform\b/,
  useMotionValue: /useMotionValue\b/,
  useSpring: /useSpring\b/,
  useInView: /useInView\b/,
  useAnimation: /useAnimation\b/,
  animatePresence: /<AnimatePresence/,
  layoutGroup: /LayoutGroup/,
  layoutProp: /\blayout\b(?!=)/,
  whileInView: /whileInView/,
  whileHover: /whileHover/,
  whileTap: /whileTap/,
  whileDrag: /whileDrag/,
  whileFocus: /whileFocus/,
  scrollTriggerConfig: /scrollTrigger\s*:/i,
  keyframes: /@keyframes\s+(\w+)/g,
  cssAnimationProp: /animation\s*:/,
  getBoundingClientRect: /getBoundingClientRect/,
  offsetDims: /offset(Width|Height|Top|Left)\b/,
  clientDims: /client(Width|Height)\b/,
  resizeObserver: /ResizeObserver/,
  intersectionObserver: /IntersectionObserver/,
  transformOnly: /transform|scale|rotate|translate|skew/,
  opacity: /opacity/,
  filterProps: /filter|blur\(|brightness|contrast|saturate|backdrop/,
  layoutCSSProps: /(?:^|\s)(width|height|top|left|right|bottom|margin|padding|flex|grid)\s*:/,
  hardcodedContent: /["'`][A-Z][a-zA-Z\s]{5,}["'`]|["'`]\$\d+|["'`]https?:\/\//g,
  priceSignals: /\$\d+|\bprice\b|\bmonthly\b|\byearly\b/i,
  formElements: /<(input|textarea|select|form)\b|<Input\b|<Select\b|<Textarea\b/gi,
  tableElements: /<(table|thead|tbody|tr|td|th)\b|<Table\b/gi,
  buttonElements: /<(button|Button)\b/gi,
  imageElements: /<img\b|<Image\b/gi,
  headingElements: /<h[1-6]\b/gi,
  childrenProp: /\bchildren\b/,
  classNameProp: /\bclassName\b/,
  exportDefault: /export\s+default\b/,
};

// Motion intents controlled list
const TAXONOMY_MOTION_INTENTS = [
  "reveal","entrance","exit","attention","emphasis","transition","morph",
  "parallax","float","pulse","shimmer","flip","scale","slide","rotate",
  "blur","glow","wave","bounce","spring","stagger","collapse","expand",
  "count","typewrite","scramble","gradient","tilt","magnetic","drag",
  "marquee","progress","pin","horizontal_scroll","cursor_follow",
  "spotlight","beam","aurora","perspective","skeleton","loading",
];

function detectMotionIntents(code, filename) {
  const intents = new Set();
  const fn = filename.toLowerCase();

  if (/whileInView|inView|viewport|IntersectionObserver/i.test(code) && /opacity|translate|scale/.test(code))
    intents.add("reveal");
  if (/fade.?up|fade.?in|slide.?in|slide.?up/i.test(fn)) intents.add("entrance");
  if (/exit|leave|AnimatePresence/i.test(code)) intents.add("exit");
  if (/parallax/i.test(fn) || /useTransform.*scrollY/i.test(code)) intents.add("parallax");
  if (/float/i.test(fn) || /repeat:\s*Infinity.*y:/i.test(code)) intents.add("float");
  if (/pulse|puls/i.test(fn) || /repeat:\s*Infinity.*scale/i.test(code)) intents.add("pulse");
  if (/shimmer|wave/i.test(fn)) intents.add("shimmer");
  if (/flip/i.test(fn) || /rotateX|rotateY/i.test(code)) intents.add("flip");
  if (/scale/i.test(fn) || /whileHover.*scale/i.test(code)) intents.add("scale");
  if (/slide/i.test(fn) || /translateX|x:/i.test(code)) intents.add("slide");
  if (/rotate/i.test(fn) || /rotate:/i.test(code)) intents.add("rotate");
  if (/blur/i.test(fn) || /filter.*blur/i.test(code)) intents.add("blur");
  if (/glow|beam/i.test(fn) || /boxShadow|box-shadow/i.test(code)) intents.add("glow");
  if (/bounce/i.test(fn) || /type:\s*["']spring["']/i.test(code)) intents.add("bounce");
  if (/spring/i.test(code) && /stiffness|damping/i.test(code)) intents.add("spring");
  if (/stagger/i.test(fn) || /staggerChildren|delayChildren/i.test(code)) intents.add("stagger");
  if (/count.?up|counter/i.test(fn)) intents.add("count");
  if (/typewrite/i.test(fn) || /typing|typewriter/i.test(fn)) intents.add("typewrite");
  if (/scramble/i.test(fn)) intents.add("scramble");
  if (/gradient/i.test(fn) && /animation|@keyframes/i.test(code)) intents.add("gradient");
  if (/tilt/i.test(fn) || /perspective.*rotateX.*rotateY/i.test(code)) intents.add("tilt");
  if (/magnetic/i.test(fn) || /magneticDistance|magnet/i.test(code)) intents.add("magnetic");
  if (/drag/i.test(fn) || /whileDrag|onDrag/i.test(code)) intents.add("drag");
  if (/marquee/i.test(fn) || /infinite.*scroll|marquee/i.test(fn)) intents.add("marquee");
  if (/progress/i.test(fn) || /scrollYProgress|scaleX.*scroll/i.test(code)) intents.add("progress");
  if (/pin/i.test(fn) || /pin:\s*true|position:\s*["']sticky/i.test(code)) intents.add("pin");
  if (/horizontal.?scroll/i.test(fn)) intents.add("horizontal_scroll");
  if (/cursor|trail/i.test(fn)) intents.add("cursor_follow");
  if (/spotlight/i.test(fn)) intents.add("spotlight");
  if (/beam/i.test(fn)) intents.add("beam");
  if (/aurora/i.test(fn)) intents.add("aurora");
  if (/perspective.?grid/i.test(fn)) intents.add("perspective");
  if (/skeleton/i.test(fn)) intents.add("skeleton");
  if (/loader|loading|spinner/i.test(fn)) intents.add("loading");
  if (/word.?reveal|word.?rotate|text.?reveal/i.test(fn)) intents.add("reveal");
  if (/character.?reveal|char.?reveal|split.?text/i.test(fn)) intents.add("reveal");
  if (/collapse|expand|accordion/i.test(fn)) { intents.add("collapse"); intents.add("expand"); }
  if (/whileHover/i.test(code) && !(/whileInView/i.test(code) || /IntersectionObserver/i.test(code)))
    intents.add("attention");
  if (/animate-pulse|animate-bounce|repeat:\s*Infinity/i.test(code)) intents.add("emphasis");

  if (intents.size === 0) {
    if (/whileHover/i.test(code)) intents.add("attention");
    else if (/whileInView|viewport/i.test(code)) intents.add("reveal");
    else if (/motion\./i.test(code)) intents.add("entrance");
    else intents.add("entrance");
  }
  return [...intents].filter((i) => TAXONOMY_MOTION_INTENTS.includes(i));
}

function matchAllGlobal(str, regex) {
  const results = [];
  const r = new RegExp(regex.source, regex.flags);
  let m;
  while ((m = r[Symbol.match] ? null : null) !== undefined) break;
  // Use string.match for global regexes
  const matches = str.match(r);
  return matches || [];
}

function extractFeatures(filePath, code) {
  const filename = path.basename(filePath, ".tsx");
  const lineCount = code.split("\n").length;

  const hasFramerMotion = P.framerMotion.test(code);
  const hasGSAP = P.gsap.test(code);
  const hasCSSAnimation = (/@keyframes/).test(code) || P.cssAnimationProp.test(code);
  const hasThreeJS = P.threeJS.test(code);
  const hasLottie = P.lottie.test(code);

  const frameworks = [];
  if (hasFramerMotion) frameworks.push("framer-motion");
  if (hasGSAP) frameworks.push("gsap");
  if (hasCSSAnimation) frameworks.push("css");
  if (hasThreeJS) frameworks.push("three.js");
  if (hasLottie) frameworks.push("lottie");
  if (frameworks.length === 0) frameworks.push("none");

  const motionElementMatches = code.match(/motion\.(div|span|section|p|h[1-6]|button|a|img|svg|path|li|ul|nav|footer|header|main|article|figure|aside|tr|td)/g) || [];
  const motionElementCount = motionElementMatches.length;

  const framerAPIs = {
    useScroll: P.useScroll.test(code),
    useTransform: P.useTransform.test(code),
    useMotionValue: P.useMotionValue.test(code),
    useSpring: P.useSpring.test(code),
    useInView: P.useInView.test(code),
    useAnimation: P.useAnimation.test(code),
    animatePresence: P.animatePresence.test(code),
    motionCreate: P.motionCreate.test(code),
    layoutGroup: P.layoutGroup.test(code),
    layout: P.layoutProp.test(code),
  };

  const triggers = new Set();
  if (P.whileInView.test(code) || P.intersectionObserver.test(code)) triggers.add("viewport");
  if (P.useScroll.test(code) || P.scrollTriggerConfig.test(code)) triggers.add("scroll_linked");
  if (P.whileHover.test(code) || /onMouse(Enter|Over|Move)/.test(code)) triggers.add("hover");
  if (P.whileTap.test(code) || /onClick\b/.test(code)) triggers.add("click");
  if (P.whileDrag.test(code)) triggers.add("drag");
  if (P.whileFocus.test(code) || /onFocus\b/.test(code)) triggers.add("focus");
  if (/useEffect\s*\(\s*\(\)\s*=>/.test(code) && !P.intersectionObserver.test(code) && !P.useScroll.test(code))
    triggers.add("mount");
  if (/setTimeout|setInterval|delay:\s*\d/.test(code)) triggers.add("time_delay");
  if (P.resizeObserver.test(code)) triggers.add("resize");
  if (triggers.size === 0) triggers.add("mount");

  const usesTransformOnly = P.transformOnly.test(code) && !P.layoutCSSProps.test(code);
  const usesOpacity = P.opacity.test(code);
  const usesFilter = P.filterProps.test(code);
  const modifiesLayout = P.layoutCSSProps.test(code);

  const requiresLayoutMeasurement =
    P.getBoundingClientRect.test(code) || P.offsetDims.test(code) ||
    P.clientDims.test(code) || P.resizeObserver.test(code);

  const hardcodedContentCount = (code.match(/["'`][A-Z][a-zA-Z\s]{5,}["'`]|["'`]\$\d+|["'`]https?:\/\//g) || []).length;
  const shadcnImportCount = (code.match(/from\s+['"]@\/components\/ui\//g) || []).length;
  const formElementCount = (code.match(/<(input|textarea|select|form)\b|<Input\b|<Select\b|<Textarea\b/gi) || []).length;
  const tableElementCount = (code.match(/<(table|thead|tbody|tr|td|th)\b|<Table\b/gi) || []).length;
  const buttonCount = (code.match(/<(button|Button)\b/gi) || []).length;
  const imageCount = (code.match(/<img\b|<Image\b/gi) || []).length;
  const headingCount = (code.match(/<h[1-6]\b/gi) || []).length;

  const hasChildren = P.childrenProp.test(code);
  const hasClassName = P.classNameProp.test(code);
  const hasPriceSignals = P.priceSignals.test(code);
  const hasLucide = P.lucide.test(code);
  const hasRadixUI = P.radixUI.test(code);

  const hasDefaultExport = P.exportDefault.test(code);
  const namedExports = [];

  // Extract named exports using matchAll
  for (const m of code.matchAll(/export\s+(?:const|function|class)\s+(\w+)/g)) {
    namedExports.push(m[1]);
  }
  for (const m of code.matchAll(/export\s*\{([^}]+)\}/g)) {
    m[1].split(",").forEach((e) => {
      const name = e.trim().split(/\s+as\s+/)[0].trim();
      if (name) namedExports.push(name);
    });
  }

  const hasStagger = /staggerChildren|delayChildren|stagger/i.test(code) ||
    /\.forEach.*delay|\.map.*delay.*index|i\s*\*\s*\d+\.\d+/i.test(code);
  const hasLooping = /repeat:\s*(Infinity|-1)|repeatType|iteration-count:\s*infinite|loop/i.test(code);
  const hasReversible = /repeatType:\s*["']reverse|yoyo|toggle|isOpen|isExpanded|isActive/i.test(code);
  const isInterruptible = hasFramerMotion || /animate\(|kill\(\)/i.test(code);
  const isComposable = hasChildren && motionElementCount <= 3 && lineCount < 100;

  const durationMatches = code.match(/duration:\s*([\d.]+)/g) || [];
  const durations = durationMatches.map((d) => parseFloat(d.replace("duration:", "").trim()));
  let durationRange = [300, 800];
  if (durations.length > 0) {
    const minD = Math.min(...durations);
    const maxD = Math.max(...durations);
    const mult = minD < 10 ? 1000 : 1;
    durationRange = [Math.round(minD * mult), Math.round(maxD * mult)];
  }

  const easingProfiles = new Set();
  if (/ease:\s*["']linear/i.test(code)) easingProfiles.add("linear");
  if (/ease:\s*["']ease/i.test(code) || /easeInOut/i.test(code)) easingProfiles.add("ease-in-out");
  if (/easeOut|ease:\s*\[[\d.,\s]+\]/i.test(code)) easingProfiles.add("ease-out");
  if (/easeIn(?!Out)/i.test(code)) easingProfiles.add("ease-in");
  if (/type:\s*["']spring/i.test(code)) easingProfiles.add("spring");
  if (/backInOut|backIn|backOut/i.test(code)) easingProfiles.add("back");
  if (easingProfiles.size === 0) easingProfiles.add("ease-out");

  const keyframeNames = [];
  for (const m of code.matchAll(/@keyframes\s+(\w+)/g)) keyframeNames.push(m[1]);

  const hasReducedMotion = /prefers-reduced-motion|reducedMotion|useReducedMotion/i.test(code);

  const directionality = new Set();
  if (/translateY|y:|top:|bottom:|slideUp|slideDown|fade.?up|fade.?down/i.test(code)) directionality.add("vertical");
  if (/translateX|x:|left:|right:|slideLeft|slideRight|slide.?in.?right|slide.?in.?left/i.test(code)) directionality.add("horizontal");
  if (/scale|rotate|opacity|blur/i.test(code) && directionality.size === 0) directionality.add("omnidirectional");
  if (directionality.size === 0) directionality.add("omnidirectional");

  const axis = [];
  if (directionality.has("vertical")) axis.push("y");
  if (directionality.has("horizontal")) axis.push("x");
  if (/rotate:|rotateZ|rotateX|rotateY/i.test(code)) axis.push("z");
  if (axis.length === 0) axis.push("none");

  return {
    filename, lineCount, frameworks, motionElementCount, framerAPIs,
    triggers: [...triggers], usesTransformOnly, usesOpacity, usesFilter,
    modifiesLayout, requiresLayoutMeasurement, hardcodedContentCount,
    shadcnImportCount, formElementCount, tableElementCount, buttonCount,
    imageCount, headingCount, hasChildren, hasClassName, hasPriceSignals,
    hasLucide, hasRadixUI, hasDefaultExport, namedExports, hasStagger,
    hasLooping, hasReversible, isInterruptible, isComposable, durationRange,
    easingProfiles: [...easingProfiles], keyframeNames, hasReducedMotion,
    directionality: [...directionality], axis,
    motionIntents: detectMotionIntents(code, filename),
  };
}

function classifyComponent(features) {
  let animationScore = 0;
  let uiScore = 0;

  if (features.frameworks.includes("framer-motion")) animationScore += 3;
  if (features.frameworks.includes("gsap")) animationScore += 3;
  if (features.frameworks.includes("css") && features.keyframeNames.length > 0) animationScore += 2;
  if (features.motionElementCount > 0) animationScore += Math.min(features.motionElementCount, 5);
  if (features.hasChildren && features.motionElementCount > 0) animationScore += 3;
  if (features.isComposable) animationScore += 2;
  if (features.hasStagger) animationScore += 1;
  if (features.hasLooping) animationScore += 1;
  if (Object.values(features.framerAPIs).some(Boolean)) animationScore += 2;
  if (features.lineCount < 80 && features.motionElementCount > 0) animationScore += 2;

  if (features.hardcodedContentCount > 5) uiScore += 3;
  if (features.shadcnImportCount > 0) uiScore += features.shadcnImportCount * 2;
  if (features.formElementCount > 0) uiScore += 3;
  if (features.tableElementCount > 0) uiScore += 3;
  if (features.hasPriceSignals) uiScore += 3;
  if (features.hasLucide) uiScore += 1;
  if (features.hasRadixUI) uiScore += 2;
  if (features.headingCount > 2) uiScore += 2;
  if (features.lineCount > 200) uiScore += 2;
  if (features.lineCount > 400) uiScore += 3;
  if (features.buttonCount > 2) uiScore += 1;
  if (features.imageCount > 2) uiScore += 1;

  if (animationScore >= 5 && uiScore >= 5) return "hybrid";
  if (animationScore > uiScore) return "animation";
  if (uiScore > animationScore) return "ui";
  return features.hasChildren ? "animation" : "ui";
}

module.exports = { extractFeatures, classifyComponent, detectMotionIntents };
