"""DeepSight CSV analysis: verify GT and four policy outputs, then publish reports safely.

Run: python scripts/build_deepsight_reports.py --root . --strict
Original inference CSVs, GT and manual review are read-only.
"""
from __future__ import annotations
import argparse
import csv
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path

POLICIES = ('legacy', 'yolo_only', 'haar_only', 'improved')
TEST_COLUMNS = ('test_id','scenario','expected_behavior','input_filename','actual_result','pass_fail','note')
EXTENDED_COLUMNS = TEST_COLUMNS + ('policy','ground_truth','detected','error','evaluation','processing_status','scene','gt_note','manual_review_required','candidate_summary','review_status','review_result','missing_faces','false_faces','mosaic_quality','review_note')
COMP_COLUMNS = ('policy','total','evaluated','exact','over','under','failed','exact_match_pct','gt_total_faces','detected_total_faces','absolute_count_error')
DETAIL_COLUMNS = ('policy','filename','ground_truth','scene','gt_note','legacy','yolo_only','haar_only','improved','legacy_error','yolo_only_error','haar_only_error','improved_error')
VALIDATION_COLUMNS = ('policy','filename','check_item','result','message')
REVIEW_COLUMNS = ('experiment_id','policy','filename','review_status','review_result','missing_faces','false_faces','mosaic_quality','review_note')
SUCCESS_STATES = {'processed_detected','processed_no_face'}


def load_csv(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f'필수 파일 없음: {path}')
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f'CSV 헤더 없음: {path}')
        return list(reader), set(reader.fieldnames)


def require_columns(headers, required, context):
    missing = set(required) - headers
    if missing:
        raise ValueError(f'{context}: 필수 컬럼 없음 {sorted(missing)}')


def integer(value, context):
    try:
        n = int(str(value).strip())
    except (ValueError, TypeError):
        raise ValueError(f'{context}: 정수 오류 {value!r}') from None
    if n < 0:
        raise ValueError(f'{context}: 음수 값 {n}')
    return n


def load_gt(path):
    rows, headers = load_csv(path)
    require_columns(headers, ('파일명','실제 얼굴 수'), str(path))
    gt = {}
    for row in rows:
        fn = (row.get('파일명') or '').strip()
        if not fn or fn in gt:
            raise ValueError(f'GT 파일명 누락 또는 중복: {fn!r}')
        gt[fn] = {'count': integer(row.get('실제 얼굴 수'),f'GT {fn}'), 'scene':(row.get('scene') or '').strip(), 'note':(row.get('note') or '').strip()}
    if not gt:
        raise ValueError('정답표가 비어 있습니다.')
    return gt


def unique_map(rows, key, policy, label, gt):
    found = {}
    for r in rows:
        fn = (r.get(key) or '').strip()
        if not fn or fn in found:
            raise ValueError(f'{policy}/{label}: 파일명 누락 또는 중복 {fn!r}')
        found[fn] = r
    if set(found) != set(gt):
        raise ValueError(f'{policy}/{label}: GT 파일명 불일치 missing={sorted(set(gt)-set(found))}, extra={sorted(set(found)-set(gt))}')
    return found


def load_reviews(root, experiment_id):
    path = root/'reviews'/'manual_review.csv'
    if not path.exists():
        return {}
    rows, headers = load_csv(path)
    require_columns(headers, REVIEW_COLUMNS, str(path))
    result = {}
    for r in rows:
        key = ((r.get('experiment_id') or '').strip(), (r.get('policy') or '').strip(), (r.get('filename') or '').strip())
        if not all(key) or key in result:
            raise ValueError(f'수동 검수 키 누락/중복: {key}')
        if key[1] not in POLICIES:
            raise ValueError(f'수동 검수 정책 오류: {key[1]}')
        if key[0] == experiment_id:
            result[key[1:]] = r
    return result


