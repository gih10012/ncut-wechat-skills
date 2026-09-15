"""Read the verified reservation calendar with the account's bound User-Agent."""
import datetime as dt
import json
import re
import urllib.parse as up
import ncut

STATUS={0:'可预约',1:'未开放',2:'已过期',3:'约满',4:'不可约'}

def read_rules(data, site):
    if not isinstance(data,dict) or data.get('e')!='OK' or not isinstance(data.get('d'),dict):
        raise ValueError('RESERVATION_RULES_SCHEMA_CHANGED')
    d=data['d'];config=d.get('config')
    if str(d.get('id'))!=site or not isinstance(config,dict) or not isinstance(config.get('rule'),list):
        raise ValueError('RESERVATION_RULES_SCHEMA_CHANGED')
    anti_bot=config.get('anti_bot')
    if type(anti_bot) is not int or anti_bot not in (0,1):
        raise ValueError('RESERVATION_VERIFICATION_MODE_CHANGED')
    fields=('class','rule_type','roles','type','min','num','times','day','time','time_type','week','start_time','end_time','start','end','format','condition','conditionTime','otherwiseStart','otherwiseEnd','config','cycle_enable','cycle_configs')
    rules=[]
    for rule in config['rule']:
        if not isinstance(rule,dict) or not isinstance(rule.get('class'),str):
            raise ValueError('RESERVATION_RULES_SCHEMA_CHANGED')
        rules.append({k:rule[k] for k in fields if k in rule})
    limits=d.get('limit_info',{})
    if not isinstance(limits,dict):raise ValueError('RESERVATION_LIMIT_INFO_CHANGED')
    windows=[{k:r[k] for k in ('week','start_time','end_time','roles','rule_type') if k in r} for r in rules if r['class']=='ServiceTimeRule']
    return {'site_id':site,'name':d.get('name'),'verification_required':anti_bot==1,'submission_windows':windows,'limit_info':limits,'rules':rules,'form_field_count':len(config.get('data_colle',[])),'rules_scope':'服务器当前返回的规则；资格及可约状态仍由当前日历和提交时校验决定','remote_write_performed':False}


def rules(args):
    if not re.fullmatch(r'\d+',args.site):raise ValueError('Expected a site ID observed in the real service entry')
    info,_=ncut.fetch('https://workflow.ncut.edu.cn/reservation/site/resource/detail?'+up.urlencode({'id':args.site,'collective':'0'}),state=ncut.load_session(args.account),expect='json')
    data=info.pop('data',None)
    if not info['ok']:ncut.emit(info);return
    ncut.emit({'ok':True,'fetched_at':info['fetched_at'],**read_rules(data,args.site)})


def calendar(args):
    if not re.fullmatch(r'\d+',args.site):raise ValueError('Expected a site ID observed in the real service entry')
    dt.date.fromisoformat(args.date)
    params={'id':args.site,'collective':'0','date':json.dumps({'start_date':args.date,'end_date':args.date},separators=(',',':'))}
    info,raw=ncut.fetch('https://workflow.ncut.edu.cn/reservation/site/resource/calendar?'+up.urlencode(params),state=ncut.load_session(args.account),expect='json')
    data=info.pop('data',None)
    if not info['ok']:ncut.emit(info|{'business_code':data.get('e') if isinstance(data,dict) else None});return
    if not isinstance(data,dict) or data.get('e')!='OK' or not isinstance(data.get('d'),dict):raise ValueError('CALENDAR_SCHEMA_CHANGED')
    value=data['d'];rows=[]
    if not all(k in value for k in ('time','resource','data')):raise ValueError('CALENDAR_SCHEMA_CHANGED')
    for resource in value['resource']:
        for period in value['time']:
            cell=value['data'].get(args.date,{}).get(str(resource['id']),{}).get(str(period['id']))
            if cell is None:continue
            status=int(cell['status'])
            rows.append({'site_id':args.site,'date':args.date,'resource_id':resource['id'],'resource':resource['name'],'period_id':period['id'],'time':period['str_time'],'status':status,'status_text':STATUS.get(status,'未知状态'),'num':cell.get('num'),'total':cell.get('total')})
    limit=max(1,min(args.limit,48))
    ncut.emit(info|{'account':args.account,'date':args.date,'site_id':args.site,'slot_count':len(rows),'slots':rows[:limit],'truncated':len(rows)>limit,'remote_write_performed':False})
