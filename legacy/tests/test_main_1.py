"""Ultralytics 실행 없이 통합·평가·오류분류를 검증하는 단위 테스트."""
import csv
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('deepsight_main',ROOT/'source'/'main_1.py')
m=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=m
spec.loader.exec_module(m)


def candidate(detector, box):
    return m.FaceCandidate(detector,box)


def test_img012_legacy_and_improved():
    y=[candidate('YOLO',(81,110,160,230))]
    h=[candidate('Haar',b) for b in [(22,114,232,232),(142,171,134,134),(133,357,94,94),(145,484,89,89)]]
    legacy,ld=m.choose_candidates(y,h,'legacy')
    improved,details=m.choose_candidates(y,h,'improved')
    assert [c.box for c in legacy]==[(81,110,160,230),(133,357,94,94),(145,484,89,89)]
    assert [c.box for c in improved]==[(81,110,160,230)]
    assert sum(x[3] for x in details)==2
    assert {x[2] for x in details if x[3]}=={'haar_unverified_review'}


def test_haar_only_fallback_preserved():
    haar=[candidate('Haar',(100,100,60,60)),candidate('Haar',(280,100,60,60))]
    selected,details=m.choose_candidates([],haar,'improved')
    assert len(selected)==2
    assert all(x[3] for x in details)


def test_yolo_confidence_not_fabricated_for_haar():
    with TemporaryDirectory() as d:
        f=Path(d)/'detail.csv'
        m.write_csv(f,m.CANDIDATE_COLUMNS,[dict(image_name='x',detector='Haar',candidate_index=1,x=1,y=1,w=60,h=60,confidence='',selected='yes',decision_reason='haar_only',review_required='no')])
        with f.open(encoding='utf-8-sig',newline='') as fp:
            assert list(csv.DictReader(fp))[0]['confidence']==''


def test_failure_excluded_from_evaluation():
    with TemporaryDirectory() as d:
        rows=[dict(image_name='ok.jpg',processing_status='processed_no_face',detected_count=0),
              dict(image_name='broken.jpg',processing_status='read_failed',detected_count='')]
        out=Path(d)/'evaluation.csv'
        metrics=m.evaluate({'ok.jpg':0,'broken.jpg':0},rows,out)
        assert metrics['evaluated']==1 and metrics['exact']==1 and metrics['failed']==1
        with out.open(encoding='utf-8-sig',newline='') as fp:
            results=list(csv.DictReader(fp))
            assert results[1]['evaluation']=='Not Evaluated'


def test_real_haar_img012_produces_candidates():
    path=ROOT/'data'/'images'/'img_012.jpg'
    image=m.read_image(path)
    assert image is not None
    frontal,profile=m.get_haar_cascades()
    detected=m.detect_haar(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),frontal,profile)
    assert isinstance(detected,list)
    assert all(m.valid_face_box(x.box,image.shape[1],image.shape[0]) for x in detected)


def test_failed_decode():
    with TemporaryDirectory() as d:
        file=Path(d)/'bad.jpg'
        file.write_bytes(b'not a jpeg')
        assert m.read_image(file) is None
