import { useEffect, useState } from 'react';
import type { Telemetry } from './types';
import { MetricPlot } from './LidarView';

type Props = {S:Telemetry|null;connected:boolean;send:(cmd:string,args?:any,danger?:boolean,label?:string)=>void;onClose:()=>void};
const fields = [['x_m','Forward X (m)'],['y_m','Left Y (m)'],['z_m','Up Z (m)'],['roll_deg','Roll (°)'],['pitch_deg','Pitch (°)']];
const targets = [['ahead','Ahead, 0°'],['far','Far ahead, 0°'],['port','Left, +90°'],['starboard','Right, −90° (check)']];

export default function LidarCalibration({S,connected,send,onClose}:Props) {
  const cal=S?.lidar_cal, result=cal?.result, applied=cal?.applied;
  const disabled=!connected||S?.mission?.armed!==false;
  const [geometry,setGeometry]=useState<Record<string,string>>(()=>Object.fromEntries(fields.map(([key])=>[key,cal?.geometry?.[key]?.toString()??''])));
  const [distances,setDistances]=useState<Record<string,string>>({});
  useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose();};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[onClose]);
  return <div className="dims-overlay" role="dialog" aria-label="Lidar calibration">
    <div className="card dims lidar calibration-wizard">
      <div className="hd">Lidar calibration
        <span className={`tag ${cal?.raw_fresh?'ok':''}`}>{cal?.raw_fresh?`${cal.samples??0} raw scans`:'Waiting for scans'}</span>
        <button className="dims-close" onClick={onClose} aria-label="Close">×</button></div>
      <p>Disarmed and still. Matte flat panel ≥ 30 cm wide, centred in the laser plane.</p>
      <fieldset disabled={disabled} className="calibration-stage">
        <legend>1. Mounting geometry</legend>
        <p>From base_link to the lidar optical centre; negative = back, right, down. Level within 3°.</p>
        <div className="connection-fields">{fields.map(([key,label])=><label key={key}>{label}<input type="number" step="0.001" value={geometry[key]} onChange={e=>setGeometry(g=>({...g,[key]:e.target.value}))}/></label>)}</div>
        <button disabled={fields.some(([key])=>geometry[key].trim()==='')} onClick={()=>send('lidar_cal_geometry',Object.fromEntries(fields.map(([key])=>[key,Number(geometry[key])])))}>Record geometry</button>
        <span>{cal?.geometry?'Recorded.':'All five values required.'}</span>
      </fieldset>
      <fieldset disabled={disabled||!cal?.geometry} className="calibration-stage">
        <legend>2. Background</legend>
        <p>Remove the panel, keep people still, wait 2 s.</p>
        <button disabled={!cal?.raw_fresh} onClick={()=>send('lidar_cal_background')}>Capture background</button>
        <span>{cal?.background_ready?'Recorded.':'Needs 15 fresh scans.'}</span>
      </fieldset>
      <fieldset disabled={disabled||!cal?.background_ready} className="calibration-stage">
        <legend>3. Targets</legend>
        <p>Panel face square to each direction; distance from optical centre to face. Hold 2 s. Far ≥ 0.5 m beyond ahead.</p>
        {targets.map(([key,label])=>{
          const capture=cal?.captures?.[key as keyof typeof cal.captures];const detail=cal?.capture_details?.[key];
          return <div className="calibration-target" key={key}>
            <strong>{label}</strong><label>Distance (m)<input type="number" min="0.4" max="4" step="0.001" value={distances[key]??''} onChange={e=>setDistances(d=>({...d,[key]:e.target.value}))}/></label>
            <button disabled={!distances[key]||!cal?.raw_fresh} onClick={()=>send('lidar_cal_capture',{where:key,distance_m:Number(distances[key])})}>Capture {key}</button>
            <span>{capture?`${capture[0].toFixed(2)}° raw, ${capture[1].toFixed(3)} m`:'Pending'}{detail?` · ${detail.samples} scans, ${detail.beams} beams · spread ${(1000*detail.spread_m).toFixed(1)} mm`:''}</span>
          </div>;
        })}
      </fieldset>
      <div className="calibration-preview"><h3>Raw scan</h3><MetricPlot scan={cal?.scan} fresh={cal?.raw_fresh}/></div>
      <div className="calibration-stage"><h3>4. Checks</h3>
        {result?<p role="status">{result.ok?`Passed. Yaw ${result.yaw_deg.toFixed(3)}°, ${result.mirrored?'mirrored':'counter-clockwise'} · direction error ${result.error_deg}° · range error ${((result.validation_error_m??0)*1000).toFixed(1)} mm · scale ${result.range_scale?.toFixed(5)}, bias ${((result.range_bias_m??0)*1000).toFixed(1)} mm`:result.reason}</p>:<p>Needs all four captures (≥ 5 returns in 15 scans each). Pass: within 2° and 30 mm.</p>}
        <p>After applying, reconnect the runtime to start a new map.</p>
        {applied&&<p>Applied yaw {applied.yaw_deg}°, {applied.mirrored?'mirrored':'counter-clockwise'} · {applied.geometry_measured?'full geometry':'legacy yaw only, position unmeasured'} · {applied.source}{applied.reason?` · ${applied.reason}`:''}</p>}
      </div>
      <div className="dims-actions"><span>{disabled?'Connect telemetry and disarm to calibrate.':''}</span>
        <button disabled={disabled} onClick={()=>send('lidar_cal_reset')}>Reset</button>
        <button className="primary" disabled={disabled||!result?.ok} onClick={()=>send('lidar_cal_apply',{},true,'Apply lidar calibration')}>Apply calibration</button></div>
    </div>
  </div>;
}
