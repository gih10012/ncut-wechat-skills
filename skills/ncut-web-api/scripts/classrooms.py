"""Empty classroom query: current form, readonly API, local filtering. Stdlib only."""
import datetime as dt
from session_http import cookie_jar, merged_state
import json
from pathlib import Path
import re
import urllib.parse as up
from academic import Document
import ncut

ORIGIN = 'https://jwxtbk.ncut.edu.cn'
FORM = '/jiaowu/pkgl/llsykb/llsykb_find_jx0601_kx.htmlx'
QUERY = '/jiaowu/kxjsgl/kxjsgl.do?method=queryJsjyxx'
ENTRY = '/jsxsd/view/kbxx/kbcx/llsykb_frm.jsp'


def minutes(value):
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise ValueError('Use HH:MM, within one day')
    h, m = map(int, value.split(':'))
    return h * 60 + m


def parse_form(raw, date, start, end, campus):
    html = raw.decode('utf-8'); root = Document(html).root
    term = root.all('input', id='xnxqh')
    weeks = root.all('select', id='zc'); campuses = root.all('select', id='xqbh')
    mode = re.search(r'''["']jxzlid["']\s*:\s*["']([A-Za-z0-9_-]+)["']''', html)
    if len(term) != 1 or len(weeks) != 1 or len(campuses) != 1 or not mode:
        raise ValueError('CLASSROOM_FORM_CHANGED: query controls missing')
    semester = term[0].attrs.get('value', '')
    term_match = re.fullmatch(r'(\d{4})-(\d{4})-([12])', semester)
    if not term_match or int(term_match[2]) != int(term_match[1]) + 1:
        raise ValueError('CLASSROOM_SEMESTER_CHANGED')
    # Infer the first week year from the actual semester, then follow school
    # week numbers. Checking all labels avoids matching the same MM-DD next year.
    week_rows = []
    for option in weeks[0].all('option'):
        m = re.search(r'\((\d{2})\.(\d{2})-(\d{2})\.(\d{2})\)', option.text())
        if not m or not option.attrs.get('value', '').isdigit():
            raise ValueError('CLASSROOM_WEEK_LABEL_CHANGED')
        week_rows.append((int(option.attrs['value']), tuple(map(int, m.groups()))))
    first = [dates for number, dates in week_rows if number == 1]
    if len(first) != 1:
        raise ValueError('CLASSROOM_WEEK_ONE_MISSING')
    year = int(term_match[1] if term_match[3] == '1' else term_match[2])
    anchor = dt.date(year, first[0][0], first[0][1]); selected = []
    for number, (sm, sd, em, ed) in week_rows:
        begin = anchor + dt.timedelta(weeks=number-1); finish = begin + dt.timedelta(days=6)
        if begin.weekday() != 0 or (begin.month, begin.day, finish.month, finish.day) != (sm, sd, em, ed):
            raise ValueError('CLASSROOM_CALENDAR_CHANGED')
        if begin <= date <= finish: selected.append(str(number))
    if len(selected) != 1:
        raise ValueError('Date does not match exactly one current school week')
    matches = [(o.attrs.get('value'), o.text()) for o in campuses[0].all('option') if campus in (o.attrs.get('value'), o.text()) and o.attrs.get('value')]
    if len(matches) != 1: raise ValueError('Unknown or ambiguous campus')
    lo, hi = minutes(start), minutes(end)
    if lo >= hi: raise ValueError('End must follow start within the same day')
    periods = []
    for node in root.all(cls='jcclass'):
        clocks = re.findall(r'\d{2}:\d{2}', node.text()); code = node.attrs.get('data-value', '')
        if len(clocks) != 2 or not re.fullmatch(r'\d{4}', code):
            raise ValueError('CLASSROOM_PERIODS_CHANGED')
        begin, finish = map(minutes, clocks)
        if begin >= finish: raise ValueError('CLASSROOM_PERIODS_CHANGED')
        if begin < hi and finish > lo: periods.append({'code': code, 'start': clocks[0], 'end': clocks[1]})
    periods.sort(key=lambda p: p['start'])
    if not periods or lo < minutes(periods[0]['start']) or hi > minutes(periods[-1]['end']):
        raise ValueError('Requested interval extends outside the available teaching periods')
    params = dict(xnxqh=semester, xqbh=matches[0][0], jxlbh='', jsbh='', bjfh='=', rnrs='', zc=selected[0], xq=str(date.isoweekday()), jc=','.join(p['code'] for p in periods), jxzlid=mode[1])
    return params, periods, matches[0][1]


