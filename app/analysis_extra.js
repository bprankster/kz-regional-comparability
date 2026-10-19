/* Analysis sections carried over from the StatQUO console (console/console.html).
   The render functions are the console's own code, unchanged except for class names that clash with the app
   (steps/step/case → xsteps/xstep/xcase) and the tooltip id. Data: console/data.json, embedded by build_app.py. */
window.StatQUOAnalysis = (function (D) {
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const pct = (x, d = 1) => x == null ? '—' : x.toFixed(d).replace('.', ',') + '%';
const num = (x, d = 1) => x == null ? '—' : x.toFixed(d).replace('.', ',');
const RU = Object.fromEntries(D.regions.map(r => [r.key, r.ru]));
const state = { childYear: 2024, finYear: 2024 };
const save = () => {};
const tip = $('#x-tip');
function showTip(e, html) { tip.innerHTML = html; tip.hidden = false; moveTip(e); }
function moveTip(e) { const x = Math.min(e.clientX + 14, innerWidth - 300), y = e.clientY + 16; tip.style.left = x + 'px'; tip.style.top = y + 'px'; }
function hideTip() { tip.hidden = true; }
function seg(el, opts, key, after) {
  el.innerHTML = opts.map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${String(state[key]) === String(v)}">${l}</button>`).join('');
  el.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
    state[key] = isNaN(+b.dataset.v) ? b.dataset.v : +b.dataset.v; save();
    el.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b)); after();
  }));
}
function rateRows(i) {
  if (i.rateRegion == null) return '';
  const mx = Math.max(i.rateRegion, i.rateRest, 1);
  const w = v => Math.max(1.5, 100 * v / Math.max(100, mx));
  return `<div class="rate"><span>${esc(RU[i.region] || i.region)}</span><div class="bar"><i style="width:${w(i.rateRegion)}%;background:var(--${i.status === 'держится' ? 'blue' : 'orange'})"></i></div><span class="num">${pct(i.rateRegion)}</span>
  <span>Остальная страна</span><div class="bar"><i style="width:${w(i.rateRest)}%;background:var(--fg-3)"></i></div><span class="num">${pct(i.rateRest)}</span></div>`;
}
/* ---------- household finance tab (case C11) ---------- */
function renderFin() {
  const el = $('#p-fin');
  if (!D.fin || !D.fin.length) { el.innerHTML = '<p class="muted">Шаг analysis/finance_impact.py не запускался.</p>'; return; }
  const y = state.finYear, rows = D.fin.filter(r => r.year === y).sort((a, b) => a.cov - b.cov);
  const n = D.finNat.find(x => x.year === y);
  const low = rows.filter(r => r.covFlag), mang = rows.find(r => r.region === 'Mangystau');
  const B = v => Math.max(0, Math.min(100, v / 70 * 100));
  el.innerHTML = `<div class="panel stack">
    <div class="row" style="justify-content:space-between"><h2>Финансы домохозяйств (Д-004): что меняет показатель уязвимости</h2><div class="seg" id="fin-year" role="group" aria-label="Год"></div></div>
    <p class="muted" style="max-width:80ch">Квартальный журнал Д-004: расходы (разделы 1.1–1.3), займы (раздел 2), доходы (раздел 3). Единица — домохозяйство за квартал, участвовавшее в обследовании; без весов. Те же вопросы, что и в детском случае: какие правила анкеты и какие региональные различия меняют цифру до публикации и насколько.</p>
    <div class="callout">
      <div><div class="big">${pct(n.savings_rate_naive_pct)}</div><div class="muted">«норма сбережений», если читать Д-004 напрямую. Раздела о питании в журнале нет: записанные расходы — ${pct(n.recorded_spend_to_income_pct)} дохода, с питанием (половина расходов по данным БНС) было бы около ${pct(n.implied_spend_to_income_if_food_half_pct, 0)}. Публиковать нельзя</div></div>
      <div><div class="big">+${num(n.gr3_added_pct, 1)}%</div><div class="muted">дохода добавляет сумма всех 23 столбцов: GR3 в анкете — «из него» внутри GR2. В регионах до +${num(n.gr3_added_region_max.pct, 1)}% (${esc(RU[n.gr3_added_region_max.region] || n.gr3_added_region_max.region)})</div></div>
      <div><div class="big">${pct(n.aktobe_share_of_food_loans_pct, 0)}</div><div class="muted">домохозяйств, занимавших на питание, — из Актобе (${pct(n.aktobe_share_of_households_pct)} всех домохозяйств). Доля займов на питание по стране ${pct(n.food_loan_pct_of_purpose)}, без Актобе ${pct(n.food_loan_pct_of_purpose_without_aktobe)}</div></div>
      <div><div class="big">${pct(mang.cov)}</div><div class="muted">домохозяйств Мангистау заполнили раздел займов (медиана регионов ${pct(rows[Math.floor(rows.length / 2)].cov, 0)}). Без ${low.length} регионов с низким охватом доля погашающих кредиты — ${pct(n.repaying_pct_without_low_coverage)} вместо ${pct(n.repaying_pct)}</div></div>
    </div>
    <div class="chart"><div style="min-width:640px">
      <div class="crow head" style="grid-template-columns:11em minmax(150px,1fr) minmax(170px,1fr) 7em"><span>Регион</span><span>Раздел займов заполнен, % домохозяйств (шкала 0–70%)</span><span>Выплаты по долгам &gt; 30% дохода, % (шкала 0–70%)</span><span>Займы на питание</span></div>
      ${rows.map(r => `<div class="crow ${r.covFlag ? 'low' : ''}" data-r="${esc(r.region)}" style="grid-template-columns:11em minmax(150px,1fr) minmax(170px,1fr) 7em">
        <span class="rn">${esc(RU[r.region])}</span>
        <div class="cov"><div class="bar"><i style="width:${B(r.cov)}%;background:var(--${r.covFlag ? 'orange' : 'blue'})"></i></div><span class="num">${pct(r.cov, 1)}</span></div>
        <div class="cov"><div class="bar"><i style="width:${B(r.burden)}%;background:var(--${r.covFlag ? 'orange' : 'blue'})"></i></div><span class="num">${pct(r.burden, 1)}</span></div>
        <span class="num"${r.food >= 30 ? ' style="color:var(--orange-ink);font-weight:600"' : ''}>${r.food == null ? '—' : pct(r.food, 0)} <span class="muted">из ${r.withPurpose}</span></span>
      </div>`).join('')}
    </div></div>
    <p class="muted" style="max-width:80ch">Оранжевым — регионы, где раздел займов заполнен меньше чем у половины медианы остальных в 3–4 годах из 4 (дело C11, сводка). Меньше займов может быть и правдой, поэтому статус — «проверить на реальных данных». В синтетике ${pct(n.kv1_repeat_rows_pct)} строк непродовольственных расходов повторяют товар (в руководстве организаторов: 15% против 2,4% в реальных данных); по регионам ${num(n.kv1_repeat_rows_region_range[0], 1)}–${num(n.kv1_repeat_rows_region_range[1], 1)}%, это ${pct(n.kv1_repeat_value_pct_of_spend)} расходов, поэтому сравнение регионов не меняется. Связи внутри домохозяйства синтез ослабляет (r = ${num(n.corr_log_income_spend_household, 2)} между логарифмами дохода и расходов), поэтому здесь только региональные доли.</p>
  </div>`;
  seg($('#fin-year'), [[2021, '2021'], [2022, '2022'], [2023, '2023'], [2024, '2024']], 'finYear', renderFin);
  el.querySelectorAll('.crow[data-r]').forEach(row => {
    const r = rows.find(x => x.region === row.dataset.r);
    row.addEventListener('mouseenter', e => showTip(e, `<b>${esc(RU[r.region])}, ${y}</b><br>Домохозяйство-кварталов: ${r.hh}<br>Раздел займов заполнен: ${pct(r.cov)}<br>Погашают кредиты: ${pct(r.repaying)}; взяли новый заём: ${pct(r.borrowed)}<br>Выплаты &gt; 30% дохода: ${pct(r.burden)}<br>Займы на питание: ${r.food == null ? '—' : pct(r.food)} из ${r.withPurpose} займов с целью<br>GR3, сложенный с GR2: +${num(r.gr3, 2)}% дохода`));
    row.addEventListener('mousemove', moveTip); row.addEventListener('mouseleave', hideTip);
  });
}

