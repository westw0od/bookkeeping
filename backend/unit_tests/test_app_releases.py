import hashlib
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import app_releases as releases


@pytest.fixture
def publication(tmp_path, monkeypatch):
    monkeypatch.setattr(releases, 'ARTIFACTS', tmp_path)
    body = b'synthetic APK fixture'
    meta = dict(schema_version=1, application_id='com.westw0od.bookkeeping', version_code=7, version_name='2.4.0',
                sha256=hashlib.sha256(body).hexdigest(), size_bytes=len(body), min_sdk=23,
                published_at='2026-11-23T08:00:00Z', notes=['应用内更新'])
    folder = tmp_path / 'android' / 'releases' / '7'
    folder.mkdir(parents=True)
    (folder / 'app.apk').write_bytes(body)
    (folder / 'manifest.json').write_text(json.dumps(meta))
    (tmp_path / 'android' / 'latest.json').write_text(json.dumps(meta))
    app = FastAPI()
    app.include_router(releases.router)
    with TestClient(app) as client:
        yield client, tmp_path, meta, body


def test_public_metadata_pins_exact_download_and_preserves_previous_versions(publication):
    client, root, meta, body = publication
    response = client.get('/api/app/releases/latest')
    assert response.status_code == 200
    download = client.get(response.json()['download_path'])
    assert download.content == body
    assert '2.4.0.apk' in download.headers['content-disposition']
    (root / 'android' / 'latest.json').unlink()
    assert client.get(response.json()['download_path']).content == body
    assert client.get('/api/app/releases/latest').status_code == 404


@pytest.mark.parametrize('damage', ['bytes', 'size', 'identity', 'missing', 'pointer'])
def test_incomplete_or_tampered_publications_fail_closed(publication, damage):
    client, root, meta, body = publication
    folder = root / 'android' / 'releases' / '7'
    if damage == 'bytes':
        (folder / 'app.apk').write_bytes(b'x' * len(body))
    elif damage == 'missing':
        (folder / 'app.apk').unlink()
    elif damage == 'pointer':
        meta['version_name'] = '2.4.1'
        (root / 'android' / 'latest.json').write_text(json.dumps(meta))
    else:
        meta['size_bytes' if damage == 'size' else 'application_id'] = 1 if damage == 'size' else 'other.app'
        (root / 'android' / 'latest.json').write_text(json.dumps(meta))
        (folder / 'manifest.json').write_text(json.dumps(meta))
    assert client.get('/api/app/releases/latest').status_code == 503


def test_download_cannot_select_other_files_or_wrong_hash(publication):
    client, _, meta, _ = publication
    for path in ['/downloads/android/-1/a.apk', '/downloads/android/7/secret.apk', '/downloads/android/8/' + meta['sha256'] + '.apk', '/downloads/android/7/' + '0' * 64 + '.apk']:
        assert client.get(path).status_code == 404
