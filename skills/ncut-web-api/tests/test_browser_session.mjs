import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {restoreCookies,resumeExpiredPortal} from '../scripts/browser-session.mjs';

async function fixture(t,cookies,current=[]){
  const dir=await fs.mkdtemp(path.join(os.tmpdir(),'school-session-test-'));
  t.after(()=>fs.rm(dir,{recursive:true,force:true}));
  const file=path.join(dir,'me.json');
  await fs.writeFile(file,JSON.stringify({cookies}),{mode:0o600});
  const writes=[];
  const client={call:async(method,args)=>{
    if(method==='Storage.getCookies')return {cookies:current};
    assert.equal(method,'Storage.setCookies');writes.push(args.cookies);return {};
  }};
  return {file,client,writes};
}
const cookie={name:'auth_test',value:'synthetic-saved',domain:'sso.ncut.edu.cn',path:'/',expires:-1,httpOnly:true,secure:true,session:true};
test('restores a lost SSO session cookie without exporting browser-only metadata',async t=>{
  const f=await fixture(t,[cookie,{...cookie,name:'expired',expires:1},{...cookie,domain:'outside.example'}]);
  assert.equal(await restoreCookies(f.client,f.file),1);
  assert.equal(f.writes[0][0].value,'synthetic-saved');
  assert.equal(f.writes[0][0].domain,'sso.ncut.edu.cn');
  assert.ok(!('session' in f.writes[0][0]));
  assert.ok(!('expires' in f.writes[0][0]));
});
test('an already open browser retains newer cookies',async t=>{
  const f=await fixture(t,[cookie],[{...cookie,value:'synthetic-newer'}]);
  assert.equal(await restoreCookies(f.client,f.file),0);
  assert.equal(f.writes.length,0);
});
test('a fresh browser restores the saved account even when its profile has an older cookie',async t=>{
  const f=await fixture(t,[cookie],[{...cookie,value:'synthetic-older'}]);
  assert.equal(await restoreCookies(f.client,f.file,{overwrite:true}),1);
  assert.equal(f.writes[0][0].value,'synthetic-saved');
});
test('first login without an account file makes no cookie calls',async t=>{
  const f=await fixture(t,[]);await fs.unlink(f.file);
  f.client.call=()=>{throw Error('unexpected browser access')};
  assert.equal(await restoreCookies(f.client,f.file),0);
});

function expiredPortalFixture({url='https://jwxt.ncut.edu.cn/',expired=true,buttonCount=1}={}){
  let clicked=0,detached=0;
  const client={call:async(method,args)=>{
    if(method==='Target.getTargets')return {targetInfos:[{type:'page',targetId:'portal',url:clicked?'https://jwxt.ncut.edu.cn/pageHome/index.html':url}]};
    if(method==='Target.attachToTarget')return {sessionId:'auth-session'};
    if(method==='Target.detachFromTarget'){detached++;return {};}
    if(method==='Runtime.evaluate'){
      const document={body:{innerText:expired?'登录状态已过期，您可以继续留在该页面，或者重新登录':'正常业务页面'},querySelectorAll:()=>Array.from({length:buttonCount},()=>({textContent:'重新登录',getClientRects:()=>[{}],click:()=>clicked++}))};
      return {result:{value:vm.runInNewContext(args.expression,{document})}};
    }
    throw Error('Unexpected browser command');
  }};
  return {client,counts:()=>({clicked,detached})};
}
test('an expired portal follows its login action once and reuses the recovered SSO page',async()=>{
  const f=expiredPortalFixture();
  const pages=await resumeExpiredPortal(f.client);
  assert.equal(pages[0].url,'https://jwxt.ncut.edu.cn/pageHome/index.html');
  assert.deepEqual(f.counts(),{clicked:1,detached:1});
});
test('a login-labelled button alone does not authorize navigating a business page',async()=>{
  const f=expiredPortalFixture({expired:false});
  await resumeExpiredPortal(f.client);
  assert.deepEqual(f.counts(),{clicked:0,detached:1});
});
test('an ambiguous login action is left untouched',async()=>{
  const f=expiredPortalFixture({buttonCount:2});
  await resumeExpiredPortal(f.client);
  assert.deepEqual(f.counts(),{clicked:0,detached:1});
});
test('the expiry handoff never evaluates unrelated pages or an existing business portal',async()=>{
  for(const url of ['https://example.com/','https://jwxt.ncut.edu.cn/pageHome/index.html']){
    const f=expiredPortalFixture({url});
    await resumeExpiredPortal(f.client);
    assert.deepEqual(f.counts(),{clicked:0,detached:0});
  }
});
