'use client';

import { motion } from 'framer-motion';

const COPY = [
  'FSCA-licensed FSP No. 53746',
  'Segregated client accounts',
  'ZAR deposits and withdrawals',
];

export default function Features() {
  return (
    <motion.section
      className="py-24"
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
    >
      <ul>
        {COPY.map((copy, i) => (
          <li key={copy} data-index={i}>
            {copy}
          </li>
        ))}
      </ul>
    </motion.section>
  );
}