/* ---------- child tab ---------- */
function renderChild() {
  const y = state.childYear, rows = D.child.filter(c => c.year === y).sort((a, b) => a.coverage - b.coverage);
  const low = rows.filter(r => r.coverage < 50), med = [...rows].sort((a, b) => a.coverage - b.coverage)[Math.floor(rows.length / 2)].coverage;
  const big = low[0];
  const X = v => Math.max(0, Math.min(100, v / 80 * 100));
  const el = $('#p-child');
  el.innerHTML = `<div class="panel stack">
    <div class="row" style="justify-content:space-between"><h2>Детская бедность: на скольких семьях держится цифра</h2><div class="seg" id="c-year" role="group" aria-label="Год"></div></div>
    <p class="muted" style="max-width:80ch">Часть 4 анкеты Д-002 служит для оценки многоаспектной бедности детей и задаётся каждому домохозяйству с детьми до 18 лет. Показатель здесь — доля семей, которые не могут позволить себе 3 и более из 14 вещей для детей (вопрос 5, код 2). Охват — сколько семей с ребёнком по списку членов Д-008 действительно ответили.</p>
    ${big ? `<div class="callout">
      <div><div class="big">${big.answered} из ${big.withKids}</div><div class="muted">семей с детьми в регионе ${esc(RU[big.region])} ответили на детский модуль (${pct(big.coverage)}); в половине регионов — не меньше ${pct(med, 0)}</div></div>
      <div><div class="big">${pct(big.deprived)} ± ${num(big.moe)}</div><div class="muted">столько показатель даёт для ${esc(RU[big.region])}: реальное значение может быть от ${pct(Math.max(0, big.deprived - big.moe), 0)} до ${pct(big.deprived + big.moe, 0)}</div></div>
      <div><div class="big">${low.length}</div><div class="muted">${low.length === 1 ? 'регион' : 'региона'} с охватом ниже 50%: ${low.map(r => esc(RU[r.region])).join(', ')}. Причина — фильтр GR40, которого нет в бумажной анкете</div></div>
    </div>` : `<p>В ${y} году во всех регионах ответило больше половины семей с детьми.</p>`}
    <div class="chart"><div style="min-width:620px">
      <div class="crow head"><span>Регион</span><span>Охват: ответили из семей с детьми</span><span>Показатель лишений, % с 95% интервалом (шкала 0–80%)</span></div>
      ${rows.map(r => `<div class="crow ${r.coverage < 50 ? 'low' : ''}" data-r="${esc(r.region)}">
        <span class="rn">${esc(RU[r.region])}</span>
        <div class="cov"><div class="bar"><i style="width:${r.coverage}%;background:var(--${r.coverage < 50 ? 'orange' : 'blue'})"></i></div><span class="num">${pct(r.coverage, 0)} · ${r.answered}/${r.withKids}</span></div>
        <div class="est">${r.deprived == null ? '<span class="muted">нет ответов</span>' : `<div class="track" role="img" aria-label="${esc(RU[r.region])}: ${pct(r.deprived)} ± ${num(r.moe)}">
          ${[20, 40, 60].map(g => `<i class="g" style="left:${X(g)}%"></i>`).join('')}
          <i class="ci" style="left:${X(r.deprived - r.moe)}%;width:${X(r.deprived + r.moe) - X(r.deprived - r.moe)}%;background:var(--${r.coverage < 50 ? 'orange' : 'blue'})"></i>
          <i class="pt" style="left:${X(r.deprived)}%;background:var(--${r.coverage < 50 ? 'orange' : 'blue'})"></i></div>`}</div>
      </div>`).join('')}
      <div class="crow head"><span></span><span></span><div class="axis">${[0, 20, 40, 60, 80].map(v => `<span style="left:${X(v)}%">${v}${v === 80 ? '%' : ''}</span>`).join('')}</div></div>
    </div></div>
    <p class="muted" style="max-width:80ch">Ширина интервала растёт, когда ответивших мало. Кроме того, ответившие — не случайная часть: в г. Алматы (2024) у ответивших в среднем ${num(D.child.find(c => c.year === 2024 && c.region === 'Almaty city').kidsAns, 2)} ребёнка против ${num(D.child.find(c => c.year === 2024 && c.region === 'Almaty city').kidsAll, 2)} у всех семей с детьми. Синтетика сохраняет доли по регионам, поэтому охват — надёжная цифра; связь между охватом и самим показателем нужно подтвердить на реальных данных.</p>
  </div>`;
  seg($('#c-year'), [[2023, '2023'], [2024, '2024']], 'childYear', renderChild);
  el.querySelectorAll('.crow[data-r]').forEach(row => {
    const r = rows.find(x => x.region === row.dataset.r);
    row.addEventListener('mouseenter', e => showTip(e, `<b>${esc(RU[r.region])}, ${y}</b><br>Ответили ${r.answered} из ${r.withKids} семей с детьми (${pct(r.coverage)})<br>Показатель: ${pct(r.deprived)} ± ${num(r.moe)}`));
    row.addEventListener('mousemove', moveTip); row.addEventListener('mouseleave', hideTip);
  });
}

