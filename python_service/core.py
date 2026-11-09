"""File contracts shared by the worker and API. No database access."""
from __future__ import annotations
import csv, hashlib, json, os, re
from pathlib import Path
from PIL import Image
HOME = Path(os.environ.get('DS_HOME', Path(__file__).resolve().parents[1])).resolve()
STORE = Path(os.environ.get('DS_STORAGE', HOME/'storage')).resolve()
LEGACY = HOME/'legacy'
POLICIES = ('legacy','yolo_only','haar_only','improved')
KINDS = ('compare','initial','baseline','analyze')
IMAGE_EXT = {'.jpg','.jpeg','.png','.bmp','.webp'}
Image.MAX_IMAGE_PIXELS = 40_000_000

def identifier(value):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', str(value)):
        raise ValueError('Invalid identifier')
    return str(value)

def safe(base, relative):
    p=(base/relative).resolve()
    if p != base.resolve() and base.resolve() not in p.parents:
        raise ValueError('Path outside storage')
    return p

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def atomic_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)

def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def csv_rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_csv(path, fields, rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def validate_dataset(folder):
    images=folder/'images';gt=csv_rows(folder/'ground_truth.csv')
    found={p.name for p in images.iterdir() if p.is_file()}
    if not found or len(found)>200:raise ValueError('사진은 1~200장이어야 합니다.')
    names=set();stems=set();rows=[]
    for r in gt:
        name=(r.get('파일명') or '').strip()
        if not name or Path(name).name!=name or name in names:raise ValueError('정답 파일명 누락/중복/경로 오류')
        count=int(r.get('실제 얼굴 수',''))
        if count<0 or count>10000:raise ValueError('실제 얼굴 수 범위 오류')
        names.add(name)
        if name not in found:raise ValueError('정답에만 존재하는 파일: '+name)
        p=images/name
        if p.suffix.lower() not in IMAGE_EXT or p.stem.lower().endswith('_mosaic'):raise ValueError('지원하지 않는 사진 이름: '+name)
        if p.stem.casefold() in stems:raise ValueError('출력 이름이 겹치는 사진: '+name)
        stems.add(p.stem.casefold())
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:w,h=im.size
        if w*h>40_000_000:raise ValueError('사진 최대 4천만 픽셀')
        rows.append({'filename':name,'groundTruth':count,'scene':r.get('scene',''),'note':r.get('note',''),'width':w,'height':h,'sha256':sha(p),'size':p.stat().st_size})
    if names!=found:raise ValueError('사진과 정답표 파일명이 일치하지 않습니다: '+str(found-names))
    return rows
