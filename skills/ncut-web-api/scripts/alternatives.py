"""Pair Web/mobile entries from the same catalog action, without guessing routes."""
import json
import urllib.parse as up
import ncut


def entry_url(value):
    if not value:return None
    url=up.urljoin('https://service.ncut.edu.cn/EIP/',value);parsed=up.urlsplit(url)
    fragments=parsed.fragment.split('?',1)[-1]
    params=up.parse_qsl(parsed.query)+up.parse_qsl(fragments)
    if parsed.scheme!='https' or any(ncut.SECRET.search(k) for k,_ in params):return None
    return url


def pairs(raw):
    result=[]
    for row in ncut.catalog_rows(raw):
        actions=[]
        for group in row.get('service',[]):
            for item in group.get('blArr',[]):
                web=entry_url(item.get('blpcurl'));mobile=entry_url(item.get('blmurl'))
                status='paired_entries' if web and mobile else 'web_entry' if web else 'mobile_only' if mobile else 'entry_needs_resolution'
                actions.append({'action':item.get('blname',''),'web':web,'mobile':mobile,'mapping':status,'fresh_entry_needed':bool((item.get('blpcurl') and not web) or (item.get('blmurl') and not mobile))})
        result.append({'name':row['name'],'availability':'retired_or_moved' if any(v in row['name'] for v in ('停用','转移','转至')) else 'listed_permission_unverified','actions':actions,'same_business_verified':False})
    return result


def catalog_alternatives(args):
    cache=ncut.STATE/'cache/service-alternatives.json'
    if args.cached:
        data=json.loads(ncut.private_read(cache));rows=data['services'];fetched=data['fetched_at']
    else:
        info,raw=ncut.fetch(ncut.service('hall')['entry'])
        if not info['ok']:ncut.emit(info);return
        rows=pairs(raw);fetched=info['fetched_at']
        ncut.private_write(cache,json.dumps({'fetched_at':fetched,'services':rows},ensure_ascii=False))
    chosen=[r for r in rows if args.query.casefold() in r['name'].casefold()];limit=max(1,min(args.limit,30))
    ncut.emit({'ok':True,'source':'cached' if args.cached else 'live','fetched_at':fetched,'scope':'学校服务大厅公开目录；不是本人企微工作台的完整清单','service_count':len(rows),'with_web_entry':sum(any(a['web'] for a in r['actions']) for r in rows),'with_paired_entry':sum(any(a['mapping']=='paired_entries' for a in r['actions']) for r in rows),'needs_fresh_entry':sum(any(a['fresh_entry_needed'] for a in r['actions']) for r in rows),'matched':len(chosen),'services':chosen[:limit],'truncated':len(chosen)>limit})
