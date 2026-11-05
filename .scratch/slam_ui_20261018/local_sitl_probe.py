"""Local real-SITL API driver and compact measurement recorder; no hardware."""
import asyncio
import json
import math
import sys
import time
import uuid
from pathlib import Path

import aiohttp

BASE = 'http://127.0.0.1:8897'
HERE = Path(__file__).resolve().parent


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 15
    latest, history, receipts, maps = {}, [], [], []
    submitted, command_outcome = None, None
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as session:
        async def post(path, data):
            async with session.post(BASE+path, json=data) as response:
                value = await response.json()
                print(json.dumps({'http': response.status, 'path': path, 'data': value}), flush=True)
                return value

        if mode == 'connect':
            await post('/api/connect', {'profile_id': 'sitl'})
            return
        async with session.ws_connect(BASE+'/ws?map_encoding=rle', heartbeat=4, max_msg_size=8*1024*1024) as ws:
            async def reader():
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    env = json.loads(msg.data)
                    kind, data = env.get('kind'), env.get('data')
                    if kind == 'telemetry':
                        latest.clear()
                        latest.update(data)
                        history.append({'wall': time.time(), 'mission': data.get('mission'),
                            'safety': data.get('safety'), 'devices': data.get('devices'),
                            'execution': data.get('execution'), 'winch': data.get('winch')})
                    elif kind in ('receipt', 'execution'):
                        receipts.append({'kind': kind, 'data': data})
                    elif kind == 'map':
                        maps.append({'wall':time.time(), 'stamp': data.get('stamp'),
                            'width':data.get('width'), 'height':data.get('height'),
                            'resolution':data.get('resolution'), 'frame':data.get('frame')})
            task = asyncio.create_task(reader())
            started = time.monotonic()
            while not latest and time.monotonic()-started < 12:
                await asyncio.sleep(.1)
            if mode == 'command':
                argument = sys.argv[3]
                value = json.loads(Path(argument[1:]).read_text() if argument.startswith('@') else argument)
                if value.get('cmd') == 'start':
                    selected = value.get('args', {}).get('task')
                    keys = {'mission': ('identity','camera','lidar','clock','camera_actuator','winch_actuator'),
                            'delivery_here': ('identity','camera','lidar','clock','camera_actuator','winch_actuator'),
                            'delivery_gps': ('identity','camera','lidar','clock','camera_actuator','winch_actuator'),
                            'mechanism': ('winch_actuator',)}.get(selected, ())
                    waiting = time.monotonic()
                    stable = None
                    while keys and time.monotonic()-waiting < 20:
                        good = all(latest.get('devices',{}).get(key,{}).get('ok') is True for key in keys)
                        stable = (stable or time.monotonic()) if good else None
                        if stable and time.monotonic()-stable >= .6:
                            break
                        await asyncio.sleep(.1)
                    print(json.dumps({'capability_wait_s':round(time.monotonic()-waiting,2),
                        'task': selected, 'devices': latest.get('devices')}), flush=True)
                value.setdefault('command_id', 'local_'+uuid.uuid4().hex)
                value.setdefault('confirm', True)
                submitted = await post('/api/commands', value)
            elif mode == 'setup':
                def global_point(x, y):
                    lat, lon = -35.3632439, 149.1652163
                    return {'lat': lat+math.degrees(y/6378137),
                            'lon': lon+math.degrees(x/(6378137*math.cos(math.radians(lat))))}
                layout = json.loads(Path('/tmp/aerothon_arena_layout.json').read_text())
                x0, x1, y0, y1 = layout['geofence_rect']
                fence = [global_point(x,y) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
                cx, cy, width, height = layout['delivery_zone_rect']
                zone = [global_point(x,y) for x,y in ((cx-width/2,cy-height/2),
                    (cx+width/2,cy-height/2),(cx+width/2,cy+height/2),(cx-width/2,cy+height/2))]
                dims = json.loads(json.dumps(latest['dimension_presets']['builtin']['Simulator arena']))
                dims['qr']['target_m'] = 3.0
                values = [('set_geofence', {'vertices': fence}),
                    ('set_delivery_zone', {'vertices': zone}),
                    ('set_banner_colours', {'colours': {'green':'#039E3D','orange':'#FF8000','red':'#F20A0A'}}),
                    ('set_arena_dimensions', {'dimensions': dims})]
                for cmd, args in values:
                    await post('/api/commands', {'command_id':'local_'+uuid.uuid4().hex,
                        'cmd':cmd, 'args':args, 'confirm':True})
                    await asyncio.sleep(.5)
            elif mode == 'configure':
                if latest.get('mission',{}).get('armed') is not False:
                    raise RuntimeError('configuration requires confirmed live disarm')
                await post('/api/disconnect', {})
                profile = json.loads((HERE/'local_sitl_state/profiles.json').read_text())['sitl']
                profile['marker_m'] = 3.0
                profile['venue_file'] = str(HERE/'local_sitl_venue.yaml')
                await post('/api/profiles', profile)
                await post('/api/connect', {'profile_id':'sitl'})
            elif mode == 'disconnect':
                await post('/api/disconnect', {})
            if submitted and submitted.get('command_id'):
                end = time.monotonic()+duration
                while time.monotonic() < end:
                    async with session.get(BASE+'/api/commands/'+submitted['command_id']) as response:
                        command_outcome = await response.json()
                    if command_outcome.get('state') in ('Completed','Failed','Outcome unknown'):
                        await asyncio.sleep(1.2)
                        break
                    await asyncio.sleep(1)
            elif mode == 'command':
                command_outcome = submitted
                await asyncio.sleep(1.2)
            else:
                await asyncio.sleep(duration)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            tag = sys.argv[4] if len(sys.argv) > 4 else mode
            output = HERE/f'local_{tag}_{time.time_ns()}.json'
            output.write_text(json.dumps({'latest': latest, 'receipts': receipts,
                'history': history, 'maps':maps, 'command_outcome':command_outcome}, indent=2))
            summary = {key: latest.get(key) for key in ('mission','flight','gps','safety',
                'sample_age_s','devices','runtime_health','winch','execution','slam_status','slam_pose')}
            print(json.dumps({'snapshot': str(output), 'latest': summary, 'command_outcome':command_outcome,
                'receipts': receipts[-12:]}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
