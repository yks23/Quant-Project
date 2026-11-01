import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import puppeteer from 'puppeteer-core';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
process.chdir(root);
const hash = (file) => createHash('sha256').update(readFileSync(file)).digest('hex');
const manifest = JSON.parse(readFileSync('slides/dist/manifest.json', 'utf8'));
for (const [file, expected] of Object.entries({ ...manifest.input_sha256, ...manifest.output_sha256 })) {
  if (hash(file) !== expected) throw new Error(`Build is stale: ${file}`);
}
const executablePath = [process.env.BROWSER_PATH,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Google/Chrome/Application/chrome.exe'),
].find((candidate) => candidate && existsSync(candidate));
if (!executablePath) throw new Error('Set BROWSER_PATH to a Chromium browser for layout QA.');
mkdirSync('slides/qa/rendered', { recursive: true });
const browser = await puppeteer.launch({ executablePath, headless: true });
let checks;
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
  await page.setOfflineMode(true);
  await page.goto(pathToFileURL(path.join(root, 'slides/.build/check.html')).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  checks = await page.evaluate(() => {
    const slides = [...document.querySelectorAll('section')];
    return slides.map((slide, index) => {
      const bounds = slide.getBoundingClientRect();
      const scale = bounds.width / 1280;
      const overflow = [];
      for (const el of slide.querySelectorAll('h1, h2, p, table, pre, blockquote, li, mjx-container')) {
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height || el.closest('header, footer')) continue;
        if (r.left < bounds.left + 55 * scale || r.right > bounds.right - 55 * scale ||
            r.top < bounds.top + 55 * scale || r.bottom > bounds.bottom - 56 * scale) {
          overflow.push({ tag: el.tagName, text: el.textContent.slice(0, 90),
            box: [r.left - bounds.left, r.top - bounds.top, r.width, r.height].map((x) => Math.round(x / scale)) });
        }
      }
      const flow = [...slide.children].filter((el) => !['HEADER', 'FOOTER'].includes(el.tagName))
        .map((el) => ({ rect: el.getBoundingClientRect(), tag: el.tagName }))
        .filter(({ rect }) => rect.height > 0);
      const overlap = flow.slice(1).flatMap((item, i) => flow[i].rect.bottom > item.rect.top + 2 * scale
        ? [`${flow[i].tag}/${item.tag}`] : []);
      return { page: index + 1, title: slide.querySelector('h1')?.textContent,
        overflow, overlap, runningFurniture: slide.querySelectorAll('header, footer').length,
        mathErrors: slide.querySelectorAll('mjx-merror, [data-mjx-error]').length,
        brokenImages: [...slide.querySelectorAll('img')].filter((img) => !img.complete || !img.naturalWidth).length,
        imageCount: slide.querySelectorAll('img').length };
    });
  });
  const frames = await page.$$('svg[data-marpit-svg]');
  if (frames.length !== checks.length) throw new Error('Slide frame count does not match section count');
  for (let i = 0; i < frames.length; i++) {
    await frames[i].screenshot({ path: `slides/qa/rendered/slide-${String(i + 1).padStart(2, '0')}.png` });
  }
  const runtimeErrors = [];
  page.on('pageerror', (error) => runtimeErrors.push(error.message));
  await page.goto(pathToFileURL(path.join(root, 'slides/dist/quant-study.html')).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const first = await page.evaluate(() => document.querySelector('.bespoke-marp-active section')?.id);
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction((id) => document.querySelector('.bespoke-marp-active section')?.id !== id, {}, first);
  const second = await page.evaluate(() => document.querySelector('.bespoke-marp-active section')?.id);
  if (!first || !second || first === second || runtimeErrors.length) {
    throw new Error(`Offline presentation navigation failed: ${JSON.stringify({ first, second, runtimeErrors })}`);
  }
} finally {
  await browser.close();
}
const failures = checks.filter((item) => item.overflow.length || item.overlap.length || item.runningFurniture || item.mathErrors || item.brokenImages);
const result = { slides: checks.length, image_count: checks.reduce((n, x) => n + x.imageCount, 0),
  offline_navigation: 'passed', failures, pages: checks,
  html_sha256: hash('slides/dist/quant-study.html'), pdf_sha256: hash('slides/dist/quant-study.pdf') };
writeFileSync('slides/qa/layout.json', JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ slides: checks.length, failures, offline_navigation: 'passed' }, null, 2));
if (checks.length !== 29 || result.image_count !== 6 || failures.length) process.exitCode = 1;
