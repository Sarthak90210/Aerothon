import asyncio,json,time,sys
from pathlib import Path
from aiohttp import ClientSession,WSMsgType
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import CompressedImage
from aerothon_runtime.device_wire import unpack

async def main():
 out=Path(sys.argv[1]);frames=out/'camera_frames';frames.mkdir(parents=True,exist_ok=True)
 async with ClientSession() as client:
  manifest=await (await client.get('http://127.0.0.1:19090/manifest')).json()
  session=manifest['session'];(out/'gateway_manifest.json').write_text(json.dumps(manifest,indent=2))
  async with client.ws_connect('http://127.0.0.1:19090/camera',params={'session':session},heartbeat=2) as ws:
   with (out/'camera_capture_events.jsonl').open('a') as log:
    n=0
    async for packet in ws:
     if packet.type!=WSMsgType.BINARY:continue
     kind,body=unpack(packet.data,session);message=deserialize_message(body,CompressedImage)
     n+=1;path=f'{n:07d}.jpg';(frames/path).write_bytes(bytes(message.data))
     log.write(json.dumps({'frame':path,'capture_stamp':message.header.stamp.sec+message.header.stamp.nanosec/1e9,
       'frame_id':message.header.frame_id,'wall':time.time(),'source':'rendered gateway input'})+'\n');log.flush()

asyncio.run(main())
