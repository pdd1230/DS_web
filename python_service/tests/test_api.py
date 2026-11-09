import importlib,sys
from pathlib import Path
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def test_internal_auth_and_path_validation(tmp_path,monkeypatch):
    import app as service
    monkeypatch.setattr(service,'STORE',tmp_path)
    monkeypatch.setattr(service,'TOKEN','test-local-token')
    with TestClient(service.app) as client:
        assert client.get('/health').status_code==401
        headers={'X-DS-Key':'test-local-token'}
        assert client.get('/health',headers=headers).status_code==200
        assert client.post('/jobs',headers=headers,json={'jobId':'../x','runId':'x','kind':'compare','revision':1}).status_code==400
        assert client.post('/datasets/validate',headers=headers,json={'datasetId':'../escape'}).status_code==400
