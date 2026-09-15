"""Verified undergraduate timetable adapter; pure HTML parsing without a browser."""
from html.parser import HTMLParser
import datetime as dt
import json
import re
import urllib.parse as up
import ncut


class Node:
    def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=dict(attrs or []);self.children=[]
    def text(self):
        return re.sub(r'\s+',' ',''.join(c if isinstance(c,str) else c.text()+' ' for c in self.children if isinstance(c,str) or c.tag not in ('script','style'))).strip()
    def all(self,tag=None,cls=None,id=None):
        out=[]
        for c in self.children:
            if isinstance(c,str):continue
            if (tag is None or c.tag==tag) and (cls is None or cls in c.attrs.get('class','').split()) and (id is None or c.attrs.get('id')==id):out.append(c)
            out.extend(c.all(tag,cls,id))
        return out


class Document(HTMLParser):
    def __init__(self,text):
        super().__init__();self.root=Node();self.stack=[self.root];self.feed(text)
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs);self.stack[-1].children.append(node)
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):self.stack.append(node)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];break
    def handle_data(self,data):self.stack[-1].children.append(data)


def parse_setup(raw):
    html=raw.decode('utf-8');root=Document(html).root
    term_select=root.all('select',id='xnxq');week_select=root.all('select',id='week')
    if len(term_select)!=1 or len(week_select)!=1:raise ValueError('TIMETABLE_SCHEMA_CHANGED: semester/week controls missing')
    terms=[{'id':o.attrs.get('value'),'name':o.text(),'selected':'selected' in o.attrs} for o in term_select[0].all('option')]
    current=[t for t in terms if t['selected']]
    if len(current)!=1:raise ValueError('TIMETABLE_SEMESTER_AMBIGUOUS')
    weeks=[{'start':o.attrs.get('value'),'label':o.text()} for o in week_select[0].all('option') if re.fullmatch(r'\d{4}-\d{2}-\d{2}',o.attrs.get('value',''))]
    mode=re.search(r'let\s+kbjcmss\s*=\s*(\[.*?\])',html,re.S)
    if not mode:raise ValueError('TIMETABLE_PERIOD_MODE_MISSING')
    modes=json.loads(mode[1]);defaults=[m for m in modes if m.get('mrms')=='1']
    if len(defaults)!=1:raise ValueError('TIMETABLE_PERIOD_MODE_AMBIGUOUS')
    return {'current_term':current[0],'terms':terms,'weeks':weeks,'mode':defaults[0]['kbjcmsid']}


def parse_grid(raw):
    root=Document(raw.decode('utf-8')).root;tables=root.all('table')
    if not tables:raise ValueError('TIMETABLE_GRID_MISSING')
    rows=tables[0].all('tr');entries=[]
    if not rows or '星期一' not in rows[0].text() or '星期日' not in rows[0].text():raise ValueError('TIMETABLE_WEEKDAY_SCHEMA_CHANGED')
    for row in rows[1:]:
        cells=[c for c in row.children if not isinstance(c,str) and c.tag in ('td','th')]
        if len(cells)!=8:raise ValueError('TIMETABLE_GRID_COLUMNS_CHANGED')
        label=cells[0].text();clock=re.search(r'\d{2}:\d{2}-\d{2}:\d{2}',label)
        for day,cell in enumerate(cells[1:],1):
            for course in cell.all(cls='person-class'):
                titles=course.all('h3');details=course.all('li')
                if len(titles)!=1 or len(details)<4:raise ValueError('TIMETABLE_COURSE_SCHEMA_CHANGED')
                entries.append({'weekday':day,'period':label,'time':clock[0] if clock else None,'course':titles[0].text(),'weeks':details[1].text(),'teacher':details[2].text(),'room':details[3].text(),'group':details[0].text()})
    unarranged=[]
    for table in root.all('table',id='tbXs'):
        for row in table.all('tr')[1:]:
            cols=[c.text() for c in row.children if not isinstance(c,str) and c.tag in ('td','th')]
            if len(cols)==6:unarranged.append(dict(zip(['course','group','start_week','end_week','teacher','note'],cols)))
    return entries,unarranged


def in_week(expression,number):
    if '单周' in expression and number%2==0:return False
    if '双周' in expression and number%2==1:return False
    bracket=re.search(r'\[([^\]]+)\]',expression)
    if not bracket:raise ValueError('TIMETABLE_WEEK_EXPRESSION_UNRECOGNIZED')
    spec=bracket[1].replace('周','').replace('，',',').replace('、',',')
    ranges=[]
    for part in spec.split(','):
        match=re.fullmatch(r'\s*(\d+)(?:\s*-\s*(\d+))?\s*',part)
        if not match:raise ValueError('TIMETABLE_WEEK_EXPRESSION_UNRECOGNIZED')
        ranges.append((int(match[1]),int(match[2] or match[1])))
    return any(start<=number<=end for start,end in ranges)


def timetable(args):
    state=ncut.load_session(args.account)
    setup_info,raw=ncut.fetch('https://jwxtbk.ncut.edu.cn/jsxsd/xskb/xskb_list.do',state=state)
    if not setup_info['ok']:ncut.emit(setup_info);return
    setup=parse_setup(raw);term=args.term or setup['current_term']['id']
    found=[t for t in setup['terms'] if t['id']==term]
    if not found:raise ValueError('Unknown semester; select from the actual school options')
    rq='all';week_label='全部周次';week_no=None
    if args.week=='current' or args.date:
        if term!=setup['current_term']['id']:raise ValueError('Current-date filtering requires the current semester')
        date=dt.date.fromisoformat(args.date or ncut.now()[:10]);weeks=setup['weeks']
        candidates=[w for w in weeks if 0<=(date-dt.date.fromisoformat(w['start'])).days<7]
        if len(candidates)!=1:raise ValueError('Date does not match exactly one school calendar week')
        rq=candidates[0]['start'];week_label=candidates[0]['label']
        week_no=next(i+1 for i,w in enumerate(weeks) if w['start']==rq)
    # The all-week fragment is reliable and contains exact ranges/parity. Avoid
    # the school's slow date-specific rendering; filter the actual ranges locally.
    params={'rq':'all','sjmsValue':setup['mode'],'xnxqid':term,'xswk':'false'}
    info,raw=ncut.fetch('https://jwxtbk.ncut.edu.cn/jsxsd/framework/mainV_index_loadkb_10009.jsp?'+up.urlencode(params),state=state)
    if not info['ok']:ncut.emit(info);return
    entries,unarranged=parse_grid(raw)
    if week_no:
        entries=[e for e in entries if in_week(e['weeks'],week_no)]
        unarranged=[e for e in unarranged if int(e['start_week'])<=week_no<=int(e['end_week'])]
    if args.date:entries=[e for e in entries if e['weekday']==dt.date.fromisoformat(args.date).isoweekday()]
    result={**info,'account':args.account,'semester':{'id':term,'name':found[0]['name']},'week':week_label,'week_start':None if rq=='all' else rq,'date':args.date,'entry_count':len(entries),'entries':sorted(entries,key=lambda e:(e['weekday'],e['time'] or '','weeks')),'unarranged':unarranged}
    if args.output:
        from pathlib import Path
        file=Path(args.output).expanduser()
        if not file.is_absolute() or not file.is_relative_to(ncut.STATE):raise ValueError('Save private timetable results under '+str(ncut.STATE))
        ncut.private_write(file,json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        ncut.emit({k:v for k,v in result.items() if k not in ('entries','unarranged')}|{'output':str(file),'unarranged_count':len(unarranged)})
    else:ncut.emit(result)
