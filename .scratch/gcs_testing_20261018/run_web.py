#!/usr/bin/env python3
"""The real web host with a stand-in runtime launch (a sleeping process)."""
import asyncio, sys
from aiohttp import web as aioweb
from aerothon_runtime import web

async def fake_launch(p):
    return await asyncio.create_subprocess_exec('sleep', 'infinity', start_new_session=True)

static, state, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
host = web.Host(static, state, launch=fake_launch)
aioweb.run_app(web.application(host), host='127.0.0.1', port=port)
