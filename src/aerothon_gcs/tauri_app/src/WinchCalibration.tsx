import { useEffect, useState } from 'react';
import type { Telemetry } from './types';

type Props = {S:Telemetry|null;connected:boolean;send:(cmd:string,args?:any,danger?:boolean,label?:string)=>void;onClose:()=>void};

export default function WinchCalibration({S,connected,send,onClose}:Props) {
  const w=S?.winch, cal=w?.calibration, limits=w?.limits;
  const disabled=!connected||S?.mission?.armed!==false;
  const active=cal?.active===true;
  const [length,setLength]=useState('');
  const estimate=w?.payout_estimate_m;
  const hand=w?.rc_manual===1||w?.rc_manual===-1?'RC6 driving':w?.rc_manual_ready?'RC6 in the middle':'RC6: put the switch in the middle';
  useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose();};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[onClose]);
  return <div className="dims-overlay" role="dialog" aria-label="Winch limit calibration">
    <div className="card dims lidar calibration-wizard">
      <div className="hd">Winch limits
        <span className={`tag ${active?'ok':''}`}>{active?`Calibrating · ${cal?.remaining_s?.toFixed(0)??'?'} s left`:limits?'Calibrated':'Not calibrated'}</span>
        <button className="dims-close" onClick={onClose} aria-label="Close">×</button></div>
      <p>On the bench, disarmed, props off. The RC6 switch drives the motor; while calibrating, its limits are lifted. No encoder: positions are motor run time.</p>
      <fieldset disabled={disabled} className="calibration-stage">
        <legend>1. Start</legend>
        <button disabled={active} onClick={()=>send('winch_cal',{action:'begin'})}>Start calibration</button>
        <span>{hand} · {w?.state??'no winch status'}</span>
      </fieldset>
      <fieldset disabled={disabled||!active} className="calibration-stage">
        <legend>2. Wound up (minimum)</legend>
        <p>Wind the line in with RC6 to where it should stop, switch to the middle, then mark it.</p>
        <button onClick={()=>send('winch_cal',{action:'set_min'})}>Set wound-up limit here</button>
        <span>{cal?.zeroed?'Marked.':'Pending'}</span>
      </fieldset>
      <fieldset disabled={disabled||!active||!cal?.zeroed} className="calibration-stage">
        <legend>3. Paid out (maximum)</legend>
        <p>Pay the line out with RC6 to where it should stop, switch to the middle, measure the line from the hook's wound-up position, then mark it.</p>
        <div className="calibration-target">
          <strong>Run time {cal?.run_s?.toFixed(1)??'0.0'} s</strong>
          <label>Line out (m)<input type="number" min="1.5" max="20" step="0.01" value={length} onChange={e=>setLength(e.target.value)}/></label>
          <button disabled={!length} onClick={()=>send('winch_cal',{action:'set_max',length_m:Number(length)},true,`Set the winch paid-out limit at ${Number(length)} m`)}>Set paid-out limit here</button>
        </div>
      </fieldset>
      <div className="calibration-stage"><h3>In force</h3>
        {limits?<p role="status">Paid-out limit {limits.max_payout_m.toFixed(2)} m · {limits.stroke_s.toFixed(1)} s of motor run · {limits.line_speed_mps.toFixed(3)} m/s both ways · {limits.source}{limits.saved_at?` · ${limits.saved_at}`:''}</p>
          :<p>No calibration: the limit is {w?.limit_m?.toFixed(2)??'?'} m (max_payout_m) and RC6 hand drive is unlimited.</p>}
        <p>Line out now (estimate): {estimate==null?'unknown':`${estimate.toFixed(2)} m`}.{cal?.reason?` ${cal.reason}`:''}</p>
        <p>Applies to RC6 hand drive, Testing → Mechanism and the mission, which releases from no higher than the line less 0.5 m.</p>
      </div>
      <div className="dims-actions"><span>{disabled?'Connect telemetry and disarm to calibrate.':''}</span>
        <button disabled={!active} onClick={()=>send('winch_cal',{action:'end'})}>Finish</button></div>
    </div>
  </div>;
}
