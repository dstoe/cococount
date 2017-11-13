import argparse
import asyncio
import json
import logging
import contextlib
import aiohttp
from aiohttp import web
from data import BeancountInterface


def get_users_handler(interface):
    async def call(message, socket):
        reply = {"state" : "prompt_users", "users" : interface.get_users()}
        await socket.send_json(reply)
    return call


def get_items_handler(interface):
    async def call(message, socket):
        reply = {
                "state" : "prompt_items",
                "user" : message["user"],
                "items" : interface.get_items()}
        await socket.send_json(reply)
    return call


def select_handler(interface):
    async def call(message, socket):
        if message["item"] is not None:
            interface.add_posting(message["user"], message["item"])
        await socket.send_json({"state" : "done"})
    return call


def flush_handler(interface):
    async def call(message, socket):
        interface.flush()
        await socket.send_json({"state" : "done"})
    return call


def websocket_handler(consumer_dispatch):
    async def call(request):
        log = logging.getLogger("websocket_handler::call")
        socket = web.WebSocketResponse()
        await socket.prepare(request)
        async for raw in socket:
            if raw.type == aiohttp.WSMsgType.TEXT:
                msg = json.loads(raw.data)
                assert(msg["state"] in consumer_dispatch)
                await consumer_dispatch[msg["state"]](msg, socket)
            elif raw.type == aiohttp.WSMsgType.ERROR:
                log.error(socket.exception())
        log.debug("Websocket closed")
        return socket
    return call


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("transactions", type=str)
    parser.add_argument("--logfile", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(filename=args.logfile, level=logging.DEBUG)

    with contextlib.closing(BeancountInterface(args.transactions)) as iface:
        consumer_dispatch = {
                "get_users" : get_users_handler(iface),
                "get_items" : get_items_handler(iface),
                "select" : select_handler(iface),
                "flush" : flush_handler(iface),
                }

        # Start the webserver
        app = web.Application()
        app.router.add_get("/ws", websocket_handler(consumer_dispatch))
        app.router.add_static("/", path="www", name="static")
        web.run_app(app, host="127.0.0.1", port=8000)
