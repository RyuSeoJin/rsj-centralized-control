/* workflow-explorer runtime
 * 입력: <script id="wfx-data" type="application/json"> — rules/explorer.md §데이터 형식
 * 화면: 전체 흐름도(유저·시스템 구역) · 행동 패널 · 화면 패널 · 경로 흐름도
 * 외부 의존 없음. 시뮬레이터 연결은 선택(meta.simulator)이며 postMessage 규약은 rules §연결 규약.
 */
(function(){
'use strict';
var DATA=JSON.parse(document.getElementById('wfx-data').textContent);
var SVGNS='http://www.w3.org/2000/svg';
/* 크기·간격 — 흐름도 작성 규칙(FigJam) 비율을 따라 열 간격을 도형 폭보다 넉넉히 둡니다(CP 열 중심 간격 · SH 갈래 행 간격 · GAP 흐름 띠 사이). */
var WIDE=false; // 넓혀 다시 찾기는 배치가 끝난 뒤 한 번만(wideSweep)
var MIN_TAIL=24; // 도형으로 들어가는 마지막 구간 최소 길이 — 화살표 머리(약 11px)가 선을 덮지 않게(2026-10-06 사용자 요청)
var SLANT=11; // 평행사변형 기울기(가로 11px) — 글자 여백은 SLANT+9로 기울어진 변에 닿지 않게(2026-10-06)
var G={LW:76,LH:40,W:200,H:72,DW:200,DH:100,RW:44,CP:330,SH:140,RG:68,PADL:96,LPAD:30,HEAD:52,GAP:64,BACK:14,UIH:330,TW:124};
var lanes=DATA.lanes||[{key:'u',label:'유저 구역'},{key:'s',label:'시스템 구역'}];
var laneIndex={};lanes.forEach(function(l,i){laneIndex[l.key]=i;});
var userLane=(DATA.meta&&DATA.meta.userLane)||lanes[0].key;

/* ---------- 그래프 ---------- */
var nodes={},out={},inc={},flows=DATA.flows||[];
/* 데이터에서 그래프(도형 · 나가고 들어오는 연결 · 섹션)를 만듭니다. */
function buildGraph(){
  nodes={};out={};inc={};flows=DATA.flows||[];incMemo=null;parMemo=null;
  flows.forEach(function(f){f.nodes.forEach(function(n){n.flow=f.code;nodes[n.id]=n;out[n.id]=[];inc[n.id]=[];});});
  flows.forEach(function(f){(f.edges||[]).forEach(function(e){addEdge(e,false);});});
  (DATA.links||[]).forEach(function(e){addEdge(e,true);});
  sections={};secList=[];
  flows.forEach(function(f){f.nodes.forEach(function(n){var k=secOf(n.id);if(!sections[k]){sections[k]={key:k,flow:f,ids:[],title:(DATA.meta&&DATA.meta.sections&&DATA.meta.sections[k])||f.title};secList.push(sections[k]);}sections[k].ids.push(n.id);});});
  if(window.WorkflowExplorer){window.WorkflowExplorer.nodes=nodes;window.WorkflowExplorer.out=out;}
}
function addEdge(e,cross){
  if(!nodes[e.from]||!nodes[e.to])return;
  e.cross=!!cross;e.key=(cross?'x:':'e:')+e.from+'>'+e.to+(e.label?'#'+e.label:'');
  out[e.from].push(e);inc[e.to].push(e);
}
function resolve(id){var seen={};while(nodes[id]&&nodes[id].type==='ref'&&nodes[id].target&&!seen[id]){seen[id]=1;id=nodes[id].target;}return id;}
function code(n){return n.code||n.id;}
function isUser(n){return n&&n.lane===userLane;}
function oneLine(t){return String(t||'').replace(/\s*\n\s*/g,' ');}
/* 이동 설명(2026-10-07 사용자 요청) — 오각형 · 칩 · 서브루틴을 누르기 전에 어디로 가는지 말풍선과 화면 낭독 이름으로 알립니다.
   도착 도형의 코드 · 문구, 다른 섹션이면 그 섹션 이름, 연결 라벨이 있으면 라벨까지 붙입니다. */
function moveInfo(to,from,back,label){var t=nodes[to];if(!t)return null;var ks=secOf(to),s=sections[ks];
  return {code:code(t),text:oneLine(t.text),sec:from&&s&&ks!==secOf(from)?s.key+' · '+s.title:'',verb:back?'돌아가기':'이동',label:label?oneLine(label):''};}
function moveTip(to,from,back,label){var m=moveInfo(to,from,back,label);if(!m)return '';
  return m.code+' '+m.text+(m.sec?' · '+m.sec.replace(' · ',' '):'')+(back?'(으)로 돌아가기':'(으)로 이동')+(m.label?' — '+m.label:'');}
/* 이동 블록(2026-10-07 사용자 요청) — 오각형 · 서브루틴에 마우스를 올리거나 초점이 가면 바로(지연 없이) 도형 곁에 도착지 블록을 띄웁니다.
   브라우저 말풍선(title)은 늦게 뜨고 모양을 정할 수 없어 쓰지 않습니다. 블록은 누름을 가로채지 않습니다(pointer-events 없음). */
var moveTipEl=null;
function moveBlock(lg,on,m,head){
  if(!on||!m){if(moveTipEl)moveTipEl.hidden=true;return;}
  if(!moveTipEl){moveTipEl=document.createElement('div');moveTipEl.className='wfx-movetip';moveTipEl.setAttribute('aria-hidden','true');document.body.appendChild(moveTipEl);}
  moveTipEl.innerHTML='<span class="wfx-movetip-verb">'+esc(head||m.verb)+'</span><div class="wfx-movetip-main"><b>'+esc(m.code)+'</b> '+esc(m.text)+'</div>'+
    (m.sec?'<div class="wfx-movetip-sec">'+esc(m.sec)+'</div>':'')+(m.label?'<div class="wfx-movetip-label">'+esc(m.label)+'</div>':'');
  moveTipEl.hidden=false;var r=lg.getBoundingClientRect(),w=moveTipEl.offsetWidth,h=moveTipEl.offsetHeight,x=Math.max(8,Math.min(r.left,innerWidth-w-8)),y=r.bottom+8;
  if(y+h>innerHeight-8)y=Math.max(8,r.top-h-8);moveTipEl.style.left=x+'px';moveTipEl.style.top=y+'px';}

/* ---------- 배치 ----------
   흐름도 작성 규칙(FigJam 보드)과 같은 구조로 그립니다.
   · 섹션 = 프로세스. 코드가 「A1-02」처럼 앞부분을 가지면 그 앞부분(A1)이 섹션이고, 아니면 흐름(G)이 섹션입니다. 이름은 meta.sections[섹션] → 흐름 이름 순입니다.
   · 읽기 나무 — 시작 섹션에서 섹션을 건너는 연결을 따라가며, 처음 닿는 섹션은 오른쪽에 자식 섹션으로 둡니다. 섹션 첫 도형이 아닌 곳으로 들어오면
     그 도형부터 닿는 도형만 담은 이어짐 섹션(「코드부터」)을 만듭니다. 형제 섹션은 아래로 쌓고 후속 섹션은 오른쪽에 둡니다(§4).
   · 부모 → 자식 섹션 연결은 실제 출발 도형에서 실제 도착 도형까지 섹션 사이 통로로 끊김 없이 그립니다(§5). 이미 다른 자리에 놓인 섹션으로 가는 연결은 「→ 코드」 칩입니다.
   · 섹션 안: 왼쪽→오른쪽 진행 · 위 유저 / 아래 시스템. 주 경로는 앞 도형의 행을 이어 곧게, 갈래는 빈 행으로(유저 구역은 위로) 쌓습니다. */
var SEC_RE=/^([A-Za-z]+\d+)-\d+$/;
function secOf(id){var n=nodes[id],m=SEC_RE.exec(code(n));return m?m[1]:n.flow;}
var sections={},secList=[];
buildGraph();
function inner(id){var k=secOf(id);return out[id].filter(function(e){return !e.cross&&secOf(e.to)===k;});}
function outer(id){var k=secOf(id);return out[id].filter(function(e){return e.cross||secOf(e.to)!==k;});}
/* 하위 섹션(2026-10-02 사용자 확정) — 화면(출력 도형)에서 유저가 할 수 있는 행동이 2개 이상이면, 행동마다 그 행동에서 시작하는 흐름을
   섹션 안의 작은 섹션(유저·시스템·UI 구역을 모두 가짐)으로 나눠 섹션 아래에 차례로 쌓습니다. 하위 섹션은 다른 흐름과 처음 만나는 도형 앞에서 끝납니다
   (들어오는 연결이 모두 그 하위 섹션이나 화면에서 오는 도형까지만 담음). 하위 섹션 안의 화면은 다시 나누지 않습니다(한 단계). 데이터에는 없고 배치할 때만 만듭니다. */
var SUBOF={},SUBS={};
function computeSubs(){
  SUBOF={};SUBS={};var only=DATA.meta&&DATA.meta.subSections; // 하위 섹션을 켤 섹션 목록(없으면 전체 · 2026-10-02)
  secList.forEach(function(s){if(only&&only.indexOf(s.key)<0)return;var inSec={};s.ids.forEach(function(i){inSec[i]=1;});
    s.ids.forEach(function(h){
      if(nodes[h].type!=='output'||SUBOF[h])return;
      var acts=inner(h).filter(function(e){return inSec[e.to]&&e.to!==h&&isUser(nodes[e.to]);});
      if(acts.length<2)return;
      var actT={},taken={},got=[];acts.forEach(function(e){actT[e.to]=1;});
      acts.forEach(function(e){var st=e.to;if(SUBOF[st]||taken[st])return;
        var sub={},list=[st];sub[st]=1;
        for(var ch=true;ch;){ch=false;list.slice().forEach(function(u){inner(u).forEach(function(x){var t=x.to;
          if(!inSec[t]||t===h||sub[t]||SUBOF[t]||taken[t]||actT[t])return;
          if(inc[t].every(function(y){return y.from===h||sub[y.from];})){sub[t]=1;list.push(t);ch=true;}});});}
        if(!inc[st].every(function(y){return y.from===h||sub[y.from]||taken[y.from];}))return; // 시작 도형도 다른 흐름에서 들어오면 나누지 않습니다
        if(list.length-1<5)return; // 하위 섹션 안에 그려질 실제 도형(메인에 남는 행동 · 서브루틴 · 오각형 제외)이 5개 이상일 때만 나눕니다(2026-10-06 사용자 확정)
        var e2=inner(st).filter(function(x){return sub[x.to]&&x.to!==st;})[0];if(!e2)return;
        list.forEach(function(i){taken[i]=1;});
        got.push({hub:h,action:st,start:e2.to,edge:e2,ids:s.ids.filter(function(i){return sub[i]&&i!==st;})}); // 유저 행동은 메인 섹션에 두고 그 다음 도형부터 하위 섹션
      });
      if(!got.length)return;
      got.forEach(function(g,k){g.key=s.key+'#'+h+'#'+k;g.n=k;g.title=code(nodes[h])+' ▸ '+oneLine(nodes[g.action].text);g.ids.forEach(function(i){SUBOF[i]=g;});});
      (SUBS[s.key]=SUBS[s.key]||[]).push({hub:h,subs:got});
    });
  });
}
computeSubs();
var views=[],viewByKey={},canon={},totalW=0,totalH=0;
function reach(t){var seen={};(function go(i){if(seen[i])return;seen[i]=1;inner(i).forEach(function(e){go(e.to);});})(t);return sections[secOf(t)].ids.filter(function(i){return seen[i];});}
function makeView(sec,entry,parent){
  var isEntry=entry===sec.ids[0],key=sec.key+'@'+(isEntry?'':entry);
  var v={key:key,sec:sec,entry:entry,cont:!isEntry,ids:(isEntry?sec.ids.slice():reach(entry)).filter(function(i){return i===entry||!SUBOF[i];}),parent:parent,children:[],lines:[],refs:[],inst:{},subs:[]};
  v.ids.forEach(function(i){if(!canon[i])canon[i]=v;});
  views.push(v);viewByKey[key]=v;if(!sec.placed)sec.placed=v;if(parent)parent.children.push(v);
  if(isEntry)(SUBS[sec.key]||[]).forEach(function(hb){hb.subs.forEach(function(g){ // 하위 섹션 — 이 섹션 상자 안 아래에 쌓습니다
    var sv={key:g.key,sec:sec,entry:g.start,cont:false,sub:g,host:v,ids:g.ids.slice(),parent:null,children:[],lines:[],refs:[],inst:{},subs:[]};
    sv.ids.forEach(function(i){if(!canon[i])canon[i]=sv;});views.push(sv);viewByKey[sv.key]=sv;v.subs.push(sv);});});
  return v;
}
function buildTree(){
  views=[];viewByKey={};canon={};secList.forEach(function(s){s.placed=null;});
  var start=DATA.meta&&DATA.meta.start&&nodes[DATA.meta.start]?DATA.meta.start:flows[0].nodes[0].id;
  var roots=[];
  /* 섹션 한 줄(sectionChain · 2026-10-07 사용자 요청) — meta.sectionChain에 적은 섹션들은 연결과 상관없이 적은 순서대로 왼쪽에서 오른쪽으로 놓습니다.
     그중 한 섹션에 처음 닿으면 목록 전체를 앞 섹션의 자식으로 차례로 놓고(이어짐 섹션을 만들지 않음), 바로 앞 섹션의 연결만 선으로, 나머지는 「→ 코드」 칩으로 잇습니다.
     목록 하나(["A3","A4"]) 또는 목록의 목록([["A3","A4"],["B1","B2"]])을 받습니다. */
  var CHAIN={},sc0=DATA.meta&&DATA.meta.sectionChain;
  if(sc0&&sc0.length)(Array.isArray(sc0[0])?sc0:[sc0]).forEach(function(list){list.forEach(function(k){CHAIN[k]=list;});});
  function placeChain(list,parent,q){var p=parent;list.forEach(function(k){var c=sections[k];if(!c)return;if(c.placed){p=c.placed;return;}var nv=makeView(c,c.ids[0],p);q.push(nv);p=nv;});}
  function grow(root){roots.push(root);var q=[root];if(CHAIN[root.sec.key])placeChain(CHAIN[root.sec.key],root,q);while(q.length){var v=q.shift();
    v.subs.forEach(function(sv){q.push(sv);});
    v.ids.forEach(function(id){outer(id).forEach(function(e){
      var t=resolve(e.to),s=sections[secOf(t)];if(!s)return;if(CHAIN[s.key]&&!s.placed)placeChain(CHAIN[s.key],v.host||v,q);var key=s.key+'@'+(t===s.ids[0]?'':t),w=viewByKey[key];
      if(!w&&s.placed)w=canon[t]||s.placed; // 이미 놓인 섹션이면 이어짐 섹션을 새로 만들지 않고 그 섹션의 도형을 가리킵니다
      if(!w){w=makeView(s,t,v.host||v);q.push(w);if(v.host||e.chip)v.refs.push({e:e,from:id,to:t,view:w});else v.lines.push({e:e,from:id,to:t,view:w});} // chip(데이터 지정)인 연결도 선 대신 칩 — 섹션은 자식 섹션으로 그대로 놓음(2026-10-06) // 하위 섹션에서 다른 섹션으로 가는 연결은 칩(그 섹션은 바깥 섹션의 자식)
      else if(w.parent===v&&w.entry===t&&!e.chip)v.lines.push({e:e,from:id,to:t,view:w});
      else v.refs.push({e:e,from:id,to:t,view:w});
    });});
  }}
  var s0=sections[secOf(start)];grow(makeView(s0,s0.ids[0],null));
  secList.forEach(function(s){if(s.ids.some(function(i){return !canon[i];}))grow(makeView(s,s.ids[0],null));});
  return roots;
}
function layoutView(v){
  var ids=v.ids,inV={};ids.forEach(function(i){inV[i]=1;});
  var internal=function(id){return inner(id).filter(function(e){return inV[e.to];});};
  var state={},order=[],back={};
  var roots=ids.filter(function(i){return !inc[i].some(function(e){return !e.cross&&inV[e.from]&&secOf(e.from)===secOf(i);});});
  roots=[v.entry].concat(roots.filter(function(i){return i!==v.entry;})); // 들어오는 도형을 맨 앞 열에 두어 섹션 사이 연결선이 다른 도형을 지나지 않게
  if(!roots.length)roots=[ids[0]];
  function dfs(i){state[i]=1;internal(i).forEach(function(e){if(state[e.to]===1||e.to===v.entry)back[e.key]=1;else if(!state[e.to])dfs(e.to);});state[i]=2;order.push(i);} // 들어오는 도형(entry)으로 가는 연결은 늘 되돌아가는 연결 — 앞 도형이 하위 섹션으로 빠져 새 시작점이 생겨도 들어오는 도형이 맨 앞 열을 지킴
  roots.forEach(function(r){if(!state[r])dfs(r);});ids.forEach(function(i){if(!state[i])dfs(i);});
  var rank={};order.reverse().forEach(function(i){if(rank[i]==null)rank[i]=0;internal(i).forEach(function(e){if(back[e.key])return;rank[e.to]=Math.max(rank[e.to]||0,rank[i]+1);});});
  /* 조건 아래 배치(below · 2026-10-02 사용자 요청) — 데이터에서 below로 지정한 도형은, 조건 도형 하나에서만 들어오고 나가는 선이 모두 앞 단계로 되돌아갈 때
     다음 열이 아니라 그 조건과 같은 열(바로 아래)에 둡니다(로그인 실패 안내 → 다시 로그인 등). 모든 갈래에 일괄 적용하면 다른 흐름의 교차가 늘어 지정한 도형에만 씁니다. */
  ids.forEach(function(i){if(!nodes[i].below)return;var ps=inc[i].filter(function(e){return !e.cross&&inV[e.from]&&secOf(e.from)===secOf(i)&&!back[e.key];});if(ps.length!==1||nodes[ps[0].from].type!=='decision')return;
    var os=internal(i);if(!os.length||outer(i).length||!os.every(function(e){return back[e.key];}))return;rank[i]=rank[ps[0].from];});
  /* 다음 열에 두기(colAfter · 2026-10-06 사용자 요청) — 데이터에서 colAfter(도형 코드)를 준 도형은 그 도형보다 한 열 이상 오른쪽에 둡니다. 같은 열에 쌓여 선이 엇갈릴 때 씁니다. */
  ids.forEach(function(i){var t=nodes[i].colAfter;if(t&&rank[t]!=null&&rank[i]<=rank[t]){var d=rank[t]+1-rank[i];
    (function push(k,dd,seen){if(seen[k])return;seen[k]=1;rank[k]+=dd;internal(k).forEach(function(e){if(!back[e.key]&&inV[e.to]&&rank[e.to]<=rank[k])push(e.to,rank[k]+1-rank[e.to],seen);});})(i,d,{});}});
  /* 먼 복귀 연결자(2026-10-02 사용자 확정) — 두 열 이상 앞 도형으로 돌아가는 연결은 긴 선 대신, 출발 도형 다음 열의 맨 왼쪽(출발 도형 바로 옆)에
     작은 오각형 표식(「↩ 코드」)을 두고 짧은 선으로 잇습니다. 단계가 아니라 표식이라 작고 흐리게 그리며 열 폭을 차지하지 않습니다(마지막 열이면 표식 폭만 늘림).
     도착 도형의 문구는 마우스를 올리면 말풍선으로 보입니다. 새 단계가 아니라 표시 방법이라 데이터에는 없고 배치할 때만 만듭니다. */
  /* 하위 섹션과 바깥 섹션·다른 하위 섹션 사이 연결도 같은 연결자로 표시합니다 — 화면(허브)이나 그보다 앞 도형으로 가면 「↩」, 그 밖은 「→」.
     화면에서 하위 섹션 첫 도형으로 가는 연결은 연결자 대신 하위 섹션으로 내려가는 선으로 그립니다(drawSubBus). */
  var sub={};ids=ids.slice();var host=v.host;
  /* 하위 섹션에서 같은 흐름의 다른 섹션으로 가는 연결도 칩 대신 「→ 코드」 연결자와 선으로 그립니다(2026-10-06 사용자 요청). 흐름 사이 연결(links)은 칩 그대로입니다. */
  var subOut=function(i){return v.sub?outer(i).filter(function(e){return !e.cross;}):[];};
  v.ids.forEach(function(i){subOut(i).forEach(function(e){v.refs=v.refs.filter(function(R){return R.e!==e;});});});
  v.ids.forEach(function(i){inner(i).concat(subOut(i)).forEach(function(e){var cross=!inV[e.to],sym='↩';
    if(cross){if(!(v.sub||SUBOF[e.to]))return;if(v.subs.some(function(sv){return sv.sub.edge===e;}))return;
      var hb=v.sub&&v.sub.hub,ac=v.sub&&v.sub.action,hi=host&&host.inst;sym=v.sub&&(e.to===hb||e.to===ac||(hi&&hi[e.to]&&hi[ac]&&hi[e.to]._rank<=hi[ac]._rank))?'↩':'→';}
    else if(!(back[e.key]||rank[e.to]<rank[i])||rank[i]-rank[e.to]<FAR_BACK)return;
    var vid='link:'+e.key,t=nodes[e.to];
    nodes[vid]={id:vid,code:code(t),type:'link',virtual:true,sym:sym,from:i,label:e.label,target:e.to,kind:e.kind,lane:nodes[i].lane,flow:nodes[i].flow,text:t.text};
    var ve={from:i,to:vid,kind:e.kind,label:e.label,key:vid,cross:false,orig:e};
    inc[vid]=[ve];out[vid]=[];sub[e.key]=ve;rank[vid]=rank[i]+1;ids.push(vid);inV[vid]=1;});});
  /* 다른 섹션·흐름으로 가는 칩(「→ 코드」 · 도형 아래)도 출발 도형 오른쪽의 연결자 도형(「→ 코드」 오각형)과 선으로 그립니다(2026-10-07 사용자 요청).
     연결자는 다음 열 자리에 두고, 나가는 선이 그것뿐이면 출발 도형 오른쪽에 바로 붙입니다(위·아래에는 붙이지 않음). 누르면 도착 도형으로 이동합니다. */
  var refOut={};v.refs.forEach(function(R){if(!inV[R.from]||nodes[R.from].virtual)return;(refOut[R.from]=refOut[R.from]||[]).push(R);});
  Object.keys(refOut).forEach(function(i){refOut[i].forEach(function(R){var e=R.e,vid='link:'+e.key,t=nodes[R.to];if(inV[vid]||!t)return;
    nodes[vid]={id:vid,code:code(t),type:'link',virtual:true,sym:'→',refConn:true,from:i,label:e.label,target:R.to,kind:e.kind,lane:nodes[i].lane,flow:nodes[i].flow,text:t.text};
    var ve={from:i,to:vid,kind:e.kind,label:e.label,key:vid,cross:false,orig:e};inc[vid]=[ve];out[vid]=[];sub[e.key]=ve;rank[vid]=rank[i]+1;ids.push(vid);inV[vid]=1;});});
  v.refs=v.refs.filter(function(R){return !(refOut[R.from]&&refOut[R.from].indexOf(R)>=0);});
  var refEdges=function(id){return (refOut[id]||[]).map(function(R){return R.e;});};
  /* 하위 섹션 열기(2026-10-02 사용자 확정 · 2026-10-03 보완) — 유저 행동은 메인 섹션의 일반 도형으로 두고, 그 뒤에 이어지는 프로세스를 서브루틴 도형
     (양옆 세로선 사각형 · 하위 섹션 첫 도형의 코드·문구 · 오른쪽에 ▸ · 그 첫 도형의 구역)으로 잇습니다.
     서브루틴을 누르면 그 하위 섹션으로 들어갑니다. 오각형은 앞 흐름으로 되돌아가는 연결에만 씁니다(서브루틴 = 하위 프로세스 열기 · 오각형 = 되돌아감).
     화면에서 하위 섹션으로 직접 긋는 선은 두지 않습니다. */
  v.subs.forEach(function(sv){var g=sv.sub,act=g.action;if(!inV[act])return;var st=nodes[g.start],sr='sr:'+g.key;
    nodes[sr]={id:sr,code:code(st),type:'process',virtual:true,subr:true,from:act,target:g.start,kind:g.edge.kind,lane:st.lane,flow:nodes[act].flow,text:st.text,title:g.title};
    var e1={from:act,to:sr,kind:g.edge.kind,label:g.edge.label,key:sr,cross:false,orig:g.edge};
    out[sr]=[];inc[sr]=[e1];sub[g.edge.key]=e1;rank[sr]=rank[act]+1;ids.push(sr);inV[sr]=1;});
  if(ids.length>v.ids.length){v.ids=ids;internal=function(id){return inner(id).concat(nodes[id].virtual?[]:subOut(id)).concat(nodes[id].virtual?[]:refEdges(id)).filter(function(e){return inV[e.to]||sub[e.key];}).map(function(e){return sub[e.key]||e;});};}
  var P={};ids.forEach(function(i){P[i]=Object.create(nodes[i]);P[i]._rank=rank[i];});
  var maxSlot=lanes.map(function(){return 0;}),maxRank=0,used={},byRank={};
  ids.forEach(function(i){maxRank=Math.max(maxRank,rank[i]);(byRank[rank[i]]=byRank[rank[i]]||[]).push(i);});
  function preds(i){return inc[i].filter(function(e){return !e.cross&&inV[e.from]&&secOf(e.from)===secOf(i)&&!back[e.key]&&P[e.from]._slot!=null;});}
  /* 정렬 키 [앞 도형 행, 앞 도형 열(가까울수록 먼저), 나가는 연결 순서]. 시작 행은 같은 구역의 앞 도형이면 그 행, 구역이 바뀌면 경계에 가장 가까운 첫 행(0)입니다. */
  function key(i){var n=nodes[i],ps=preds(i);if(!ps.length)return{s:[0,0,ids.indexOf(i)],start:0};var best=null,start=null;ps.forEach(function(e){var p=P[e.from],k=[p.lane===n.lane?p._slot:-p._slot,p._rank,internal(e.from).indexOf(e)];if(!best||k[0]<best[0]||(k[0]===best[0]&&(k[1]>best[1]||(k[1]===best[1]&&k[2]<best[2])))){best=k;start=p.lane===n.lane?p._slot:0;}});return{s:best,start:start};}
  for(var r=0;r<=maxRank;r++){
    var col=(byRank[r]||[]).map(function(i){return{i:i,k:key(i)};});
    col.sort(function(a,b){return (nodes[b.i].rowFirst?1:0)-(nodes[a.i].rowFirst?1:0)||a.k.s[0]-b.k.s[0]||b.k.s[1]-a.k.s[1]||a.k.s[2]-b.k.s[2];}); // rowFirst(데이터 지정)인 도형을 그 열에서 먼저 쌓아 경계 쪽 행에 둡니다(2026-10-06 사용자 요청)
    col.forEach(function(c){var li=laneIndex[nodes[c.i].lane]||0,s=c.k.start;while(used[li+':'+s+':'+r])s++;used[li+':'+s+':'+r]=1;P[c.i]._slot=s;maxSlot[li]=Math.max(maxSlot[li],s+1);});
  }
  /* 섹션마다 열·행 간격 — 기본값에, 선을 겹치지 않게 놓지 못한 섹션은 넓힘 단계(GROW)만큼 더합니다. */
  var gw=GROW[v.key]||0;v._cp=G.CP+gw*120;v._rg=G.RG+gw*40;
  /* 도형 크기 — 글자가 잘리면 도형 높이를 늘리고(fitSize), 행 높이는 그 행에서 가장 높은 도형에 맞춥니다. */
  /* 선이 여럿 드나드는 도형은 출발·도착점 사이가 16px 이상 되도록 높이를 늘립니다(평행선 최소 간격 CLEAR보다 넓게). */
  var nOut={},nIn={};ids.forEach(function(i){nOut[i]=0;nIn[i]=0;});
  var lab={};ids.forEach(function(i){internal(i).forEach(function(e){nOut[i]++;nIn[e.to]++;if(e.label)lab[i]=1;});});
  v.lines.forEach(function(L){nOut[L.from]++;if(L.e.label)lab[L.from]=1;});if(v.parent)v.parent.lines.forEach(function(L){if(L.view===v)nIn[L.to]++;});
  ids.forEach(function(i){var s=fitSize(nodes[i]),k=Math.max(nOut[i]-(nodes[i].type==='decision'?2:0),nIn[i]),step=lab[i]?28:16,need=k>1?24+(k-1)*step:0;if(nodes[i].type==='decision')need=need*2;P[i]._w=s[0];P[i]._h=Math.max(s[1],need);P[i]._step=step;});
  v._rows=lanes.map(function(l,li){var hs=[];for(var s=0;s<Math.max(1,maxSlot[li]);s++)hs.push(G.H);ids.forEach(function(i){var n=P[i];if((laneIndex[n.lane]||0)===li)hs[n._slot]=Math.max(hs[n._slot],n._h);});return hs;});
  v.inst=P;v._back=back;v._maxRank=maxRank;v._laneH=v._rows.map(function(hs){return G.LPAD+hs.reduce(function(s,h){return s+h+v._rg;},0);});
  v._edges=[];ids.forEach(function(i){internal(i).forEach(function(e){v._edges.push(e);});});
  v._nb=v._edges.filter(function(e){return isBack(v,e);}).length;
  v._nc=v.lines.length; // 섹션 아래 통로 줄 수(되돌아가는 연결 · 자식 섹션 연결)
  var ly=G.HEAD;v._laneY=[];v._laneH.forEach(function(h,i){v._laneY[i]=ly;ly+=h;});
  v._uiH=ids.some(function(i){return nodes[i].thumb;})?G.UIH:0; // UI 구역은 통로 아래 맨 끝이라 선이 썸네일을 지나지 않습니다
  var realMax=0;ids.forEach(function(i){if(!nodes[i].virtual||nodes[i].subr)realMax=Math.max(realMax,rank[i]);}); // 서브루틴은 한 열을 차지하므로 섹션 폭에 넣습니다(오각형만 표식 폭으로 셈 · 2026-10-06)
  colGaps(v,P,maxRank);
  v._h=ly+G.BACK+6+(v._nb+v._nc+3)*14+v._uiH;v._w=G.PADL+v._colX[realMax]+v._cp+40+(maxRank>realMax?G.LW+60:0);
}
/* 열 사이 간격(2026-10-06 사용자 요청) — 열 사이를 지나는 선이 모두 같은 줄에서 곧게 이어지는 선(다음 열 · 같은 구역 같은 행 · 출발은 나가는 선 하나 또는 조건 ·
   도착은 왼쪽으로 들어오는 선 하나)뿐이면 그 사이를 GAP_MIN으로 좁히고, 선에 글(예 · 아니오 · 계기)이 있으면 그 글 폭만큼만 더합니다.
   꺾이는 선(다른 행·구역 · 두 열 이상 건너뜀 · 되돌아감 · 자식 섹션 선)이 세로로 지나는 열 사이는 통로가 필요하므로 기본 간격(CP)을 둡니다.
   오른쪽에 붙는 연결자는 그 사이에 들어갈 만큼, 서브루틴은 도형이 넓은 만큼 더합니다. 선을 놓지 못해 넓힌(GROW) 섹션도 곧은 선만 지나는 열 사이는 통로가 필요 없어 좁힙니다. */
var GAP_MIN=64;
function colGaps(v,P,maxRank){
  var wide={},need={},att={},deg={},cnt=function(k,i){deg[k+i]=(deg[k+i]||0)+1;};
  var total={};v._edges.forEach(function(e){total[e.from]=(total[e.from]||0)+1;});v.lines.forEach(function(L){total[L.from]=(total[L.from]||0)+1;}); // 연결자 붙이기(place)의 「다른 선 없음」과 같은 셈
  var nonLink={};v._edges.forEach(function(e){if(P[e.to]&&P[e.to].type!=='link')nonLink[e.from]=(nonLink[e.from]||0)+1;});v.lines.forEach(function(L){nonLink[L.from]=(nonLink[L.from]||0)+1;});
  v._edges.forEach(function(e){var a=P[e.from],b=P[e.to];if(!a||!b)return;if(b.type==='link'&&a.type!=='decision'&&nonLink[e.from])return; /* 다른 출구가 있으면 연결자는 위·아래에 붙음 */cnt('o',e.from);if(b._rank!==a._rank)cnt('i',e.to);});
  v.lines.forEach(function(L){cnt('o',L.from);if(P[L.from].type!=='decision')wide[P[L.from]._rank]=1;}); // 조건 도형의 자식 섹션 선은 아래·위 꼭짓점에서 곧게 통로로 내려감(findRoute)
  if(v.parent)v.parent.lines.forEach(function(L){if(L.view===v)cnt('i',L.to);});
  v._edges.forEach(function(e){var a=P[e.from],b=P[e.to];if(!a||!b)return;var ra=a._rank,rb=b._rank,lw=e.label?labelW(e.label):0;
    if(b.refConn&&rb===ra+1){att[ra]=Math.max(att[ra]||0,(lw?lw+40:36)+G.LW+16+v._edges.filter(function(x){return x.from===e.from&&P[x.to]&&P[x.to].refConn;}).length*24);need[ra]=Math.max(need[ra]||0,att[ra]);return;} // 칩 대신 그린 연결자 — 붙는 폭(att)을 통로와 별도로 더합니다(2026-10-07)
    if(b.type==='link'&&rb===ra+1&&!NOSHIFT[v.key+'|'+ra]&&((a.type==='decision'?(a.lane===b.lane&&a._slot===b._slot):total[e.from]===1))){need[ra]=Math.max(need[ra]||0,(lw?lw+30:36)+G.LW+16);return;} // 오른쪽에 붙는 연결자
    if(b.type==='link'&&!NOSHIFT[v.key+'|'+ra])return; // 그 밖의 연결자는 출발 도형 위·아래에 붙어 열 안에서 세로로
    if(rb===ra)return; // 같은 열(조건 아래 · 위아래 연결자)은 열 안에서 세로로
    if(rb<ra||isBack(v,e)){wide[ra]=1;if(rb>0)wide[rb-1]=1;return;}
    if(rb>ra+1){wide[ra]=1;wide[rb-1]=1;return;}
    var straight=a.lane===b.lane&&a._slot===b._slot&&(a.type==='decision'||(deg['o'+e.from]||0)===1)&&(deg['i'+e.to]||0)===1;
    if(!straight){wide[ra]=1;return;}
    need[ra]=Math.max(need[ra]||0,lw?lw+48:GAP_MIN);});
  v._colX=[0];for(var r=0;r<=maxRank;r++){
    var subr=v.ids.some(function(i){return P[i]._rank===r&&nodes[i].subr;})?24:0;
    var g=(wide[r]||need[r]==null)?v._cp-G.W+(att[r]||0):Math.max(att[r]?att[r]+24:0,Math.min(v._cp-G.W,Math.max(GAP_MIN,need[r])+subr)); // 통로가 필요한 열 사이에 연결자가 붙으면 그 폭만큼 넓혀 통로를 비워 둡니다
    v._colX.push(v._colX[r]+G.W+g);}
}
function colAt(v,r){var X=v._colX||[0];return r<X.length?X[r]:X[X.length-1]+(r-X.length+1)*v._cp;}
function isBack(v,e){return !!v._back[e.key]||v.inst[e.to]._rank<v.inst[e.from]._rank;}
// 먼 복귀 — 두 열 이상 앞 도형으로 돌아가는 연결은 오각형 연결자로 그립니다(layoutView · 2026-10-02 「↩ 코드 · 동일 단계」 칩을 같은 단계로 오해해 바꿈).
var FAR_BACK=2;
/* 위 구역(유저)은 첫 행을 아래 구역과 맞닿은 맨 아래에 두고 갈래 행을 위로 쌓습니다(§5 짧은 세로 이동). */
function mirrored(li){return lanes.length>1&&li<lanes.length-1;}
function rowCy(v,li,slot){var hs=v._rows[li],m=hs.length,y=v._laneY[li]+G.LPAD+8;for(var d=0;d<m;d++){var s=mirrored(li)?m-1-d:d;if(s===slot)return y+hs[s]/2;y+=hs[s]+v._rg;}return y;}
// 행 사이 통로의 가운데 높이(구역마다 첫 행 위 · 행 사이 · 마지막 행 아래)
function rowGaps(v){var ys=[];v._rows.forEach(function(hs,li){var m=hs.length,y=v._laneY[li]+G.LPAD+8;ys.push(y-v._rg/2);for(var d=0;d<m;d++){var s=mirrored(li)?m-1-d:d;y+=hs[s]+v._rg;ys.push(y-v._rg/2);}});return ys;}
var meas=null;
function fitSize(n){var s=size(n);if(n.type==='ref'||n.type==='link')return s;
  if(!meas){meas=document.createElement('div');meas.setAttribute('aria-hidden','true');meas.style.cssText='position:absolute;left:-9999px;top:0;visibility:hidden';document.body.appendChild(meas);}
  var pad=n.type==='decision'?34:(n.type==='process'?14:(n.type==='input'||n.type==='output'?SLANT+9:8)),d=document.createElement('div');d.className='wfx-label';d.style.height='auto';d.style.width=(s[0]-(n.subr?SUBR_PAD:pad*2))+'px';
  var c=document.createElement('b');c.textContent=code(n);d.appendChild(c);var t=document.createElement('span');t.textContent=n.text;d.appendChild(t);meas.innerHTML='';meas.appendChild(d);
  var ch=d.scrollHeight,need=n.type==='decision'?Math.ceil(ch*2.9)+4:ch+14+(n.type==='link'?16:0);return[s[0],Math.max(s[1],need)];}
function size(n){if(n.type==='link')return[G.LW,G.LH];if(n.subr)return[G.W+24,G.H];if(n.type==='decision')return[G.DW,G.DH];if(n.type==='ref')return[G.RW,G.RW];return[G.W,G.H];}
function gapX(v){return 120+v.lines.length*16+(GROW[v.key]||0)*100;}
function place(v,x,y){
  v._x=x;v._y=y;v._laneY=v._laneY.map(function(t){return t+y;});
  v.ids.forEach(function(i){var n=v.inst[i],li=laneIndex[n.lane]||0;n._cx=x+G.PADL+colAt(v,n._rank)+(n.type==='link'?n._w/2:G.W/2)+20;n._cy=rowCy(v,li,n._slot);}); // 연결자는 열 맨 왼쪽(출발 도형 쪽)
  /* 바로 아래 붙이기(under · 2026-10-06 사용자 요청) — 데이터에서 under(위 도형 코드)를 준 도형은 같은 열이면 그 도형 바로 아래(행 간격만큼)로 끌어올립니다.
     행 높이는 그 행에서 가장 큰 도형에 맞춰져 같은 열 두 도형이 멀리 떨어질 수 있어서입니다. 사이에 다른 도형이 있거나 구역을 벗어나면 그대로 둡니다. */
  v.ids.forEach(function(i){var n=v.inst[i],up=n.under&&v.inst[n.under];if(!up||up._rank!==n._rank||up.lane!==n.lane)return;
    var d=up._cy+up._h/2+v._rg+n._h/2-n._cy;if(d>=0)return;
    // 같은 구역·같은 행의 도형을 함께 올려 줄 맞춤을 지킵니다 — 올린 자리에서 위 도형과 행 간격보다 가까워지는 도형이 있으면 그만큼만 올립니다
    var row=v.ids.filter(function(j){var m=v.inst[j];return m.lane===n.lane&&m._slot===n._slot&&m.type!=='link';});
    row.forEach(function(j){var m=v.inst[j];v.ids.forEach(function(k){var o=v.inst[k];if(k===j||row.indexOf(k)>=0||Math.abs(o._cx-m._cx)>=(o._w+m._w)/2||o._cy>=m._cy)return;
      var lim=o._cy+o._h/2+v._rg+m._h/2-m._cy;if(lim>d)d=lim;});});
    if(d<0)row.forEach(function(j){v.inst[j]._cy+=d;});});
  /* 연결자 붙이기(2026-10-02 사용자 확정) — 열 자리 대신 출발 도형의 비어 있는 면에 붙입니다. 나가는 선이 연결자뿐이면(조건은 같은 줄이면) 오른쪽,
     오른쪽을 다른 선이 쓰면 아래(유저 구역은 바깥쪽인 위)를 먼저, 안 되면 반대쪽에 짧은 세로선으로 붙입니다. 선 길이는 라벨이 들어갈 만큼만입니다.
     다른 도형과 겹치거나 구역을 벗어나거나, 그 열 사이에서 선을 놓지 못하면(NOSHIFT) 붙이지 않고 다음 열 맨 왼쪽에 둡니다. */
  v.ids.forEach(function(i){var n=v.inst[i];if(n.type!=='link')return;var a=v.inst[n.from];if(!a||(NOSHIFT[v.key+'|'+a._rank]&&!n.refConn))return; // 칩 대신 그린 연결자는 열 사이를 넓혀 두었으므로 그대로 붙입니다(2026-10-07) · 선을 놓지 못해 떼어 낸 열(NOSHIFT)은 칩 대신 그린 연결자도 다음 열 자리에 둡니다
    var others=v._edges.filter(function(e){return e.from===a.id&&e.to!==n.id;}).length+v.lines.filter(function(L){return L.from===a.id;}).length;
    if(a.type==='decision'?(a.lane===n.lane&&a._slot===n._slot):!others){/* 오른쪽이 비어 있을 때만(조건은 같은 줄이면 오른쪽 꼭짓점) — 그 자리에 다른 도형이 있으면 아래·위로(2026-10-06) */
      var rx=a._cx+a._w/2+(n.label?labelW(n.label)+30:36)+n._w/2,ry=a._cy,lx=a._cx+a._w/2;
      var rhit=v.ids.some(function(j){if(j===i||j===a.id)return false;var m=v.inst[j];if(m.type==='link'&&!m._attach)return false;return m._cx+m._w/2>lx&&m._cx-m._w/2<rx+n._w/2+10&&m._cy+m._h/2>ry-n._h/2-10&&m._cy-m._h/2<ry+n._h/2+10;});
      if(!rhit){n._cx=rx;n._cy=ry;n._attach='r';return;}} // 같은 줄로도 맞춥니다 — 칩에서 바꾼 연결자는 다음 열의 다른 줄에 잡혀 있을 수 있음(2026-10-07)
    /* 칩 대신 그린 연결자(2026-10-07 사용자 요청 「바로 우측에」) — 오른쪽 가운데를 다른 선이 쓰면, 같은 출발 도형의 연결자끼리 출발 도형 바로 오른쪽 아래(안 되면 위)로
       차례로 쌓습니다. 자리가 없으면(구역 밖 · 다른 도형과 겹침) 다음 열 자리에 둡니다. 위·아래 면에는 붙이지 않습니다. */
    if(n.refConn){var mine=v.ids.filter(function(j){var m=v.inst[j];return m.refConn&&m.from===a.id&&m._attach!=='r';}),kk=Math.max(0,mine.indexOf(i));
      var mlw=mine.reduce(function(s,j){var m=v.inst[j];return Math.max(s,m.label?labelW(m.label):0);},0); // 한 묶음은 같은 x에 세로로 맞춥니다 — 가장 긴 라벨 + 선마다 꺾을 통로(24px)
      var rcx=a._cx+a._w/2+(mlw?mlw+40:36)+mine.length*24+n._w/2,rli=laneIndex[a.lane]||0,rl0=v._laneY[rli],rl1=rl0+v._laneH[rli],rsides=mirrored(rli)?['u','d']:['d','u'];
      /* 여럿이면 아래 · 위로 번갈아 쌓아 한쪽으로 길게 내려가지 않게 합니다(갈래 많은 도형). */
      /* 다른 선이 위(또는 아래)로만 가면 연결자는 반대쪽에만 쌓아 그 선과 엇갈리지 않게 합니다(2026-10-07). */
      var oup=0,odn=0;v._edges.forEach(function(e){if(e.from!==a.id)return;var b=v.inst[e.to];if(!b||b.refConn)return;if(b._cy<a._cy-4)oup++;else if(b._cy>a._cy+4)odn++;});if(v.lines.some(function(L){return L.from===a.id;}))odn++;
      var alt=mine.length>2&&!(oup&&!odn)&&!(odn&&!oup);if(oup&&!odn)rsides=['d','u'];else if(odn&&!oup)rsides=['u','d'];
      var half=Math.floor(kk/2),pref=kk%2?rsides.slice().reverse():rsides;rsides=alt?pref:rsides;
      for(var q=0;q<rsides.length*(mine.length+1);q++){var rs=rsides[q%rsides.length],off=(alt?half:kk)+Math.floor(q/rsides.length),dg=a.type==='decision'?24:0,rcy=rs==='d'?a._cy+a._h/2+12+dg+n._h/2+off*(n._h+10):a._cy-a._h/2-12-dg-n._h/2-off*(n._h+10); // 조건은 꼭짓점에서 라벨 붙은 세로선이 들어갈 만큼 더 띄웁니다 · 자리가 차 있으면 한 칸씩 더 바깥으로
        if(rcy-n._h/2<rl0+G.LPAD||rcy+n._h/2>rl1-6)continue;
        var rh=v.ids.some(function(j){if(j===i||j===a.id)return false;var m=v.inst[j];if(m.type==='link'&&!m._attach)return false;return m._cx+m._w/2>rcx-n._w/2-10&&m._cx-m._w/2<rcx+n._w/2+10&&m._cy+m._h/2>rcy-n._h/2-6&&m._cy-m._h/2<rcy+n._h/2+6;});
        if(!rh){n._cx=rcx;n._cy=rcy;n._attach='rs';return;}}
      return;}
    var li=laneIndex[a.lane]||0,ly0=v._laneY[li],ly1=ly0+v._laneH[li],L=n.label?44:24,sides=mirrored(li)?['u','d']:['d','u'];
    for(var k=0;k<sides.length;k++){var sd=sides[k],cy=sd==='d'?a._cy+a._h/2+L+n._h/2:a._cy-a._h/2-L-n._h/2;
      if(cy-n._h/2<ly0+G.LPAD||cy+n._h/2>ly1-6)continue;
      var x1=a._cx-n._w/2-10,x2=a._cx+n._w/2+10,y1=Math.min(cy-n._h/2,sd==='d'?a._cy+a._h/2:cy)-4,y2=Math.max(cy+n._h/2,sd==='u'?a._cy-a._h/2:cy)+4;
      var hit=v.ids.some(function(j){if(j===i||j===a.id)return false;var m=v.inst[j];if(m.type==='link'&&!m._attach)return false;return m._cx+m._w/2>x1&&m._cx-m._w/2<x2&&m._cy+m._h/2>y1&&m._cy-m._h/2<y2;});
      if(hit)continue;
      n._cx=a._cx;n._cy=cy;n._attach=sd;n._rank=a._rank;return;}
  });
  placeSubs(v,x,y);
  var cx=x+v._wT+gapX(v),cy=y,bottom=y+v._hT;
  /* 형제 섹션은 같은 흐름의 섹션을 먼저, 다른 흐름은 그 아래에 쌓습니다 — 큰 다른 흐름 가지에 같은 흐름 섹션이 멀리 밀리지 않게. */
  v.children.slice().sort(function(a,b){return (a.sec.flow!==v.sec.flow)-(b.sec.flow!==v.sec.flow)||v.children.indexOf(a)-v.children.indexOf(b);}).forEach(function(c){var b=place(c,cx,cy);cy=b+G.GAP;bottom=Math.max(bottom,b);});
  totalW=Math.max(totalW,x+v._wT);return bottom;
}
/* 하위 섹션 배치 — 바깥 섹션 내용(구역·UI 구역) 아래에, 화면(허브)마다 내려가는 통로 줄을 두고 그 아래에 하위 섹션을 쌓습니다.
   화면은 왼쪽부터 k번이고, k번 화면의 선은 화면 아래 → 그 열 오른쪽 틈 → 통로 줄 k → 왼쪽 기둥 k → 각 하위 섹션 첫 도형으로 갑니다.
   (2026-10-02 사용자 확정으로 내려가는 선 대신 서브루틴·오각형으로 이동 — 오른쪽 화면의 하위 섹션을 위에 둡니다.) */
function placeSubs(v,x,y){
  v._hT=v._h;v._wT=v._w;v._hubs=[];if(!v.subs.length)return;
  v.subs.forEach(function(sv){if(v._hubs.indexOf(sv.sub.hub)<0)v._hubs.push(sv.sub.hub);});
  v._hubs.sort(function(a,b){return v.inst[a]._cx-v.inst[b]._cx;});
  var indent=24,sy=y+v._h+16,w=v._w;
  v._hubs.slice().reverse().forEach(function(h){v.subs.forEach(function(sv){if(sv.sub.hub!==h)return;place(sv,x+indent,sy);sy+=sv._h+18;w=Math.max(w,indent+sv._w+14);});});
  v._hT=sy-y;v._wT=w;
}
function layout(){
  var roots=buildTree();views.forEach(layoutView);totalW=0;var y=0;views.forEach(function(v){v._hT=v._h;v._wT=v._w;});
  roots.forEach(function(r){y=place(r,0,y)+G.GAP*2;});totalH=Math.max(0,y-G.GAP*2);
  Object.keys(canon).forEach(function(id){var p=canon[id].inst[id],n=nodes[id];n._cx=p._cx;n._cy=p._cy;n._w=p._w;n._h=p._h;n._view=canon[id];});
}

/* ---------- SVG ---------- */
function el(tag,attrs,parent){var e=document.createElementNS(SVGNS,tag);for(var k in attrs)e.setAttribute(k,attrs[k]);if(parent)parent.appendChild(e);return e;}
/* 한 도형·연결이 여러 섹션(이어짐 섹션)에 그려질 수 있어, 강조는 그려진 것 전부에 줍니다. */
function multi(){var els=[];return{els:els,classList:{add:function(){var a=arguments;els.forEach(function(e){e.classList.add.apply(e.classList,a);});},remove:function(){var a=arguments;els.forEach(function(e){e.classList.remove.apply(e.classList,a);});},toggle:function(c,f){els.forEach(function(e){e.classList.toggle(c,f);});}}};}
function reg(map,k,e){(map[k]=map[k]||multi()).els.push(e);}
var svg,view,edgeEls={},nodeEls={},chipEls={};
function shape(n,g){
  var w=n._w,h=n._h,x=n._cx-w/2,y=n._cy-h/2,cls='wfx-shape',s=11;
  switch(n.type){
    case 'term':return el('rect',{x:x,y:y,width:w,height:h,rx:h/2,class:cls},g);
    case 'decision':return el('polygon',{points:[n._cx,y,x+w,n._cy,n._cx,y+h,x,n._cy].join(' '),class:cls},g);
    case 'input':case 'output':s=SLANT;return el('polygon',{points:[x+s,y,x+w,y,x+w-s,y+h,x,y+h].join(' '),class:cls},g);
    case 'link':return el('polygon',{points:[x,y,x+w,y,x+w,y+h-11,n._cx,y+h,x,y+h-11].join(' '),class:cls},g); // 아래가 뾰족한 오각형(페이지 외 연결자)
    case 'ref':return el('circle',{cx:n._cx,cy:n._cy,r:w/2,class:cls},g);
    case 'process':var r=el('rect',{x:x,y:y,width:w,height:h,rx:3,class:cls},g);el('line',{x1:x+9,y1:y,x2:x+9,y2:y+h,class:'wfx-bar'},g);el('line',{x1:x+w-9,y1:y,x2:x+w-9,y2:y+h,class:'wfx-bar'},g);return r;
    default:return el('rect',{x:x,y:y,width:w,height:h,rx:4,class:cls},g);
  }
}
var SUBR_PAD=42; // 서브루틴 글자 영역 = 폭 - (왼쪽 14 + 오른쪽 ▸ 자리 28) — ▸ 자리만큼만 도형을 넓힘(224px · 구분선 없음 · 2026-10-06 사용자 정정)
function label(n,g){
  var pad=n.type==='decision'?34:(n.type==='process'?14:(n.type==='input'||n.type==='output'?SLANT+9:8));
  var fo=el('foreignObject',{x:n._cx-n._w/2+pad,y:n._cy-n._h/2,width:n._w-(n.subr?SUBR_PAD:pad*2),height:n._h},g);
  var d=document.createElement('div');d.className='wfx-label'+(n.type==='ref'?' is-ref':'');
  if(n.type!=='ref'){var c=document.createElement('b');c.textContent=code(n);d.appendChild(c);}
  var t=document.createElement('span');t.textContent=n.type==='ref'?(nodes[n.target]?code(nodes[n.target]):n.text):n.text;d.appendChild(t);
  fo.appendChild(d);
}
function pathD(pts){return pts.map(function(p,i){return(i?'L':'M')+p[0]+' '+p[1];}).join(' ');}
/* 교차점 다리(2026-10-06 사용자 요청) — 가로 선분이 다른 선의 세로 선분을 가로지르는 곳에서 가로 선이 작은 반원(반지름 HOP)으로 넘어가게 그립니다.
   합쳐지는 것이 아니라 지나가는 것임을 보이기 위해서입니다. 선 경로는 그대로이고 그리기만 바뀝니다. 꺾이는 점·끝점 가까이의 교차는 건너뜁니다. */
var HOP=5,VSEG=[]; // SLANT(평행사변형 기울기)는 맨 위 크기 상수 옆
// 같은 점이 겹치거나 한 줄로 이어지는 점은 합칩니다 — 교차점 위에 점이 하나 더 찍혀 선분이 쪼개지면 교차가 끝점으로 보여 다리가 빠지기 때문입니다
function simplePts(p){var o=[];p.forEach(function(q){var n=o.length;if(n&&Math.abs(o[n-1][0]-q[0])<0.5&&Math.abs(o[n-1][1]-q[1])<0.5)return;
  if(n>=2){var a=o[n-2],b=o[n-1];if((Math.abs(a[0]-b[0])<0.5&&Math.abs(b[0]-q[0])<0.5)||(Math.abs(a[1]-b[1])<0.5&&Math.abs(b[1]-q[1])<0.5)){o[n-1]=q;return;}}o.push(q);});return o;}
function collectV(){VSEG=[];views.forEach(function(v){v._conns.forEach(function(c){var p=simplePts(c.pts);for(var i=0;i<p.length-1;i++){var a=p[i],b=p[i+1];if(Math.abs(a[0]-b[0])<0.5&&Math.abs(a[1]-b[1])>0.5)VSEG.push({x:a[0],y1:Math.min(a[1],b[1]),y2:Math.max(a[1],b[1]),c:c});}});});}
function hopPath(c){var p=simplePts(c.pts),d='M'+p[0][0]+' '+p[0][1];
  for(var i=1;i<p.length;i++){var a=p[i-1],b=p[i];
    if(Math.abs(a[1]-b[1])<0.5&&Math.abs(a[0]-b[0])>0.5){var y=a[1],lo=Math.min(a[0],b[0]),hi=Math.max(a[0],b[0]),dir=b[0]>a[0]?1:-1;
      var xs=VSEG.filter(function(s){return s.c!==c&&s.x>lo+HOP+2&&s.x<hi-HOP-2&&y>s.y1+HOP&&y<s.y2-HOP;}).map(function(s){return s.x;});
      xs=xs.filter(function(x,k){return xs.indexOf(x)===k;}).sort(function(m,n){return(m-n)*dir;});
      // 12px 안에 붙은 교차는 하나로 묶어 긴 다리(높이는 HOP 그대로인 납작한 반원) 하나로 넘습니다(2026-10-06 사용자 확정 — 이전에는 두 번째 교차를 건너뜀)
      var grp=[];xs.forEach(function(x){var g=grp[grp.length-1];if(g&&Math.abs(x-g[g.length-1])<HOP*2+2)g.push(x);else grp.push([x]);});
      grp.forEach(function(g){var x0=g[0]-dir*HOP,x1=g[g.length-1]+dir*HOP,rx=Math.abs(x1-x0)/2;d+=' L'+x0+' '+y+' A'+rx+' '+HOP+' 0 0 '+(dir>0?1:0)+' '+x1+' '+y;});}
    d+=' L'+b[0]+' '+b[1];}
  return d;}
function kindClass(k){return k==='yes'?'is-yes':k==='no'?'is-no':'is-normal';}
/* ---------- 연결선 경로 ----------
   흐름도 작성 규칙 §5 — 연결선은 서로 겹치지 않습니다. 한 도형에서 나가는 선은 저마다 다른 점에서 출발하고(조건은 오른쪽·아래·위 꼭짓점, 그 밖은 오른쪽 면을 나눠),
   들어오는 선도 서로 다른 점으로 들어옵니다(왼쪽 면을 나눠 · 같은 열의 도형은 위·아래 면). 선마다 후보 경로(열 사이 통로 · 행 사이 통로 · 섹션 아래 통로)를
   차례로 보며 도형을 지나지 않고 이미 그린 선과 같은 줄에서 포개지거나 맞닿지 않는 첫 경로를 고릅니다. */
var RT={h:{},v:{}},routeFails=0,failed=[],GROW={},NOSHIFT={},layoutStats=null;
function segsOf(pts){var s=[];for(var i=0;i<pts.length-1;i++){var a=pts[i],b=pts[i+1];if(Math.abs(a[0]-b[0])<0.5&&Math.abs(a[1]-b[1])<0.5)continue;if(Math.abs(a[1]-b[1])<0.5)s.push({o:'h',c:a[1],a:Math.min(a[0],b[0]),b:Math.max(a[0],b[0])});else s.push({o:'v',c:a[0],a:Math.min(a[1],b[1]),b:Math.max(a[1],b[1])});}return s;}
/* 평행한 두 선은 CLEAR(12px) 안으로 붙지 않습니다 — 그보다 가까우면 한 선처럼 보여 겹친 것으로 봅니다. 통로 줄·출발·도착점 간격도 이에 맞춥니다. */
var CLEAR=12,STEP=14;
function rk(c){return Math.round(c/CLEAR);}
function clash(ss){return ss.some(function(s){var m=RT[s.o];for(var k=rk(s.c)-1;k<=rk(s.c)+1;k++){var L=m[k];if(L&&L.some(function(t){return Math.abs(t.c-s.c)<CLEAR&&Math.min(t.b,s.b)-Math.max(t.a,s.a)>-CLEAR;}))return true;}return false;});}
function commitSegs(ss){ss.forEach(function(s){(RT[s.o][rk(s.c)]=RT[s.o][rk(s.c)]||[]).push(s);});return ss;}
function uncommit(c){(c._segs||[]).forEach(function(s){var L=RT[s.o][rk(s.c)],i=L?L.indexOf(s):-1;if(i>=0)L.splice(i,1);});c._segs=null;if(c.lab){var j=LB.indexOf(c.lab);if(j>=0)LB.splice(j,1);}}
function hitsBox(ss,boxes,skip){return ss.some(function(s){return boxes.some(function(b){if(b.n===skip[0]||b.n===skip[1])return false;return s.o==='h'?(s.c>b.y1-4&&s.c<b.y2+4&&s.b>b.x1-4&&s.a<b.x2+4):(s.c>b.x1-4&&s.c<b.x2+4&&s.b>b.y1-4&&s.a<b.y2+4);});});}
function chans(lo,hi){var c=(lo+hi)/2,o=[];if(hi-lo<2*CLEAR)return o;o.push(c);for(var d=STEP;c-d>=lo+CLEAR||c+d<=hi-CLEAR;d+=STEP){if(c+d<=hi-CLEAR)o.push(c+d);if(c-d>=lo+CLEAR)o.push(c-d);}return o;}
function near(list,t){return list.slice().sort(function(a,b){return Math.abs(a-t)-Math.abs(b-t);});}
function sideX(n,side,dy){var hw=n._w/2;if(n.type==='decision')hw=n._w/2*Math.max(0,1-Math.abs(dy)/(n._h/2));
  /* 평행사변형(입력·출력)은 변이 기울어 있어 그 높이의 실제 변 위치에서 나가고 들어옵니다 — 오른쪽 변은 위가 바깥·아래가 11px 안쪽, 왼쪽 변은 반대(2026-10-06 사용자 요청: 선이 도형에 닿지 않던 것) */
  if(n.type==='input'||n.type==='output'){var t=Math.max(0,Math.min(1,(dy+n._h/2)/n._h));return side==='r'?n._cx+hw-SLANT*t:n._cx-hw+SLANT*(1-t);}
  return side==='r'?n._cx+hw:n._cx-hw;}
function spread(n,i,k){return k===1?0:(i-(k-1)/2)*Math.min(n._step||18,(n._h-(n.type==='decision'?n._h/2:16))/Math.max(1,k-1));} // 라벨 선이 있는 도형은 28px 간격
function colL(v,r){return v._x+G.PADL+colAt(v,r)+20;}
function colR(v,r){return colL(v,r)+G.W;}
function byKey(list,f){var m={},o=[];list.forEach(function(x){var k=f(x);if(!m[k]){m[k]=[];o.push(m[k]);}m[k].push(x);});return o;}
function routeAll(){
  RT={h:{},v:{}};LB=[];routeFails=0;failed=[];buildLanes();
  views.forEach(function(v){
    v._boxes=v.ids.map(function(i){var n=v.inst[i];return{x1:n._cx-n._w/2,y1:n._cy-n._h/2,x2:n._cx+n._w/2,y2:n._cy+n._h/2,n:n};});
    v._gaps=rowGaps(v);v._corr=[];for(var k=0;k<v._nb+v._nc+3;k++){var cy=v._y+v._h-v._uiH-G.BACK-6-k*STEP;v._gaps.push(cy);v._corr.push(cy);}
  });
  /* 출발점·도착점은 모든 섹션의 선을 모아 한 번에 나눕니다 — 섹션 첫 도형에 부모 섹션 선과 섹션 안 선이 함께 들어와도 점이 겹치지 않게. */
  var conns=[];
  views.forEach(function(v){
    v._edges.forEach(function(e){conns.push({e:e,v:v,bv:v,a:v.inst[e.from],b:v.inst[e.to],line:false});});
    v.lines.forEach(function(L){conns.push({e:L.e,v:v,bv:L.view,a:v.inst[L.from],b:L.view.inst[L.to],line:true});});
  });
  conns.forEach(function(c){c.same=!c.line&&c.b._rank===c.a._rank;});
  {
    /* 출발점 */
    byKey(conns,function(c){return c.v.key+'|'+c.a.id;}).forEach(function(list){
      var a=list[0].a;
      var att=list.filter(function(c){return c.b._attach==='d'||c.b._attach==='u';}); // 위·아래에 붙인 연결자는 그 면 가운데(조건은 꼭짓점)에서 곧게
      att.forEach(function(c){c.dir=c.b._attach;c.S=[a._cx,c.dir==='d'?a._cy+a._h/2:a._cy-a._h/2];});
      if(att.length)list=list.filter(function(c){return att.indexOf(c)<0;});
      if(a.type==='decision'){var used={},extra=0,c2=function(c){return c.line?99:(c.b._rank>=a._rank?c.b._rank-a._rank:50+a._rank-c.b._rank);};
        att.forEach(function(c){used[c.dir]=1;});
        // 데이터가 연결에 exit(r·d·u)를 주면 그 꼭짓점에서 나갑니다(2026-10-06 사용자 요청 — 자동 배정이 선끼리 겹칠 때)
        var vx=function(d){return d==='r'?[sideX(a,'r',0),a._cy]:d==='d'?[a._cx,a._cy+a._h/2]:[a._cx,a._cy-a._h/2];};
        list=list.filter(function(c){var d=c.e.exit;if(!/^[rdu]$/.test(d||'')||used[d])return true;used[d]=1;c.dir=d;c.S=vx(d);return false;});
        list.forEach(function(c){c.grp=list;}); // 오른쪽에 쌓은 연결자 묶음(rs)
        list.slice().sort(function(p,q){var gp=c2(p),gq=c2(q);return Math.abs(p.b._cy-a._cy)-Math.abs(q.b._cy-a._cy)||gp-gq;}).forEach(function(c){ // 같은 행에서 가장 가까운(열 차이가 작은) 도착이 오른쪽 꼭짓점
          var dy=c.b._cy-a._cy,pref=Math.abs(dy)<4&&!c.same?['r','d','u']:dy>0?['d','r','u']:['u','r','d'],d=pref.filter(function(p){return !used[p];})[0];
          if(!d){extra++;var oy=(extra%2?1:-1)*Math.ceil(extra/2)*18;c.dir='r';c.S=[sideX(a,'r',oy),a._cy+oy];return;}
          used[d]=1;c.dir=d;c.S=d==='r'?[a._cx+a._w/2,a._cy]:d==='d'?[a._cx,a._cy+a._h/2]:[a._cx,a._cy-a._h/2];});
      }else{list.sort(function(p,q){return p.b._cy-q.b._cy;});list.forEach(function(c,i){var dy=spread(a,i,list.length);c.dir='r';c.S=[sideX(a,'r',dy),a._cy+dy];c.grp=list;});}
    });
    /* 도착점 — 왼쪽 면은 출발 높이 순으로 나눠 들어오고, 같은 열(위·아래로 쌓인 도형)에서 오는 선은 위·아래 면의 가운데 왼쪽으로 들어옵니다. */
    byKey(conns,function(c){return c.bv.key+'|'+c.b.id;}).forEach(function(list){
      var b=list[0].b,left=list.filter(function(c){return !c.same;}),top=list.filter(function(c){return c.same&&c.a._cy<b._cy;}),bot=list.filter(function(c){return c.same&&c.a._cy>b._cy;});
      left.sort(function(p,q){return p.S[1]-q.S[1];});left.forEach(function(c,i){var dy=spread(b,i,left.length);c.T=[sideX(b,'l',dy),b._cy+dy];c.end='l';});
      top.forEach(function(c,i){if(top.length===1&&c.dir==='d'){c.T=[c.S[0],b._cy-b._h/2];c.end='t';return;} // 바로 위 조건의 아래 꼭짓점에서 오는 선 하나는 가운데로 받아 곧게
        c.T=[b._cx-24-i*18,b._cy-b._h/2+(b.type==='decision'?b._h*(24+i*18)/b._w:0)];c.end='t';});
      bot.forEach(function(c,i){if(bot.length===1&&c.dir==='u'&&c.b._attach){c.T=[c.S[0],b._cy+b._h/2];c.end='b';return;} // 아래 조건 위에 붙인 연결자는 뾰족한 끝으로 곧게
        c.T=[b._cx-24-i*18,b._cy+b._h/2-(b.type==='decision'?b._h*(24+i*18)/b._w:0)];c.end='b';});
    });
  }
  views.forEach(function(v){v._conns=[];});
  conns.sort(function(p,q){return (p.line-q.line)||(Math.abs(p.b._rank-p.a._rank-1)-Math.abs(q.b._rank-q.a._rank-1));});
  conns.forEach(function(c){c.pts=findRoute(c);commitRoute(c);c.v._conns.push(c);});
  /* 점 순서 맞추기 — 들어오는 점은 선이 실제로 다가오는 높이(마지막 꺾임 전) 순으로, 나가는 점은 선이 향하는 높이(첫 꺾임 뒤) 순으로 다시 나눕니다.
     아래에서 올라오는 선이 아래 점을, 위로 가는 선이 위 점을 써야 같은 도형에 드나드는 선끼리 교차하지 않습니다. 순서가 바뀐 선만 다시 찾습니다. */
  var redo=[];
  byKey(conns.filter(function(c){return c.end==='l';}),function(c){return c.bv.key+'|'+c.b.id;}).forEach(function(list){if(list.length<2)return;
    var ys=list.map(function(c){return c.T[1];}).sort(function(a,b){return a-b;}),xs={};list.forEach(function(c){xs[c.T[1]]=c.T[0];});
    list.slice().sort(function(p,q){var a=p.pts.length>=3?p.pts[p.pts.length-3][1]:p.S[1],b=q.pts.length>=3?q.pts[q.pts.length-3][1]:q.S[1];return a-b;}).forEach(function(c,i){if(c.T[1]!==ys[i]){c.T=[sideX(c.b,'l',ys[i]-c.b._cy),ys[i]];if(redo.indexOf(c)<0)redo.push(c);}});});
  byKey(conns.filter(function(c){return c.dir==='r'&&c.a.type!=='decision';}),function(c){return c.v.key+'|'+c.a.id;}).forEach(function(list){if(list.length<2)return;
    var ys=list.map(function(c){return c.S[1];}).sort(function(a,b){return a-b;});
    list.slice().sort(function(p,q){var a=p.pts.length>=3?p.pts[2][1]:p.T[1],b=q.pts.length>=3?q.pts[2][1]:q.T[1];return a-b;}).forEach(function(c,i){if(c.S[1]!==ys[i]){c.S=[sideX(c.a,'r',ys[i]-c.a._cy),ys[i]];if(redo.indexOf(c)<0)redo.push(c);}});});
  redo.forEach(uncommit);redo.forEach(function(c){c.failed=false;c.pts=findRoute(c);commitRoute(c);});
  /* 점 순서 고르기 — 같은 도형에 2~4개 선이 드나들면 점 배정 순서를 모두 시험해(선만 다시 찾음) 교차가 가장 적은 순서를 씁니다. 지금 순서도 후보라 나빠지지 않습니다. */
  function perms(a){if(a.length<2)return[a];var o=[];a.forEach(function(x,i){perms(a.slice(0,i).concat(a.slice(i+1))).forEach(function(r){o.push([x].concat(r));});});return o;}
  function trySlots(list,key,pool){
    var slots=pool||list.map(function(c){return c[key];}),orig=list.map(function(c){return{p:c.pts,lab:c.lab,s:c[key]};});
    list.forEach(uncommit);
    var base=0;list.forEach(function(c){base+=routeScore(c,c.pts);commitRoute(c);});list.forEach(uncommit); // 묶음 안 선끼리의 교차도 셉니다
    var best=null;
    perms(slots).map(function(pm){return pm.slice(0,list.length);}).forEach(function(perm){
      var cost=0,okAll=true,got=[];
      for(var i=0;i<list.length;i++){var c=list[i];c[key]=perm[i];var np=findRoute(c,false,true);if(!np){okAll=false;break;}c.pts=np;cost+=routeScore(c,np);commitRoute(c);got.push(c);}
      got.forEach(uncommit);
      if(okAll&&(!best||cost<best.cost))best={cost:cost,perm:perm};
    });
    if(best&&best.cost<base){list.forEach(function(c,i){c[key]=best.perm[i];var np=findRoute(c,false,true);if(!np){c[key]=orig[i].s;np=orig[i].p;c.lab=orig[i].lab;}c.pts=np;commitRoute(c);});}
    else list.forEach(function(c,i){c[key]=orig[i].s;c.pts=orig[i].p;c.lab=orig[i].lab;commitRoute(c);});
  }
  var rf0=routeFails,fl0=failed.length;
  conns.forEach(function(c){if(c.a.type==='decision')c.P={S:c.S,dir:c.dir};}); // 조건 도형 선만 꼭짓점 배정(P)을 따릅니다
  /* 조건 도형은 오른쪽·아래·위 꼭짓점 배정을 모두 시험해 예·아니오 선끼리(그리고 다른 선과) 덜 교차하는 배정을 씁니다. */
  byKey(conns.filter(function(c){return c.a.type==='decision'&&!c.failed&&!conns.some(function(x){return x.a===c.a&&(x.b._attach==='d'||x.b._attach==='u'||x.e.exit);});}),function(c){return c.v.key+'|'+c.a.id;}).forEach(function(list){
    if(list.length<2||list.length>3)return;var a=list[0].a;
    var pool=[{S:[a._cx+a._w/2,a._cy],dir:'r'},{S:[a._cx,a._cy+a._h/2],dir:'d'},{S:[a._cx,a._cy-a._h/2],dir:'u'}];
    if(list.some(function(c){uncommit(c);var x=routeScore(c,c.pts);commitRoute(c);return x>0;}))trySlots(list,'P',pool);});
  byKey(conns.filter(function(c){return c.end==='l'&&!c.failed;}),function(c){return c.bv.key+'|'+c.b.id;}).forEach(function(list){if(list.length>=2&&list.length<=4&&list.some(function(c){uncommit(c);var x=routeScore(c,c.pts);commitRoute(c);return x>0;}))trySlots(list,'T');});
  byKey(conns.filter(function(c){return c.dir==='r'&&c.a.type!=='decision'&&!c.failed&&c.b._attach!=='rs';}),function(c){return c.v.key+'|'+c.a.id;}).forEach(function(list){if(list.length>=2&&list.length<=4&&list.some(function(c){uncommit(c);var x=routeScore(c,c.pts);commitRoute(c);return x>0;}))trySlots(list,'S');});
  routeFails=rf0;failed.length=fl0;
  /* 교차 줄이기 — 한 선씩 그려 앞선 선이 뒤 선의 좋은 길을 막을 수 있으므로, 교차가 있는 선을 뽑아 나머지를 둔 채 다시 찾고 교차가 줄면 바꿉니다(2바퀴). */
  for(var round=0;round<2;round++)conns.forEach(function(c){
    if(c.failed)return;uncommit(c);var old=c.pts,oldLab=c.lab,before=routeScore(c,old);
    if(!before){commitRoute(c);return;}
    var rf=routeFails,fl=failed.length,np=findRoute(c,false,true);
    if(routeFails>rf||!np){routeFails=rf;failed.length=fl;c.pts=old;c.lab=oldLab;commitRoute(c);return;}
    if(routeScore(c,np)<before){c.pts=np;}else{c.pts=old;c.lab=oldLab;}commitRoute(c);
  });
  /* 끝점 맞바꾸기(2026-10-06 사용자 요청) — 같은 도형에 들어오는(또는 나가는) 두 선이 서로 가로지르면, 들어오는 점(나가는 점)을 맞바꿔 두 선을 다시 찾고
     둘 사이 교차가 사라지고 전체 교차가 늘지 않을 때만 바꿉니다. 앞의 점 순서 맞추기 뒤 다시 찾는 과정에서 순서가 뒤집혀 남는 교차를 마지막에 풉니다. */
  function pairX(p,q){var n=0;segsOf(p.pts).forEach(function(s){segsOf(q.pts).forEach(function(t){if(s.o===t.o)return;var h=s.o==='h'?s:t,v=s.o==='h'?t:s;if(v.c>h.a+1&&v.c<h.b-1&&h.c>v.a+1&&h.c<v.b-1)n++;});});return n;}
  function trySwap(p,q,key){var px=pairX(p,q);if(!px)return;
    var save=[p,q].map(function(c){return{pts:c.pts,lab:c.lab,k:c[key],P:c.P};});
    uncommit(p);uncommit(q);var before=routeScore(p,save[0].pts)+routeScore(q,save[1].pts);
    var t=p[key];p[key]=q[key];q[key]=t;if(key==='S'){p.P=null;q.P=null;}
    /* 먼저 경로는 그대로 두고 도형 바로 앞(뒤)의 꺾임만 새 점 높이로 옮겨 봅니다 — 선 전체를 다시 찾으면 다른 선과 새로 엇갈릴 수 있어서입니다. 안 되면 다시 찾습니다. */
    function edgeFit(c,pts){var bx=c.line?c.v._boxes.concat(c.bv._boxes):c.v._boxes,ss=segsOf(pts);return !hitsBox(ss,bx,[c.a,c.b])&&!clash(ss)&&!hitsLabel(ss)&&!nearLane(ss);}
    function shift(c,old){var n=old.length;if(n<3)return null;var o=old.map(function(x){return x.slice();});
      if(key==='T'){if(Math.abs(o[n-2][0]-o[n-3][0])>0.5||Math.abs(c.T[0]-o[n-2][0])<MIN_TAIL)return null;o[n-2]=[o[n-2][0],c.T[1]];o[n-1]=c.T.slice();}
      else{if(c.lw||Math.abs(o[1][0]-o[2][0])>0.5)return null;o[0]=c.S.slice();o[1]=[o[1][0],c.S[1]];}
      return edgeFit(c,o)?o:null;}
    var rf=routeFails,fl=failed.length;
    for(var mode=0;mode<2;mode++){ // 0: 꺾임만 옮기기 · 1: 다시 찾기 — 앞 방식이 채택되지 않으면 다음 방식
      var np=mode?findRoute(p,false,true):shift(p,save[0].pts),okp=!!np;if(okp){p.pts=np;commitRoute(p);}
      var nq=okp?(mode?findRoute(q,false,true):shift(q,save[1].pts)):null;if(nq){q.pts=nq;commitRoute(q);}
      var after=okp&&nq?routeScore(p,p.pts)+routeScore(q,q.pts):1e9;
      if(okp&&nq&&pairX(p,q)<px&&after<=before+px){routeFails=rf;failed.length=fl;return;} // 둘 사이 교차가 줄고 다른 선과의 교차가 늘지 않으면 채택
      if(okp)uncommit(p);if(nq)uncommit(q);routeFails=rf;failed.length=fl;}
    [p,q].forEach(function(c,i){c.pts=save[i].pts;c.lab=save[i].lab;c[key]=save[i].k;c.P=save[i].P;commitRoute(c);});}
  byKey(conns.filter(function(c){return c.end==='l'&&!c.failed;}),function(c){return c.bv.key+'|'+c.b.id;}).forEach(function(list){
    for(var i=0;i<list.length;i++)for(var j=i+1;j<list.length;j++)trySwap(list[i],list[j],'T');});
  byKey(conns.filter(function(c){return c.dir==='r'&&c.a.type!=='decision'&&!c.failed;}),function(c){return c.v.key+'|'+c.a.id;}).forEach(function(list){
    for(var i=0;i<list.length;i++)for(var j=i+1;j<list.length;j++)trySwap(list[i],list[j],'S');});
  ENDX=0; // 맞바꾼 뒤에도 같은 도형에 드나들며 서로 엇갈리는 선 쌍 수(layoutStats().endCross)
  byKey(conns.filter(function(c){return c.end==='l';}),function(c){return c.bv.key+'|'+c.b.id;}).concat(byKey(conns.filter(function(c){return c.dir==='r';}),function(c){return c.v.key+'|'+c.a.id;})).forEach(function(list){
    for(var i=0;i<list.length;i++)for(var j=i+1;j<list.length;j++)if(pairX(list[i],list[j]))ENDX++;});
}
var ENDX=0;
/* 선 라벨(예·아니오·계기) — 선이 시작되는 쪽 첫 선분 곁에 둡니다(오른쪽으로 나가면 선 위, 아래·위로 나가면 선 오른쪽).
   라벨도 도형·다른 선·다른 라벨과 겹치지 않아야 하므로, 첫 선분은 라벨 길이보다 길게 잡고(모자라면 섹션 간격을 넓혀 다시 배치),
   놓은 라벨은 뒤에 그리는 선이 피해 가는 장애물(LB)이 됩니다. */
var LB=[],measCtx=null;
function labelW(s){if(!measCtx){measCtx=document.createElement('canvas').getContext('2d');var ff=getComputedStyle(document.body).fontFamily||'sans-serif';measCtx.font='600 11px '+ff;}return Math.ceil(measCtx.measureText(String(s)).width)+14;}
/* 라벨 자리 — 선 옆이 아니라 선 위에 얹은 상자(선이 라벨을 지나감)로 둡니다. 나란한 선 사이에 라벨이 끼어 어느 선의 라벨인지 헷갈리지 않게(2026-10-01 사용자 요청). */
function labelRects(c,pts){var w=c.lw,S=pts[0],P=pts[1];if(Math.abs(S[1]-P[1])<0.5){var sx=Math.max(S[0],c.a._cx+c.a._w/2);return[{x1:sx+10,x2:sx+10+w,y1:S[1]-9,y2:S[1]+9,tx:sx+10+w/2,ty:S[1]+4}];} // 평행사변형의 기울어진 변에서 나가도 라벨은 도형 상자 바깥에서 시작
  var y1=P[1]>S[1]?S[1]+12:S[1]-30;return[{x1:S[0]-w/2,x2:S[0]+w/2,y1:y1,y2:y1+18,tx:S[0],ty:y1+13}];}
function rectFree(r,boxes){
  if(boxes.some(function(b){return r.x2>b.x1-2&&r.x1<b.x2+2&&r.y2>b.y1-2&&r.y1<b.y2+2;}))return false;
  if(LB.some(function(b){return r.x2>b.x1-4&&r.x1<b.x2+4&&r.y2>b.y1-2&&r.y1<b.y2+2;}))return false;
  for(var k=rk(r.y1)-1;k<=rk(r.y2)+1;k++)if((RT.h[k]||[]).some(function(s){return s.c>r.y1-3&&s.c<r.y2+3&&s.b>r.x1-3&&s.a<r.x2+3;}))return false;
  for(var k2=rk(r.x1)-1;k2<=rk(r.x2)+1;k2++)if((RT.v[k2]||[]).some(function(s){return s.c>r.x1-3&&s.c<r.x2+3&&s.b>r.y1-3&&s.a<r.y2+3;}))return false;
  return true;}
/* 이미 그린 선과 가로지르는 횟수 — 후보 가운데 교차가 가장 적은 경로를 고르는 데 씁니다(흐름도 작성 규칙 §5 교차 최소). */
function crossCount(ss){var n=0;ss.forEach(function(s){var m=RT[s.o==='h'?'v':'h'];for(var k=rk(s.a);k<=rk(s.b);k++){var L=m[k];if(L)L.forEach(function(t){if(t.c>s.a+1&&t.c<s.b-1&&s.c>t.a+1&&s.c<t.b-1)n++;});}});return n;}
function plen(p){var l=0;for(var i=0;i<p.length-1;i++)l+=Math.abs(p[i+1][0]-p[i][0])+Math.abs(p[i+1][1]-p[i][1]);return l;}
function hitsLabel(ss){return ss.some(function(s){return LB.some(function(r){return s.o==='h'?(s.c>r.y1-3&&s.c<r.y2+3&&s.b>r.x1-3&&s.a<r.x2+3):(s.c>r.x1-3&&s.c<r.x2+3&&s.b>r.y1-3&&s.a<r.y2+3);});});}
/* 경로 찾기 — 후보를 선분 하나씩 검사해 막히면 바로 다음 후보로 넘어갑니다(①한 번 꺾기 ②통로 세 번 꺾기 ③같은 열). */
function findRoute(c,full,retry,wide){
  if(c.P){c.S=c.P.S;c.dir=c.P.dir;}
  var v=c.v,a=c.a,b=c.b,S=c.S,T=c.T,boxes=c.line?v._boxes.concat(c.bv._boxes):v._boxes,first=null;
  c.lw=c.e.label?labelW(c.e.label):0;
  function ok(p,q){var ss=segsOf([p,q]);if(!ss.length)return true;return !hitsBox(ss,boxes,[a,b])&&!clash(ss)&&!hitsLabel(ss)&&!nearLane(ss);}
  /* 겹치지 않는 후보를 모아 교차 수(우선) · 꺾임 수 · 길이로 점수를 매기고, 교차 없는 후보가 나오면 바로, 아니면 40개까지 본 뒤 가장 나은 것을 고릅니다. */
  var best=null,cnt=0;
  /* 아래로 지나가기(passBelow · 2026-10-07 사용자 요청) — 연결에 도형 id 목록을 주면, 그 도형들의 가로 범위를 지나는 가로 선분을 모두 그 도형들 아래(CLEAR 이상)로 냅니다. 위쪽 통로로 가면 들어오고 나가는 선을 여럿 가로지를 때 씁니다. */
  var pbB=null;if(c.e.passBelow&&c.e.passBelow.length){var pbs=boxes.filter(function(x){return x.n&&c.e.passBelow.indexOf(x.n.id)>=0;});if(pbs.length)pbB={x1:Math.min.apply(null,pbs.map(function(x){return x.x1;})),x2:Math.max.apply(null,pbs.map(function(x){return x.x2;})),y:Math.max.apply(null,pbs.map(function(x){return x.y2;}))};}
  function belowOk(p){if(!pbB)return true;for(var i=1;i<p.length;i++){var A=p[i-1],B=p[i];if(Math.abs(A[1]-B[1])<1&&Math.max(A[0],B[0])>pbB.x1&&Math.min(A[0],B[0])<pbB.x2&&A[1]<pbB.y+CLEAR)return false;}return true;}
  function take(p){if(!belowOk(p)||!done(p))return false;var cx=crossCount(segsOf(p)),lv=laneVio(c,p),sc=(cx+LANE_W*lv)*100000+p.length*500+plen(p);cnt++;if(!best||sc<best.sc)best={p:p,lab:c.lab,sc:sc};return (cx===0&&lv===0)||cnt>=(wide?400:40);} // 넓혀 다시 찾을 때는 후보를 400개까지 봅니다
  /* 교차·구역 벗어남이 남은 경로는 통로 후보(가로 통로 전부)를 넓혀 한 번 더 찾고 더 나은 쪽을 씁니다(2026-10-06 사용자 요청 — 가까운 통로 14개만 보다 교차 없는 먼 통로를 놓치던 것) */
  function fin(){c.lab=best.lab;c._sc=best.sc;
    if(WIDE&&best.sc>=100000&&!full&&!wide){var keep={p:best.p,lab:best.lab,sc:best.sc},w=findRoute(c,false,retry,true);if(w&&c._sc<keep.sc)return w;c.lab=keep.lab;c._sc=keep.sc;return keep.p;}
    return best.p;}
  function done(pts){if(!c.lw)return pts;var bx=c.line?boxes:v._boxes,rs=labelRects(c,pts);for(var q=0;q<rs.length;q++)if(rectFree(rs[q],bx)){c.lab=rs[q];return pts;}return null;}
  /* 같은 세로줄(조건 아래 배치 등)로 곧게 내려가거나 올라가는 선은 꺾지 않습니다. */
  if(c.same&&Math.abs(S[0]-T[0])<1&&(c.dir==='d'||c.dir==='u')&&Math.abs(T[1]-S[1])>=(c.lw?40:MIN_TAIL)){var straight=[S,T];if(ok(S,T)&&take(straight))return fin();}
  /* 오른쪽에 붙인 연결자처럼 같은 높이 바로 옆으로 가는 선은 곧게 잇습니다 — 통로 후보가 그 짧은 틈에 없어 위로 돌아가던 것 막음(2026-10-06 사용자 지적). */
  if(c.dir==='r'&&c.end==='l'&&Math.abs(S[1]-T[1])<1&&T[0]-S[0]>=(c.lw?c.lw+20:6)){if(ok(S,T)&&take([S,T]))return fin();}
  /* 오른쪽에 쌓은 연결자(rs · 2026-10-07) — 묶음 안 선끼리 엇갈리지 않게 꺾는 x를 정해 둡니다. 연결자에서 먼 출발점(아래로 쌓으면 아래 점)일수록 도형 가까이에서 꺾고,
     가장 긴 라벨을 지난 뒤부터 16px씩 물러납니다. 그 길이 막히면 아래 일반 후보로 찾습니다. */
  if(c.b._attach==='rs'&&(c.dir==='d'||c.dir==='u')&&c.end==='l'&&Math.abs(T[1]-S[1])>=(c.lw?40:MIN_TAIL)&&T[0]-S[0]>=MIN_TAIL&&ok(S,[S[0],T[1]])&&ok([S[0],T[1]],T)&&take([S,[S[0],T[1]],T]))return fin(); // 조건의 아래·위 꼭짓점에서 나가면 한 번만 꺾어 곧게
  if(c.b._attach==='rs'&&c.dir==='r'&&c.end==='l'&&c.grp){var dn=b._cy>a._cy,mates=c.grp.filter(function(x){return x.b._attach==='rs'&&x.dir==='r'&&(x.b._cy>a._cy)===dn;});
    mates.sort(function(p,q){return dn?q.S[1]-p.S[1]:p.S[1]-q.S[1];});var Lm=mates.reduce(function(s,x){return Math.max(s,x.e.label?labelW(x.e.label):0);},0);
    var rx=a._cx+a._w/2+(Lm?Lm+26:12)+mates.indexOf(c)*16;
    if(rx<=T[0]-MIN_TAIL&&ok(S,[rx,S[1]])&&ok([rx,S[1]],[rx,T[1]])&&ok([rx,T[1]],T)){if(take([S,[rx,S[1]],[rx,T[1]],T]))return fin();if(best){c.lab=best.lab;c._sc=best.sc;return best.p;}}} // 교차가 하나 있어도 멀리 돌아가지 않고 바로 옆 길을 씁니다(교차는 다리로 그림)
  var needV=c.lw?40:8,needH=c.lw?c.lw+26:6,H0s=[S[1]];
  if(c.dir!=='r'){H0s=[];v._gaps.forEach(function(g){[0,-STEP,STEP,-2*STEP,2*STEP].forEach(function(d){var y=g+d;if(c.dir==='d'?(y>=S[1]+needV&&y<S[1]+v._rg+60):(y<=S[1]-needV&&y>S[1]-v._rg-60))H0s.push(y);});});H0s=near(H0s,S[1]);}
  var aHi=a._rank<v._maxRank?colL(v,a._rank+1):v._x+v._w-6,gapA=chans(Math.max(colR(v,a._rank),S[0]),aHi);
  var gapB;if(c.line)gapB=chans(v._x+v._wT+12,c.bv._x-12);else if(c.end==='l')gapB=chans(b._rank>0?colR(c.bv,b._rank-1):c.bv._x+24,T[0]-MIN_TAIL+CLEAR);else gapB=gapA;
  var ys=(full||wide)?near(v._gaps,(S[1]+T[1])/2):near(v._gaps,(S[1]+T[1])/2).slice(0,14),gA=full?gapA.slice(0,40):gapA.slice(0,10),gB=full?gapB.slice(0,40):gapB.slice(0,10); // 후보 수 제한(넓힘으로 해결 · 넓힌 섹션도 통로 후보는 가운데부터 40개까지 — 열 사이가 아주 넓어지면 전체를 보느라 멈추던 것 막음) · 섹션 아래 통로는 늘 후보
  if(c.line&&(c.dir==='d'||c.dir==='u')&&gA.indexOf(S[0])<0)gA.unshift(S[0]); // 자식 섹션 선은 꼭짓점에서 곧게 내려가 통로로(열 사이를 쓰지 않음 · 2026-10-06)
  v._corr.forEach(function(y){if(ys.indexOf(y)<0)ys.push(y);});
  if(pbB)[CLEAR*2,CLEAR*2+STEP,CLEAR*2+2*STEP,CLEAR*2+4*STEP].forEach(function(d){var y=pbB.y+d;if(ys.indexOf(y)<0)ys.unshift(y);}); // 아래로 지나가기 — 도형 아래 가로 통로 후보
  if(!full)H0s=H0s.slice(0,6);
  for(var h=0;h<H0s.length;h++){
    var H0=H0s[h],X0=S[0],st=c.dir==='r'?[S]:[S,[X0,H0]];
    if(c.dir!=='r'&&!ok(S,[X0,H0]))continue;
    var minX=X0+(c.dir==='r'?needH:6);
    if(c.end==='l'){
      for(var i=0;i<gapB.length;i++){var cb=gapB[i];if(cb<minX)continue;
        if(ok([X0,H0],[cb,H0])&&ok([cb,H0],[cb,T[1]])&&ok([cb,T[1]],T)){var p=st.concat([[cb,H0],[cb,T[1]],T]);if(!first)first=p;if(take(p))return fin();}}
      for(var i2=0;i2<gA.length;i2++){var ca=gA[i2];if(ca<minX||!ok([X0,H0],[ca,H0]))continue;
        for(var j=0;j<ys.length;j++){var y=ys[j];if(!ok([ca,H0],[ca,y]))continue;
          for(var k=0;k<gB.length;k++){var cb2=gB[k];if(ok([ca,y],[cb2,y])&&ok([cb2,y],[cb2,T[1]])&&ok([cb2,T[1]],T)){var p2=st.concat([[ca,H0],[ca,y],[cb2,y],[cb2,T[1]],T]);if(!first)first=p2;if(take(p2))return fin();}}}}
    }else{
      var yy=[];v._gaps.forEach(function(g){if(c.end==='t'?(g<T[1]-6&&g>T[1]-v._rg-30):(g>T[1]+6&&g<T[1]+v._rg+30))[0,-STEP,STEP].forEach(function(d){yy.push(g+d);});});yy=yy.filter(function(y){return Math.abs(T[1]-y)>=MIN_TAIL;});yy=near(yy,c.end==='t'?T[1]-v._rg/2:T[1]+v._rg/2);
      for(var i3=0;i3<gA.length;i3++){var ca3=gA[i3];if(ca3<minX||!ok([X0,H0],[ca3,H0]))continue;
        for(var j3=0;j3<yy.length;j3++){if(ok([ca3,H0],[ca3,yy[j3]])&&ok([ca3,yy[j3]],[T[0],yy[j3]])&&ok([T[0],yy[j3]],T)){var p3=st.concat([[ca3,H0],[ca3,yy[j3]],[T[0],yy[j3]],T]);if(!first)first=p3;if(take(p3))return fin();}}}
    }
  }
  if(best)return fin();
  if(!full)return findRoute(c,true,retry); // 막힌 선만 후보 전부로 한 번 더
  if(retry)return null;
  routeFails++;failed.push(c);c.failed=true;var fb=first||[S,T];if(c.lw)c.lab=labelRects(c,fb)[0];return fb;
}
/* 구역 테두리(2026-10-06 사용자 요청) — 선이 유저·시스템·UI 구역 테두리 위를 따라가면 테두리와 겹쳐 보이므로, 테두리와 12px(CLEAR) 안에서 나란히 가는 선분은
   놓지 않습니다. 테두리를 가로지르는 것은 그대로 허용하고, 테두리는 교차 수 계산(crossCount)에 넣지 않습니다. */
var LANES={h:{},v:{}};
function buildLanes(){LANES={h:{},v:{}};function add(o,c,a,b){(LANES[o][rk(c)]=LANES[o][rk(c)]||[]).push({c:c,a:a,b:b});}
  views.forEach(function(v){var x1=v._x+10,x2=v._x+v._wT-10;
    v._laneY.forEach(function(y,i){var y2=y+v._laneH[i];add('h',y,x1,x2);add('h',y2,x1,x2);add('v',x1,y,y2);add('v',x2,y,y2);});
    if(v._uiH){var u=v._y+v._h-v._uiH,u2=u+v._uiH-10,ux=v._x+v._w-10;add('h',u,x1,ux);add('h',u2,x1,ux);add('v',x1,u,u2);add('v',ux,u,u2);}});}
function nearLane(ss){return ss.some(function(s){var m=LANES[s.o];for(var k=rk(s.c)-1;k<=rk(s.c)+1;k++){var L=m[k];if(L&&L.some(function(t){return Math.abs(t.c-s.c)<CLEAR&&Math.min(t.b,s.b)-Math.max(t.a,s.a)>0;}))return true;}return false;});}
/* 자기 구역 지키기(2026-10-06 사용자 요청) — 같은 구역의 도형끼리 잇는 선(시스템 → 시스템 등)은 다른 구역 안으로 들어가지 않습니다. 구역 아래 통로는 다른 구역이 아니라 씁니다.
   길이 아예 없을 때 막히지 않도록 거절 대신 큰 감점(LANE_W · 교차 20곳)으로 다룹니다. */
function laneVio(c,pts){if(!c.a||!c.b||c.a.lane!==c.b.lane)return 0;
  if(!c._forb){c._forb=[];[c.v,c.bv].forEach(function(v,k){if(!v||(k&&v===c.v))return;lanes.forEach(function(l,li){if(l.key===c.a.lane)return;
    c._forb.push({x1:v._x+10,x2:v._x+v._wT-10,y1:v._laneY[li],y2:v._laneY[li]+v._laneH[li]});});});}
  var n=0;segsOf(pts).forEach(function(s){c._forb.forEach(function(r){if(s.o==='h'?(s.c>r.y1&&s.c<r.y2&&s.a<r.x2&&s.b>r.x1):(s.c>r.x1&&s.c<r.x2&&s.a<r.y2&&s.b>r.y1))n++;});});return n;}
var LANE_W=20; // 구역 벗어남 1회 = 교차 20곳 — 길이 아예 없을 때만 벗어남(2026-10-06 · 2 → 20)
function routeScore(c,pts){return crossCount(segsOf(pts))+LANE_W*laneVio(c,pts);}
/* 넓혀 다시 찾기(2026-10-06) — 배치가 끝난 뒤 교차·구역 벗어남이 남은 선만 가로 통로 후보 전부·후보 400개까지 보고 다시 찾아, 점수가 나아질 때만 바꿉니다.
   섹션을 넓혀 다시 배치할 때마다 하면 오래 걸려 마지막에 한 번만 합니다. */
function wideSweep(){var all=[];views.forEach(function(v){all=all.concat(v._conns);});
  all.forEach(function(c){if(c.failed)return;uncommit(c);var old=c.pts,oldLab=c.lab,before=routeScore(c,old);if(!before){commitRoute(c);return;}
    var rf=routeFails,fl=failed.length,np=findRoute(c,false,true,true);
    if(routeFails>rf||!np){routeFails=rf;failed.length=fl;c.pts=old;c.lab=oldLab;commitRoute(c);return;}
    if(routeScore(c,np)<before){c.pts=np;}else{c.pts=old;c.lab=oldLab;}commitRoute(c);});}
function commitRoute(c){c._segs=commitSegs(segsOf(c.pts));if(c.lab)LB.push(c.lab);}
function edgeLabel(c,g){if(!c.e.label||!c.lab)return;var r=c.lab;el('rect',{x:r.x1,y:r.y1,width:r.x2-r.x1,height:r.y2-r.y1,rx:9,class:'wfx-edge-label-bg '+kindClass(c.e.kind)},g);var tx=el('text',{x:r.tx,y:r.ty,class:'wfx-edge-label '+kindClass(c.e.kind),'text-anchor':'middle'},g);tx.textContent=c.e.label;}
/* 먼 복귀 연결자 동작 — 마우스를 올리면 도착 도형에 테두리를 켜고 표식에서 도착 도형까지 흐린 점선을 잠깐 긋습니다(미리 보기).
   누르면 지금 위치가 출발 도형이면 그 연결을 고른 것처럼 한 걸음 나아가고(직전 동작 = 출발 도형), 아니면 도착 도형을 누른 것과 같습니다. 도착 도형은 잠깐 깜빡입니다. */
function linkEvents(n,lg){
  var ghost=null;
  /* 미리 보기 선 — 들어오는 선의 색(예·아니오·일반) 3px 점선 · 아래에 화면색 띠(다른 선과 겹쳐도 위에 떠 보이게) · 도착 쪽 화살표(2026-10-02 사용자 확정) */
  var kc=kindClass(n.kind);
  function peek(on){var te=nodeEls[n.target];if(te){te.classList.toggle('is-peek',on);te.classList.toggle('peek-'+kc,on);}
    moveBlock(lg,on,moveInfo(n.target,n.subr?null:n.from,!n.subr&&n.sym!=='→',n.subr?'':n.label),n.subr?n.title+' 하위 섹션 열기':'');
    if(ghost){ghost.remove();ghost=null;}
    if(on){var t=nodes[n.target],d='M'+n._cx+' '+(n._cy+n._h/2)+' L'+t._cx+' '+(t._cy+t._h/2+4);ghost=el('g',{class:'wfx-link-ghost-g'},view);
      el('path',{d:d,class:'wfx-link-ghost-bg'},ghost);el('path',{d:d,class:'wfx-link-ghost '+kc,'marker-end':'url(#wfx-arrow-'+(n.kind||'normal')+')'},ghost);}}
  function go(ev){ev.stopPropagation();peek(false);pushJump(n);
    var orig=(inc[n.id]||[])[0];orig=orig&&orig.orig;
    if(orig&&(S.pos===n.from||S.pos===orig.from))take(orig);else select(n.target);
    focusNode(n.target,true);openDock();
    var te=nodeEls[n.target];if(te){te.classList.remove('is-flash');void (te.els[0]&&te.els[0].getBoundingClientRect());te.classList.add('is-flash');setTimeout(function(){te.classList.remove('is-flash');},1400);}}
  lg.addEventListener('mouseenter',function(){peek(true);});lg.addEventListener('mouseleave',function(){peek(false);});
  lg.addEventListener('focus',function(){peek(true);});lg.addEventListener('blur',function(){peek(false);});
  lg.addEventListener('click',go);lg.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();go(ev);}});
}
/* 하위 섹션 제목의 「↑ 여는 곳」 — 이 하위 섹션을 여는 서브루틴(정의상 하나)으로 갑니다. 실제로 지나온 곳은 왼쪽 아래 「← 이전 위치로」가 맡습니다. */
function subUp(v,g){var h=nodes[v.sub.hub],sr='sr:'+v.sub.key,a=el('g',{class:'wfx-sub-up',role:'button',tabindex:0,'aria-label':code(h)+' '+oneLine(h.text)+'의 서브루틴으로 가기'},g);
  var tx=el('text',{x:v._x+v._wT-16,y:v._y+31,'text-anchor':'end'},a);tx.textContent='↑ '+code(h)+' '+oneLine(h.text).replace(/^\[[^\]]*\]\s*/,'');
  el('title',{},a).textContent='이 하위 섹션을 여는 서브루틴으로 갑니다';
  function go(ev){ev.stopPropagation();var hv=v.host,p=hv&&hv.inst[sr];if(!p)return;JUMPS.push({tf:{x:tf.x,y:tf.y,k:tf.k},id:null,label:'↓ '+v.sub.title});renderBack();
    var r=svg.getBoundingClientRect();if(tf.k<0.7)tf.k=0.85;tf.x=r.width/2-p._cx*tf.k;tf.y=r.height/2-p._cy*tf.k;apply();
    var e=document.querySelector('[data-linkid="'+sr+'"]');if(e){e.classList.remove('is-flash');void e.getBoundingClientRect();e.classList.add('is-flash');setTimeout(function(){e.classList.remove('is-flash');},1400);}}
  a.addEventListener('click',go);a.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();go(ev);}});}
