# tsuserver3, an Attorney Online server
#
# Copyright (C) 2017 argoneus <argoneuscze@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio

from websockets import ConnectionClosed
from aiohttp import WSMsgType

from server.network.aoprotocol import AOProtocol


class AOProtocolWS(AOProtocol):
    """A websocket wrapper around AOProtocol."""

    class TransportWrapper:
        """A class to wrap asyncio's Transport class."""

        def __init__(self, websocket):
            self.ws = websocket

        def get_extra_info(self, key):
            """Get extra info about the client.
            Used for getting the remote address.

            :param key: requested key

            """
            info = {'peername': self.ws.remote_address}
            return info[key]

        def write(self, message):
            """Write message to the socket.

            :param message: message in bytes

            """
            message = message.decode('utf-8')
            asyncio.ensure_future(self.ws_try_writing_message(message))

        def close(self):
            """Disconnect the client by force."""
            asyncio.ensure_future(self.ws.close())

        async def ws_try_writing_message(self, message):
            """
            Try writing the message if the client has not already closed
            the connection.
            """
            try:
                await self.ws.send(message)
            except ConnectionClosed:
                return

    def __init__(self, server, websocket):
        super().__init__(server)
        self.ws = websocket
        self.ws_connected = True

        self.ws_on_connect()

    def ws_on_connect(self):
        """Handle a new client connection."""
        print(f"DEBUG: New WebSocket client connected from {self.ws.remote_address}")
        self.connection_made(self.TransportWrapper(self.ws))

    async def ws_handle(self):
        try:
            data = await self.ws.recv()
            print(f"DEBUG: Received from client: {data}")
            self.data_received(data)
        except Exception as exc:
            # Any event handled in data_received could raise any exception
            self.ws_connected = False
            self.connection_lost(exc)


def new_websocket_client(server):
    """
    Factory for creating a new WebSocket client.
    :param server: server object

    """
    async def func(websocket, _):
        client = AOProtocolWS(server, websocket)
        while client.ws_connected:
            await client.ws_handle()

    return func


class AOProtocolAioHTTP(AOProtocol):
    """An aiohttp websocket wrapper around AOProtocol."""

    class TransportWrapper:
        """A class to wrap aiohttp WebSocketResponse transport behavior."""

        def __init__(self, websocket, request):
            self.ws = websocket
            self.request = request

        def get_extra_info(self, key):
            """Get extra info about the client.
            Used for getting the remote address.

            :param key: requested key

            """
            peername = None
            transport = self.request.transport
            if transport is not None:
                peername = transport.get_extra_info('peername')
            info = {'peername': peername}
            return info.get(key)

        def write(self, message):
            """Write message to the socket.

            :param message: message in bytes

            """
            message = message.decode('utf-8')
            asyncio.ensure_future(self.ws_try_writing_message(message))

        def close(self):
            """Disconnect the client by force."""
            asyncio.ensure_future(self.ws.close())

        async def ws_try_writing_message(self, message):
            """Try writing if the client has not closed the connection."""
            if self.ws.closed:
                return
            await self.ws.send_str(message)

    def __init__(self, server, websocket, request):
        super().__init__(server)
        self.ws = websocket
        self.request = request
        self.ws_connected = True
        self.connection_made(self.TransportWrapper(self.ws, self.request))

    async def ws_handle(self):
        try:
            message = await self.ws.receive()
            if message.type == WSMsgType.TEXT:
                self.data_received(message.data)
            elif message.type == WSMsgType.BINARY:
                self.data_received(message.data)
            elif message.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
                self.ws_connected = False
                self.connection_lost(None)
            elif message.type == WSMsgType.ERROR:
                self.ws_connected = False
                self.connection_lost(self.ws.exception())
        except Exception as exc:
            self.ws_connected = False
            self.connection_lost(exc)
