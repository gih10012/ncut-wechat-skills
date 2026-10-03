"""Assigned Safety Companion tasks, course materials and progress readback."""
import json
import urllib.parse as up
from pathlib import Path

from ncut import emit, fetch, load_session, service, STATE, private_read, private_write, now


def _post(state, auth, path, fields):
    url = service('weiban')['origins'][0] + '/pharos/' + path.lstrip('/')
    body = up.urlencode({
        'tenantCode': auth['tenantCode'],
        'userId': auth['userId'],
        **fields,
    }).encode()
    info, _ = fetch(url, method='POST', data=body,
                    content_type='application/x-www-form-urlencoded;charset=utf8',
                    state=state, expect='json', timeout=20)
    if not info['ok']:
        if info.get('status') == 701:
            return {**info, 'code': 'ACCOUNT_TEMPORARILY_LOCKED',
                    'hint': 'Follow the native access-denial page; stop requests until its stated unlock time, then re-enter normally.'}, None
        return info, None
    wrapper = info.get('data')
    if not isinstance(wrapper, dict) or str(wrapper.get('code')) != '0':
        detail_code = wrapper.get('detailCode') if isinstance(wrapper, dict) else None
        return {**info, 'ok': False,
                'code': 'AUTH_REQUIRED' if str(detail_code) == '-105' else 'BUSINESS_ERROR'}, None
    return info, wrapper.get('data')


def status(args):
    state = load_session(args.account)
    auth = state.get('service_data', {}).get('weiban', {})
    header = state.get('headers', {}).get(service('weiban')['origins'][0], {})
    if not auth.get('userId') or not auth.get('tenantCode') or not header.get('X-Token'):
        emit({'ok': False, 'code': 'AUTH_REQUIRED',
              'hint': 'Safety Companion session has not been captured for this account.'})
        return
    info, tasks = _post(state, auth, 'index/listStudyTask.do', {})
    if tasks is None:
        emit(info); return
    rows = tasks.get('studyTaskList', []) if isinstance(tasks, dict) else []
    if not args.all and rows:
        active = [r for r in rows if r.get('endTime') and r.get('startTime') and r['startTime'] <= info['fetched_at'][:10] <= r['endTime']]
        rows = sorted(active, key=lambda r: r['startTime'], reverse=True)[:1] or rows[:1]
    projects = []
    for row in rows:
        project_id = row.get('userProjectId')
        if not project_id:
            continue
        pinfo, progress = _post(state, auth, 'project/showProgress.do', {'userProjectId': project_id})
        einfo, exams = _post(state, auth, 'exam/listPlan.do', {'userProjectId': project_id})
        if progress is None:
            emit(pinfo); return
        if exams is None:
            emit(einfo); return
        projects.append({
            'project_id': project_id,
            'name': row.get('projectName'),
            'start_date': row.get('startTime'),
            'end_date': row.get('endTime'),
            'state': progress.get('studyStateLabel'),
            'progress_percent': progress.get('progressPet'),
            'courses': {'finished': progress.get('requiredFinishedNum'), 'total': progress.get('requiredNum')},
            'assessed_exams': {'finished': progress.get('examFinishedNum'), 'total': progress.get('examAssessmentNum')},
            'exams': [{
                'exam_plan_id': exam.get('id'),
                'name': exam.get('examPlanName'),
                'score': exam.get('examScore'),
                'finished_attempts': exam.get('examFinishNum'),
                'remaining_attempts': exam.get('examOddNum'),
                'pass_score': exam.get('passScore'),
                'end_time': exam.get('endTime'),
                'is_makeup': exam.get('isRetake') == 1,
                'available': exam.get('examTimeState') == 2,
            } for exam in exams if exam.get('displayState') == 1],
        })
    emit({'ok': True, 'account': args.account, 'source': 'live',
          'fetched_at': info['fetched_at'], 'projects': projects})


