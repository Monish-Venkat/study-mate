import { chromium } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

const OUT_DIR = process.argv[2] || path.resolve('screenshots');
fs.mkdirSync(OUT_DIR, { recursive: true });

const BASE = 'http://127.0.0.1:3000';

// Real tool tabs: clicking these swaps the main panel content.
const tabs = [
  { label: 'Ask a question', file: '01-ask.png' },
  { label: 'Guided learning', file: '02-guided-learning.png' },
  { label: 'Revision notes', file: '03-revision-notes.png' },
  { label: 'Past paper review', file: '04-past-paper-review.png' },
  { label: 'Practice paper', file: '05-practice-paper.png' },
];

async function resetScroll(page) {
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    document.querySelectorAll('*').forEach((el) => {
      if (el.scrollTop > 0) el.scrollTop = 0;
    });
  });
  await page.waitForTimeout(200);
}

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);

  for (const tab of tabs) {
    const btn = page.getByRole('button', { name: tab.label, exact: false }).first();
    await btn.click();
    await page.waitForTimeout(600);
    await resetScroll(page);
    await page.screenshot({ path: path.join(OUT_DIR, tab.file) });
    console.log('captured', tab.file);
  }

  // "YouTube persona" and "Study plan & scores" are scroll-to-anchor shortcuts
  // within the currently active tool, not separate tabs. Go back to "Ask a
  // question" first so the anchor scroll lands in a natural, default context.
  await page.getByRole('button', { name: 'Ask a question', exact: false }).first().click();
  await page.waitForTimeout(400);
  await resetScroll(page);

  await page.getByRole('button', { name: 'YouTube persona', exact: false }).first().click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(OUT_DIR, '06-youtube-persona.png') });
  console.log('captured 06-youtube-persona.png');

  await page.getByRole('button', { name: 'Study plan & scores', exact: false }).first().click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(OUT_DIR, '07-study-plan.png') });
  console.log('captured 07-study-plan.png');

  // Teacher tools is a separate route
  await page.goto(`${BASE}/teacher`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(OUT_DIR, '08-teacher-tools.png') });
  console.log('captured 08-teacher-tools.png');

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
