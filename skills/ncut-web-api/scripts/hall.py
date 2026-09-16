"""Service-hall SSO and reversible personal favorite writes, without a browser."""
import json
import re
import urllib.parse as up
import ncut
from session_http import follow_login

ORIGIN='https://service.ncut.edu.cn'
LOGIN='/EIP/nonlogin/login/isLogin.htm'
PAGE='/EIP/nonlogin/elobby/service/more.htm'
SOURCE='/EIP/resources/js/elobby/elobby.js'
SEARCH='/EIP/nonlogin/elobby/portal/services/list.htm'
OPEN='/EIP/nonlogin/serviceHandleCenter/openService.htm'


def authenticated(state):
    info,raw=ncut.fetch(ORIGIN+LOGIN,method='POST',data=b'',state=state)
    if not info['ok']:return info
    if raw.strip() not in (b'true',b'false'):return {'ok':False,'code':'HALL_LOGIN_SCHEMA_CHANGED'}
    return {'ok':raw.strip()==b'true','code':'LOGIN_READY' if raw.strip()==b'true' else 'AUTH_REQUIRED'}


def ensure_login(account):
    state=ncut.load_session(account);check=authenticated(state)
    if check['ok'] or check.get('code')!='AUTH_REQUIRED':return check
    info,raw=ncut.fetch(ORIGIN+PAGE,state=state)
    if not info['ok']:return info
    match=re.search(r'''loginPageParam\s*=\s*'.*?url:"([^"]+)"''',raw.decode('utf-8'))
    if not match:return {'ok':False,'code':'HALL_LOGIN_ENTRY_CHANGED'}
    flow,state=follow_login(match[1],state)
    if not flow['ok']:return flow
    check=authenticated(state)
    if check['ok']:ncut.private_write(ncut.account_path(account),json.dumps(state,ensure_ascii=False))
    return {**check,'http_handoff':True,'verified_scope':'personal_service_hall'}


def lookup(account, query, expected_id=None):
    info,_=ncut.fetch(ORIGIN+SEARCH,method='POST',data=up.urlencode({'keyword':query}).encode(),content_type='application/x-www-form-urlencoded',state=ncut.load_session(account),expect='json')
    rows=info.pop('data',None)
    if not info['ok']:raise ValueError('HALL_LOOKUP_'+info.get('code','FAILED'))
    if not isinstance(rows,list):raise ValueError('HALL_SERVICE_LIST_CHANGED')
    selected=[r for r in rows if isinstance(r,dict) and (r.get('id')==expected_id if expected_id else r.get('name')==query)]
    if len(selected)!=1:raise ValueError('Use an exact service name from catalog; result must be unique')
    row=selected[0]
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',str(row.get('id',''))) or str(row.get('isf')) not in ('0','1'):
        raise ValueError('HALL_FAVORITE_FIELDS_CHANGED')
    return {'id':row['id'],'name':row['name'],'favorite':str(row['isf'])=='1'}


def verify_source(account):
    info,raw=ncut.fetch(ORIGIN+SOURCE,state=ncut.load_session(account))
    if not info['ok']:raise ValueError('HALL_WRITE_SOURCE_UNAVAILABLE')
    text=raw.decode('utf-8')
    for marker in ("'elobby/'+sid+'/fav/yes.htm'","'elobby/'+sid+'/fav/no.htm'","'nonlogin/login/isLogin.htm'"):
        if marker not in text:raise ValueError('HALL_WRITE_SOURCE_CHANGED')
    return info['sha256']


