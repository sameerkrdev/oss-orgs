(() => {
  const D = window.DATA, P = D.program;
  const $ = (s) => document.querySelector(s);
  const view = $("#view");
  const more = $("#more");

  // ---------- helpers ----------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  // only http(s)/mailto links ever reach an href
  const safe = (u) => {
    if (!u) return null;
    let s = String(u).trim();
    if (!/^[a-z]+:/i.test(s)) s = "https://" + s;
    try {
      const x = new URL(s);
      return ["http:", "https:", "mailto:"].includes(x.protocol) ? x.href : null;
    } catch { return null; }
  };
  const a = (u, text, cls = "") => {
    const h = safe(u);
    return h ? `<a href="${esc(h)}" target="_blank" rel="noopener noreferrer" class="${cls}">${esc(text ?? u)}</a>` : esc(text ?? "");
  };
  const short = (u) => String(u).replace(/^(https?:\/\/|mailto:)(www\.)?/, "").replace(/\/$/, "");
  const num = (n) => (n == null ? "–" : n >= 10000 ? (n / 1000).toFixed(n >= 100000 ? 0 : 1) + "k" : n.toLocaleString());
  const money = (n, c) => { try { return n.toLocaleString(undefined, { style: "currency", currency: c || "USD", maximumFractionDigits: 0 }); } catch { return n + " " + c; } };
  const norm = (s) => String(s || "").toLowerCase().trim();
  // blank line = paragraph; single newlines (often PDF wrapping) flow, except list items
  const para = (t) => esc(t).replace(/(\w)-\n(?=[a-z])/g, "$1").split(/\n\s*\n/)
    .map((x) => `<p>${x.trim().replace(/\n(?=\s*([-*•]|\d+[.)])\s)/g, "<br>").replace(/\n/g, " ")}</p>`).join("");
  const initials = (n) => esc((n || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase());
  const avatar = (u, name, cls = "avatar") => u?.avatar_url && safe(u.avatar_url)
    ? `<img class="${cls}" src="${esc(safe(u.avatar_url))}&s=96" alt="" loading="lazy">`
    : `<span class="${cls} ph">${initials(name)}</span>`;

  const PLAT = {
    slack: ["Slack", "#4a154b"], discord: ["Discord", "#5865f2"], zulip: ["Zulip", "#6492fe"], matrix: ["Matrix", "#0dbd8b"],
    gitter: ["Gitter", "#ed1965"], irc: ["IRC", "#7c7c7c"], telegram: ["Telegram", "#26a5e4"], whatsapp: ["WhatsApp", "#25d366"],
    mattermost: ["Mattermost", "#1e325c"], rocketchat: ["Rocket.Chat", "#f5455c"], forum: ["Forum", "#d97706"],
    mailinglist: ["Mailing list", "#8b5cf6"], github: ["GitHub", "#6e7681"], gitlab: ["GitLab", "#fc6d26"], x: ["X / Twitter", "#111"],
    facebook: ["Facebook", "#1877f2"], blog: ["Blog", "#0ea5e9"], email: ["Email", "#64748b"], chat: ["Chat", "#14b8a6"], other: ["Link", "#94a3b8"],
  };
  const LANG = ["#0f766e", "#7c3aed", "#d97706", "#2563eb", "#db2777", "#65a30d", "#0891b2", "#9ca3af"];

  // ---------- indexes ----------
  const orgBy = Object.fromEntries(D.orgs.map((o) => [o.slug, o]));
  const projBy = {};
  for (const p of D.projects) (projBy[p.org] ||= []).push(p);
  for (const o of D.orgs) {
    o._p = projBy[o.slug] || [];
    o._tech = new Set((o.tech_tags || []).map(norm));
    o._plats = new Set(o.links.map((l) => l.type));
    o._text = norm([o.name, o.tagline, o.description, ...(o.tech_tags || []), ...(o.topic_tags || []), ...(o.categories || [])].join(" "));
  }
  for (const p of D.projects) {
    const u = D.users[p.gh] || {};
    p._text = norm([p.title, p.name, p.gh, u.name, p.org, orgBy[p.org]?.name, ...p.tech, ...p.mentors].join(" "));
    p._tech = new Set(p.tech.map(norm));
  }
  const cats = [...new Set(D.orgs.flatMap((o) => o.categories || []))].sort();
  const techCount = {};
  for (const o of D.orgs) for (const t of o._tech) techCount[t] = (techCount[t] || 0) + 1;
  const plats = Object.keys(PLAT).filter((k) => D.orgs.some((o) => o._plats.has(k)) && !["other", "chat", "blog", "email", "facebook"].includes(k));

  // ---------- state ----------
  const S = { q: "", years: new Set(), cat: "", techs: new Set(), plats: new Set(), sort: "name", pSort: ["year", -1] };
  try { Object.assign(S, { sort: localStorage.getItem("gsoc.sort") || "name" }); } catch {}

  const orgMatch = (o) =>
    (!S.years.size || o.years.some((y) => S.years.has(y))) &&
    (!S.cat || (o.categories || []).includes(S.cat)) &&
    [...S.techs].every((t) => o._tech.has(t) || o._p.some((p) => p._tech.has(t))) &&
    [...S.plats].every((k) => o._plats.has(k));
  const projMatch = (p) => {
    const o = orgBy[p.org];
    return (!S.years.size || S.years.has(p.year)) &&
      (!S.cat || (o?.categories || []).includes(S.cat)) &&
      [...S.techs].every((t) => p._tech.has(t) || o?._tech.has(t)) &&
      [...S.plats].every((k) => o?._plats.has(k));
  };
  const qOrg = (o, q) => !q || o._text.includes(q) || o._p.some((p) => p._text.includes(q));

  // ---------- filters UI ----------
  $("#gen").textContent = `Data from ${P.sources} · updated ${D.generated}`;
  $("#h1").textContent = `${P.title} organizations ${[...new Set([D.years[0], D.years.at(-1)])].join("–")}`;
  document.querySelectorAll(".progs a").forEach((x) => x.classList.toggle("on", x.dataset.p === P.key));
  $("#f-years").innerHTML = D.years.map((y) => `<button data-y="${y}">${y}</button>`).join("");
  $("#f-cat").insertAdjacentHTML("beforeend", cats.map((c) => `<option>${esc(c)}</option>`).join(""));
  $("#tech-list").innerHTML = Object.entries(techCount).sort((a, b) => b[1] - a[1]).map(([t]) => `<option value="${esc(t)}">`).join("");
  $("#f-plats").innerHTML = plats.map((k) => `<button class="chip" data-p="${k}"><i class="dot" style="--c:${PLAT[k][1]}"></i>${PLAT[k][0]}</button>`).join("");
  $("#f-sort").value = S.sort;

  const syncChips = () => {
    document.querySelectorAll("#f-years button").forEach((b) => b.classList.toggle("on", S.years.has(+b.dataset.y)));
    document.querySelectorAll("#f-plats .chip").forEach((b) => b.classList.toggle("on", S.plats.has(b.dataset.p)));
    $("#f-techs").innerHTML = [...S.techs].map((t) => `<button class="chip on" data-t="${esc(t)}">${esc(t)} ×</button>`).join("");
    $("#f-count").textContent = S.techs.size + S.plats.size || "";
  };
  $("#f-years").onclick = (e) => { const b = e.target.closest("[data-y]"); if (!b) return; const y = +b.dataset.y; S.years.has(y) ? S.years.delete(y) : S.years.add(y); update(); };
  $("#f-plats").onclick = (e) => { const b = e.target.closest("[data-p]"); if (!b) return; const k = b.dataset.p; S.plats.has(k) ? S.plats.delete(k) : S.plats.add(k); update(); };
  $("#f-techs").onclick = (e) => { const b = e.target.closest("[data-t]"); if (b) { S.techs.delete(b.dataset.t); update(); } };
  $("#f-tech-in").onchange = (e) => { const t = norm(e.target.value); if (t) { S.techs.add(t); e.target.value = ""; update(); } };
  $("#f-cat").onchange = (e) => { S.cat = e.target.value; update(); };
  $("#f-sort").onchange = (e) => { S.sort = e.target.value; try { localStorage.setItem("gsoc.sort", S.sort); } catch {} update(); };
  let t0;
  $("#q").oninput = (e) => { clearTimeout(t0); t0 = setTimeout(() => { S.q = norm(e.target.value); update(); }, 150); };
  $("#reset").onclick = () => { Object.assign(S, { q: "", cat: "" }); S.years.clear(); S.techs.clear(); S.plats.clear(); $("#q").value = ""; $("#f-cat").value = ""; update(); };

  // ---------- lazy list ----------
  let io, fill = 0; // fill: page height to render up front, so a saved scroll position can be restored
  const lazy = (container, items, render, step = 60) => {
    io?.disconnect();
    let i = 0;
    const next = () => { container.insertAdjacentHTML("beforeend", items.slice(i, i + step).map(render).join("")); i += step; if (i >= items.length) io?.disconnect(); };
    do next(); while (i < items.length && document.documentElement.scrollHeight < fill);
    if (i < items.length) { io = new IntersectionObserver((es) => es[0].isIntersecting && next(), { rootMargin: "800px" }); io.observe(more); }
  };

  // ---------- stats ----------
  const stats = (ps, nOrgs) => {
    const people = new Set(ps.map((p) => p.gh || p.org + "/" + p.name));
    const withGh = ps.filter((p) => p.gh).length;
    const merged = ps.reduce((s, p) => s + (p.prs?.merged || 0), 0);
    $("#stats").innerHTML = [[nOrgs, "organizations"], [ps.length, "projects"], [people.size, "contributors"], [withGh, "on GitHub"], [merged, "merged PRs"]]
      .map(([n, l]) => `<b>${n.toLocaleString()}</b> ${l}`).join(" &nbsp;·&nbsp; ");
  };

  // ---------- orgs view ----------
  const orgCard = (o) => {
    const ps = o._p.filter(projMatch);
    return `<a class="card" href="#org/${esc(o.slug)}">
      <div class="card-head">${o.logo_url ? `<img class="logo" src="${esc(safe(o.logo_url))}" alt="" loading="lazy">` : ""}
        <div><h3>${esc(o.name)}</h3><div class="meta">${esc((o.categories || []).join(", "))}</div></div></div>
      <p>${esc(o.tagline)}</p>
      <div class="meta">${esc((o.tech_tags || []).slice(0, 5).join(" · "))}</div>
      <div class="meta">${ps.length} projects${o.gh?.stars != null ? ` · ★ ${num(o.gh.stars)}` : ""} · ${o.years.map((y) => "’" + String(y).slice(2)).join(" ")}</div>
    </a>`;
  };
  const renderOrgs = () => {
    const sorters = {
      name: (a, b) => a.name.localeCompare(b.name),
      projects: (a, b) => b._p.filter(projMatch).length - a._p.filter(projMatch).length,
      stars: (a, b) => (b.gh?.stars || 0) - (a.gh?.stars || 0),
      years: (a, b) => b.years.length - a.years.length || a.name.localeCompare(b.name),
    };
    const list = D.orgs.filter((o) => orgMatch(o) && qOrg(o, S.q)).sort(sorters[S.sort]);
    stats(list.flatMap((o) => o._p.filter(projMatch)), list.length);
    view.innerHTML = list.length ? `<div class="grid" id="grid"></div>` : `<div class="empty">No organizations match these filters.</div>`;
    if (list.length) lazy($("#grid"), list, orgCard);
  };

  // ---------- person bits ----------
  const socials = (p) => {
    const u = D.users[p.gh];
    if (!u) return p.linkedin ? `<div class="soc">${a(p.linkedin, "LinkedIn")}</div>` : "";
    const out = [[`https://github.com/${p.gh}`, "GitHub"]];
    const seen = new Set(["github"]);
    if (u.twitter_username) { out.push([`https://x.com/${u.twitter_username}`, "X @" + u.twitter_username]); seen.add("twitter"); }
    for (const s of u.socials || []) {
      if (seen.has(s.provider)) continue;
      seen.add(s.provider);
      out.push([s.url, s.provider === "generic" ? short(s.url) : s.provider[0].toUpperCase() + s.provider.slice(1)]);
    }
    if (u.blog && !out.some(([x]) => short(x) === short(u.blog))) out.push([u.blog, short(u.blog)]);
    if (p.linkedin && !seen.has("linkedin")) out.push([p.linkedin, "LinkedIn"]);
    return `<div class="soc">${out.map(([h, t]) => a(h, t)).join("")}</div>`;
  };
  const howNote = (p) => !p.gh ? "" : p.how === "gsoc" ? "" :
    `<div class="warn">GitHub account taken from the final-work link (${p.how === "author" ? "PR/issue author" : "link owner"})${p.name_ok ? "" : " — name differs from the ${P.name} listing, verify"}.</div>`;
  const prList = (p) => !p.prs ? (p.gh ? `<div class="muted small">No PR data (org not on GitHub or not linked).</div>` : "") : `
    <div class="small"><b>${p.prs.total}</b> PRs to the org in ${p.year} · <b>${p.prs.merged}</b> merged${p.prs.total > 100 ? " (in first 100)" : ""} · ${a(p.prs.search, "see on GitHub")}</div>
    <ul class="prs">${p.prs.items.map((it) => `<li><span class="st ${esc(it.s)}">${esc(it.s)}</span>${a(it.u, it.t)}</li>`).join("")}</ul>`;

  const projItem = (p) => {
    const u = D.users[p.gh];
    return `<details class="proj"><summary>${avatar(u, p.name)}
      <div class="s-main"><b>${esc(p.title)}</b><span>${esc(p.name)}${p.gh ? " · @" + esc(p.gh) : ""}</span></div>
      <div class="s-side">${p.prs ? `${p.prs.merged} merged · ` : ""}${esc(p.size || "")}</div></summary>
      <div class="proj-body">
        <div><div class="prose">${para(p.body)}</div>
          <dl class="kv"><dt>Mentors</dt><dd>${esc(p.mentors.join(", ") || "–")}</dd>
          <dt>Tech</dt><dd>${esc(p.tech.join(" · ") || "–")}</dd>
          ${p.repo ? `<dt>Repo / issue</dt><dd>${a(p.repo, short(p.repo))}</dd>` : `<dt>Final work</dt><dd>${p.code ? a(p.code, short(p.code)) : "–"}</dd>`}
          <dt>${esc(P.name)}</dt><dd>${a(p.url, "project page")}${p.status ? ` · ${esc(p.status)}` : ""}</dd></dl>
          <h4>Pull requests</h4>${prList(p) || '<div class="muted small">No GitHub account linked.</div>'}</div>
        <div>${u ? `<div class="person">${avatar(u, p.name, "avatar lg")}<div><b>${esc(u.name || p.gh)}</b>
            <div class="bio">${esc(u.bio || "")}</div>
            <div class="small muted">${[u.company, u.location].filter(Boolean).map(esc).join(" · ")}</div>
            <div class="small muted">${num(u.followers)} followers · ${num(u.public_repos)} repos</div></div></div>
            <div style="margin-top:10px">${socials(p)}</div>${howNote(p)}`
          : `<div class="muted small">No GitHub account in the ${esc(P.name)} listing${p.code ? " or final-work link" : ""}.</div>${socials(p)}`}</div>
      </div></details>`;
  };

  // ---------- org detail ----------
  const fact = (k, label, f) => f?.[k]?.length ? `<dt>${label}</dt><dd>${esc(f[k].join(", "))}</dd>` : "";
  const renderOrg = (slug) => {
    const o = orgBy[slug];
    if (!o) { view.innerHTML = `<div class="empty">Unknown organization.</div>`; return; }
    io?.disconnect();
    const ps = o._p.filter(projMatch).filter((p) => !S.q || p._text.includes(S.q) || o._text.includes(S.q));
    stats(ps, 1);
    const g = o.gh || {}, f = o.facts || {}, oc = f.oc;
    const langs = Object.entries(g.langs || {});
    const byYear = D.years.slice().reverse().map((y) => [y, ps.filter((p) => p.year === y)]).filter(([, l]) => l.length);
    const bg = ["founded_by", "Founded by", "inception", "Founded", "parent", "Parent org", "owned_by", "Owned by", "sponsor", "Sponsor", "funder", "Funded by", "industry", "Industry", "ceo", "CEO", "chair", "Chair", "hq", "HQ", "country", "Country"];
    let bgRows = "";
    for (let i = 0; i < bg.length; i += 2) bgRows += fact(bg[i], bg[i + 1], f);
    view.innerHTML = `<a class="back" href="#orgs">← All organizations</a>
      <div class="org-hero">${o.logo_url ? `<img class="logo big" src="${esc(safe(o.logo_url))}" alt="">` : ""}
        <div><h1>${esc(o.name)}</h1><p>${esc(o.tagline)}</p>
        <div class="meta">${esc((o.categories || []).join(", "))} · ${esc(P.name)} ${o.years.join(", ")}</div></div></div>
      <div class="detail"><div>
        <div class="sec"><h2>About</h2><div class="prose">${para(o.description)}</div>
          <dl class="kv"><dt>Topics</dt><dd>${esc((o.topic_tags || []).join(", "))}</dd><dt>Tech stack</dt><dd>${esc((o.tech_tags || []).join(" · "))}</dd><dt>License</dt><dd>${esc(o.license || "–")}</dd></dl></div>
        ${byYear.map(([y, l]) => `<div class="year-h"><h2>${y}</h2><span class="muted small">${l.length} projects</span></div>${l.map(projItem).join("")}`).join("") || `<div class="empty">${D.projects.length ? "No projects match these filters." : esc(P.title) + " doesn't publish per-student projects."}</div>`}
      </div><aside>
        <div class="sec"><h2>Links</h2><div class="links">
          ${o.website_url ? `<a href="${esc(safe(o.website_url))}" target="_blank" rel="noopener"><span class="lk">Website</span>${esc(short(o.website_url))}</a>` : ""}
          ${o.source_code ? `<a href="${esc(safe(o.source_code))}" target="_blank" rel="noopener"><span class="lk">Source</span>${esc(short(o.source_code))}</a>` : ""}
          ${o.ideas_link ? `<a href="${esc(safe(o.ideas_link))}" target="_blank" rel="noopener"><span class="lk">Ideas list</span>${esc(short(o.ideas_link))}</a>` : ""}
          ${o.contributor_guidance_url ? `<a href="${esc(safe(o.contributor_guidance_url))}" target="_blank" rel="noopener"><span class="lk">Guidance</span>${esc(short(o.contributor_guidance_url))}</a>` : ""}
          ${a(o.page, `${P.name} page`)}</div></div>
        ${o.mentors?.length ? `<div class="sec"><h2>Mentors</h2><div class="links">${o.mentors.map((m) => a(m.url, m.name)).join("")}</div></div>` : ""}
        <div class="sec"><h2>Community</h2><div class="links">${o.links.map((l) => { const h = safe(l.url); return h ? `<a href="${esc(h)}" target="_blank" rel="noopener"><span class="lk"><i class="dot" style="--c:${(PLAT[l.type] || PLAT.other)[1]}"></i> ${(PLAT[l.type] || PLAT.other)[0]}</span>${esc(short(l.url))}</a>` : ""; }).join("")}
          ${g.twitter ? a(`https://x.com/${g.twitter}`, `X @${g.twitter} (from GitHub)`) : ""}${g.blog ? a(g.blog, short(g.blog) + " (from GitHub)") : ""}</div></div>
        ${g.repo ? `<div class="sec"><h2>Repository</h2><dl class="kv"><dt>Repo</dt><dd>${a("https://github.com/" + g.repo, g.repo)}</dd>
          <dt>Stars</dt><dd>${num(g.stars)}</dd><dt>Forks</dt><dd>${num(g.forks)}</dd><dt>Open issues</dt><dd>${num(g.issues)}</dd>
          <dt>Created</dt><dd>${esc((g.created || "").slice(0, 10))}</dd><dt>Last push</dt><dd>${esc((g.pushed || "").slice(0, 10))}</dd>
          ${o.gh_owners?.length ? `<dt>GitHub orgs</dt><dd>${o.gh_owners.map((x) => a("https://github.com/" + x, x)).join(", ")}</dd>` : ""}
          ${g.followers != null ? `<dt>Followers</dt><dd>${num(g.followers)}</dd>` : ""}</dl>
          ${langs.length ? `<div class="langbar">${langs.map(([l, pc], i) => `<i style="width:${pc}%;background:${LANG[i % LANG.length]}" title="${esc(l)} ${pc}%"></i>`).join("")}</div>
          <div class="legend">${langs.map(([l, pc], i) => `<span><i class="dot" style="--c:${LANG[i % LANG.length]}"></i>${esc(l)} ${pc}%</span>`).join("")}</div>` : ""}</div>` : ""}
        <div class="sec"><h2>Background & backing</h2>
          ${bgRows || oc ? `<dl class="kv">${bgRows}${oc ? `<dt>Fiscal host</dt><dd>${esc(oc.host || "Independent")}</dd><dt>Raised (OC)</dt><dd>${money(oc.raised, oc.currency)}</dd>${oc.budget ? `<dt>Yearly budget</dt><dd>${money(oc.budget, oc.currency)}</dd>` : ""}` : ""}</dl>` : `<div class="muted small">No founder or funding data found in Wikidata or Open Collective.</div>`}
          <div class="src" style="margin-top:10px">Sources: ${[f.wikipedia && a(f.wikipedia, "Wikipedia"), f.wikidata && a(f.wikidata, "Wikidata"), oc && a(oc.url, "Open Collective")].filter(Boolean).join(" · ") || "none matched"}</div></div>
      </aside></div>`;
    window.scrollTo(0, 0);
  };

  // ---------- people ----------
  const PCOLS = [["name", "Contributor"], ["org", "Organization"], ["year", "Year"], ["title", "Project"], [null, "Contact"], ["merged", "PRs merged"], [null, "Final work"]];
  const pKey = { name: (p) => norm(p.name), org: (p) => norm(orgBy[p.org]?.name), year: (p) => p.year, title: (p) => norm(p.title), merged: (p) => p.prs?.merged ?? -1 };
  const personRow = (p) => {
    const u = D.users[p.gh];
    return `<tr><td><div class="who">${avatar(u, p.name)}<div><b>${esc(p.name)}</b>${u?.company ? `<div class="small muted">${esc(u.company)}</div>` : ""}</div></div></td>
      <td><a href="#org/${esc(p.org)}">${esc(orgBy[p.org]?.name || p.org)}</a></td><td class="num">${p.year}</td>
      <td>${a(p.url, p.title)}</td>
      <td>${socials(p) || '<span class="muted">–</span>'}</td>
      <td class="num">${p.prs ? `${a(p.prs.search, `${p.prs.merged} / ${p.prs.total}`)}` : "–"}</td>
      <td>${p.code ? a(p.code, short(p.code).slice(0, 38) + (short(p.code).length > 38 ? "…" : "")) : "–"}</td></tr>`;
  };
  // SoB publishes no per-student project list: show its alumni page data instead
  const renderAlumni = () => {
    const list = D.alumni.filter((x) => (!S.q || norm([x.name, x.role, x.company].join(" ")).includes(S.q)))
      .sort((x, y) => y.year - x.year || x.name.localeCompare(y.name));
    $("#stats").innerHTML = `<b>${list.length}</b> alumni &nbsp;·&nbsp; <b>${new Set(list.map((x) => x.company)).size}</b> employers`;
    view.innerHTML = `<p class="muted small">${esc(P.title)} doesn't publish which student did which project; this is its alumni list with where they work now.</p>
      <div class="tbl-wrap"><table><thead><tr><th>Alumnus</th><th>Year</th><th>Role</th><th>Company</th></tr></thead><tbody>
      ${list.map((x) => `<tr><td><b>${esc(x.name)}</b></td><td class="num">${esc(x.year)}</td><td>${esc(x.role)}</td><td>${esc(x.company)}</td></tr>`).join("")}</tbody></table></div>`;
  };
  const renderPeople = () => {
    if (D.alumni) return renderAlumni();
    const [k, dir] = S.pSort;
    const list = D.projects.filter((p) => projMatch(p) && (!S.q || p._text.includes(S.q)))
      .sort((x, y) => { const a1 = pKey[k](x), b1 = pKey[k](y); return (a1 < b1 ? -1 : a1 > b1 ? 1 : 0) * dir; });
    stats(list, new Set(list.map((p) => p.org)).size);
    view.innerHTML = `<div class="tbl-wrap"><table><thead><tr>${PCOLS.map(([c, l]) => `<th ${c ? `data-k="${c}"` : ""} class="${c === k ? "sorted" : ""}">${l}${c === k ? (dir > 0 ? " ↑" : " ↓") : ""}</th>`).join("")}</tr></thead><tbody id="rows"></tbody></table></div>`;
    view.querySelector("thead").onclick = (e) => { const th = e.target.closest("[data-k]"); if (!th) return; const c = th.dataset.k; S.pSort = [c, S.pSort[0] === c ? -S.pSort[1] : c === "merged" || c === "year" ? -1 : 1]; renderPeople(); };
    if (list.length) lazy($("#rows"), list, personRow, 80);
    else view.insertAdjacentHTML("beforeend", `<div class="empty">No contributors match these filters.</div>`);
  };

  // ---------- insights ----------
  const bars = (title, entries) => {
    const max = entries[0]?.[1] || 1;
    return `<div class="sec"><h2>${title}</h2><div class="bars">${entries.map(([k, n]) => `<div class="bar"><span title="${esc(k)}">${esc(k)}</span><div class="track"><div class="fill" style="width:${(n / max) * 100}%"></div></div><span class="n">${n}</span></div>`).join("")}</div></div>`;
  };
  const top = (arr, n = 15) => { const c = {}; for (const x of arr) c[x] = (c[x] || 0) + 1; return Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, n); };
  const renderInsights = () => {
    io?.disconnect();
    const ps = D.projects.filter((p) => projMatch(p) && (!S.q || p._text.includes(S.q)));
    const os = D.orgs.filter((o) => orgMatch(o) && qOrg(o, S.q));
    stats(ps, os.length);
    const byOrg = top(ps.map((p) => orgBy[p.org]?.name || p.org));
    const merged = Object.entries(ps.reduce((m, p) => { if (p.prs) m[orgBy[p.org]?.name || p.org] = (m[orgBy[p.org]?.name || p.org] || 0) + p.prs.merged; return m; }, {})).sort((a, b) => b[1] - a[1]).slice(0, 15);
    view.innerHTML = `<div class="ins-grid">
      ${bars("Project tech tags", top(ps.flatMap((p) => p.tech.map(norm))))}
      ${bars("Org tech stack", top(os.flatMap((o) => [...o._tech])))}
      ${bars("Orgs by projects", byOrg)}
      ${bars("Orgs by merged PRs (found)", merged)}
      ${bars("Categories", top(os.flatMap((o) => o.categories || [])))}
      ${bars("Community platforms", top(os.flatMap((o) => [...o._plats]).map((k) => (PLAT[k] || PLAT.other)[0])))}
      ${bars("Project size", top(ps.map((p) => p.size || "unknown")))}
      ${bars("Fiscal hosts (Open Collective)", top(os.map((o) => o.facts?.oc?.host).filter(Boolean)))}
    </div>`;
  };

  // ---------- router ----------
  const route = () => location.hash.replace(/^#/, "") || "orgs";
  let prev = route(), listY = 0;
  function update() {
    syncChips();
    more.innerHTML = "";
    const r = route();
    // back from an org page: return to the grid where the user left it
    if (prev === "orgs" && r !== "orgs") listY = scrollY;
    const back = r === "orgs" && prev.startsWith("org/");
    prev = r;
    $("#f-sort").hidden = r !== "orgs";
    document.querySelectorAll(".tabs a").forEach((x) => x.classList.toggle("on", r === x.dataset.tab || (r.startsWith("org/") && x.dataset.tab === "orgs")));
    if (r.startsWith("org/")) renderOrg(decodeURIComponent(r.slice(4)));
    else if (r === "people") renderPeople();
    else if (r === "insights") renderInsights();
    else {
      fill = back ? listY + innerHeight : 0;
      renderOrgs();
      fill = 0;
      if (back) scrollTo(0, listY);
    }
  }
  window.addEventListener("hashchange", update);
  update();
})();
