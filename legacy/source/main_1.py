"""DeepSight 얼굴 모자이크 v2 (PDCA D 단계).

기본 실행: python source/main_1.py              # 기존 방식 유지
비교 실행: python source/main_1.py --compare     # 4개 정책 비교, 별도 폴더
개선 실행: python source/main_1.py --policy improved

주의: 자동 모자이크는 완전한 비식별화를 보장하지 않습니다. 원본/출력의 수동 검수가 필요합니다.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import re

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / 'data' / 'images'
OUTPUT_DIR = BASE_DIR / 'outputs'
GT_PATH = BASE_DIR / 'data' / 'ground_truth.csv'
MODEL_PATH = BASE_DIR / 'shared' / 'models' / 'yolov8n-face-lindevs.pt'
# MODEL_PATH = BASE_DIR / 'shared' / 'models' / 'yolov8s-face-lindevs.pt'
# MODEL_PATH = BASE_DIR / 'shared' / 'models' / 'yolov8m-face-lindevs.pt'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
MIN_FACE_SIZE = 30   # 50 --> 30
MIN_FACE_ASPECT = 0.60
MAX_FACE_ASPECT = 1.40
FRONTAL_NEIGHBORS = 9
PROFILE_NEIGHBORS = 7  # 9 --> 7
YOLO_CONFIDENCE = 0.20  # 0.35 --> 0.20
YOLO_IMAGE_SIZE = 1280  # 960 --> 1280
YOLO_NMS_IOU = 0.50
YOLO_HAAR_IOU_THRESHOLD = 0.30
MOSAIC_SIZE = 6
FACE_PADDING_RATIO = 0.00
POLICIES = ('legacy', 'yolo_only', 'haar_only', 'improved')

CANDIDATE_COLUMNS = ['image_name','detector','candidate_index','x','y','w','h','confidence','selected','decision_reason','review_required']
RESULT_COLUMNS = ['image_name','image_width','image_height','face_index','x','y','w','h','box_x1','box_y1','box_x2','box_y2','status']
STATUS_COLUMNS = ['image_name','processing_status','detected_count','error_message','manual_review_required']
EVAL_COLUMNS = ['filename','ground_truth','detected','evaluation','processing_status']


@dataclass(frozen=True)
class FaceCandidate:
    detector: str
    box: tuple[int, int, int, int]
    confidence: float | None = None


def natural_sort_key(path: Path):
    values = re.findall(r'\d+', path.stem)
    return (int(values[-1]), path.name.lower()) if values else (float('inf'), path.name.lower())


def read_image(path: Path):
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except (OSError, cv2.error, ValueError) as exc:
        print(f'[읽기 오류] {path.name}: {exc}')
        return None


def save_image(path: Path, image) -> bool:
    try:
        ok, encoded = cv2.imencode(path.suffix, image)
        if not ok:
            return False
        encoded.tofile(str(path))
        return True
    except (OSError, cv2.error, ValueError) as exc:
        print(f'[저장 오류] {path.name}: {exc}')
        return False


def valid_face_box(box, image_width: int, image_height: int) -> bool:
    x,y,w,h = box
    return (w >= MIN_FACE_SIZE and h >= MIN_FACE_SIZE
            and 0 <= x and 0 <= y and x + w <= image_width
            and y + h <= image_height and MIN_FACE_ASPECT <= w/h <= MAX_FACE_ASPECT)


def box_iou(a, b) -> float:
    ax,ay,aw,ah = a
    bx,by,bw,bh = b
    x1,y1 = max(ax,bx),max(ay,by)
    x2,y2 = min(ax+aw,bx+bw),min(ay+ah,by+bh)
    overlap = max(0,x2-x1)*max(0,y2-y1)
    union = aw*ah + bw*bh - overlap
    return overlap/union if union > 0 else 0.0


def dedupe(candidates: list[FaceCandidate], threshold: float = 0.40):
    """기존 규칙 보존: 큰 면적 박스를 먼저 채택한다."""
    retained = []
    for item in sorted(candidates, key=lambda c:c.box[2]*c.box[3], reverse=True):
        if not any(box_iou(item.box, k.box) >= threshold for k in retained):
            retained.append(item)
    return retained


def get_haar_cascades():
    frontal = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    profile = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_profileface.xml')
    if frontal.empty() or profile.empty():
        raise RuntimeError('Haar Cascade 모델 로드 실패')
    return frontal, profile


def detect_haar(gray, frontal, profile) -> list[FaceCandidate]:
    height,width = gray.shape
    equalized = cv2.equalizeHist(gray)
    min_size = max(24,int(min(width,height)*0.018))
    frontal_boxes=[]
    profile_boxes=[]
    for x,y,w,h in frontal.detectMultiScale(equalized,scaleFactor=1.05,
                    minNeighbors=FRONTAL_NEIGHBORS,minSize=(min_size,min_size),flags=cv2.CASCADE_SCALE_IMAGE):
        b=tuple(map(int,(x,y,w,h)))
        if valid_face_box(b,width,height):
            frontal_boxes.append(FaceCandidate('Haar',b))
    for source,flipped in ((equalized,False),(cv2.flip(equalized,1),True)):
        for x,y,w,h in profile.detectMultiScale(source,scaleFactor=1.05,
                    minNeighbors=PROFILE_NEIGHBORS,minSize=(min_size,min_size),flags=cv2.CASCADE_SCALE_IMAGE):
            x,y,w,h = map(int,(x,y,w,h))
            b=(width-x-w if flipped else x,y,w,h)
            if valid_face_box(b,width,height):
                profile_boxes.append(FaceCandidate('Haar',b))
    # 기존 소스와 동일: 정면/측면 따로 중복제거 후 합쳐 한 번 더 중복제거
    return dedupe(dedupe(frontal_boxes)+dedupe(profile_boxes))


def detect_yolo(image, model) -> list[FaceCandidate]:
    height,width=image.shape[:2]
    result=[]
    for prediction in model.predict(source=image,imgsz=YOLO_IMAGE_SIZE,
                                    conf=YOLO_CONFIDENCE,iou=YOLO_NMS_IOU,verbose=False):
        if prediction.boxes is None:
            continue
        boxes = prediction.boxes.xyxy.cpu().numpy()
        confidences = prediction.boxes.conf.cpu().numpy()
        for coords, conf in zip(boxes, confidences):
            x1,y1,x2,y2 = map(int,coords)
            box=(x1,y1,x2-x1,y2-y1)
            if valid_face_box(box,width,height):
                result.append(FaceCandidate('YOLO',box,float(conf)))
    return result


def choose_candidates(yolo: list[FaceCandidate], haar: list[FaceCandidate], policy: str):
    """모든 후보의 채택/제외 이유를 반환한다.

    improved는 시험용 보수 정책: YOLO 검출이 있으면 YOLO 우선,
    중복되지 않는 Haar 후보는 자동 채택하지 않고 수동 검수 목록으로 보류.
    YOLO 검출이 전혀 없는 경우 Haar를 보완 채택(수동 검수 표시).
    이 정책이 더 안전하거나 정확하다는 것을 가정하지 않는다.
    """
    if policy not in POLICIES:
        raise ValueError(f'지원하지 않는 정책: {policy}')
    details=[]
    eligible=[]
    for candidate in yolo:
        include = policy in ('legacy','yolo_only','improved')
        details.append((candidate,include,'yolo_primary' if include else 'policy_excluded',False))
        if include:
            eligible.append(candidate)
    for candidate in haar:
        duplicate = any(box_iou(candidate.box, y.box) >= YOLO_HAAR_IOU_THRESHOLD for y in yolo)
        if policy == 'yolo_only':
            include,reason,review=False,'policy_excluded',False
        elif policy == 'haar_only':
            include,reason,review=True,'haar_only',False
        elif duplicate and policy in ('legacy','improved'):
            include,reason,review=False,'overlap_with_yolo',False
        elif policy == 'improved' and yolo:
            include,reason,review=False,'haar_unverified_review',True
        else:
            include=True
            reason = 'haar_fallback_review' if policy=='improved' else 'haar_supplement'
            review = (policy=='improved')
        details.append((candidate,include,reason,review))
        if include:
            eligible.append(candidate)
    # 후보별 최종 중복 결과를 기록; yolo 단독의 중복 제거는 기존 소스와 동일하게 적용하지 않음
    if policy=='legacy':
        # 원본은 YOLO가 먼저 나열되고 Haar가 추가된 후, 전체를 면적순 중복제거
        chosen=dedupe(eligible)
    elif policy=='haar_only':
        chosen=dedupe(eligible)
    elif policy=='improved':
        chosen=dedupe(eligible)
    else:
        chosen=list(eligible)
    chosen_ids={id(x) for x in chosen}
    normalized=[]
    for item,include,reason,review in details:
        selected = include and id(item) in chosen_ids
        if include and not selected:
            reason='final_nms_duplicate'
        normalized.append((item,selected,reason,review))
    chosen.sort(key=lambda c:(c.box[1],c.box[0]))
    return chosen,normalized


def expand_box(box,image_width,image_height,padding=FACE_PADDING_RATIO):
    x,y,w,h=box
    px,py=int(w*padding),int(h*padding)
    x1,y1=max(0,x-px),max(0,y-py)
    x2,y2=min(image_width,x+w+px),min(image_height,y+h+py)
    return (x1,y1,x2-x1,y2-y1)


def mosaic_face(image,box,block_size=MOSAIC_SIZE):
    x,y,w,h=box
    if w<=0 or h<=0:
        return
    roi=image[y:y+h,x:x+w]
    if roi.size==0:
        return
    small=cv2.resize(roi,(max(1,w//block_size),max(1,h//block_size)),interpolation=cv2.INTER_LINEAR)
    roi[:]=cv2.resize(small,(w,h),interpolation=cv2.INTER_NEAREST)


def ground_truth_counts():
    if not GT_PATH.exists():
        return {}
    result={}
    with GT_PATH.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            result[row['파일명'].strip()]=int(row['실제 얼굴 수'])
    return result


def write_csv(path,columns,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def evaluate(gt, statuses, path):
    by_filename={row['image_name']:row for row in statuses}
    rows=[]
    exact=over=under=failed=0
    for filename,true_count in gt.items():
        entry=by_filename.get(filename)
        status=entry['processing_status'] if entry else 'not_processed'
        if status not in ('processed_detected','processed_no_face'):
            failed+=1
            rows.append(dict(filename=filename,ground_truth=true_count,detected='',evaluation='Not Evaluated',processing_status=status))
            continue
        count=int(entry['detected_count'])
        label='Exact Match' if count==true_count else ('Over-detection' if count>true_count else 'Under-detection')
        exact+=label=='Exact Match'
        over+=label=='Over-detection'
        under+=label=='Under-detection'
        rows.append(dict(filename=filename,ground_truth=true_count,detected=count,evaluation=label,processing_status=status))
    write_csv(path,EVAL_COLUMNS,rows)
    return dict(total=len(gt),evaluated=len(gt)-failed,exact=int(exact),over=int(over),under=int(under),failed=int(failed),
                exact_match_pct=round(100*exact/(len(gt)-failed),2) if len(gt)>failed else None)


def run(policies, input_dir=INPUT_DIR, output_dir=OUTPUT_DIR, model=None, cascades=None):
    """동일 모델 추론 결과를 모든 정책에 재사용해 객관적으로 비교한다."""
    if model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f'YOLO 모델이 없습니다: {MODEL_PATH}')
        from ultralytics import YOLO  # 사용자 환경에서만 필요; 정책 단위테스트는 독립 실행
        model=YOLO(str(MODEL_PATH))
    frontal,profile = cascades if cascades is not None else get_haar_cascades()
    files=sorted((p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
                  and not p.stem.lower().endswith('_mosaic')),key=natural_sort_key)
    if not files:
        raise RuntimeError(f'입력 이미지가 없습니다: {input_dir}')
    results={p:dict(details=[],faces=[],statuses=[]) for p in policies}
    for idx,path in enumerate(files,1):
        print(f'[{idx}/{len(files)}] {path.name}')
        src=read_image(path)
        processing_error=None
        yolo=[];haar=[]
        if src is None:
            processing_error=('read_failed','image_decode_failed')
        else:
            try:
                yolo=detect_yolo(src,model)
                gray=cv2.cvtColor(src,cv2.COLOR_BGR2GRAY)
                haar=detect_haar(gray,frontal,profile)
            except Exception as exc:
                processing_error=('inference_failed',f'{type(exc).__name__}: {str(exc)[:160]}')
        print(f'  YOLO 검출: {len(yolo)}, Haar 검출: {len(haar)}')
        for policy in policies:
            store=results[policy]
            dest=output_dir if len(policies)==1 and policy=='legacy' else output_dir/'experiments'/policy
            dest.mkdir(parents=True,exist_ok=True)
            if processing_error:
                store['statuses'].append(dict(image_name=path.name,processing_status=processing_error[0],detected_count='',error_message=processing_error[1],manual_review_required='yes'))
                continue
            selected,details=choose_candidates(yolo,haar,policy)
            review=any(x[3] for x in details)
            for i,(candidate,selected_flag,reason,manual_review) in enumerate(details,1):
                x,y,w,h=candidate.box
                store['details'].append(dict(image_name=path.name,detector=candidate.detector,candidate_index=i,
                    x=x,y=y,w=w,h=h,confidence=round(candidate.confidence,6) if candidate.confidence is not None else '',
                    selected='yes' if selected_flag else 'no',decision_reason=reason,review_required='yes' if manual_review else 'no'))
            image=src.copy()
            height,width=image.shape[:2]
            for i,candidate in enumerate(selected,1):
                x,y,w,h=candidate.box
                bx,by,bw,bh=expand_box(candidate.box,width,height)
                mosaic_face(image,(bx,by,bw,bh))
                thickness=max(3,int(max(width,height)*0.004))
                cv2.rectangle(image,(bx,by),(bx+bw-1,by+bh-1),(0,0,255),thickness)
                cv2.putText(image,f'Face {i}',(bx,max(25,by-8)),cv2.FONT_HERSHEY_SIMPLEX,
                    max(0.7,max(width,height)/1800),(0,0,255),max(2,thickness//2),cv2.LINE_AA)
                store['faces'].append(dict(image_name=path.name,image_width=width,image_height=height,face_index=i,
                    x=x,y=y,w=w,h=h,box_x1=bx,box_y1=by,box_x2=bx+bw,box_y2=by+bh,status='detected'))
            if not selected:
                store['faces'].append(dict(image_name=path.name,image_width=width,image_height=height,face_index='',
                    x='',y='',w='',h='',box_x1='',box_y1='',box_x2='',box_y2='',status='no_face_detected'))
            saved=save_image(dest/f'{path.stem}_mosaic{path.suffix}',image)
            status = ('processed_detected' if selected else 'processed_no_face') if saved else 'save_failed'
            if not saved:
                # 기존 데이터 정확도에 저장 실패가 끼어들지 않도록 결과 건수를 평가에서 제외
                store['faces']=[r for r in store['faces'] if r['image_name']!=path.name]
            store['statuses'].append(dict(image_name=path.name,processing_status=status,
                detected_count=len(selected) if saved else '',error_message='' if saved else 'image_save_failed',
                manual_review_required='yes' if review or not selected or not saved else 'no'))
            print(f'  {policy}: 최종 {len(selected)}개 / {status}'+(' / 수동 검토 필요' if review else ''))
    gt=ground_truth_counts()
    comparison=[]
    for policy,records in results.items():
        dest=output_dir if len(policies)==1 and policy=='legacy' else output_dir/'experiments'/policy
        write_csv(dest/'detection_details.csv',CANDIDATE_COLUMNS,records['details'])
        write_csv(dest/'face_mosaic_results.csv',RESULT_COLUMNS,records['faces'])
        write_csv(dest/'processing_status.csv',STATUS_COLUMNS,records['statuses'])
        metrics=evaluate(gt,records['statuses'],dest/'evaluation_results.csv')
        comparison.append({'policy':policy,**metrics})
        print(f'{policy}: {metrics}')
    # 종합 policy_comparison.csv는 scripts/build_deepsight_reports.py에서만 생성합니다.
    return comparison


def main():
    parser=argparse.ArgumentParser(description='DeepSight 얼굴 모자이크 및 PDCA 정책 비교')
    parser.add_argument('--policy',choices=POLICIES,default='legacy',help='기본은 기존 검출 정책')
    parser.add_argument('--compare',action='store_true',help='4개 정책 동일 입력 비교')
    args=parser.parse_args()
    print('DeepSight YOLOv8-Face + Haar Cascade — PDCA v2')
    print(f'입력: {INPUT_DIR} / 모델: {MODEL_PATH}')
    if args.compare:
        print('[안내] 실험 결과 보존을 위해 scripts/run_experiment.py --compare 사용을 권장합니다.')
    try:
        run(POLICIES if args.compare else (args.policy,))
    except (OSError,RuntimeError,ValueError) as exc:
        print(f'[실행 오류] {exc}')
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
