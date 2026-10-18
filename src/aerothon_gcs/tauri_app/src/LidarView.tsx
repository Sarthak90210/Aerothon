import { useEffect, useMemo, useRef, useState } from 'react';
import { gridBounds, rasterizeGrid, scanInMap, scanPoints, type Grid, type GridPalette, type MapPose, type Scan } from './lidarGeometry';
export type { Grid, MapPose } from './lidarGeometry';

// Free space reads as the page, walls as ink, unexplored as a quiet tone.
const PALETTES: Record<'light'|'dark', GridPalette> = {
  light: {free:[250,251,252], occupied:[28,35,43], unknown:[206,212,219], uncertain:[150,160,172]},
  dark: {free:[46,54,64], occupied:[232,238,245], unknown:[25,29,35], uncertain:[112,122,134]},
};
const SCAN = '#14a5c9', AIRCRAFT = '#f39c32';

function gridImage(grid: Grid, theme: 'light'|'dark'): HTMLCanvasElement {
  const off = document.createElement('canvas'); off.width = grid.w; off.height = grid.h;
  const oc = off.getContext('2d')!, pixels = oc.createImageData(grid.w, grid.h);
  new Uint32Array(pixels.data.buffer).set(rasterizeGrid(grid, PALETTES[theme]));
  oc.putImageData(pixels, 0, 0);
  return off;
}

type View = {x:number; y:number; span:number};

/**
 * Metric plot of a SLAM grid (map frame, north-up as published) or of a bare
 * scan (aircraft frame, nose up). The grid is rasterised once per map, not on
 * every telemetry frame: the per-frame rebuild held a browser's main thread
 * long enough for the host to drop the socket. Drawing is coalesced into one
 * animation frame.
 */