def parse_policy(folder, policy, gt, reviews):
    ev, eh = load_csv(folder/'evaluation_results.csv')
    faces, fh = load_csv(folder/'face_mosaic_results.csv')
    details, dh = load_csv(folder/'detection_details.csv')
    statuses, sh = load_csv(folder/'processing_status.csv')
    require_columns(eh, ('filename','ground_truth','detected','evaluation','processing_status'), f'{policy}/evaluation')
    require_columns(fh, ('image_name','status','x','y','w','h'), f'{policy}/faces')
    require_columns(dh, ('image_name','detector','selected','review_required'), f'{policy}/details')
    require_columns(sh, ('image_name','processing_status','detected_count','error_message','manual_review_required'), f'{policy}/status')
    by_e = unique_map(ev,'filename',policy,'evaluation',gt)
    by_s = unique_map(statuses,'image_name',policy,'processing_status',gt)
    final_count = Counter()
    zero_rows = Counter()
    chosen_count = Counter()
    candidates = Counter()
    review_candidates = Counter()
    for r in faces:
        fn = (r.get('image_name') or '').strip()
        if fn not in gt:
            raise ValueError(f'{policy}/face_mosaic_results: 알 수 없는 파일명 {fn}')
        state = (r.get('status') or '').strip()
        if state == 'detected':
            for c in ('x','y','w','h'):
                integer(r.get(c), f'{policy}/{fn}/face {c}')
            if integer(r.get('w'),f'{policy}/{fn}/w')==0 or integer(r.get('h'),f'{policy}/{fn}/h')==0:
                raise ValueError(f'{policy}/{fn}: 얼굴 박스 크기 0')
            final_count[fn] += 1
        elif state == 'no_face_detected':
            zero_rows[fn] += 1
        else:
            raise ValueError(f'{policy}/{fn}: 알 수 없는 얼굴 상태 {state}')
    for r in details:
        fn = (r.get('image_name') or '').strip()
        if fn not in gt:
            raise ValueError(f'{policy}/detection_details: 알 수 없는 파일명 {fn}')
        candidates[(fn, r.get('detector',''))] += 1
        if r.get('selected') not in ('yes','no') or r.get('review_required') not in ('yes','no'):
            raise ValueError(f'{policy}/{fn}: 후보 상태 값 오류')
        if r['selected']=='yes':
            chosen_count[fn] += 1
        if r['review_required']=='yes':
            review_candidates[fn] += 1
    tests = []
    validations = []
    metrics = Counter()
    detected_total = 0
    error_total = 0
    for i,(fn,entry) in enumerate(gt.items(),1):
        e = by_e[fn]
        s = by_s[fn]
        state = (s.get('processing_status') or '').strip()
        ev_state = (e.get('processing_status') or '').strip()
        if state != ev_state:
            raise ValueError(f'{policy}/{fn}: 처리 상태 불일치 {state!r} != {ev_state!r}')
        if s.get('manual_review_required') not in ('yes','no'):
            raise ValueError(f'{policy}/{fn}: 수동 검토 필요 여부 오류')
        ok = state in SUCCESS_STATES
        if ok:
            pred = integer(e.get('detected'), f'{policy}/{fn}/evaluation 검출 수')
            status_pred = integer(s.get('detected_count'), f'{policy}/{fn}/processing 검출 수')
            if pred != status_pred or pred != final_count[fn] or pred != chosen_count[fn]:
                raise ValueError(f'{policy}/{fn}: 검출 수 불일치 평가={pred}, 처리={status_pred}, 좌표={final_count[fn]}, 채택={chosen_count[fn]}')
            if integer(e.get('ground_truth'), f'{policy}/{fn}/evaluation GT') != entry['count']:
                raise ValueError(f'{policy}/{fn}: 정답 수 불일치')
            if (state == 'processed_no_face') != (pred==0):
                raise ValueError(f'{policy}/{fn}: 처리 상태와 얼굴 수 충돌')
            if zero_rows[fn] != (1 if pred == 0 else 0):
                raise ValueError(f'{policy}/{fn}: 얼굴 없음 행 오류')
            if s.get('error_message','').strip():
                raise ValueError(f'{policy}/{fn}: 정상 처리에 오류 메시지 존재')
            delta = pred-entry['count']
            label = 'Exact Match' if delta == 0 else ('Over-detection' if delta > 0 else 'Under-detection')
            if e.get('evaluation') != label:
                raise ValueError(f'{policy}/{fn}: 평가 판정 불일치 {e.get("evaluation")!r} != {label!r}')
            metrics['evaluated']+=1
            metrics['exact' if delta==0 else ('over' if delta>0 else 'under')] += 1
            detected_total+=pred
            error_total+=abs(delta)
        else:
            if state not in ('read_failed','inference_failed','save_failed','not_processed'):
                raise ValueError(f'{policy}/{fn}: 알 수 없는 실패 상태 {state}')
            if e.get('evaluation')!='Not Evaluated' or str(e.get('detected','')).strip():
                raise ValueError(f'{policy}/{fn}: 실패 상태의 평가/예측 값 오류')
            if s.get('detected_count','').strip() or final_count[fn] or zero_rows[fn]:
                raise ValueError(f'{policy}/{fn}: 실패인데 검출 결과가 남음')
            pred=None; delta=None; label='Not Evaluated'
            metrics['failed']+=1
        summary = f"YOLO {candidates[(fn,'YOLO')]}개 후보, Haar {candidates[(fn,'Haar')]}개 후보; 채택 {chosen_count[fn]}개"
        flag = 'yes' if review_candidates[fn] or not ok or pred==0 or s['manual_review_required']=='yes' else 'no'
        note = f'실제 {entry["count"]}개 / 검출 {pred if pred is not None else "평가 불가"}개; 상태: {state}; {summary}'
        if delta not in (None,0): note+=f'; 오차 {delta:+d}개, 이미지 수동 확인 필요'
        if entry['note']: note += f'; 촬영 조건: {entry["note"]}'
        review=reviews.get((policy,fn),{})
        test = {'test_id': f'T{i:03}', 'scenario': entry['scene'] or '미기록',
                'expected_behavior':f'얼굴 {entry["count"]}개 검출', 'input_filename':fn,
                'actual_result':f'얼굴 {pred}개 검출' if pred is not None else f'처리 실패({state})',
                'pass_fail':'PASS' if delta==0 else 'FAIL', 'note':note,
                'policy':policy,'ground_truth':entry['count'],'detected':pred if pred is not None else '',
                'error':delta if delta is not None else '', 'evaluation':label,'processing_status':state,
                'scene':entry['scene'],'gt_note':entry['note'],'manual_review_required':flag,
                'candidate_summary':summary, 'review_status':review.get('review_status') or '미검수',
                'review_result':review.get('review_result',''), 'missing_faces':review.get('missing_faces',''),
                'false_faces':review.get('false_faces',''), 'mosaic_quality':review.get('mosaic_quality',''),
                'review_note':review.get('review_note','')}
        tests.append(test)
        validations.append({'policy':policy,'filename':fn,'check_item':'GT/평가/좌표/후보/처리상태 일관성','result':'PASS','message':'4종 추론 CSV 일치'})
    total=len(gt)
    metrics_row={'policy':policy,'total':total,'evaluated':metrics['evaluated'],'exact':metrics['exact'],'over':metrics['over'],
        'under':metrics['under'],'failed':metrics['failed'],
        'exact_match_pct':round(metrics['exact']/metrics['evaluated']*100,2) if metrics['evaluated'] else '',
        'gt_total_faces':sum(v['count'] for v in gt.values()),'detected_total_faces':detected_total,
        'absolute_count_error':error_total}
    return tests,metrics_row,validations