/* 이전 오각형으로 돌아가기(2026-10-02 사용자 요청) — 오각형·서브루틴을 눌러 화면이 옮겨 가면, 누르기 전 화면 위치를 쌓아 두고 흐름도 왼쪽 아래에
   「← 이전 오각형으로」 버튼을 띄웁니다. 누르면 그 위치로 돌아가 눌렀던 오각형을 깜빡입니다. 여러 번 옮겨 갔으면 한 번에 하나씩 거슬러 올라갑니다. */
var JUMPS=[];
function pushJump(n){JUMPS.push({tf:{x:tf.x,y:tf.y,k:tf.k},id:n.id,label:n.subr?'┃'+code(n)+' '+oneLine(n.text)+'┃':'⬠ '+(n.sym||'↩')+' '+code(n)});renderBack();}
function renderBack(){var c=document.getElementById('wfx-canvas');if(!c)return;var b=document.getElementById('wfx-back');
  if(!b){b=document.createElement('button');b.type='button';b.id='wfx-back';b.className='wfx-back';b.addEventListener('click',goBack);c.parentNode.appendChild(b);}
  var j=JUMPS[JUMPS.length-1];b.hidden=!j;if(j)b.textContent='← 이전 위치로 · '+j.label+(JUMPS.length>1?' (+'+(JUMPS.length-1)+')':'');}
