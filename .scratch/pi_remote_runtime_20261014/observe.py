import asyncio,json,time,sys
from pathlib import Path
from aiohttp import ClientSession,WSMsgType

async def main():
 out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
 duration=float(sys.argv[2]) if len(sys.argv)>2 else 300
 end=time.monotonic()+duration
 async with ClientSession() as client:
  async with client.ws_connect('http://192.168.0.101:8899/ws',heartbeat=2) as ws:
   with (out/'telemetry.jsonl').open('a') as log:
    async for message in ws:
     if message.type!=WSMsgType.TEXT:continue
     d=json.loads(message.data);d['observer_wall']=time.time()
     log.write(json.dumps(d)+'\n');log.flush()
     if d.get('kind')=='telemetry':
      temp=out/'latest.tmp';temp.write_text(json.dumps(d['data'],indent=2));temp.replace(out/'latest.json')
     if time.monotonic()>end:break

asyncio.run(main())
