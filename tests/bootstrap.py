import atexit
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
directory=tempfile.TemporaryDirectory(prefix='cun-zoom-test-')
os.environ['CUN_ZOOM_DATA_DIR']=directory.name
atexit.register(directory.cleanup)
