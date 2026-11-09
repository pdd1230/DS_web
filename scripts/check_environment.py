"""Run with the project's Python 3.11.9 venv."""
import sys,platform,importlib.metadata,hashlib,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
print('Python:',platform.python_version(),sys.executable)
for name in ['fastapi','uvicorn','numpy','opencv-python','Pillow','torch','torchvision','ultralytics']:
 try:print(name,importlib.metadata.version(name))
 except importlib.metadata.PackageNotFoundError:print(name,'MISSING')
model=root/'legacy/shared/models/yolov8n-face-lindevs.pt'
print('Model exists:',model.is_file())
if model.exists():print('Model SHA256:',hashlib.sha256(model.read_bytes()).hexdigest())
print('Free disk GiB:',round(shutil.disk_usage(root).free/1024**3,2))
if platform.python_version()!='3.11.9':sys.exit('Required Python version is 3.11.9')
