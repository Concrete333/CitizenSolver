/* Integer percentages, proportional redistribution, deterministic rounding. */
(function (root) {
  function redistribute(weights, changed, value) {
    const keys = Object.keys(weights);
    if (!keys.includes(changed) || keys.length < 2 || !Number.isFinite(value)) throw new Error('Invalid priority');
    const next = Math.max(0, Math.min(100, Math.round(value)));
    const others = keys.filter(k => k !== changed);
    const previous = others.reduce((sum, k) => sum + weights[k], 0);
    const portions = others.map((key, index) => {
      const exact = (100 - next) * (previous ? weights[key] / previous : 1 / others.length);
      return {key, index, value: Math.floor(exact), fraction: exact - Math.floor(exact)};
    });
    let remainder = 100 - next - portions.reduce((sum, p) => sum + p.value, 0);
    portions.sort((a,b) => b.fraction - a.fraction || a.index - b.index);
    for (const p of portions) if (remainder-- > 0) p.value++;
    const result = {...weights, [changed]: next};
    for (const p of portions) result[p.key] = p.value;
    return result;
  }
  if (typeof module !== 'undefined') module.exports = {redistribute};
  else root.PriorityBudget = {redistribute};
})(typeof globalThis !== 'undefined' ? globalThis : this);
