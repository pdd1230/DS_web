import csv,json,sys,tempfile
from pathlib import Path
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import safe,identifier,sha,validate_dataset,write_csv

def dataset(root,rows):
    (root/'images').mkdir();Image.new('RGB',(64,64)).save(root/'images/한글.jpg')
    write_csv(root/'ground_truth.csv',['파일명','실제 얼굴 수','scene','note'],rows)

def test_reject_traversal(tmp_path):
    with pytest.raises(ValueError):safe(tmp_path,'../../etc/passwd')
    with pytest.raises(ValueError):identifier('../escape')

def test_unicode_ground_truth(tmp_path):
    dataset(tmp_path,[{'파일명':'한글.jpg','실제 얼굴 수':0,'scene':'없음','note':'밝음'}])
    rows=validate_dataset(tmp_path);assert rows[0]['groundTruth']==0;assert rows[0]['sha256']==sha(tmp_path/'images/한글.jpg')

@pytest.mark.parametrize('rows',[[{'파일명':'다른.jpg','실제 얼굴 수':1}],[{'파일명':'한글.jpg','실제 얼굴 수':-1}],[{'파일명':'한글.jpg','실제 얼굴 수':1}]*2])
def test_reject_invalid_truth(tmp_path,rows):
    dataset(tmp_path,rows)
    with pytest.raises(ValueError):validate_dataset(tmp_path)

def test_reject_same_stem(tmp_path):
    dataset(tmp_path,[{'파일명':'한글.jpg','실제 얼굴 수':0},{'파일명':'한글.png','실제 얼굴 수':0}])
    Image.new('RGB',(64,64)).save(tmp_path/'images/한글.png')
    with pytest.raises(ValueError):validate_dataset(tmp_path)
