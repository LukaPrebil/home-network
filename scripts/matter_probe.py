#!/usr/bin/env python3
"""Read-only WebSocket probe for matter-server (fabric identity + node inventory).

Connects to the matter-server WebSocket API, reads the server-info message,
requests the node list, and prints:

- compressed_fabric_id (the migration tripwire value)
- SDK and schema versions
- node count and a one-liner per node (node_id, vendor/product, available)
- all 0/56/* attributes for nodes exposing the Time Synchronization cluster (56)

The probe never mutates the fabric: it only reads server info and get_nodes.

Usage:
    python3 -m venv /tmp/mp-venv
    /tmp/mp-venv/bin/pip install websockets
    /tmp/mp-venv/bin/python scripts/matter_probe.py [ws://host:port/ws]

Defaults to ws://192.168.1.110:5580/ws (matter-server on rpi4).
"""

import asyncio
import json
import sys

import websockets

DEFAULT_URL = "ws://192.168.1.110:5580/ws"

VENDOR_NAME_ATTR = "0/40/1"
PRODUCT_NAME_ATTR = "0/40/3"
TIME_SYNC_CLUSTER_PREFIX = "0/56/"
GET_NODES_MESSAGE_ID = "matter-probe-get-nodes"


async def probe(url):
    async with websockets.connect(url, max_size=2**26) as ws:
        server_info = json.loads(await ws.recv())
        print(f"Server: {url}")
        print(f"  compressed_fabric_id: {server_info.get('compressed_fabric_id')}")
        print(f"  fabric_id:            {server_info.get('fabric_id')}")
        print(f"  sdk_version:          {server_info.get('sdk_version')}")
        print(f"  schema_version:       {server_info.get('schema_version')}")
        print()

        await ws.send(json.dumps({"message_id": GET_NODES_MESSAGE_ID, "command": "get_nodes"}))

        # The server interleaves event messages; only the reply carries our message_id
        while True:
            message = json.loads(await ws.recv())
            if message.get("message_id") == GET_NODES_MESSAGE_ID:
                break

        if message.get("error_code") is not None:
            print(f"get_nodes failed: {message}")
            sys.exit(1)

        nodes = message.get("result") or []
        print(f"Nodes: {len(nodes)}")
        for node in sorted(nodes, key=lambda n: n.get("node_id", 0)):
            attributes = node.get("attributes") or {}
            vendor = attributes.get(VENDOR_NAME_ATTR, "?")
            product = attributes.get(PRODUCT_NAME_ATTR, "?")
            print(
                f"  node {node.get('node_id')}: {vendor} / {product}"
                f" (available={node.get('available')})"
            )

            time_sync_attrs = {
                key: value
                for key, value in attributes.items()
                if key.startswith(TIME_SYNC_CLUSTER_PREFIX)
            }
            for key in sorted(time_sync_attrs, key=lambda k: int(k.rsplit("/", 1)[-1])):
                print(f"    {key} = {time_sync_attrs[key]}")


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    asyncio.run(probe(url))


if __name__ == "__main__":
    main()
