import { chromium } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

const OUT_DIR = process.argv[2] || path.resolve('screenshots');
// Comma-separated subset, e.g. "summary,pyq". Defaults to every tool.
const ONLY = (process.argv[3] || '').split(',').map((s) => s.trim()).filter(Boolean);
fs.mkdirSync(OUT_DIR, { recursive: true });

const BASE = 'http://127.0.0.1:3000';
// A local 7B model on CPU needs minutes per answer.
const ANSWER_TIMEOUT = 3600000;

function log(...args) {
  console.log(new Date().toISOString().slice(11, 19), ...args);
}

async function selectCourse(page, { subject, level }) {
  await page.locator('#study-form select').first().selectOption(subject);
  await page.locator('#study-form select').nth(1).selectOption(level);
  await page.waitForTimeout(300);
}

async function submitAndWait(page, buttonName, file) {
  const button = page.locator('#study-form button[type="submit"]');
  await button.waitFor({ state: 'visible', timeout: 30000 });
  log('clicking', buttonName);
  await button.click();
  // Confirm the request actually started before committing to the long wait.
  await page.waitForSelector('.loading-state', { timeout: 30000 });
  log('request in flight, waiting for answer...');
  await page.waitForSelector('section.answer-panel', { timeout: ANSWER_TIMEOUT });
  await page.waitForTimeout(1500);
  await page.locator('section.answer-panel').first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(OUT_DIR, file) });
  log('captured', file);
}

async function openTool(page, label) {
  const btn = page.locator('nav[aria-label="Study tools"] button', { hasText: label }).first();
  await btn.click();
  await page.waitForTimeout(800);
}

const steps = {
  ask: async (page) => {
    await openTool(page, 'Ask a question');
    await selectCourse(page, { subject: 'physics', level: 'PUC2' });
    await page.locator('#study-form textarea').first().fill('Explain the principle of superposition of waves.');
    await submitAndWait(page, 'Ask StudyMate', 'r01-ask-result.png');
  },
  socratic: async (page) => {
    await openTool(page, 'Guided learning');
    await selectCourse(page, { subject: 'physics', level: 'PUC2' });
    await page.locator('#study-form textarea').first().fill('Help me understand electric potential.');
    await submitAndWait(page, 'Start guided learning', 'r02-guided-result.png');
  },
  summary: async (page) => {
    await openTool(page, 'Revision notes');
    await selectCourse(page, { subject: 'physics', level: 'PUC2' });
    const chapter = page.locator('#study-form input[placeholder="e.g. Wave optics"]');
    await chapter.waitFor({ state: 'visible', timeout: 30000 });
    await chapter.fill('Wave optics');
    log('chapter =', await chapter.inputValue());
    await submitAndWait(page, 'Create revision notes', 'r03-revision-result.png');
  },
  pyq: async (page) => {
    await openTool(page, 'Past paper review');
    await selectCourse(page, { subject: 'physics', level: 'PUC2' });
    await submitAndWait(page, 'Review past papers', 'r04-pyq-result.png');
  },
  mock: async (page) => {
    await openTool(page, 'Practice paper');
    await selectCourse(page, { subject: 'physics', level: 'PUC2' });
    await submitAndWait(page, 'Generate practice paper', 'r05-mock-result.png');
  },
  planner: async (page) => {
    await openTool(page, 'Ask a question');
    await page.locator('#learning-plan input[type="date"]').first().fill('2026-12-15');
    await page.locator('#learning-plan textarea').first()
      .fill('Wave optics\nElectric charges and fields\nCurrent electricity\nMagnetism\nSemiconductors');
    await page.locator('#learning-plan button.primary-button').first().click();
    await page.waitForSelector('.plan-result', { timeout: 120000 });
    await page.waitForTimeout(1000);
    await page.locator('.plan-result').first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, 'r06-planner-result.png') });
    log('captured r06-planner-result.png');
  },
};

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
  const page = await context.newPage();
  // Without this, a non-actionable element hangs the script forever.
  page.setDefaultTimeout(45000);

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  const names = ONLY.length ? ONLY : Object.keys(steps);
  for (const name of names) {
    if (!steps[name]) throw new Error(`Unknown step: ${name}`);
    log('=== step:', name);
    await steps[name](page);
  }

  await browser.close();
  log('done');
}

main().catch((err) => {
  console.error('FAILED:', err && err.message ? err.message : err);
  process.exit(1);
});
