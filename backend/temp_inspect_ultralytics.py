from pathlib import Path
import sys
import inspect
import ultralytics
from ultralytics.nn import tasks
from ultralytics.utils import patches
from ultralytics.utils import torch_utils

print('executable', sys.executable)
print('ultralytics', ultralytics.__version__)
print('torch', __import__('torch').__version__)
print('tasks module', tasks.__file__)
print('patches module', patches.__file__)
print('torch_utils module', torch_utils.__file__)
print('SAFE_LOAD', getattr(tasks, 'SAFE_LOAD', None))
print('TORCH_1_13', getattr(torch_utils, 'TORCH_1_13', None))
print('\n--- torch_load source ---')
print(inspect.getsource(patches.torch_load))
print('\n--- torch_safe_load source ---')
print(inspect.getsource(tasks.torch_safe_load)[:800])
print('\n--- load_checkpoint source ---')
print(inspect.getsource(tasks.load_checkpoint)[:800])