def free_rooms(data, params, date, query):
    if not isinstance(data, dict) or data.get('success') is not True or not isinstance(data.get('dataList'), list) or not isinstance(data.get('xqmxList'), list):
        raise ValueError('CLASSROOM_RESPONSE_CHANGED: no verified room list')
    days = [d for d in data['xqmxList'] if isinstance(d, dict) and str(d.get('xqid')) == params['xq']]
    if len(days) != 1 or days[0].get('mxrq') != date.strftime('%m-%d'):
        raise ValueError('CLASSROOM_RESPONSE_DATE_MISMATCH')
    keys = [params['xq'] + p for p in params['jc'].split(',')]; found = []
    for room in data['dataList']:
        if not isinstance(room, dict) or not {'jsid','jsmc','jslx','yxzws','xqid','zt'}.issubset(room):
            raise ValueError('CLASSROOM_ROOM_FIELDS_CHANGED')
        flags = [room.get(k, '0') for k in keys]
        if any(str(f) not in ('0','1') for f in flags):
            raise ValueError('CLASSROOM_OCCUPANCY_CHANGED')
        if any(str(f) == '1' for f in flags): continue
        if room['jslx'] != '普通教室' or str(room['zt']) != '1' or str(room['xqid']) != params['xqbh']: continue
        seats = int(room['yxzws'] or 0)
        if seats <= 0 or any(word in room['jsmc'] for word in ('实验室','实习工厂')): continue
        if query and query.casefold() not in room['jsmc'].casefold(): continue
        found.append({'id':room['jsid'], 'name':room['jsmc'], 'seats':seats})
    return sorted(found, key=lambda r:r['name'])


def classrooms(args):
    date = dt.date.fromisoformat(args.date); minutes(args.start); minutes(args.end)
    if args.start >= args.end: raise ValueError('End must follow start')
    output = Path(args.output).expanduser() if args.output else None
    if output and (not output.is_absolute() or not output.is_relative_to(ncut.STATE)):
        raise ValueError('Save private results under '+str(ncut.STATE))
    state = ncut.load_session(args.account); jar = cookie_jar(state)
    def get(path):
        return ncut.fetch(ORIGIN+path, state=state, cookie_jar=jar)
    info, raw = get(FORM)
    # A missing root application session is different from expired /jsxsd login.
    # Exchange only on an authentication response, at most once, without a browser.
    if info.get('code') in ('AUTH_REQUIRED','REDIRECT'):
        info, raw = get(ENTRY)
        if not info['ok']: ncut.emit(info); return
        frames = [n.attrs.get('src','') for n in Document(raw.decode('utf-8')).root.all() if n.tag in ('frame','iframe')]
        urls = [up.urljoin(ORIGIN+ENTRY, src) for src in frames]
        urls = [u for u in urls if ncut.origin(u) == ORIGIN and up.urlsplit(u).path == '/Logon.do']
        if len(urls) != 1: raise ValueError('CLASSROOM_HANDOFF_CHANGED')
        info, _ = ncut.fetch(urls[0], state=state, cookie_jar=jar)
        if not info['ok']: ncut.emit(info); return
        info, raw = get(FORM)
    if not info['ok']: ncut.emit(info); return
    params, periods, campus = parse_form(raw,date,args.start,args.end,args.campus)
    info, _ = ncut.fetch(ORIGIN+QUERY, method='POST', data=up.urlencode(params).encode(), content_type='application/x-www-form-urlencoded', state=state, cookie_jar=jar, expect='json')
    if not info['ok']: ncut.emit({k:v for k,v in info.items() if k != 'data'}); return
    rooms = free_rooms(info.pop('data'), params, date, args.query)
    refreshed = merged_state(state,jar)
    if refreshed != state: ncut.private_write(ncut.account_path(args.account),json.dumps(refreshed,ensure_ascii=False))
    result = {'ok':True, 'fetched_at':info['fetched_at'], 'date':args.date, 'start':args.start, 'end':args.end, 'campus':campus, 'semester':params['xnxqh'], 'week':int(params['zc']), 'checked_periods':periods, 'matched':len(rooms), 'rooms':rooms, 'availability_scope':'学校排课及借用记录；不代表现场无人或有借用权限', 'remote_write_performed':False}
    if output:
        ncut.private_write(output,json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        result['output'] = str(output)
    result['rooms'] = rooms[:max(1,min(args.limit,30))]; result['truncated'] = len(result['rooms']) < len(rooms)
    ncut.emit(result)
