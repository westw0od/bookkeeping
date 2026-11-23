"""On the app server, validate and atomically publish a prepared Android release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app_releases import AndroidRelease, read_release


def publish(source):
    manifest = AndroidRelease.model_validate_json((source / 'manifest.json').read_text(encoding='utf-8'))
    apk = source / 'app.apk'
    if apk.stat().st_size != manifest.size_bytes:
        raise ValueError('APK size differs from manifest')
    digest = hashlib.sha256()
    with apk.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != manifest.sha256:
        raise ValueError('APK SHA256 differs from manifest')
    target = ROOT / 'artifacts' / 'android'
    target.mkdir(parents=True, exist_ok=True)
    latest = target / 'latest.json'
    if latest.exists():
        previous = AndroidRelease.model_validate_json(latest.read_text(encoding='utf-8'))
        if previous.version_code > manifest.version_code:
            raise ValueError('Refusing to downgrade published version')
    release_dir = target / 'releases' / str(manifest.version_code)
    release_dir.parent.mkdir(parents=True, exist_ok=True)
    if release_dir.exists():
        existing, _ = read_release(release_dir / 'manifest.json')
        if existing != manifest:
            raise ValueError('Published version is immutable; increase versionCode')
    else:
        staging = release_dir.parent / ('.staging-' + uuid4().hex)
        try:
            staging.mkdir()
            shutil.copyfile(apk, staging / 'app.apk')
            (staging / 'manifest.json').write_text(manifest.model_dump_json(indent=2), encoding='utf-8')
            os.replace(staging, release_dir)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    # Recheck copied files before changing the only mutable pointer.
    read_release(release_dir / 'manifest.json')
    temporary = target / ('.latest-' + uuid4().hex)
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            stream.write(manifest.model_dump_json(indent=2))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, latest)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps({'published': manifest.version_name, 'version_code': manifest.version_code, 'sha256': manifest.sha256}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Directory containing only app.apk and manifest.json')
    publish(parser.parse_args().source.resolve())
