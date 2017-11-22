import argparse
import asyncio
import json
import logging
import contextlib
import aiohttp
import os
from aiohttp import web
from systemd import daemon
from cococount.accounting import BeancountInterface


BASEPATH = os.path.dirname(os.path.realpath(__file__))


async def get_users_handler(message, request, socket):
    reply = {
            "state" : "send_users",
            "users" : request.app["data_interface"].get_users()}
    await socket.send_json(reply)


async def get_items_handler(message, request, socket):
    reply = {
            "state" : "send_items",
            "user" : message["user"],
            "items" : request.app["data_interface"].get_items()}
    await socket.send_json(reply)


async def do_select_handler(message, request, socket):
    if message["item-id"] is not None:
        request.app["data_interface"].add_posting(message["user"], message["item-id"])
    await socket.send_json({"state" : "done_select"})


async def do_flush_handler(message, request, socket):
    request.app["data_interface"].flush()
    await socket.send_json({"state" : "done_flush"})


async def do_reload_handler(message, request, socket):
    request.app["data_interface"].reload()
    await socket.send_json({"state" : "done_reload"})


async def do_ping_handler(message, request, socket):
    await socket.send_json({"state" : "done_ping"})


async def get_balances_handler(message, request, socket):
    await socket.send_json({
            "state" : "send_balances",
            "balances" : request.app["data_interface"].get_balances()})


async def get_balance_handler(message, request, socket):
    assert("user" in message)
    balances = request.app["data_interface"].get_balances()
    assert(message["user"] in balances)
    await socket.send_json({
            "state" : "send_balance",
            "user" : message["user"],
            "balance" : balances[message["user"]]})


async def websocket_handler(request):
    log = logging.getLogger("websocket_handler::call")
    socket = web.WebSocketResponse()
    await socket.prepare(request)
    request.app["websockets"].append(socket)
    try:
        async for raw in socket:
            if raw.type == aiohttp.WSMsgType.TEXT:
                log.debug("Received message: {}".format(raw.data))
                msg = json.loads(raw.data)
                assert(msg["state"] in request.app["consumer_dispatch"])
                await request.app["consumer_dispatch"][msg["state"]](msg, request, socket)
            elif raw.type == aiohttp.WSMsgType.ERROR:
                log.error(socket.exception())
                break
            elif raw.type == aiohttp.WSMsgType.CLOSE:
                break
    finally:
        request.app["websockets"].remove(socket)
    return socket


async def close_sockets(app):
    for socket in app["websockets"]:
        await socket.close(
                code=aiohttp.WSCloseCode.GOING_AWAY,
                message={"state" : "notify_shutdown"})


async def notify_ready(app):
    daemon.notify(daemon.Notification.READY)


async def notify_stopping(app):
    daemon.notify(daemon.Notification.STOPPING)


def main():
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
                "do_select" : do_select_handler,
                "do_flush" : do_flush_handler,
                "do_reload" : do_reload_handler,
                "do_ping" : do_ping_handler,
                "get_balances" : get_balances_handler,
                "get_balance" : get_balance_handler,
                }
        app["websockets"] = []
        app.router.add_get("/ws", websocket_handler)
        app.router.add_static("/", path=os.path.join(BASEPATH, "static"), name="static")
        # Signal handlers
        app.on_startup.append(notify_ready)
        app.on_shutdown.append(close_sockets)
        app.on_shutdown.append(notify_stopping)
        # Start the webserver
        web.run_app(app, host="127.0.0.1", port=8000)
