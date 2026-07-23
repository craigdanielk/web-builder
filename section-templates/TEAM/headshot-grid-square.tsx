"use client";

import { motion } from "framer-motion";
import Image from "next/image";

/**
 * TEAM | headshot-grid-square
 * Parameterized section template — brand tokens injected at build time.
 *
 * Square-aspect headshot grid that remains dense and readable on mobile.
 * Each member card renders a square photo, name, role, and optional social links.
 *
 * Token placeholders (replaced by orchestrator):
 *   {{brand.bg_primary}}          → e.g. "stone-50"
 *   {{brand.bg_secondary}}        → e.g. "white"
 *   {{brand.text_heading}}        → e.g. "stone-950"
 *   {{brand.text_primary}}        → e.g. "stone-900"
 *   {{brand.text_muted}}          → e.g. "stone-500"
 *   {{brand.accent}}              → e.g. "amber-700"
 *   {{brand.accent_hover}}        → e.g. "amber-800"
 *   {{brand.heading_font}}        → e.g. "DM Serif Display"
 *   {{brand.body_font}}           → e.g. "DM Sans"
 *
 * Slot placeholders (filled by tenant data):
 *   {section_title}               → "Meet Our Team"
 *   {section_subtitle}            → "The people behind the product"
 *   {member_1_name}               → "Alex Johnson"
 *   {member_1_role}               → "CEO & Founder"
 *   {member_1_image_url}          → "/images/team/alex.jpg"
 *   {member_1_bio}                → "Building the future of..."
 *   {member_2_name}               → ...
 *   {member_3_name}               → ...
 *   {member_4_name}               → ...
 *   {member_5_name}               → ...
 *   {member_6_name}               → ...
 *   {member_7_name}               → ...
 *   {member_8_name}               → ...
 */

interface Member {
  name: string;
  role: string;
  imageUrl: string;
  bio: string;
}

interface TeamHeadshotGridSquareProps {
  sectionTitle?: string;
  sectionSubtitle?: string;
  members?: Member[];
}

const defaultMembers: Member[] = [
  { name: "{member_1_name}", role: "{member_1_role}", imageUrl: "{member_1_image_url}", bio: "{member_1_bio}" },
  { name: "{member_2_name}", role: "{member_2_role}", imageUrl: "{member_2_image_url}", bio: "{member_2_bio}" },
  { name: "{member_3_name}", role: "{member_3_role}", imageUrl: "{member_3_image_url}", bio: "{member_3_bio}" },
  { name: "{member_4_name}", role: "{member_4_role}", imageUrl: "{member_4_image_url}", bio: "{member_4_bio}" },
  { name: "{member_5_name}", role: "{member_5_role}", imageUrl: "{member_5_image_url}", bio: "{member_5_bio}" },
  { name: "{member_6_name}", role: "{member_6_role}", imageUrl: "{member_6_image_url}", bio: "{member_6_bio}" },
  { name: "{member_7_name}", role: "{member_7_role}", imageUrl: "{member_7_image_url}", bio: "{member_7_bio}" },
  { name: "{member_8_name}", role: "{member_8_role}", imageUrl: "{member_8_image_url}", bio: "{member_8_bio}" },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" },
  },
};

export default function TeamHeadshotGridSquare({
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  members = defaultMembers,
}: TeamHeadshotGridSquareProps) {
  return (
    <section className="py-16 md:py-24 bg-{{brand.bg_primary}}">
      <div className="container mx-auto px-4 max-w-7xl">
        {/* Section heading */}
        <div className="text-center mb-12 md:mb-16">
          <h2
            className="text-3xl md:text-4xl lg:text-5xl font-bold text-{{brand.text_heading}} mb-4 leading-tight tracking-tight"
            style={{ fontFamily: "var(--font-heading, '{{brand.heading_font}}')" }}
          >
            {sectionTitle}
          </h2>
          <p
            className="text-lg md:text-xl text-{{brand.text_muted}} max-w-3xl mx-auto leading-relaxed"
            style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
          >
            {sectionSubtitle}
          </p>
        </div>

        {/* Square headshot grid — 2 cols mobile, 3 cols tablet, 4 cols desktop */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-8"
        >
          {members.map((member, index) => (
            <motion.div
              key={index}
              variants={itemVariants}
              className="group flex flex-col items-center text-center"
            >
              {/* Square headshot — 1:1 aspect ratio, circular crop */}
              <div className="relative w-full aspect-square max-w-[200px] mx-auto mb-4 rounded-full overflow-hidden bg-{{brand.bg_secondary}} shadow-md ring-2 ring-{{brand.text_muted}}/10 transition-shadow duration-300 group-hover:shadow-lg group-hover:ring-{{brand.accent}}/30">
                <Image
                  src={member.imageUrl}
                  alt={member.name}
                  fill
                  className="object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                  sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
                />
              </div>

              {/* Member info */}
              <h3
                className="font-semibold text-{{brand.text_heading}} text-sm sm:text-base mb-0.5 leading-tight"
                style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
              >
                {member.name}
              </h3>
              <p
                className="text-xs sm:text-sm text-{{brand.accent}} font-medium mb-2"
                style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
              >
                {member.role}
              </p>
              <p
                className="text-xs sm:text-sm text-{{brand.text_muted}} leading-relaxed line-clamp-3 hidden sm:block"
                style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
              >
                {member.bio}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