function goBack(){var j=JUMPS.pop();if(!j)return;tf={x:j.tf.x,y:j.tf.y,k:j.tf.k};apply();
  var e=j.id&&document.querySelector('[data-linkid="'+j.id+'"]');if(e){e.classList.remove('is-flash');void e.getBoundingClientRect();e.classList.add('is-flash');setTimeout(function(){e.classList.remove('is-flash');},1400);}
  renderBack();}
function render(){
  /* 선을 겹치지 않게 놓지 못하면 그 선이 지나는 섹션(출발·도착)의 열·행 간격을 넓혀 다시 배치합니다(최대 6번). 한 번 넓혀도 막히면 그 열 사이에 붙인 연결자를 떼어 다음 열 자리로 돌립니다. */
  var t0=Date.now();GROW={};NOSHIFT={};var LGROW={};for(var it=0;it<6;it++){layout();routeAll();
    if(!routeFails){ // 같은 구역 선이 다른 구역으로 넘어갔으면 그 섹션을 한 번 넓혀 다시 배치합니다(구역 안 길을 만들 틈 · 2026-10-06)
      var lv=[];views.forEach(function(v){v._conns.forEach(function(c){if(laneVio(c,c.pts)>0&&!LGROW[c.v.key]){LGROW[c.v.key]=1;lv.push(c.v.key);}});});
      if(!lv.length||it>=5)break;lv.forEach(function(k){GROW[k]=(GROW[k]||0)+1;});continue;}var grown=Object.assign({},GROW);failed.forEach(function(c){if(grown[c.v.key]){if(c.line)NOSHIFT[c.v.key+'|'+c.a._rank]=1;else for(var r=Math.min(c.a._rank,c.b._rank);r<=Math.max(c.a._rank,c.b._rank);r++)NOSHIFT[c.v.key+'|'+r]=1;}GROW[c.v.key]=(GROW[c.v.key]||0)+1;if(c.bv!==c.v)GROW[c.bv.key]=(GROW[c.bv.key]||0)+1;});}
  wideSweep();
  layoutStats={ms:Date.now()-t0,passes:it+1,fails:routeFails,endCross:ENDX,laneOut:(typeof laneVio==='function'?views.reduce(function(n,v){return n+v._conns.filter(function(c){return laneVio(c,c.pts)>0;}).length;},0):-1),failed:failed.map(function(c){return code(c.a)+'>'+code(c.b)+(c.line?' line':'')+(c.same?' same':'')+' '+c.dir+(c.lw?' L'+c.lw:'')+' r'+c.a._rank+'>'+c.b._rank;})};
  edgeEls={};nodeEls={};chipEls={};
  var host=document.getElementById('wfx-canvas');host.innerHTML='';
  svg=el('svg',{class:'wfx-svg',width:'100%',height:'100%'});host.appendChild(svg);
  var defs=el('defs',{},svg);
  ['normal','yes','no','path'].forEach(function(k){var m=el('marker',{id:'wfx-arrow-'+k,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'},defs);el('path',{d:'M0 0L10 5L0 10z',class:'wfx-arrow is-'+k},m);});
  view=el('g',{class:'wfx-view'},svg);
  collectV(); // 교차점 다리용 세로 선분 모음
  var secG=el('g',{},view),crossG=el('g',{class:'wfx-cross'},view),topG=el('g',{},view);
  views.forEach(function(v){
    var g=el('g',{class:'wfx-flow'+(v.cont?' is-cont':''),'data-flow':v.sec.flow.code,'data-section':v.key},secG);
    el('rect',{x:v._x,y:v._y,width:v._wT,height:v._hT,rx:10,class:'wfx-section'+(v.sub?' is-sub':'')},g);
    var t=el('text',{x:v._x+16,y:v._y+33,class:'wfx-section-title'},g);if(v.sub)subUp(v,g);t.textContent=v.sub?v.sub.title:v.sec.key+' · '+v.sec.title+(v.cont?' · '+code(nodes[v.entry])+'부터':'');if(v.sub)t.setAttribute('class','wfx-section-title is-sub');
    lanes.forEach(function(l,i){
      el('rect',{x:v._x+10,y:v._laneY[i],width:v._wT-20,height:v._laneH[i],class:'wfx-lane lane-'+l.key},g);
      var lt=el('text',{x:v._x+22,y:v._laneY[i]+20,class:'wfx-lane-title'},g);lt.textContent=l.label;
    });
    if(v._uiH)drawUi(v,g);
    var eg=el('g',{},g);
    v._conns.forEach(function(c){var host=c.line?crossG:eg;
      var p=el('path',{d:hopPath(c),class:'wfx-edge'+(c.line?' is-crossline ':' ')+kindClass(c.e.kind),'marker-end':'url(#wfx-arrow-'+(c.e.kind||'normal')+')'},host);reg(edgeEls,(c.e.orig||c.e).key,p);edgeLabel(c,host);});
    var ng0=el('g',{},topG);
    v.ids.forEach(function(id){
      var n=v.inst[id];
      if(n.subr){ // 하위 섹션 서브루틴 — 누르면 오각형과 같이 하위 섹션으로 이동합니다
        var sg=el('g',{class:'wfx-node type-process is-subr lane-'+n.lane,'data-subr':n.target,'data-linkid':n.id,tabindex:0,role:'button','aria-label':n.title+' 하위 섹션 열기 — 첫 도형 '+code(nodes[n.target])+' '+oneLine(nodes[n.target].text)},ng0);
        shape(n,sg);label(n,sg);var mk=el('text',{x:n._cx+n._w/2-21,y:n._cy+1,class:'wfx-subr-mark','text-anchor':'middle'},sg);mk.textContent='▸';
        reg(edgeEls,inc[n.id][0].orig.key,sg);linkEvents(n,sg);return;
      }
      if(n.virtual){ // 먼 복귀 연결자 — 누르면 도착 도형으로 이동합니다
        var lg=el('g',{class:'wfx-node wfx-link type-link '+kindClass(n.kind)+' lane-'+n.lane,'data-link':n.target,'data-from':n.from,'data-linkid':n.id,tabindex:0,role:'button','aria-label':moveTip(n.target,n.from,n.sym!=='→',n.label)},ng0);
        shape(n,lg);reg(edgeEls,n.id.slice(5),lg);
        var lt=el('text',{x:n._cx,y:n._cy+1,'text-anchor':'middle',class:'wfx-link-text'},lg);lt.textContent=(n.sym||'↩')+' '+code(n);
        
        linkEvents(n,lg);
        return;
      }
      var ng=el('g',{class:'wfx-node type-'+n.type+' lane-'+n.lane,'data-id':n.id,tabindex:0,role:'button','aria-label':code(n)+' '+oneLine(n.text)},ng0);
      shape(n,ng);label(n,ng);reg(nodeEls,n.id,ng);
      var xs=v.refs.filter(function(R){return R.from===id;}).map(function(R){return{e:R.e,to:R.to,cross:true};});
      if(xs.length){
        var cg=el('g',{class:'wfx-chips','data-id':n.id},ng);
        var items=xs.map(function(x){return{x:x,txt:'→ '+code(nodes[x.to])};});
        items.forEach(function(it){it.w=labelW(it.txt)+4;}); // 실제 글자 폭으로 칩 너비
        var total=items.reduce(function(s,it){return s+it.w;},0)+(items.length-1)*4,cx=n._cx-total/2;
        items.forEach(function(it){
          var e=it.x.e,to=it.x.to,tip=moveTip(to,n.id,false,e.label),one=el('g',{class:'wfx-chip '+kindClass(e.kind),role:'button',tabindex:0,'aria-label':tip},cg);
          var py=n._cy+n._h/2+5;el('polygon',{points:[cx,py,cx+it.w-8,py,cx+it.w,py+9,cx+it.w-8,py+18,cx,py+18].join(' ')},one); // 칩도 오각형(2026-10-07 사용자 요청)
          var ct=el('text',{x:cx+it.w/2,y:n._cy+n._h/2+18,'text-anchor':'middle'},one);ct.textContent=it.txt;
          (function(one,to,lab){var on=function(){moveBlock(one,true,moveInfo(to,n.id,false,lab));},off=function(){moveBlock(one,false);};one.addEventListener('mouseenter',on);one.addEventListener('mouseleave',off);one.addEventListener('focus',on);one.addEventListener('blur',off);})(one,to,e.label);
          reg(edgeEls,e.key,one);cx+=it.w+4;
          var go=function(ev){ev.stopPropagation();moveBlock(null,false);focusNode(to,true);select(to);openDock();};
          one.addEventListener('click',go);one.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();go(ev);}});
        });
        chipEls[n.id]=cg;
      }
      ng.addEventListener('click',function(){select(n.id);openDock();});
      ng.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();select(n.id);}});
    });
  });
  bindPanZoom();fit();
  renderIndex();
}

