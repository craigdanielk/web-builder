'use client';

import { motion } from 'framer-motion';

const COPY = [
  'FSCA-licensed FSP No. 53746',
  'Segregated client accounts',
  'ZAR deposits and withdrawals',
];

// The historical failure: token sanitization substituted the value out of
// `key={copy}` and left a bare `key=`, which the Next.js (SWC) parser reported
// as `Expected '</', got 'ident'`. Nothing in stage_validate caught it — the
// braces balance and `export default` is present.
export default function Features() {
  return (
    <motion.section
      className="py-24"
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
    >
      <ul>
        {COPY.map((copy, i) => (
          <li key= data-index={i}>
            {copy}
          </li>
        ))}
      </ul>
    </motion.section>
  );
}
