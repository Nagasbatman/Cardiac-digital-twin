import importlib, torch

for dep in ['nibabel', 'sklearn', 'torch']:
    try:
        importlib.import_module(dep)
        print(f"{dep} OK")
    except Exception as e:
        print(f"{dep} MISSING: {e}")

print('CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('CUDA device:', torch.cuda.get_device_name(0))