/* ---------- new form tab ---------- */
function renderNew() {
  const N = D.newForm, by = {};
  N.rules.forEach(r => { (by[r.typeRu] = by[r.typeRu] || []).push(r); });
  const order = Object.keys(by).sort((a, b) => by[b].length - by[a].length);
  const docs = N.rules.filter(r => r.type === 'doc_issue');
  $('#p-new').innerHTML = `
    <div class="panel stack"><h2>Подключение новой анкеты или нового года</h2>
      <p class="muted" style="max-width:80ch">Пример — анкета Д-002 за 2022 год, которая не использовалась при разработке инструмента. Модель получила только типовой запрос, бланк анкеты и структуру файла и сформировала по ним правила проверки; затем правила выполнены на записях 2022 года. Отдельная интеграция не требуется: запрос выполняется через API или в веб-интерфейсе Claude. В модель передаются только бланк и структура файла — микроданные остаются на компьютере Бюро.</p>
      <div class="xsteps">
        <div class="xstep"><span class="k">1 · вход</span><span class="v">Бланк 2022</span><span class="muted">анкета и структура файла, без микроданных</span></div>
        <div class="xstep"><span class="k">2 · модель</span><span class="v">${N.rules.length} правила</span><span class="muted">за ${Math.floor(N.seconds.extraction / 60)} мин ${N.seconds.extraction % 60} с, у каждого цитата</span></div>
        <div class="xstep"><span class="k">3 · движок</span><span class="v">${num(N.seconds.engine)} с</span><span class="muted">каждое правило по каждому региону</span></div>
        <div class="xstep"><span class="k">4 · результат</span><span class="v">${N.flags.length} сигнала</span><span class="muted">${N.notRun.length} — на решение специалиста, ${docs.length} противоречий в документации</span></div>
      </div></div>
    <div class="grid2">
      <div class="panel stack"><h2>Сигналы по регионам</h2>
        ${N.flags.map(f => `<article class="issue" data-status="${f.trust.startsWith('вытекает') ? 'держится' : 'проверить'}">
          <div class="row" style="justify-content:space-between"><b>${esc(RU[f.region] || f.region)}</b><span class="pill ${f.trust.startsWith('вытекает') ? 'hold' : 'check'}">${esc(f.trust)}</span></div>
          <div>${esc(f.ru)}</div>${rateRows({ region: f.region, rateRegion: f.rateRegion, rateRest: f.rateRest, status: f.trust.startsWith('вытекает') ? 'держится' : 'проверить' })}
          <span class="code muted">${esc(f.rule)}</span></article>`).join('')}
        <h3>Оставлено на решение специалиста</h3>
        ${N.notRun.map(n => `<p class="muted"><span class="code">${esc(n.rule)}</span>: ${esc(n.reason)}</p>`).join('')}
        <h3>Противоречия в документации</h3>
        ${docs.map(d => `<div class="stack" style="gap:4px"><p class="quote">«${esc(d.quote)}»</p>${d.note ? `<span class="note-en">Примечание модели (англ.): ${esc(d.note)}</span>` : ''}</div>`).join('')}
      </div>
      <div class="panel stack"><h2>Правила, сформированные моделью</h2>
        ${order.map(t => `<details ${t === order[0] ? 'open' : ''}><summary>${esc(t)} — ${by[t].length}</summary><div class="stack" style="margin-top:8px">
          ${by[t].map(r => `<div style="display:flex;flex-direction:column;gap:3px"><span>${esc(r.ru)}</span>${r.quote ? `<span class="quote">«${esc(r.quote)}»</span>` : ''}</div>`).join('')}</div></details>`).join('')}
      </div>
    </div>`;
}

