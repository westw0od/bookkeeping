import asyncio
import json

import httpx
import pytest
from main import model_error


@pytest.mark.parametrize('host,error,status,fragment', [
    ('xplt.sdu.edu.cn', httpx.ConnectTimeout, 503, '山东大学'),
    ('api.deepseek.com', httpx.ConnectError, 503, '无法连接'),
    ('api.deepseek.com', httpx.ReadTimeout, 504, '回复超时'),
])
def test_network_failures_are_actionable_without_echoing_credentials(host, error, status, fragment):
    request = httpx.Request('POST', f'https://{host}/v1/chat/completions', headers={'Authorization': 'Bearer private-test-token'})
    response = asyncio.run(model_error(None, error('private-test-token', request=request)))
    assert response.status_code == status
    assert fragment in json.loads(response.body)['detail']
    assert b'private-test-token' not in response.body


@pytest.mark.parametrize('upstream,status,fragment', [(401, 502, 'Key'), (403, 502, '权限'), (429, 429, '服务商'), (500, 502, '暂时不可用')])
def test_provider_failures_do_not_echo_response_body(upstream, status, fragment):
    request = httpx.Request('POST', 'https://api.deepseek.com/v1/chat/completions')
    original = httpx.Response(upstream, request=request, text='private-test-token')
    error = httpx.HTTPStatusError('private-test-token', request=request, response=original)
    response = asyncio.run(model_error(None, error))
    assert response.status_code == status
    assert fragment in json.loads(response.body)['detail']
    assert b'private-test-token' not in response.body
