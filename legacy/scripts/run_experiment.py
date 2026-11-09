"""Safe interactive entry point for DeepSight four-policy comparison.

Official command (project root): python scripts/run_experiment.py --compare
If previous outputs exist, a verified snapshot and written note are REQUIRED.
"""
from __future__ import annotations
import argparse
import ast
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

POLICIES = ('legacy','yolo_only','haar_only','improved')
AGGREGATES = ('policy_comparison.csv','policy_test_cases.csv','data_validation.csv','aggregate_status.csv','experiment_run.json')
IMAGE_SUFFIXES = {'.jpg','.jpeg','.png','.bmp','.webp'}


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def snapshot_files(root):
    out=root/'outputs'
    files=[]
    experiment=out/'experiments'
    if experiment.is_dir():
        files.extend(p for p in experiment.rglob('*') if p.is_file())
    files.extend(out/name for name in AGGREGATES if (out/name).is_file())
    # first/ and second-baseline/ deliberately excluded.
    return sorted(set(files))


def parse_config(source):
    program=source.read_text(encoding='utf-8-sig')
    tree=ast.parse(program)
    settings={}
    for stmt in tree.body:
        if isinstance(stmt,ast.Assign) and len(stmt.targets)==1 and isinstance(stmt.targets[0],ast.Name):
            key=stmt.targets[0].id
            if key in ('MIN_FACE_SIZE','YOLO_CONFIDENCE','YOLO_IMAGE_SIZE','YOLO_NMS_IOU','YOLO_HAAR_IOU_THRESHOLD','FRONTAL_NEIGHBORS','PROFILE_NEIGHBORS','MOSAIC_SIZE','FACE_PADDING_RATIO'):
                try:settings[key]=ast.literal_eval(stmt.value)
                except (ValueError,TypeError): settings[key]='미확인: 동적 표현식'
    match=re.search(r"^MODEL_PATH\s*=\s*BASE_DIR\s*/\s*['\"]shared['\"]\s*/\s*['\"]models['\"]\s*/\s*['\"]([^'\"]+)['\"]", program, re.M)
    settings['model_filename']=match.group(1) if match else '미확인: 소스에서 추출 실패'
    return settings


def input_manifest(root,source):
    config=parse_config(source)
    model=root/'shared'/'models'/config['model_filename']
    inputs=[source,root/'scripts'/'build_deepsight_reports.py',root/'data'/'ground_truth.csv']
    inputs+=sorted(p for p in (root/'data'/'images').iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    inputs.append(model)
    result=[]
    for p in inputs:
        result.append({'path':p.relative_to(root).as_posix(),'exists':p.is_file(), 'size':p.stat().st_size if p.is_file() else None, 'sha256':sha256(p) if p.is_file() else None})
    return config,result


def make_id():
    return datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]


def safe_text(prompt, input_fn=input):
    try:
        return input_fn(prompt).strip()
    except (EOFError,KeyboardInterrupt):
        return ''


def backup(root, old_files, note, backup_id):
    if not old_files:
        return None
    destination=root/'csv_backup'/backup_id
    if destination.exists():
        raise FileExistsError(f'백업 폴더가 이미 있습니다: {destination}')
    destination.mkdir(parents=True,exist_ok=False)
    entries=[]
    try:
        for original in old_files:
            rel=original.relative_to(root/'outputs')
            copied=destination/'outputs_snapshot'/rel
            copied.parent.mkdir(parents=True,exist_ok=True)
            expected=sha256(original)
            shutil.copy2(original,copied)
            if original.stat().st_size!=copied.stat().st_size or sha256(copied)!=expected:
                raise IOError(f'백업 검증 실패: {original}')
            entries.append({'path':rel.as_posix(),'size':copied.stat().st_size,'sha256':expected})
        previous=root/'outputs'/'experiment_run.json'
        prev=json.loads(previous.read_text(encoding='utf8')) if previous.is_file() else None
        (destination/'previous_settings.json').write_text(json.dumps(prev if prev is not None else {'status':'미확인','reason':'과거 실행 당시 설정 기록 없음; 현재 소스 설정을 소급하여 적용하지 않음'},ensure_ascii=False,indent=2),encoding='utf8')
        (destination/'experiment_note.md').write_text('# 이전 실험 결과 백업\n\n'+note+'\n',encoding='utf8')
        (destination/'backup_manifest.json').write_text(json.dumps({'backup_id':backup_id,'file_count':len(entries),'files':entries},ensure_ascii=False,indent=2),encoding='utf8')
        if len(entries)!=len(old_files):
            raise IOError('백업 파일 수 불일치')
        return destination
    except BaseException:
        shutil.rmtree(destination,ignore_errors=True)
        raise