/* ---------- rules tab ---------- */
function renderRules() {
  const el = $('#p-rules');
  const types = [...new Set(D.rules.map(r => r.type))];
  const TR = { domain: 'Допустимые коды', required: 'Обязательный ответ', skip: 'Переход', multi_select: 'Множественный выбор', consistency: 'Связь ответов', cross_form: 'Связь с другой формой', doc_issue: 'Документация' };
  el.innerHTML = `<div class="panel stack"><h2>Все правила из анкет</h2>
    <p class="muted">${D.rules.length} правил: ${Object.entries(D.ruleCounts).map(([f, n]) => `${esc(D.forms[f] || f)} — ${n}`).join(', ')}. Каждое прочитано моделью из бланка, инструкции или структуры файла и цитирует источник. У ${D.rules.filter(r => r.sql).length} есть SQL-запрос, который считает нарушения по регионам.</p>
    <div class="row"><input type="search" id="r-q" placeholder="Поиск: столбец, слово из анкеты…" aria-label="Поиск по правилам">
      <select id="r-form" aria-label="Форма"><option value="all">Все формы</option>${Object.keys(D.ruleCounts).map(f => `<option value="${f}">${esc(D.forms[f] || f)}</option>`).join('')}</select>
      <select id="r-type" aria-label="Вид правила"><option value="all">Все виды</option>${types.map(t => `<option value="${t}">${esc(TR[t] || t)}</option>`).join('')}</select>
      <span class="muted" id="r-n"></span></div>
    <div class="tbl"><table><thead><tr><th>Правило</th><th>Цитата из источника</th><th>Вид</th><th>Код</th></tr></thead><tbody id="r-body"></tbody></table></div></div>`;
  const draw = () => {
    const q = $('#r-q').value.trim().toLowerCase(), f = $('#r-form').value, t = $('#r-type').value;
    const rows = D.rules.filter(r => (f === 'all' || r.form === f) && (t === 'all' || r.type === t) && (!q || (r.ru + ' ' + r.quote + ' ' + r.id).toLowerCase().includes(q)));
    $('#r-n').textContent = `${rows.length} из ${D.rules.length}`;
    $('#r-body').innerHTML = rows.slice(0, 200).map(r => `<tr><td>${esc(r.ru)}${r.added ? ' <span class="pill neutral">добавлено после ревью</span>' : ''}
      ${r.sql ? `<details><summary>SQL</summary><pre class="sql">${esc(r.sql)}</pre></details>` : ''}</td>
      <td><span class="quote" style="display:block">«${esc(r.quote)}»</span><span class="muted">${esc(r.doc)}${r.conf ? ' · уверенность: ' + esc({ high: 'высокая', medium: 'средняя', low: 'низкая' }[r.conf] || r.conf) : ''}</span></td>
      <td>${esc(TR[r.type] || r.type)}</td><td class="id">${esc(r.id)}</td></tr>`).join('');
  };
  ['#r-q', '#r-form', '#r-type'].forEach(s => $(s).addEventListener('input', draw));
  draw();
}

