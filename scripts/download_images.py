"""从固定提交下载照片；SHA256 校验避免来源漂移。无需额外下载库。"""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    manifest = json.loads((ROOT/'data'/'sources.json').read_text(encoding='utf-8'))
    for item in manifest['images']:
        path = ROOT/'data'/item['file']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']:
            print('Verified:', item['file']); continue
        request = urllib.request.Request(item['url'], headers={'User-Agent':'cv-experiment3'})
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise ValueError('SHA256 不匹配: '+item['file'])
        temporary = path.with_suffix('.download')
        temporary.write_bytes(data); temporary.replace(path)
        print('Downloaded:', item['file'])
