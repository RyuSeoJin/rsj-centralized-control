// app-simulator 셸 공용 실행기 — 규칙: core/modules/app-simulator/rules/simulator.md
// SimShell.wfx()      셸 주소에 ?wfx가 있는가(워크플로우 탐색기 안에서 열렸는가)
// SimShell.relay()    탐색기(부모 창 · wfx-host / wfx-app)와 앱(iframe · 프로젝트 채널) 사이에서 메시지를 전달합니다
// SimShell.capture()  기기 화면 캡처 · 녹화 — 셸에 #capture · #capture-stop · #capture-frame · #capture-status · #record가 있어야 합니다
const SimShell=(()=>{
const wfx=()=>/[?&]wfx(=|&|$)/.test(location.search);
// 탐색기 안에서 열렸을 때만 씁니다. host: 앱이 받는 채널, app: 앱이 보내는 채널.
function relay(frame,{host,app}){if(parent!==window){window.addEventListener('message',e=>{if(e.source===parent&&e.data?.channel==='wfx-host')frame.contentWindow?.postMessage({...e.data,channel:host},'*');else if(e.source===frame.contentWindow&&e.data?.channel===app)parent.postMessage({...e.data,channel:'wfx-app'},'*')});}}
// 현재 기기 화면 캡처(2026-09-30 사용자 요청) — 브라우저의 탭 화면 공유(getDisplayMedia)로 보이는 그대로(영상·흐림 효과·섀도 DOM 포함) 한 장면을 받아 PNG로 저장합니다.
// Chrome·Edge는 영역 캡처(CropTarget · cropTo)로 기기 화면(iframe) 또는 기기 프레임 요소만 직접 받아 좌표 계산이 필요 없습니다. 지원하지 않으면 새 장면을 받은 뒤 좌표로 자릅니다.
// 장면은 매번 새로 받습니다(ImageCapture.grabFrame · 없으면 다음 영상 프레임을 기다림). 처음 한 번 「이 탭 공유」를 허용하면 연결을 유지합니다.
// 화면만 캡처할 때는 실제 iOS 스크린샷처럼 모서리를 둥글게 자르지 않고, 프레임 포함일 때는 기기 모서리 밖을 투명하게 둡니다.
// opts: frame(앱 iframe) · device(기기 프레임 요소) · prefix(저장 파일 이름 앞부분) · screenName(지금 화면 이름을 돌려주는 함수 · 실패하면 'screen')
function capture(opts){
 const frame=opts.frame,device=opts.device,prefix=opts.prefix||'simulator',screenName=()=>{try{return (opts.screenName&&opts.screenName())||'screen'}catch{return 'screen'}};
 const button=document.getElementById('capture'),stopButton=document.getElementById('capture-stop'),withFrame=document.getElementById('capture-frame'),note=document.getElementById('capture-status');
 const supported=!!(navigator.mediaDevices&&navigator.mediaDevices.getDisplayMedia);
 let stream=null,track=null,video=null,cropped=null;
 if(!supported){button.disabled=true;note.textContent='이 브라우저는 화면 캡처를 지원하지 않아요. Chrome·Edge에서 열어 주세요.';}
 const wait=ms=>new Promise(r=>setTimeout(r,ms));
 // 화면이 다시 그려지기를 기다리되, 창이 가려져 그리기가 멈춰도 300ms 뒤에는 넘어갑니다.
 const nextFrames=n=>Promise.race([new Promise(r=>{let i=0;const step=()=>{if(++i>=n)r();else requestAnimationFrame(step)};requestAnimationFrame(step)}),wait(300)]);
 function stop(){
  if(recorder)stopRecording();
  if(stream)stream.getTracks().forEach(t=>t.stop());
  stream=null;track=null;cropped=null;
  if(video){video.srcObject=null;video.remove();video=null}
  stopButton.hidden=true;
 }
 async function connect(){
  stream=await navigator.mediaDevices.getDisplayMedia({video:{displaySurface:'browser',frameRate:30},audio:false,preferCurrentTab:true,selfBrowserSurface:'include',surfaceSwitching:'exclude',monitorTypeSurfaces:'exclude'});
  track=stream.getVideoTracks()[0];
  track.addEventListener('ended',()=>{stop();note.textContent='캡처 연결이 끝났어요. 다시 누르면 새로 연결합니다.'});
  const surface=track.getSettings?.().displaySurface;
  if(surface&&surface!=='browser'){stop();throw new Error('surface')}
  // 화면 밖에 두면 Chrome이 음소거 영상을 멈춰 오래된 장면이 남으므로, 화면 모서리에 1px로 둡니다.
  video=document.createElement('video');
  video.muted=true;video.playsInline=true;video.srcObject=stream;
  video.style.cssText='position:fixed;left:0;top:0;width:1px;height:1px;opacity:.01;pointer-events:none;z-index:-1';
  document.body.append(video);
  await video.play();
  stopButton.hidden=false;
  // 공유 알림 줄로 창 높이가 바뀌고 기기 크기가 다시 맞춰지기를 기다립니다.
  await wait(700);
 }
 // 새 장면 한 장 — ImageCapture가 있으면 트랙에서 바로 받고, 없으면 다음 영상 프레임을 기다려 영상 요소를 씁니다.
 async function grab(){
  if(typeof ImageCapture!=='undefined'){try{return await new ImageCapture(track).grabFrame()}catch{}}
  if(video.requestVideoFrameCallback)await Promise.race([new Promise(r=>video.requestVideoFrameCallback(()=>r())),wait(500)]);else await wait(120);
  return video;
 }
 const sizeOf=img=>img instanceof HTMLVideoElement?[img.videoWidth,img.videoHeight]:[img.width,img.height];
 // 영역 캡처 — 대상 요소만 받도록 트랙을 자르고, 잘린 장면(비율이 요소와 같아진 장면)이 올 때까지 기다립니다.
 async function croppedShot(target){
  if(typeof CropTarget==='undefined'||!track.cropTo)return null;
  try{
   if(cropped!==target){await track.cropTo(await CropTarget.fromElement(target));cropped=target;}
   const r=target.getBoundingClientRect(),want=r.width/r.height;
   for(let i=0;i<12;i++){await wait(i?120:200);const img=await grab(),[w,h]=sizeOf(img);if(w&&h&&Math.abs(w/h-want)<want*0.02)return img;}
  }catch{}
  cropped=null;
  try{await track.cropTo(null)}catch{}
  return null;
 }
 function stamp(){const d=new Date(),p=n=>String(n).padStart(2,'0');return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`}
 async function capture(){
  if(!supported)return;
  button.disabled=true;
  const framed=withFrame.checked;
  let scrollBack=null;
  try{
   if(!stream)await connect();
   document.body.classList.add(framed?'capturing-framed':'capturing-screen');
   // 창 밖으로 나간 부분은 찍히지 않으므로, 기기 전체가 창 안에 보이도록 잠시 스크롤했다가 캡처 뒤 되돌립니다.
   const target=framed?device:frame;
   scrollBack=[scrollX,scrollY];
   let box=target.getBoundingClientRect();
   if(box.top<0||box.left<0||box.bottom>innerHeight||box.right>innerWidth){target.scrollIntoView({block:'center',inline:'center',behavior:'instant'});}
   await nextFrames(2);
   await wait(250);
   const r=target.getBoundingClientRect();
   if(r.top<-1||r.left<-1||r.bottom>innerHeight+1||r.right>innerWidth+1)throw new Error('offscreen');
   let img=await croppedShot(target),sx=0,sy=0,sw,sh;
   if(img){[sw,sh]=sizeOf(img);}
   else{
    // 영역 캡처를 못 쓰면 창 전체 장면에서 좌표로 자릅니다.
    img=await grab();
    const [vw,vh]=sizeOf(img),ratio=vw/innerWidth;
    // 다른 탭·창을 골랐으면 화면 비율이 맞지 않습니다.
    if(!vw||!vh||Math.abs(vh/ratio-innerHeight)>innerHeight*0.04)throw new Error('mismatch');
    sx=Math.round(r.left*ratio);sy=Math.round(r.top*ratio);sw=Math.round(r.width*ratio);sh=Math.round(r.height*ratio);
   }
   const canvas=document.createElement('canvas');canvas.width=sw;canvas.height=sh;
   const ctx=canvas.getContext('2d');
   if(framed&&ctx.roundRect){ctx.beginPath();ctx.roundRect(0,0,sw,sh,56*sw/device.offsetWidth);ctx.clip()}
   ctx.drawImage(img,sx,sy,sw,sh,0,0,sw,sh);
   if(img.close)img.close();
   const blob=await new Promise(res=>canvas.toBlob(res,'image/png'));
   if(!blob)throw new Error('blob');
   const a=document.createElement('a');
   a.href=URL.createObjectURL(blob);
   a.download=`${prefix}-${screenName()}${framed?'-frame':''}-${stamp()}.png`;
   document.body.append(a);a.click();a.remove();
   setTimeout(()=>URL.revokeObjectURL(a.href),5000);
   note.textContent=`캡처를 저장했어요 · ${a.download} · ${sw}×${sh}px`;
  }catch(err){
   const name=err&&err.name,msg=err&&err.message;
   if(msg==='mismatch')stop();
   note.textContent=msg==='offscreen'?'기기 화면이 창 안에 모두 보이도록 창을 키운 뒤 다시 눌러 주세요.':name==='NotAllowedError'?'화면 공유를 허용해야 캡처할 수 있어요.':msg==='surface'||msg==='mismatch'?'공유할 대상으로 「이 탭」을 골라 주세요. 다른 탭·창·전체 화면은 캡처할 수 없어요.':'캡처하지 못했어요. 다시 시도해 주세요.';
  }finally{
   document.body.classList.remove('capturing-framed','capturing-screen');
   if(scrollBack)scrollTo({left:scrollBack[0],top:scrollBack[1],behavior:'instant'});
   button.disabled=!supported;
  }
 }
 // 화면 영상 녹화(2026-10-01) — 캡처와 같은 「이 탭 공유」 연결과 영역 자르기를 쓰고, 매 장면을 캔버스에 옮겨 MediaRecorder로 녹화합니다.
 // 영역 캡처를 쓰면 트랙이 대상 요소만 담고, 못 쓰면 매 장면 창 전체에서 대상 요소 자리를 잘라 냅니다(녹화 중 스크롤해도 따라갑니다).
 // 기기 프레임 포함이면 기기 테두리까지 담고, 둥근 모서리 밖을 투명하게 잘라 투명을 담을 수 있는 WebM(VP9)으로 저장합니다(MP4는 투명을 담지 못함 · 2026-10-01).
 // 화면만 녹화하면 MP4를 지원할 때 MP4, 아니면 WebM으로 저장합니다.
 const recordButton=document.getElementById('record');
 let recorder=null,recordLoop=0,recordTimer=0,recordStart=0,recordChunks=[];
 if(!supported||typeof MediaRecorder==='undefined')recordButton.disabled=true;
 function recordType(framed){
  const mp4=[['video/mp4;codecs=avc1.42E01E','mp4'],['video/mp4','mp4']],webm=[['video/webm;codecs=vp9','webm'],['video/webm;codecs=vp8','webm'],['video/webm','webm']];
  for(const [type,ext] of framed?[...webm,...mp4]:[...mp4,...webm])
   if(MediaRecorder.isTypeSupported(type))return {type,ext};
  return {type:'',ext:'webm'};
 }
 const clock=ms=>{const s=Math.floor(ms/1000);return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')};
 function cancelLoop(){if(video&&video.cancelVideoFrameCallback)try{video.cancelVideoFrameCallback(recordLoop)}catch{}clearTimeout(recordLoop)}
 async function startRecording(){
  if(!supported||recorder)return;
  recordButton.disabled=true;button.disabled=true;
  const framed=withFrame.checked;
  try{
   if(!stream)await connect();
   document.body.classList.add(framed?'capturing-framed':'capturing-screen');
   const target=framed?device:frame;
   const box=target.getBoundingClientRect();
   if(box.top<0||box.left<0||box.bottom>innerHeight||box.right>innerWidth)target.scrollIntoView({block:'center',inline:'center',behavior:'instant'});
   await nextFrames(2);
   await wait(250);
   const r=target.getBoundingClientRect();
   if(r.top<-1||r.left<-1||r.bottom>innerHeight+1||r.right>innerWidth+1)throw new Error('offscreen');
   const shot=await croppedShot(target),regional=!!shot;if(shot&&shot.close)shot.close();
   const vw=video.videoWidth,vh=video.videoHeight,k=regional?vw/r.width:vw/innerWidth;
   if(!vw||!vh||(!regional&&Math.abs(vh/k-innerHeight)>innerHeight*0.04))throw new Error('mismatch');
   const sw=Math.max(2,Math.round(r.width*k/2)*2),sh=Math.max(2,Math.round(r.height*k/2)*2);
   const canvas=document.createElement('canvas');
   canvas.width=sw;canvas.height=sh;
   const ctx=canvas.getContext('2d'),radius=framed?56*sw/device.offsetWidth:0;
   const draw=()=>{
    if(!recorder||!video)return;
    let sx=0,sy=0,w=video.videoWidth,h=video.videoHeight;
    if(!regional){const b=target.getBoundingClientRect(),q=video.videoWidth/innerWidth;sx=b.left*q;sy=b.top*q;w=b.width*q;h=b.height*q;}
    if(w&&h){if(radius&&ctx.roundRect){ctx.clearRect(0,0,sw,sh);ctx.save();ctx.beginPath();ctx.roundRect(0,0,sw,sh,radius);ctx.clip();ctx.drawImage(video,sx,sy,w,h,0,0,sw,sh);ctx.restore()}else ctx.drawImage(video,sx,sy,w,h,0,0,sw,sh)}
    schedule();
   };
   const schedule=()=>{recordLoop=video&&video.requestVideoFrameCallback?video.requestVideoFrameCallback(draw):setTimeout(draw,33)};
   const {type,ext}=recordType(framed),name=`${prefix}-${screenName()}${framed?'-frame':''}-${stamp()}.${ext}`;
   recorder=new MediaRecorder(canvas.captureStream(30),type?{mimeType:type,videoBitsPerSecond:8000000}:{videoBitsPerSecond:8000000});
   recordChunks=[];
   recorder.ondataavailable=e=>{if(e.data&&e.data.size)recordChunks.push(e.data)};
   recorder.onstop=()=>{
    const seconds=clock(Date.now()-recordStart),blob=new Blob(recordChunks,{type:(recorder&&recorder.mimeType)||type||'video/webm'});
    recorder=null;recordChunks=[];
    document.body.classList.remove('capturing-framed','capturing-screen');
    recordButton.textContent='녹화 시작';recordButton.classList.remove('is-recording');recordButton.disabled=!supported;button.disabled=!supported;
    if(!blob.size){note.textContent='녹화된 장면이 없어 저장하지 않았어요. 다시 시도해 주세요.';return}
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);a.download=name;
    document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(a.href),10000);
    note.textContent=`영상을 저장했어요 · ${name} · ${seconds} · ${sw}×${sh}px`;
   };
   schedule();
   recorder.start(1000);
   recordStart=Date.now();
   recordButton.textContent='녹화 종료 · 저장';recordButton.classList.add('is-recording');recordButton.disabled=false;
   const tick=()=>{note.textContent=`녹화 중 · ${clock(Date.now()-recordStart)} · 시뮬레이터를 조작한 뒤 「녹화 종료 · 저장」을 누르세요.`};
   tick();recordTimer=setInterval(tick,500);
  }catch(err){
   recorder=null;cancelLoop();
   document.body.classList.remove('capturing-framed','capturing-screen');
   const name=err&&err.name,msg=err&&err.message;
   if(msg==='mismatch')stop();
   note.textContent=msg==='offscreen'?'기기 화면이 창 안에 모두 보이도록 창을 키운 뒤 다시 눌러 주세요.':name==='NotAllowedError'?'화면 공유를 허용해야 녹화할 수 있어요.':msg==='surface'||msg==='mismatch'?'공유할 대상으로 「이 탭」을 골라 주세요. 다른 탭·창·전체 화면은 녹화할 수 없어요.':'녹화를 시작하지 못했어요. 다시 시도해 주세요.';
   recordButton.disabled=!supported||typeof MediaRecorder==='undefined';button.disabled=!supported;
  }
 }
 function stopRecording(){
  if(!recorder)return;
  clearInterval(recordTimer);cancelLoop();
  recordButton.disabled=true;
  note.textContent='녹화를 마무리하고 있어요…';
  try{if(recorder.state!=='inactive')recorder.stop();else recorder.onstop()}catch{recorder.onstop&&recorder.onstop()}
 }
 recordButton.addEventListener('click',()=>{if(recorder)stopRecording();else startRecording()});
 button.addEventListener('click',capture);
 stopButton.addEventListener('click',()=>{stop();note.textContent='캡처 연결을 끊었어요. 다시 누르면 새로 연결합니다.'});
}
return {wfx,relay,capture};
})();
