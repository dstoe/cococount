import argparse
import asyncio
import json
import logging
import contextlib
import aiohttp
from aiohttp import web
from data import BeancountInterface


async def get_users_handler(message, request, socket):
    reply = {
            "state" : "prompt_users",
            "users" : request.app["data_interface"].get_users()}
    await socket.send_json(reply)


async def get_items_handler(message, request, socket):
    reply = {
            "state" : "prompt_items",
            "user" : message["user"],
            "items" : request.app["data_interface"].get_items()}
    await socket.send_json(reply)


async def select_handler(message, request, socket):
    if message["item"] is not None:
        request.app["data_interface"].add_posting(message["user"], message["item"])
    await socket.send_json({"state" : "done"})


async def flush_handler(message, request, socket):
    request.app["data_interface"].flush()
    await socket.send_json({"state" : "done"})


async def reload_handler(message, request, socket):
    request.app["data_interface"].reload()
    await socket.send_json({"state" : "done"})


async def websocket_handler(request):
    log = logging.getLogger("websocket_handler::call")
    socket = web.WebSocketResponse()
    await socket.prepare(request)
    async for raw in socket:
        if raw.type == aiohttp.WSMsgType.TEXT:
            msg = json.loads(raw.data)
            assert(msg["state"] in request.app["consumer_dispatch"])
            await request.app["consumer_dispatch"][msg["state"]](msg, request, socket)
        elif raw.type == aiohttp.WSMsgType.ERROR:
            log.error(socket.exception())
    log.debug("Websocket closed")
    return socket


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("transactions", type=str)
    parser.add_argument("--logfile", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(filename=args.logfile, level=logging.DEBUG)

    with contextlib.closing(BeancountInterface(args.transactions)) as iface:
        # Setup webserver
        app = web.Application()
        app["data_interface"] = iface
        app["consumer_dispatch"] = {
                "get_users" : get_users_handler,
                "get_items" : get_items_handler,
                "select" : select_handler,
                "flush" : flush_handler,
                "reload" : reload_handler}
        app.router.add_get("/ws", websocket_handler)
        app.router.add_static("/", path="www", name="static")
        # Start the webserver
        web.run_app(app, host="127.0.0.1", port=8000)
