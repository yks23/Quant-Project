import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
process.chdir(root);
const hash = (file) => createHash('sha256').update(readFileSync(file)).digest('hex');
const assets = JSON.parse(readFileSync('slides/assets/manifest.json', 'utf8'));
for (const [file, sha] of Object.entries(assets.inputs_sha256)) {
  if (hash(file) !== sha) throw new Error(`Changed figure evidence: ${file}`);
}
for (const [file, entry] of Object.entries(assets.outputs)) {
  if (hash(file) !== entry.sha256) throw new Error(`Changed figure: ${file}; rerun make figures`);
}
if (hash('slides/scripts/make_figures.py') !== assets.generator_sha256) {
  throw new Error('Figure generator changed; rerun make figures');
}

const source = readFileSync('slides/quant-study.md', 'utf8');
const embedded = source.replace(/!\[([^\]]*)\]\(assets\/([a-z0-9-]+\.svg)\)/g, (_, alt, name) => {
  const data = readFileSync(`slides/assets/${name}`).toString('base64');
  const width = alt.match(/width:(\d+)px/)?.[1] ?? '1100';
  return `<img src="data:image/svg+xml;base64,${data}" width="${width}" alt="${name}">`;
});
mkdirSync('slides/.build', { recursive: true });
mkdirSync('slides/dist', { recursive: true });
writeFileSync('slides/.build/embedded.md', embedded);
const cli = require.resolve('@marp-team/marp-cli/marp-cli.js');
for (const format of ['html', 'pdf']) {
  const args = [cli, 'slides/.build/embedded.md', '--config-file', 'slides/marp.config.cjs',
    '--no-stdin', '-o', `slides/dist/quant-study.${format}`];
  if (format === 'pdf') args.push('--pdf');
  const result = spawnSync(process.execPath, args, { stdio: 'inherit' });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
const check = spawnSync(process.execPath, [cli, 'slides/.build/embedded.md',
  '--config-file', 'slides/marp.config.cjs', '--no-stdin', '--template', 'bare',
  '-o', 'slides/.build/check.html'], { stdio: 'inherit' });
if (check.status !== 0) process.exit(check.status ?? 1);
const inputs = ['slides/quant-study.md', 'slides/theme/lecture.css', 'slides/marp.config.cjs',
  'slides/scripts/build.mjs', 'slides/assets/manifest.json', 'package-lock.json'];
const outputs = ['slides/dist/quant-study.html', 'slides/dist/quant-study.pdf'];
writeFileSync('slides/dist/manifest.json', JSON.stringify({
  purpose: 'Marp presentation of existing evidence, not a new research edition',
  marp_cli: require('@marp-team/marp-cli/package.json').version,
  input_sha256: Object.fromEntries(inputs.map((file) => [file, hash(file)])),
  output_sha256: Object.fromEntries(outputs.map((file) => [file, hash(file)])),
}, null, 2) + '\n');
