import fs from 'node:fs';
const base=process.argv[2]||'http://192.168.0.104:8899';
const output=process.argv[3]||'.scratch/pi_deploy_20261019/gcs_live.json';
const state=await (await fetch(base+'/api/state',{signal:AbortSignal.timeout(6000)})).json();
const html=await (await fetch(base+'/',{signal:AbortSignal.timeout(6000)})).text();
const asset=html.match(/\/assets\/index-[^" ]+\.js/)?.[0];
const sample={endpoint:base,asset,profile_id:state.profile_id,runtime:state.runtime,host_fresh:state.fresh,execution:state.execution,
    telemetry_messages:0,map_messages:0,closes:0,first:null,last:null};
const socket=new WebSocket(base.replace(/^http/,'ws')+'/ws?map_encoding=rle');
const summary=d=>({mission:d.mission,sample_age_s:d.sample_age_s,slam_status:d.slam_status,slam_pose:d.slam_pose,
    scan_frame:d.scan?.frame,scan_returns:d.scan?.ranges?.filter(Number.isFinite).length||0,
    scan_total:d.scan?.ranges?.length||0,devices:d.devices});
socket.onmessage=e=>{const p=JSON.parse(e.data);if(p.kind==='telemetry'){sample.telemetry_messages++;sample.first??=summary(p.data);sample.last=summary(p.data)}else if(p.kind==='map')sample.map_messages++;};
socket.onclose=()=>sample.closes++;
socket.onerror=()=>{};
await new Promise(r=>setTimeout(r,12000));
sample.closed_while_sampling=sample.closes;
socket.close();
fs.writeFileSync(output,JSON.stringify(sample,null,2));
console.log(JSON.stringify({endpoint:base,asset,runtime:sample.runtime,messages:sample.telemetry_messages,maps:sample.map_messages,
    disconnects:sample.closed_while_sampling,mission:sample.last?.mission,source_ages:sample.last?.sample_age_s,
    scan_returns:sample.last?.scan_returns,scan_total:sample.last?.scan_total}));
