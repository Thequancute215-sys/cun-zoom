/** Use the pinned Understand Anything core validator, not a substitute schema. */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [pluginRoot, ...files] = process.argv.slice(2);
if (!pluginRoot || !files.length) throw new Error('Usage: node scripts/validate_workflow_graphs.mjs PLUGIN_ROOT GRAPH...');
const modulePath = path.join(pluginRoot, 'packages', 'core', 'dist', 'schema.js');
if (!fs.existsSync(modulePath)) throw new Error('Build @understand-anything/core in the pinned plugin checkout first.');
const { validateGraph } = await import(pathToFileURL(modulePath).href);
for (const filename of files) {
  const original = JSON.parse(fs.readFileSync(filename, 'utf8'));
  const result = validateGraph(original);
  // Do not silently publish a graph whose nodes/edges the tolerant validator drops.
  if (!result.success || result.issues.length) {
    throw new Error(`${filename}: ${JSON.stringify(result.errors ?? result.issues)}`);
  }
  console.log(`Understand Anything schema OK: ${path.basename(filename)} (${original.nodes.length} nodes, ${original.edges.length} edges)`);
}
