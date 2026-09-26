/* Generic app preview runtime. Project data stays outside this module. */
(function (global) {
  'use strict';
  const css = `.ap-toolbar,.ap-controls{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:12px}.ap-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:16px}.ap-card{min-width:0;padding:16px;border:1px solid var(--ap-border,#cbd5e1);border-radius:12px;background:var(--ap-bg,#fff);color:var(--ap-ink,#172033)}.ap-card h3{margin:0 0 12px}.ap-root button,.ap-root select,.ap-root input{font:inherit;color:inherit;background:var(--ap-bg,#fff);border:1px solid var(--ap-border,#cbd5e1);border-radius:6px;padding:6px;max-width:100%}.ap-root input[type=number]{width:80px}.ap-root input[type=checkbox]{width:auto}.ap-root button{cursor:pointer}.ap-root button:disabled{opacity:.5;cursor:default}.ap-viewport{overflow:auto;max-height:680px;background:transparent;border-radius:8px}.ap-size{position:relative;margin:auto;outline:1px solid var(--ap-border,#cbd5e1)}.ap-frame{position:absolute;left:0;top:0;border:0;transform-origin:top left;background:white}.ap-meta,.ap-note{font-size:13px;line-height:1.6}.ap-root :focus-visible{outline:2px solid #6366f1;outline-offset:2px}[data-theme=dark] .ap-root{--ap-bg:#1c222c;--ap-ink:#e5eaf3;--ap-border:#465266;--ap-well:#111820}.ap-root{color:var(--ap-ink,#172033)}`;
  function validate(screens, presets, flow) {
    if (!Array.isArray(screens) || !Array.isArray(presets)) throw Error('screens·presets는 배열이어야 합니다');
    const ids = new Set();
    screens.forEach(s => {
      if (!s || typeof s.id !== 'string' || !s.id || ids.has(s.id) || typeof s.title !== 'string') throw Error('화면 ID·제목을 확인해주세요');
      if ((typeof s.image === 'string') === (typeof s.html === 'string')) throw Error('화면에는 image 또는 html 하나가 필요합니다');
      ids.add(s.id);
    });
    screens.forEach(s => (s.actions || []).forEach(a => {
      if (!ids.has(a.target) || typeof a.label !== 'string') throw Error('없는 화면 연결 또는 동작 이름');
      if (s.image && (!['x','y','width','height'].every(k => Number.isFinite(a[k]) && a[k] >= 0 && a[k] <= 100) || a.width <= 0 || a.height <= 0 || a.x+a.width > 100 || a.y+a.height > 100)) throw Error('잘못된 선택 영역');
    }));
    screens.filter(s => typeof s.html === 'string').forEach(s => {
      const doc = new DOMParser().parseFromString(s.html, 'text/html');
      doc.querySelectorAll('[data-preview-target]').forEach(el => {
        if (!ids.has(el.dataset.previewTarget)) throw Error('HTML의 없는 화면 연결');
      });
      const fields = new Set();
      doc.querySelectorAll('[data-preview-field]').forEach(el => {
        if (!el.dataset.previewField || fields.has(el.dataset.previewField)) throw Error('중복되거나 빈 입력 ID');
        fields.add(el.dataset.previewField);
      });
    });
    const names = new Set();
    presets.forEach(p => {
      if (!p.id || names.has(p.id) || !p.label || !size(p.width) || !size(p.height)) throw Error('잘못된 프리셋');
      names.add(p.id);
    });
    if (flow) {
      const fields=flow.defaults;
      if (!fields || Object.values(fields).some(v=>typeof v!=='boolean') || !Array.isArray(flow.entry) || !Array.isArray(flow.edges)) throw Error('잘못된 상태 흐름');
      const records=flow.records||{};
      const scalar=v=>typeof v==='boolean'||typeof v==='string'||(typeof v==='number'&&Number.isFinite(v));
      if(!records||Array.isArray(records)||typeof records!=='object'||Object.entries(records).some(([k,v])=>Object.hasOwn(fields,k)||!scalar(v)))throw Error('잘못된 사용자 기록');
      const conditions={...fields,...records};
      const checkValues=(values,defaults)=>{if(values && (typeof values!=='object'||Array.isArray(values)||Object.entries(values).some(([k,v])=>!Object.hasOwn(defaults,k)||typeof v!==typeof defaults[k]||!scalar(v))))throw Error('없는 상태 조건 또는 잘못된 값');};
      const checkWhen=when=>checkValues(when,conditions);
      const arrivals=flow.onEnter||[];
      if(!Array.isArray(arrivals))throw Error('잘못된 화면 진입 규칙');
      arrivals.forEach(e=>{if(!ids.has(e.from)||!ids.has(e.target))throw Error('없는 화면 진입 대상');checkWhen(e.when);});
      const visit=(id,trail)=>{if(trail.has(id))throw Error('화면 진입 규칙 순환');const next=new Set(trail);next.add(id);arrivals.filter(e=>e.from===id).forEach(e=>visit(e.target,next));};
      ids.forEach(id=>visit(id,new Set()));
      if (!flow.entry.length || Object.keys(flow.entry.at(-1).when||{}).length) throw Error('진입 기본 분기가 필요합니다');
      flow.entry.forEach(e=>{if(!ids.has(e.target))throw Error('없는 진입 화면');checkWhen(e.when);});
      const edgeIds=new Set();
      flow.edges.forEach(e=>{
        if(!e.id || edgeIds.has(e.id) || !ids.has(e.from) || !ids.has(e.target) || typeof e.event!=='string')throw Error('잘못된 전환');
        edgeIds.add(e.id);checkWhen(e.when);checkValues(e.set,fields);checkValues(e.recordSet,records);
        if(e.request && ['success','failure','timeout'].some(k=>!ids.has(e.request[k])))throw Error('없는 요청 결과 화면');
      });
    }
  }
  function size(n) { return Number.isInteger(n) && n >= 100 && n <= 10000; }
  function esc(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function mount(root, config) {
    if (!root || root.dataset.appPreviewReady) return;
    const screens = config.screens || [], presets = config.presets || [];
    const flow=config.flow;
    validate(screens, presets, flow);
    const byId = new Map(screens.map(s => [s.id,s]));
    const first = (screens.find(s => s.start) || screens[0] || {}).id;
    const base = new URL(config.assetBase || './', document.baseURI).href;
    const choices = presets.length ? presets : [{id:'virtual',label:'임시 가상 크기 · 미확정',width:390,height:844}];
    if(config.defaultPreset && !choices.some(p=>p.id===config.defaultPreset))throw Error('없는 기본 프리셋');
    const defaultPreset=choices.find(p=>p.id===config.defaultPreset)||choices[0];
    const matches=(when,fields)=>Object.entries(when||{}).every(([k,v])=>fields[k]===v);
    const manualStart=config.manualStart===true;
    const recordDefaults=flow?.records||{};
    function enter(id,state){
      const values={...state.fields,...state.records};
      const visited=new Set();
      while(id){if(visited.has(id))throw Error('화면 진입 규칙 순환');visited.add(id);
        const rule=(flow?.onEnter||[]).find(e=>e.from===id&&matches(e.when,values));
        if(!rule)break;id=rule.target;
      }
      return id;
    }
    const fresh=(fields,started=!manualStart,records=recordDefaults)=>{
      const state={id:null,history:[],fields:JSON.parse(JSON.stringify(fields||flow?.defaults||{})),records:JSON.parse(JSON.stringify(records)),pending:false,trace:[]};
      if(started)state.id=enter(flow?flow.entry.find(e=>matches(e.when,{...state.fields,...state.records})).target:first,state);
      return state;
    };
    function cancel(c){clearTimeout(c.timer);c.serial=(c.serial||0)+1;if(c.state.pending){c.state.id=c.origin;c.state.pending=false;}}
    function reset(c,fields,started=!manualStart){
      cancel(c);
      const savedFields=Object.fromEntries(Object.keys(flow?.defaults||{}).map(k=>[k,c.state.fields[k]]));
      c.state=fresh(fields||savedFields,started,c.state.records);publish(c);
    }
    root.dataset.appPreviewReady = 'true'; root.classList.add('ap-root'); root.replaceChildren();
    const style = document.createElement('style'); style.textContent = css; root.append(style);
    style.textContent += '.ap-debug{margin:12px 0;padding:12px;border:1px solid var(--ap-border,#cbd5e1);border-radius:8px}.ap-debug summary{cursor:pointer;margin-bottom:8px}.ap-debug>label{display:inline-flex;align-items:center;gap:6px;margin:6px 10px 6px 0;max-width:100%;flex-wrap:wrap}.ap-debug>button{margin:6px 0}.ap-debug pre{padding:12px;background:var(--ap-well,#eef2f6);border-radius:6px}';
    style.textContent += '.ap-control-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px;width:100%}.ap-stage{display:grid;grid-template-columns:minmax(0,1fr) 150px;gap:16px}.ap-shortcuts button{display:block;width:100%;margin:6px 0;text-align:left}.ap-shortcuts button[aria-current=true]{font-weight:bold;border:2px solid #6366f1}.ap-shortcuts summary{cursor:pointer}.ap-root [hidden]{display:none!important}@media(max-width:700px){.ap-stage{grid-template-columns:minmax(0,1fr)}.ap-shortcuts{grid-row:1}}';
    const toolbar = document.createElement('div'); toolbar.className='ap-toolbar'; root.append(toolbar);
    function button(parent, text, fn) { const b=document.createElement('button'); b.type='button'; b.textContent=text; b.onclick=fn; parent.append(b); return b; }
    const add = button(toolbar,'디바이스 화면 추가',()=>create());
    button(toolbar,'전체 초기화',()=>cards.forEach(c=>{cancel(c);c.state=fresh();render(c);}));
    const label=document.createElement('label'), sync=document.createElement('input'); sync.type='checkbox'; sync.checked=true;
    label.append(sync,document.createTextNode(' 화면·입력 동기화')); toolbar.append(label);
    const note=document.createElement('p'); note.className='ap-note'; note.textContent='가상 뷰포트 비교 · 실제 OS 에뮬레이션이 아닙니다. 이미지 모드는 반응형 UI 검증을 대신하지 않습니다.'; root.append(note);
    const grid=document.createElement('div'); grid.className='ap-grid'; root.append(grid);
    const cards=[]; let serial=0;
    const copy = s => JSON.parse(JSON.stringify(s));
    sync.onchange=()=>{cards.forEach(c=>{cancel(c);render(c);});if(sync.checked && cards.length) cards.slice(1).forEach(c=>{c.state=copy(cards[0].state);render(c);});};
    function publish(c, redraw=true) {
      if(redraw) render(c);
      else if(c.trace)c.trace.textContent=JSON.stringify({screen:c.state.id,state:c.state.fields,records:c.state.records,pending:c.state.pending,events:c.state.trace},null,2);
      if(sync.checked) cards.filter(x=>x!==c).forEach(x=>{cancel(x);x.origin=c.origin;x.state=copy(c.state);if(redraw)render(x);else applyFields(x);});
    }
    function go(c,id) { if(!byId.has(id)||c.state.pending) return; if(c.state.id)c.state.history.push(c.state.id); c.state.id=enter(id,c.state);publish(c); }
    function dispatch(c,event){
      if(!flow||c.state.pending)return;
      const e=flow.edges.find(e=>e.from===c.state.id && e.event===event && matches(e.when,{...c.state.fields,...c.state.records}));
      if(!e)return;
      c.state.trace.push(c.state.id+' → '+e.id+' ['+event+'] → '+e.target);c.state.trace=c.state.trace.slice(-30);
      Object.assign(c.state.fields,e.set||{});c.state.history.push(c.state.id);c.origin=c.state.id;c.state.id=e.target;
      if(!e.request){Object.assign(c.state.records,e.recordSet||{});c.state.id=enter(c.state.id,c.state);publish(c);return;}
      c.state.id=enter(c.state.id,c.state);c.state.pending=true;
      const result=c.outcome.value,delay=Math.min(5000,Math.max(0,Number(c.delay.value)||0));
      c.outcome.value='success';const ticket=++c.serial;publish(c);
      c.timer=setTimeout(()=>{if(c.removed||ticket!==c.serial)return;c.state.pending=false;if(result==='success')Object.assign(c.state.records,e.recordSet||{});c.state.id=enter(e.request[result],c.state);c.state.trace.push('요청 '+result+' → '+c.state.id);publish(c);},delay);
    }
    function applyFields(c) {
      const doc=c.frame.contentDocument; if(!doc) return;
      doc.querySelectorAll('[data-preview-field]').forEach(el=>{
        const value=c.state.fields[el.dataset.previewField]; if(value===undefined)return;
        if(el.type==='checkbox')el.checked=!!value;else el.value=value;
      });
      doc.querySelectorAll('[data-preview-requires]').forEach(el=>{el.disabled=c.state.pending||!c.state.fields[el.dataset.previewRequires];});
    }
    function fit(c) {
      const w=c.width,h=c.height, available=c.viewport.clientWidth;
      const scale=c.zoomScale !== null ? c.zoomScale : Math.min(1,Math.max(100,available)/w,600/h);
      c.frame.style.width=w+'px';c.frame.style.height=h+'px';c.frame.style.transform='scale('+scale+')';
      c.spacer.style.width=(w*scale)+'px';c.spacer.style.height=(h*scale)+'px';
      const gcd=(a,b)=>b?gcd(b,a%b):a,d=gcd(w,h);
      if(c.zoomInput)c.zoomInput.value=Math.round(scale*100);
      c.meta.textContent=w+' × '+h+' CSS px · 비율 '+w/d+':'+h/d+' · 표시 '+Math.round(scale*100)+'%';
    }
    function render(c) {
      const s=byId.get(c.state.id); c.screen.value=c.state.id || ''; c.back.disabled=c.state.pending||!c.state.history.length;c.screen.disabled=c.state.pending||!screens.length;
      if(c.launch)c.launch.hidden=!!s;
      if(c.debug)c.debug.hidden=!s;
      if(c.requestSettings)c.requestSettings.hidden=!s||c.state.pending||!flow.edges.some(e=>e.from===c.state.id&&e.request);
      if(c.shortcuts) c.shortcuts.querySelectorAll('button').forEach(b=>{b.disabled=c.state.pending;b.setAttribute('aria-current',String(b.dataset.screen===c.state.id));});

      if(c.start)c.start.disabled=!!s||!screens.length;
      if(manualStart&&!s&&c.inputs)Object.entries(c.inputs).forEach(([k,input])=>{input.checked=!!c.state.fields[k];});
      if(c.trace)c.trace.textContent=JSON.stringify({screen:c.state.id,state:c.state.fields,records:c.state.records,pending:c.state.pending,events:c.state.trace},null,2);
      const body=s ? (s.html !== undefined ? s.html : '<div class="image"><img alt="'+esc(s.alt||s.title)+'" src="'+esc(new URL(s.image,base).href)+'">'+(s.actions||[]).map(a=>'<button data-preview-target="'+esc(a.target)+'" aria-label="'+esc(a.label)+'" style="left:'+a.x+'%;top:'+a.y+'%;width:'+a.width+'%;height:'+a.height+'%"></button>').join('')+'</div>') : (manualStart&&screens.length?'<div style="min-height:100vh;display:grid;place-content:center;text-align:center;background:#f3f5fa;color:#526079;padding:24px;box-sizing:border-box"><h2 style="font-size:20px">앱 시작 대기</h2><p>초기 상태를 선택한 뒤<br>앱 시작을 눌러주세요.</p></div>':'<p>등록된 화면이 없습니다.</p>');
      c.frame.onload=()=>{
        const doc=c.frame.contentDocument; if(!doc)return;
        applyFields(c);
        doc.addEventListener('click',e=>{const event=e.target.closest('[data-preview-event]');if(event){e.preventDefault();if(!event.disabled)dispatch(c,event.dataset.previewEvent);return;}const target=e.target.closest('[data-preview-target]'); if(target){e.preventDefault();go(c,target.dataset.previewTarget);}else if(e.target.closest('a'))e.preventDefault();});
        doc.addEventListener('submit',e=>e.preventDefault());
        const update=e=>{const el=e.target;if(!el.dataset.previewField||c.state.pending)return;c.state.fields[el.dataset.previewField]=el.type==='checkbox'?el.checked:el.value;applyFields(c);publish(c,false);};
        doc.addEventListener('input',update);doc.addEventListener('change',update);
      };
      c.frame.srcdoc='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><base href="'+esc(base)+'"><style>body{margin:0;font:16px system-ui;color:#172033;background:#fff}body>p{padding:24px}.image{position:relative;width:100%}.image img{display:block;width:100%;height:auto}.image button{position:absolute;border:2px dashed #6366f1;background:transparent;cursor:pointer}</style></head><body>'+body+'</body></html>';
      fit(c);
    }
    function create() {
      const c={width:defaultPreset.width,height:defaultPreset.height,serial:0,zoomScale:null,state:sync.checked && cards.length?copy(cards[0].state):fresh(),origin:cards[0]?.origin};
      cards.push(c); const card=document.createElement('section');card.className='ap-card';grid.append(card);c.card=card;
      const title=document.createElement('h3');title.textContent='디바이스 '+(++serial);card.append(title);
      const controls=document.createElement('div');controls.className='ap-controls';card.append(controls);
      function row(label){const el=document.createElement('div');el.className='ap-control-row';el.setAttribute('role','group');el.setAttribute('aria-label',label);controls.append(el);return el;}
      const deviceRow=row('디바이스 선택'),sizeRow=row('크기와 보기'),appRow=row('앱 조작');

      function select(name,items){const el=document.createElement('select');el.setAttribute('aria-label',name);items.forEach(([value,text])=>{const o=document.createElement('option');o.value=value;o.textContent=text;el.append(o);});controls.append(el);return el;}
      const preset=select('디바이스 프리셋',[]),groups=new Map();
      choices.forEach(p=>{let parent=preset;if(p.group){if(!groups.has(p.group)){const g=document.createElement('optgroup');g.label=p.group;groups.set(p.group,g);preset.append(g);}parent=groups.get(p.group);}const o=document.createElement('option');o.value=p.id;o.textContent=p.label;parent.append(o);});
      const custom=document.createElement('option');custom.value='custom';custom.textContent='사용자 설정';preset.append(custom);preset.value=defaultPreset.id;
      const dimension=(name,value)=>{const l=document.createElement('label');l.textContent=name+' ';const input=document.createElement('input');input.type='number';input.min=100;input.max=10000;input.step=1;input.value=value;l.append(input);controls.append(l);return input;};
      const width=dimension('가로',c.width),height=dimension('세로',c.height);
      function resize(){const w=Number(width.value),h=Number(height.value);if(!size(w)||!size(h)){width.value=c.width;height.value=c.height;return;}c.width=w;c.height=h;preset.value='custom';fit(c);}
      width.onchange=resize;height.onchange=resize;
      preset.onchange=()=>{const p=choices.find(p=>p.id===preset.value);if(p){c.width=p.width;c.height=p.height;width.value=p.width;height.value=p.height;fit(c);}};
      button(controls,'회전',()=>{[c.width,c.height]=[c.height,c.width];width.value=c.width;height.value=c.height;preset.value='custom';fit(c);});
      const zoomLabel=document.createElement('label');zoomLabel.textContent='배율 ';
      const zoomInput=document.createElement('input');zoomInput.type='number';zoomInput.min=1;zoomInput.max=400;zoomInput.step=1;zoomInput.setAttribute('aria-label','보기 배율(%)');c.zoomInput=zoomInput;
      zoomLabel.append(zoomInput,document.createTextNode('% 보기'));controls.append(zoomLabel);
      zoomInput.onchange=()=>{const n=Number(zoomInput.value);if(Number.isInteger(n)&&n>=1&&n<=400)c.zoomScale=n/100;fit(c);};
      zoomInput.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();zoomInput.blur();}};
      const removeDevice=button(controls,'디바이스 제거',()=>{if(c.state.pending&&sync.checked)cards.forEach(x=>{cancel(x);render(x);});cancel(c);c.removed=true;c.observer.disconnect();cards.splice(cards.indexOf(c),1);card.remove();add.focus();});
      deviceRow.append(preset,removeDevice);sizeRow.append(...Array.from(controls.children).filter(el=>el!==deviceRow&&el!==sizeRow&&el!==appRow));
      c.screen=select('앱 화면',screens.length?screens.map(s=>[s.id,s.title]):[['','등록된 화면 없음']]);c.screen.disabled=!screens.length;c.screen.onchange=()=>go(c,c.screen.value);
      c.back=button(controls,'이전 화면',()=>{if(c.state.history.length){c.state.id=enter(c.state.history.pop(),c.state);publish(c);}});
      button(controls,manualStart?'앱 종료':'처음부터',()=>reset(c));
      const currentLabel=document.createElement('label');currentLabel.textContent='현재 화면 ';currentLabel.append(c.screen);
      appRow.append(currentLabel,c.back,controls.lastElementChild);
      if(flow)button(appRow,'사용자 기록 초기화',()=>{cancel(c);c.state=fresh();c.outcome.value='success';publish(c);});
      let launch;
      if(manualStart){launch=document.createElement('div');launch.className='ap-debug';c.launch=launch;const heading=document.createElement('strong');heading.textContent='앱 시작 설정';launch.append(heading,document.createElement('br'));card.append(launch);}
      if(flow){
        const debug=document.createElement('details');debug.className='ap-debug';c.debug=debug;const summary=document.createElement('summary');summary.textContent='실행 기록 · 검증용';debug.append(summary);card.append(debug);
        const inputs={};c.inputs=inputs;Object.keys(flow.defaults).forEach(key=>{const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=flow.defaults[key];inputs[key]=input;label.append(input,document.createTextNode(flow.labels?.[key]||key));(launch||debug).append(label);});
        if(!manualStart)button(debug,'설정으로 재시작',()=>reset(c,Object.fromEntries(Object.entries(inputs).map(([k,input])=>[k,input.checked])),true));
        const requestSettings=document.createElement('div');requestSettings.className='ap-debug';c.requestSettings=requestSettings;card.append(requestSettings);
        const requestTitle=document.createElement('strong');requestTitle.textContent='다음 동작의 요청 설정';requestSettings.append(requestTitle,document.createElement('br'));
        const ol=document.createElement('label');ol.textContent='다음 요청 결과 ';c.outcome=document.createElement('select');[['success','성공'],['failure','실패'],['timeout','시간 초과']].forEach(([v,t])=>{const o=document.createElement('option');o.value=v;o.textContent=t;c.outcome.append(o);});ol.append(c.outcome);requestSettings.append(ol);
        const dl=document.createElement('label');dl.textContent='응답 지연(ms) ';c.delay=document.createElement('input');c.delay.type='number';c.delay.min=0;c.delay.max=5000;c.delay.value=600;dl.append(c.delay);requestSettings.append(dl);
        c.trace=document.createElement('pre');c.trace.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px';debug.append(c.trace);
      }
      if(manualStart)c.start=button(launch,'앱 시작',()=>reset(c,c.inputs?Object.fromEntries(Object.entries(c.inputs).map(([k,input])=>[k,input.checked])):undefined,true));
      c.meta=document.createElement('p');c.meta.className='ap-meta';card.append(c.meta);
      c.viewport=document.createElement('div');c.viewport.className='ap-viewport';
      const stage=document.createElement('div');stage.className='ap-stage';card.append(stage);stage.append(c.viewport);
      const shortcuts=document.createElement('details');shortcuts.className='ap-shortcuts';shortcuts.open=global.innerWidth>700;c.shortcuts=shortcuts;
      const shortcutTitle=document.createElement('summary');shortcutTitle.textContent='화면 바로가기';shortcuts.append(shortcutTitle);
      const hint=document.createElement('p');hint.className='ap-note';hint.textContent='앞선 이동은 생략하고 진입 규칙을 적용합니다.';shortcuts.append(hint);
      screens.forEach(s=>{const b=button(shortcuts,s.title,()=>go(c,s.id));b.dataset.screen=s.id;});
      stage.append(shortcuts);
      c.spacer=document.createElement('div');c.spacer.className='ap-size';c.viewport.append(c.spacer);
      c.frame=document.createElement('iframe');c.frame.title=title.textContent+' 앱 화면';c.frame.className='ap-frame';c.frame.setAttribute('sandbox','allow-same-origin');c.spacer.append(c.frame);
      c.observer=new ResizeObserver(()=>fit(c));c.observer.observe(c.viewport);render(c);
    }
    create();
    return {destroy(){cards.forEach(c=>{cancel(c);c.removed=true;c.observer.disconnect();});root.replaceChildren();delete root.dataset.appPreviewReady;}};
  }
  global.AppPreview={mount,validate};
})(window);
