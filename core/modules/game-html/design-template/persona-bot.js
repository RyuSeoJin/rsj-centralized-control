// {게임 이름} 숙련도별 플레이 봇 — 프로토타입 {버전} 기준 ({YYYY-MM-DD})
// 규칙: core/modules/game-html/rules/playtest-bots.md
// 쓰는 법: 프로토타입을 브라우저로 열고 콘솔에 이 파일을 붙여 넣은 뒤
//   const players = __panel();                 // 섞은 10명 (보고용 한 판 묶음)
//   const avg = __perPersona(10);              // 페르소나마다 10판 평균
// 저장을 덮어쓰므로 시험용 브라우저에서만 돌립니다.

// 1. 페르소나 — 판단 매개변수 묶음 (§1). 숫자는 게임마다 정하고 보고서에 표로 남긴다
window.PERSONAS = {
  novice:  { name: '미숙',    know: 0.3, mistake: 0.3,  risk: 1.4, plan: 0, reserve: 0 },
  casual:  { name: '조금 앎', know: 0.6, mistake: 0.15, risk: 1.1, plan: 0, reserve: 2 },
  skilled: { name: '익숙',    know: 0.9, mistake: 0.05, risk: 1.0, plan: 1, reserve: 4 },
  optimal: { name: '최적',    know: 1,   mistake: 0,    risk: 'ev', plan: 2, reserve: 4 },
};
window.PANEL = ['novice', 'novice', 'novice', 'casual', 'casual', 'casual', 'skilled', 'skilled', 'optimal', 'optimal'];   // 섞은 10명 (§3)

// 판단 도우미 — 같은 판단 함수가 페르소나를 읽어 다르게 고른다
window.__knows = P => Math.random() < P.know;                                    // 이번 턴에 이 시스템을 떠올리나
window.__choose = (P, list, score) => {                                           // 점수가 가장 높은 것 — 실수하면 무작위
  if (!list.length) return null;
  if (Math.random() < P.mistake) return list[Math.floor(Math.random() * list.length)];
  return list.slice().sort((a, b) => score(b) - score(a))[0];
};

// 2. 지표 기록 (§2) — 결과 · 경로(턴마다) · 행동 횟수 · 선택의 질 · 큰 일정
window.__newMetrics = (id, persona) => ({ id, persona, end: null, path: [], acts: {}, picks: [], big: [] });
window.__act = (m, k, n = 1) => { m.acts[k] = (m.acts[k] || 0) + n; };

// 3. 한 턴의 판단 — 게임마다 채운다. 게임의 공개 함수만 부른다 (§4)
window.__turn = (P, m) => {
  // 예) if (__knows(P)) { 제작할 것을 __choose(P, 후보, 점수)로 골라 공개 함수로 시작; __act(m, 'craft'); }
  // 예) 도전 고르기 — P.risk === 'ev' 이면 (이길 확률 × 보상)이 가장 큰 것, 아니면 (상대 / 나) ≤ P.risk 인 것 가운데 보상이 큰 것
  //     m.picks.push({ ratio: 상대 / 나, win: 결과 });
  // 예) 큰 일정 몇 주 전(P.plan)부터 쉬기 · 비축
};

// 4. 한 판 — 새 게임부터 끝(패배 · 목표 · 상한)까지
window.__play = (id, personaKey, maxTurn = 90) => {
  const P = PERSONAS[personaKey], m = __newMetrics(id, P.name);
  const keep = { render: window.render, toast: window.toast };              // 그리기 · 알림은 잠시 끔
  window.render = () => {}; window.toast = () => {};
  try {
    newGame();
    for (let t = 0; t < maxTurn && !isOver(); t++) {
      __turn(P, m);
      m.path.push(snapshot());                                               // 게임마다 snapshot()을 정한다 — { turn, power, money, people, … }
      endTurn();                                                             // 게임의 턴 넘기기 공개 함수
    }
  } catch (e) { m.error = String(e && e.stack || e).slice(0, 300); }
  m.end = outcome();                                                         // 게임마다 outcome()을 정한다 — { turn, reason, cleared }
  window.render = keep.render; window.toast = keep.toast;
  return m;
};

// 5. 묶음 · 요약
window.__panel = (maxTurn) => PANEL.map((k, i) => __play(i + 1, k, maxTurn));
window.__perPersona = (n = 10, maxTurn) => Object.fromEntries(Object.keys(PERSONAS).map(k => {
  const runs = Array.from({ length: n }, (_, i) => __play(i + 1, k, maxTurn));
  return [PERSONAS[k].name, __summary(runs)];
}));
window.__summary = runs => {
  const avg = f => Math.round(runs.reduce((a, r) => a + (f(r) || 0), 0) / runs.length * 10) / 10;
  const keys = [...new Set(runs.flatMap(r => Object.keys(r.acts)))];
  return { n: runs.length, endTurn: avg(r => r.end?.turn), cleared: avg(r => r.end?.cleared),
    acts: Object.fromEntries(keys.map(k => [k, avg(r => r.acts[k])])),
    pickRatio: avg(r => r.picks.length ? r.picks.reduce((a, p) => a + p.ratio, 0) / r.picks.length : 0),
    pickWin: avg(r => r.picks.length ? r.picks.filter(p => p.win).length / r.picks.length * 100 : 0),
    errors: runs.filter(r => r.error).length };
};
'persona bot ready';
