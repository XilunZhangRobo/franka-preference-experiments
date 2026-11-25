"""Export the consolidated report and its local viewing dependencies."""
import argparse
from collections import deque
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import stat
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

BASE = Path(__file__).resolve().parent
ENTRY = Path('index.html')
ROOTS = [BASE.resolve(), (BASE/'visual-interaction-study-v1').resolve(), (BASE/'audit-revision').resolve()]
MARKDOWN_LINK = re.compile(r'\[[^\]\n]*\]\(([^)\n]+)\)')

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('src','href','poster') and value:
                self.references.append(value)

def refs(path, content):
    if path.suffix == '.html':
        h=Links()
        h.feed(content)
        return h.references
    if path.suffix == '.md':
        return [m.strip('<>') for m in MARKDOWN_LINK.findall(content)]
    return []

def dependency(parent, ref):
    u=urlsplit(ref)
    if u.scheme or u.netloc:
        raise ValueError(f'External resource on {parent}: {u.scheme!r}')
    if not u.path:
        return parent
    decoded=unquote(u.path)
    if decoded.startswith('/') or '\\' in decoded:
        raise ValueError(f'Nonportable link on {parent}: {decoded}')
    relative=Path(os.path.normpath(parent.parent/decoded))
    if '..' in relative.parts:
        raise ValueError(f'Outside report: {relative}')
    return relative

def contents(key):
    path=(BASE/key)
    resolved=path.resolve(strict=True)
    if not any(resolved.is_relative_to(root) for root in ROOTS):
        raise ValueError(f'Out-of-bundle target: {key}')
    if path.suffix not in {'.html','.jpg','.mp4','.md','.json','.jsonl','.txt','.png','.css','.webm'}:
        raise ValueError(f'Unexpected asset type: {key}')
    return path.read_bytes()

def pack(target):
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix('.building')
    if tmp.exists(): raise RuntimeError('Export already in progress.')
    queue=deque([ENTRY]);seen=set();files=0;videos=0;images=0;max_path=''
    # The ZIP contains ordinary file entries even when the source is behind a Virgo symlink.
    try:
        with ZipFile(tmp,'x',compression=ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
            while queue:
                key=queue.popleft()
                if key in seen:continue
                seen.add(key);data=contents(key)
                if key.suffix in {'.html','.md'}:
                    s=data.decode()
                    queue.extend(dependency(key,ref) for ref in refs(key,s))
                    data=s.encode()
                name=key.as_posix()
                if len(name)>len(max_path):max_path=name
                info=ZipInfo(name)
                info.external_attr=(stat.S_IFREG|0o644)<<16
                info.compress_type=ZIP_STORED if key.suffix in ('.mp4','.webm','.jpg','.png') else ZIP_DEFLATED
                z.writestr(info,data)
                files+=1;videos+=key.suffix in ('.mp4','.webm');images+=key.suffix in ('.jpg','.png')
            z.writestr('OPEN-ME.txt',
                'Robot personalization across ten simulated tasks\n\n'
                'Extract the entire ZIP into one folder. Open index.html in Firefox, Chrome, Edge, or Safari.\n'
                'Choose an experiment and a trial. Its interaction menu links to robot action, human response, note, transfer and scope control.\n'
                'The linked evidence pages, images and videos are included for offline viewing.\n')
        os.chmod(tmp,0o600)
        os.replace(tmp,target)
    finally:
        tmp.unlink(missing_ok=True)
    print(f'{target}: {files} report files, {videos} videos, {images} images, longest member path {len(max_path)}. Size {target.stat().st_size} bytes.')

if __name__=='__main__':
    par=argparse.ArgumentParser()
    par.add_argument('output',type=Path)
    pack(par.parse_args().output)
