import json
import pytest
import requests

try:
    from websocket import create_connection
except ImportError:
    pytest.skip("websocket-client is required for this test", allow_module_level=True)

from neptune.neptune_api import NeptuneService
from neptune.tests.conftest import get_server_addr, get_ws_addr

@pytest.mark.fpgas(1)
def test_sface(request):
    """
    Check the streaming facedetect service from Neptune with a known video

    Args:
        request (fixture): get the cmdline options
    """
    server_addr = get_server_addr(request.config)
    ws_addr = get_ws_addr(request.config)

    service = NeptuneService(server_addr, 'sface')

    service.start()

    ws = create_connection(ws_addr)
    response = json.loads(ws.recv())
    assert isinstance(response, dict)
    assert response['topic'] == 'id'
    assert 'message' in response

    client_id = response['message']

    post_data = {
        'url': 'https://www.youtube.com/watch?v=f5NJQiY9AuY',
        'dtype': 'uint8',
        'callback_id': client_id
    }

    r = requests.post('%s/serve/sface' % server_addr, post_data)
    assert r.status_code == 200, r.text

    response = r.json()
    assert type(response) is dict
    # TODO should this response be checked?

    # collect some number of frames
    for i in range(20):
        for j in range(10):
            response = json.loads(ws.recv())
            assert isinstance(response, dict)
            assert response['topic'] == 'callback'
            assert 'message' in response

            response = json.loads(response['message'])
            assert isinstance(response, dict)
            assert 'img' in response
            assert 'boxes' in response
            assert response['callback_id'] == client_id

            # in this video, there should be a face (i.e. boxes) in all frames
            assert response['boxes']

        # issue keepalive request every so often
        r = requests.post('%s/serve/sface' % server_addr, post_data)
        assert r.status_code == 200, r.text

    ws.close()
    service.stop()
