import { chromium } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

const OUT_DIR = process.argv[2] || path.resolve('screenshots');
const QUESTION = process.argv[3] || 'Explain the principle of superposition of waves.';
fs.mkdirSync(OUT_DIR, { recursive: true });

const BASE = 'http://127.0.0.1:3000';
const ANSWER_TIMEOUT = 900000;

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
  const page = await context.newPage();
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // 1. Style fingerprint: expand the registered educator's profile.
  const detail = page.locator('details.educator-detail').first();
  await detail.locator('summary').first().click();
  await page.waitForTimeout(600);
  await detail.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT_DIR, 'r07-persona-fingerprint.png') });
  console.log('captured r07-persona-fingerprint.png');

  // 2. Persona-conditioned answer: pick the educator, then ask.
  const styleSelect = page.getByLabel('Teaching style');
  const options = await styleSelect.locator('option').all();
  let personaValue = '';
  for (const opt of options) {
    const value = await opt.getAttribute('value');
    if (value) { personaValue = value; break; }
  }
  if (!personaValue) throw new Error('No persona option available in the Teaching style select');
  await styleSelect.selectOption(personaValue);
  await page.waitForTimeout(400);

  // The registered lecture is Class 11 material, so ask against PUC1.
  await page.locator('#study-form select').nth(1).selectOption('PUC1');
  await page.waitForTimeout(300);

  await page.locator('#study-form textarea').first().fill(QUESTION);
  await page.getByRole('button', { name: 'Ask StudyMate', exact: false }).first().click();
  await page.waitForSelector('section.answer-panel', { timeout: ANSWER_TIMEOUT });
  await page.waitForTimeout(1500);
  await page.locator('section.answer-panel').first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(OUT_DIR, 'r08-persona-answer.png') });
  console.log('captured r08-persona-answer.png');

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