/* ---------- 이동·확대 ---------- */
var tf={x:0,y:0,k:1};
/* UI 구역 — 화면 썸네일(node.thumb)을 그 도형과 같은 가로 위치(같은 열)에 둡니다. 한 열에 셋 이상이면 둘만 보이고 「+n」을 붙입니다.
   배율 35% 미만에서는 그림을 감추고 자리만 그립니다(.is-far). 낡은 캡처(thumb.stale)는 테두리와 표시로 알립니다. */
function drawUi(v,g){
  var y0=v._y+v._h-v._uiH;
  el('rect',{x:v._x+10,y:y0,width:v._w-20,height:v._uiH-10,class:'wfx-lane lane-ui'},g);
  var lt=el('text',{x:v._x+22,y:y0+20,class:'wfx-lane-title'},g);lt.textContent='UI 구역';
  var cols={};v.ids.forEach(function(id){if(nodes[id].thumb){var r=v.inst[id]._rank;(cols[r]=cols[r]||[]).push(id);}});
  Object.keys(cols).forEach(function(r){
    var ids=cols[r],shown=ids.slice(0,2),gap=8,pitch=Math.min(r>0?colAt(v,+r)-colAt(v,r-1):v._cp,colAt(v,+r+1)-colAt(v,+r)),tw=shown.length>1?(pitch-40-gap)/2:Math.min(G.TW,pitch-24),tw2=Math.min(G.TW,tw),cx=v.inst[ids[0]]._cx,x=cx-(shown.length*tw2+(shown.length-1)*gap)/2;
    shown.forEach(function(id){
      var n=nodes[id],t=n.thumb,h=Math.min(v._uiH-74,tw2*(t.h&&t.w?t.h/t.w:2.17)),ty=y0+32;
      var tg=el('g',{class:'wfx-thumb'+(t.stale?' is-stale':''),'data-id':id,role:'button',tabindex:0,'aria-label':code(n)+' 화면'},g);
      el('rect',{x:x,y:ty,width:tw2,height:h,rx:8,class:'wfx-thumb-frame'},tg);
      el('image',{x:x,y:ty,width:tw2,height:h,href:t.src,preserveAspectRatio:'xMidYMin slice','clip-path':'inset(0 round 8px)'},tg);
      var c=el('text',{x:x+tw2/2,y:ty+h+16,'text-anchor':'middle',class:'wfx-thumb-code'},tg);c.textContent=code(n)+(t.stale?' · 낡음':'');
      el('title',{},tg).textContent=code(n)+' '+oneLine(n.text)+(t.stale?' — 시뮬레이터가 바뀐 뒤 다시 찍지 않은 캡처입니다':'');
      var go=function(ev){ev.stopPropagation();select(id);openDock();};tg.addEventListener('click',go);tg.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();go(ev);}});
      x+=tw2+gap;
    });
    if(ids.length>2){var m=el('text',{x:cx,y:y0+v._uiH-22,'text-anchor':'middle',class:'wfx-thumb-more'},g);m.textContent='+'+(ids.length-2)+' · '+ids.slice(2).map(function(i){return code(nodes[i]);}).join(', ');}
  });
}
function apply(){if(svg)svg.classList.toggle('is-far',tf.k<0.35);view.setAttribute('transform','translate('+tf.x+' '+tf.y+') scale('+tf.k+')');document.getElementById('wfx-zoom').textContent=Math.round(tf.k*100)+'%';}
function fit(){var r=svg.getBoundingClientRect();var k=Math.min(r.width/(totalW+20),r.height/(totalH+20));tf={k:k,x:(r.width-totalW*k)/2,y:10};apply();}
function zoomAt(f,cx,cy){var r=svg.getBoundingClientRect();if(cx==null){cx=r.width/2;cy=r.height/2;}var k=Math.max(0.05,Math.min(3,tf.k*f));tf.x=cx-(cx-tf.x)*(k/tf.k);tf.y=cy-(cy-tf.y)*(k/tf.k);tf.k=k;apply();}
function focusNode(id,zoom){var n=nodes[id];if(!n)return;var r=svg.getBoundingClientRect();var f=flows.filter(function(x){return x.code===n.flow;})[0];if(zoom&&tf.k<0.7)tf.k=0.85;tf.x=r.width/2-n._cx*tf.k;tf.y=r.height/2-n._cy*tf.k;apply();}
// 흐름으로 이동 — 그 흐름의 첫 섹션을 글자가 읽히는 배율(35% 이상)로 왼쪽 위에 맞춥니다.
function focusFlow(c){var f=views.filter(function(x){return x.sec.flow.code===c;})[0];if(!f)return;var r=svg.getBoundingClientRect();var k=Math.max(0.35,Math.min(1,r.height/(f._h+40),r.width/(f._w+40)));tf={k:k,x:20-f._x*k,y:20-f._y*k};apply();}
function bindPanZoom(){
  var drag=null;
  /* 휠: 확대·축소 · Shift+휠: 가로 이동 · 끌기: 이동 */
  svg.addEventListener('wheel',function(e){e.preventDefault();var r=svg.getBoundingClientRect();if(e.shiftKey){tf.x-=e.deltaY||e.deltaX;apply();return;}zoomAt(Math.exp(-e.deltaY*0.0015),e.clientX-r.left,e.clientY-r.top);},{passive:false});
  svg.addEventListener('pointerdown',function(e){if(e.target.closest('.wfx-node,.wfx-chip'))return;drag={x:e.clientX,y:e.clientY,tx:tf.x,ty:tf.y};svg.setPointerCapture(e.pointerId);svg.classList.add('is-dragging');});
  svg.addEventListener('pointermove',function(e){if(!drag)return;tf.x=drag.tx+e.clientX-drag.x;tf.y=drag.ty+e.clientY-drag.y;apply();});
  svg.addEventListener('pointerup',function(){drag=null;svg.classList.remove('is-dragging');});
}

