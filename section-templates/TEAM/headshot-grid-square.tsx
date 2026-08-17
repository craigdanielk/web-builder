"use client";

import { motion } from "framer-motion";
import Image from "next/image";

/**
 * TEAM | headshot-grid-square
 * Token-driven section template — tenant content filled at build time.
 *
 * Replaces a double-brace brand-token template that interpolated Tailwind
 * palette NAMES into class strings — a `bg-` prefix concatenated with a
 * bg_primary token, `text-` with text_muted, `ring-` with accent plus an
 * opacity suffix — and set its rhythm with a hardcoded `py-16 md:py-24`.
 * (Those tokens are paraphrased rather than spelled: brand injection is a raw
 * string replace over the WHOLE file, comments included, so writing one here
 * verbatim would have this note silently rewritten too.) Four departures:
 *
 *   1. EVERY COLOUR AND RHYTHM IS A CSS CUSTOM PROPERTY. The build compiles the
 *      market benchmark into --accent / --foreground / --background / --surface
 *      / --border / --section-py and this reads them. The old form could not
 *      carry a design system at all: a Tailwind class assembled at build time
 *      from a literal palette NAME renders one look for every tenant. Worse,
 *      such a class only exists if the JIT scanner happened to see it — an
 *      unresolved token left the ring and the tile transparent, silently.
 *
 *   2. ARITY FROM THE HARVEST. The old body spelled out eight member literals,
 *      so a four-person team rendered four real cards and four cards of raw
 *      `{member_5_name}` text. The repeat block below is written once and
 *      emitted once per harvested member — four renders four, twelve renders
 *      twelve, none renders nothing at all.
 *
 *   3. NO EMPTY `src`. `<Image src="">` THROWS in next/image and takes the
 *      whole route down while every brace and string check passes. A member
 *      whose portrait did not resolve gets a token-derived tile instead, and
 *      the <Image> element is not rendered. The initials on that tile are
 *      sliced from the member's own harvested name — derived, not invented.
 *
 *   4. HIERARCHY BY SIZE AND SPACE, NOT WEIGHT. Weight comes from
 *      --heading-weight; nothing here reaches for font-bold.
 *
 * Slots:
 *   {section_title}       → "The people behind Cape Crypto"
 *   {section_subtitle}    → one line of context under the heading
 *   {members[].name}      → harvested name                        (required)
 *   {members[].role}      → harvested role                        (optional)
 *   {members[].bio}       → harvested one-liner                   (optional)
 *   {members[].image_url} → resolved local portrait asset         (optional)
 *   {members[].image_alt} → alt text for the above
 */

// The prose block above is documentation. THIS line is the contract:
// `slot_contract.declared_slots()` reads only a `// Tokens:` line (plus one
// legacy prose dialect). With neither, every non-reserved brace token in the
// body is swept up as fillable — which is how a JSX loop variable in a `key=`
// position was substituted away and took a build down with
// `Expected '</', got 'ident'`.
// Tokens: {section_title} {section_subtitle} {members[].name} {members[].role} {members[].bio} {members[].image_url} {members[].image_alt}

// The DEMAND declaration — and it is declared precisely so it can be REFUSED.
// `asset_resolver.claim_bearing_reason()` reads the TEAM context and emits no
// job, recording the refusal in the build record instead. A generated face
// beside a real name and a real job title is not decoration; it is a
// fabricated person on the site of a licensed FSP. This slot is filled from the
// harvest or it stays empty — never commissioned.
// Art: slot=members[].image_url intent=scene aspect=1:1 role=load-bearing

interface Member {
  name: string;
  role: string;
  bio: string;
  image_url: string;
  image_alt: string;
}

interface TeamHeadshotGridSquareProps {
  sectionTitle?: string;
  sectionSubtitle?: string;
  members?: Member[];
}

const harvestedMembers: Member[] = [
  /* repeat:members */
  {
    name: "{members[].name}",
    role: "{members[].role}",
    bio: "{members[].bio}",
    image_url: "{members[].image_url}",
    image_alt: "{members[].image_alt}",
  },
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";
//: The portrait tile's ground and the fallback tile's fill. Derived from
//: --foreground so it reads as a recessed surface on a light tenant AND on a
//: dark one; a literal `bg-white` or an rgba grey is correct for exactly one.
const TILE_FILL = "color-mix(in srgb, var(--foreground) 7%, var(--background))";

/** A slot value that survived the fill. Empty, whitespace, or an unsubstituted
 *  placeholder are all "the harvest had nothing here". */
function resolved(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed.startsWith("{")) return "";
  return trimmed;
}