/* ---------- trust tab ---------- */
function renderTrust() {
  const A = D.acc, order = ['skip', 'multi_select', 'required', 'domain', 'required_any', 'cross_form', 'doc_issue', 'consistency'];
  const L = { skip: 'Переходы', multi_select: 'Множественный выбор', required: 'Обязательные ответы', domain: 'Допустимые коды', required_any: 'Хотя бы одна отметка', cross_form: 'Связи с другими формами', doc_issue: 'Документация', consistency: 'Связи между ответами' };
  const B = D.blind, alm = B.t001[0], nxt = B.t001[1];
  const akt = B.aktobe;
  $('#p-trust').innerHTML = `
    <div class="panel stack"><h2>Вслепую: три случая, которые Бюро уже знает</h2>
      <p class="muted">Инструменту ничего о них не сообщали: те же обзоры и модели, что работают по всем регионам и формам.</p>
      <div class="cards3">
        <div class="xcase"><span class="verdict found">Найдено</span><h3>Алматинская обл.: работники без договора (Т-001)</h3><span>Модель «2023 против 2024» ставит регион на 1-е место из 20: AUC ${num(alm.auc, 2)}, следующий — ${esc(RU[nxt.region])} ${num(nxt.auc, 2)}.</span></div>
        <div class="xcase"><span class="verdict found">Найдено</span><h3>Актобе: займы на продукты питания (Д-004)</h3><span>Ответы о цели займа — ${akt.map(a => a.rank).join('-е и ')}-е места из ${B.d004Signals} сигналов Д-004: ${pct(akt[0].share, 0)} против ${pct(akt[0].rest)} в остальных (${akt[0].year}).</span></div>
        <div class="xcase"><span class="verdict missed">Пропущено</span><h3>Норма сбережений 66% (Д-004)</h3><span>Новое извлечение формы нашло ${B.d004DocIssues} проблем в документации, но не то, что в журнале нет раздела о продуктах. Пробел между двумя инструментами не виден внутри одной формы.</span></div>
      </div></div>
    <div class="stack">
      <div class="panel stack"><h2>Насколько точно модель выписывает правила</h2>
        <p class="muted">Извлечение по Д-002 против эталона, собранного отдельно по тем же документам (${A.ALL.reference} правил). Точность ${pct(100 * A.ALL.precision)}, полнота ${pct(100 * A.ALL.recall)}. Эталон собран вторым запуском модели и проверен командой по бланку: ${D.review.ticked} из ${D.review.rows} решений подтверждено, остальные исправлены.</p>
        ${order.map(t => `<div class="accrow"><span>${L[t]} <span class="muted">(${A[t].reference})</span></span><div class="bar" style="height:10px"><i style="width:${100 * A[t].recall}%;background:var(--blue)"></i></div><span class="num">${pct(100 * A[t].recall, 0)}</span></div>`).join('')}
        <p class="muted">Полоса — полнота: доля правил эталона, которые нашла модель. Слабое место — связи между ответами; здесь нужен человек.</p>
      </div>
      <div class="panel stack"><h2>Внесённые ошибки находятся</h2>
        <p class="muted">Ошибки внесены в записи одного региона (Д-002, 2024), ${D.proofRuns} запусков. В клетке: найдено на синтетике как есть → после исправления фоновых ошибок, которые создаёт синтез.</p>
        <div class="tbl"><table><thead><tr><th>Ошибка</th><th>Фон</th>${D.proofRates.map(r => `<th class="num">${r}%</th>`).join('')}</tr></thead><tbody>
          ${D.proof.map(p => `<tr><td>${esc(p.kind)}</td><td class="num">${pct(p.background)}</td>${p.shipped.map((a, k) => `<td class="num" style="white-space:nowrap"><span class="muted">${a}</span> → <b style="color:var(${p.repaired[k] >= 75 ? '--blue-ink' : '--fg'})">${p.repaired[k]}</b></td>`).join('')}</tr>`).join('')}
        </tbody></table></div>
        <p class="muted">Где у региона 30+ записей, к которым относится правило, и 10+ ошибок, на исправленных данных ошибка находится в ${D.proofOk['10']}% запусков начиная с 10% и в ${D.proofOk['5']}% при 5%. Новых сигналов в других регионах: ${D.proofFp} за ${D.proofRuns} запусков. Регион, получивший домохозяйства другого региона, дал новый сигнал в ${D.spec.flagged} из ${D.spec.runs} случаев: реальное различие не называется ошибкой.</p>
      </div>
    </div>`;
}


