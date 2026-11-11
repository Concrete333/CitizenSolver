'use strict';
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (value, decimals = 0) => value == null ? '—' : Number(value).toLocaleString(undefined, {maximumFractionDigits: decimals});
const definitions = {
  firepower: ['Firepower', 'Gun damage over the engagement'],
  shields: ['Shielding', 'Total shield capacity'],
  stealth: ['Stealth', 'Lower estimated EM and IR'],
  handling: ['Maneuverability', 'Average rated pitch and yaw'],
  speed: ['Straight-line speed', 'Maximum rated flight speed'],
  hull: ['Hull', 'Total part HP · fixed hull trait'],
  armor: ['Armor', 'Armor HP · fixed hull trait'],
  cargo: ['Cargo', 'Grid SCU · fixed hull trait'],
};
const presets = {
  balanced: {weights: {firepower:50, stealth:50}, text:'Equal importance to firepower and low signatures.'},
  pve: {weights: {firepower:65, shields:25, handling:10}, text:'Damage and shields first, with a small handling preference.'},
  pvp: {weights: {handling:75, firepower:20, shields:5}, text:'Handling dominates this starting point. Adjust for your flying style.'},
  cargo: {weights: {cargo:65, shields:15, speed:15, handling:5}, text:'Capacity first, then survivability and travel speed. Route profit is not modeled.'},
};
let options, lastResult, busy = false, weights = makeWeights(presets.balanced.weights);
function makeWeights(values) { return Object.fromEntries(Object.keys(definitions).map(k => [k, values[k] || 0])); }
function scope() {return document.querySelector('input[name="scope"]:checked').value;}
function setStatus(text, kind = '') {$('search-status').textContent = text; $('search-status').className = 'status ' + kind;}
function markDirty() {if (lastResult && !busy) setStatus('Settings changed. Find my fits again to update the results below.', 'dirty');}
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Request failed');
  return value;
}
function renderPriorityControls() {
  $('priorities').innerHTML = Object.entries(definitions).map(([key, [name, hint]]) => `<div class="priority"><label for="weight-${key}"><span class="stat-name">${name}</span><output id="value-${key}" for="weight-${key}"></output></label><input id="weight-${key}" data-weight="${key}" type="range" min="0" max="100" step="1" aria-label="${name} priority"><small>${hint}</small></div>`).join('');
  $('priorities').addEventListener('input', event => {
    const key = event.target.dataset.weight;
    if (!key) return;
    weights = PriorityBudget.redistribute(weights, key, Number(event.target.value));
    document.querySelectorAll('[data-preset]').forEach(b => b.classList.remove('active'));
    $('preset-description').textContent = 'Your custom mix. Priorities always total 100%.';
    updateWeights();
  });
  updateWeights();
}
function updateWeights() {
  for (const [key, value] of Object.entries(weights)) {
    const input = $('weight-' + key);
    input.value = value; input.style.setProperty('--value', value + '%');
    input.setAttribute('aria-valuetext', value + ' percent priority');
    $('value-' + key).textContent = value + '%';
  }
  $('total').innerHTML = `${Object.values(weights).reduce((a,b) => a+b,0)}<span>% allocated</span>`;
}
function updateGoal() {
  const custom = $('goal').value === 'custom';
  const objective = options.objectives.find(o => o.id === $('goal').value);
  $('goal-description').textContent = objective?.detail || '';
  $('damage-retention').hidden = !['balanced','stealth'].includes($('goal').value);
  for (const id of ['min-shield','min-range','duration']) $(id).disabled = busy || $('goal').value === 'cargo';
  document.querySelector('.priority-panel').classList.toggle('inactive', !custom);
  document.querySelectorAll('[data-weight]').forEach(el => {el.disabled = busy || !custom;});
  if (!custom) $('preset-description').textContent = 'Single goal active. Choose an activity preset to use the priority budget.';
  else $('preset-description').textContent = 'Your priorities determine the ranking. Every percentage point is shared.';
  $('fixed-traits').textContent = scope() === 'ship' ? 'Cargo, hull and armor are mostly hull choices. On one ship, their priorities cannot create extra capacity.' : 'Comparing ships lets cargo, hull and armor influence the ranking. Equipment is optimized for each eligible ship.';
}
function updateScope() {
  $('ship-fields').hidden = scope() !== 'ship'; $('class-fields').hidden = scope() !== 'class';
  updateGoal();
}
function shipOptions() {
  const selected = $('ship').value;
  const query = $('ship-filter').value.trim().toLowerCase();
  const rows = options.ships.filter(s => (s.name + ' ' + s.id).toLowerCase().includes(query));
  $('ship').replaceChildren(...rows.map(s => new Option(s.name + (options.ships.filter(x => x.name === s.name).length > 1 ? ` · ${s.id}` : ''), s.id)));
  if (rows.some(s => s.id === selected)) $('ship').value = selected;
  shipFacts();
}
function shipFacts() {
  const ship = options.ships.find(s => s.id === $('ship').value);
  if (!ship) {$('ship-facts').textContent = 'No matching ship. Try another name.'; return;}
  const m = options.market.ships[ship.id.toLowerCase()] || {};
  $('ship-facts').textContent = `${ship.role || 'Role unknown'} · ${m.hangar ? m.hangar + ' hangar class' : 'Hangar fit unknown'} · ${m.usd ? '$' + number(m.usd) + ' reference' : 'USD price unknown'} · ${m.auec ? number(m.auec) + ' aUEC' : 'No recorded shop price'}`;
}
function readRequest() {
  const numeric = id => $(id).value === '' ? null : Number($(id).value);
  const quick = $('depth').value === 'quick';
  return {scope:scope(), ship:$('ship').value, role:$('role').value, goal:$('goal').value,
    max_crew:numeric('crew'), max_usd:numeric('max-usd'), max_auec:numeric('max-auec'),
    require_ingame:$('ingame').checked, hangar:$('hangar').value || null,
    search:{weights:{...weights}, duration:$('goal').value === 'cargo' ? 120 : numeric('duration'), damage_floor:Number($('retention').value)/100,
      min_shield:$('goal').value === 'cargo' ? 0 : numeric('min-shield') || 0,
      min_range:$('goal').value === 'cargo' ? 0 : numeric('min-range') || 0,
      beam:quick ? 3 : 6, passes:quick ? 1 : 2, max_evaluations:quick ? 3000 : 15000, limit:5}};
}
function setBusy(value) {
  busy = value;
  document.querySelectorAll('#solver input, #solver select, #solver button[data-preset], #solver button[type="submit"], #refresh-market').forEach(el => {el.disabled = value;});
  document.querySelector('[data-preset="cargo"]').disabled = value;
  // The unreleased mining preset has no data-preset attribute and stays disabled.
  for (const id of ['solve','solve-priorities']) $(id).innerHTML = value ? 'Searching… <span>◌</span>' : 'Find my fits <span>↗</span>';
  $('progress').hidden = !value;
  updateGoal();
}
async function runJob(path, body) {
  const job = await api(path, body);
  sessionStorage.setItem('citizensolver-job', JSON.stringify({id:job.id, path}));
  return await followJob(job.id, path);
}
async function followJob(id, path) {
  // Polling is confined to the UI; the server performs one search per job.
  for (;;) {
    const state = await api('/api/jobs/' + id);
    if (state.status === 'error') {sessionStorage.removeItem('citizensolver-job'); throw new Error(state.error);}
    if (state.status === 'complete') {sessionStorage.removeItem('citizensolver-job'); return state.result;}
    const p = state.progress;
    if (p.total) {$('progress').max = p.total; $('progress').value = p.done;}
    else $('progress').removeAttribute('value');
    setStatus(path.includes('market') ? 'Refreshing reference prices and hangar classes…' : `Searching ${p.ship} · ${p.done} of ${p.total || '…'} ships complete`);
    await new Promise(resolve => setTimeout(resolve, 800));
  }
}
function download(value, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value,null,2)], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const displayMetrics = [
  ['duration_dps','Engagement damage','DPS'], ['shield_hp','Shield capacity','HP'],
  ['em','Estimated EM','',true], ['ir','Estimated IR','',true],
  ['pitch','Pitch','°/s'], ['yaw','Yaw','°/s'], ['max_speed','Max speed','m/s'], ['cargo_scu','Cargo grid','SCU'],
];
function metricHTML(metrics, [key,label,unit,lower], baseline) {
  const value = metrics[key], base = baseline?.metrics[key];
  let delta = '';
  if (value != null && base != null) {
    const difference = value - base;
    delta = Math.abs(difference) < .005 ? '<span class="delta">Same as stock</span>' : `<span class="delta ${(lower ? difference<0 : difference>0) ? 'up' : 'down'}">${difference>0?'+':''}${number(difference,1)} vs stock</span>`;
  }
  return `<div class="metric"><label>${label}</label><strong>${number(value,1)}<span class="unit">${unit}</span></strong>${delta}</div>`;
}
function weaponReachHTML(weapons, minimum) {
  if (!weapons?.length) return '';
  const groups = new Map();
  for (const weapon of weapons) {
    const group = groups.get(weapon.id) || {...weapon, count:0, burst:0, sustained:0};
    group.count++; group.burst += weapon.burst_dps; group.sustained += weapon.sustained_dps;
    groups.set(weapon.id, group);
  }
  const rows = [...groups.values()].map(w => `<tr><td>${w.count} × ${escapeHTML(w.name)}</td><td>${number(w.range_m)} m</td><td>${number(w.burst,1)}</td><td>${number(w.sustained,1)}</td><td>${number(w.pellets_per_shot)}</td></tr>`).join('');
  const spread = weapons.some(w => w.pellets_per_shot > 1);
  return `<section class="fit-details weapon-reach" aria-label="Damage and weapon reach"><strong>Damage & weapon reach</strong><p>${minimum ? `Every gun must reach at least ${number(minimum)} m.` : 'Any range allowed in this search.'} DPS below is the total for each weapon group, assuming all shots hit.</p><div class="table-wrap"><table><thead><tr><th>Weapons</th><th>Listed reach</th><th>Burst DPS</th><th>Repeating DPS</th><th>Pellets / shot</th></tr></thead><tbody>${rows}</tbody></table></div><p>${spread ? '<strong>Scattergun trade-off:</strong> full damage requires every pellet to hit. Spread can reduce damage well before the listed reach. ' : ''}Listed reach is a range limit, not a full-damage guarantee. Target size, spread and hit probability are not modeled.</p></section>`;
}
function resultHTML(r, index, report) {
  const m = r.metrics, market = r.market || {}, cargoOnly = r.kind === 'ship';
  const scoreText = report.goal === 'custom' ? `${number(r.score*100,1)}` : report.goal === 'cargo' ? number(m.cargo_scu) : '';
  const scoreLabel = report.goal === 'custom' ? 'PREFERENCE SCORE / 100' : 'CARGO SCU';
  const baseline = report.baseline?.ship.id === r.ship.id ? report.baseline : null;
  const pips = r.power?.allocation || {};
  const loadout = (r.loadout || []).map(i => `<tr><td>${escapeHTML((i.path || [i.hardpoint]).map(p=>p.replace(/^hardpoint_/,'').replaceAll('_',' ')).join(' › '))}</td><td class="${i.changed?'changed':''}">${escapeHTML(i.name)}${i.changed?' · changed':''}</td><td>${escapeHTML(i.type)} · S${i.size ?? '?'}</td><td>${pips[i.port] ?? (i.type==='WeaponGun'?'Shared':'—')}</td></tr>`).join('');
  const price = market.usd ? '$'+number(market.usd)+' reference' : 'USD price unknown';
  const auec = market.auec ? number(market.auec)+' aUEC' : 'No recorded in-game listing';
  const extraStats = [['burst_dps','Burst damage','DPS'],['sustained_dps','Repeating damage¹','DPS'],['alpha','One salvo','damage'],['shield_regen','Shield regeneration','HP/s'],['scm_speed','SCM speed','m/s'],['roll','Roll','°/s'],['hull_hp','Total part HP','HP'],['armor_hp','Armor rating','HP']];
  return `<article class="panel fit-card"><div class="fit-top"><div><p class="eyebrow">FIT ${String(index+1).padStart(2,'0')} / ${index===0?'HIGHEST RANKED FOUND':'ALTERNATIVE'}</p><h3>${escapeHTML(r.ship.name)}</h3><div class="role">${escapeHTML(r.ship.role)} · ${cargoOnly?'Cargo comparison':'Optimized equipment · pilot guns'}</div></div>${scoreText?`<div class="fit-score"><strong>${scoreText}</strong><span>${scoreLabel}</span></div>`:''}</div>
    <div class="price-strip"><span>${price}</span><span>${auec}</span><span>${market.hangar ? escapeHTML(market.hangar)+' hangar class' : 'Hangar fit unknown'}</span></div>
    <div class="metric-grid">${displayMetrics.map(d => metricHTML(m,d,baseline)).join('')}</div>
    ${cargoOnly ? '' : weaponReachHTML(r.weapons, report.request.search.min_range)}
    ${cargoOnly?'':`<details class="fit-details"><summary>Equipment & power allocation · ${Object.keys(r.swaps).length} changed ports</summary><p>Power: ${r.power.used} / ${r.power.available} pips · Cooling: ${number(r.cooling.demand,1)} / ${number(r.cooling.available,1)} modeled units. Priority percentages above are preferences, not these equipment pips.</p><div class="table-wrap"><table><thead><tr><th>Mount / port</th><th>Component</th><th>Type</th><th>Pips</th></tr></thead><tbody>${loadout}</tbody></table></div><div class="pip-list"><span class="pip-chip">Shared weapons: ${pips.weapons ?? 0} pips</span></div><p>Only supported powered components are listed. Other mounts stay stock; shop availability of these components is not verified.</p></details><details class="fit-details"><summary>More stats & ranking breakdown</summary><div class="metric-grid">${extraStats.map(d=>metricHTML(m,d,baseline)).join('')}</div><p>¹ Repeating DPS before ballistic ammunition runs out. Engagement DPS accounts for the selected ${r.scenario.duration_seconds}-second duration. All damage assumes hits; distortion is reported separately in the saved build.</p>${r.priority_scores?`<div class="table-wrap"><table><thead><tr><th>Priority</th><th>Your weight</th><th>Stat score / 100</th><th>Points earned</th></tr></thead><tbody>${Object.entries(r.priority_scores).map(([k,v])=>`<tr><td>${definitions[k][0]}</td><td>${report.request.search.weights[k]}%</td><td>${number(v,1)}</td><td>${number(v*report.request.search.weights[k]/100,1)}</td></tr>`).join('')}</tbody></table></div>`:''}</details>`}
    <details class="fit-details"><summary>Assumptions & source details</summary>${(r.assumptions || []).map(s=>`<p>${escapeHTML(s)}</p>`).join('')}<p>Hull and armor ratings do not predict damage to destruction. Hangar fit: ${escapeHTML(market.hangar_basis || 'Not known')} USD prices are reference values, not a current purchase offer. In-game prices are cached shop listings; check them in game before buying.</p><p>FleetYards record updated: ${escapeHTML(market.updated_at || 'unknown')}. Cache downloaded: ${escapeHTML(report.market_downloaded_at || 'not downloaded')}.</p>${(market.locations||[]).map(p=>`<p>${escapeHTML(p.name)} · ${number(p.price)} aUEC · ${escapeHTML(p.updated_at || 'date unknown')}</p>`).join('')}</details>
    <div class="fit-actions"><span>${cargoOnly?'Exported cargo capacity':'Best found in a bounded search · experimental'}</span><button type="button" class="quiet" data-save="${index}">↓ Save ${cargoOnly?'ship':'build'}</button></div></article>`;
}
function showResults(report) {
  lastResult = report; $('export').hidden = false;
  const names = Object.entries(report.request.search.weights).filter(([,v])=>v).map(([k,v])=>`${definitions[k][0]} ${v}%`).join(' · ');
  setStatus(`${report.results.length} fits · ${report.ships_eligible} eligible / ${report.ships_considered} considered${report.goal==='custom'?' · '+names:''}`);
  $('results').innerHTML = report.results.length ? report.results.map((r,i)=>resultHTML(r,i,report)).join('') : '<div class="panel empty-state"><h3>No fit meets these limits.</h3><p>Try a wider budget, another class, or fewer constraints. See the exclusions below for specific reasons.</p></div>';
  $('exclusions').hidden = !report.skipped.length;
  $('exclusions').querySelector('summary').textContent = `${report.skipped.length} ships excluded · see why`;
  $('exclusions').querySelector('div').innerHTML = report.skipped.map(s=>`<p><strong>${escapeHTML(s.name || s.ship)}</strong> — ${escapeHTML(s.reason)}</p>`).join('');
}
async function loadOptions(initial = false) {
  options = await api('/api/options');
  $('game-version').textContent = options.data.game_version;
  const matched = options.ships.filter(s=>options.market.ships[s.id.toLowerCase()]).length;
  $('coverage').textContent = `${options.ships.length} ships · ${matched} matched price / size records`;
  $('source-info').textContent = `Game data: ${options.data.source} · Prices / dock classes: FleetYards · Market cache: ${options.market.downloaded_at?.slice(0,10) || 'not downloaded'}`;
  if (initial) {
    $('goal').replaceChildren(...options.objectives.filter(o=>!['pve','pvp'].includes(o.id)).map(o=>new Option(o.name,o.id)));
    $('role').append(...options.roles.map(r=>new Option(r,r)));
    $('role').value = options.roles.includes('Medium Fighter') ? 'Medium Fighter' : '';
    shipOptions();
    const meteor = options.ships.find(s=>s.id.toLowerCase()==='rsi_meteor');
    if (meteor) $('ship').value = meteor.id;
    $('roadmap').innerHTML = options.roadmap.map(r=>`<article><h3>${escapeHTML(r.name)}</h3><p>${escapeHTML(r.detail)}</p></article>`).join('');
  }
  shipFacts(); updateScope();
}
async function submit(event) {
  event.preventDefault();
  if (busy) return;
  if (scope()==='ship' && !$('ship').value) {setStatus('Choose a ship to continue.', 'error'); return;}
  const request = readRequest();
  setBusy(true); setStatus('Preparing your search…');
  try {showResults(await runJob('/api/search', request));}
  catch(error) {setStatus(error.message, 'error');}
  finally {setBusy(false);}
}
renderPriorityControls();
$('solver').addEventListener('submit', submit);
$('solver').addEventListener('input', event => {if (event.target.name !== 'view') markDirty();});
$('solver').addEventListener('change', event => {
  if (event.target.name === 'scope') updateScope();
  if (event.target.name === 'view') $('priorities').className = 'priorities ' + event.target.value;
});
$('ship-filter').addEventListener('input', shipOptions); $('ship').addEventListener('change', shipFacts);
$('goal').addEventListener('change', updateGoal);
$('retention').addEventListener('input', () => {$('retention-value').textContent = $('retention').value + '%';});
document.querySelectorAll('[data-preset]').forEach(button => button.addEventListener('click', () => {
  const preset = presets[button.dataset.preset]; weights = makeWeights(preset.weights); $('goal').value = 'custom';
  document.querySelectorAll('[data-preset]').forEach(b=>b.classList.toggle('active',b===button));
  updateWeights(); updateGoal(); $('preset-description').textContent = preset.text; markDirty();
}));
$('export').addEventListener('click', () => download(lastResult, 'citizensolver-results.json'));
$('results').addEventListener('click', event => {
  const save = event.target.closest('[data-save]');
  if (save && lastResult) {const build = lastResult.results[Number(save.dataset.save)]; download(build, build.ship.id+'-build.json');}
});
$('refresh-market').addEventListener('click', async () => {
  setBusy(true);
  try {await runJob('/api/market/refresh', {}); await loadOptions(); setStatus('Prices and hangar data refreshed. Run a new search to apply them.');}
  catch(error) {setStatus(error.message, 'error');}
  finally {setBusy(false);}
});
(async () => {
  try {
    await loadOptions(true); $('solve').disabled = false; $('solve-priorities').disabled = false; setStatus('Ready when you are. Set your priorities and find your fits.');
    const pending = JSON.parse(sessionStorage.getItem('citizensolver-job') || 'null');
    if (pending) {
      setBusy(true);
      const result = await followJob(pending.id, pending.path);
      if (pending.path === '/api/search') showResults(result); else {await loadOptions(); setStatus('Market data refreshed.');}
      setBusy(false);
    }
  } catch(error) {sessionStorage.removeItem('citizensolver-job'); if(options) setBusy(false); setStatus('Unable to continue: '+error.message,'error');}
})();
