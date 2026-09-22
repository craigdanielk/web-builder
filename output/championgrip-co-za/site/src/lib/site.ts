export const shop = {
  name: "Champion Grip",
  slogan: "The Choice of Champions",
  logo: "/media/champion-grip/brand-logo.png",
};

export const social = {
  instagram: "https://www.instagram.com/champion_grip/",
  facebook: "https://www.facebook.com/profile.php?id=100054611102140",
  whatsapp: "https://api.whatsapp.com/send?phone=27612602932",
  whatsappDemo:
    "https://api.whatsapp.com/send?phone=27711244212&text=Hi%20Champion%20Grip%20%E2%80%94%20I%27d%20like%20to%20book%20a%20club%20demo",
  email: "mailto:info@championgrip.co.za",
  phone: "tel:+27612602932",
};

export const nav = [
  {
    label: "Shop",
    href: "/products/champion-grip-spray-120ml-can-elevate-your-bowling-game-with-confidence",
  },
  { label: "Features", href: "/features" },
  { label: "Story", href: "/about" },
  { label: "Stockists", href: "/find-a-stockist" },
  { label: "Demo", href: "/book-a-demo" },
  { label: "Blog", href: "/blog" },
  { label: "Contact", href: "/contact" },
];

export const product = {
  handle: "champion-grip-spray-120ml-can-elevate-your-bowling-game-with-confidence",
  title: "Champion Grip Spray 120ml",
  price: "R85.00",
  image: "/media/champion-grip/can-plate-front.webp",
  summary: "The world's first aerosol bowls grip enhancer. The Choice of Champions.",
};

/**
 * CAD-A media map — one job per section.
 * Prefer webp where present. Legacy KEEP ON ROLLING and junk corpus stay off the home path.
 */
export const media = {
  logo: "/media/champion-grip/brand-logo.png",
  /** Studio — commerce / hero product */
  packshot: "/media/champion-grip/can-plate-front.webp",
  packshotHero: "/media/champion-grip/can-plate-hero34.webp",
  packshotSpine: "/media/champion-grip/can-plate-spine.webp",
  /** Location product (can on green) — lifestyle proof, not hero primary */
  heroOutdoor: "/media/champion-grip/hero-outdoor.png",
  sceneOutdoor: "/media/champion-grip/scene-outdoor-single.webp",
  sceneGroup: "/media/champion-grip/scene-outdoor-group.webp",
  sceneSpray: "/media/champion-grip/scene-spray-hand.webp",
  /** Atmosphere — no product (section depth / story plates). 4K where available. */
  atmRink: "/media/champion-grip/atm-rink-16x9.webp",
  atmRinkMobile: "/media/champion-grip/atm-rink-9x16.webp",
  atmMist: "/media/champion-grip/atm-mist-4x5.webp",
  atmFelt: "/media/champion-grip/atm-green-felt.webp",
  /** TEMP — replace with real SA nozzle macro (CG-UI-14 P2) */
  nozzleTemp: "/media/champion-grip/temp-nozzle-macro.webp",
  /** Low-res bowls lifestyle (online stock) — Journal / Features strip only, not hero */
  bowlsLine: "/media/champion-grip/bowls-line-wide.jpeg",
  bowlsJack: "/media/champion-grip/bowls-jack-golden.jpeg",
  bowlsClub: "/media/champion-grip/bowls-clubhouse-portrait.jpeg",
  bowlsMatch: "/media/champion-grip/bowls-match-jack.jpeg",
  /** B2B */
  dozen: "/media/champion-grip/dozen-plate-hero34.webp",
  dozenBox: "/media/champion-grip/dozen-box.webp",
  /** People — real only */
  founder: "/media/champion-grip/be1df040775cff26.jpg",
} as const;

/** Ordered PDP gallery — studio → lifestyle → macro interim. */
export const pdpGallery = [
  { url: media.packshot, altText: "Champion Grip Spray front", width: 896, height: 1200 },
  { url: media.packshotHero, altText: "Champion Grip Spray three-quarter", width: 896, height: 1200 },
  { url: media.packshotSpine, altText: "Champion Grip Spray side", width: 896, height: 1200 },
  { url: media.sceneOutdoor, altText: "Champion Grip on the bowling green", width: 896, height: 1200 },
  { url: media.sceneSpray, altText: "Champion Grip spray in use", width: 1264, height: 848 },
  { url: media.nozzleTemp, altText: "Nozzle mist detail (interim)", width: 1024, height: 1024 },
] as const;
