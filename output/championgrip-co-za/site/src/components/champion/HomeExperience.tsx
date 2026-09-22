"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AddToCartButton } from "@/lib/shopify/AddToCartButton";
import { media, shop } from "@/lib/site";

export type ChampionProduct = {
  title: string;
  handle: string;
  imageUrl: string;
  imageAlt: string;
  priceLabel: string;
  variantId: string;
};

const SCENES = [
  {
    kicker: "01",
    line: "MORE GRIP.",
    plate: media.atmMist,
    plateAlt: "Fine aerosol mist over the green",
  },
  {
    kicker: "02",
    line: "MORE CONTROL.",
    plate: media.sceneOutdoor,
    plateAlt: "Champion Grip on the bowling green",
  },
  {
    kicker: "03",
    line: "MORE CONFIDENCE.",
    plate: media.founder,
    plateAlt: "Werner Kunte",
  },
] as const;

export function HomeExperience({ product }: { product: ChampionProduct }) {
  const root = useRef<HTMLElement>(null);
  const pin = useRef<HTMLElement>(null);
  const can = useRef<HTMLImageElement>(null);
  const heroCan = useRef<HTMLImageElement>(null);
  const heroWrap = useRef<HTMLDivElement>(null);
  const heroStage = useRef<HTMLDivElement>(null);
  const [scene, setScene] = useState(0);
  const [reduced, setReduced] = useState(false);
  const [narrow, setNarrow] = useState(false);
  const [handoff, setHandoff] = useState(0);

  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const width = window.matchMedia("(max-width: 767px)");
    const apply = () => {
      setReduced(motion.matches);
      setNarrow(width.matches);
    };
    apply();
    motion.addEventListener("change", apply);
    width.addEventListener("change", apply);
    return () => {
      motion.removeEventListener("change", apply);
      width.removeEventListener("change", apply);
    };
  }, []);

  // Desktop: pin story + shared hero→story handoff scrub
  useEffect(() => {
    if (reduced || narrow) return;
    let revert = () => {};
    let dead = false;
    (async () => {
      const gsap = (await import("gsap")).default;
      const { ScrollTrigger } = await import("gsap/ScrollTrigger");
      if (dead) return;
      gsap.registerPlugin(ScrollTrigger);
      const ctx = gsap.context(() => {
        if (heroStage.current && pin.current) {
          const handoffNode = heroWrap.current || heroCan.current;
          ScrollTrigger.create({
            trigger: heroStage.current,
            start: "center center",
            endTrigger: pin.current,
            end: "top top",
            scrub: 0.45,
            onUpdate: (self) => {
              setHandoff(self.progress);
              if (handoffNode) {
                gsap.set(handoffNode, {
                  opacity: 1 - self.progress * 0.85,
                  scale: 1 - self.progress * 0.12,
                  y: self.progress * 40,
                });
              }
            },
          });
        }

        if (pin.current && can.current) {
          ScrollTrigger.create({
            trigger: pin.current,
            start: "top top",
            end: "+=180%",
            pin: true,
            scrub: 0.45,
            onUpdate: (self) => {
              const p = self.progress;
              const next = p < 0.34 ? 0 : p < 0.67 ? 1 : 2;
              setScene(next);
              gsap.set(can.current, {
                rotate: -8 + p * 16,
                x: (p - 0.5) * 90,
                y: Math.sin(p * Math.PI) * -18,
                scale: 0.92 + p * 0.12,
                opacity: Math.min(1, 0.35 + p * 1.2),
              });
            },
          });
        }
      }, root);
      revert = () => ctx.revert();
    })();
    return () => {
      dead = true;
      revert();
    };
  }, [reduced, narrow]);

  useEffect(() => {
    if (reduced || narrow) return;
    const node = heroCan.current;
    if (!node) return;
    const onMove = (event: PointerEvent) => {
      if (event.pointerType === "touch") return;
      const x = (event.clientX / window.innerWidth - 0.5) * 18;
      const y = (event.clientY / window.innerHeight - 0.5) * 12;
      node.style.transform = `translate3d(${x}px, ${y}px, 0) rotate(-6deg)`;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [reduced, narrow]);

  return (
    <article ref={root} className="cg-home" data-handoff={handoff.toFixed(2)}>
      <section className="cg-hero">
        <div className="cg-hero-copy">
          <p className="cg-kicker">{shop.slogan}</p>
          <h1>
            World&apos;s first
            <br />
            aerosol bowls
            <br />
            grip enhancer.
          </h1>
          <p className="cg-lead">
            Champion Grip Spray, 120ml. Hold the bowl lightly, with a secure grip indoors and outdoors.
          </p>
          <div className="cg-cta-row">
            <AddToCartButton variantId={product.variantId} className="cg-buy">
              Shop Champion Grip
              <span>R85</span>
            </AddToCartButton>
            <a className="cg-text-link" href="#story">
              Read the sequence
            </a>
          </div>
        </div>
        <div className="cg-hero-stage" ref={heroStage}>
          <div className="cg-glow" />
          <div ref={heroWrap} className="cg-hero-can-wrap">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={heroCan}
              src={media.packshotHero}
              alt={product.imageAlt || product.title}
              className="cg-can"
            />
          </div>
        </div>
      </section>

      <section className="cg-manifesto" aria-labelledby="cg-manifesto-heading">
        <picture>
          <source media="(max-width: 860px)" srcSet={media.atmRinkMobile} type="image/webp" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={media.atmRink} alt="" className="cg-manifesto-plate" />
        </picture>
        <div>
          <p className="cg-kicker">On the green</p>
          <h2 id="cg-manifesto-heading">Hold the bowl lightly.</h2>
          <p>
            Secure grip indoors and outdoors. A small amount is enough — spray away from yourself, outdoors or in a
            well-ventilated place.
          </p>
        </div>
      </section>

      {/* Desktop pinned story */}
      {!narrow ? (
        <section id="story" ref={pin} className="cg-story" data-scene={scene}>
          {SCENES.map((item, index) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={item.plate}
              src={item.plate}
              alt=""
              className="cg-story-plate"
              data-active={index === scene}
              aria-hidden
            />
          ))}
          <div className="cg-story-veil" aria-hidden />
          <div className="cg-story-copy">
            <p className="cg-kicker">{SCENES[scene].kicker}</p>
            <h2>{SCENES[scene].line}</h2>
            <ol>
              {SCENES.map((item, index) => (
                <li key={item.line} data-active={index === scene}>
                  {item.line}
                </li>
              ))}
            </ol>
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img ref={can} src={media.packshot} alt="" className="cg-can cg-can-story" />
        </section>
      ) : (
        <section id="story" className="cg-story-snap" aria-label="Product story">
          <div className="cg-story-snap-track">
            {SCENES.map((item) => (
              <article key={item.line} className="cg-story-snap-card">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={item.plate} alt={item.plateAlt} className="cg-story-snap-plate" />
                <div>
                  <p className="cg-kicker">{item.kicker}</p>
                  <h2>{item.line}</h2>
                </div>
              </article>
            ))}
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={media.packshot} alt="" className="cg-can cg-can-snap" />
        </section>
      )}

      <section className="cg-howto" aria-labelledby="cg-howto-heading">
        <div className="cg-howto-main">
          <p className="cg-kicker">How it works</p>
          <h2 id="cg-howto-heading" className="cg-howto-pull">
            A small amount is enough.
          </h2>
          <p className="cg-howto-lead">
            Indoor and outdoor. Hold the bowl lightly, with a secure grip across changing green conditions.
          </p>
        </div>
        <p className="cg-howto-aside">Use outdoors or in a well-ventilated place. Spray away from yourself.</p>
      </section>

      <section id="founder" className="cg-founder">
        <div className="cg-founder-media">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={media.founder} alt="Werner Kunte" />
        </div>
        <div className="cg-founder-copy">
          <p className="cg-kicker">The chemist</p>
          <h2>Werner Kunte.</h2>
          <p>
            Werner Kunte arrived in South Africa from Germany in 1957, an industrial chemist. Silhouette Chemicals, then
            Schwarzkopf.
          </p>
          <Link href="/about" className="cg-text-link">
            Read the full story
          </Link>
        </div>
      </section>

      <section className="cg-buyblock">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={media.packshot} alt={product.imageAlt || product.title} />
        <div>
          <p className="cg-kicker">120ml</p>
          <h2>{product.title}</h2>
          <p className="cg-price">{product.priceLabel}</p>
          <p>Hold the bowl lightly. The world&apos;s first aerosol bowls grip enhancer.</p>
          <AddToCartButton variantId={product.variantId} className="cg-buy">
            Add to cart
            <span>{product.priceLabel}</span>
          </AddToCartButton>
        </div>
      </section>

      <section className="cg-use" style={{ backgroundImage: `url(${media.atmFelt})` }}>
        <div>
          <p className="cg-kicker">On the green</p>
          <h2>A small amount.</h2>
          <p>
            Use it outdoors or in a well-ventilated place, and spray away from yourself. Bowls treated with Champion Grip
            Spray are less likely to pick up grass clippings or sand.
          </p>
        </div>
        <blockquote>Hold the bowl lightly.</blockquote>
      </section>

      <section className="cg-close">
        <p className="cg-kicker">{shop.slogan}</p>
        <h2>Elevate your game.</h2>
        <AddToCartButton variantId={product.variantId} className="cg-buy cg-buy-gold">
          Shop Champion Grip
          <span>R85</span>
        </AddToCartButton>
      </section>
    </article>
  );
}
