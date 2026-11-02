const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.textContent = ''; }
    appendChild(node) { this.children.push(node); return node; }
    replaceChildren(...nodes) { this.children = nodes; }
}
const context = { document: { createElement: tag => new Element(tag) } };
vm.createContext(context);
const source = fs.readFileSync(__dirname + '/helios_ui.js', 'utf8');
vm.runInContext(source.slice(0, source.indexOf('/**')), context);
const panel = new Element('div');
const collect = node => [node, ...node.children.flatMap(collect)];
const report = { status: 'completed', summary: 'Summary', accepted_count: 1, rejected_count: 1,
    unanswered_aspects: ['Unanswered'], ranked_hypotheses: [
        { rank: 2, score: 0, accepted: false, reason: '<img src=x>', hypothesis: { Hypothesis_Text: 'Second' } },
        { rank: 1, score: 9.5, accepted: true, reason: 'Relevant', hypothesis: { Hypothesis_Text: 'First' } }
    ] };
context.renderRankingReport(panel, report);
const body = collect(panel).find(node => node.tag === 'tbody');
assert.deepEqual(body.children.map(row => row.children[0].textContent), ['1', '2']);
assert.equal(body.children[0].children[2].textContent, 'First');
assert.equal(body.children[0].children[1].textContent, '9.5 / 10');
assert.equal(body.children[1].children[3].textContent, 'Rejected');
assert.equal(body.children[1].children[4].textContent, '<img src=x>');
assert.equal(body.children[1].children[4].children.length, 0);
context.renderRankingReport(panel, { status: 'skipped', reason: 'No query' });
assert(collect(panel).some(node => node.textContent === 'No query'));
assert(!collect(panel).some(node => node.tag === 'table'));
context.renderRankingReport(panel, null);
assert(collect(panel).some(node => node.textContent.includes('No Ranking Agent report')));
console.log('Ranking UI ordering, decisions, safe text and empty states OK');


