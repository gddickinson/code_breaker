/* Mystery Lab: index and generic renderer for case-file sections. */
const STATUS = { solved: "good", open: "warn", untestable: "bad", private: "warn" };

route(/^\/mysteries$/, async () => {
  const { cases } = await api("/mysteries");
  view().innerHTML = `<h1>Mystery Lab</h1>
    <p class="lead">Real attempts on historical unsolved ciphers. A claim only counts if the solver can read a control text of the same size and the real ciphertext beats scrambled copies of itself.</p>
    <div class="grid">${cases.map(c => `<a class="card" href="#/mystery/${esc(c.id)}"><b>${esc(c.title)}</b><small><span class="tag ${STATUS[c.status_kind] || ""}">${esc(c.status)}</span></small><span>${esc(c.tagline)}</span></a>`).join("")}</div>`;
}, "mysteries");

function section(s) {
  return `${s.heading ? `<h2>${esc(s.heading)}</h2>` : ""}${(s.paragraphs || []).map(p => `<p>${esc(p)}</p>`).join("")}
    ${s.verdict ? `<div class="verdict">${esc(s.verdict)}</div>` : ""}
    ${s.table ? table(s.table.cols, s.table.rows) : ""}
    ${(s.mono || []).map(m => `${m.label ? `<h3>${esc(m.label)}</h3>` : ""}<pre>${esc(m.text)}</pre>`).join("")}`;
}

route(/^\/mystery\/(\w+)$/, async id => {
  const c = await api("/mysteries/" + id);
  view().innerHTML = `<a href="#/mysteries">← Mystery Lab</a><h1>${esc(c.title)}</h1>
    <p><span class="tag ${STATUS[c.status_kind] || ""}">${esc(c.status)}</span></p><p class="lead">${esc(c.tagline)}</p>
    ${c.sections.map(section).join("")}
    <h2>Sources</h2><ul>${c.sources.map(([t, u]) => `<li><a href="${esc(u)}" rel="noreferrer">${esc(t)}</a></li>`).join("")}</ul>`;
}, "mysteries");
