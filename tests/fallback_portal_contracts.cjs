const assert=require('assert'),fs=require('fs');
const source=fs.readFileSync('docs/portal.js','utf8');
assert.ok(source.includes("labels.push(first?'Fallback':'Fallback provider')"));
assert.ok(source.includes("labels.push(first[0])"));
assert.ok(source.includes("label==='Fallback'||label.startsWith('FALLBACK BUILD:')?'badge fallback'"));
assert.ok(source.includes('On Android 9/10 Obtainium cannot read signers; Android itself still refuses any update signed by another key'));
assert.ok(fs.readFileSync('docs/index.html','utf8').includes('.badge.fallback'));
console.log('FALLBACK_PORTAL_CONTRACTS_PASS=1');
