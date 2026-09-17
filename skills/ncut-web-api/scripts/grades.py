"""Verified undergraduate grade query; saved HTTP session, no UI on normal calls."""
import json
from pathlib import Path
import re
import urllib.parse as up

from academic import Document
import ncut

ORIGIN = 'https://jwxtbk.ncut.edu.cn'
QUERY = '/jsxsd/kscj/cjcx_query'
LIST = '/jsxsd/kscj/cjcx_list'


def parse_query(raw):
    text = raw.decode('utf-8')
    forms = Document(text).root.all('form', id='kscjQueryForm')
    if len(forms) != 1 or forms[0].attrs.get('method', '').lower() != 'post':
        raise ValueError('GRADES_QUERY_SCHEMA_CHANGED: query form missing')
    actions = re.findall(r'''var\s+actionUrl\s*=\s*["']([^"']+)["']''', text)
    if actions != [LIST]:
        raise ValueError('GRADES_QUERY_SCHEMA_CHANGED: query action changed')
    form = forms[0]
    if len([s for s in form.all('select') if s.attrs.get('name') == 'kksj']) != 1:
        raise ValueError('GRADES_QUERY_SCHEMA_CHANGED: ambiguous semester control')
    params = {node.attrs['name']: node.attrs.get('value', '') for node in form.all('input')
              if node.attrs.get('name') and (node.attrs.get('type', 'text') in ('text', 'hidden') or
                 (node.attrs.get('type') == 'checkbox' and 'checked' in node.attrs))}
    terms = []
    for select in form.all('select'):
        name = select.attrs.get('name')
        options = select.all('option')
        if not name or not options:
            raise ValueError('GRADES_QUERY_SCHEMA_CHANGED: incomplete control')
        selected = [option for option in options if 'selected' in option.attrs]
        if len(selected) > 1:
            raise ValueError('GRADES_QUERY_SCHEMA_CHANGED: ambiguous default')
        params[name] = (selected or options)[0].attrs.get('value', '')
        if name == 'kksj':
            terms = [{'id': o.attrs['value'], 'name': o.text()} for o in options if o.attrs.get('value')]
    if not terms or len({t['id'] for t in terms}) != len(terms) or any(
            not re.fullmatch(r'\d{4}-\d{4}-\d+', t['id']) for t in terms):
        raise ValueError('GRADES_QUERY_SCHEMA_CHANGED: semester options missing or ambiguous')
    display = [s for s in form.all('select') if s.attrs.get('name') == 'xsfs']
    if len(display) != 1 or 'all' not in {o.attrs.get('value') for o in display[0].all('option')}:
        raise ValueError('GRADES_QUERY_SCHEMA_CHANGED: all-attempts option missing')
    params['xsfs'] = 'all'  # Preserve repeated attempts; never silently choose the highest score.
    terms.sort(key=lambda t: tuple(map(int, t['id'].split('-'))), reverse=True)
    return terms, params


def parse_grades(raw, term):
    tables = Document(raw.decode('utf-8')).root.all('table', id='dataList')
    if len(tables) != 1:
        raise ValueError('GRADES_RESPONSE_UNVERIFIED: grade table missing')
    rows = [[c for c in row.children if not isinstance(c, str) and c.tag in ('th', 'td')]
            for row in tables[0].all('tr')]
    if not rows:
        raise ValueError('GRADES_RESPONSE_UNVERIFIED: grade headers missing')
    headers = [re.sub(r'\s+', '', c.text()) for c in rows[0]]
    score_columns = [i for i, h in enumerate(headers) if h in ('成绩', '成绩（原始成绩）', '成绩(原始成绩)')]
    required = {'semester': '开课学期', 'course_id': '课程编号', 'course': '课程名称', 'credits': '学分'}
    if len(score_columns) != 1 or any(headers.count(label) != 1 for label in required.values()):
        raise ValueError('GRADES_RESPONSE_UNVERIFIED: grade columns changed')
    fields = {key: headers.index(label) for key, label in required.items()}
    fields['score'] = score_columns[0]
    for key, label in {'usual_weight': '平时成绩比例（%）', 'usual_score': '平时成绩',
                       'final_score': '期末成绩', 'score_note': '成绩标识',
                       'hours': '总学时', 'exam_type': '考试性质'}.items():
        if headers.count(label) == 1:
            fields[key] = headers.index(label)
    entries = []
    empty = False
    for cells in rows[1:]:
        if len(cells) == 1 and cells[0].attrs.get('colspan') == str(len(headers)) and re.fullmatch(
                r'(?:暂无数据|暂无记录|无数据|未查询到数据|未查询到记录|没有查询到数据|没有查询到记录)[！!。.]?', cells[0].text()):
            empty = True
            continue
        if len(cells) != len(headers):
            raise ValueError('GRADES_RESPONSE_UNVERIFIED: incomplete grade row')
        row = {key: cells[index].text() for key, index in fields.items()}
        if row['semester'] not in (term['id'], term['name']):
            raise ValueError('GRADES_TERM_MISMATCH: server ignored the selected semester')
        if not row['course_id'] or not row['course'] or not row['score']:
            raise ValueError('GRADES_RESPONSE_UNVERIFIED: course or score missing')
        entries.append(row)
    if empty and entries:
        raise ValueError('GRADES_RESPONSE_UNVERIFIED: conflicting empty marker')
    return entries


def grades(args):
    state = ncut.load_session(args.account)
    info, raw = ncut.fetch(ORIGIN+QUERY, state=state, expect='html')
    if not info['ok']:
        ncut.emit(info)
        return
    terms, params = parse_query(raw)
    selected = [term for term in terms if term['id'] == args.term] if args.term else terms
    if not selected:
        ncut.emit({'ok': False, 'code': 'GRADES_UNKNOWN_TERM', 'available_terms': terms})
        return
    checked, entries, chosen = [], [], None
    for term in selected:
        params['kksj'] = term['id']
        info, raw = ncut.fetch(ORIGIN+LIST, method='POST', data=up.urlencode(params).encode(),
                              content_type='application/x-www-form-urlencoded', state=state, expect='html')
        if not info['ok']:
            ncut.emit({**info, 'checked_terms': checked, 'failed_term': term})
            return
        entries = parse_grades(raw, term)
        checked.append(term)
        if entries or args.term:
            chosen = term
            break
    result = {**info, 'code': 'GRADES_FOUND' if entries else 'GRADES_EMPTY',
              'account': args.account, 'semester': chosen, 'checked_terms': checked,
              'available_terms': terms, 'entry_count': len(entries), 'entries': entries,
              'selection': 'specified_term' if args.term else 'latest_term_with_results'}
    if args.output:
        dest = Path(args.output).expanduser().resolve()
        if not dest.is_relative_to(ncut.STATE.resolve()):
            raise ValueError('Save private grade results under '+str(ncut.STATE))
        ncut.private_write(dest, json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        ncut.emit({k: v for k, v in result.items() if k != 'entries'} | {'output': str(dest)})
    else:
        ncut.emit(result)
