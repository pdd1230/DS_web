"""D1 contract tests; no YOLO inference or original-image modification."""
import csv
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

reports=load('build_deepsight_reports')
runner=load('run_experiment')

class TestD1(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='deepsight-test-')
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'data',self.root/'data')
        shutil.copytree(ROOT/'scripts',self.root/'scripts')
        shutil.copytree(ROOT/'source',self.root/'source')
        shutil.copytree(ROOT/'shared',self.root/'shared')
        (self.root/'outputs'/'experiments').mkdir(parents=True)
        for policy in reports.POLICIES:
            src=ROOT/'outputs'/'experiments'/policy
            dst=self.root/'outputs'/'experiments'/policy
            dst.mkdir()
            for name in ('evaluation_results.csv','face_mosaic_results.csv','detection_details.csv','processing_status.csv'):
                shutil.copy2(src/name,dst/name)
        (self.root/'reviews').mkdir()
        shutil.copy2(ROOT/'reviews'/'manual_review.csv',self.root/'reviews'/'manual_review.csv')

    def tearDown(self):self.temp.cleanup()

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root/'outputs').rglob('*') if p.is_file()}

    def test_baseline_and_seven_columns(self):
        result=reports.analyze(self.root,strict=True)
        self.assertEqual([r['exact'] for r in result],[15,19,10,17])
        with (self.root/'outputs'/'experiments'/'legacy'/'test_cases.csv').open(encoding='utf-8-sig') as f:
            self.assertEqual(next(csv.reader(f)),list(reports.TEST_COLUMNS))
        with (self.root/'outputs'/'policy_comparison.csv').open(encoding='utf-8-sig') as f:
            self.assertEqual(next(csv.reader(f)),list(reports.COMP_COLUMNS))

    def test_validation_wrong_second_policy_preserves_all_reports(self):
        reports.analyze(self.root,strict=True)
        before=self.snapshot()
        p=self.root/'outputs'/'experiments'/'yolo_only'/'processing_status.csv'
        p.write_text(p.read_text(encoding='utf-8-sig').replace('processed_detected,1,','processed_detected,999,',1),encoding='utf-8-sig')
        baseline=self.snapshot()
        with self.assertRaisesRegex(ValueError,'검출 수 불일치'):
            reports.analyze(self.root,strict=True)
        self.assertEqual(baseline,self.snapshot())

    def test_missing_policy_strict_and_non_strict(self):
        shutil.rmtree(self.root/'outputs'/'experiments'/'improved')
        with self.assertRaises(FileNotFoundError): reports.analyze(self.root,strict=True)
        result=reports.analyze(self.root,strict=False)
        self.assertEqual(len(result),3)
        self.assertFalse((self.root/'outputs'/'policy_comparison.csv').exists())
        self.assertTrue((self.root/'outputs'/'aggregate_status.csv').exists())

    def test_manual_review_survives_reanalysis(self):
        p=self.root/'reviews'/'manual_review.csv'
        with p.open('a',encoding='utf-8',newline='') as f:
            csv.writer(f).writerow(['run-123','yolo_only','img_020.jpg','검수완료','미검출',1,0,'검토 필요','왼쪽 얼굴 누락'])
        first=p.read_bytes()
        reports.analyze(self.root,strict=True,experiment_id='run-123')
        with (self.root/'outputs'/'experiments'/'yolo_only'/'test_cases_detailed.csv').open(encoding='utf-8-sig') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(rows[-1]['review_status'],'검수완료')
        self.assertEqual(rows[-1]['missing_faces'],'1')
        reports.analyze(self.root,strict=True,experiment_id='run-123')
        self.assertEqual(first,p.read_bytes())
        reports.analyze(self.root,strict=True,experiment_id='another-run')
        with (self.root/'outputs'/'experiments'/'yolo_only'/'test_cases_detailed.csv').open(encoding='utf-8-sig') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(rows[-1]['review_status'],'미검수')

    def test_missing_and_duplicate_gt(self):
        gt=self.root/'data'/'ground_truth.csv'
        gt.write_bytes(gt.read_bytes()+b'img_001.jpg,1,,\r\n')
        with self.assertRaisesRegex(ValueError,'중복'):
            reports.analyze(self.root,strict=True)

    def test_safe_publish_rollback(self):
        p=self.root/'outputs'/'policy_comparison.csv'
        p.write_text('old',encoding='utf8')
        q=self.root/'outputs'/'data_validation.csv'
        # Inject a directory at destination, causing a rename failure after first rename.
        q.mkdir()
        with self.assertRaises(Exception):
            reports.publish_safely({p:b'new',q:b'text'},self.root)
        self.assertEqual(p.read_text(encoding='utf8'),'old')

    def test_cancel_and_noninteractive_no_inference(self):
        called=[]
        code=runner.execute(self.root,input_fn=lambda _: 'n',runner=lambda *a,**k:called.append(a))
        self.assertEqual(code,2);self.assertEqual(called,[])
        code=runner.execute(self.root,input_fn=lambda _: '',runner=lambda *a,**k:called.append(a))
        self.assertEqual(code,2);self.assertFalse(called)

    def test_backup_and_metadata_is_unknown_for_old_run(self):
        files=runner.snapshot_files(self.root)
        backup=runner.backup(self.root,files,'이전 결과 검토',runner.make_id())
        manifest=json.loads((backup/'backup_manifest.json').read_text(encoding='utf8'))
        self.assertEqual(manifest['file_count'],len(files))
        self.assertEqual(json.loads((backup/'previous_settings.json').read_text(encoding='utf8'))['status'],'미확인')
        self.assertIn('이전 결과 검토',(backup/'experiment_note.md').read_text(encoding='utf8'))

    def test_backup_then_failed_inference_restores(self):
        before=self.snapshot()
        answers=iter(['Y','기존 실험','새로운 실험'])
        def fake_run(command,**kwargs):
            (self.root/'outputs'/'experiments'/'legacy'/'evaluation_results.csv').write_text('broken',encoding='utf8')
            return SimpleNamespace(returncode=1)
        code=runner.execute(self.root,input_fn=lambda _:next(answers),runner=fake_run)
        self.assertEqual(code,1)
        self.assertEqual(before,self.snapshot())

    def test_backup_copy_failure_prevents_inference(self):
        before=self.snapshot()
        answers=iter(['Y','이전 실험 설명'])
        calls=[]
        with patch.object(runner.shutil,'copy2',side_effect=OSError('simulated copy failure')):
            code=runner.execute(self.root,input_fn=lambda _:next(answers),runner=lambda *a,**k:calls.append(a))
        self.assertEqual(code,1)
        self.assertEqual(calls,[])
        self.assertEqual(before,self.snapshot())

    def test_runner_mock_pipeline(self):
        answers=iter(['Y','기존 설정 미확인','YOLO 설정 비교'])
        calls=[]
        def fake_run(command,**kwargs):
            calls.append(command)
            if 'build_deepsight_reports.py' in ' '.join(command):
                reports.analyze(self.root,strict=True,experiment_id=command[-1])
            return SimpleNamespace(returncode=0)
        code=runner.execute(self.root,input_fn=lambda _:next(answers),runner=fake_run)
        self.assertEqual(code,0)
        self.assertEqual(len(calls),2)
        record=json.loads((self.root/'outputs'/'experiment_run.json').read_text(encoding='utf8'))
        self.assertEqual(record['settings']['YOLO_IMAGE_SIZE'],1280)
        self.assertTrue(record['previous_backup'])
        self.assertTrue(all(item['sha256'] for item in record['input_files']))

if __name__=='__main__': unittest.main()
