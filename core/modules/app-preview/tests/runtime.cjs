/* Generic fixtures only: no product policies or real assets. */
const {chromium} = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({channel:process.env.BROWSER_CHANNEL || 'msedge',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1300,height:1000}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.setContent('<main id="preview"></main>');
    await page.addScriptTag({path:path.join(__dirname,'../runtime/app-preview.js')});
    const init = empty => page.evaluate(empty => {
      const screens=empty?[]:[
        {id:'first',title:'First',html:'<style>@media(min-width:700px){body{background:rgb(1,2,3)}}</style><input data-preview-field="name"><button data-preview-target="second">Next</button>'},
        {id:'second',title:'Second',html:'<p>Second screen</p><input data-preview-field="name">'}
      ];
      window.preview=AppPreview.mount(document.querySelector('#preview'),{screens,assetBase:'https://example.invalid/',presets:[{id:'narrow',label:'Narrow',width:320,height:640},{id:'wide',label:'Wide',width:900,height:700}]});
    },empty);
    await init(false);
    await page.getByRole('button',{name:'디바이스 화면 추가',exact:true}).click();
    assert.equal(await page.locator('.ap-card').count(),2);
    const cards=page.locator('.ap-card');
    await cards.nth(1).getByLabel('디바이스 프리셋').selectOption('wide');
    await page.waitForFunction(()=>document.querySelectorAll('iframe')[1].contentDocument?.body);
    assert.equal(await cards.nth(1).locator('iframe').evaluate(el=>el.contentWindow.innerWidth),900);
    assert.equal(await cards.nth(1).locator('iframe').evaluate(el=>el.contentWindow.getComputedStyle(el.contentDocument.body).backgroundColor),'rgb(1, 2, 3)');
    await cards.nth(0).frameLocator('iframe').locator('input').fill('Shared');
    await page.waitForFunction(()=>document.querySelectorAll('iframe')[1].contentDocument.querySelector('input').value==='Shared');
    await cards.nth(0).frameLocator('iframe').getByRole('button',{name:'Next'}).click();
    await cards.nth(1).frameLocator('iframe').getByText('Second screen').waitFor();
    assert.equal(await cards.nth(1).frameLocator('iframe').locator('input').inputValue(),'Shared');
    await page.getByLabel('화면·입력 동기화').uncheck();
    await cards.nth(0).getByRole('button',{name:'이전 화면',exact:true}).click();
    assert.equal(await cards.nth(1).getByLabel('앱 화면').inputValue(),'second');
    await page.getByLabel('화면·입력 동기화').check();
    assert.equal(await cards.nth(1).getByLabel('앱 화면').inputValue(),'first');
    await cards.nth(1).getByRole('button',{name:'회전',exact:true}).click();
    assert.equal(await cards.nth(1).locator('iframe').evaluate(el=>el.contentWindow.innerWidth),700);
    await cards.nth(1).getByLabel('보기 배율(%)').fill('75');
    await cards.nth(1).getByLabel('보기 배율(%)').press('Tab');
    assert.equal(await cards.nth(1).locator('iframe').evaluate(el=>el.style.transform),'scale(0.75)');
    assert.equal(await cards.nth(1).locator('iframe').evaluate(el=>el.contentWindow.innerWidth),700);
    await cards.nth(1).getByLabel('보기 배율(%)').fill('125');
    await cards.nth(1).getByLabel('보기 배율(%)').press('Tab');
    assert.equal(await cards.nth(1).locator('iframe').evaluate(el=>el.style.transform),'scale(1.25)');
    await cards.nth(1).getByLabel('보기 배율(%)').fill('0');
    await cards.nth(1).getByLabel('보기 배율(%)').press('Tab');
    assert.equal(await cards.nth(1).getByLabel('보기 배율(%)').inputValue(),'125');
    assert.equal(await cards.nth(1).getByRole('button',{name:'화면에 맞추기'}).count(),0);
    await cards.nth(1).getByLabel('보기 배율(%)').fill('100');
    await cards.nth(1).getByLabel('보기 배율(%)').press('Tab');
    assert.equal(await cards.nth(1).locator('iframe').evaluate(el=>el.style.transform),'scale(1)');
    await cards.nth(1).getByRole('button',{name:'디바이스 제거',exact:true}).click();
    assert.equal(await cards.count(),1);
    await page.getByRole('button',{name:'전체 초기화'}).click();
    await cards.nth(0).frameLocator('iframe').locator('input').waitFor();
    assert.equal(await cards.nth(0).frameLocator('iframe').locator('input').inputValue(),'');
    assert.equal(await page.evaluate(()=>{try{AppPreview.validate([{id:'x',title:'x',html:'',actions:[{label:'bad',target:'missing'}]}],[]);return false;}catch{return true;}}),true);
    await page.evaluate(()=>preview.destroy());await init(true);
    await page.frameLocator('iframe').getByText('등록된 화면이 없습니다.').waitFor();
    await page.evaluate(()=>{
      preview.destroy();
      const screens=[{id:'a',title:'A',html:'<button data-preview-event="next">Run</button>'},{id:'wait',title:'Wait',html:'<p>Waiting</p>'},{id:'b',title:'B',html:'<p>Finished</p>'}];
      const flow={defaults:{ready:false},entry:[{when:{ready:true},target:'b'},{target:'a'}],edges:[{id:'run',from:'a',event:'next',target:'wait',request:{success:'b',failure:'a',timeout:'a'}}]};
      window.preview=AppPreview.mount(document.querySelector('#preview'),{screens,presets:[],flow,manualStart:true,assetBase:'https://example.invalid/'});
      for(const mutate of [f=>f.entry[0].target='missing',f=>f.edges[0].when={unknown:true},f=>f.edges[0].request.success='missing']){
        const f=JSON.parse(JSON.stringify(flow));mutate(f);let rejected=false;try{AppPreview.validate(screens,[],f)}catch{rejected=true}if(!rejected)throw Error('Invalid flow accepted');
      }
    });
    assert.equal(await page.getByText('앱 시작 설정',{exact:true}).isVisible(),true);
    assert.equal(await page.getByText('다음 동작의 요청 설정',{exact:true}).isVisible(),false);
    await page.getByRole('button',{name:'앱 시작',exact:true}).click();
    assert.equal(await page.getByText('앱 시작 설정',{exact:true}).isVisible(),false);
    assert.equal(await page.getByText('다음 동작의 요청 설정',{exact:true}).isVisible(),true);
    await page.getByLabel('응답 지연(ms)').fill('300');
    await page.frameLocator('iframe').getByRole('button',{name:'Run'}).click();
    assert.equal(await page.getByText('다음 동작의 요청 설정',{exact:true}).isVisible(),false);

    await page.frameLocator('iframe').getByText('Finished').waitFor();
    assert.equal(await page.getByText('다음 동작의 요청 설정',{exact:true}).isVisible(),false);
    await page.locator('.ap-shortcuts').getByRole('button',{name:'A',exact:true}).click();
    assert.equal(await page.getByText('다음 동작의 요청 설정',{exact:true}).isVisible(),true);
    await page.getByRole('button',{name:'앱 종료',exact:true}).click();
    assert.equal(await page.getByText('앱 시작 설정',{exact:true}).isVisible(),true);
    await page.locator('.ap-shortcuts').getByRole('button',{name:'B',exact:true}).click();
    assert.equal(await page.getByRole('button',{name:'이전 화면',exact:true}).isDisabled(),true);
    await page.screenshot({path:require('os').tmpdir()+'/hf-preview-controls.png'});
    assert.deepEqual(errors,[]);
    console.log('app-preview browser checks passed');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