/* ---------- 경로 추적 ---------- */
/* 현재 위치에서 고를 수 있는 것(options)을 구하고, 고른 연결에서 다음 유저 행동 지점까지 자동으로 따라갑니다.
   멈추는 곳: ① 나가는 연결에 유저 구역 도형이 있음(유저 행동 대기) ② 조건 판단(결과를 알 수 없을 때) ③ 여러 갈래 ④ 끝 */
var S={pos:null,options:[],segments:[],sel:null,pending:null};
function outs(id){return out[id]||[];}
function stopKind(id){
  var n=nodes[id],es=outs(id);
  if(!es.length)return'end';
  if(es.some(function(e){return e.kind==='yes'||e.kind==='no';}))return'decision';
  if(es.some(function(e){return isUser(nodes[resolve(e.to)]);}))return'wait';
  if(es.length>1)return'choice';
  return null;
}
/* 시뮬레이터 연동 중(simOn)에는 두 가지가 더해집니다.
   · 판정 기준(check)이 있는 조건은 시뮬레이터 상태로 예·아니오를 고릅니다.
   · 실행 action이 있는 연결은 그 사건이 올 때까지 건너가지 않습니다(await) — 흐름도가 시뮬레이터보다 앞서 가지 않게 합니다. */
function simOn(){return !!(sim&&sim.connected);}
function actionsOf(e){return(e.actions||[]).concat(nodes[resolve(e.to)].actions||[]);}
function lookup(obj,path){return String(path).split('.').reduce(function(o,k){return o==null?undefined:o[k];},obj);}
function decide(n){
  if(!simOn()||!n.check||!S.snap)return null;
  var c=n.check,v=lookup(S.snap,c.path),want=String(c.equals),yes=!('equals' in c)?!!v:want.slice(-1)==='*'?String(v).indexOf(want.slice(0,-1))===0:String(v)===want;
  return outs(n.id).filter(function(e){return e.kind===(yes?'yes':'no');})[0]||null;
}
function walk(edge){
  var steps=[],guard=0,e=edge;
  while(e&&guard++<80){
    var to=resolve(e.to);steps.push({edge:e,node:to});
    var n=nodes[to],next=null;
    if(n.type==='decision'){next=decide(n);if(!next)return{steps:steps,stop:'decision',at:to};}
    else{var k=stopKind(to);if(k)return{steps:steps,stop:k,at:to};next=outs(to)[0];}
    if(simOn()&&actionsOf(next).length)return{steps:steps,stop:'await',at:to,pending:next};
    e=next;
  }
  return{steps:steps,stop:'loop',at:steps.length?steps[steps.length-1].node:null};
}
/* 정지 모드(기본)는 사용자가 고를 때만 한 도형씩 나아갑니다 — 열 때 · 상태를 옮긴 뒤에도 그 도형에만 둡니다(2026-10-02 사용자 확정). */
function stopMode(){return simMode()==='stop';}
function start(id){S.segments=[];S.pos=id;S.pending=null;
  if(stopMode()){S.segments.push({steps:[{edge:null,node:id}],stop:stopKind(id)||'step',at:id,title:'시작'});refresh(true);return;}
  var seg={steps:[{edge:null,node:id}],stop:stopKind(id),at:id,title:'시작'};
  var d=nodes[id].type==='decision'?decide(nodes[id]):null;
  if(d){var wd=walk(d);seg.steps=seg.steps.concat(wd.steps);seg.stop=wd.stop;seg.at=wd.at;seg.pending=wd.pending;S.segments.push(seg);S.pos=seg.at;refresh(true);return;}
  if(!seg.stop){var first=outs(id)[0];
    if(simOn()&&actionsOf(first).length){seg.stop='await';seg.pending=first;}
    else{var w=walk(first);seg.steps=seg.steps.concat(w.steps);seg.stop=w.stop;seg.at=w.at;seg.pending=w.pending;}}
  S.segments.push(seg);S.pos=seg.at;refresh(true);}
