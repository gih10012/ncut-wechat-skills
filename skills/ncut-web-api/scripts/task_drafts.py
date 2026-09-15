"""Persist a reviewable reservation task draft; no scheduler or booking side effects."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import ncut


def task_path(task_id):
    if not re.fullmatch(r'[0-9a-f]{20}',task_id):raise ValueError('Invalid task ID')
    return ncut.STATE/'tasks'/(task_id+'.json')


def validate(task):
    if task.get('schema_version')!=1 or task.get('kind')!='badminton-reservation' or task.get('status')!='draft' or task.get('enabled') is not False or task.get('validation_only') is not True:
        raise ValueError('Unsupported task state; this command only handles disabled validation drafts')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',task.get('account','')) or not task.get('intent'):
        raise ValueError('Task account and intent are required')
    return {'schema_valid':True,'booking_ready':False,'missing_for_real_booking':['用户指定的预约日期/时段/场馆','当前真实资源和时间段匹配','可用的预约验证步骤','明确实际订场授权'],'scheduler_registered':False,'remote_write_performed':False}


def main(args):
    if args.operation=='show':
        file=task_path(args.id);task=json.loads(ncut.private_read(file));ncut.emit({'ok':True,'task':task,'validation':validate(task),'file':str(file)});return
    if args.operation=='list':
        rows=[]
        for file in sorted((ncut.STATE/'tasks').glob('*.json')):
            task=json.loads(ncut.private_read(file))
            rows.append({k:task.get(k) for k in ['id','kind','account','status','created_at','intent']})
        ncut.emit({'ok':True,'tasks':rows[:20],'total':len(rows)});return
    if not args.validation_only:raise ValueError('This adapter currently creates validation-only drafts; it does not schedule real reservations')
    content={'schema_version':1,'kind':'badminton-reservation','account':args.account,'intent':args.intent,'status':'draft','enabled':False,'validation_only':True}
    validate(content)
    task_id=hashlib.sha256((args.account+'\0'+args.key).encode()).hexdigest()[:20]
    file=task_path(task_id);file.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=os.open(file.parent/'.lock',os.O_CREAT|os.O_RDWR,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX)
        replay=file.exists()
        if replay:
            task=json.loads(ncut.private_read(file))
            if any(task.get(k)!=v for k,v in content.items()):raise ValueError('Idempotency key was already used for a different task')
        else:
            task={**content,'id':task_id,'created_at':ncut.now(),'source_capability':'badminton-reservation-draft'}
            ncut.private_write(file,json.dumps(task,ensure_ascii=False,indent=2)+'\n')
        actual=json.loads(ncut.private_read(file))
        if actual!=task:raise ValueError('Task readback mismatch')
        ncut.emit({'ok':True,'task':actual,'validation':validate(actual),'file':str(file),'idempotent_replay':replay,'readback_verified':True})
    finally:os.close(lock)