/** Up to two initials off a sourced name. Derived from harvested copy — this
 *  invents no identity, it abbreviates one the page already carries. */
function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function TeamHeadshotGridSquare({
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  members = harvestedMembers,
}: TeamHeadshotGridSquareProps) {
  // camelCase deliberately: a local rendered as `{title}` is indistinguishable
  // from a `{title}` slot to the brace sweep, and gets substituted away.
  const headingText = resolved(sectionTitle);
  const subheadingText = resolved(sectionSubtitle);

  // A headshot with no name is a photograph, not a team member. Cards the
  // harvest could not name are dropped rather than rendered blank.
  const roster = members
    .map((member) => ({
      name: resolved(member.name),
      role: resolved(member.role),
      bio: resolved(member.bio),
      imageUrl: resolved(member.image_url),
      imageAlt: resolved(member.image_alt),
    }))
    .filter((member) => member.name);

  // A heading over an empty grid is worse than no section.
  if (!roster.length) return null;

  return (
    <section
      className="w-full"
      style={{
        background: "var(--surface, var(--background))",
        color: "var(--foreground)",
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "var(--section-py, 96px)",
      }}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {(headingText || subheadingText) && (
          <div className="max-w-2xl" style={{ marginBottom: "var(--block-gap, 48px)" }}>
            {headingText && (
              <h2
                className="text-[2rem] leading-[1.1] tracking-tight md:text-[3rem]"
                style={{
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: "var(--heading-weight, 400)" as unknown as number,
                }}
              >
                {headingText}
              </h2>
            )}
            {subheadingText && (
              <p
                className="mt-5 text-lg leading-relaxed"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
              >
                {subheadingText}
              </p>
            )}
          </div>
        )}

        {/* Square grid — 2 up on mobile, 3 on tablet, 4 on desktop. */}
        <motion.ul
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          className="grid grid-cols-2 gap-8 sm:grid-cols-3 lg:grid-cols-4"
        >
          {roster.map((member, index) => (
            <motion.li key={index} variants={itemVariants} className="flex flex-col">
              <div
                className="relative w-full overflow-hidden"
                style={{
                  aspectRatio: "1 / 1",
                  background: TILE_FILL,
                  border: `1px solid ${HAIRLINE}`,
                  borderRadius: "var(--radius-card, 8px)",
                }}
              >
                {member.imageUrl ? (
                  <Image
                    src={member.imageUrl}
                    alt={member.imageAlt || member.name}
                    fill
                    sizes="(min-width: 1024px) 22vw, (min-width: 640px) 30vw, 45vw"
                    className="object-cover"
                  />
                ) : (
                  /* No portrait resolved. A token-coloured tile carrying the
                     member's own initials — never an empty src, never a broken
                     image icon, never a stock face. */
                  <span
                    className="absolute inset-0 flex items-center justify-center text-2xl tracking-widest"
                    style={{
                      color: MUTED,
                      fontFamily: "var(--font-heading, inherit)",
                      fontWeight: "var(--heading-weight, 400)" as unknown as number,
                    }}
                  >
                    {initialsOf(member.name)}
                  </span>
                )}
              </div>

              {/* Decorative accent rule — the one use of --accent per card. */}
              <span
                aria-hidden="true"
                className="mt-5 block h-[3px] w-8"
                style={{ background: ACCENT, borderRadius: "var(--radius-button, 4px)" }}
              />

              <h3
                className="mt-4 text-base leading-snug"
                style={{ fontFamily: "var(--font-heading, inherit)", fontWeight: 500 }}
              >
                {member.name}
              </h3>

              {member.role && (
                <p
                  className="mt-1 text-sm leading-snug"
                  style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                >
                  {member.role}
                </p>
              )}

              {member.bio && (
                <p
                  className="mt-3 text-sm leading-relaxed"
                  style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                >
                  {member.bio}
                </p>
              )}
            </motion.li>
          ))}
        </motion.ul>
      </div>
    </section>
  );
}
