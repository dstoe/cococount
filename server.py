import argparse
import asyncio
import websockets
import data
import json
import logging
import contextlib
from data import BeancountInterface


def get_users_handler(interface):
    async def call(message, socket):
        reply = {"state" : "prompt_users", "users" : interface.get_users()}
        await socket.send(json.dumps(reply))
    return call


def get_items_handler(interface):
    async def call(message, socket):
        reply = {
                "state" : "prompt_items",
                "user" : message["user"],
                "items" : interface.get_items()}
        await socket.send(json.dumps(reply))
    return call


def select_handler(interface):
    async def call(message, socket):
        if message["item"] is not None:
            interface.add_posting(message["user"], message["item"])
        await socket.send(json.dumps({"state" : "done"}))
    return call


def flush_handler(interface):
    async def call(message, socket):
        interface.flush()
        await socket.send(json.dumps({"state" : "done"}))
    return call


def handler(consumer_dispatch):
    async def call(websocket, path):
        while True:
            raw = await websocket.recv()
            msg = json.loads(raw)
            assert(msg["state"] in consumer_dispatch)
            await consumer_dispatch[msg["state"]](msg, websocket)
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
        start_server = websockets.serve(handler(consumer_dispatch), "0", 8765)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server)
        loop.run_forever()
