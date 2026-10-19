/* The model step inside the app.
   Stage 0: questionnaire documents → rules (prompts/extract_rules_v2.md, the same prompt as extract/llm_extract.py).
   Analysis: the regional deviations of the last file check → case files (problem → impact → fix).
   Three ways to reach the model: an Anthropic API key (called from this browser tab, streamed), a Claude chat
   (copy the request, paste the answer back), or the saved run of 10 Oct 2026 (D-002 2022), replayed.
   Only the blank form, instruction, file structure and column names go to the model; for case files, only the
   regional summary (rule, region, shares). Survey records never leave the computer.
   Runs after the main script and uses its globals (B, E, $, esc, pct, FORM, RU, RULESETS, FILE_RS, ...). */
(function () {
const CFG = /*AICFG*/null;
const AI = { docs: [], cols: {}, mode: 'api', abort: null, spec: null, seconds: null, source: '' };
const LIBS = {
  JSZip: 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js',
  XLSX: 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js',
  pdfjsLib: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
};
const FORMNAME = f => FORM[f] || (f === 'OTHER' ? 'Другая форма' : f);
const store = { get(k) { try { return sessionStorage.getItem(k) || ''; } catch (e) { return ''; } }, set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} } };

function loadLib(g) {
  if (window[g]) return Promise.resolve(window[g]);
  return new Promise((ok, bad) => {
    const s = document.createElement('script'); s.src = LIBS[g];
    s.onload = () => { if (g === 'pdfjsLib' && window.pdfjsLib) window.pdfjsLib.GlobalWorkerOptions.workerSrc = LIBS.pdfjsLib.replace('pdf.min.js', 'pdf.worker.min.js'); ok(window[g]); };
    s.onerror = () => bad(new Error('для чтения этого формата нужен интернет'));
    document.head.appendChild(s);
  });
}
function toB64(buf) { const u = new Uint8Array(buf); let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); }
function docxText(xml) {
  return xml.replace(/<w:tab\/>/g, '\t').replace(/<\/w:tc>/g, ' | ').replace(/<\/w:p>/g, '\n').replace(/<[^>]+>/g, '')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&')
    .replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}
