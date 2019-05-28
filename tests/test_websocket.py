from __future__ import annotations

import logging
import unittest
from time import sleep

from ..src import Jsonable, WebSocketClient, WebSocketServer


HOST = '127.0.0.1'
PORT = 20000
ROUTE = '/test'
MAXSIZE = 4


DATA = ['str', b'bytes', {'k': 'v'}]
FLAG = [False, False, False]


class TestWebSocket(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        for name in ['WebSocketServer', 'WebSocketClient']:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
            sh = logging.StreamHandler()
            sh.setLevel(logging.DEBUG)
            sh.setFormatter(formatter)
            logger.addHandler(sh)

    def str_cb(self, msg: str, client):
        self.assertEqual(msg, DATA[0])
        FLAG[0] = True

    def bytes_cb(self, msg: bytes, client):
        self.assertEqual(msg, DATA[1])
        FLAG[1] = True

    def Jsonable_cb(self, msg: Jsonable, client):
        self.assertEqual(msg, DATA[2])
        FLAG[2] = True

    def test_websocket(self):
        with WebSocketClient(host=HOST, port=PORT, route=ROUTE, maxsize=MAXSIZE,
                             callbacks=[self.str_cb, self.bytes_cb, self.Jsonable_cb]):
            with WebSocketServer(host=HOST, port=PORT, route=ROUTE, maxsize=MAXSIZE) as server:
                sleep(1)
                for data in DATA:
                    server.send(data)
                server.join()
                while not all(FLAG):
                    sleep(1)
