#!/usr/bin/env python3
"""Install both skills as repository links; preserve previous local directories."""
import datetime
import os
from pathlib import Path

repo=Path(__file__).resolve().parents[1]
destination=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills'
destination.mkdir(parents=True,exist_ok=True)
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup=Path.home()/'.local/state/ncut-wechat-skills/install-backups'/stamp
for name in ('ncut-web-api','wechat-personal'):
    source=repo/'skills'/name;target=destination/name
    if target.is_symlink() and target.resolve()==source:
        print(f'{name}: already linked');continue
    if target.exists() or target.is_symlink():
        backup.mkdir(parents=True,exist_ok=True,mode=0o700)
        target.rename(backup/name)
        print(f'{name}: previous installation backed up to {backup/name}')
    target.symlink_to(source,target_is_directory=True)
    print(f'{name}: linked to {source}')