/* ---------- decoder tab ---------- */
function renderDecoder() {
  const X = D.decoder, V = X.validation;
  const ok = V.filter(v => v.grade === 'correct').length, hi = V.filter(v => v.conf === 'high'), hiok = hi.filter(v => v.grade === 'correct').length;
  const conf = { high: 'высокая', medium: 'средняя', low: 'низкая' };
  const gr = { correct: ['hold', 'верно'], partial: ['neutral', 'частично'], wrong: ['check', 'неверно'] };
  const cols = [...new Set(X.t001.map(r => r.column))];
  const kz = X.kyzylorda, al = X.almaty;
  const COLNAME = { 'D-008/STATUS': 'Д-008 · статус деятельности', 'D-008/SEM_POL': 'Д-008 · семейное положение', 'D-008/UROV': 'Д-008 · образование', 'D-006/TIP_J': 'Д-006 · тип жилья' };
  $('#p-dec').innerHTML = `
    <div class="panel stack"><h2>Декодер: что означает код, если в документации нет расшифровки</h2>
      <p class="muted" style="max-width:85ch">В архиве нет анкеты Т-001, а в Д-002 не напечатаны коды пола. Декодер строит для каждого кода «отпечаток» — с чем он связан в данных: возраст, город или село, отрасль (ОКЭД), профессия (НКЗ), часы работы и коды других вопросов. Затем две независимые проверки: сопоставление с формой, где коды расшифрованы (Д-008), и прочтение отпечатка моделью (LLM). Код считает, модель предлагает смысл, человек подтверждает.</p>
      <div class="xsteps">
        <div class="xstep"><span class="k">проверка вслепую</span><span class="v">${ok} из ${V.length}</span><span class="muted">кодов модель назвала верно, когда расшифровку спрятали (Д-008, Д-006)</span></div>
        <div class="xstep"><span class="k">высокая уверенность</span><span class="v">${hiok} из ${hi.length}</span><span class="muted">верны из тех, где модель уверена; ошибки — там, где она сама сомневалась</span></div>
        <div class="xstep"><span class="k">перенумерация</span><span class="v">${X.renumber.filter(r => r.pct >= 99.9).length} из ${X.renumber.length}</span><span class="muted">столбцов: спрятанную перестановку кодов между годами расчёт восстанавливает на 100%</span></div>
        <div class="xstep"><span class="k">сдвиги кодов</span><span class="v">${X.shiftsFlagged}</span><span class="muted">случая, где код региона ведёт себя как другой код остальной страны (из ${X.shiftsTested} проверенных пар)</span></div>
      </div></div>
    <div class="grid2">
      <div class="panel stack"><h2>Находка: Кызылорда</h2>
        <p>Детей 7–10 лет, которые учатся в 1–4 классах, по инструкции Д-008 кодируют 1 «дошкольное». В Кызылорде кодом 7 «не достигнут никакой уровень» записаны <b>${pct(kz['2023'].kyzylorda_pct_code7)}</b> таких детей в 2023 и <b>${pct(kz['2024'].kyzylorda_pct_code7)}</b> в 2024; в остальных регионах — не больше ${pct(kz['2023'].other_regions_max)} и ${pct(kz['2024'].other_regions_max)}.</p>
        <div class="rate"><span>Кызылорда, 2024</span><div class="bar"><i style="width:${kz['2024'].kyzylorda_pct_code7}%;background:var(--blue)"></i></div><span class="num">${pct(kz['2024'].kyzylorda_pct_code7)}</span>
          <span>Медиана регионов</span><div class="bar"><i style="width:${Math.max(1.5, kz['2024'].other_regions_median)}%;background:var(--fg-3)"></i></div><span class="num">${pct(kz['2024'].other_regions_median)}</span></div>
        <p class="muted">Декодер нашёл это сам: коды 1 и 7 в Кызылорде ведут себя как 7 и 1 в остальной стране, оба года. Доли по региону переживают синтез, поэтому находка держится; подтвердить на реальных данных.</p>
      </div>
      <div class="panel stack"><h2>Находка: код работодателя 5 в 2024 году</h2>
        <p>Наёмных работников у физических лиц в Алматинской области в 2023 записывали с типом работодателя 2 (${al['2023'].status2_code2} записей), в 2024 — только с кодом 5 (${al['2024'].status2_code5}). В тот же год устный договор у них — <b>${pct(al['2024'].no_contract_status2_almaty_pct)}</b> против ${pct(al['2024'].no_contract_status2_rest_pct)} в остальных.</p>
        <p>Вне области код 5 тоже изменился: устный договор у ${pct(al['2023'].oral_among_code5_outside_almaty_pct)} его записей в 2023 и у <b>${pct(al['2024'].oral_among_code5_outside_almaty_pct)}</b> в 2024. По профилю коды 2 и 5 почти неотличимы, то есть это те же работники.</p>
        <p class="muted">Вопрос к Бюро: переопределили ли код 5 в инструкции Т-001 за 2024 год? Если да, рост неформальной занятости в Алматинской области — эффект кодирования. Урок для декодера: отпечаток кода 5 за 2024 год построен в основном на одной области, поэтому его смысл помечен как зависящий от года.</p>
      </div>
    </div>
    <div class="panel stack"><h2>Расшифровка кодов Т-001</h2>
      <p class="muted">Предложение модели по отпечаткам 2024 года, без анкеты. «Д-008» — что даёт независимое сопоставление с расшифрованной формой по возрасту и типу поселения. Это гипотезы до сверки с анкетой Т-001.</p>
      ${cols.map(c => { const rows = X.t001.filter(r => r.column === c); return `<details ${c === 'ORB_STATUS' ? 'open' : ''}><summary><span class="code">${esc(c)}</span> — ${esc(rows[0].concept)} (${rows.length} кодов)</summary>
        <div class="tbl"><table><thead><tr><th>Код</th><th>Смысл (модель)</th><th>Уверенность</th><th>Д-008</th><th>По каким признакам</th></tr></thead><tbody>
        ${rows.map(r => `<tr><td class="id">${esc(r.code)}</td><td>${esc(r.meaning)}${c === 'ORB_PKHDHL' && r.code === '5' ? ' <span class="pill neutral">смысл менялся в 2024</span>' : ''}</td><td><span class="pill ${r.conf === 'high' ? 'hold' : r.conf === 'low' ? 'check' : 'neutral'}">${conf[r.conf] || r.conf}</span></td>
          <td>${r.sister ? esc(r.sister) + (r.sisterMargin != null ? `<br><span class="muted">запас ${num(r.sisterMargin, 3)}</span>` : '') : '<span class="muted">—</span>'}</td><td class="muted">${esc(r.evidence)}</td></tr>`).join('')}
        </tbody></table></div></details>`; }).join('')}
    </div>
    <div class="panel stack"><h2>Проверка вслепую: модель против документации</h2>
      <p class="muted">Те же отпечатки для столбцов, у которых расшифровка есть, но модели её не показали. Оценка: «верно» — та же категория, «частично» — соседняя.</p>
      <div class="tbl"><table><thead><tr><th>Столбец</th><th>Код</th><th>Модель</th><th>Документация</th><th>Уверенность</th><th>Оценка</th></tr></thead><tbody>
        ${V.map(v => `<tr><td>${esc(COLNAME[v.column] || v.column)}</td><td class="id">${esc(v.code)}</td><td>${esc(v.model)}</td><td>${esc(v.truth)}</td><td>${conf[v.conf] || v.conf}</td><td><span class="pill ${gr[v.grade][0]}">${gr[v.grade][1]}</span></td></tr>`).join('')}
      </tbody></table></div></div>`;
}