export function MetricPlot({scan, grid, fresh=true, pose, trail, theme='light'}: {
  scan?:Scan; grid?:Grid|null; fresh?:boolean; pose?:MapPose|null; trail?:Array<[number,number]>; theme?:string;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [size,setSize] = useState([700,500]);
  const [view,setView] = useState<View>({x:0,y:0,span:12});
  const drag = useRef<{x:number;y:number;vx:number;vy:number}|null>(null);
  // The view follows the growing map until the operator pans or zooms.
  const moved = useRef(false);
  const palette = theme === 'dark' ? 'dark' : 'light';
  const image = useMemo(() => grid ? gridImage(grid, palette) : null, [grid, palette]);
  const bounds = grid ? gridBounds(grid) : null;
  const boundsKey = bounds ? [bounds.minX,bounds.maxX,bounds.minY,bounds.maxY].map(v=>v.toFixed(2)).join() : '';
  const fitted = (): View => {
    if(!bounds) return {x:0,y:0,span:12};
    return {x:(bounds.minX+bounds.maxX)/2, y:(bounds.minY+bounds.maxY)/2,
      span:Math.max(2,bounds.maxY-bounds.minY,(bounds.maxX-bounds.minX)*size[1]/size[0])*1.08};
  };
  const fit = () => { moved.current = false; setView(fitted()); };
  useEffect(()=>{ if(!moved.current) setView(fitted()); },[boundsKey,size[0],size[1]]);
  useEffect(()=>{
    if(!canvas.current)return;
    const observer=new ResizeObserver(entries=>{const r=entries[0].contentRect;if(r.width&&r.height)setSize([r.width,r.height]);});
    observer.observe(canvas.current);return()=>observer.disconnect();
  },[]);
  useEffect(()=>{
    const node=canvas.current;if(!node)return;
    const wheel=(e:WheelEvent)=>{e.preventDefault();moved.current=true;setView(v=>({...v,span:Math.max(.5,Math.min(400,v.span*Math.exp(e.deltaY*.001)))}));};
    node.addEventListener('wheel',wheel,{passive:false});return()=>node.removeEventListener('wheel',wheel);
  },[]);
  const latest = useRef({scan,grid,image,fresh,pose,trail,size,view});
  latest.current = {scan,grid,image,fresh,pose,trail,size,view};
  const frame = useRef(0);
  useEffect(()=>{
    if(frame.current) return;
    frame.current = requestAnimationFrame(()=>{ frame.current = 0; draw(canvas.current, latest.current); });
  },[scan,image,fresh,pose,trail,size,view]);
  useEffect(()=>()=>cancelAnimationFrame(frame.current),[]);
  const zoom = (factor:number) => { moved.current = true; setView(v=>({...v,span:Math.max(.5,Math.min(400,v.span*factor))})); };
  const beams = scan ? scanPoints(scan).length : 0;
  return <div className="metric-plot">
    <div className="plot-tools"><button onClick={fit}>Fit view</button>
      <button aria-label="Zoom in" onClick={()=>zoom(1/1.5)}>+</button>
      <button aria-label="Zoom out" onClick={()=>zoom(1.5)}>−</button>
      <span>Drag to pan · Scroll to zoom{scan&&!grid?` · ${beams} valid / ${scan.ranges.length} beams`:''}</span></div>
    <canvas ref={canvas} aria-label={grid?'SLAM occupancy grid with metric scale':'Live lidar scan, nose up, full resolution'}
      onPointerDown={e=>{e.currentTarget.setPointerCapture(e.pointerId);drag.current={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y};}}
      onPointerMove={e=>{const d=drag.current;if(d){moved.current=true;setView(v=>({...v,x:d.vx-(e.clientX-d.x)*v.span/size[1],y:d.vy+(e.clientY-d.y)*v.span/size[1]}));}}}
      onPointerUp={()=>{drag.current=null;}} onPointerCancel={()=>{drag.current=null;}} />
  </div>;
}

function draw(node: HTMLCanvasElement|null, p: {scan?:Scan; grid?:Grid|null; image:HTMLCanvasElement|null; fresh:boolean;
  pose?:MapPose|null; trail?:Array<[number,number]>; size:number[]; view:View}) {
  const c=node?.getContext('2d');if(!node||!c)return;
  const {scan,grid,image,fresh,pose,trail,view}=p, [w,h]=p.size, dpr=window.devicePixelRatio||1, k=h/view.span;
  if(node.width!==Math.round(w*dpr)||node.height!==Math.round(h*dpr)){node.width=Math.round(w*dpr);node.height=Math.round(h*dpr);}
  c.setTransform(dpr,0,0,dpr,0,0);
  const css=getComputedStyle(node),text=css.getPropertyValue('--text').trim()||'#d8e2ee',muted=css.getPropertyValue('--muted').trim()||'#8995a2';
  c.fillStyle=css.getPropertyValue('--field').trim()||'#101824';c.fillRect(0,0,w,h);
  const xy=(x:number,y:number)=>[w/2+(x-view.x)*k,h/2-(y-view.y)*k];
  const step=10**Math.floor(Math.log10(view.span/7));
  const spacing=view.span/step>15?step*2:step;
  if(grid&&image){
    c.save();c.globalAlpha=fresh?1:.55;c.translate(w/2,h/2);c.scale(k,-k);c.translate(-view.x,-view.y);
    c.translate(grid.ox,grid.oy);c.rotate(grid.yaw||0);c.scale(grid.res,-grid.res);c.imageSmoothingEnabled=false;
    c.drawImage(image,0,-grid.h);c.restore();
  }
  // Metric grid lines over the map, faint enough not to read as walls.
  c.lineWidth=1;c.strokeStyle=grid?'#7f8c9a2e':'#61758b44';c.font='11px system-ui, sans-serif';c.fillStyle=muted;
  for(let x=Math.floor((view.x-w/k/2)/spacing)*spacing;x<view.x+w/k/2;x+=spacing){
    const [sx]=xy(x,0);c.beginPath();c.moveTo(sx,0);c.lineTo(sx,h);c.stroke();
    if(grid&&sx>28&&sx<w-28)c.fillText(`${Number(x.toFixed(2))}`,sx+3,h-8);
  }
  for(let y=Math.floor((view.y-view.span/2)/spacing)*spacing;y<view.y+view.span/2;y+=spacing){
    const [,sy]=xy(0,y);c.beginPath();c.moveTo(0,sy);c.lineTo(w,sy);c.stroke();
    if(grid&&sy>14&&sy<h-24)c.fillText(`${Number(y.toFixed(2))}`,5,sy-4);
  }
  if(grid){
    if(trail&&trail.length>1){
      c.strokeStyle=AIRCRAFT+'99';c.lineWidth=2;c.lineJoin='round';c.beginPath();
      trail.forEach(([x,y],i)=>{const [sx,sy]=xy(x,y);if(i)c.lineTo(sx,sy);else c.moveTo(sx,sy);});c.stroke();
    }
    if(pose){
      c.fillStyle=SCAN;
      scanInMap(scanPoints(scan),pose).forEach(([x,y])=>{const [sx,sy]=xy(x,y);c.fillRect(sx-1.25,sy-1.25,2.5,2.5);});
      aircraft(c,xy(pose.x,pose.y),-pose.yaw);
    }
  } else {
    const [ox,oy]=xy(0,0);
    c.strokeStyle='#8296ae66';
    for(let r=spacing;r<view.span;r+=spacing){
      c.beginPath();c.arc(ox,oy,r*k,0,Math.PI*2);c.stroke();
      if(r*k<h/2-15)c.fillText(`${Number(r.toFixed(2))} m`,ox+5,oy-r*k+12);
    }
    c.fillStyle=fresh?SCAN:'#8995a2';
    scanPoints(scan).forEach(([forward,left])=>{const [x,y]=xy(-left,forward);c.fillRect(x-1.25,y-1.25,2.5,2.5);});
    aircraft(c,[ox,oy],-Math.PI/2);
    c.fillStyle=text;c.fillText('Nose 0°',ox+12,oy-16);c.fillText('Left +90°',ox-85,oy+22);
  }
  // Scale bar bottom right, clear of the axis labels on the left and bottom.
  c.fillStyle=text;c.fillRect(w-16-k,h-30,k,2);c.textAlign='right';c.fillText('1 m',w-16,h-36);c.textAlign='left';
}

/** An arrowhead at a screen point, pointing along a screen angle. */
function aircraft(c: CanvasRenderingContext2D, [x,y]: number[], angle: number) {
  c.save();c.translate(x,y);c.rotate(angle);
  c.beginPath();c.moveTo(13,0);c.lineTo(-8,8);c.lineTo(-3,0);c.lineTo(-8,-8);c.closePath();
  c.fillStyle=AIRCRAFT;c.strokeStyle='#1b1c1d';c.lineWidth=1.5;c.fill();c.stroke();c.restore();
}

const age = (s: number) => s < 10 ? `${s.toFixed(1)} s` : s < 120 ? `${Math.round(s)} s` : `${Math.round(s/60)} min`;

export default function Slam({grid,mapAge,scan,lidarFresh,slamEnabled,status,pose,trail,theme}: {
  grid:Grid|null; mapAge:number|null; scan?:Scan; lidarFresh:boolean;
  slamEnabled:boolean; status?:{state?:string;reason?:string;source?:string};
  pose?:MapPose|null; trail?:Array<[number,number]>; theme?:string;
}) {
  const [mode,setMode]=useState<'map'|'scan'>('map');
  const showMap=mode==='map'&&!!grid;
  // slam_toolbox publishes the map about once a second; a busy Pi can stretch
  // that, so a few seconds is still live. Only a long gap is called stale.
  const mapState = mapAge==null ? 'none' : mapAge < 5 ? 'live' : mapAge < 15 ? 'slow' : 'stale';
  const chip = showMap
    ? {live:['ok',`Map updated ${age(mapAge??0)} ago`],slow:['warn',`Map updated ${age(mapAge??0)} ago`],
       stale:['bad',`Map not updated for ${age(mapAge??0)}`],none:['bad','No map']}[mapState]
    : lidarFresh ? ['ok','Live scan'] : ['bad','Scan stale'];
  return <div className="slam-view">
    <div className="slam-bar">
      <div className="segmented" role="group" aria-label="SLAM display">
        <button aria-pressed={mode==='map'} onClick={()=>setMode('map')}>SLAM map</button>
        <button aria-pressed={mode==='scan'} onClick={()=>setMode('scan')}>Live lidar</button>
      </div>
      <span className={`chip ${chip[0]}`}>{chip[1]}</span>
      {showMap&&<span className={`chip ${pose?'ok':'warn'}`}>{pose?'Aircraft located on map':'No SLAM pose'}</span>}
      {status?.state&&<span className="chip">{status.source||'LiDAR odometry'}: {status.state}{status.reason?` · ${status.reason}`:''}</span>}
    </div>
    {/* One plot per mode: map metres and the nose-up scan frame do not share a view. */}
    <MetricPlot key={showMap?'map':'scan'} scan={scan} grid={showMap?grid:null} fresh={showMap?mapState!=='stale':lidarFresh}
      pose={showMap?pose:null} trail={showMap?trail:undefined} theme={theme}/>
    {showMap&&grid?<p className="view-note">Frame {grid.frame} · {grid.res} m/cell · {grid.w} × {grid.h} cells · origin {grid.ox.toFixed(2)}, {grid.oy.toFixed(2)} m · local map, no GPS required</p>:
      <p className="view-note">{!lidarFresh?'Waiting for live lidar.':!slamEnabled?'SLAM is disabled in this profile. Live scan needs no GPS.':!grid?'Waiting for the first map from slam_toolbox. Full lidar scan shown.':'Full scan in the aircraft frame. No GPS required.'}</p>}
    <div className="slam-legend view-note">
      <span><i className="swatch free"/>Free</span><span><i className="swatch occupied"/>Occupied</span>
      <span><i className="swatch unknown"/>Unexplored</span><span><i className="swatch scan"/>Live scan</span>
      <span><i className="swatch aircraft"/>Aircraft and track</span>
      <span>Local scan matching does not establish GPS position.</span>
    </div>
  </div>;
}
