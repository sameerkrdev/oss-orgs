(() => {
  const D = window.OSS;
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  // only http(s) links ever reach an href
  const safe = (u) => {
    if (!u) return null;
    let s = String(u).trim();
    if (!/^[a-z]+:/i.test(s)) s = "https://" + s;
    try { const x = new URL(s); return ["http:", "https:"].includes(x.protocol) ? x.href : null; } catch { return null; }
  };
  const a = (u, text) => { const h = safe(u); return h ? `<a href="${esc(h)}" target="_blank" rel="noopener noreferrer">${esc(text ?? u)}</a>` : esc(text ?? ""); };
  const short = (u) => String(u).replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");
  const num = (n) => (n == null ? "–" : n >= 10000 ? (n / 1000).toFixed(n >= 100000 ? 0 : 1) + "k" : n.toLocaleString());
  const LABEL = { slack: "Slack", discord: "Discord", zulip: "Zulip", matrix: "Matrix", gitter: "Gitter", telegram: "Telegram", whatsapp: "WhatsApp",
    mattermost: "Mattermost", rocketchat: "Rocket.Chat", irc: "IRC", forum: "Forum", x: "X / Twitter", reddit: "Reddit", youtube: "YouTube",
    linkedin: "LinkedIn", bluesky: "Bluesky", mastodon: "Mastodon" };
  const LANG = ["#0f766e", "#7c3aed", "#d97706", "#2563eb", "#db2777", "#9ca3af"];

  const S = { q: "", group: "", sort: "stars" };
  for (const g of D.groups) for (const p of g.projects) {
    p._g = g.title;
    p._text = [p.repo, p.desc, p.backer, p.lang, ...p.topics].join(" ").toLowerCase();
  }

  $("#gen").textContent = `GitHub data as of ${D.generated} · merged PRs counted since ${D.since} · careers links checked to load`;
  $("#groups").innerHTML = [["", "All"], ...D.groups.map((g) => [g.title, g.title.replace("JavaScript / TypeScript", "JS / TS")])]
    .map(([v, l]) => `<button data-g="${esc(v)}">${esc(l)}</button>`).join("");
  $("#groups").onclick = (e) => { const b = e.target.closest("[data-g]"); if (b) { S.group = b.dataset.g; render(); } };
  $("#sort").onchange = (e) => { S.sort = e.target.value; render(); };
  let t0;
  $("#q").oninput = (e) => { clearTimeout(t0); t0 = setTimeout(() => { S.q = e.target.value.toLowerCase().trim(); render(); }, 150); };

  const key = { stars: (p) => p.stars, merged30: (p) => p.prs.merged30 || 0, gfi: (p) => p.prs.gfi || 0 };

  const row = (p, i) => {
    const o = p.owner, pr = p.prs, langs = Object.entries(p.langs);
    return `<details class="proj"><summary>
      <span class="rank">${i + 1}</span>
      ${o.avatar && safe(o.avatar) ? `<img class="avatar" src="${esc(safe(o.avatar))}&s=64" alt="" loading="lazy">` : `<span class="avatar"></span>`}
      <div class="s-main"><b>${esc(p.repo)}</b><span>${esc(p.desc || "")}</span></div>
      <div class="s-side">★ ${num(p.stars)} · ${num(pr.merged30)} merged/30d · ${num(pr.gfi)} starter issues<br><span class="muted">${esc(p.backer)}</span></div></summary>
      <div class="proj-body">
        <div>
          <dl class="kv">
            <dt>Repository</dt><dd>${a(p.url, p.repo)}</dd>
            ${p.homepage ? `<dt>Website</dt><dd>${a(p.homepage, short(p.homepage))}</dd>` : ""}
            <dt>Stars / forks</dt><dd>${num(p.stars)} / ${num(p.forks)}</dd>
            <dt>Open issues</dt><dd>${num(p.issues)}</dd>
            <dt>License</dt><dd>${esc(p.license || "–")}</dd>
            <dt>Started</dt><dd>${esc((p.created || "").slice(0, 10))} · last push ${esc((p.pushed || "").slice(0, 10))}</dd>
            ${p.topics.length ? `<dt>Topics</dt><dd>${esc(p.topics.join(" · "))}</dd>` : ""}
          </dl>
          ${langs.length ? `<div class="langbar">${langs.map(([l, pc], k) => `<i style="width:${+pc}%;background:${LANG[k % LANG.length]}" title="${esc(l)} ${+pc}%"></i>`).join("")}</div>
          <div class="legend">${langs.map(([l, pc], k) => `<span><i class="dot" style="--c:${LANG[k % LANG.length]}"></i>${esc(l)} ${+pc}%</span>`).join("")}</div>` : ""}
          <h4>Pull requests & issues</h4>
          <div class="small">${a(pr.open_url, `${num(pr.open)} open PRs`)} · ${a(pr.merged_url, `${num(pr.merged30)} merged in 30 days`)} · ${a(pr.gfi_url, `${num(pr.gfi)} good-first / help-wanted issues`)}</div>
          ${pr.recent.length ? `<ul class="prs">${pr.recent.map((it) => `<li><span class="st merged">merged</span>${a(it.u, it.t)}<span class="muted small">@${esc(it.by)}</span></li>`).join("")}</ul>` : ""}
        </div>
        <div>
          <div class="sec"><h2>Company</h2>
            <div class="links">${a(p.backer_site, p.backer)}${p.careers ? a(p.careers, "Careers page →") : `<span class="muted small">No careers page found${p.careers_tried ? " (link didn't load)" : ""}</span>`}</div></div>
          <div class="sec"><h2>GitHub org</h2>
            <div class="small">${a("https://github.com/" + o.login, o.name || o.login)}${o.type === "User" ? " (user account)" : ""}</div>
            <div class="small muted">${[o.location, o.followers != null ? num(o.followers) + " followers" : "", o.repos != null ? num(o.repos) + " repos" : ""].filter(Boolean).map(esc).join(" · ")}</div>
            <div class="soc" style="margin-top:6px">${[o.blog && a(o.blog, short(o.blog)), o.twitter && a("https://x.com/" + o.twitter, "X @" + o.twitter)].filter(Boolean).join("")}</div></div>
          <div class="sec"><h2>Community</h2>
            <div class="links">${p.channels.map((c) => a(c.url, `${LABEL[c.type] || c.type} · ${short(c.url).slice(0, 40)}`)).join("") || '<span class="muted small">No chat links in README</span>'}</div></div>
          <div class="sec"><h2>Contribute</h2>
            <div class="links">${p.contributing ? a(p.contributing, "Contributing guide") : '<span class="muted small">No CONTRIBUTING file</span>'}${p.coc ? a(p.coc, "Code of conduct") : ""}</div></div>
        </div>
      </div></details>`;
  };

  function render() {
    document.querySelectorAll("#groups button").forEach((b) => b.classList.toggle("on", b.dataset.g === S.group));
    const groups = D.groups.filter((g) => !S.group || g.title === S.group)
      .map((g) => ({ ...g, projects: g.projects.filter((p) => !S.q || p._text.includes(S.q)).sort((x, y) => key[S.sort](y) - key[S.sort](x)) }))
      .filter((g) => g.projects.length);
    const all = groups.flatMap((g) => g.projects);
    $("#stats").innerHTML = [[all.length, "projects"], [new Set(all.map((p) => p.backer)).size, "companies"],
      [all.reduce((s, p) => s + (p.prs.merged30 || 0), 0), "PRs merged in 30 days"], [all.reduce((s, p) => s + (p.prs.gfi || 0), 0), "starter issues open"]]
      .map(([n, l]) => `<b>${n.toLocaleString()}</b> ${l}`).join(" &nbsp;·&nbsp; ");
    $("#view").innerHTML = groups.map((g) => `<div class="year-h"><h2>${esc(g.title)}</h2><span class="muted small">top ${g.projects.length} by ${$("#sort").selectedOptions[0].text.toLowerCase()}</span></div>${g.projects.map(row).join("")}`).join("")
      || `<div class="empty">No projects match.</div>`;
  }
  render();
})();