def csv_bytes(columns, rows):
    import io
    buf = io.StringIO(newline='')
    writer=csv.DictWriter(buf,fieldnames=columns,extrasaction='ignore')
    writer.writeheader(); writer.writerows(rows)
    return ('\ufeff'+buf.getvalue()).encode('utf-8')


def publish_safely(payloads, root):
    """Prepare every file first; rollback replaced files if any rename fails."""
    output = root/'outputs'
    output.mkdir(exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.analysis-stage-',dir=output))
    originals={}
    installed=[]
    try:
        for index,(destination, data) in enumerate(payloads.items()):
            item=stage/f'{index:03d}.csv'
            item.write_bytes(data)
            if item.read_bytes()!=data:
                raise OSError(f'임시 파일 검증 실패: {destination}')
        for index,(destination, data) in enumerate(payloads.items()):
            destination.parent.mkdir(parents=True,exist_ok=True)
            if destination.exists():
                old=stage/f'original_{index:03d}.bak'
                shutil.copy2(destination,old)
                originals[destination]=old
            else:
                originals[destination]=None
            os.replace(stage/f'{index:03d}.csv',destination)
            installed.append(destination)
    except Exception:
        for destination in reversed(installed):
            old=originals[destination]
            if old is None:
                destination.unlink(missing_ok=True)
            else:
                shutil.copy2(old,destination)
        raise
    finally:
        shutil.rmtree(stage,ignore_errors=True)


def analyze(root, gt_path=None, strict=False, experiment_id=None):
    root=root.resolve()
    gt=load_gt(gt_path or root/'data'/'ground_truth.csv')
    # Existing runs with no recorded experiment ID cannot safely inherit manual reviews.
    reviews=load_reviews(root,experiment_id) if experiment_id else {}
    analyses={}; summaries=[]; all_validations=[]
    for policy in POLICIES:
        folder=root/'outputs'/'experiments'/policy
        if not folder.is_dir():
            if strict:
                raise FileNotFoundError(f'정책 폴더 없음: {folder}')
            print(f'[건너뜀] 정책 폴더 없음: {folder}')
            continue
        tests,summary,checks=parse_policy(folder,policy,gt,reviews)
        analyses[policy]=tests
        summaries.append(summary); all_validations.extend(checks)
    if not summaries:
        raise RuntimeError('처리 가능한 정책 폴더 없음')
    payloads={}
    for policy,tests in analyses.items():
        folder=root/'outputs'/'experiments'/policy
        payloads[folder/'test_cases.csv']=csv_bytes(TEST_COLUMNS,tests)
        payloads[folder/'test_cases_detailed.csv']=csv_bytes(EXTENDED_COLUMNS,tests)
    payloads[root/'outputs'/'data_validation.csv']=csv_bytes(VALIDATION_COLUMNS,all_validations)
    if len(summaries)==len(POLICIES):
        payloads[root/'outputs'/'policy_comparison.csv']=csv_bytes(COMP_COLUMNS,summaries)
        matrix=[]
        for fn,entry in gt.items():
            row={'policy':'','filename':fn,'ground_truth':entry['count'],'scene':entry['scene'],'gt_note':entry['note']}
            for policy in POLICIES:
                test=next(t for t in analyses[policy] if t['input_filename']==fn)
                row[policy]=test['detected'];row[f'{policy}_error']=test['error']
            matrix.append(row)
        payloads[root/'outputs'/'policy_test_cases.csv']=csv_bytes(DETAIL_COLUMNS,matrix)
    else:
        # If incomplete, withdraw old aggregate reports so they cannot look current.
        # Prefer keeping originals intact: explicitly mark stale with a separate status file.
        payloads[root/'outputs'/'aggregate_status.csv']=csv_bytes(('status','message'),[{'status':'STALE','message':f'{len(summaries)}/4 정책 존재; 종합표 재생성 안 함. 기존 종합표는 이전 실행 자료일 수 있음'}])
    publish_safely(payloads,root)
    for summary in summaries:
        print(f'[완료] {summary["policy"]}: {summary["exact"]}/{summary["evaluated"]} 일치 ({summary["exact_match_pct"]}%)')
    if len(summaries)==len(POLICIES):
        # Remove an old stale marker only after complete success.
        (root/'outputs'/'aggregate_status.csv').unlink(missing_ok=True)
        print('[완료] 4개 정책 분석 및 종합표 생성')
    else:
        print('[안내] 일부 정책만 분석: 기존 종합표는 최신 결과로 간주하지 마세요')
    return summaries


def main():
    p=argparse.ArgumentParser(description='DeepSight 정답표 기반 CSV 안전 검증 및 오차분석')
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    p.add_argument('--gt',type=Path)
    p.add_argument('--strict',action='store_true')
    p.add_argument('--experiment-id',help='수동 검수 연결용 현재 실험 ID (기존 실행에는 적용하지 않음)')
    args=p.parse_args()
    try:
        analyze(args.root,args.gt,args.strict,args.experiment_id)
    except (OSError,ValueError,RuntimeError) as exc:
        print(f'[검증 실패] {exc}')
        # Separate diagnostic log; never modify an existing analysis CSV on failure.
        try:
            log=args.root.resolve()/'logs'/'validation_errors.log'
            log.parent.mkdir(parents=True,exist_ok=True)
            from datetime import datetime
            with log.open('a',encoding='utf-8') as f:
                f.write(f'{datetime.now().isoformat(timespec="seconds")} | {type(exc).__name__}: {exc}\n')
        except OSError:
            pass
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