function take(e,how){
  if(stopMode()){var to=resolve(e.to);S.segments.push({steps:[{edge:e,node:to}],stop:stopKind(to)||'step',at:to,title:how||optionLabel(e),from:e.from});S.pos=to;refresh(true);return;}
  var from=nodes[e.from],w=walk(e);w.title=how||optionLabel(e);w.from=e.from;
  S.segments.push(w);S.pos=w.at;refresh(true);
}
function undo(){if(S.segments.length>1){S.segments.pop();S.pos=S.segments[S.segments.length-1].at;refresh(true);}}
function optionLabel(e){var t=nodes[resolve(e.to)];if(e.kind==='yes'||e.kind==='no')return(e.kind==='yes'?'예':'아니오')+' → '+code(t);return(e.label?e.label+' · ':'')+code(t)+' '+oneLine(t.text);}

/* ---------- 패널 ---------- */
function $(id){return document.getElementById(id);}
function refresh(follow){
  Object.keys(nodeEls).forEach(function(k){nodeEls[k].classList.remove('on-path','is-pos','is-last');});
  Object.keys(edgeEls).forEach(function(k){edgeEls[k].classList.remove('on-path','is-last');});
  S.segments.forEach(function(seg,si){var last=si===S.segments.length-1;seg.steps.forEach(function(st){
    var ne=nodeEls[st.node];if(ne){ne.classList.add('on-path');if(last)ne.classList.add('is-last');}
    if(st.edge){var ee=edgeEls[st.edge.key];if(ee){ee.classList.add('on-path');if(last)ee.classList.add('is-last');}var fe=nodeEls[st.edge.to];if(fe)fe.classList.add('on-path');}
  });});
  if(S.pos&&nodeEls[S.pos])nodeEls[S.pos].classList.add('is-pos');
  if(svg)svg.classList.toggle('has-path',S.segments.some(function(g){return g.steps.length>1;})||S.segments.length>1);
  renderOptions();renderTrace();renderStep();renderShot();
  if(follow&&S.pos){select(S.pos,true);if(svg&&tf.k>=0.4)focusNode(S.pos,false);}
}
/* 현재 위치(패널 왼쪽 칸 · 2026-10-02 사용자 지정) — 현재 도형, 직전 유저 행동 · 직전 동작([이동]), 다음 가능 동작.
   직전은 지나온 경로에서 찾고, 경로가 없으면(열자마자 · 상태를 옮긴 뒤) 노출 조건 카드와 같은 계산 경로에서 찾습니다.
   시뮬레이터와 정지 모드로 그 화면에 있으면 다음 동작마다 무엇을 하는지(버튼 누름 · 화면 옮김 · 방법 없음)를 붙이고 단계 막대와 같게 진행합니다. */