def assigned_courses(state, auth, project_id):
    info, tasks = _post(state, auth, 'index/listStudyTask.do', {})
    if tasks is None:
        return info, None
    project = next((r for r in tasks.get('studyTaskList', []) if r.get('userProjectId') == project_id), None)
    if project is None:
        return {'ok': False, 'code': 'PROJECT_NOT_ASSIGNED'}, None
    info, categories = _post(state, auth, 'usercourse/listCategory.do', {'userProjectId': project_id, 'chooseType': 3})
    if categories is None:
        return info, None
    courses = []
    for category in categories:
        info, rows = _post(state, auth, 'usercourse/listCourse.do', {'userProjectId': project_id, 'chooseType': 3, 'categoryCode': category['categoryCode']})
        if rows is None:
            return info, None
        courses.extend({**r, 'categoryCode': category['categoryCode']} for r in rows)
    return {'ok': True, 'project': project}, courses


def courses(args):
    state = load_session(args.account)
    auth = state.get('service_data', {}).get('weiban', {})
    if not auth.get('userId') or not auth.get('tenantCode'):
        emit({'ok': False, 'code': 'AUTH_REQUIRED'}); return
    info, rows = assigned_courses(state, auth, args.project)
    if rows is None:
        emit(info); return
    emit({'ok': True, 'project_id': args.project, 'project_name': info['project']['projectName'],
          'courses': [{'course_id': r['resourceId'], 'user_course_id': r['userCourseId'],
                       'name': r['resourceName'], 'category': r.get('categoryName'),
                       'finished': str(r.get('finished')) == '1', 'source': r.get('source')} for r in rows]})


def course(args):
    state = load_session(args.account)
    auth = state.get('service_data', {}).get('weiban', {})
    if not auth.get('userId') or not auth.get('tenantCode'):
        emit({'ok': False, 'code': 'AUTH_REQUIRED'}); return
    info, rows = assigned_courses(state, auth, args.project)
    if rows is None:
        emit(info); return
    row = next((r for r in rows if r.get('resourceId') == args.course), None)
    if row is None:
        emit({'ok': False, 'code': 'COURSE_NOT_ASSIGNED'}); return
    if args.action == 'verify':
        finished = str(row.get('finished')) == '1'
        emit({'ok': True, 'name': row['resourceName'], 'finished': finished,
              'code': 'COURSE_FINISHED' if finished else 'COURSE_NOT_FINISHED'}); return
    if str(row.get('finished')) == '1':
        emit({'ok': True, 'already_finished': True, 'name': row['resourceName']}); return
    if row.get('source') != 1:
        emit({'ok': False, 'code': 'COURSE_SOURCE_UNVERIFIED'}); return
    record = STATE / 'safety' / args.account / args.project / (row['userCourseId'] + '.json')
    fields = {'userProjectId': args.project, 'courseId': args.course}
    if args.action == 'start':
        if record.exists() and json.loads(private_read(record)).get('submission_started_at'):
            emit({'ok': False, 'code': 'USE_NATIVE_COMPLETION_FLOW',
                  'hint': 'A prior completion remains unresolved; opening it again must not reset the submission record.'}); return
        info, _ = _post(state, auth, 'usercourse/study.do', fields)
        if not info['ok']:
            emit({k: v for k, v in info.items() if k != 'data'}); return
        info, url = _post(state, auth, 'usercourse/getCourseUrl.do', fields)
        if not isinstance(url, str):
            emit({k: v for k, v in info.items() if k != 'data'}); return
        parsed = up.urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname != 'mcwk.mycourse.cn':
            emit({'ok': False, 'code': 'MATERIAL_ORIGIN_UNVERIFIED'}); return
        params = up.parse_qs(parsed.query)
        private_write(record, json.dumps({'url': url, 'started_at': now(), 'course_id': args.course,
                                         'user_course_id': row['userCourseId'], 'cs_capt': params.get('csCapt', [''])[0]}, ensure_ascii=False))
        emit({'ok': True, 'name': row['resourceName'], 'material_url': parsed._replace(query='', fragment='').geturl(),
              'private_record': str(record), 'captcha_required': params.get('csCapt', [''])[0] != 'false'}); return