def resolve_entry(account, query):
    """Resolve one actual hall service; tickets stay in private state only."""
    ready=ensure_login(account)
    if not ready['ok']:return ready
    row=lookup(account,query)
    info,_=ncut.fetch(ORIGIN+OPEN+'?'+up.urlencode({'sid':row['id']}),state=ncut.load_session(account),expect='json')
    value=info.pop('data',None)
    if not info['ok']:return info
    if not isinstance(value,dict):raise ValueError('HALL_ENTRY_SCHEMA_CHANGED')
    if value.get('needToLogin') in (True,'true',1,'1'):
        return {'ok':False,'code':'AUTH_REQUIRED','service':query}
    if value.get('tip'):
        return {'ok':False,'code':'SERVICE_UNAVAILABLE','service':query,
                'message':re.sub('<[^>]*>','',str(value['tip']))[:400]}
    url=value.get('url')
    if not isinstance(url,str) or not url:raise ValueError('HALL_ENTRY_MISSING')
    url=up.urljoin(ORIGIN+'/EIP/',url)
    if ncut.origin(url) not in ncut.allowed_origins():
        return {'ok':False,'code':'UNREGISTERED_SERVICE_ENTRY','service':query}
    terminal={}
    flow,state=follow_login(url,ncut.load_session(account),terminal=terminal)
    if not flow['ok']:return {**flow,'service':query}
    ncut.private_write(ncut.account_path(account),json.dumps(state,ensure_ascii=False))
    landing=terminal['url'];parsed=up.urlsplit(landing);params=up.parse_qs(parsed.query)
    allowed=('id','platform_id','flowId','flowKey','resType','campusId','buildingId')
    safe_params={k:v[0] for k,v in params.items() if k in allowed and len(v)==1 and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',v[0])}
    record=ncut.STATE/'entries'/('hall-'+account+'-'+row['id']+'.json')
    ncut.private_write(record,json.dumps({'service':query,'entry':url,'landing':landing,'resolved_at':ncut.now()},ensure_ascii=False))
    result={'ok':True,'service':query,'landing':ncut.safe_url(landing),'parameters':safe_params,
            'chain':flow['chain'],'business_verified':False,'private_entry':str(record),'resolved_at':ncut.now()}
    if ncut.origin(landing)=='https://workflow.ncut.edu.cn' and parsed.path=='/reservation/fe/site/reservationInfo':
        site=safe_params.get('id','')
        if not re.fullmatch(r'\d+',site):raise ValueError('RESERVATION_ENTRY_ID_MISSING')
        check,_=ncut.fetch('https://workflow.ncut.edu.cn/reservation/site/resource/detail?'+up.urlencode({'id':site,'collective':'0'}),state=state,expect='json')
        data=check.pop('data',None)
        if not check['ok']:return {**result,'ok':False,'code':check.get('code','BUSINESS_CHECK_FAILED')}
        from reservation import read_rules
        detail=read_rules(data,site)
        result.update(business_verified=True,business={'type':'reservation','site_id':site,'name':detail['name']},
                      next_command=['reservation','calendar','--account',account,'--site',site,'--date','YYYY-MM-DD'])
    return result


def set_favorite(account, service_id, value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',service_id):raise ValueError('Invalid observed service ID')
    path='/EIP/elobby/'+service_id+'/fav/'+('yes' if value else 'no')+'.htm'
    info,_=ncut.fetch(ORIGIN+path,method='POST',data=b'',state=ncut.load_session(account))
    return info


def favorite(args):
    ready=ensure_login(args.account)
    if not ready['ok']:ncut.emit(ready);return
    before=lookup(args.account,args.query)
    result={'ok':True,'service':before,'remote_write_performed':False}
    if args.operation=='show':ncut.emit(result);return
    if not args.allow_write:raise ValueError('WRITE_REQUIRES_AUTHORIZATION: review exact service and operation')
    source_sha=verify_source(args.account)
    if args.operation=='set':
        if args.value is None:raise ValueError('Choose --value yes or no')
        desired=args.value=='yes'
        if before['favorite']==desired:ncut.emit(result|{'unchanged':True});return
        write=set_favorite(args.account,before['id'],desired)
        after=lookup(args.account,args.query,before['id'])
        ncut.emit({'ok':write['ok'] and after['favorite']==desired,'before':before,'after':after,'remote_write_performed':True,'readback_verified':after['favorite']==desired,'source_sha256':source_sha});return
    # Persist the original state before the test so an interrupted run is
    # reviewable. Restore the exact original value, including pre-existing favorites.
    journal=ncut.STATE/'write-checks'/('hall-favorite-'+args.account+'.json')
    record={'account':args.account,'query':args.query,'before':before,'started_at':ncut.now(),'restored':False}
    if journal.exists() and not json.loads(ncut.private_read(journal)).get('restored'):
        raise ValueError('UNFINISHED_WRITE_CHECK: inspect the private journal and restore its original favorite first')
    ncut.private_write(journal,json.dumps(record,ensure_ascii=False))
    changed=False;restored=False;error=None;writes=[]
    try:
        writes.append(set_favorite(args.account,before['id'],not before['favorite']))
        after=lookup(args.account,args.query,before['id'])
        changed=writes[-1]['ok'] and after['favorite']!=before['favorite']
    except (ValueError,OSError) as exc:error=str(exc)
    finally:
        try:
            writes.append(set_favorite(args.account,before['id'],before['favorite']))
            final=lookup(args.account,args.query,before['id'])
            restored=writes[-1]['ok'] and final['favorite']==before['favorite']
        except (ValueError,OSError) as exc:error=str(exc)
        record.update(restored=restored,change_readback_verified=changed,finished_at=ncut.now(),error=error)
        ncut.private_write(journal,json.dumps(record,ensure_ascii=False))
    ncut.emit({'ok':changed and restored,'operation':'verify','service':before['name'],'change_readback_verified':changed,'original_state_restored':restored,'remote_write_performed':True,'write_request_count':len(writes),'source_sha256':source_sha,'checked_at':ncut.now(),'error':error,'journal':str(journal)})
