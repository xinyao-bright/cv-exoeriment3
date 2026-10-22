"""用当前 Python 环境执行 Notebook，临时内核配置不污染全局 Jupyter。"""
from pathlib import Path
import argparse
import json
import os
import sys
import tempfile
import asyncio
import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager
from jupyter_client import AsyncKernelManager

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    parser=argparse.ArgumentParser()
    parser.add_argument('--notebook',default='notebooks/image_stitching.ipynb')
    args=parser.parse_args()
    path=ROOT/args.notebook
    nb=nbformat.read(path,as_version=4)
    with tempfile.TemporaryDirectory(prefix='cv-stitching-kernel-') as directory:
        kernel=Path(directory)/'cv-stitching'; kernel.mkdir()
        spec={'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
              'display_name':'Python (cv-stitching)','language':'python',
              'env':{'PYTHONPATH':os.environ.get('PYTHONPATH','')}}
        (kernel/'kernel.json').write_text(json.dumps(spec),encoding='utf-8')
        manager=KernelSpecManager(kernel_dirs=[directory],ensure_native_kernel=False)
        kernel_manager=AsyncKernelManager(kernel_name='cv-stitching',kernel_spec_manager=manager)
        client=NotebookClient(nb,timeout=300,kernel_name='cv-stitching',
                              resources={'metadata':{'path':str(ROOT/'notebooks')}},
                              km=kernel_manager,allow_errors=False)
        try:
            client.execute()
        finally:
            if kernel_manager.has_kernel:
                asyncio.run(kernel_manager.shutdown_kernel(now=True))
    nbformat.validate(nb)
    nbformat.write(nb,path)
    code=[c for c in nb.cells if c.cell_type=='code']
    print(f'Executed {len(code)} code cells successfully; saved {path.name}')
