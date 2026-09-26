/* Persistent records and entry rules use generic verification screens. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('path');
(async()=>{
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'msedge',headless:true});
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(const mode of ['restart','last-step','checkpoint']){
   await page.setContent('<main id="preview"></main>');
   await page.addScriptTag({path:path.join(__dirname,'../runtime/app-preview.js')});
   await page.evaluate(mode=>{
    const screens=[
     {id:'home',title:'Home',html:'<h1>Home</h1>'},
     ...['one','two','three'].map(id=>({id,title:id,html:'<h1>'+id+'</h1><button data-preview-event="next">Next</button>'}))
    ];
    const resume=mode==='restart'?[]:[{from:'home',when:{done:false,[mode==='checkpoint'?'checkpoint':'step']:'three'},target:'three'},{from:'home',when:{done:false,[mode==='checkpoint'?'checkpoint':'step']:'two'},target:'two'}];
    const flow={defaults:{loggedIn:true},records:{done:false,step:'one',checkpoint:'one'},entry:[{target:'home'}],
     onEnter:[...resume,{from:'home',when:{done:false},target:'one'}],
     edges:[
      {id:'one-two',from:'one',event:'next',target:'two',recordSet:{step:'two',checkpoint:'two'}},
      {id:'two-three',from:'two',event:'next',target:'three',recordSet:{step:'three'}},
      {id:'finish',from:'three',event:'next',target:'home',recordSet:{done:true}}
     ]};
    window.fixture={screens,flow};window.preview=AppPreview.mount(document.querySelector('#preview'),{screens,flow,presets:[],manualStart:true,assetBase:'https://example.invalid/'});
   },mode);
   const current=()=>page.getByLabel('앱 화면').inputValue();
   const next=()=>page.frameLocator('iframe').getByRole('button',{name:'Next',exact:true}).click();
   await page.getByRole('button',{name:'앱 시작',exact:true}).click();assert.equal(await current(),'one');
   await next();await next();assert.equal(await current(),'three');
   await page.getByRole('button',{name:'앱 종료',exact:true}).click();
   await page.getByRole('button',{name:'앱 시작',exact:true}).click();
   const expected={restart:'one','last-step':'three',checkpoint:'two'}[mode];assert.equal(await current(),expected);
   await page.getByLabel('앱 화면').selectOption('home');assert.equal(await current(),expected);
   while(await current()!=='home')await next();
   await page.getByRole('button',{name:'앱 종료',exact:true}).click();
   await page.getByRole('button',{name:'앱 시작',exact:true}).click();assert.equal(await current(),'home');
   await page.getByLabel('앱 화면').selectOption('home');assert.equal(await current(),'home');
   await page.getByRole('button',{name:'디바이스 화면 추가',exact:true}).click();
   assert.equal(await page.locator('.ap-card').nth(1).getByLabel('앱 화면').inputValue(),'home');
   await page.getByLabel('화면·입력 동기화').uncheck();
   await page.locator('.ap-card').nth(0).getByRole('button',{name:'사용자 기록 초기화',exact:true}).click();
   await page.locator('.ap-card').nth(0).getByRole('button',{name:'앱 시작',exact:true}).click();
   assert.equal(await page.locator('.ap-card').nth(0).getByLabel('앱 화면').inputValue(),'one');
   assert.equal(await page.locator('.ap-card').nth(1).getByLabel('앱 화면').inputValue(),'home');
   await page.getByLabel('화면·입력 동기화').check();
   assert.equal(await page.locator('.ap-card').nth(1).getByLabel('앱 화면').inputValue(),'one');
   const invalid=await page.evaluate(()=>{
    const {screens,flow}=fixture;let n=0;
    for(const mutate of [
     f=>f.onEnter.push({from:'one',target:'home'}),
     f=>f.edges[0].recordSet={unknown:true},
     f=>f.records.done={bad:true},
     f=>f.onEnter[0].target='missing'
    ]){const f=JSON.parse(JSON.stringify(flow));mutate(f);try{AppPreview.validate(screens,[],f);}catch{n++;}}
    return n;
   });assert.equal(invalid,4);
   await page.evaluate(()=>preview.destroy());
  }
  assert.deepEqual(errors,[]);console.log('record persistence: restart, last-step, checkpoint, completion, shortcut, reset, sync and validation passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
