from pathlib import Path
p=Path('src/aerothon_gcs/tauri_app/src/App.tsx')
s=p.read_text()
s=s.replace('  commandEnvelope,\n','').replace('  defaultProfile,\n','').replace('  endpoint,\n','').replace('  type ConnectionProfile,','  api,\n  type HostState,')
s=s.replace('import ArenaDimensions', 'import Connections from "./Connections";\nimport ArenaDimensions')
a=s.index('function savedProfiles()');b=s.index('export default function App()',a);s=s[:a]+s[b:]
a=s.index('  const [profiles,');b=s.index('  const [linked,',a)
s=s[:a]+'''  const activeEndpoint = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
  const [hostState, setHostState] = useState<HostState | null>(null);
  const [waypoints, setWaypoints] = useState('');
  async function refreshHost() {
    try { setHostState(await api('/api/state')); } catch { setHostState(null); }
  }
  useEffect(() => { void refreshHost(); const timer = window.setInterval(() => void refreshHost(), 2000); return () => window.clearInterval(timer); }, []);
'''+s[b:]
s=s.replace('    if (!enabled) return;\n','').replace('  }, [activeEndpoint, nonce, enabled]);','  }, [activeEndpoint]);')
s=s.replace('          } else if (envelope.kind === "map") {','          } else if (envelope.kind === "execution" || envelope.kind === "receipt") {\n            setOutcome({ ...envelope.data, cmd: "execution" });\n            setStarting(false);\n          } else if (envelope.kind === "map") {')
a=s.index('    return new Promise((resolve) => {',s.index('  async function send('));b=s.index('\n  async function perform(',a)
s=s[:a]+'''    try {
      const result = await api('/api/commands', {command_id:id, cmd, args, confirm:true});
      setOutcome({...result, cmd});
      return {...result, cmd};
    } catch (e) {
      const result = {...submitted, state:'Outcome unknown' as const, reason: e instanceof Error ? e.message : String(e)};
      setOutcome(result);
      return result;
    }
  }
'''+s[b:]
s=s.replace('cmd === "start_mission" || cmd === "start_test"', 'cmd === "start"')
s=s.replace('review.cmd === "start_mission" || review.cmd === "start_test"','review.cmd === "start"')
a=s.index('  function saveProfile()');b=s.index('  useEffect(() => {',a);s=s[:a]+s[b:]
a=s.index('      {settings && (');b=s.index('      <main>',a)
s=s[:a]+'      {settings && <Connections state={hostState} refresh={refreshHost} />}\n'+s[b:]
s=s.replace('const request = taskCommand(selectedTask, action);','const request = taskCommand(selectedTask, action, {height, target, waypoints: waypoints.trim() ? boundary(waypoints) : []});')
s=s.replace('cmd: "abort",\n                args: {},\n                label: "Stop and recover', 'cmd: "stop",\n                args: {},\n                label: "Stop and recover')
s=s.replace('          <p className="task-note">','''          {taskInfo.movement && selectedTask !== 'mission' && <label>Test height above home (m)<input type="number" min={1} max={10} value={height} onChange={e => setHeight(Number(e.target.value))}/></label>}
          {selectedTask.startsWith('delivery_') && <label>QR payload to verify<input value={target} onChange={e => setTarget(e.target.value)} /></label>}
          {['delivery_gps','avoidance_route'].includes(selectedTask) && <label>GPS waypoints (latitude, longitude per line)<textarea value={waypoints} onChange={e => setWaypoints(e.target.value)} /></label>}
          <p className="task-note">''')
s=s.replace('Endpoint: {activeEndpoint}', "Vehicle: {hostState?.profile_id ?? 'None'}")
s=s.replace('                ? "Production mission / FCU"','                ? t?.execution?.control_owner || "Production runtime"')
s=s.replace('text={t?.mission.state || "Unavailable"}', 'text={t?.execution ? `${t.execution.task}: ${t.execution.state} ${t.execution.stage || \'\'}` : t?.mission.state || "Unavailable"}')
s=s.replace('Uses current mission behaviours and configured heights. Readiness and GUIDED mode are required. No browser joystick.', 'Flight tasks use production behaviours and readiness checks. Passive QR and SLAM tasks observe without arming. No browser joystick.')
p.write_text(s)