async function pdfText(buf) {
  const pdfjs = await loadLib('pdfjsLib'); const doc = await pdfjs.getDocument({ data: new Uint8Array(buf) }).promise; const out = [];
  for (let i = 1; i <= doc.numPages; i++) { const pg = await doc.getPage(i); const tc = await pg.getTextContent(); out.push(tc.items.map(x => x.str + (x.hasEOL ? '\n' : ' ')).join('')); }
  return out.join('\n');
}
async function readFile(f) {
  const ext = (f.name.split('.').pop() || '').toLowerCase();
  if (ext === 'csv') {   // only the header line is read
    const line = (await f.slice(0, 65536).text()).split(/\r?\n/)[0].replace(/^﻿/, '');
    const sep = (line.match(/;/g) || []).length > (line.match(/,/g) || []).length ? ';' : ',';
    const cols = line.split(sep).map(x => x.replace(/"/g, '').trim()).filter(Boolean);
    const [, role] = detect({ cols: Object.fromEntries(cols.map(c => [c, [null]])) });
    return { kind: 'cols', name: f.name, table: role || f.name.replace(/\.csv$/i, '').replace(/_\d{4}$/, ''), cols };
  }
  if (ext === 'doc') throw new Error('формат .doc не читается в браузере — сохраните файл как .docx или PDF');
  if (ext === 'pdf') { const buf = await f.arrayBuffer(); let text = null; try { text = await pdfText(buf.slice(0)); } catch (e) {} return { kind: 'doc', name: f.name, pdf: toB64(buf), text }; }
  if (ext === 'docx') { const JSZip = await loadLib('JSZip'); const z = await JSZip.loadAsync(f); return { kind: 'doc', name: f.name, text: docxText(await z.file('word/document.xml').async('string')) }; }
  if (ext === 'xls' || ext === 'xlsx') {
    const X = await loadLib('XLSX'); const wb = X.read(await f.arrayBuffer(), { type: 'array' });
    const text = wb.SheetNames.map(n => X.utils.sheet_to_json(wb.Sheets[n], { header: 1, blankrows: false, defval: '' })
      .map(r => r.map(c => String(c).trim()).filter(Boolean).join(' | ')).filter(Boolean).join('\n')).join('\n');
    return { kind: 'doc', name: f.name, text };
  }
  return { kind: 'doc', name: f.name, text: await f.text() };
}

/* ---------- inputs ---------- */
function renderInputs() {
  const docs = AI.docs.map((d, k) => `<div class="row"><span class="pill ok">${d.pdf ? 'PDF' : 'текст'}</span><span>${esc(d.name)}</span><span class="muted">${d.saved ? 'из сохранённого запуска' : d.text ? d.text.length.toLocaleString('ru-RU') + ' знаков' : 'передаётся как PDF'}</span><button class="btn" data-rm="d${k}" aria-label="Убрать">×</button></div>`);
  const cols = Object.entries(AI.cols).map(([t, cs]) => `<div class="row"><span class="pill hold">столбцы</span><span>${esc(t)}</span><span class="muted">${cs.length} столбцов (только заголовок)</span><button class="btn" data-rm="c${esc(t)}" aria-label="Убрать">×</button></div>`);
  $('#ai-list').innerHTML = docs.join('') + cols.join('') + (AI.docs.length && !Object.keys(AI.cols).length ? '<p class="muted">Добавьте CSV обследования: модель должна знать точные названия столбцов (сами записи не читаются).</p>' : '');
  $('#ai-list').querySelectorAll('[data-rm]').forEach(b => b.addEventListener('click', () => { const v = b.dataset.rm; if (v[0] === 'd') AI.docs.splice(+v.slice(1), 1); else delete AI.cols[v.slice(1)]; renderInputs(); }));
  const ready = AI.docs.length > 0;
  $('#ai-run').disabled = !ready || !modelReady(); $('#ai-copy').disabled = !ready;
}
async function addFiles(list) {
  if (AI.docs.some(d => d.saved)) { AI.docs = []; AI.cols = {}; }   // new files replace the replayed run's inputs
  $('#ai-status').textContent = 'Читаю файлы…';
  for (const f of list) {
    try { const r = await readFile(f); if (r.kind === 'cols') AI.cols[r.table] = r.cols; else AI.docs.push(r); }
    catch (e) { alertLine(`${f.name}: ${e.message}`); }
  }
  $('#ai-status').textContent = ''; renderInputs();
}
function alertLine(msg) { const p = document.createElement('p'); p.className = 'muted'; p.style.color = 'var(--orange-ink)'; p.textContent = msg; $('#ai-list').after(p); setTimeout(() => p.remove(), 9000); }
const drop = $('#ai-drop'), input = $('#ai-files');
drop.addEventListener('click', e => { if (e.target !== input) input.click(); });
drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
input.addEventListener('change', () => { addFiles([...input.files]); input.value = ''; });
['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => addFiles([...e.dataTransfer.files]));

/* ---------- the request (same text as extract/llm_extract.py) ---------- */
function userText(forChat) {
  const docs = AI.docs.map(d => `=== ${d.name} ===\n${!forChat && d.pdf ? '(PDF приложен к сообщению)' : d.text != null ? d.text : '(PDF приложен к сообщению)'}`).join('\n\n');
  return `Form: ${$('#ai-form').value}\n\nData columns by table:\n${JSON.stringify(AI.cols)}\n\nDocumentation:\n${docs}\n\nReturn only the JSON object.`;
}
function apiContent() {
  const pdfs = AI.docs.filter(d => d.pdf).map(d => ({ type: 'document', title: d.name, source: { type: 'base64', media_type: 'application/pdf', data: d.pdf } }));
  return [...pdfs, { type: 'text', text: userText(false) }];
}

/* ---------- calling the model ---------- */
async function callClaude({ system, content, maxTokens, onText, signal }) {
  const key = $('#ai-key').value.trim(), model = $('#ai-model').value;
  if (!key) throw new Error('введите ключ Anthropic API');
  let res;
  try {
    res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST', signal,
      headers: { 'content-type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true' },
      body: JSON.stringify({ model, max_tokens: maxTokens, system, stream: true, messages: [{ role: 'user', content }] }),
    });
  } catch (e) { if (e.name === 'AbortError') throw e; throw new Error('нет связи с api.anthropic.com (интернет или сетевой фильтр)'); }
  if (!res.ok) {
    let m = ''; try { const j = await res.json(); m = (j.error && j.error.message) || ''; } catch (e) {}
    throw new Error(res.status === 401 ? 'ключ не принят (401)' : res.status === 429 ? 'превышен лимит запросов (429), подождите минуту' : res.status === 529 ? 'модель перегружена (529), повторите' : `ошибка API ${res.status}${m ? ': ' + m : ''}`);
  }
  const reader = res.body.getReader(), dec = new TextDecoder(); let buf = '', text = '', stop = null;
  for (;;) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true }); let i;
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const ev = buf.slice(0, i); buf = buf.slice(i + 2);
      const data = ev.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5).trim()).join('');
      if (!data) continue; let j; try { j = JSON.parse(data); } catch (e) { continue; }
      if (j.type === 'content_block_delta' && j.delta && j.delta.type === 'text_delta') { text += j.delta.text; onText(text); }
      else if (j.type === 'message_delta' && j.delta) stop = j.delta.stop_reason;
      else if (j.type === 'error') throw new Error('ошибка модели: ' + ((j.error && j.error.message) || ''));
    }
  }
  return { text, stop };
}
/* any model with an OpenAI-compatible /v1/chat/completions (Ollama, vLLM, the Bureau's LLM platform, cloud providers) */
async function callOpenAI({ system, text, maxTokens, onText, signal }) {
  const base = $('#ai-oai-url').value.trim().replace(/\/+$/, ''), model = $('#ai-oai-model').value.trim(), key = $('#ai-oai-key').value.trim();
  if (!base || !model) throw new Error('укажите адрес API и название модели');
  let res;
  try {
    res = await fetch(base + '/chat/completions', {
      method: 'POST', signal,
      headers: Object.assign({ 'content-type': 'application/json' }, key ? { authorization: 'Bearer ' + key } : {}),
      body: JSON.stringify({ model, max_tokens: maxTokens, temperature: 0, stream: true, messages: [{ role: 'system', content: system }, { role: 'user', content: text }] }),
    });
  } catch (e) { if (e.name === 'AbortError') throw e; throw new Error(`нет связи с ${base} (сервер не запущен или не разрешает запросы из браузера — CORS)`); }
  if (!res.ok) { let m = ''; try { m = (await res.text()).slice(0, 200); } catch (e) {} throw new Error(`ошибка сервера ${res.status}${m ? ': ' + m : ''}`); }
  const reader = res.body.getReader(), dec = new TextDecoder(); let buf = '', out = '', stop = null;
  for (;;) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true }); let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      if (!line.startsWith('data:')) continue; const data = line.slice(5).trim(); if (data === '[DONE]') continue;
      let j; try { j = JSON.parse(data); } catch (e) { continue; }
      const c = j.choices && j.choices[0]; if (!c) continue;
      const t = (c.delta && c.delta.content) || (c.message && c.message.content) || ''; if (t) { out += t; onText(out); }
      if (c.finish_reason) stop = c.finish_reason === 'length' ? 'max_tokens' : c.finish_reason;
    }
  }
  return { text: out, stop };
}
const modelLabel = () => AI.mode === 'oai' ? $('#ai-oai-model').value.trim() || 'модель' : $('#ai-model').selectedOptions[0].textContent.split(' (')[0];
const modelId = () => AI.mode === 'oai' ? `${$('#ai-oai-model').value.trim()} (${$('#ai-oai-url').value.trim()})` : $('#ai-model').value;
function modelReady() { return AI.mode === 'oai' ? !!($('#ai-oai-url').value.trim() && $('#ai-oai-model').value.trim()) : AI.mode === 'api' ? !!$('#ai-key').value.trim() : false; }
function callModel({ system, content, text, maxTokens, onText, signal }) {
  if (AI.mode === 'oai') return callOpenAI({ system, text, maxTokens: Math.min(maxTokens, 16000), onText, signal });
  return callClaude({ system, content: content || [{ type: 'text', text }], maxTokens, onText, signal });
}
function parseJSON(text, listKey) {
  const a = text.indexOf('{'), b = text.lastIndexOf('}');
  if (a < 0) throw new Error('в ответе нет JSON');
  try { return JSON.parse(text.slice(a, b + 1)); } catch (e) {
    const at = text.indexOf(`"${listKey}"`); let k = b;   // cut off answer: keep every complete item
    while (at > 0 && k > at) { try { const j = JSON.parse(text.slice(a, k + 1) + ']}'); j._truncated = true; return j; } catch (e2) { k = text.lastIndexOf('}', k - 1); } }
    throw new Error('ответ не разобран как JSON');
  }
}