function renderOptions(){
  var box=$('wfx-options');if(!box)return;box.innerHTML='';var id=S.pos;if(!id)return;var n=nodes[id];
  var seg=S.segments[S.segments.length-1];
  var h='<p class="wfx-pos"><b>'+esc(code(n))+'</b> '+esc(oneLine(n.text))+'</p>'; // 모드 · 멈춘 까닭 안내 줄은 뺌(정지·연속은 화면 칸 전환으로 봄 · 2026-10-02 사용자 요청)
  var hist=[];S.segments.forEach(function(g){g.steps.forEach(function(st){if(hist[hist.length-1]!==st.node)hist.push(st.node);});});
  var before=hist.slice(0,hist.lastIndexOf(id)),prev=before.length?before[before.length-1]:null,user=null;
  for(var k=before.length-1;k>=0;k--)if(isUser(nodes[before[k]])){user=before[k];break;}
  var calcPrev=false,calcUser=false; // 지나온 경로가 아니라 계산 경로에서 찾은 줄에 「(계산)」을 붙입니다
  if((!prev||!user)&&id!==startId()){var ins=incR(id); // 시작 도형은 지나온 경로가 없으면 직전도 없음(다른 흐름에서 들어오는 연결은 계산하지 않음)
   if(ins.length){var r=routeTo(ins[Math.min(S.condIdx||0,ins.length-1)]);if(!prev){prev=ins[Math.min(S.condIdx||0,ins.length-1)].from;calcPrev=true;}
    if(!user){r.edges.forEach(function(e){if(isUser(nodes[e.from]))user=e.from;});if(user)calcUser=true;}}}
  var row=function(label,nid,calc){return '<dt'+(calc?' class="is-calc"':'')+'>'+label+'</dt><dd>'+(nid?'<span><b>'+esc(code(nodes[nid]))+'</b> '+esc(oneLine(nodes[nid].text))+'</span><button type="button" class="wfx-go" data-go="'+esc(nid)+'">이동</button>':'<span class="wfx-empty">없음</span>')+'</dd>';};
  h+='<dl class="wfx-prev">'+row('직전 유저 행동',user,calcUser)+row('직전 동작',prev,calcPrev)+'</dl>';
  h+='<h3 class="wfx-next-title">다음 가능 동작</h3>';
  box.innerHTML=h;
  box.querySelectorAll('[data-go]').forEach(function(bt){bt.addEventListener('click',function(){goNode(bt.dataset.go);});});
  var es=outs(id),stepping=simOn()&&stopMode()&&S.hold===id&&!sim.busy;
  if(!es.length){var p=document.createElement('p');p.className='wfx-empty';p.textContent='나가는 연결이 없습니다.';box.appendChild(p);}
  es.forEach(function(e){
    var t=nodes[resolve(e.to)],b=document.createElement('button'),plan=stepping?stepPlan(e):null;
    b.className='wfx-opt '+kindClass(e.kind)+(isUser(t)?' to-user':' to-system')+(e.cross?' is-cross':'');
    var lane=(e.kind==='yes'||e.kind==='no')?'조건':(isUser(t)?'유저':'시스템');
    var how=plan?{press:'시뮬레이터에서 버튼 누름',move:'시뮬레이터 화면 옮김',off:plan.why,take:''}[plan.how]:'';
    b.innerHTML='<i>'+lane+'</i><span>'+esc(optionLabel(e))+'</span>'+(how?'<em>'+esc(how)+'</em>':e.cross?'<em>'+esc(t.flow)+' 흐름</em>':'');
    if(plan&&plan.how==='off')b.disabled=true;
    b.addEventListener('click',function(){if(plan)stepGo(e,plan);else take(e);});box.appendChild(b);
  });
}
/* [이동] — 지나온 경로에 있으면 그 지점까지 되돌리고(경로 유지), 없으면 그 도형에서 새로 시작합니다. 시뮬레이터가 연결되어 있고 옮길 방법이 있으면 화면도 옮깁니다. */
/* 지나온 경로에 그 도형이 있으면 그 지점까지 되돌립니다(앞의 경로 유지). 있으면 true. */
function cutTo(nid){
  var cut=-1;S.segments.forEach(function(g,gi){g.steps.forEach(function(st){if(st.node===nid)cut=gi;});});
  if(cut<0)return false;
  S.segments=S.segments.slice(0,cut+1);var last=S.segments[cut],k=-1;last.steps.forEach(function(st,si){if(st.node===nid)k=si;});
  last.steps=last.steps.slice(0,k+1);last.at=nid;last.stop=stopKind(nid)||'step';S.pos=nid;S.pending=null;
  if(simOn()&&stopMode()&&sim.at===nid)S.hold=nid;
  refresh(true);return true;
}
function inPath(nid){return S.segments.some(function(g){return g.steps.some(function(st){return st.node===nid;});});}
/* [이동] — 도형을 누른 것과 같은 규칙이며, 시뮬레이터가 연결되어 있고 옮길 방법이 있으면 「선택하면 이동」과 관계없이 화면도 옮깁니다. */
function goNode(nid){
  var kept=cutTo(nid);if(!kept)start(nid);
  if(simOn()&&reachOf(nodes[nid])&&sim.at!==nid)moveSim(nid,kept);
  focusNode(nid,false);
}


function renderTrace(){
  var box=$('wfx-trace');box.innerHTML='';
  var segs=S.segments;var from=Math.max(0,segs.length-4);
  if(from>0){var more=document.createElement('p');more.className='wfx-more';more.textContent='앞선 구간 '+from+'개 생략';box.appendChild(more);}
  for(var si=from;si<segs.length;si++){
    var seg=segs[si],wrap=document.createElement('section');wrap.className='wfx-seg'+(si===segs.length-1?' is-last':'');
    var h=document.createElement('h4');h.textContent=(si===0?'시작':'행동 '+si)+' · '+seg.title;wrap.appendChild(h);
    var grid=document.createElement('div');grid.className='wfx-seg-grid';grid.style.gridTemplateColumns='repeat('+seg.steps.length+',minmax(120px,1fr))';
    lanes.forEach(function(l,li){
      seg.steps.forEach(function(st,ci){
        var cell=document.createElement('div');cell.className='wfx-cell lane-'+l.key;cell.style.gridRow=li+1;cell.style.gridColumn=ci+1;
        var n=nodes[st.node];
        if(n.lane===l.key){var c=document.createElement('button');c.className='wfx-card type-'+n.type+(st.edge?' '+kindClass(st.edge.kind):'');
          c.innerHTML=(st.edge&&(st.edge.label||st.edge.kind!=='normal')?'<i>'+esc(st.edge.label||(st.edge.kind==='yes'?'예':'아니오'))+'</i>':'')+'<b>'+esc(code(n))+'</b><span>'+esc(oneLine(n.text))+'</span>';
          c.addEventListener('click',function(){focusNode(n.id,true);select(n.id);});cell.appendChild(c);}
        grid.appendChild(cell);
      });
    });
    wrap.appendChild(grid);box.appendChild(wrap);
  }
  var lanesLbl=$('wfx-trace-lanes');if(lanesLbl)lanesLbl.innerHTML=lanes.map(function(l){return '<span class="lane-'+l.key+'">'+esc(l.label)+'</span>';}).join('');
  box.scrollLeft=box.scrollWidth;
}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function select(id,fromTrace){
  var n=nodes[id];if(!n)return;S.sel=id;
  Object.keys(nodeEls).forEach(function(k){nodeEls[k].classList.toggle('is-sel',k===id);});
  var f=flows.filter(function(x){return x.code===n.flow;})[0];
  if(S.condFor!==id){S.condFor=id;S.condIdx=null;}
  if(!fromTrace){if(!cutTo(id))start(id);followSim(id);} // 도형을 누르면 그 도형이 현재 위치(경로 안이면 되돌림 · 밖이면 새로 시작) — start·cutTo는 다시 select(id,true)를 부릅니다
  try{history.replaceState(null,'','#node='+encodeURIComponent(id));}catch(e){}
}
function typeName(t){return{term:'시작·종료',action:'행동·처리',process:'공통 처리',input:'입력',output:'출력·노출',decision:'조건 판단',ref:'반복 지점'}[t]||t;}

/* ---------- 노출 조건 ----------
   선택한 도형이 어떤 조건을 지나 나타나는지 흐름 데이터에서 계산합니다. 들어오는 연결마다, 시작 도형에서 그 연결의 출발 도형까지
   가장 짧은 경로를 잇고 그 위의 조건 판단(예·아니오)과 직전 유저 행동을 모읍니다. 들어오는 연결이 여럿이면 경로마다 넘겨 봅니다.
   시작에서 닿지 않는 도형은 들어오는 연결이 없는 도형들을 출발점으로 다시 찾습니다. 시뮬레이터가 연결되어 있으면
   보내 온 상태 요약(snap)을 meta.snapLabels의 이름으로 함께 보입니다. */
var incMemo=null,parMemo=null;
function incR(id){if(!incMemo){incMemo={};Object.keys(out).forEach(function(k){out[k].forEach(function(e){var t=resolve(e.to);(incMemo[t]=incMemo[t]||[]).push(e);});});}return incMemo[id]||[];}
function parents(){
  if(parMemo)return parMemo;var par={},s=startId();par[s]=null;
  function run(q){while(q.length){var id=q.shift();outs(id).forEach(function(e){var t=resolve(e.to);if(!(t in par)){par[t]=e;q.push(t);}});}}
  run([s]);
  var roots=Object.keys(nodes).filter(function(k){return !nodes[k].virtual&&!(k in par)&&nodes[k].type!=='ref'&&!incR(k).length;});
  roots.forEach(function(r){par[r]=null;});run(roots);
  return parMemo=par;
}
function routeTo(e){var par=parents(),list=[e],id=e.from,guard=0;while(par[id]&&guard++<500){list.unshift(par[id]);id=par[id].from;}return{edges:list,root:id,reached:id in par};}
function snapText(v,map){if(map&&Object.prototype.hasOwnProperty.call(map,String(v)))return map[String(v)];if(v===true)return'예';if(v===false)return'아니오';if(v===''||v==null)return'—';return typeof v==='object'?JSON.stringify(v):String(v);}
/* 화면(오른쪽 칸 · 2026-10-02 사용자 확정) — 현재 위치의 이름을 적고, 시뮬레이터를 불러오기 전에는 그 도형의 캡처를 크게 보입니다.
   캡처가 없으면 「화면 캡처 없음」만 적습니다(앞 화면으로 대신하지 않음 · 사용자 확정). 불러온 뒤에는 시뮬레이터가 그 자리를 씁니다. */
function renderShot(){
  var id=S.pos,n=nodes[id],t=$('wfx-shot-title');if(t)t.innerHTML=n?'<b>'+esc(code(n))+'</b> '+esc(oneLine(n.text)):'';
  var v=$('wfx-shot');if(!v||!n)return;
  v.innerHTML=n.thumb?'<img class="wfx-shot-big'+(n.thumb.stale?' is-stale':'')+'" src="'+n.thumb.src+'" alt="'+esc(code(n))+' 화면 캡처">'+(n.thumb.stale?'<p class="wfx-shot-note">낡은 캡처 — 시뮬레이터가 바뀐 뒤 다시 찍지 않았습니다</p>':''):'<p class="wfx-shot-empty">화면 캡처 없음</p>';
}

/* 여기서 시작 — 시뮬레이터가 연결되어 있고 상태 키가 있으면 시뮬레이터도 그 상태로 옮깁니다. 옮기는 동안 오는 사건은 무시합니다. */
function startAt(id){var n=nodes[id];if(simOn()&&reachOf(n)){moveSim(id);return;}start(id);}
/* 도달 방법 — 상태 키가 있으면 그 상태, 없으면 프로젝트가 검증해 넣은 reach(출발 상태 + 누를 행동)입니다. */
function reachOf(n){if(n.state)return{state:n.state,actions:[]};if(n.reach&&n.reach.state)return{state:n.reach.state,actions:n.reach.actions||[]};return null;}
function moveSim(id,keep){var r=reachOf(nodes[id]);if(!r)return;sim.keepPath=!!keep;
  if(sim.busy){sim.queued=id;$('wfx-sim-status').textContent='상태 이동 중 · 다음 '+code(nodes[id]);return;}
  sim.busy=true;sim.queued=null;S.hold=null;hideFreeze();renderStep();$('wfx-sim-status').textContent='상태 이동 중 · '+code(nodes[id])+(r.actions.length?' ('+r.state+' + 행동 '+r.actions.length+'개)':' ('+r.state+')');
  post({command:'goto',state:r.state,actions:r.actions,node:id});if(keep)refresh(true);else start(id);}
