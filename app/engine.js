/* StatQUO check engine for the browser — a line-by-line port of engine/statquo.py (run_rules, flag_regions,
   synthesis_check). Same rule files (rules/*.json), same results; checked against the Python outputs.
   Works in the browser (window.StatQUO) and in Node (module.exports). */
(function (root) {
  'use strict';
  const REGION = { "10": "Abai", "11": "Akmola", "15": "Aktobe", "19": "Almaty oblast", "23": "Atyrau",
    "27": "West Kazakhstan", "31": "Zhambyl", "33": "Zhetysu", "35": "Karaganda", "39": "Kostanay",
    "43": "Kyzylorda", "47": "Mangystau", "55": "Pavlodar", "59": "North Kazakhstan", "61": "Turkistan",
    "62": "Ulytau", "63": "East Kazakhstan", "71": "Astana", "75": "Almaty city", "79": "Shymkent" };
  // pandas read_csv default NA strings (dtype=str keeps everything else as text)
  const NA = new Set(["", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan", "1.#IND", "1.#QNAN",
    "<NA>", "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null"]);

  /* ---------- tables: {cols: {NAME: array of string|null}, n} ---------- */
  function parseCSV(text) {
    // RFC-4180 parser (quotes, commas, CRLF); the survey files are plain comma CSV
    const rows = []; let row = [], f = '', q = false, i = 0;
    if (text.charCodeAt(0) === 0xFEFF) i = 1;
    for (; i < text.length; i++) {
      const c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c;
      } else if (c === '"') q = true;
      else if (c === ',') { row.push(f); f = ''; }
      else if (c === '\n' || c === '\r') {
        if (c === '\r' && text[i + 1] === '\n') i++;
        row.push(f); rows.push(row); row = []; f = '';
      } else f += c;
    }
    if (f !== '' || row.length) { row.push(f); rows.push(row); }
    while (rows.length && rows[rows.length - 1].length === 1 && rows[rows.length - 1][0] === '') rows.pop();
    const head = rows[0].map(h => h.trim().toUpperCase());
    const cols = {}; head.forEach(h => { cols[h] = new Array(rows.length - 1); });
    for (let r = 1; r < rows.length; r++) {
      const rr = rows[r];
      for (let j = 0; j < head.length; j++) {
        const raw = rr[j];
        cols[head[j]][r - 1] = (raw === undefined || NA.has(raw)) ? null : raw.trim();
      }
    }
    return { cols, n: rows.length - 1 };
  }
  const has = (t, c) => Object.prototype.hasOwnProperty.call(t.cols, c);
  const num1 = v => { if (v === null || v === undefined) return NaN; const s = String(v).trim(); if (s === '') return NaN; const x = Number(s); return Number.isFinite(x) ? x : NaN; };
  const filled1 = v => v !== null && v !== undefined && String(v).trim() !== '';
  const str1 = v => (v === null || v === undefined) ? 'nan' : String(v);
  const lstrip0 = s => s.replace(/^0+/, '');
  const fill = (n, v) => { const a = new Uint8Array(n); if (v) a.fill(1); return a; };

  function whenMask(t, cond) {
    const n = t.n;
    if (cond === null || cond === undefined) return fill(n, 1);
    if (cond.all) { const m = fill(n, 1); for (const c of cond.all) { const k = whenMask(t, c); for (let i = 0; i < n; i++) m[i] &= k[i]; } return m; }
    if (cond.any) { const m = fill(n, 0); for (const c of cond.any) { const k = whenMask(t, c); for (let i = 0; i < n; i++) m[i] |= k[i]; } return m; }
    const col = cond.col; const m = fill(n, 0);
    if (!has(t, col)) return m;
    const a = t.cols[col];
    if (cond.blank) { for (let i = 0; i < n; i++) m[i] = filled1(a[i]) ? 0 : 1; return m; }
    if (cond.filled) { for (let i = 0; i < n; i++) m[i] = filled1(a[i]) ? 1 : 0; return m; }
    if ('lt' in cond) { for (let i = 0; i < n; i++) m[i] = num1(a[i]) < cond.lt ? 1 : 0; return m; }
    if ('ge' in cond) { for (let i = 0; i < n; i++) m[i] = num1(a[i]) >= cond.ge ? 1 : 0; return m; }
    const set = new Set(cond.in.map(Number));
    for (let i = 0; i < n; i++) { const x = num1(a[i]); m[i] = (!Number.isNaN(x) && set.has(x)) ? 1 : 0; }
    return m;
  }

  function tablesFor(rule, tables) {
    const t = rule.table || 'both';
    if (t === 'both') return Object.keys(tables).filter(k => k !== 'hh').map(k => [k, tables[k]]);
    return tables[t] ? [[t, tables[t]]] : [];
  }

  /* yields [table, column, applicable, violation, state|null] like evaluate() in statquo.py */
  function evaluate(rule, tables) {
    const out = [], typ = rule.type;
    const skip = new Set(((rule.skip_targets_by_year || {})[String(rule._year)]) || []);
    for (const [tname, t] of tablesFor(rule, tables)) {
      const n = t.n;
      const cols = (rule.targets || []).filter(c => has(t, c) && !skip.has(c));
      if (typ === 'domain') {
        const a = rule.allowed;
        for (const c of cols) {
          const x = t.cols[c], f = fill(n, 0), bad = fill(n, 0);
          for (let i = 0; i < n; i++) f[i] = filled1(x[i]) ? 1 : 0;
          if (a && !Array.isArray(a) && a.codebook) throw new Error('codebook rule: needs the code book file');
          if (a && !Array.isArray(a) && a.equals_column) {
            const y = has(t, a.equals_column) ? t.cols[a.equals_column] : new Array(n).fill(null);
            for (let i = 0; i < n; i++) bad[i] = f[i] && lstrip0(str1(x[i])) !== lstrip0(str1(y[i])) ? 1 : 0;
          } else if (a && !Array.isArray(a) && a.equals_year) {
            for (let i = 0; i < n; i++) bad[i] = f[i] && num1(x[i]) !== rule._year ? 1 : 0;
          } else if (Array.isArray(a) && a.some(v => typeof v === 'string')) {
            const set = new Set(a.map(String));
            for (let i = 0; i < n; i++) bad[i] = f[i] && !set.has(str1(x[i]).trim()) ? 1 : 0;
          } else if (a && !Array.isArray(a) && a.no_leading_zero) {
            for (let i = 0; i < n; i++) bad[i] = f[i] && /^0[0-9]/.test(str1(x[i])) ? 1 : 0;
          } else if (a && !Array.isArray(a) && ('min' in a || 'max' in a)) {
            const lo = 'min' in a ? a.min : -Infinity, hi = 'max' in a ? a.max : Infinity;
            for (let i = 0; i < n; i++) { const v = num1(x[i]); bad[i] = f[i] && !(v >= lo && v <= hi) ? 1 : 0; }
          } else if (!a || (Array.isArray(a) && !a.length)) {
            throw new Error('domain rule without allowed codes');
          } else {
            const set = new Set(a.map(Number));
            for (let i = 0; i < n; i++) { const v = num1(x[i]); bad[i] = f[i] && !(!Number.isNaN(v) && set.has(v)) ? 1 : 0; }
          }
          out.push([tname, c, f, bad, null]);
        }
      } else if (typ === 'required') {
        const app = whenMask(t, rule.when);
        if (rule.mode === 'any') {
          if (cols.length) {
            const state = fill(n, 0), bad = fill(n, 0);
            for (let i = 0; i < n; i++) { let any = 0; for (const c of cols) if (filled1(t.cols[c][i])) { any = 1; break; } state[i] = any ? 0 : 1; bad[i] = app[i] & state[i]; }
            out.push([tname, cols.join('|'), app, bad, state]);
          }
        } else {
          for (const c of cols) {
            const x = t.cols[c], state = fill(n, 0), bad = fill(n, 0);
            for (let i = 0; i < n; i++) { state[i] = filled1(x[i]) ? 0 : 1; bad[i] = app[i] & state[i]; }
            out.push([tname, c, app, bad, state]);
          }
        }
      } else if (typ === 'skip') {
        const app = whenMask(t, rule.when);
        for (const c of cols) {
          const x = t.cols[c], state = fill(n, 0), bad = fill(n, 0);
          for (let i = 0; i < n; i++) { state[i] = filled1(x[i]) ? 1 : 0; bad[i] = app[i] & state[i]; }
          out.push([tname, c, app, bad, state]);
        }
      } else if (typ === 'multi_select') {
        for (const c of cols) {
          const x = t.cols[c], f = fill(n, 0), bad = fill(n, 0);
          for (let i = 0; i < n; i++) { f[i] = filled1(x[i]) ? 1 : 0; bad[i] = f[i] && num1(x[i]) !== 1 ? 1 : 0; }
          out.push([tname, c, f, bad, null]);
        }
        const ex = (rule.exclusive || []).filter(c => has(t, c));
        const others = cols.filter(c => !ex.includes(c));
        for (const c of ex) {
          const app = fill(n, 0), bad = fill(n, 0);
          for (let i = 0; i < n; i++) { app[i] = filled1(t.cols[c][i]) ? 1 : 0; if (app[i]) { for (const o of others) if (filled1(t.cols[o][i])) { bad[i] = 1; break; } } }
          out.push([tname, c + '+other', app, bad, null]);
        }
      } else if (typ === 'consistency') {
        const chk = rule.check;
        if (chk === undefined || chk === null) throw new Error("consistency rule without a 'check'");
        if (chk === 'manual') throw new Error("marked 'manual' by the extraction: for a person to check");
        const all1 = fill(n, 1);
        if (chk === 'implies') {
          const app = whenMask(t, rule.if), ok = whenMask(t, rule.then), bad = fill(n, 0), state = fill(n, 0);
          for (let i = 0; i < n; i++) { state[i] = ok[i] ? 0 : 1; bad[i] = app[i] & state[i]; }
          out.push([tname, (rule.then && rule.then.col) || (rule.targets || []).join('+'), app, bad, state]);
        } else if (chk === 'lte') {
          const x = has(t, rule.a) ? t.cols[rule.a] : null, y = has(t, rule.b) ? t.cols[rule.b] : null;
          if (!x || !y) throw new Error('KeyError: ' + (!x ? rule.a : rule.b));
          const app = fill(n, 0), bad = fill(n, 0);
          for (let i = 0; i < n; i++) { const a = num1(x[i]), b = num1(y[i]); app[i] = (!Number.isNaN(a) && !Number.isNaN(b)) ? 1 : 0; bad[i] = app[i] && a > b ? 1 : 0; }
          out.push([tname, rule.a + '<=' + rule.b, app, bad, null]);
        } else if (chk === 'hh_size') {
          const cnt = {}, k = t.cols.NOMER; for (let i = 0; i < n; i++) cnt[k[i]] = (cnt[k[i]] || 0) + 1;
          const bad = fill(n, 0); for (let i = 0; i < n; i++) bad[i] = num1(t.cols.KOL_CHL[i]) !== cnt[k[i]] ? 1 : 0;
          out.push([tname, 'KOL_CHL', all1, bad, null]);
        } else if (chk === 'one_head') {
          const h = {}, k = t.cols.NOMER; for (let i = 0; i < n; i++) h[k[i]] = (h[k[i]] || 0) + (num1(t.cols.RODSTVO[i]) === 1 ? 1 : 0);
          const bad = fill(n, 0); for (let i = 0; i < n; i++) bad[i] = h[k[i]] !== 1 ? 1 : 0;
          out.push([tname, 'RODSTVO', all1, bad, null]);
        } else if (chk === 'head_is_member1') {
          const app = fill(n, 0), bad = fill(n, 0);
          for (let i = 0; i < n; i++) { app[i] = lstrip0(str1(t.cols.NOMP[i])) === '1' ? 1 : 0; bad[i] = app[i] && num1(t.cols.RODSTVO[i]) !== 1 ? 1 : 0; }
          out.push([tname, 'RODSTVO', app, bad, null]);
        } else if (chk === 'unique') {
          const seen = {}, keys = new Array(n);
          for (let i = 0; i < n; i++) { keys[i] = cols.map(c => t.cols[c][i] === null ? '\u0000NA' : t.cols[c][i]).join('\u0001'); seen[keys[i]] = (seen[keys[i]] || 0) + 1; }
          const bad = fill(n, 0); for (let i = 0; i < n; i++) bad[i] = seen[keys[i]] > 1 ? 1 : 0;
          out.push([tname, cols.join('+'), all1, bad, null]);
        } else if (chk === 'refusal_all_or_none') {
          const bad = fill(n, 0);
          for (let i = 0; i < n; i++) { let any = false, all = true; for (const c of cols) { const v = num1(t.cols[c][i]); if (v === rule.code) any = true; else all = false; } bad[i] = any && !all ? 1 : 0; }
          out.push([tname, 'FIES block', all1, bad, null]);
        } else if (chk === 'tables_agree') {
          if (tname === Object.keys(tables)[0]) {
            const otherName = Object.keys(tables).filter(k => k !== tname)[0], o = tables[otherName];
            const idx = {}; const ok = o.cols[rule.key];
            for (let j = 0; j < o.n; j++) if (!(ok[j] in idx)) idx[ok[j]] = j;
            const bad = fill(n, 0), key = t.cols[rule.key];
            for (let i = 0; i < n; i++) {
              const j = idx[key[i]];
              for (const c of cols) {
                const a = t.cols[c][i], b = (j === undefined || !has(o, c)) ? null : o.cols[c][j];
                if (a === null || b === null || a !== b) { bad[i] = 1; break; }
              }
            }
            out.push([tname, cols.join('+'), all1, bad, null]);
          }
        }
      }
    }
    return out;
  }

  /* ---------- loading a form from files ---------- */
  function addAge(t, year) {
    if (!has(t, 'GOD_ROJD')) return;
    const a = new Array(t.n);
    for (let i = 0; i < t.n; i++) { const g = num1(t.cols.GOD_ROJD[i]); a[i] = Number.isNaN(g) ? null : (year - g).toFixed(1); }
    t.cols.AGE = a;
  }
  function mergeHH(sub, oc) {
    const idx = {}; for (let j = 0; j < oc.n; j++) { const k = oc.cols.NOMER[j]; (idx[k] = idx[k] || []).push(j); }
    const ocOnly = Object.keys(oc.cols).filter(c => !has(sub, c));
    const cols = {}; Object.keys(sub.cols).forEach(c => cols[c] = []); ocOnly.forEach(c => cols[c] = []);
    let n = 0;
    for (let i = 0; i < sub.n; i++) {
      const js = idx[sub.cols.NOMER[i]]; if (!js) continue;
      for (const j of js) { for (const c in sub.cols) cols[c].push(sub.cols[c][i]); for (const c of ocOnly) cols[c].push(oc.cols[c][j]); n++; }
    }
    return { cols, n };
  }
  function attachRoster(tables, roster, year) {
    const u18 = {};
    for (let i = 0; i < roster.n; i++) { const g = num1(roster.cols.GOD_ROJD[i]); const k = roster.cols.NOMER[i]; const under = (year - g) < 18; if (!(k in u18)) u18[k] = false; if (under) u18[k] = true; }
    const oc = tables.ocenka, a = new Array(oc.n);
    for (let i = 0; i < oc.n; i++) { const k = oc.cols.NOMER[i]; a[i] = (k in u18) ? (u18[k] ? '1' : '2') : null; }
    const copy = { n: oc.n, cols: Object.assign({}, oc.cols, { ROSTER_U18: a }) };
    return Object.assign({}, tables, { ocenka: copy });
  }
  /* files: {subject, ocenka} for D002, {rio} for D006, {kontr_k} for D008 (parsed tables); roster optional for D002 */
  function buildTables(form, files, year) {
    if (form === 'D002') {
      let t = { subject: files.subject, ocenka: files.ocenka };
      t.hh = mergeHH(files.subject, files.ocenka);
      if (files.roster) t = attachRoster(t, files.roster, year);
      return t;
    }
    if (form === 'D006') return { rio: files.rio };
    if (form === 'D008') { addAge(files.kontr_k, year); return { kontr_k: files.kontr_k }; }
    throw new Error('unknown form ' + form);
  }

  function runRules(rules, tables, year, opts) {
    opts = opts || {};
    const rows = [], notRun = [];
    const haveRoster = !!(tables.ocenka && has(tables.ocenka, 'ROSTER_U18'));
    for (const r0 of rules) {
      if (r0.type === 'doc_issue' || r0.type === 'cross_form' || r0.superseded_by) continue;
      if (!haveRoster && JSON.stringify(r0).includes('ROSTER_U18')) { notRun.push({ rule_id: r0.id, type: r0.type, reason: 'нужен файл Д-008 (список членов домохозяйства)' }); continue; }
      const rule = Object.assign({}, r0, { _year: year });
      let items;
      try { items = evaluate(rule, tables); } catch (e) { notRun.push({ rule_id: rule.id, type: rule.type, reason: String(e.message || e).slice(0, 200) }); continue; }
      if (!items.length) notRun.push({ rule_id: rule.id, type: rule.type, reason: 'в файле нет столбцов этого правила' });
      for (const [tname, col, app, bad, state] of items) {
        const te = tables[tname].cols.TE, g = {};
        for (let i = 0; i < tables[tname].n; i++) {
          const k = te[i]; if (k === null) continue;
          const s = g[k] || (g[k] = { rec: 0, app: 0, bad: 0, state: 0 });
          s.rec++; s.app += app[i]; s.bad += bad[i]; s.state += (state ? state[i] : bad[i]);
        }
        Object.keys(g).sort().forEach(code => {
          const s = g[code];
          rows.push({ rule_id: rule.id, type: rule.type, table: tname, column: col, year, te: code, region: REGION[code] || code,
            records: s.rec, applicable: s.app, violations: s.bad, conditional: !!state, bad_state: s.state,
            rate: s.app > 0 ? s.bad / s.app : NaN });
        });
      }
    }
    return { rows, notRun };
  }

  function synthesisCheck(applicable, badState, records, violations) {
    const pa = applicable / Math.max(records, 1), pb = badState / Math.max(records, 1);
    if (applicable === 0) return [NaN, NaN, 'no cases'];
    const obs = violations / applicable, floor = Math.max(0, pa + pb - 1) / pa, indep = pb;
    let label;
    if (obs < 0.01) label = 'holds';
    else if (floor >= 0.5 * obs) label = 'forced by the answer shares';
    else if (indep > 0 && obs >= 0.7 * indep) label = 'could be broken links in the synthetic data';
    else label = 'partly forced';
    return [floor, indep, label];
  }

  function flagRegions(rows, o) {
    o = Object.assign({ minRate: 0.05, ratio: 3.0, minN: 30, minExcess: 10 }, o || {});
    const groups = {};
    for (const r of rows) { const k = r.rule_id + '\u0001' + r.column + '\u0001' + r.year; (groups[k] = groups[k] || []).push(r); }
    const out = [];
    for (const k of Object.keys(groups)) {
      const g = groups[k];
      let ta = 0, tb = 0, tn = 0; for (const r of g) { ta += r.applicable; tb += r.violations; tn += r.records; }
      for (const r of g) {
        const ra = ta - r.applicable, rb = tb - r.violations, rn = tn - r.records;
        if (r.applicable < o.minN || ra < o.minN) continue;
        const p1 = r.violations / r.applicable, p0 = rb / ra, p = (r.violations + rb) / (r.applicable + ra);
        const se = Math.sqrt(p * (1 - p) * (1 / r.applicable + 1 / ra));
        const z = se > 0 ? (p1 - p0) / se : NaN;
        const excess = r.violations - r.applicable * p0;
        const test1 = p1 >= o.minRate && p1 >= o.ratio * Math.max(p0, 1e-9) && z > 3;
        if (!test1) continue;
        let floor = NaN, indep = NaN, label = 'not conditional';
        if (r.conditional) [floor, indep, label] = synthesisCheck(r.applicable, r.bad_state, r.records, r.violations);
        out.push({ synthesis: label, floor, independent: indep, rule_id: r.rule_id, type: r.type, column: r.column, year: r.year,
          te: r.te, region: r.region, records: r.records, applicable: r.applicable, violations: r.violations,
          rate_region: 100 * p1, rate_rest: 100 * p0, z, excess, flag: excess >= o.minExcess });
      }
    }
    return out;
  }

  /* ---------- one record at a time (entry module): which rules does this answer set break? ----------
     A rule is checked when every column its condition names is on the entry form and at least one of its
     targets is; only the targets on the form are checked. Returns [{rule, column, kind}] for broken rules. */
  function condCols(c, acc) { if (!c) return acc; if (c.all) c.all.forEach(x => condCols(x, acc)); else if (c.any) c.any.forEach(x => condCols(x, acc)); else if (c.col) acc.push(c.col); return acc; }
  function checkRecord(rules, record, year) {
    const t = { n: 1, cols: {} };
    Object.keys(record).forEach(c => { const v = record[c]; t.cols[c] = [v === '' || v === undefined ? null : String(v)]; });
    const tables = { entry: t }, hits = [];
    for (const r0 of rules) {
      if (r0.type === 'doc_issue' || r0.type === 'cross_form' || r0.superseded_by) continue;
      if (r0.type === 'consistency' && r0.check !== 'implies' && r0.check !== 'lte') continue;   // checks that need one record only
      const conds = condCols(r0.when, []).concat(condCols(r0.if, []), r0.type === 'consistency' ? condCols(r0.then, []) : [], r0.check === 'lte' ? [r0.a, r0.b] : []);
      if (!conds.every(c => has(t, c))) continue;
      if (r0.type !== 'consistency' && !(r0.targets || []).some(c => has(t, c))) continue;
      let items; try { items = evaluate(Object.assign({}, r0, { table: 'entry', _year: year }), tables); } catch (e) { continue; }
      for (const [, col, app, bad] of items) if (app[0] && bad[0]) hits.push({ rule: r0, column: col, kind: r0.type === 'required' ? 'missing' : 'error' });
    }
    return hits;
  }

  const api = { REGION, parseCSV, buildTables, runRules, flagRegions, synthesisCheck, checkRecord, evaluate, whenMask };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.StatQUO = api;
})(typeof window !== 'undefined' ? window : globalThis);