p=Path('src/aerothon_gcs/tauri_app/src/runtime.ts');s=p.read_text()
a=s.index('export interface ConnectionProfile');b=s.index('\nexport function commandId',a)
s=s[:a]+'''export interface ConnectionProfile {
  id:string; name:string; transport:'tcp'|'udp'|'serial'; host:string; port:number; bind_port:number;
  system_id:number; component_id:number; gateway:string; device:string; baud:number;
  camera_device:string; lidar_port:string; lidar_yaw_deg:number; lidar_mirrored:boolean;
  camera_hfov:number; marker_m:number; rc_config:Record<string,unknown>; slam:boolean;
  hardware_reviewed:boolean; delivery_calibration:string;
}
export interface HostState {profiles:ConnectionProfile[]; profile_id:string|null; runtime:'Stopped'|'Running'; can_disconnect:boolean; can_edit_profiles:boolean;}
export async function api(path:string, data?:unknown):Promise<any> {
  const r=await fetch(path, data === undefined ? undefined : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const body=await r.json(); if(!r.ok) throw new Error(body.error || `Request failed (${r.status})`); return body;
}
'''+s[b:]
a=s.index('export const tasks =');b=s.index('\nexport function endpoint',a)
s=s[:a]+'''export const tasks = [
  {id:'mission',label:'Full mission',movement:true,description:'Complete production workflow: takeoff, detection, delivery, return and disarm.'},
  {id:'slam',label:'SLAM mapping',movement:false,description:'Map using the production lidar while the transmitter controls flight. Enable SLAM in the connection profile.'},
  {id:'qr',label:'QR detection',movement:false,description:'Run production QR detection using the current camera pose. No automatic arming or camera movement.'},
  {id:'banner',label:'Banner alignment',movement:true,description:'Take off and align using the production banner behaviour, then return and land.'},
  {id:'avoidance_manual',label:'Avoidance with transmitter',movement:true,description:'Use configured RC channels as pilot intent through the production obstacle controller.'},
  {id:'avoidance_route',label:'Avoidance with GPS route',movement:true,description:'Follow GPS waypoints through the production obstacle controller, then return and land.'},
  {id:'mechanism',label:'Mechanism only',movement:false,description:'Disarmed bench lower, release, stow or stop. Measured device feedback is required.'},
  {id:'delivery_here',label:'Payload delivery here',movement:true,description:'Take off at the current location, centre on the specified QR and run production delivery.'},
  {id:'delivery_gps',label:'Payload delivery at GPS',movement:true,description:'Fly to one GPS location and height, verify the specified QR and deliver through production behaviours.'},
] as const;
'''+s[b:]
a=s.index('export function defaultProfile');b=s.index('\nexport function age(',a)
s=s[:a]+'''export function defaultProfile(host = ''): ConnectionProfile {
  return {id:'vehicle',name:'Vehicle',transport:'tcp',host,port:5762,bind_port:14555,system_id:1,component_id:1,
    gateway:host ? `http://${host}:8090` : '',device:'/dev/ttyAMA0',baud:115200,camera_device:'/dev/video0',lidar_port:'/dev/ttyUSB0',
    lidar_yaw_deg:0,lidar_mirrored:false,camera_hfov:.851919,marker_m:2.2,rc_config:{},slam:false,hardware_reviewed:false,delivery_calibration:''};
}
export function videoUrl(_value:string, topic:string):string {
  return `/video/stream?topic=${encodeURIComponent(topic)}&type=mjpeg`;
}
'''+s[b:]
a=s.index('export function startAllowed(');b=s.index('\nexport function reviewAllowed(',a)
s=s[:a]+'''export function startAllowed(t:Telemetry|null, connected:boolean, task:string):boolean {
  if(!connected || t?.runtime_health?.fresh !== true || (t.execution && ['Submitted','Accepted','Running'].includes(t.execution.state))) return false;
  if(task === 'qr' || task === 'slam') return t.devices?.[task === 'qr' ? 'camera' : 'lidar']?.ok === true;
  if(!freshFcu(t)) return false;
  if(task === 'mechanism') return t.mission.armed === false && t.devices?.winch_actuator?.ok === true;
  return age(t,'readiness') < 3 && t.safety.ready === true;
}
export function taskCommand(task:string, action:string, params:Record<string,unknown> = {}):{cmd:string;args:Record<string,unknown>} {
  if(!tasks.some(t=>t.id===task)) throw new Error('Unknown production task');
  if(task==='mechanism' && !['lower','release','stow','stop'].includes(action)) throw new Error('Select a mechanism action');
  return {cmd:'start',args:{task,params:task==='mechanism' ? {action} : params}};
}
'''+s[b:]
s=s.replace('["abort", "land"]', '["abort", "land", "stop"]')
s=s.replace('  if (!freshFcu(t)) return false;\n  if (["start_mission"', '  if (cmd === "start") return startAllowed(t, connected, String(args.task));\n  if (!freshFcu(t)) return false;\n  if (["start_mission"')
p.write_text(s)

p=Path('src/aerothon_gcs/tauri_app/src/types.ts');s=p.read_text();s=s.replace('export interface Telemetry {','''export interface Telemetry {
  execution?: {task:string; state:string; stage?:string; control_owner?:string};
  runtime_health?: {fresh:boolean};''')
s=s.replace('    camera?: DeviceMetric;', '    [key:string]: DeviceMetric | undefined;\n    camera?: DeviceMetric;').replace('"ack" | "map"','"ack" | "map" | "execution" | "receipt"')
s=s.replace('  ok: boolean;\n  hz?', '  ok: boolean;\n  reason?:string;\n  hz?')
p.write_text(s)
