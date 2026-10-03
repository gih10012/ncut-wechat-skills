import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {restoreCookies,resumeExpiredPortal,captureAccount} from '../scripts/browser-session.mjs';

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

test('capturing school cookies preserves independent service credentials and private metadata',async t=>{
  const f=await fixture(t,[cookie]);
  const saved={cookies:[cookie],headers:{'https://ncut.smartclass.cn':{platform_token:'synthetic-live-token'},'https://weiban.mycourse.cn':{'X-Token':'synthetic-safety-token'}},service_data:{weiban:{tenantCode:'school',userId:'owner'}},private_note:'keep'};
  await fs.writeFile(f.file,JSON.stringify(saved),{mode:0o600});
  const c={call:async method=>{
    if(method==='Storage.getCookies')return {cookies:[{...cookie,value:'synthetic-new-cookie'},{...cookie,domain:'outside.example'}]};
    if(method==='Browser.getVersion')return {userAgent:'synthetic-agent'};
    throw Error('Unexpected browser command');
  }};
  await captureAccount(c,f.file,[]);
  const actual=JSON.parse(await fs.readFile(f.file,'utf8'));
  assert.deepEqual(actual.headers,saved.headers);
  assert.deepEqual(actual.service_data,saved.service_data);
  assert.equal(actual.private_note,'keep');
  assert.equal(actual.cookies.length,1);
  assert.equal(actual.cookies[0].value,'synthetic-new-cookie');
  assert.equal((await fs.stat(f.file)).mode&0o077,0);
});

test('Safety Companion capture keeps only the observed auth fields and scopes the token to its origin',async t=>{
  const f=await fixture(t,[]);
  let detached=0;
  const user={token:'synthetic-new-token',userId:'owner',tenantCode:'school',realName:'private-name',password:'must-not-save'};
  const c={call:async(method,args)=>{
    if(method==='Storage.getCookies')return {cookies:[]};
    if(method==='Browser.getVersion')return {userAgent:'synthetic-agent'};
    if(method==='Target.attachToTarget')return {sessionId:'synthetic-session'};
    if(method==='Target.detachFromTarget'){detached++;return {};}
    if(method==='Runtime.evaluate'){
      const localStorage={getItem:key=>{assert.equal(key,'user');return JSON.stringify(user);}};
      return {result:{value:vm.runInNewContext(args.expression,{localStorage})}};
    }
    throw Error('Unexpected browser command');
  }};
  const result=await captureAccount(c,f.file,[{type:'page',targetId:'safety',url:'https://weiban.mycourse.cn/#/index'}]);
  const raw=await fs.readFile(f.file,'utf8'),actual=JSON.parse(raw);
  assert.equal(result.weiban_captured,true);
  assert.deepEqual(actual.headers,{'https://weiban.mycourse.cn':{'X-Token':'synthetic-new-token'}});
  assert.deepEqual(actual.service_data,{weiban:{userId:'owner',tenantCode:'school'}});
  assert.ok(!raw.includes('private-name'));
  assert.ok(!raw.includes('must-not-save'));
  assert.equal(detached,1);
});

test('unrelated pages cannot supply Safety Companion credentials',async t=>{
  const f=await fixture(t,[]);
  const c={call:async method=>{
    if(method==='Storage.getCookies')return {cookies:[]};
    if(method==='Browser.getVersion')return {userAgent:'synthetic-agent'};
    throw Error('Unrelated page must not be evaluated');
  }};
  await assert.rejects(captureAccount(c,f.file,[{type:'page',targetId:'unrelated',url:'https://weiban.mycourse.cn.example/'}]),/NO_SCHOOL_SESSION_COOKIES/);
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