/* ---------- stage 0: run, stream, check, show ---------- */
let timer = null;
function startProgress(label) {
  const t0 = performance.now(); AI.seconds = 0; $('#ai-prog').hidden = false; $('#ai-stream').hidden = false; $('#ai-stream').textContent = ''; $('#ai-out').hidden = true;
  const bar = $('#ai-prog i'); bar.style.width = '3%';
  clearInterval(timer); timer = setInterval(() => { const s = (performance.now() - t0) / 1000; AI.seconds = s; $('#ai-status').textContent = `${label} · ${s.toFixed(0)} с${AI.n ? ` · получено правил: ${AI.n}` : ''}`; bar.style.width = Math.min(95, 3 + s * 0.8) + '%'; }, 250);
  return t0;
}
function onStream(text) { AI.n = (text.match(/"id"\s*:/g) || []).length; const pre = $('#ai-stream'); pre.textContent = text.slice(-1800); pre.scrollTop = pre.scrollHeight; }
function stopProgress() { clearInterval(timer); $('#ai-prog i').style.width = '100%'; setTimeout(() => { $('#ai-prog').hidden = true; }, 600); }

$('#ai-run').addEventListener('click', async () => {
  AI.abort = new AbortController(); $('#ai-run').disabled = true; $('#ai-stop').hidden = false; AI.n = 0;
  if (AI.mode === 'oai' && AI.docs.some(d => d.pdf && d.text == null)) { $('#ai-status').textContent = 'PDF не удалось прочитать как текст (нужен интернет для pdf.js) — сохраните его как DOCX или TXT'; $('#ai-run').disabled = false; $('#ai-stop').hidden = true; return; }
  startProgress(`Модель читает документы (${modelLabel()})`);
  try {
    const { text, stop } = await callModel({ system: CFG.prompt, content: apiContent(), text: userText(true), maxTokens: 32000, onText: onStream, signal: AI.abort.signal });
    stopProgress(); AI.source = `${modelId()}, вызов из приложения, ${new Date().toLocaleString('ru-RU')}`;
    accept(text, stop === 'max_tokens');
  } catch (e) { stopProgress(); $('#ai-status').textContent = e.name === 'AbortError' ? 'Остановлено' : 'Не получилось: ' + e.message; }
  $('#ai-run').disabled = false; $('#ai-stop').hidden = true;
});
$('#ai-stop').addEventListener('click', () => AI.abort && AI.abort.abort());
$('#ai-key').value = store.get('statquo-key');
const PRESETS = { ollama: 'http://localhost:11434/v1', server: '', openrouter: 'https://openrouter.ai/api/v1', custom: '' };
for (const id of ['ai-oai-url', 'ai-oai-model', 'ai-oai-key']) { $('#' + id).value = store.get('statquo-' + id); $('#' + id).addEventListener('input', () => { store.set('statquo-' + id, $('#' + id).value.trim()); renderInputs(); }); }
$('#ai-oai-preset').value = store.get('statquo-preset') || 'ollama';
if (!$('#ai-oai-url').value) $('#ai-oai-url').value = PRESETS[$('#ai-oai-preset').value];
$('#ai-oai-preset').addEventListener('change', e => { store.set('statquo-preset', e.target.value); $('#ai-oai-url').value = PRESETS[e.target.value]; store.set('statquo-ai-oai-url', $('#ai-oai-url').value); if (e.target.value === 'server') $('#ai-oai-url').focus(); renderInputs(); });
$('#ai-key').addEventListener('input', () => { store.set('statquo-key', $('#ai-key').value.trim()); renderInputs(); });
$('#ai-copy').addEventListener('click', async () => {
  const text = CFG.prompt + '\n\n---\n\n' + userText(true);
  const pdfs = AI.docs.filter(d => d.pdf && d.text == null).map(d => d.name);
  try { await navigator.clipboard.writeText(text); $('#ai-copy-st').textContent = `Скопировано: ${text.length.toLocaleString('ru-RU')} знаков.` + (pdfs.length ? ` Приложите в чат: ${pdfs.join(', ')}.` : ''); }
  catch (e) { $('#ai-reply').value = text; $('#ai-copy-st').textContent = 'Буфер обмена недоступен: запрос вставлен в поле ниже — выделите и скопируйте его, затем замените ответом.'; }
});
$('#ai-parse').addEventListener('click', () => { AI.seconds = null; AI.source = 'чат Claude, ответ вставлен вручную'; accept($('#ai-reply').value, false); });
$('#ai-mode').querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
  AI.mode = b.dataset.v; $('#ai-mode').querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
  for (const m of ['api', 'oai', 'chat', 'saved']) $('#ai-m-' + m).hidden = AI.mode !== m;
  $('#ai-run').hidden = !['api', 'oai'].includes(AI.mode); store.set('statquo-mode', AI.mode); renderInputs();
}));
const S = CFG.saved;
$('#ai-saved-note').textContent = `Запуск ${S.when}: модель Claude (Anthropic) получила только бланк ${FORMNAME(S.form)} ${S.year} года и структуру файла (анкета не использовалась при разработке) и работала ${S.seconds} с. Здесь записанный ответ воспроизводится за несколько секунд; дальше всё как при живом вызове.`;
$('#ai-replay').addEventListener('click', async () => {
  $('#ai-form').value = S.form; $('#ai-year').value = String(S.year); AI.cols = JSON.parse(JSON.stringify(S.columns)); AI.docs = S.docs.map(n => ({ kind: 'doc', name: n, text: '(в сохранённом запуске)', saved: true }));
  renderInputs(); AI.n = 0; startProgress('Воспроизвожу сохранённый ответ');
  const txt = S.reply, step = Math.ceil(txt.length / 60);
  for (let i = step; i < txt.length + step; i += step) { onStream(txt.slice(0, i)); await new Promise(r => setTimeout(r, 70)); }
  stopProgress(); AI.seconds = S.seconds; AI.source = `сохранённый запуск ${S.when} (Claude, prompt v2)`; accept(txt, false);
});

