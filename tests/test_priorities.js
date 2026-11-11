const assert = require('node:assert/strict');
const {redistribute} = require('../citizensolver/static/priorities.js');
let weights = {firepower:50, shields:0, stealth:50, handling:0, speed:0, hull:0, armor:0, cargo:0};
weights = redistribute(weights,'shields',20);
assert.deepEqual(weights,{firepower:40,shields:20,stealth:40,handling:0,speed:0,hull:0,armor:0,cargo:0});
weights = redistribute(weights,'firepower',100);
assert.equal(weights.stealth,0);
weights = redistribute(weights,'firepower',0);
assert.equal(Object.values(weights).reduce((a,b)=>a+b),100);
// Exercise repeated edits, endpoints, all-zero peers and rounding remainders.
for (const key of Object.keys(weights)) for(let value=0;value<=100;value++) {
  weights = redistribute(weights,key,value);
  assert.equal(weights[key],value);
  assert.equal(Object.values(weights).reduce((a,b)=>a+b),100);
  assert.ok(Object.values(weights).every(v=>Number.isInteger(v)&&v>=0&&v<=100));
}
assert.throws(()=>redistribute(weights,'bad',10));
console.log('Priority budget: 808 sequential edits preserved exactly 100%.');
