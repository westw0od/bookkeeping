"""Public, immutable Android releases. No account data or arbitrary file paths."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ARTIFACTS = Path(__file__).resolve().parents[1] / 'artifacts'
router = APIRouter(tags=['应用更新'])


class AndroidRelease(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1] = 1
    application_id: Literal['com.westw0od.bookkeeping']
    version_code: int = Field(gt=0)
    version_name: str = Field(pattern=r'^\d+\.\d+\.\d+(?:[.-][A-Za-z0-9]+)*$')
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    size_bytes: int = Field(gt=0, le=100 * 1024 * 1024)
    min_sdk: int = Field(ge=23, le=100)
    published_at: str = Field(max_length=40)
    notes: list[str] = Field(min_length=1, max_length=20)


@lru_cache(maxsize=16)
def file_digest(path, size, mtime_ns):
    with open(path, 'rb') as source:
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
        return digest.hexdigest()


def read_release(manifest_path):
    try:
        release = AndroidRelease.model_validate_json(manifest_path.read_text(encoding='utf-8'))
        stored = ARTIFACTS / 'android' / 'releases' / str(release.version_code) / 'manifest.json'
        if json.loads(stored.read_text(encoding='utf-8')) != release.model_dump():
            raise ValueError('Inconsistent release')
        apk = stored.parent / 'app.apk'
        stat = apk.stat()
        if stat.st_size != release.size_bytes or file_digest(str(apk), stat.st_size, stat.st_mtime_ns) != release.sha256:
            raise ValueError('Corrupt release')
        return release, apk
    except (OSError, ValueError, ValidationError):
        raise HTTPException(503, '更新包暂不可用，请稍后重试') from None


@router.get('/api/app/releases/latest')
def latest_release():
    manifest = ARTIFACTS / 'android' / 'latest.json'
    if not manifest.is_file():
        raise HTTPException(404, '尚未发布应用更新')
    release, _ = read_release(manifest)
    return {**release.model_dump(), 'download_path': f'/downloads/android/{release.version_code}/{release.sha256}.apk'}


@router.get('/downloads/android/{version_code}/{digest}.apk', include_in_schema=False)
def versioned_apk(version_code: int, digest: str):
    if version_code <= 0 or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise HTTPException(404, '更新包不存在')
    manifest = ARTIFACTS / 'android' / 'releases' / str(version_code) / 'manifest.json'
    if not manifest.is_file():
        raise HTTPException(404, '更新包不存在')
    release, apk = read_release(manifest)
    if release.version_code != version_code or release.sha256 != digest:
        raise HTTPException(404, '更新包不存在')
    return FileResponse(apk, media_type='application/vnd.android.package-archive',
                        filename=f'bookkeeping-{release.version_name}.apk',
                        headers={'Cache-Control': 'public, max-age=31536000, immutable', 'ETag': f'"{digest}"'})


def current_apk():
    release, apk = read_release(ARTIFACTS / 'android' / 'latest.json')
    return FileResponse(apk, media_type='application/vnd.android.package-archive',
                        filename=f'bookkeeping-{release.version_name}.apk', headers={'Cache-Control': 'no-store'})
