// Equal route audit information for all methods, hidden while paused or testing.
async function refreshRouteAudit() {
  const panel = document.getElementById('a07-audit');
  const id = localStorage.getItem('B06v2-session');
  if (!panel || !id) return;
  if (typeof busy !== 'undefined' && busy) { panel.hidden = true; return; }
  try {
    const response = await fetch('/api/session?id=' + encodeURIComponent(id));
    if (!response.ok) return;
    const view = await response.json();
    panel.hidden = view.status !== 'ACTIVE' || !['reading', 'feedback'].includes(view.phase);
    panel.replaceChildren();
    if (panel.hidden) return;
    const heading = document.createElement('h2');
    heading.textContent = '路线依据与逐项成本 · ' + view.runtime_version;
    panel.append(heading);
    for (const row of view.route_explanations || []) {
      const block = document.createElement('p');
      const lines = row.source_spans.map(s => `${s.path}:L${s.start_line}–${s.end_line}`).join('; ');
      const versions = row.source_versions.map(s => s.commit).join(', ');
      const why = row.completed ? '已完成项继续计作覆盖；阅读不新增掌握证据' :
        `覆盖本任务概念：${row.target_concepts.join(', ')}；需优先于：${row.required_by_remaining.join(', ') || '无硬性先修后继'}`;
      block.textContent = `${row.completed ? '已完成保留' : '剩余'} ${row.unit_id} · ${row.base_proxy_cost} proxy_cost（非分钟）\n` +
        `${why}\n源码：${lines}；commit：${versions}`;
      panel.append(block);
    }
  } catch (_) { panel.hidden = true; }
}
setInterval(refreshRouteAudit, 2000);
for (const id of ['pause', 'withdraw', 'complete', 'answer', 'submit', 'new']) {
  document.getElementById(id)?.addEventListener('click', () => {
    document.getElementById('a07-audit').hidden = true;
  }, true);
}
refreshRouteAudit();