/* ---------- data tab ---------- */
function renderData() {
  const S = D.schema, el = $('#p-data');
  if (!S) { el.innerHTML = '<div class="panel muted">Модель данных не собрана: запустите schema/profile.py и schema/draw.py.</div>'; return; }
  const GR = { 'person': 'человек', 'household': 'домохозяйство', 'household x quarter': 'домохозяйство × квартал',
    'household x quarter x item': 'домохозяйство × квартал × строка', 'person (respondent)': 'респондент' };
  const KIND = { code: 'код', integer: 'целое', number: 'число', text: 'текст', empty: 'пусто' };
  const LINK = { 'D002.subject -> D008.kontr_k': 'Д-002 → Д-008 (домохозяйство)', 'D002.subject respondent -> D008.kontr_k person': 'Д-002 респондент → Д-008 человек',
    'D006.rio -> D008.kontr_k': 'Д-006 → Д-008', 'D004.kv_vopr0 -> D008.kontr_k': 'Д-004 визит → Д-008',
    'D002.subject <-> D002.ocenka': 'Д-002 subject ↔ ocenka', 'D004.kv_vopr1 -> D004.kv_vopr0': 'Д-004 строки (kv_vopr1) → визит',
    'D004.kv_vopr12 -> D004.kv_vopr0': 'Д-004 строки (kv_vopr12) → визит',
    "D002.ocenka GR40 'has children' vs D008 member under 18": 'GR40 «есть дети» при ребёнке в Д-008 / без него',
    "D002.ocenka GR31_1 'rent: not relevant' vs D006 owner (VLAD1 1-2)": 'GR31_1 «не актуально» у собственника / не собственника' };
  const years = [...new Set(S.household.map(r => r.year))].sort();
  const t = S.tables, big = n => n.toLocaleString('ru-RU');
  const tabs = [...new Set(S.columns.map(c => c.f + '.' + c.t))];
  el.innerHTML = `
  <div class="panel stack">
    <figure class="dg"><div class="dgscroll">${S.svg.links_ru_inline || ''}</div>
      <figcaption>Номер домохозяйства NOMER один и тот же в Д-002, Д-004, Д-006 и Д-008: каждая запись находит своё домохозяйство в контрольной карточке Д-008, регион и тип местности совпадают. Т-001 номера не имеет. Связь Д-002 ↔ Д-008 сохранилась в синтетических данных по каждому домохозяйству, связь Д-002 ↔ Д-006 — нет (ответы независимы), поэтому там сравниваются только доли по регионам.</figcaption></figure></div>
  <div class="panel stack"><h2>Проверка по каждому домохозяйству: фильтр детского модуля</h2>
    <p class="muted">Д-002 GR40 («есть дети до 18 лет») против членов домохозяйства моложе 18 лет в Д-008, по номеру NOMER. Это правила D002-x-D008-child-household и D002-x-D008-nochild-household: они проходят тот же тест «регион против остальной страны», что и все правила, и отмеченные регионы попадают в сводку и в дело C1. Таблица показывает все регионы, а не только отмеченные.</p>
    <div class="row"><div class="seg" id="hc-year" role="group" aria-label="Год"></div></div>
    <div class="tbl"><table><thead><tr><th>Регион</th><th class="num">С ребёнком в Д-008</th><th class="num">из них «нет детей» в Д-002</th><th class="num">%</th><th class="num">Без детей в Д-008: «есть дети»</th></tr></thead><tbody id="hc-body"></tbody></table></div></div>
  <div class="panel stack">
    <figure class="dg"><div class="dgscroll">${S.svg.pipeline_ru_inline || ''}</div>
      <figcaption>Языковая модель работает только на первом шаге: читает анкету и пишет правила с цитатой источника. Дальше всё считает код по записям; ML-сравнения и декодер находят то, для чего правила не написаны.</figcaption></figure></div>
  <div class="panel stack"><h2>Таблицы</h2>
    <p class="muted">Последний год выпуска. «Найдено в Д-008» — доля домохозяйств таблицы, которые есть в контрольной карточке того же года.</p>
    <div class="tbl"><table><thead><tr><th>Таблица</th><th>Одна запись</th><th>Ключ</th><th class="num">Записей</th><th class="num">Столбцов (выпуск / реальные)</th><th>Ключ уникален</th><th class="num">Найдено в Д-008</th></tr></thead><tbody>
    ${t.map(r => `<tr><td class="id">${esc(r.form)}.${esc(r.table)}</td><td>${esc(GR[r.grain] || r.grain)}</td><td class="code">${esc(r.key === 'none' ? 'нет' : r.key)}</td>
      <td class="num">${big(r.rows)}</td><td class="num">${r.cols} / ${r.colsReal}</td><td>${r.unique == null ? '—' : r.unique ? 'да' : 'нет'}</td><td class="num">${r.inRoster == null ? '—' : pct(r.inRoster, 0)}</td></tr>`).join('')}
    </tbody></table></div></div>
  <div class="panel stack"><h2>Связи по годам</h2>
    <div class="tbl"><table><thead><tr><th>Связь</th><th>Ключ</th>${years.length ? '' : ''}${[2021, 2022, 2023, 2024].map(y => `<th class="num">${y}</th>`).join('')}</tr></thead><tbody>
    ${[...new Set(S.links.map(l => l.link))].map(name => {
      const cell = y => { const l = S.links.find(x => x.link === name && x.year === y); if (!l) return '—';
        if (l.share_if_condition_pct != null) return `${num(l.share_if_condition_pct)} / ${num(l.share_if_not_condition_pct)}`;
        if (l.respondent_differs != null) return `найдено ${pct(l.found_pct, 0)}; другой человек: ${l.respondent_differs}`;
        return `найдено ${pct(l.found_pct, 0)}` + (l.region_agrees_pct != null ? `, регион ${pct(l.region_agrees_pct, 0)}` : '') + (l.sex_agrees_pct != null ? `, пол ${pct(l.sex_agrees_pct, 0)}` : ''); };
      const k = S.links.find(x => x.link === name).key;
      return `<tr><td>${esc(LINK[name] || name)}</td><td class="code">${esc(k)}</td>${[2021, 2022, 2023, 2024].map(y => `<td class="num">${cell(y)}</td>`).join('')}</tr>`; }).join('')}
    </tbody></table></div>
    <p class="muted">Две последние строки — доля ответа при условии и без него (в %): 86 против 7 — ответы связаны; 50 против 52 — не связаны.</p></div>
  <div class="panel stack"><h2>Словарь столбцов</h2>
    <p class="muted">${S.columns.length} столбцов. Описание — из файла структуры Бюро, где он его даёт; вид, заполненность и частые значения посчитаны по последнему году; «правила» — какие правила проверяют столбец.</p>
    <div class="row"><input type="search" id="c-q" placeholder="Поиск: столбец, описание, правило…" aria-label="Поиск по столбцам">
      <select id="c-t" aria-label="Таблица"><option value="all">Все таблицы</option>${tabs.map(x => `<option>${esc(x)}</option>`).join('')}</select>
      <span class="muted" id="c-n"></span></div>
    <div class="tbl" style="max-height:70vh"><table><thead><tr><th>Столбец</th><th>Описание</th><th>Вид</th><th class="num">Заполнено</th><th>Частые значения</th><th>Правила</th></tr></thead><tbody id="c-body"></tbody></table></div></div>
  <div class="panel stack"><h2>Для технических специалистов</h2>
    <details><summary>Все таблицы с ключами (схема)</summary><div class="erd">${S.svg.erd_data || ''}</div></details>
    <details><summary>Все выходные файлы и как они соединяются</summary><div class="erd">${S.svg.erd_outputs || ''}</div></details>
    <p class="muted">То же в пакете: diagrams/, out/schema_*.csv и DATA_MODEL.md.</p></div>`;
  state.hcYear = years.includes(state.hcYear) ? state.hcYear : years[years.length - 1];
  const drawHc = () => {
    const rows = S.household.filter(r => r.year === state.hcYear).sort((a, b) => b.missed_pct - a.missed_pct);
    $('#hc-body').innerHTML = rows.map(r => `<tr><td${r.missed_pct >= 20 ? ' style="color:var(--orange-ink);font-weight:600"' : ''}>${esc(RU[r.region] || r.region)}</td>
      <td class="num">${r.with_child_in_roster}</td><td class="num">${r.coded_no_children}</td><td class="num">${pct(r.missed_pct)}</td><td class="num"${r.false_yes_pct >= 20 ? ' style="color:var(--orange-ink);font-weight:600"' : ''}>${pct(r.false_yes_pct)}</td></tr>`).join('');
  };
  seg($('#hc-year'), years.map(y => [y, y]), 'hcYear', drawHc); drawHc();
  const drawCols = () => {
    const q = $('#c-q').value.trim().toLowerCase(), tt = $('#c-t').value;
    const rows = S.columns.filter(c => (tt === 'all' || c.f + '.' + c.t === tt) && (!q || (c.c + ' ' + c.d + ' ' + c.r).toLowerCase().includes(q)));
    $('#c-n').textContent = `${rows.length} из ${S.columns.length}` + (rows.length > 300 ? ' (показаны первые 300)' : '');
    $('#c-body').innerHTML = rows.slice(0, 300).map(c => `<tr><td class="id">${esc(c.f)}.${esc(c.t)}.<b>${esc(c.c)}</b></td><td>${esc(c.d)}</td><td>${esc(KIND[c.k] || c.k || '')}</td>
      <td class="num">${c.fp == null ? '—' : pct(c.fp, 0)}</td><td class="code">${esc((c.top || '').split('; ').slice(0, 4).join(' · '))}</td>
      <td class="id" style="white-space:normal">${esc((c.r || '').split('; ').slice(0, 3).join(', '))}${(c.r || '').split('; ').length > 3 ? ' …' : ''}</td></tr>`).join('');
  };
  ['#c-q', '#c-t'].forEach(s => $(s).addEventListener('input', drawCols)); drawCols();
}
return { renderChild, renderFin, renderNew, renderDecoder, renderRules, renderTrust, renderData, rateRows, esc, pct };
})(/*CONSOLE*/null);