def restore_snapshot(root,backup_path):
    """Recover the prior snapshot after an interrupted or failed run.
    Does not touch first/, second-baseline/, reviews/, or csv_backup history.
    """
    out=root/'outputs'
    experiment=out/'experiments'
    if experiment.exists():shutil.rmtree(experiment)
    for name in AGGREGATES:
        (out/name).unlink(missing_ok=True)
    for p in (backup_path/'outputs_snapshot').rglob('*'):
        if p.is_file():
            target=out/p.relative_to(backup_path/'outputs_snapshot')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,target)
    # All recovery files are checked using their saved manifest.
    manifest=json.loads((backup_path/'backup_manifest.json').read_text(encoding='utf8'))
    for item in manifest['files']:
        restored=out/item['path']
        if not restored.is_file() or sha256(restored)!=item['sha256']:
            raise IOError(f'복원 검증 실패: {restored}')


def execute(root, input_fn=input, runner=subprocess.run, output_fn=print):
    old=snapshot_files(root)
    saved=None
    if old:
        output_fn(f'[기존 결과 발견] 파일 {len(old)}개')
        answer=safe_text('기존 결과를 백업하시겠습니까? [Y/N, 기본 취소]: ',input_fn).lower()
        if answer not in ('y','yes'):
            output_fn('[취소] 백업 동의가 없어 실행하지 않습니다.')
            return 2
        note=safe_text('백업할 이전 실험에 대한 주석을 입력하세요: ',input_fn)
        if not note:
            output_fn('[취소] 기존 결과 설명이 비어 있습니다.')
            return 2
        try:
            saved=backup(root,old,note,make_id())
        except (OSError,ValueError) as exc:
            output_fn(f'[백업 실패] {exc}; 추론 실행 안 함')
            return 1
        output_fn(f'[백업 완료] {saved} ({len(old)}개 파일 SHA-256 확인)')
    new_note=safe_text('새 실험 목적·변경사항을 입력하세요: ',input_fn)
    if not new_note:
        output_fn('[취소] 새 실험 주석이 비어 있습니다.')
        return 2
    experiment_id=make_id()
    source=root/'source'/'main_1.py'
    try:
        settings,inputs=input_manifest(root,source)
        if not all(item['exists'] for item in inputs):
            missing=[i['path'] for i in inputs if not i['exists']]
            raise FileNotFoundError(f'실험 필수 입력 없음: {missing}')
        output_fn(f'[새 실험] {experiment_id}; 모델={settings["model_filename"]}, min_face={settings.get("MIN_FACE_SIZE")}, conf={settings.get("YOLO_CONFIDENCE")}')
        command=[sys.executable,str(source),'--compare']
        completed=runner(command,cwd=str(root),check=False)
        if completed.returncode:
            raise RuntimeError(f'추론 프로그램 종료 코드: {completed.returncode}')
        command=[sys.executable,str(root/'scripts'/'build_deepsight_reports.py'),'--root',str(root),'--strict','--experiment-id',experiment_id]
        completed=runner(command,cwd=str(root),check=False)
        if completed.returncode:
            raise RuntimeError(f'분석 프로그램 종료 코드: {completed.returncode}')
        record={'experiment_id':experiment_id,'created_at':datetime.now().isoformat(timespec='seconds'),
                'user_note':new_note,'run_command':'python scripts/run_experiment.py --compare',
                'settings':settings,'input_files':inputs,'policy_names':list(POLICIES),
                'status':'completed','previous_backup':str(saved.relative_to(root)) if saved else None}
        target=root/'outputs'/'experiment_run.json'
        target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
        output_fn(f'[완료] 4개 정책 실행 및 분석 성공; 실험 ID: {experiment_id}')
        return 0
    except (OSError,ValueError,RuntimeError,KeyboardInterrupt) as exc:
        output_fn(f'[실험 실패] {exc}')
        if saved:
            try:
                restore_snapshot(root,saved)
                output_fn('[복원 완료] 백업에서 이전 결과를 복원했습니다.')
            except (OSError,ValueError) as restore_exc:
                output_fn(f'[복원 오류] {restore_exc}; 백업은 보존되어 있습니다: {saved}')
        return 1


def main():
    parser=argparse.ArgumentParser(description='DeepSight 안전 실험 실행 및 자동 백업')
    parser.add_argument('--compare',action='store_true',help='4개 정책 비교 실행')
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    args=parser.parse_args()
    if not args.compare:
        parser.error('공식 실험은 --compare 옵션이 필요합니다.')
    return execute(args.root.resolve())

if __name__=='__main__':
    raise SystemExit(main())
