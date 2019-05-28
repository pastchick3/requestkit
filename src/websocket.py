from __future__ import annotations

__all__ = ['Jsonable', 'WebSocketServer', 'WebSocketClient']

import asyncio
import json
import logging
import reprlib
from queue import Empty, Full, Queue
from threading import Thread
from time import sleep
from typing import Callable, List, Optional, Union

from aiohttp import ClientSession, WSMsgType, web

from .request import Jsonable


class _AbstractWebSocket:

    def __init__(self, *,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 route: str = '/ws',
                 maxsize: int = 0,
                 callbacks: Optional[List[Callable]] = None) -> None:
        self._name = self.__class__.__name__
        self._logger = logging.getLogger(f'{self._name}')
        self._host = host
        self._port = port
        self._route = route
        self._maxsize = maxsize
        self._callbacks = self._prepare_callbacks(callbacks)
        self._queue = Queue(self._maxsize)
        self._running = True
        self._stopped = False
        self._thread = Thread(target=self._main)
        self._thread.start()

    def send(self, item: Union[str, bytes, Jsonable]) -> None:
        try:
            self._queue.put_nowait(item)
        except Full:
            self._queue.get_nowait()
            self._queue.task_done()
            self._queue.put_nowait(item)

    def join(self) -> None:
        self._queue.join()

    def close(self) -> None:
        self._running = False
        while self._thread.is_alive():
            sleep(0.1)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _prepare_callbacks(self, callbacks):
        cb_dict = {
            'str': [],
            'bytes': [],
            'Jsonable': [],
        }
        if callbacks:
            for cb in callbacks:
                key = cb.__annotations__.get('msg')
                if key in cb_dict:
                    cb_dict[key].append(cb)
                else:
                    raise RuntimeError('Expect "msg" parameter with annotation'
                                       ' type: str, bytes, or Jsonable.')
        return cb_dict

    def _main(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        raise NotImplementedError

    async def _loop(self, ws):
        self._logger.info('start')
        self._logger.info(f'callbacks: {self._callbacks}')
        while self._running:
            try:
                msg = await ws.receive(timeout=0.05)
            except asyncio.TimeoutError:
                pass
            else:
                data = msg.data
                if data is not None:
                    self._logger.debug(f'receive {reprlib.repr(data)}')
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(data)
                    except ValueError:
                        for cb in self._callbacks['str']:
                            cb(data, self)
                    else:
                        for cb in self._callbacks['Jsonable']:
                            cb(data, self)
                elif msg.type == WSMsgType.BINARY:
                    for cb in self._callbacks['bytes']:
                        cb(data, self)
            try:
                item = self._queue.get_nowait()
            except Empty:
                pass
            else:
                self._logger.debug(f'send {reprlib.repr(item)}')
                if isinstance(item, str):
                    await ws.send_str(item)
                elif isinstance(item, bytes):
                    await ws.send_bytes(item)
                else:
                    await ws.send_json(item)
                self._queue.task_done()
        await ws.close()
        self._logger.info('close')
        self._stopped = True


class WebSocketServer(_AbstractWebSocket):

    async def _async_main(self):
        app = web.Application()
        app.add_routes([web.get(self._route, self._handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port)
        await site.start()
        while not self._stopped:
            await asyncio.sleep(0.1)
        await runner.cleanup()

    async def _handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self._loop(ws)
        return ws


class WebSocketClient(_AbstractWebSocket):

    async def _async_main(self):
        async with ClientSession() as session:
            async with session.ws_connect(f'http://{self._host}:{self._port}'
                                          f'{self._route}') as ws:
                await self._loop(ws)
