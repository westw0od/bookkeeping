"""Prepare immutable publication files after building and verifying an APK."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app_releases import AndroidRelease


def prepare(apk, metadata, notes):
    build = json.loads(metadata.read_text(encoding='utf-8'))
    element = build['elements'][0]
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    release = AndroidRelease(application_id=build['applicationId'], version_code=element['versionCode'],
        version_name=element['versionName'], sha256=digest, size_bytes=apk.stat().st_size, min_sdk=23,
        published_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(), notes=notes)
    folder = ROOT / 'artifacts' / 'android' / 'releases' / str(release.version_code)
    if folder.exists():
        raise SystemExit('Version already prepared. Use a higher versionCode; published releases must remain immutable.')
    folder.mkdir(parents=True)
    shutil.copyfile(apk, folder / 'app.apk')
    payload = release.model_dump_json(indent=2)
    (folder / 'manifest.json').write_text(payload, encoding='utf-8')
    (folder.parents[1] / 'latest.json').write_text(payload, encoding='utf-8')
    print(f'Release {release.version_name}, versionCode={release.version_code}, SHA256={digest}')
    print(f'Publication folder: {folder.parents[1]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, default=ROOT / 'artifacts' / 'bookkeeping-debug.apk')
    parser.add_argument('--metadata', type=Path, default=ROOT / 'frontend/android/app/build/outputs/apk/debug/output-metadata.json')
    parser.add_argument('--note', action='append', required=True)
    args = parser.parse_args()
    if any(not note.strip() or len(note) > 1000 for note in args.note):
        parser.error('Each release note must contain 1–1000 characters')
    prepare(args.apk, args.metadata, args.note)
