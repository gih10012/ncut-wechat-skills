#!/usr/bin/env node
// One-time browser login/capture using installed Chrome and Node built-ins.
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

process.umask(0o077);
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const state=path.join(os.homedir(),'.local/state/ncut-web-api');
const [command, account, serviceAlias, ...options]=process.argv.slice(2);
const report=value=>process.stdout.write(JSON.stringify(value,null,2)+'\n');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const services=JSON.parse(await fs.readFile(path.join(root,'references/services.json'),'utf8')).services;
const domains=new Set(services.flatMap(s=>s.origins.map(o=>new URL(o).hostname)));

async function privateDir(dir){
  await fs.mkdir(dir,{recursive:true,mode:0o700});
  const info=await fs.lstat(dir);
  if(!info.isDirectory()||info.uid!==process.getuid())throw Error('UNSAFE_PROFILE_DIRECTORY');
  await fs.chmod(dir,0o700);
}
export async function restoreCookies(c,file,{overwrite=false}={}){
  let saved;
  try{
    const info=await fs.lstat(file);
    if(!info.isFile()||info.uid!==process.getuid()||(info.mode&0o077))throw Error('UNSAFE_ACCOUNT_FILE');
    saved=JSON.parse(await fs.readFile(file,'utf8'));
  }catch(error){if(error.code==='ENOENT')return 0;throw error;}
  const {cookies:current}=await c.call('Storage.getCookies');
  const key=x=>[x.name,x.domain,x.path||'/'].join('\0');
  const present=new Set(current.map(key));
  const cookies=(saved.cookies||[]).filter(x=>
    (domains.has(x.domain?.replace(/^\./,''))||x.domain==='.ncut.edu.cn')&&
    (!x.expires||x.expires<0||x.expires>Date.now()/1000)&&
    (overwrite||!present.has(key(x)))
  ).map(x=>{
    const result={};
    for(const field of ['name','value','domain','path','secure','httpOnly','sameSite'])
      if(x[field]!==undefined)result[field]=x[field];
    if(x.expires>0)result.expires=x.expires;
    return result;
  });
  if(cookies.length)await c.call('Storage.setCookies',{cookies});
  return cookies.length;
}
export async function connection(profile){
  const portFile=await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8');
  const [port,browserPath]=portFile.trim().split('\n');
  if(!/^\d+$/.test(port)||Number(port)<1||Number(port)>65535||!/^\/devtools\/browser\/[a-zA-Z0-9-]+$/.test(browserPath))throw Error('BROWSER_NOT_READY');
  const ws=new WebSocket(`ws://127.0.0.1:${port}${browserPath}`);
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{ws.close();reject(Error('BROWSER_NOT_CONNECTED'));},3000);
    ws.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
    ws.addEventListener('error',()=>{clearTimeout(timer);reject(Error('BROWSER_NOT_CONNECTED'));},{once:true});
  });
  let counter=0;
  return {close:()=>ws.close(),on:callback=>ws.addEventListener('message',event=>callback(JSON.parse(event.data))),call:(method,params={},sessionId)=>new Promise((resolve,reject)=>{
    const id=++counter;
    const timer=setTimeout(()=>{ws.removeEventListener('message',listener);reject(Error('BROWSER_COMMAND_TIMEOUT'));},5000);
    function listener(event){
      const msg=JSON.parse(event.data);if(msg.id!==id)return;
      clearTimeout(timer);ws.removeEventListener('message',listener);
      if(msg.error)reject(Error('BROWSER_COMMAND_FAILED'));else resolve(msg.result);
    }
    ws.addEventListener('message',listener);ws.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));
  })};
}
async function main(){
  if(!['open','status','capture','close','handoff'].includes(command)||!/^[a-zA-Z0-9_-]{1,64}$/.test(account||'')){
    report({usage:'node browser-session.mjs open ACCOUNT SERVICE [--headless] | status ACCOUNT | capture ACCOUNT | close ACCOUNT'});return;
  }
  const profile=path.join(state,'browser',account);
  await privateDir(state);await privateDir(path.join(state,'browser'));await privateDir(profile);
  if(command==='open'){
    const service=services.find(s=>[s.id,...s.aliases].includes(serviceAlias));
    if(!service?.entry)throw Error('UNKNOWN_SERVICE');
    let existing;
    try{existing=await connection(profile);}catch{}
    if(existing){
      await restoreCookies(existing,path.join(state,'accounts',account+'.json'));
      await existing.call('Target.createTarget',{url:service.entry});existing.close();
      report({ok:true,account,service:service.id,browser_opened:true,reused_profile:true});return;
    }
    if(!options.includes('--headless')&&!process.env.DISPLAY&&!process.env.WAYLAND_DISPLAY)throw Error('FIRST_LOGIN_NEEDS_VISIBLE_BROWSER_OR_EXISTING_SESSION');
    const args=[`--user-data-dir=${profile}`,'--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--no-first-run','--no-default-browser-check'];
    if(options.includes('--headless'))args.push('--headless=new');
    // Restore session cookies before any business/SSO request. Chrome normally
    // drops these when the previous dedicated login window is closed.
    args.push('about:blank');
    const child=spawn('/usr/bin/google-chrome-stable',args,{stdio:'ignore',detached:true});
    let launchError=false;child.on('error',()=>{launchError=true;});child.unref();
    let ready=false;
    for(let i=0;i<16&&!launchError;i++){
      await pause(250);
      try{const c=await connection(profile);c.close();ready=true;break;}catch{}
    }
    if(!ready)throw Error('BROWSER_LAUNCH_FAILED');
    const c=await connection(profile);
    try{
      await restoreCookies(c,path.join(state,'accounts',account+'.json'),{overwrite:true});
      const {targetInfos}=await c.call('Target.getTargets');
      await c.call('Target.createTarget',{url:service.entry});
      for(const target of targetInfos.filter(t=>t.type==='page'&&t.url==='about:blank'))
        await c.call('Target.closeTarget',{targetId:target.targetId});
    }finally{c.close();}
    report({ok:true,account,service:service.id,browser_opened:true,headless:options.includes('--headless'),next:'Complete the real login in this browser, then capture the same account. No credentials need to be pasted into chat.'});return;
  }
  const c=await connection(profile);
  try{
    if(command==='close'){
      await c.call('Browser.close');report({ok:true,account,browser_closed:true});return;
    }
    if(command==='handoff'){
      const {targetInfos}=await c.call('Target.getTargets');
      const portals=targetInfos.filter(t=>t.type==='page'&&t.url.startsWith('https://jwxt.ncut.edu.cn/pageHome/'));
      if(portals.length!==1)throw Error('OPEN_SCHOOL_PORTAL_AFTER_LOGIN');
      const {sessionId}=await c.call('Target.attachToTarget',{targetId:portals[0].targetId,flatten:true});
      const click=async(selector,label)=>{
        const expression=`(()=>{const items=[...document.querySelectorAll(${JSON.stringify(selector)})].filter(e=>e.getClientRects().length&&e.textContent.trim()===${JSON.stringify(label)});if(items.length!==1)return false;items[0].click();return true;})()`;
        for(let i=0;i<20;i++){
          const r=await c.call('Runtime.evaluate',{expression,userGesture:true,returnByValue:true},sessionId);
          if(r.result.value===true)return;
          await pause(100);
        }
        throw Error('SCHOOL_MENU_CHANGED');
      };
      await click('.tabs .tab','本科生');
      await click('.one-menu-cell','选课&课表');
      await click('.three-menu-cell .cell-info','学生个人课表');
      for(let i=0;i<40;i++){
        await pause(250);
        const {targetInfos:current}=await c.call('Target.getTargets');
        if(current.some(t=>t.type==='page'&&t.url.startsWith('https://jwxtbk.ncut.edu.cn/jsxsd/'))){
          report({ok:true,account,handoff_completed:true,live_identity_verified:false});return;
        }
      }
      throw Error('SCHOOL_HANDOFF_NOT_READY');
    }
    const {targetInfos}=await c.call('Target.getTargets');
    const pages=targetInfos.filter(t=>t.type==='page'&&t.url.startsWith('https://')).map(t=>{
      const u=new URL(t.url);return {title:t.title,url:u.origin+u.pathname};
    });
    if(command==='status'){
      let login_state='business_page_or_unknown';
      const sso=targetInfos.find(t=>t.type==='page'&&t.url.startsWith('https://sso.ncut.edu.cn/'));
      if(sso){
        login_state='awaiting_login';
        const {sessionId}=await c.call('Target.attachToTarget',{targetId:sso.targetId,flatten:true});
        try{
          // Inspect login instructions, never field values or QR contents. The
          // school's actual login form lives in a same-origin iframe.
          const expression=`(()=>{const docs=[document];for(const frame of document.querySelectorAll('iframe')){try{if(frame.contentDocument)docs.push(frame.contentDocument);}catch{}}const text=docs.map(d=>d.body?.innerText||'').join(' ');return /二维码已失效/.test(text)?'qr_expired':'awaiting_login';})()`;
          const r=await c.call('Runtime.evaluate',{expression,returnByValue:true},sessionId);
          if(['qr_expired','awaiting_login'].includes(r.result.value))login_state=r.result.value;
        }finally{await c.call('Target.detachFromTarget',{sessionId});}
      }
      report({ok:true,account,pages,login_state,live_identity_verified:false});return;
    }
    const {cookies:all}=await c.call('Storage.getCookies');
    const {userAgent}=await c.call('Browser.getVersion');
    const cookies=all.filter(c=>domains.has(c.domain.replace(/^\./,''))||c.domain==='.ncut.edu.cn');
    if(!cookies.length)throw Error('NO_SCHOOL_SESSION_COOKIES');
    const accounts=path.join(state,'accounts');await privateDir(accounts);
    const file=path.join(accounts,account+'.json'),temp=file+'.'+process.pid+'.tmp';
    await fs.writeFile(temp,JSON.stringify({cookies,headers:{},user_agent:userAgent,imported_at:new Date().toISOString()}),{mode:0o600,flag:'wx'});
    await fs.rename(temp,file);
    report({ok:true,account,cookie_count:cookies.length,user_agent_preserved:true,pages,live_identity_verified:false,next:'Validate the current identity/business response; saved cookies alone do not prove successful login.'});
  }finally{c.close();}
}
if(path.resolve(process.argv[1]||'')===fileURLToPath(import.meta.url)){
  try{await main();}catch(error){report({ok:false,code:/^[A-Z_]+$/.test(error.message)?error.message:'BROWSER_SESSION_ERROR'});process.exitCode=1;}
}
