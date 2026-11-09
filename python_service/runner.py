"""One isolated process per job. Original Python sources remain byte-for-byte intact."""
from __future__ import annotations
import contextlib, importlib.util, io, json, os, re, shutil, sys, uuid
from pathlib import Path
from core import *

def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

def work_bind(module, work):
    values={'BASE_DIR':work,'INPUT_DIR':work/'data/images','OUTPUT_DIR':work/'outputs',
            'GT_PATH':work/'data/ground_truth.csv','GROUND_TRUTH_PATH':work/'data/ground_truth.csv',
            'MODEL_PATH':LEGACY/'shared/models/yolov8n-face-lindevs.pt',
            'YOLO_MODEL_PATH':LEGACY/'shared/models/yolov8n-face-lindevs.pt'}
    for name,value in values.items():
        if hasattr(module,name):setattr(module,name,value)

class Tee:
    def __init__(self):self.saved=io.StringIO();self.real=sys.stdout
    def write(self,text):self.saved.write(text);self.real.write(text);return len(text)
    def flush(self):self.real.flush()

def normalize(work,kind,experiment_id):
    gt={r['파일명']:r for r in csv_rows(work/'data/ground_truth.csv')}
    rows=[];summaries=[]
    if kind=='compare':
        summaries=csv_rows(work/'outputs/policy_comparison.csv')
        for policy in POLICIES:
            folder=work/'outputs/experiments'/policy
            candidates=csv_rows(folder/'detection_details.csv');faces=csv_rows(folder/'face_mosaic_results.csv')
            for r in csv_rows(folder/'test_cases_detailed.csv'):
                fn=r['input_filename'];path=folder/(Path(fn).stem+'_mosaic'+Path(fn).suffix)
                rows.append({'filename':fn,'policy':policy,'groundTruth':int(r['ground_truth']),
                    'detected':int(r['detected']) if r['detected']!='' else None,
                    'evaluation':r['evaluation'],'processingStatus':r['processing_status'],
                    'reviewRequired':r['manual_review_required']=='yes','scene':r['scene'],'note':r['gt_note'],
                    'image':path.relative_to(work/'outputs').as_posix() if path.exists() else '',
                    'candidates':[c for c in candidates if c['image_name']==fn],
                    'faces':[c for c in faces if c['image_name']==fn and c['status']=='detected']})
    else:
        policy='initial' if kind=='initial' else 'baseline';folder=work/'outputs'/('first' if kind=='initial' else 'second-baseline')
        if kind=='initial':
            metrics=read_json(work/'initial_counts.json');face_rows=[]
        else:
            face_rows=csv_rows(folder/'face_mosaic_results.csv');metrics={}
            for fn in gt:metrics[fn]=sum(r['image_name']==fn and r['status']=='detected' for r in face_rows)
        counts={'total':len(gt),'evaluated':0,'exact':0,'over':0,'under':0,'failed':0}
        for fn,g in gt.items():
            img=folder/(Path(fn).stem+'_mosaic'+Path(fn).suffix)
            pred=metrics.get(fn) if img.exists() else None
            actual=int(g['실제 얼굴 수']);delta=None if pred is None else pred-actual
            label='Not Evaluated' if delta is None else ('Exact Match' if delta==0 else 'Over-detection' if delta>0 else 'Under-detection')
            counts['failed' if delta is None else 'evaluated']+=1
            if delta is not None:counts['exact' if delta==0 else 'over' if delta>0 else 'under']+=1
            rows.append({'filename':fn,'policy':policy,'groundTruth':actual,'detected':pred,'evaluation':label,
               'processingStatus':('historical_count_unknown' if kind=='initial' and img.exists() else 'not_processed') if pred is None else 'processed_detected' if pred else 'processed_no_face',
               'reviewRequired':True,'scene':g.get('scene',''),'note':g.get('note',''),
               'image':img.relative_to(work/'outputs').as_posix() if img.exists() else '',
               'candidates':[],'faces':[r for r in face_rows if r['image_name']==fn and r['status']=='detected']})
        counts['policy']=policy;counts['exact_match_pct']=round(counts['exact']/counts['evaluated']*100,2) if counts['evaluated'] else ''
        summaries=[counts]
        # Adapter report supplements initial script; it does not invent face coordinates.
        write_csv(folder/'web_evaluation.csv',['filename','policy','groundTruth','detected','evaluation','processingStatus'],rows)
    return {'experimentId':experiment_id,'kind':kind,'summaries':summaries,'results':rows}

def infer(request,run,work):
    import torch
    torch.set_num_threads(int(os.environ.get('DS_CPU_THREADS','2')))
    kind=request['kind']
    if kind=='compare':
        m=load(LEGACY/'source/main_1.py','ds_core');work_bind(m,work)
        for name,value in request.get('settings',{}).items():setattr(m,name,value)
        from functools import partial
        m.expand_box=partial(m.expand_box,padding=m.FACE_PADDING_RATIO)
        m.mosaic_face=partial(m.mosaic_face,block_size=m.MOSAIC_SIZE)
        m.run(m.POLICIES,input_dir=m.INPUT_DIR,output_dir=m.OUTPUT_DIR)
        analyze(work,request['runId'])
    elif kind=='baseline':
        m=load(LEGACY/'source/main_1_baseline.py','ds_baseline');work_bind(m,work)
        m.OUTPUT_DIR=work/'outputs/second-baseline';m.CSV_PATH=m.OUTPUT_DIR/'face_mosaic_results.csv';m.EVAL_CSV_PATH=m.OUTPUT_DIR/'evaluation_results.csv';m.main()
    elif kind=='initial':
        m=load(LEGACY/'source/main.py','ds_initial');work_bind(m,work);m.OUTPUT_DIR=work/'outputs/first'
        out=Tee()
        with contextlib.redirect_stdout(out):m.main()
        text=out.saved.getvalue();counts={};name=None
        for line in text.splitlines():
            match=re.search(r'^\[\d+/\d+\] (.+)$',line)
            if match:name=match.group(1)
            detected=re.search(r'검출 얼굴: (\d+)개',line)
            if detected and name:counts[name]=int(detected.group(1))
        atomic_json(work/'initial_counts.json',counts)

