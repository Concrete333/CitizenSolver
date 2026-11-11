'use strict';
let chosenBuild, chosenRequest, componentOptions, lockedPorts = new Set();
const reportDate = value => value ? new Date(value * 1000).toLocaleDateString() : 'date unknown';
function purchaseHTML(row) {
  const purchase = row.purchase || {};
  const status = purchase.status === 'stock' ? 'Included with this ship' : purchase.status === 'listed' ? 'Recorded NPC sellers' : 'No recorded NPC seller';
  return `<strong>${status}</strong>${(purchase.offers || []).map(o => `<div>${escapeHTML(o.shop)} · ${number(o.price)} aUEC · patch ${escapeHTML(o.game_version || 'unknown')} · ${escapeHTML(reportDate(o.reported_at))}</div>`).join('')}`;
}
function insightHTML(build) {
  const s = build.stealth, h = build.maneuverability, m = build.metrics;
  const axes = Object.entries(s.axes).map(([axis,value]) => `<tr><td>${axis}</td><td>${number(value)}</td><td>${number(s.signal_by_axis[axis])}</td></tr>`).join('');
  const radar = s.own_radars.map(r => `<p><strong>${escapeHTML(r.name)}</strong>: ${Object.entries(r.sensitivity || {}).filter(([k])=>['IR','EM','CS'].includes(k)).map(([k,v])=>`${escapeHTML(k)} sensitivity ${number(v,2)}`).join(' · ') || 'Sensitivity unknown'}. These are receiver ratings, not distances. Radar aiming-assist range is a separate targeting value.</p>`).join('');
  const turn = ['Pitch','Yaw','Roll'].map(axis=>`<tr><td>${axis}</td><td>${number(h.rated_turning[axis],1)} °/s</td><td>${number(h.rated_boost_turning[axis],1)} °/s</td></tr>`).join('');
  return `<div class="metric-grid">${[['duration_dps','Engagement damage','DPS'],['shield_hp','Shield capacity','HP'],['em','Estimated EM',''],['ir','Estimated IR','']].map(d=>metricHTML(m,d)).join('')}</div>
    <details class="fit-details" open><summary>Stealth profile · emissions & silhouette</summary><p>EM reflects electrical activity; IR reflects heat; cross-section describes the hull's radar signature. Lower EM or IR cannot remove the hull's silhouette.</p><div class="table-wrap"><table><thead><tr><th>Hull axis</th><th>Effective cross-section</th><th>Strongest signal¹</th></tr></thead><tbody>${axes}</tbody></table></div><p>¹ The larger of EM, IR and that axis's cross-section. Axis-average ranking signal: <strong>${number(m.signature)}</strong>. ${escapeHTML(s.scope)}</p><p>${escapeHTML(s.operation_note)}</p><p>${escapeHTML(s.detection_note)}</p>${radar}<p>Cross-section includes the exported hull multiplier. These axes are shown as X/Y/Z because front, side and top mappings have not been validated.</p><p><a href="https://robertsspaceindustries.com/en/comm-link/engineering/14926-Design-Notes-Electronic-Warfare" target="_blank" rel="noopener">CIG signature design notes (historical)</a> · <a href="https://www.cstone.space/resources/knowledge-base/89-know-your-hardware-the-complete-list-of-ship-installed-radars-and-their-ir-em-cs-and-rs-values" target="_blank" rel="noopener">Radar data explained by Cornerstone</a></p></details>
    <details class="fit-details"><summary>Maneuverability · turning, acceleration & braking</summary><div class="table-wrap"><table><thead><tr><th>Axis</th><th>Rated</th><th>Boost rating</th></tr></thead><tbody>${turn}</tbody></table></div><p>Forward acceleration: <strong>${number(h.forward_acceleration,1)} m/s²</strong> · Braking: <strong>${number(h.braking_acceleration,1)} m/s²</strong>.</p><p>SCM: ${number(m.scm_speed)} m/s · Maximum: ${number(m.max_speed)} m/s. Ideal 0 → SCM: ${number(h.zero_to_scm_seconds,2)} s; SCM → 0: ${number(h.scm_to_zero_seconds,2)} s.</p><p>${escapeHTML(h.scope)}</p><p>${escapeHTML(h.limits)}</p><p><a href="https://robertsspaceindustries.com/en/comm-link/transmission/20935-Engineering-Gameplay-Guide" target="_blank" rel="noopener">CIG engineering guide</a> · <a href="https://support.robertsspaceindustries.com/hc/en-us/articles/360025028633-Getting-Started-in-the-Verse" target="_blank" rel="noopener">CIG flight guide</a></p></details>`;
}
async function chooseFit(build, request, keepLocks = false) {
  setBusy(true);
  try {
    const components = await api('/api/components?ship=' + encodeURIComponent(build.ship.id));
    chosenBuild = build; chosenRequest = structuredClone(request); componentOptions = components;
    if (!keepLocks) lockedPorts = new Set();
    renderChosen(); $('selected-fit').scrollIntoView({behavior:'smooth', block:'start'});
  } catch(error) {setStatus(error.message, 'error');}
  finally {setBusy(false);}
}
function renderChosen(editorOpen = false) {
  const b = chosenBuild, shop = chosenRequest.search.equipment_mode === 'shop';
  const rows = componentOptions.ports.map((port,index) => {
    const fitted = b.loadout.find(i=>i.port===port.port);
    const portName = (fitted.path || [fitted.hardpoint]).map(p=>p.replace(/^hardpoint_/,'').replaceAll('_',' ')).join(' › ');
    const choices = port.choices.map(c=>`<option value="${escapeHTML(c.id)}" ${c.id===fitted.id?'selected':''} ${shop && c.id!==port.stock && !c.offers.length?'disabled':''}>${escapeHTML(c.name)}${c.id===port.stock?' · stock':c.offers.length?' · shop listed':' · seller unknown'}</option>`).join('');
    return `<tr><td><label for="component-${index}">${escapeHTML(portName)}</label><small>${escapeHTML(fitted.type)} · S${fitted.size}</small></td><td><select id="component-${index}" data-component="${index}" aria-label="${escapeHTML(portName)} component">${choices}</select></td><td><label class="check"><input type="checkbox" data-lock="${index}" ${lockedPorts.has(port.port)?'checked':''} aria-label="Lock ${escapeHTML(portName)}">Lock</label></td></tr>`;
  }).join('');
  $('selected-fit').hidden = false;
  $('selected-fit').innerHTML = `<div class="fit-top"><div><p class="eyebrow">YOUR SELECTED BUILD</p><h3>${escapeHTML(b.ship.name)}</h3><p class="hint">${shop?'Shop-listed upgrades':'Best compatible equipment'} · ${b.power.used} / ${b.power.available} allocated power pips</p></div><button class="quiet" type="button" data-editor-action="save">↓ Save this build</button></div>
    ${insightHTML(b)}${weaponReachHTML(b.weapons, chosenRequest.search.min_range)}
    <details class="fit-details"><summary>Where to find this equipment</summary><p>Stock parts come with the ship. UEX reports are recorded shop listings, not live stock guarantees. Check the individual patch and date before buying. Cache downloaded: ${escapeHTML(b.equipment_source?.downloaded_at || 'not downloaded')}.</p><div class="table-wrap"><table><thead><tr><th>Component</th><th>Purchase evidence</th></tr></thead><tbody>${[...new Map(b.loadout.map(i=>[i.id+'|'+i.purchase?.status,i])).values()].map(i=>`<tr><td>${escapeHTML(i.name)}</td><td>${purchaseHTML(i)}</td></tr>`).join('')}</tbody></table></div></details>
    <details class="fit-details" ${editorOpen?'open':''}><summary>Change equipment & locks · optional</summary><p>Swap a component or lock it in place, then optimize the rest. Locks keep equipment fixed; power allocation is recalculated. This editor does not track your inventory.</p><div class="table-wrap"><table class="editor-table"><thead><tr><th>Port</th><th>Equipment</th><th>Keep fixed</th></tr></thead><tbody>${rows}</tbody></table></div><label for="edit-profile">Power preference for applying swaps</label><select id="edit-profile"><option value="damage">Firepower</option><option value="balanced">Balanced</option><option value="stealth">Lower emissions</option></select><p class="hint">Optimize unlocked equipment compares all three power profiles using your original priorities and limits.</p><div class="editor-actions"><button type="button" class="quiet" data-editor-action="apply">Apply equipment</button><button type="button" class="quiet" data-editor-action="optimize">Optimize unlocked equipment ↗</button></div><p id="editor-status" class="status" role="status">Equipment changes are drafts until applied or optimized.</p></details>
    <div class="note matchup-note"><strong>Next: test this build against a target.</strong> Target size, opposing radar and time to destroy each ship belong here, after selection. That comparison is not implemented yet and does not affect this ranking. Owned-inventory matching is also reserved for a later step.</div>`;
  $('edit-profile').value = b.scenario.power_profile;
}
function editorDraft() {
  const swaps = {}, locks = {};
  componentOptions.ports.forEach((port,index) => {
    const id = $('component-'+index).value;
    if (id !== port.stock) swaps[port.port] = id;
    if (lockedPorts.has(port.port)) locks[port.port] = id;
  });
  return {swaps,locks};
}
$('selected-fit').addEventListener('change', event => {
  if (event.target.dataset.lock !== undefined) {
    const port = componentOptions.ports[Number(event.target.dataset.lock)].port;
    if (event.target.checked) lockedPorts.add(port); else lockedPorts.delete(port);
  }
  if ($('editor-status')) $('editor-status').textContent = 'Draft changed. Apply equipment or optimize the unlocked ports.';
});
$('selected-fit').addEventListener('click', async event => {
  const action = event.target.closest('[data-editor-action]')?.dataset.editorAction;
  if (!action || busy) return;
  if (action === 'save') {download(chosenBuild, chosenBuild.ship.id+'-build.json'); return;}
  const draft = editorDraft(), profile = $('edit-profile').value;
  setBusy(true); $('editor-status').textContent = action === 'apply' ? 'Checking this equipment…' : 'Searching the unlocked ports…';
  try {
    if (action === 'apply') {
      const result = await api('/api/evaluate', {ship:chosenBuild.ship.id, swaps:draft.swaps, profile,
        duration:chosenBuild.scenario.duration_seconds, revision:componentOptions.revision});
      if (!result.feasible) throw new Error(result.violations.join('. ') + '. Your previous build is unchanged.');
      chosenBuild = result; renderChosen(true);
      $('editor-status').textContent = 'Equipment applied. Stats describe this manual build; it has not been ranked against your search limits.';
    } else {
      const request = {...chosenRequest, scope:'ship', ship:chosenBuild.ship.id, revision:componentOptions.revision,
        search:{...chosenRequest.search, seed_swaps:draft.swaps, locks:draft.locks}};
      const result = await runJob('/api/search', request);
      if (!result.results.length) throw new Error('No fit meets your original limits with these locks. Unlock a component or change the limits and search again.');
      chosenBuild = result.results[0]; chosenRequest = request; showResults(result); renderChosen(true);
      $('editor-status').textContent = `${Object.keys(draft.locks).length} component locks preserved. Other equipment and power were optimized.`;
    }
  } catch(error) {$('editor-status').textContent = error.message; $('editor-status').className = 'status error';}
  finally {setBusy(false);}
});
