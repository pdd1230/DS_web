from __future__ import annotations
import concurrent.futures, os, subprocess, sys, threading, time
from datetime import datetime,timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel,Field
from core import *
app=FastAPI(title='DeepSight internal worker',docs_url=None,redoc_url=None)
executor=concurrent.futures.ThreadPoolExecutor(max_workers=1)
lock=threading.RLock()
children=set()
TOKEN=os.environ.get('DS_API_KEY','')
SETTINGS={'YOLO_CONFIDENCE':(0.01,1.0),'YOLO_IMAGE_SIZE':(320,1920),'MIN_FACE_SIZE':(1,500),'MOSAIC_SIZE':(2,100),'FACE_PADDING_RATIO':(0,0.5)}

class JobRequest(BaseModel):
    jobId:str;runId:str;kind:Literal['compare','initial','baseline','analyze','import_compare','import_initial','import_baseline']
    revision:int=Field(ge=1,le=9999)
    settings:dict[str,float|int]=Field(default_factory=dict)
class ValidateRequest(BaseModel):datasetId:str

def auth(x_ds_key:str=Header(default='')):
    import hmac
    if not TOKEN or not hmac.compare_digest(x_ds_key,TOKEN):raise HTTPException(401,'Invalid internal API key')

def status_path(jobid):return STORE/'jobs'/(identifier(jobid)+'.json')
def update(jobid,**fields):
    with lock:
        p=status_path(jobid);old=read_json(p);old.update(fields);atomic_json(p,old)

def worker(request):
    jobid=request['jobId'];run=STORE/'runs'/request['runId'];log=run/'logs'/(jobid+'.log');log.parent.mkdir(exist_ok=True)
    request_file=run/'requests'/(jobid+'.json');atomic_json(request_file,request)
    update(jobid,status='RUNNING',progress=1)
    try:
        env=dict(os.environ,PYTHONUNBUFFERED='1',PYTHONIOENCODING='utf-8',CUDA_VISIBLE_DEVICES='',MPLBACKEND='Agg')
        with log.open('w',encoding='utf-8') as out:
            proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('runner.py')),str(request_file)],stdout=out,stderr=subprocess.STDOUT,env=env)
            with lock:children.add(proc)
            started=time.monotonic()
            while proc.poll() is None:
                if time.monotonic()-started>int(os.environ.get('DS_JOB_TIMEOUT','3600')):
                    proc.kill();proc.wait();raise TimeoutError('작업 제한 시간 초과')
                time.sleep(.3)
            with lock:children.discard(proc)
            if proc.returncode:raise RuntimeError('추론/분석 실패. 실행 로그를 확인하세요.')
        report=next((line[len('DS_REPORT='):] for line in reversed(log.read_text(encoding='utf-8').splitlines()) if line.startswith('DS_REPORT=')),None)
        if not report:raise RuntimeError('완료 매니페스트 없음')
        update(jobid,status='COMPLETED',progress=100,report=report,error='')
    except Exception as exc:update(jobid,status='FAILED',error=str(exc))

@app.on_event('startup')
def recover():
    (STORE/'jobs').mkdir(parents=True,exist_ok=True)
    for p in (STORE/'jobs').glob('*.json'):
        v=read_json(p)
        if v.get('status') in ('QUEUED','RUNNING'):update(p.stem,status='FAILED',error='Python 재시작으로 중단됨. 기존 결과는 보존됩니다. 새 실험으로 다시 실행하세요.')

@app.on_event('shutdown')
def shutdown():
    with lock:
        for proc in list(children):
            if proc.poll() is None:proc.kill()
    executor.shutdown(wait=False,cancel_futures=True)

@app.get('/health')
def health(_=Depends(auth)):
    model=LEGACY/'shared/models/yolov8n-face-lindevs.pt'
    return {'status':'ok','python':sys.version.split()[0],'modelExists':model.exists(),'storage':str(STORE),'freeBytes':__import__('shutil').disk_usage(STORE).free}

@app.post('/datasets/validate')
def validate(r:ValidateRequest,_=Depends(auth)):
    try:return {'images':validate_dataset(STORE/'datasets'/identifier(r.datasetId)/'data')}
    except Exception as exc:raise HTTPException(400,str(exc))

@app.post('/jobs',status_code=202)
def submit(r:JobRequest,_=Depends(auth)):
    try:
        identifier(r.jobId);identifier(r.runId)
        run=STORE/'runs'/r.runId
        if not (run/'data/ground_truth.csv').is_file():raise ValueError('실험 입력 없음')
        for k,v in r.settings.items():
            if k not in SETTINGS or not SETTINGS[k][0]<=v<=SETTINGS[k][1]:raise ValueError('허용되지 않는 설정: '+k)
            if k in ('YOLO_IMAGE_SIZE','MIN_FACE_SIZE','MOSAIC_SIZE') and v!=int(v):raise ValueError('정수 설정 필요: '+k)
        payload=r.model_dump()
        for k in ('YOLO_IMAGE_SIZE','MIN_FACE_SIZE','MOSAIC_SIZE'):
            if k in payload['settings']:payload['settings'][k]=int(payload['settings'][k])
        with lock:
            p=status_path(r.jobId)
            if p.exists():
                old=read_json(p)
                if old['runId']!=r.runId:raise ValueError('중복 작업 ID 충돌')
                return old
            atomic_json(p,{'id':r.jobId,'runId':r.runId,'status':'QUEUED','progress':0,'error':'','createdAt':datetime.now(timezone.utc).isoformat()})
            executor.submit(worker,payload)
        return read_json(p)
    except ValueError as exc:raise HTTPException(400,str(exc))

@app.get('/jobs/{jobid}')
def get_job(jobid:str,_=Depends(auth)):
    try:p=status_path(jobid)
    except ValueError:raise HTTPException(400,'Invalid ID')
    if not p.exists():raise HTTPException(404,'작업 없음')
    v=read_json(p);log=STORE/'runs'/v['runId']/'logs'/(jobid+'.log')
    v['log']=log.read_text(encoding='utf-8',errors='replace')[-48000:] if log.exists() else ''
    import re
    matches=re.findall(r'\[(\d+)/(\d+)\]',v['log'])
    if matches and v['status']=='RUNNING':
        a,b=map(int,matches[-1]);v['progress']=min(95,int(a/max(1,b)*90))
    return v