const TYPES = { domain: 'Допустимые коды', required: 'Обязательный ответ', skip: 'Переход', multi_select: 'Множественный выбор', consistency: 'Связь ответов', cross_form: 'Связь с другой формой', doc_issue: 'Противоречие в документации' };
function check(spec) {
  const known = new Set(Object.values(AI.cols).flat().map(c => c.toUpperCase())), tables = Object.keys(AI.cols);
  for (const r of spec.rules) {
    const w = [];
    if (!TYPES[r.type]) w.push(`неизвестный вид «${r.type}»`);
    if (!(r.source && r.source.quote)) w.push('нет цитаты');
    if (known.size && r.type !== 'doc_issue') { const miss = (r.targets || []).filter(c => !known.has(String(c).toUpperCase())); if (miss.length) w.push(`нет в данных: ${listCols(miss)}`); }
    if (tables.length && r.table && !['both', 'hh'].includes(r.table) && !tables.includes(r.table)) w.push(`таблица ${r.table} не загружена`);
    if (r.type === 'consistency' && (r.check === 'manual' || !r.check)) w.push('для специалиста');
    r._warn = w;
    r._exec = !['doc_issue', 'cross_form'].includes(r.type) && !(r.type === 'consistency' && (r.check === 'manual' || !r.check)) && TYPES[r.type] && !w.some(x => x.startsWith('нет в данных') || x.startsWith('неизвестный'));
  }
}
function accept(text, cut) {
  let spec;
  try { spec = parseJSON(text, 'rules'); } catch (e) { $('#ai-status').textContent = 'Не получилось: ' + e.message; return; }
  if (!Array.isArray(spec.rules)) { $('#ai-status').textContent = 'В ответе нет списка rules'; return; }
  spec.rules.forEach((r, k) => { if (!r.id) r.id = `AI-${k + 1}`; });
  check(spec); AI.spec = spec; AI.truncated = cut || spec._truncated;
  $('#ai-status').textContent = `Готово: ${spec.rules.length} правил` + (AI.seconds ? ` за ${Math.round(AI.seconds)} с` : '');
  renderSpec();
}
function renderSpec() {
  const sp = AI.spec, rules = sp.rules, form = $('#ai-form').value, year = +$('#ai-year').value;
  const exec = rules.filter(r => r._exec), docs = rules.filter(r => r.type === 'doc_issue'), warn = rules.filter(r => r._warn.length && r.type !== 'doc_issue');
  const by = {}; rules.filter(r => r.type !== 'doc_issue').forEach(r => (by[r.type] = by[r.type] || []).push(r));
  const canRun = ['D002', 'D006', 'D008'].includes(form);
  const out = $('#ai-out'); out.hidden = false;
  out.innerHTML = `<div class="panel stack">
    <div class="row" style="justify-content:space-between"><h2>3. Правила, извлечённые моделью · ${esc(FORMNAME(form))} ${year}</h2>
      <div class="row"><button class="btn" id="ai-dl">Скачать правила (JSON)</button><button class="btn primary" id="ai-apply"${exec.length ? '' : ' disabled'}>Применить: форма и проверка файла →</button></div></div>
    ${AI.truncated ? '<p class="pill err" style="align-self:flex-start">Ответ модели обрезан по длине: показаны все правила, которые пришли целиком</p>' : ''}
    <div class="kpis">
      <div class="kpi"><span class="big">${rules.length}</span><span class="muted">правил и замечаний, у ${rules.filter(r => r.source && r.source.quote).length} есть цитата-источник</span></div>
      <div class="kpi"><span class="big">${exec.length}</span><span class="muted">выполняются программой на записях</span></div>
      <div class="kpi"><span class="big">${docs.length}</span><span class="muted">противоречий в документации</span></div>
      <div class="kpi"><span class="big">${warn.length}</span><span class="muted">на решение специалиста</span></div>
    </div>
    <p class="muted">Источник: ${esc(AI.source)}. Правила проверены программой: вид правила, цитата, есть ли столбцы в данных. Утверждает специалист.${canRun ? '' : ' Проверка файлов в приложении есть для Д-002, Д-006 и Д-008; для этой формы правила можно скачать и выполнить движком на Python.'}</p>
    <div class="stack">${Object.entries(by).sort((a, b) => b[1].length - a[1].length).map(([t, rs], k) => `<details${k === 0 ? ' open' : ''}><summary>${esc(TYPES[t] || t)} — ${rs.length}</summary><div class="stack" style="margin-top:8px">
      ${rs.map(r => `<div class="hit${r._exec ? '' : ' miss'}"><div class="head"><b>${esc(describeRule(r))}</b>${r._warn.map(w => `<span class="pill ${w === 'для специалиста' ? 'miss' : 'err'}">${esc(w)}</span>`).join(' ')}</div>
        ${r.source && r.source.quote ? `<p class="quote">«${esc(r.source.quote)}» — ${esc(DOC[r.source.doc] || r.source.doc || '')}</p>` : ''}<p class="muted"><code>${esc(r.id)}</code>${r.confidence ? ` · уверенность: ${esc({ high: 'высокая', medium: 'средняя', low: 'низкая' }[r.confidence] || r.confidence)}` : ''}</p></div>`).join('')}</div></details>`).join('')}
      ${docs.length ? `<details><summary>Противоречия в документации — ${docs.length}</summary><div class="stack" style="margin-top:8px">${docs.map(r => `<div class="hit miss"><b>${esc(r.note || describeRule(r))}</b>${r.source && r.source.quote ? `<p class="quote">«${esc(r.source.quote)}»</p>` : ''}</div>`).join('')}</div></details>` : ''}
    </div></div>`;
  $('#ai-dl').addEventListener('click', () => download(`rules_${form.toLowerCase()}_${year}_ai.json`, JSON.stringify({ form, years: [year], rules: rules.map(r => { const { _warn, _exec, ...x } = r; return x; }), extracted_by: AI.source + ', prompt v2' }, null, 1), 'application/json'));
  $('#ai-apply').addEventListener('click', () => {
    const key = `AI-${form}-${year}-${Object.keys(RULESETS).length}`;
    RULESETS[key] = { key, form, year, label: `${FORMNAME(form)} ${year} · правила ИИ`, rules: rules.filter(r => r.type === 'doc_issue' || r._exec).map(r => { const { _warn, _exec, ...x } = r; return x; }), ai: true };
    if (canRun) { for (const k of Object.keys(FILE_RS)) delete FILE_RS[k]; FILE_RS[form] = key; $('#f-year').value = String(year); }
    selectRuleset(key); openTab('t-entry'); window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

/* ---------- analysis: the model writes case files from the regional summary ---------- */
const CASE_SYSTEM = `Ты — методолог Бюро национальной статистики Казахстана. Тебе дана сводка отклонений, которые программа нашла при проверке файла обследования домохозяйств по регионам. Для каждого отклонения: номер, форма, год, регион, правило анкеты (текст и цитата из документации), доля нарушений в регионе и в остальной стране (в процентах), число записей, к которым применимо правило, и статус: «держится» — вывод устойчив на синтетических данных; «проверить» — его нужно подтвердить на реальных записях.

Сгруппируй связанные отклонения в дела (не больше 6, сначала самые важные для официальной статистики). Для каждого дела верни:
- "title": короткое название;
- "issues": номера отклонений из сводки;
- "finding": что выявлено — только числа из сводки, с указанием региона и года;
- "indicator": какой официальный показатель или раздел публикации это может исказить и в какую сторону;
- "cause": вероятная причина (гипотеза: формулировка бланка, инструкция, ввод данных, своё кодирование в регионе);
- "fix": что исправить (инструкция, бланк, контроль при вводе, проверка на реальных записях);
- "confidence": "высокая", "средняя" или "низкая".
Не придумывай чисел, которых нет в сводке. Если у отклонений статус «проверить», так и напиши. Пиши по-русски, коротко и конкретно. Ответ — только JSON {"cases": [...]}.`;
function caseInput() {
  const list = [...RUN.issues].sort((a, b) => (a.status === b.status ? 0 : a.status === 'hold' ? -1 : 1) || b.excess - a.excess).slice(0, 25);
  return { list, json: list.map((i, k) => ({ n: k + 1, form: FORM[i.form], year: i.year, region: RU[i.region] || i.region, rule: i.ru || i.rule_id, quote: i.quote || '', rate_region: +i.rate_region.toFixed(1), rate_rest: +i.rate_rest.toFixed(1), records: i.records, status: i.status === 'hold' ? 'держится' : 'проверить' })) };
}
function numbersIn(s) { return (String(s).match(/(?<![\p{L}\d_.,])\d+(?:[.,]\d+)?/gu) || []).map(x => x.replace(',', '.')); }
function verify(cases, inputJSON) {
  const ok = new Set(numbersIn(JSON.stringify(inputJSON)).flatMap(x => [x, String(+x), (+x).toFixed(1), (+x).toFixed(0)]));
  let n = 0, good = 0;
  const mark = s => esc(s).replace(/(?<![\p{L}\d_.,])\d+(?:[.,]\d+)?/gu, m => { n++; const v = m.replace(',', '.'); if (ok.has(v) || ok.has(String(+v))) { good++; return m; } return `<mark title="Этого числа нет в расчёте" style="background:var(--orange-1);color:var(--orange-ink)">${m}</mark>`; });
  const html = cases.map(c => ({ ...c, _f: mark(c.finding || ''), _i: mark(c.indicator || '') }));
  return { html, n, good };
}
function renderAiCases() {
  let box = $('#a-ai');
  if (!box) { box = document.createElement('div'); box.id = 'a-ai'; box.className = 'panel stack'; $('#a-loose').before(box); }
  if (!RUN) { box.hidden = true; return; }
  box.hidden = false;
  if (!RUN.issues.length) { box.innerHTML = '<h2>Дела по этой проверке · ИИ</h2><p class="muted">В последней проверке отклонений нет — составлять дела не из чего.</p>'; return; }
  if (AI.cases && AI.cases.run === RUN) return drawCases(box);
  box.innerHTML = `<div class="row" style="justify-content:space-between"><h2>Дела по этой проверке · ИИ</h2>
      <div class="row"><button class="btn primary" id="ac-run">Составить дела</button><button class="btn" id="ac-copy">Скопировать запрос</button></div></div>
    <p class="muted">Модель получает только сводку отклонений последней проверки (правило, регион, доли, число записей) — ни одной записи — и группирует их в дела «проблема → влияние → рекомендация». Числа в тексте программа сверяет с расчётом. Модель — та, что выбрана на этапе 0 (Claude или другая), или ответ из чата.</p>
    <div id="ac-paste" class="stack" hidden><textarea id="ac-reply" rows="5" placeholder="Вставьте ответ модели (JSON)" style="font:12.5px var(--mono);width:100%;border:1px solid var(--line-strong);border-radius:8px;padding:8px;background:var(--surface);color:var(--fg)"></textarea><div class="row"><button class="btn primary" id="ac-parse">Разобрать ответ</button></div></div>
    <span id="ac-status" class="muted"></span><pre id="ac-stream" class="sql" hidden style="max-height:140px;overflow:auto"></pre>`;
  const inp = caseInput(), user = 'Сводка отклонений:\n' + JSON.stringify(inp.json, null, 1);
  $('#ac-copy').addEventListener('click', async () => { $('#ac-paste').hidden = false; try { await navigator.clipboard.writeText(CASE_SYSTEM + '\n\n---\n\n' + user); $('#ac-status').textContent = 'Запрос скопирован: вставьте его в чат Claude, ответ — в поле ниже.'; } catch (e) { $('#ac-reply').value = CASE_SYSTEM + '\n\n---\n\n' + user; $('#ac-status').textContent = 'Буфер обмена недоступен: запрос в поле ниже.'; } });
  $('#ac-parse').addEventListener('click', () => take($('#ac-reply').value, 'чат Claude'));
  $('#ac-run').addEventListener('click', async () => {
    if (!modelReady()) { $('#ac-status').textContent = 'Модель не настроена: на этапе 0 выберите «Claude · ключ API» или «Другая модель» и заполните поля, либо используйте «Скопировать запрос».'; return; }
    $('#ac-run').disabled = true; const t0 = performance.now(); const pre = $('#ac-stream'); pre.hidden = false;
    const tick = setInterval(() => { $('#ac-status').textContent = `Модель пишет дела · ${((performance.now() - t0) / 1000).toFixed(0)} с`; }, 250);
    try { const { text } = await callModel({ system: CASE_SYSTEM, text: user, maxTokens: 8000, onText: t => { pre.textContent = t.slice(-1200); pre.scrollTop = pre.scrollHeight; } }); clearInterval(tick); take(text, `${modelId()}, ${((performance.now() - t0) / 1000).toFixed(0)} с`); }
    catch (e) { clearInterval(tick); $('#ac-status').textContent = 'Не получилось: ' + e.message; $('#ac-run').disabled = false; }
  });
  function take(text, src) {
    let j; try { j = parseJSON(text, 'cases'); } catch (e) { $('#ac-status').textContent = 'Не получилось: ' + e.message; return; }
    AI.cases = { run: RUN, cases: j.cases || [], input: inp, src }; drawCases(box);
  }
}
function drawCases(box) {
  const C = AI.cases, v = verify(C.cases, C.input.json);
  box.innerHTML = `<div class="row" style="justify-content:space-between"><h2>Дела по этой проверке · ИИ</h2><div class="row"><span class="pill ${v.good === v.n ? 'ok' : 'err'}">Числа сверены с расчётом: ${v.good} из ${v.n}</span><button class="btn" id="ac-again">Составить заново</button></div></div>
    <p class="muted">Источник: ${esc(C.src)}. Модель видела только сводку из ${C.input.list.length} отклонений. Числа, которых нет в расчёте, подсвечены. Выводы — гипотезы для методолога.</p>
    ${v.html.map((c, k) => `<article class="hit" style="border-left-color:var(--blue)"><div class="head"><b>И${k + 1}. ${esc(c.title || '')}</b><span class="pill ${c.confidence === 'высокая' ? 'hold' : 'miss'}">${esc(c.confidence || '')}</span></div>
      <div class="cols3"><div class="stack" style="gap:4px"><p class="lbl">1 · Проблема</p><p>${c._f}</p></div>
        <div class="stack" style="gap:4px"><p class="lbl">2 · Влияние</p><p>${c._i}</p></div>
        <div class="stack" style="gap:4px"><p class="lbl">3 · Рекомендация</p><p>${esc(c.fix || '')}</p><p class="muted"><b>Вероятная причина:</b> ${esc(c.cause || '')}</p></div></div>
      <p class="muted">Отклонения: ${(c.issues || []).map(n => { const i = C.input.list[n - 1]; return i ? `${esc(RU[i.region] || i.region)} · ${esc(FORM[i.form])} (${n})` : n; }).join('; ')}</p></article>`).join('')}`;
  $('#ac-again').addEventListener('click', () => { AI.cases = null; renderAiCases(); });
}
const baseRender = renderAnalysis;
renderAnalysis = function () { baseRender(); renderAiCases(); };
const m0 = store.get('statquo-mode'); if (m0 && m0 !== 'api') { const b = $(`#ai-mode button[data-v="${m0}"]`); if (b) b.click(); }
renderInputs();
})();