def analyze(work,runid):
    m=load(LEGACY/'scripts/build_deepsight_reports.py','ds_reports');m.analyze(work,strict=True,experiment_id=runid)

def execute(request):
    run=STORE/'runs'/identifier(request['runId']);revision=int(request['revision'])
    if revision<1:raise ValueError('Invalid revision')
    work=run/('work' if request['kind']!='analyze' else 'analysis-'+identifier(request['jobId']))
    if work.exists():raise ValueError('작업 공간이 이미 존재합니다. 새 작업 ID를 사용하세요.')
    work.mkdir(parents=True)
    shutil.copytree(run/'data',work/'data')
    if request['kind'].startswith('import_'):
        kind=request['kind'].removeprefix('import_')
        # Only the bundled source dataset is imported. Do not attach different GT.
        if sha(run/'data/ground_truth.csv')!=sha(LEGACY/'data/ground_truth.csv'):
            raise ValueError('기존 자료 가져오기는 첨부 기준 데이터셋을 선택하세요.')
        for p in (run/'data/images').iterdir():
            if not (LEGACY/'data/images'/p.name).exists() or sha(p)!=sha(LEGACY/'data/images'/p.name):raise ValueError('과거 결과의 사진과 불일치')
        shutil.copytree(LEGACY/'outputs',work/'outputs')
        if kind=='compare':analyze(work,request['runId'])
        elif kind=='initial':atomic_json(work/'initial_counts.json',{})
    elif request['kind']=='analyze':
        shutil.copytree(run/'work/outputs',work/'outputs')
        shutil.copytree(run/'review_inputs'/request['jobId'],work/'reviews')
        analyze(work,request['runId']);kind='compare'
    else:
        validate_dataset(work/'data');infer(request,run,work);kind=request['kind']
    bundle=normalize(work,kind,request['runId'])
    outputs=work/'outputs'
    if not outputs.is_dir() or not any(outputs.rglob('*_mosaic.*')):raise RuntimeError('결과 이미지가 생성되지 않았습니다. 로그를 확인하세요.')
    stage=run/('publish-'+request['jobId']);stage.mkdir()
    shutil.copytree(outputs,stage/'outputs')
    (stage/'inputs').mkdir()
    shutil.copy2(work/'data/ground_truth.csv',stage/'inputs/ground_truth.csv')
    if (work/'reviews').exists():shutil.copytree(work/'reviews',stage/'inputs/reviews')
    bundle['revision']=revision
    atomic_json(stage/'bundle.json',bundle)
    manifest=[]
    for path in sorted(stage.rglob('*')):
        if path.is_file():manifest.append({'path':path.relative_to(stage).as_posix(),'size':path.stat().st_size,'sha256':sha(path)})
    provenance={'sourceOrigin':'IMPORTED_UNKNOWN_SETTINGS' if request['kind'].startswith('import_') else 'NEW_EXECUTION','python':sys.version,'settings':request.get('settings',{}),'sourceHashes':{},'inputHashes':{p.name:sha(p) for p in (run/'data/images').iterdir()},'groundTruthHash':sha(run/'data/ground_truth.csv')}
    for rel in ['source/main.py','source/main_1.py','source/main_1_baseline.py','scripts/build_deepsight_reports.py','shared/models/yolov8n-face-lindevs.pt']:
        provenance['sourceHashes'][rel]=sha(LEGACY/rel)
    import cv2
    provenance['opencv']=cv2.__version__
    for n in ['haarcascade_frontalface_default.xml','haarcascade_profileface.xml']:
        provenance['sourceHashes']['cv2/'+n]=sha(Path(cv2.data.haarcascades)/n)
    if request['kind'].startswith('import_'):
        provenance={'sourceOrigin':'첨부 ZIP 과거 결과','originalSettings':'미확인','note':'현재 모델/설정을 과거 실행 정보로 소급하지 않음','analysisEnvironmentOnly':provenance}
    atomic_json(stage/'experiment_run.json',provenance)
    manifest.append({'path':'experiment_run.json','size':(stage/'experiment_run.json').stat().st_size,'sha256':sha(stage/'experiment_run.json')})
    atomic_json(stage/'manifest.json',manifest)
    target=run/'reports'/f'r{revision:04}'
    target.parent.mkdir(exist_ok=True)
    if target.exists():raise ValueError('기존 보고서 덮어쓰기 금지')
    stage.replace(target)
    return target.relative_to(STORE).as_posix()

if __name__=='__main__':
    request=read_json(sys.argv[1])
    try:
        result=execute(request);print('DS_REPORT='+result,flush=True)
    except Exception:
        import traceback;traceback.print_exc();sys.exit(1)
