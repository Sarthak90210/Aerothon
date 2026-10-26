import { useEffect } from 'react';
import type { Telemetry } from './types';

type Props = {S:Telemetry|null;connected:boolean;send:(cmd:string,args?:any,danger?:boolean)=>void;onClose:()=>void};
// camera_ctrl/tilt_calibration.py POSES: what the operator can judge by eye.
const poses = [['FORWARD','Forward (level)'],['ALIGN','45° down'],['NADIR','Straight down']] as const;
const nudges = [-5,-1,1,5];

export default function CameraCalibration({S,connected,send,onClose}:Props) {
  const pose=S?.camera_pose, cal=S?.camera_cal, draft=cal?.draft??{}, applied=cal?.applied;
  const disabled=!connected||S?.mission?.armed!==false;
  const output=pose?.output_deg;
  const complete=poses.every(([key])=>draft[key]!==undefined);
  useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose();};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[onClose]);
  return <div className="dims-overlay" role="dialog" aria-label="Camera tilt calibration">
    <div className="card dims lidar calibration-wizard">
      <div className="hd">Camera tilt calibration
        <span className={`tag ${pose?'ok':''}`}>{output==null?'No camera output':`Output ${output.toFixed(1)}°`}</span>
        <button className="dims-close" onClick={onClose} aria-label="Close">×</button></div>
      <p>Disarmed. Judge the angle on the camera itself, not on the video. The output is the mount pitch sent to the flight controller (−90° to +30°).</p>
      <fieldset disabled={disabled} className="calibration-stage">
        <legend>1. Send a pose</legend>
        <p>Sends where the aircraft thinks each pose is{applied?.points?', through the calibration in force':''}.</p>
        <div className="actions">{poses.map(([key,label])=><button key={key} onClick={()=>send('camera_cal',{action:'pose',pose:key})}>{label}</button>)}</div>
      </fieldset>
      <fieldset disabled={disabled||output==null} className="calibration-stage">
        <legend>2. Adjust until the camera is exactly at a pose</legend>
        <div className="actions">{nudges.map(d=><button key={d} onClick={()=>send('camera_cal',{action:'nudge',delta_deg:d})}>{d>0?`+${d}`:d}°</button>)}</div>
        <span>{output==null?'Send a pose first.':`Output now ${output.toFixed(1)}°`}</span>
      </fieldset>
      <fieldset disabled={disabled||output==null} className="calibration-stage">
        <legend>3. The camera is now at</legend>
        <p>Records the output above for the pose you can see.</p>
        {poses.map(([key,label])=><div className="calibration-target" key={key}>
          <strong>{label}</strong>
          <button onClick={()=>send('camera_cal',{action:'mark',pose:key})}>This is {label.toLowerCase()}</button>
          <span>{draft[key]!==undefined?`Recorded ${draft[key].toFixed(1)}°`:'Pending'}{applied?.points?.[key]!==undefined?` · in force ${applied.points[key].toFixed(1)}°`:''}</span>
        </div>)}
      </fieldset>
      <div className="calibration-stage"><h3>4. Apply</h3>
        <p>All three poses, running one way from straight down to forward. Other angles (banner −20°, ground −35°) follow the straight line through the neighbouring poses.</p>
        {applied&&<p role="status">{applied.points?`In force: forward ${applied.points.FORWARD}°, 45° ${applied.points.ALIGN}°, down ${applied.points.NADIR}°`:'No calibration: output = angle.'} · {applied.source}{applied.reason?` · ${applied.reason}`:''}</p>}
        <p>If a pose is out of reach within −90° to +30°, widen SERVO5_MIN/MAX on the flight controller and calibrate again.</p>
      </div>
      <div className="dims-actions"><span>{disabled?'Connect telemetry and disarm to calibrate.':''}</span>
        <button disabled={disabled} onClick={()=>send('camera_cal',{action:'reset'})}>Reset</button>
        <button disabled={disabled||!applied?.points} onClick={()=>send('camera_cal',{action:'clear'},true)}>Clear saved</button>
        <button className="primary" disabled={disabled||!complete} onClick={()=>send('camera_cal',{action:'apply'},true)}>Apply calibration</button></div>
    </div>
  </div>;
}
