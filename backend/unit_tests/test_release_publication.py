import hashlib
import importlib.util
import json
from pathlib import Path
import pytest
import app_releases

spec = importlib.util.spec_from_file_location('publish_android', Path(__file__).resolve().parents[2] / 'scripts/publish-android-release.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


@pytest.fixture
def publication(tmp_path, monkeypatch):
    monkeypatch.setattr(publisher, 'ROOT', tmp_path / 'server')
    monkeypatch.setattr(app_releases, 'ARTIFACTS', tmp_path / 'server/artifacts')
    source = tmp_path / 'upload'
    source.mkdir()
    body = b'publication fixture'
    manifest = dict(schema_version=1, application_id='com.westw0od.bookkeeping', version_code=7, version_name='2.4.0',
        sha256=hashlib.sha256(body).hexdigest(), size_bytes=len(body), min_sdk=23,
        published_at='2026-11-23T08:00:00Z', notes=['应用内更新'])
    (source / 'app.apk').write_bytes(body)
    (source / 'manifest.json').write_text(json.dumps(manifest))
    return source, tmp_path / 'server/artifacts/android', manifest


def test_first_publish_and_identical_retry_are_consistent(publication):
    source, target, manifest = publication
    publisher.publish(source)
    publisher.publish(source)
    assert json.loads((target / 'latest.json').read_text(encoding='utf-8')) == manifest
    assert (target / 'releases/7/app.apk').read_bytes() == (source / 'app.apk').read_bytes()
    assert not list(target.glob('.latest-*'))


def test_corrupt_upload_does_not_change_published_release(publication):
    source, target, manifest = publication
    publisher.publish(source)
    (source / 'app.apk').write_bytes(b'x' * manifest['size_bytes'])
    with pytest.raises(ValueError, match='SHA256'):
        publisher.publish(source)
    assert json.loads((target / 'latest.json').read_text(encoding='utf-8')) == manifest


def test_relabel_and_downgrade_cannot_replace_existing_version(publication):
    source, target, manifest = publication
    publisher.publish(source)
    for changes in [dict(notes=['changed after publish']), dict(version_code=6)]:
        (source / 'manifest.json').write_text(json.dumps({**manifest, **changes}))
        with pytest.raises(ValueError):
            publisher.publish(source)
    assert json.loads((target / 'latest.json').read_text(encoding='utf-8')) == manifest
