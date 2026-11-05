"""Local display fixture: real web host, synthetic vehicle, no hardware."""
import asyncio
import sys
from aiohttp import web as aioweb
from aerothon_runtime import web

async def fixture_launch(profile):
    return await asyncio.create_subprocess_exec('sleep', 'infinity', start_new_session=True)

host = web.Host(sys.argv[1], sys.argv[2], launch=fixture_launch,
                aggregator='http://127.0.0.1:8777')
aioweb.run_app(web.application(host), host='127.0.0.1', port=8898)