/* ---------- 정지 · 연속 ----------
   정지(기본): 도형을 골라 옮기면 그 화면에 멈추고, 시뮬레이터 위 단계 막대에서 다음 동작을 골라 [다음] · [이전]으로 넘깁니다.
   연속: 옮긴 뒤 앱이 스스로 이어 가는 흐름을 그대로 두고 사건을 따라 경로를 그립니다(유저 행동을 기다리는 곳에서 멈춤). */
function simMode(){try{return localStorage.getItem('wfx-mode')==='run'?'run':'stop';}catch(e){return'stop';}}
function setMode(m){try{localStorage.setItem('wfx-mode',m);}catch(e){}document.querySelectorAll('.wfx-mode button').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.mode===m));});
  if(m==='run'){S.hold=null;hideFreeze();}else if(simOn()&&sim.at&&S.pos===sim.at)S.hold=sim.at;renderStep();}
/* 다음 동작 하나를 어떻게 진행할지 — 누를 버튼(press) · 옮길 도형(move) · 지금 상태로 판정된 조건(take) · 방법 없음(off) */
function stepPlan(e){
  var t=resolve(e.to),acts=actionsOf(e).filter(function(a){return a.slice(-1)!=='*';}).concat(actionsOf(e).filter(function(a){return a.slice(-1)==='*';}));
  if(acts.length&&isUser(nodes[t]))return{how:'press',action:acts[0]}; // 버튼은 유저 행동으로 가는 연결에서만 누릅니다(시스템 연결의 이름은 앱이 알리는 사건입니다)
  var n=nodes[e.from];if(n.type!=='decision'&&!isUser(nodes[t]))return{how:'take'};
  if(n.type==='decision'){var d=decide(n);if(d===e)return{how:'take'};}
  var w=walk(e),cand=[t].concat(w.steps.map(function(s){return s.node;}),[w.at]);
  for(var i=0;i<cand.length;i++){if(cand[i]&&cand[i]!==S.hold&&reachOf(nodes[cand[i]]))return{how:'move',to:cand[i]};}
  return{how:'off',why:n.type==='decision'?'이 답이 나오는 상태로 옮길 방법이 없습니다':'누를 버튼을 모릅니다'};
}
/* [이전] — 이 흐름에 들어오기 직전 화면입니다. 노출 조건 카드의 경로를 거꾸로 보며 다른 흐름의(없으면 같은 흐름의) 옮길 수 있는 도형을 고릅니다. */
function prevScreen(id){var ins=incR(id);if(!ins.length)return null;var r=routeTo(ins[Math.min(S.condIdx||0,ins.length-1)]),list=r.edges.map(function(e){return e.from;}).reverse(),f=nodes[id].flow,same=null;
  for(var i=0;i<list.length;i++){var c=list[i];if(c===id||!reachOf(nodes[c]))continue;if(nodes[c].flow!==f)return c;if(!same)same=c;}return same;}
function renderStep(){
  if(arguments[0]!=='solo')renderOptions();
  var bar=$('wfx-stepbar');if(!bar)return;var id=S.hold;
  if(!id||!simOn()||simMode()!=='stop'||sim.busy){bar.hidden=true;return;}
  var n=nodes[id],es=outs(id),plans=es.map(stepPlan),pick=-1;plans.forEach(function(p,i){if(pick<0&&p.how!=='off')pick=i;});
  var prev=prevScreen(id),h='<h3><b>'+esc(code(n))+'</b> '+esc(oneLine(n.text))+' · 정지</h3>';
  h+=es.length?'<div class="wfx-step-opts" role="radiogroup" aria-label="다음 동작">'+es.map(function(e,i){var t=nodes[resolve(e.to)],p=plans[i],lane=(e.kind==='yes'||e.kind==='no')?'조건':(isUser(t)?'유저':'시스템');
    return '<label'+(p.how==='off'?' class="is-off"':'')+'><input type="radio" name="wfx-step" value="'+i+'"'+(i===pick?' checked':'')+(p.how==='off'?' disabled':'')+'><i>'+lane+'</i><span>'+esc(optionLabel(e))+(p.how==='off'?'<small>'+esc(p.why)+'</small>':p.how==='press'?'<small>시뮬레이터에서 「'+esc(p.action)+'」를 누릅니다</small>':p.how==='move'?'<small>'+esc(code(nodes[p.to]))+' 화면으로 옮깁니다</small>':'')+'</span></label>';}).join('')+'</div>'
    :'<p class="wfx-cond-empty">나가는 연결이 없습니다</p>';
  h+='<div class="wfx-step-nav"><button type="button" id="wfx-step-prev"'+(prev?'':' disabled')+'>◀ 이전'+(prev?' · '+esc(code(nodes[prev])):'')+'</button><button type="button" id="wfx-step-next" class="is-primary"'+(pick<0?' disabled':'')+'>다음 ▶</button></div>';
  bar.innerHTML=h;bar.hidden=false;
  $('wfx-step-prev').addEventListener('click',function(){if(prev){S.condIdx=null;moveSim(prev);}});
  $('wfx-step-next').addEventListener('click',function(){var c=bar.querySelector('input[name=wfx-step]:checked');if(!c)return;var e=es[Number(c.value)],p=plans[Number(c.value)];stepGo(e,p);});
}
function stepGo(e,p){
  hideFreeze();
  if(p.how==='move'){moveSim(p.to);return;}
  /* 버튼을 누르면 시뮬레이터는 그 뒤 화면으로 넘어가지만, 탐색기는 고른 도형 하나에만 나아가 멈춥니다(다음 도형은 [다음]으로). */
  if(p.how==='press')post({command:'press',action:p.action});
  sim.quietUntil=Date.now()+1500;take(e,'정지 · '+optionLabel(e));S.hold=S.pos;sim.at=S.pos;renderStep();
}
/* 정지 화면 — 앱이 스스로 넘어간 로딩·토스트·전환 화면은 캡처(thumb)를 시뮬레이터 위에 겹쳐 보입니다. */
function showFreeze(id){var n=nodes[id],box=$('wfx-sim');if(!box||!n||!n.thumb||box.querySelector('.wfx-freeze'))return;
  var f=document.createElement('div');f.className='wfx-freeze';f.innerHTML='<img src="'+n.thumb.src+'" alt="'+esc(code(n))+' 정지 화면"><p><b>'+esc(code(n))+'</b> 정지 화면(캡처)<br>앱은 다음 화면으로 넘어갔습니다</p><button type="button">실제 화면 보기</button>';
  f.querySelector('button').addEventListener('click',hideFreeze);box.appendChild(f);}
function hideFreeze(){var f=document.querySelector('#wfx-sim .wfx-freeze');if(f)f.remove();}
/* 선택하면 시뮬레이터도 이동(켜기·끄기 · 브라우저에 기억) — 빠르게 여러 도형을 누르면 마지막 것만 옮깁니다. */
var followTimer=null;
function followOn(){try{return localStorage.getItem('wfx-follow')!=='off';}catch(e){return true;}}
function followSim(id){if(!simOn()||!followOn())return;
  if(!reachOf(nodes[id])){$('wfx-sim-status').textContent='이 도형은 시뮬레이터로 옮길 방법이 없습니다'+(nodes[id].reachNote?' — '+nodes[id].reachNote:'');return;}
  if(id===sim.at)return;clearTimeout(followTimer);followTimer=setTimeout(function(){moveSim(id,inPath(id));},350);}

/* ---------- 시뮬레이터 연결 (선택) ---------- */
var sim={frame:null,ready:false,connected:false,busy:false,states:[],queued:null,at:null,quietUntil:0,settle:null};
function post(msg){if(!sim.frame)return;msg.channel='wfx-host';try{sim.frame.contentWindow.postMessage(msg,'*');}catch(e){}}
function loadSim(){
  var cfg=DATA.meta&&DATA.meta.simulator;if(!cfg||sim.frame)return;
  var f=document.createElement('iframe');f.src=cfg.src;f.title=cfg.title||'시뮬레이터';f.className='wfx-sim-frame';f.setAttribute('allow','autoplay');
  $('wfx-sim').innerHTML='';$('wfx-sim').appendChild(f);sim.frame=f;$('wfx-sim-status').textContent='불러오는 중';
  f.addEventListener('load',function(){sim.ready=true;if(!sim.connected)$('wfx-sim-status').textContent=cfg.bridge?'연결 대기':'연동 전 · 자유 조작';post({command:'hello'});});
}
window.addEventListener('message',function(ev){
  if(!sim.frame||ev.source!==sim.frame.contentWindow)return;var d=ev.data||{};if(d.channel!=='wfx-app')return;
  if(d.snap)S.snap=d.snap;
  if(d.type==='ready'){sim.connected=true;sim.states=d.states||[];$('wfx-sim-status').textContent='연결됨 · 상태 이동 '+sim.states.length+'개';document.querySelector('.wfx-simcol').classList.add('is-sim-on');renderOptions();return;}
  if(d.type==='goto'){sim.busy=false;sim.at=d.ok?d.node:null;$('wfx-sim-status').textContent=d.ok?'연결됨 · '+(d.node?code(nodes[d.node])+' 화면':d.state+' 상태'):'상태 이동 실패 · '+(d.node?code(nodes[d.node]):d.state);
    if(sim.queued&&sim.queued!==d.node){var q=sim.queued;sim.queued=null;moveSim(q);return;}S.hold=d.ok&&d.node&&simMode()==='stop'?d.node:null;sim.quietUntil=Date.now()+1500;hideFreeze();if(d.ok&&d.node){if(sim.keepPath){sim.keepPath=false;refresh(true);}else start(d.node);}return;}
  /* 누를 버튼을 찾지 못하면 [다음]으로 나아간 경로를 되돌려, 흐름도와 시뮬레이터 화면이 갈라지지 않게 합니다. */
  if(d.type==='press'){if(!d.ok){clearTimeout(sim.settle);$('wfx-sim-last').textContent='누를 버튼을 찾지 못해 진행하지 않았습니다 · '+d.action;if(S.segments.length>1)undo();if(simMode()==='stop'){S.hold=S.pos;sim.at=S.pos;renderStep();}}return;}
  if(sim.busy)return;
  /* 정지 중에는 시뮬레이터 사건으로 경로를 옮기지 않습니다. 앱이 스스로 다음 화면으로 넘어가면(이동 직후 잠깐은 제외) 캡처를 겹쳐 정지 화면을 보입니다. */
  if((S.hold||stopMode())&&(d.type==='action'||d.type==='event')){if(!S.hold){$('wfx-sim-last').textContent=(d.type==='event'?d.name:d.action)+' · 정지 중';return;}$('wfx-sim-last').textContent=(d.type==='event'?d.name:d.action)+' · 정지 중';if(Date.now()>sim.quietUntil)showFreeze(S.hold);return;}
  if(d.type==='action'||d.type==='event'){var name=d.type==='event'?d.name:d.action,m=matchAction(name);
    $('wfx-sim-last').textContent=name+(m?' → '+code(nodes[resolve(m[m.length-1].to)]):' · 현재 위치에서 대응 연결 없음');
    if(m)takePath(m,'시뮬레이터 · '+name);}
});
/* 사건 a에 맞는 연결을 현재 위치에서 찾습니다. 사건이 걸리지 않은 도형(입력·이동 대상 선택·공통 처리 등)은
   건너가며 몇 단계 앞까지 봅니다. 조건 도형은 건너가지 않습니다. 가장 가까운 연결 경로를 돌려줍니다. */
function hit(e,a){return actionsOf(e).some(function(p){return p===a||(p.slice(-1)==='*'&&a.indexOf(p.slice(0,-1))===0);});}
function matchAction(a){
  if(!S.pos)return null;
  var seg=S.segments[S.segments.length-1],here=nodes[S.pos],decided=here.type==='decision'?decide(here):null;
  /* 조건에서 멈췄으면 정해진 한 갈래만, 처리·출력에서 멈췄으면 결과 갈래 전부를 봅니다(처리 결과가 여러 갈래로 갈릴 수 있습니다). */
  var start=seg&&seg.pending?(here.type==='decision'?[seg.pending]:outs(S.pos)):decided?[decided]:outs(S.pos);
  var queue=start.map(function(e){return[e];}),seen={};seen[S.pos]=1;
  while(queue.length){
    var path=queue.shift(),e=path[path.length-1];
    if(hit(e,a))return path;
    var t=nodes[resolve(e.to)];
    if(path.length>=5||actionsOf(e).length||t.type==='decision'||seen[t.id])continue;
    seen[t.id]=1;outs(t.id).forEach(function(n){queue.push(path.concat([n]));});
  }
  return null;
}
/* 건너간 연결까지 한 구간으로 묶어 그립니다. */
function takePath(path,how){
  if(path.length===1)return take(path[0],how);
  var steps=path.slice(0,-1).map(function(e){return{edge:e,node:resolve(e.to)};}),w=walk(path[path.length-1]);
  w.steps=steps.concat(w.steps);w.title=how;S.segments.push(w);S.pos=w.at;refresh(true);
}

/* ---------- 목록·검색 ---------- */
function renderIndex(){
  var ul=$('wfx-index');ul.innerHTML='';
  flows.forEach(function(f){var li=document.createElement('li');var b=document.createElement('button');b.innerHTML='<b>'+esc(f.code)+'</b> '+esc(f.title)+'<small>'+f.nodes.length+'</small>';b.addEventListener('click',function(){focusFlow(f.code);});li.appendChild(b);ul.appendChild(li);});
}
function search(q){
  q=q.trim().toLowerCase();var res=$('wfx-results');res.innerHTML='';if(!q)return;
  var hits=Object.keys(nodes).map(function(k){return nodes[k];}).filter(function(n){return !n.virtual&&(code(n).toLowerCase().indexOf(q)>=0||n.id.toLowerCase()===q||oneLine(n.text).toLowerCase().indexOf(q)>=0);}).slice(0,12);
  hits.forEach(function(n){var b=document.createElement('button');b.innerHTML='<b>'+esc(code(n))+'</b> '+esc(oneLine(n.text));b.addEventListener('click',function(){focusNode(n.id,true);select(n.id);openDock();res.innerHTML='';});res.appendChild(b);});
  if(!hits.length)res.innerHTML='<p>찾은 도형이 없습니다</p>';
}

/* ---------- 플로우 패널(현재 위치 · 경로 흐름도 · 흐름도 위 줄 · 2026-10-02) ----------
   처음에는 펼쳐 둡니다. 「플로우 패널 접기」로 접으면 도형을 눌러도 다시 펼치지 않습니다(펼치기 버튼으로만 · 2026-10-02 사용자 지정).
   처음에는 접어 두어 흐름도가 왼쪽 전체 높이를 씁니다. 도형·칩·검색 결과를 누르면 펼치고, 도구 막대 버튼으로 언제든 여닫습니다. */
function setDock(open){var app=document.querySelector('.wfx-app'),b=$('wfx-dock');if(!app)return;var c=svg&&svg.getBoundingClientRect(),cx=c?c.width/2:0,cy=c?c.height/2:0,wx=(cx-tf.x)/tf.k,wy=(cy-tf.y)/tf.k;
  app.classList.toggle('is-dock-closed',!open);if(b){b.textContent=open?'플로우 패널 접기':'플로우 패널 펼치기';b.setAttribute('aria-expanded',String(open));}
  if(c){var n=svg.getBoundingClientRect();tf.x=n.width/2-wx*tf.k;tf.y=n.height/2-wy*tf.k;apply();}}
function openDock(){} // 접힌 패널을 저절로 펼치지 않습니다(사용자가 접은 상태를 지킴)
/* ---------- 시작 ---------- */
function init(){
  render();
  var db=$('wfx-dock');if(db)db.addEventListener('click',function(){setDock(document.querySelector('.wfx-app').classList.contains('is-dock-closed'));});
  $('wfx-fit').addEventListener('click',fit);
  $('wfx-in').addEventListener('click',function(){zoomAt(1.25);});
  $('wfx-out').addEventListener('click',function(){zoomAt(0.8);});
  $('wfx-q').addEventListener('input',function(e){search(e.target.value);});
  document.querySelectorAll('.wfx-mode button').forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.mode===simMode()));b.addEventListener('click',function(){setMode(b.dataset.mode);});});
  var fo=$('wfx-follow');if(fo){fo.checked=followOn();fo.addEventListener('change',function(){try{localStorage.setItem('wfx-follow',fo.checked?'on':'off');}catch(e){}if(fo.checked&&S.sel)followSim(S.sel);});}
  var sb=$('wfx-sim-load');if(sb){if(DATA.meta&&DATA.meta.simulator)sb.addEventListener('click',loadSim);else sb.hidden=true;}
  window.addEventListener('resize',function(){apply();});
  var m=/node=([^&]+)/.exec(location.hash),first=m&&nodes[decodeURIComponent(m[1])]?decodeURIComponent(m[1]):null;
  start(first||startId());
  if(first)focusNode(first,true);else focusFlow(nodes[S.pos].flow); // 처음 화면은 전체 축소 대신 시작 흐름 띠를 읽히는 배율로 엽니다
}
function startId(){var s=DATA.meta&&DATA.meta.start;if(s&&nodes[s])return s;return flows[0].nodes[0].id;}
window.WorkflowExplorer={routeFails:function(){return routeFails;},layoutStats:function(){return layoutStats;},nodes:nodes,out:out,start:start,startAt:startAt,take:take,select:select,state:S,sim:sim,matchAction:matchAction};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
// 좁은 창(1200px 미만)에서는 오른쪽 화면·시뮬레이터 칸이 서랍이 됩니다. 머리말 버튼으로 여닫습니다.
(function(){
  var b=document.getElementById('wfx-simcol-toggle');if(!b)return;
  var col=document.getElementById('wfx-simcol'),top=document.querySelector('.wfx-top');
  function set(on){
    // 서랍은 머리말 아래에서 시작해 여닫기 버튼을 가리지 않습니다
    if(on)col.style.setProperty('--wfx-drawer-top',Math.round(top.getBoundingClientRect().bottom)+'px');
    document.body.classList.toggle('wfx-simcol-open',on);b.setAttribute('aria-expanded',String(on));
  }
  b.addEventListener('click',function(){set(!document.body.classList.contains('wfx-simcol-open'));});
  document.addEventListener('keydown',function(ev){if(ev.key==='Escape'&&document.body.classList.contains('wfx-simcol-open')&&!document.querySelector('dialog[open]'))set(false);});
})();
// 작성 규칙 창(meta.guide) — 머리말 버튼으로 열고, 목차·본문 링크는 주소(node= 해시)를 바꾸지 않고 창 안에서 스크롤합니다.
(function(){
  var dlg=document.getElementById('wfx-guide'),open=document.getElementById('wfx-guide-open');
  if(!dlg||!open)return;
  var art=document.getElementById('wfx-guide-article');
  open.addEventListener('click',function(){if(dlg.showModal)dlg.showModal();else dlg.setAttribute('open','');});
  document.getElementById('wfx-guide-close').addEventListener('click',function(){dlg.close?dlg.close():dlg.removeAttribute('open');});
  dlg.addEventListener('click',function(ev){
    if(ev.target===dlg){dlg.close();return;}
    var a=ev.target.closest&&ev.target.closest('a[data-guide]');if(!a)return;
    var t=document.getElementById('wfx-guide-'+a.getAttribute('data-guide'));if(!t)return;
    ev.preventDefault();art.scrollTop=t.getBoundingClientRect().top-art.getBoundingClientRect().top+art.scrollTop-8;
  });
})();
})();
