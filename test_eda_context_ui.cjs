const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('visualizationtools.js', 'utf8');
new vm.Script(source);
const start = source.indexOf('function renderGenerationContext(rawContext) {');
const end = source.indexOf('\nfunction formatHypothesisBullets', start);
const sandbox = vm.createContext({});
vm.runInContext(source.slice(start, end), sandbox);
const render = value => sandbox.renderGenerationContext(value);
const context = {dataset: {row_count: 5, target: 'mass', columns: [{name: 'mass', dtype: 'float64'}]},
    eda_agent: {status: 'completed', summary: 'Five records', execution_report: 'Ran Python and SQL.',
        hypothesis_directions: ['Compare groups'], limitations: ['Exploratory'], query_count: 2,
        data_access: {backend_rows: 5}, custom_field: 'Preserve this field',
        evidence: [{query: {operation: 'python', code: 'if len(df) > 0:\n    result = "<script>"'}, result: {result: {mean: 1.23456789012345}}},
                   {query: {operation: 'sql', sql: 'SELECT <mass> FROM dataset'}, result: {error: '<script>alert(1)</script>'}}]}};
const html = render(JSON.stringify(context));
assert.equal(html, render(context));
for (const text of ['Agent Report','Agent Output','Step 1: Python code','Step 2: SQL query','Preserve this field','1.23456789012345']) assert.ok(html.includes(text), text);
assert.equal((html.match(/<section /g)||[]).length,2);
assert.equal((html.match(/class="language-python"/g)||[]).length,1);
assert.ok(html.includes('if len(df) &gt; 0:\n    result = &quot;&lt;script&gt;&quot;'));
assert.ok(!source.includes('sunburst-top10'));
assert.ok(!source.includes('Top 10 Hypotheses by Category'));
assert.ok(!html.includes('Dataset features'));
assert.ok(!html.includes('<script>alert(1)</script>'));
assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
const output = html.slice(html.indexOf('<h3 id="eda-output-title"'));
const escape = value => value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
assert.ok(output.includes(escape(JSON.stringify(context,null,2))), 'Output must contain the entire handoff without precision loss');
assert.ok(render(null).includes('No EDA output'));
assert.ok(render('{bad').includes('No EDA report'));
assert.ok(render({dataset:{}}).includes('No EDA report'));
assert.ok(fs.readFileSync('helios.html','utf8').includes('visualizationtools.js?v=eda-code-sunburst-5'));
console.log('EDA record, query/error display, exact Output and HTML escaping checks passed.');
