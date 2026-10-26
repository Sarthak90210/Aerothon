import { useEffect, useState } from 'react';
import type { ConnectionProfile, HostState } from './runtime';
import { defaultProfile, api } from './runtime';

// Choosing the vehicle fills the link it uses; every field stays editable.
function asVehicle(p: ConnectionProfile, vehicle: 'simulation' | 'drone'): ConnectionProfile {
  return vehicle === 'drone'
    ? { ...p, vehicle, transport: 'serial', device: '/dev/ttyAMA0', baud: p.baud || 115200, gateway: '', winch_backend: p.winch_backend ?? 'l298n', autoconnect:true, slam:true, slam_odometry:'lidar' }
    : { ...p, vehicle, transport: 'tcp', port: 5762, hardware_reviewed: false, winch_backend: 'mavlink', autoconnect:false, slam_odometry:'fcu',
        gateway: p.gateway || (p.host ? `http://${p.host}:8090` : '') };
}

export default function Connections({ state, refresh }: { state: HostState | null; refresh: () => Promise<void> }) {
  const [p, setP] = useState<ConnectionProfile>(() => state?.profiles.find(x => x.id === state.profile_id) ?? state?.profiles[0] ?? defaultProfile());
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [rc, setRc] = useState('{}');
  const [log, setLog] = useState('');
  async function loadLog() {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 8000);
    try {
      const text = await (await fetch('/api/logs', {signal: controller.signal})).text();
      setLog(text.split('\n').slice(-80).join('\n') || 'Empty.');
    } catch { setLog('Could not read the runtime log.'); }
    finally { clearTimeout(timer); }
  }
  useEffect(() => { setRc(JSON.stringify(p.rc_config, null, 2)); }, [p.id]);
  const change = (key: string, value: unknown) => setP(old => ({ ...old, [key]: value }));
  const vehicle = p.vehicle ?? (p.transport === 'serial' ? 'drone' : 'simulation');
  const field = (key: keyof ConnectionProfile, label: string, type = 'text') =>
    <label key={key}>{label}<input type={type} value={String(p[key] ?? '')}
      onChange={e => change(key, type === 'number' ? Number(e.target.value) : e.target.value)} /></label>;
  async function run(path: string, data?: unknown) {
    setBusy(true); setMessage('');
    try {
      const result = await api(path, data);
      if (path === '/api/check') setItems(result.items);
      else setMessage(path === '/api/profiles' ? 'Saved.' : 'Accepted. Watch the connection status.');
      await refresh();
    } catch (e) { setMessage(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  return <section className="connections">
    <h2>Connections</h2>
    <p>Runtime: {state?.runtime ?? '—'} · Profile: {state?.profile_id ?? 'none'}</p>
    {state?.connection_error&&<p role="alert">Auto-connect: {state.connection_error}</p>}
    {/* A launch that fails at once used to leave only "Runtime: Stopped". */}
    {state?.runtime === 'Stopped' && state.profile_id && !state.autoconnect_suspended &&
      <p role="alert">Runtime for {state.profile_id} is not running. If Connect was just pressed, it exited: see Runtime log.</p>}
    <fieldset disabled={busy || !state?.can_edit_profiles}>
      <div className="connection-fields">
        <label>Saved profile<select value={p.id} onChange={e => setP(state?.profiles.find(x => x.id === e.target.value) ?? defaultProfile())}>
          <option value="vehicle">New profile</option>{state?.profiles.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}
        </select></label>
        {field('id', 'Profile ID')}{field('name', 'Name')}
        <label>Vehicle<select value={vehicle} onChange={e => setP(old => asVehicle(old, e.target.value as 'simulation' | 'drone'))}>
          <option value="simulation">Laptop simulation</option><option value="drone">Real drone</option>
        </select></label>
        <label>FCU link<select value={p.transport} onChange={e => change('transport', e.target.value)}>
          <option value="tcp">TCP</option><option value="udp">UDP</option><option value="serial">UART</option>
        </select></label>
        {p.transport === 'serial' ? <>{field('device', 'FCU device')}{field('baud', 'Baud', 'number')}
          {field('gcs_host', 'Extra Mission Planner IP (optional)')}</> :
          <>{field('host', 'Host / IP')}{field('port', 'FCU port', 'number')}{p.transport === 'udp' && field('bind_port', 'Pi UDP port', 'number')}</>}
        {field('system_id', 'System ID', 'number')}{field('component_id', 'Component ID', 'number')}
        {vehicle === 'simulation' && field('gateway', 'Sensor gateway URL')}
        {vehicle === 'drone' && <>{field('camera_device', 'Camera device')}{field('lidar_port', 'Lidar device')}
          <label>Winch<select value={p.winch_backend ?? 'mavlink'} onChange={e => change('winch_backend', e.target.value)}>
            <option value="l298n">Pi L298N (RC ch6 by hand)</option><option value="mavlink">FC (DO_WINCH)</option><option value="gpio">Pi GPIO + encoder (needs measured values)</option>
          </select></label>
          <label><input type="checkbox" checked={p.autoconnect !== false} onChange={e => change('autoconnect', e.target.checked)} /> Auto-connect at boot</label></>}
      </div>
      <details><summary>Calibration and RC</summary><div className="connection-fields">
        {field('camera_hfov', 'Camera HFOV (rad)', 'number')}{field('marker_m', 'Launch QR side (m)', 'number')}
        {field('lidar_yaw_deg', 'Lidar yaw (deg)', 'number')}{field('delivery_calibration', 'Delivery calibration file')}
        <label><input type="checkbox" checked={p.lidar_mirrored} onChange={e => change('lidar_mirrored', e.target.checked)} /> Lidar mirrored</label>
        <label><input type="checkbox" checked={p.slam} onChange={e => change('slam', e.target.checked)} /> SLAM mapping</label>
        <label>SLAM pose<select value={p.slam_odometry??(vehicle==='drone'?'lidar':'fcu')} onChange={e=>change('slam_odometry',e.target.value)}>
          <option value="lidar">LiDAR scan matching (no GPS)</option><option value="fcu">FCU odometry</option></select></label>
      </div><label>RC channels (JSON: forward, left, yaw, climb, takeover)<textarea rows={6} value={rc} onChange={e => setRc(e.target.value)} /></label></details>
      <button onClick={() => { try { void run('/api/profiles', { ...p, rc_config: JSON.parse(rc) }); } catch { setMessage('RC mapping must be valid JSON.'); } }}>Save profile</button>
    </fieldset>
    <div className="actions">
      <button disabled={busy || state?.runtime !== 'Stopped' || !state?.profiles.some(x => x.id === p.id)} onClick={() => void run('/api/connect', { profile_id: p.id })}>Connect</button>
      <button disabled={busy} onClick={() => void run('/api/check')}>Check</button>
      {/* After a reboot the last profile stays selected with no runtime; Disconnect
          releases it (the host still refuses while an armed session is unresolved). */}
      <button disabled={busy || (state?.runtime === 'Stopped' && !state?.profile_id) || !state?.can_disconnect}
        title="Pauses auto-connect until restart or Connect"
        onClick={() => void run('/api/disconnect', {})}>Disconnect</button>
    </div>
    {message && <p role="status">{message}</p>}
    <details onToggle={e => { if ((e.target as HTMLDetailsElement).open) void loadLog(); }}>
      <summary>Runtime log</summary>
      <button onClick={() => void loadLog()}>Refresh</button>
      <pre className="runtime-log">{log}</pre>
    </details>
    {items.map(item => <div className="readiness-row" key={String(item.key)}><span>{String(item.key)}</span><span>{item.ok === true ? 'Ready' : 'Unavailable'}</span><span>{String(item.reason ?? '')} {item.key === 'identity' ? `system ${item.value ?? '?'}` : ''} {typeof item.hz === 'number' ? `${item.hz.toFixed(1)} Hz` : ''} {typeof item.vehicle_hz === 'number' ? ` · ${item.vehicle_hz.toFixed(1)} Hz sensor` : ''} {typeof item.capture_age_s === 'number' ? ` · age ${item.capture_age_s.toFixed(3)} s` : ''}</span></div>)}
  </section>;
}
