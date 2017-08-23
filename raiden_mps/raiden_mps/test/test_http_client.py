import logging
import json

from raiden_mps import DefaultHTTPClient
from raiden_mps.client import Channel

log = logging.getLogger(__name__)


def check_response(response: bytes):
    assert response.decode().strip() == '"HI I AM A DOGGO"'


def test_default_http_client(
        doggo_proxy,
        default_http_client: DefaultHTTPClient,
        clean_channels,
        sender_address,
        receiver_address
):
    logging.basicConfig(level=logging.INFO)

    check_response(default_http_client.run('doggo.jpg'))

    client = default_http_client.client
    open_channels = client.get_open_channels()
    assert len(open_channels) == 1

    channel = open_channels[0]
    assert channel == default_http_client.channel
    assert channel.balance_sig
    assert channel.balance < channel.deposit
    assert channel.sender == sender_address
    assert channel.receiver == receiver_address


def test_default_http_client_topup(
        doggo_proxy, default_http_client: DefaultHTTPClient, clean_channels
):
    logging.basicConfig(level=logging.INFO)

    # Create a channel that has just enough capacity for one transfer.
    default_http_client.initial_deposit = lambda x: 0
    check_response(default_http_client.run('doggo.jpg'))

    client = default_http_client.client
    open_channels = client.get_open_channels()
    assert len(open_channels) == 1
    channel1 = open_channels[0]
    assert channel1 == default_http_client.channel
    assert channel1.balance_sig
    assert channel1.balance == channel1.deposit

    # Do another payment. Topup should occur.
    check_response(default_http_client.run('doggo.jpg'))
    open_channels = client.get_open_channels()
    assert len(open_channels) == 1
    channel2 = open_channels[0]
    assert channel2 == default_http_client.channel
    assert channel2.balance_sig
    assert channel2.balance < channel2.deposit
    assert channel1 == channel2


def test_default_http_client_close(
    doggo_proxy, default_http_client: DefaultHTTPClient, clean_channels
):
    logging.basicConfig(level=logging.INFO)

    client = default_http_client.client
    check_response(default_http_client.run('doggo.jpg'))
    default_http_client.close_active_channel()
    open_channels = client.get_open_channels()
    assert len(open_channels) == 0


def test_default_http_client_existing_channel(
        doggo_proxy, default_http_client: DefaultHTTPClient, clean_channels, receiver_address
):
    logging.basicConfig(level=logging.INFO)

    client = default_http_client.client
    channel = client.open_channel(receiver_address, 50)
    check_response(default_http_client.run('doggo.jpg'))
    assert channel.balance == 2
    assert channel.deposit == 50


def test_default_http_client_existing_channel_topup(
        doggo_proxy, default_http_client: DefaultHTTPClient, clean_channels, receiver_address
):
    logging.basicConfig(level=logging.INFO)

    client = default_http_client.client
    default_http_client.topup_deposit = lambda x: 13
    channel = client.open_channel(receiver_address, 1)
    check_response(default_http_client.run('doggo.jpg'))
    assert channel.balance == 2
    assert channel.deposit == 13


def test_coop_close(doggo_proxy, default_http_client: DefaultHTTPClient, clean_channels,
                    sender_address, receiver_address):
    logging.basicConfig(level=logging.INFO)

    check_response(default_http_client.run('doggo.jpg'))

    client = default_http_client.client
    open_channels = [c for c in client.channels if c.state == Channel.State.open]
    assert len(open_channels) == 1

    channel = open_channels[0]
    import requests
    reply = requests.get('http://localhost:5000/api/1/channels/%s/%s' %
                         (channel.sender, channel.block))
    assert reply.status_code == 200
    json_reply = json.loads(reply.text)

    request_data = {'signature': json_reply['last_signature']}
    reply = requests.delete('http://localhost:5000/api/1/channels/%s/%s' %
                            (channel.sender, channel.block), data=request_data)

    assert reply.status_code == 200