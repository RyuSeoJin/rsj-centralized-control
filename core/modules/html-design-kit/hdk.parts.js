/* 생성물: 공용 부품 초기화 함수 */

hdk.register('code-block.line-numbers', function (root) {const r=root,c=r.querySelector('code'),hl=(r.dataset.hl||'').split(',').map(Number);
const lines=c.textContent.split('\n');c.innerHTML=lines.map((l,i)=>`<span class="hdk-code-block__line" ${hl.includes(i+1)?'data-hl="true"':''}>${l.replace(/</g,'&lt;')||' '}</span>`).join('\n');
r.querySelector('.hdk-code-block__nums').textContent=lines.map((_,i)=>i+1).join('\n');});


hdk.register('code-block.titled-copy', function (root) {const r=root,b=r.querySelector('[data-action="copy"]');b.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(r.querySelector('code').textContent);b.textContent='복사됨';setTimeout(()=>b.textContent='복사',2000);}catch(e){}});});


hdk.register('faq.grouped-tabs', function (root) {const r=root,c=[...r.querySelectorAll('.hdk-faq__chip')],d=[...r.querySelectorAll('details[data-group]')];
c.forEach(b=>b.addEventListener('click',()=>{c.forEach(x=>x.setAttribute('aria-pressed',String(x===b)));const g=b.dataset.group;d.forEach(x=>x.hidden=!(g==='all'||x.dataset.group===g));}));});


hdk.register('frame.sidebar-shell', function (root) {
  root.querySelector('.hdk-frame__scrim').addEventListener('click', () => root.dataset.open = 'false');
  // topbar 안의 [data-action="toggle-sidebar"] 가 있으면 연결
  root.addEventListener('click', e => {
    const b = e.target.closest('[data-action="toggle-sidebar"]'); if (!b) return;
    const desktop = window.matchMedia('(min-width: 1024px)').matches;
    if (desktop) root.dataset.collapsed = root.dataset.collapsed === 'true' ? 'false' : 'true';
    else root.dataset.open = root.dataset.open === 'true' ? 'false' : 'true';
  });
});


hdk.register('modal.dialog', function (root) {const r=root,d=r.querySelector('dialog');r.querySelectorAll('[data-action="close"]').forEach(b=>b.addEventListener('click',()=>d.close()));});


hdk.register('modal.drawer', function (root) {const r=root;r.querySelectorAll('[data-action="close"]').forEach(b=>b.addEventListener('click',()=>r.dataset.open='false'));});


hdk.register('pricing.toggle-period', function (root) {const r=root;r.querySelectorAll('.hdk-pricing__toggle button').forEach(b=>b.addEventListener('click',()=>{r.dataset.period=b.dataset.period;r.querySelectorAll('.hdk-pricing__toggle button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));r.querySelectorAll('[data-monthly]').forEach(v=>v.textContent=v.dataset[b.dataset.period]);}));});


hdk.register('slider.logo-marquee', function (root) {const r=root,t=r.querySelector('.hdk-slider__track');t.appendChild(t.querySelector('.hdk-slider__list').cloneNode(true));});


hdk.register('slider.thumbnail-strip', function (root) {const r=root,t=r.querySelector('.hdk-slider__track'),n=t.children.length;let i=0;
function go(k){i=(k+n)%n;t.style.transform='translateX(-'+(i*100)+'%)';r.querySelectorAll('[data-dot]').forEach((d,j)=>d.setAttribute('aria-current',String(j===i)));}
r.querySelectorAll('[data-action="prev"]').forEach(b=>b.onclick=()=>go(i-1));r.querySelectorAll('[data-action="next"]').forEach(b=>b.onclick=()=>go(i+1));
r.querySelectorAll('[data-dot]').forEach((d,j)=>d.onclick=()=>go(j));});


hdk.register('tabs.card-attached', function (root) {const r=root,t=[...r.querySelectorAll('.hdk-tabs__tab')],p=[...r.querySelectorAll('.hdk-tabs__panel')];
t.forEach((b,i)=>b.addEventListener('click',()=>{t.forEach((x,k)=>x.setAttribute('aria-selected',String(k===i)));p.forEach((x,k)=>x.hidden=k!==i);}));});
hdk.register('tabs.pill', function (root) {
  const tabs = [...root.querySelectorAll('.hdk-tabs__tab')];
  const panels = [...root.querySelectorAll('.hdk-tabs__panel')];
  tabs.forEach((t, i) => t.addEventListener('click', () => {
    tabs.forEach((x, k) => x.setAttribute('aria-selected', String(k === i)));
    panels.forEach((p, k) => { p.hidden = k !== i; });
  }));
});


hdk.register('tabs.underline', function (root) {
  const tabs = [...root.querySelectorAll('.hdk-tabs__tab')];
  const panels = [...root.querySelectorAll('.hdk-tabs__panel')];
  const ind = root.querySelector('.hdk-tabs__indicator');
  function activate(i) {
    tabs.forEach((t, k) => t.setAttribute('aria-selected', String(k === i)));
    panels.forEach((p, k) => { p.hidden = k !== i; });
    const t = tabs[i];
    ind.style.left = t.offsetLeft + 'px'; ind.style.width = t.offsetWidth + 'px';
  }
  tabs.forEach((t, i) => t.addEventListener('click', () => activate(i)));
  activate(tabs.findIndex(t => t.getAttribute('aria-selected') === 'true') || 0);
  window.addEventListener('resize', () => activate(tabs.findIndex(t => t.getAttribute('aria-selected') === 'true')));
});

hdk.register('tabs.vertical', function (root) {const r=root,t=[...r.querySelectorAll('.hdk-tabs__tab')],p=[...r.querySelectorAll('.hdk-tabs__panel')];
t.forEach((b,i)=>b.addEventListener('click',()=>{t.forEach((x,k)=>x.setAttribute('aria-selected',String(k===i)));p.forEach((x,k)=>x.hidden=k!==i);}));});