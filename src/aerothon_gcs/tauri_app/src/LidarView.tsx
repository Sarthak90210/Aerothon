import { useEffect, useMemo, useRef, useState, type PointerEvent } from 'react';
import { gridBounds, rasterizeGrid, scanInBody, scanInMap, scanMountTransform, scanPoints, type Grid, type GridPalette, type MapPose, type MeasuredScanMount, type Scan, type ScanTransform } from './lidarGeometry';
import { fitMetricView, mapScanAvailable, metricScale, scanBounds, usablePose, worldAt, zoomMetricView, type MetricView, type ViewportSize } from './slamViewport';
export type { Grid, MapPose } from './lidarGeometry';

// Occupancy stays neutral. Colour belongs to the aircraft and sensor returns.
const PALETTES: Record<'light' | 'dark', GridPalette> = {
  light: { free: [247, 249, 250], occupied: [44, 57, 69], unknown: [218, 225, 231], uncertain: [145, 159, 172] },
  dark: { free: [49, 63, 77], occupied: [221, 230, 238], unknown: [26, 37, 48], uncertain: [108, 127, 145] },
};
const SCAN = '#089bb4', AIRCRAFT = '#e9a23b';
const age = (s: number) => !Number.isFinite(s) ? 'unknown' : s < 10 ? `${Math.max(0, s).toFixed(1)} s` : s < 120 ? `${Math.round(s)} s` : `${Math.round(s / 60)} min`;
const number = (n: number) => n.toFixed(2).replace(/^-0\.00$/, '0.00');

function Icon({ name }: { name: 'fit' | 'follow' | 'layers' | 'expand' | 'map' | 'scan' }) {
  const paths = {
    fit: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M8 12h8m-4-4v8',
    follow: 'M12 2v4m0 12v4M2 12h4m12 0h4M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z',
    layers: 'm12 3 10 5-10 5L2 8l10-5ZM3 12l9 5 9-5M3 16l9 5 9-5',
    expand: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5',
    map: 'm9 3-7 3v15l7-3 6 3 7-3V3l-7 3-6-3Zm0 0v15m6-12v15',
    scan: 'M12 12V3m0 9 6-6m-6 6h9M3 12a9 9 0 0 0 9 9m-6-9a6 6 0 0 0 6 6m-2-6a2 2 0 1 0 4 0 2 2 0 0 0-4 0Z',
  };
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}

function gridImage(grid: Grid, theme: 'light' | 'dark'): HTMLCanvasElement {
  const off = document.createElement('canvas');
  off.width = grid.w; off.height = grid.h;
  const context = off.getContext('2d')!, pixels = context.createImageData(grid.w, grid.h);
  new Uint32Array(pixels.data.buffer).set(rasterizeGrid(grid, PALETTES[theme]));
  context.putImageData(pixels, 0, 0);
  return off;
}

interface Layers { map: boolean; scan: boolean; trail: boolean; grid: boolean; }
type Gesture = { view: MetricView; centre: [number, number]; distance: number };

/** Rasterise only changed maps; coalesce moving overlays into one animation frame. */
export function MetricPlot({ scan, grid, fresh = true, scanFresh = fresh, poseFresh = fresh, pose, trail, theme = 'light',
  scanRegistered = true, scanTransform, workspace = false, notice }: {
  scan?: Scan; grid?: Grid | null; fresh?: boolean; scanFresh?: boolean; poseFresh?: boolean; pose?: MapPose | null;
  trail?: Array<[number, number]>; theme?: string; scanRegistered?: boolean; scanTransform?: ScanTransform | null; workspace?: boolean;
  notice?: { title: string; detail: string };
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState<ViewportSize>([700, 500]);
  const [view, setView] = useState<MetricView>({ x: 0, y: 0, span: 16 });
  const [camera, setCamera] = useState<'fit' | 'follow' | 'free'>('fit');
  const [layers, setLayers] = useState<Layers>({ map: true, scan: true, trail: true, grid: true });
  const [cursor, setCursor] = useState<[number, number] | null>(null);
  const pointers = useRef(new Map<number, [number, number]>());
  const gesture = useRef<Gesture | null>(null);
  const palette = theme === 'dark' ? 'dark' : 'light';
  const image = useMemo(() => grid ? gridImage(grid, palette) : null, [grid, palette]);
  const points = useMemo(() => scanPoints(scan), [scan]);
  const registeredPoints = useMemo(() => scanTransform ? scanInBody(points, scanTransform) : [], [points, scanTransform]);
  const bounds = useMemo(() => grid ? gridBounds(grid) : scanBounds(points, scan?.range_max), [grid, points, scan?.range_max]);
  const boundsKey = bounds ? [bounds.minX, bounds.maxX, bounds.minY, bounds.maxY].join() : '';
  const located = usablePose(pose, grid?.frame);
  const fit = () => { setCamera('fit'); setView(fitMetricView(bounds, size)); };
  useEffect(() => { if (camera === 'fit') setView(fitMetricView(bounds, size)); }, [boundsKey, size, camera]);
  useEffect(() => {
    if (camera === 'follow' && usablePose(pose, grid?.frame)) setView(v => ({ ...v, x: pose.x, y: pose.y }));
    else if (camera === 'follow') setCamera('free');
  }, [pose?.x, pose?.y, located, camera]);
  useEffect(() => {
    const node = canvas.current;
    if (!node) return;
    const observer = new ResizeObserver(entries => {
      const r = entries[0].contentRect;
      if (r.width && r.height) setSize(old => old[0] === r.width && old[1] === r.height ? old : [r.width, r.height]);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  const interaction = useRef({ view, size });
  interaction.current = { view, size };
  useEffect(() => {
    const node = canvas.current;
    if (!node) return;
    const wheel = (event: WheelEvent) => {
      event.preventDefault(); setCamera('free');
      const r = node.getBoundingClientRect(), current = interaction.current;
      setView(v => zoomMetricView(v, current.size, Math.exp(Math.max(-500, Math.min(500, event.deltaY)) * .0015),
        event.clientX - r.left, event.clientY - r.top));
    };
    node.addEventListener('wheel', wheel, { passive: false });
    return () => node.removeEventListener('wheel', wheel);
  }, []);
  const latest = useRef({ points, registeredPoints, grid, image, fresh, scanFresh, poseFresh, pose, trail, size, view, layers, scanRegistered });
  latest.current = { points, registeredPoints, grid, image, fresh, scanFresh, poseFresh, pose, trail, size, view, layers, scanRegistered };
  const frame = useRef(0);
  useEffect(() => {
    if (!frame.current) frame.current = requestAnimationFrame(() => {
      frame.current = 0; draw(canvas.current, latest.current);
    });
  }, [points, registeredPoints, image, fresh, scanFresh, poseFresh, pose, trail, size, view, layers, scanRegistered]);
  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  const zoom = (factor: number) => { setCamera('free'); setView(v => zoomMetricView(v, size, factor)); };
  const anchorGesture = () => {
    const pts = [...pointers.current.values()];
    gesture.current = !pts.length ? null : {
      view: interaction.current.view,
      centre: pts.length > 1 ? [(pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2] : pts[0],
      distance: pts.length > 1 ? Math.hypot(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]) : 0,
    };
  };
  const localPoint = (event: PointerEvent<HTMLCanvasElement>): [number, number] => {
    const r = event.currentTarget.getBoundingClientRect();
    return [event.clientX - r.left, event.clientY - r.top];
  };
  const movePointer = (event: PointerEvent<HTMLCanvasElement>) => {
    const point = localPoint(event);
    setCursor(worldAt(view, size, ...point));
    if (!pointers.current.has(event.pointerId) || !gesture.current) return;
    pointers.current.set(event.pointerId, point);
    const pts = [...pointers.current.values()], start = gesture.current;
    const centre = pts.length > 1 ? [(pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2] : pts[0];
    const distance = pts.length > 1 ? Math.hypot(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]) : 0;
    const next = distance > 0 && start.distance > 0 ? zoomMetricView(start.view, size, start.distance / distance, ...start.centre) : start.view;
    setCamera('free');
    setView({ ...next, x: next.x - (centre[0] - start.centre[0]) * next.span / size[1],
      y: next.y + (centre[1] - start.centre[1]) * next.span / size[1] });
  };
  const releasePointer = (event: PointerEvent<HTMLCanvasElement>) => { pointers.current.delete(event.pointerId); anchorGesture(); };
  const scale = metricScale(view, size);
  const toggle = (layer: keyof Layers) => setLayers(old => ({ ...old, [layer]: !old[layer] }));
  return <div className="metric-plot">
    <div className="plot-tools">
      <div className="plot-navigation" role="group" aria-label="Map navigation">
        <button onClick={fit} title="Fit the complete map. Resume fitting as it grows."><Icon name="fit" />{grid ? 'Fit map' : 'Fit scan'}</button>
        {workspace && grid && <button disabled={!located} aria-pressed={camera === 'follow'}
          title={located ? 'Keep the aircraft centred with fixed map orientation' : 'Waiting for a SLAM pose'}
          onClick={() => setCamera(old => old === 'follow' ? 'free' : 'follow')}><Icon name="follow" />Follow aircraft</button>}
      </div>
      <div className="plot-zoom" role="group" aria-label="Map zoom">
        <button aria-label="Zoom out" onClick={() => zoom(1.5)}>−</button>
        <button aria-label="Zoom in" onClick={() => zoom(1 / 1.5)}>+</button>
      </div>
    </div>
    <div className="plot-stage">
      <canvas ref={canvas} tabIndex={0} aria-label={grid ? 'SLAM occupancy grid with metric scale' : 'Live lidar scan, nose up, full resolution'}
        aria-describedby={workspace ? 'slam-interaction-help' : undefined}
        onPointerDown={event => { if (event.button !== 0) return; event.currentTarget.setPointerCapture(event.pointerId); pointers.current.set(event.pointerId, localPoint(event)); anchorGesture(); }}
        onPointerMove={movePointer} onPointerUp={releasePointer} onPointerCancel={releasePointer}
        onLostPointerCapture={releasePointer} onPointerLeave={() => setCursor(null)}
        onKeyDown={event => {
          const directions: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] };
          if (directions[event.key]) { event.preventDefault(); setCamera('free'); const [x, y] = directions[event.key]; setView(v => ({ ...v, x: v.x + x * v.span * .1, y: v.y + y * v.span * .1 })); }
          else if (event.key === '+' || event.key === '=') { event.preventDefault(); zoom(1 / 1.5); }
          else if (event.key === '-') { event.preventDefault(); zoom(1.5); }
          else if (event.key.toLowerCase() === 'f') { event.preventDefault(); fit(); }
        }} />
      <div className="plot-frame-label"><span className="plot-frame-dot" />{grid ? grid.frame : 'Aircraft frame'}<span>{grid ? '2D occupancy' : 'Live lidar'}</span></div>
      <div className="plot-orientation" aria-label={grid ? 'Map coordinates, positive Y up and positive X right. No compass alignment.' : 'Aircraft forward up, left to the left.'}>
        <svg viewBox="0 0 58 58" aria-hidden="true"><path d="M17 42V9m0 33h32M12 15l5-6 5 6m21 22 6 5-6 5" /><text x="25" y="16">{grid ? '+Y' : 'F'}</text><text x="37" y="31">{grid ? '+X' : 'R'}</text></svg>
      </div>
      {notice && <div className="plot-notice" role="status"><Icon name="scan" /><strong>{notice.title}</strong><span>{notice.detail}</span></div>}
      {!scanFresh && !grid && !notice && <div className="plot-notice" role="status"><Icon name="scan" /><strong>Waiting for lidar</strong><span>Old returns shown grey.</span></div>}
      <div className="plot-coordinates">{cursor ? `${grid ? 'X' : 'Right'} ${number(cursor[0])}  ${grid ? 'Y' : 'Forward'} ${number(cursor[1])} m` : grid ? 'Local coordinates · metres' : `${points.length} / ${scan?.ranges.length ?? 0} valid returns`}</div>
      <div className="plot-scale" aria-label={`Scale ${scale.label}`}><span>{scale.label}</span><i style={{ width: scale.pixels }} /></div>
    </div>
    {workspace && <div className="plot-layerbar">
      <div className="plot-layers" role="group" aria-label="Visible map layers"><Icon name="layers" />
        {grid && <button aria-pressed={layers.map} onClick={() => toggle('map')}>Occupancy</button>}
        <button aria-pressed={layers.scan} onClick={() => toggle('scan')}><i className="layer-key scan" />Lidar returns</button>
        {grid && <button aria-pressed={layers.trail} onClick={() => toggle('trail')}><i className="layer-key trail" />Track</button>}
        <button aria-pressed={layers.grid} onClick={() => toggle('grid')}>Grid</button>
      </div>
      <span id="slam-interaction-help">Drag · scroll to zoom · F to fit</span>
    </div>}
  </div>;
}

function draw(node: HTMLCanvasElement | null, p: {
  points: Array<[number, number]>; registeredPoints: Array<[number, number]>; grid?: Grid | null; image: HTMLCanvasElement | null; fresh: boolean; scanFresh: boolean; poseFresh: boolean;
  pose?: MapPose | null; trail?: Array<[number, number]>; size: ViewportSize; view: MetricView; layers: Layers; scanRegistered: boolean;
}) {
  const c = node?.getContext('2d');
  if (!node || !c) return;
  const { points, registeredPoints, grid, image, fresh, scanFresh, poseFresh, pose, trail, view, layers, scanRegistered } = p;
  const [w, h] = p.size, dpr = Math.min(window.devicePixelRatio || 1, 2), k = h / view.span;
  if (node.width !== Math.round(w * dpr) || node.height !== Math.round(h * dpr)) { node.width = Math.round(w * dpr); node.height = Math.round(h * dpr); }
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const css = getComputedStyle(node);
  c.fillStyle = css.getPropertyValue('--plot-bg').trim() || '#eaf0f4'; c.fillRect(0, 0, w, h);
  const xy = (x: number, y: number): [number, number] => [w / 2 + (x - view.x) * k, h / 2 - (y - view.y) * k];
  const step = metricScale({ ...view, span: view.span * .8 }, p.size).distance;
  if (grid && image && layers.map) {
    c.save(); c.globalAlpha = fresh ? 1 : .55; c.translate(w / 2, h / 2); c.scale(k, -k); c.translate(-view.x, -view.y);
    c.translate(grid.ox, grid.oy); c.rotate(grid.yaw || 0); c.scale(grid.res, -grid.res); c.imageSmoothingEnabled = false;
    c.drawImage(image, 0, -grid.h); c.restore();
  }
  if (layers.grid) {
    c.lineWidth = 1; c.strokeStyle = css.getPropertyValue('--plot-grid').trim() || '#8a9daf29'; c.beginPath();
    for (let x = Math.ceil((view.x - w / k / 2) / step) * step; x < view.x + w / k / 2; x += step) {
      const [sx] = xy(x, 0); c.moveTo(sx, 0); c.lineTo(sx, h);
    }
    for (let y = Math.ceil((view.y - view.span / 2) / step) * step; y < view.y + view.span / 2; y += step) {
      const [, sy] = xy(0, y); c.moveTo(0, sy); c.lineTo(w, sy);
    }
    c.stroke();
    if (!grid) {
      const [ox, oy] = xy(0, 0);
      c.strokeStyle = css.getPropertyValue('--plot-axis').trim(); c.beginPath();
      for (let r = step; r < view.span; r += step) { c.moveTo(ox + r * k, oy); c.arc(ox, oy, r * k, 0, Math.PI * 2); }
      c.stroke();
    }
  }
  if (grid) {
    if (layers.trail && trail && trail.length > 1) {
      c.save(); c.globalAlpha = fresh ? .8 : .4; c.strokeStyle = AIRCRAFT; c.lineWidth = 2; c.lineJoin = 'round'; c.lineCap = 'round'; c.beginPath();
      trail.forEach(([x, y], i) => { const [sx, sy] = xy(x, y); if (i) c.lineTo(sx, sy); else c.moveTo(sx, sy); }); c.stroke(); c.restore();
    }
    if (usablePose(pose, grid.frame)) {
      if (layers.scan && scanRegistered) drawPoints(c, scanInMap(registeredPoints, pose).map(([x, y]) => xy(x, y)), true);
      aircraft(c, xy(pose.x, pose.y), -pose.yaw, poseFresh);
    }
  } else {
    if (layers.scan) drawPoints(c, points.map(([forward, left]) => xy(-left, forward)), scanFresh);
    aircraft(c, xy(0, 0), -Math.PI / 2, scanFresh);
  }
}

function drawPoints(c: CanvasRenderingContext2D, points: Array<[number, number]>, fresh: boolean) {
  c.fillStyle = fresh ? SCAN : '#8995a2'; c.beginPath();
  points.forEach(([x, y]) => c.rect(x - 1.4, y - 1.4, 2.8, 2.8)); c.fill();
}

function aircraft(c: CanvasRenderingContext2D, [x, y]: [number, number], angle: number, fresh: boolean) {
  c.save(); c.translate(x, y);
  c.fillStyle = fresh ? '#e9a23b25' : '#8995a225'; c.beginPath(); c.arc(0, 0, 21, 0, Math.PI * 2); c.fill();
  c.rotate(angle); c.beginPath(); c.moveTo(13, 0); c.lineTo(-9, 9); c.lineTo(-4, 0); c.lineTo(-9, -9); c.closePath();
  c.fillStyle = fresh ? AIRCRAFT : '#8995a2'; c.strokeStyle = '#24313e'; c.lineWidth = 1.5; c.fill(); c.stroke(); c.restore();
}

export default function Slam({ grid, mapAge, scan, lidarFresh, slamEnabled, status, statusAge = Infinity, pose, poseAge = Infinity, trail, theme, mount }: {
  grid: Grid | null; mapAge: number | null; scan?: Scan; lidarFresh: boolean; slamEnabled: boolean;
  status?: { state?: string; reason?: string; source?: string }; statusAge?: number; pose?: MapPose | null; poseAge?: number;
  trail?: Array<[number, number]>; theme?: string; mount?: MeasuredScanMount | null;
}) {
  const [mode, setMode] = useState<'map' | 'scan'>('map');
  const [expanded, setExpanded] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const update = () => setExpanded(document.fullscreenElement === root.current);
    document.addEventListener('fullscreenchange', update);
    return () => document.removeEventListener('fullscreenchange', update);
  }, []);
  const showMap = mode === 'map' && !!grid, located = usablePose(pose, grid?.frame);
  const mapState = mapAge == null ? 'none' : mapAge < 5 ? 'live' : mapAge < 15 ? 'slow' : 'stale';
  const statusFresh = !status || statusAge < 3;
  const scanTransform = useMemo(() => scanMountTransform(scan?.frame, mount), [scan?.frame, mount]);
  const scanRegistered = !!scanTransform && mapScanAvailable(pose, poseAge, lidarFresh, status?.state, grid?.frame, statusFresh);
  const holding = !!status?.state && /held|lost|fail|wait|degrad|reset|initial/i.test(status.state);
  const mapTone = mapState === 'live' ? 'ok' : mapState === 'stale' ? 'bad' : 'warn';
  const notice = mode === 'map' && !grid ? {
    title: slamEnabled ? 'Waiting for the first map' : 'Mapping off in this profile',
    detail: lidarFresh ? 'Live lidar shown meanwhile.' : 'Check lidar and mapping.',
  } : undefined;
  return <div className="slam-view" ref={root}>
    <div className="slam-heading">
      <div><h2>Local map</h2></div>
      <div className="slam-heading-actions">
        <div className="segmented" role="group" aria-label="SLAM display">
          <button aria-pressed={mode === 'map'} onClick={() => setMode('map')}><Icon name="map" />SLAM map</button>
          <button aria-pressed={mode === 'scan'} onClick={() => setMode('scan')}><Icon name="scan" />Live lidar</button>
        </div>
        {document.fullscreenEnabled && <button className="slam-expand" aria-label={expanded ? 'Exit expanded map' : 'Expand map'} title={expanded ? 'Exit expanded map' : 'Expand map'}
          onClick={() => { void (expanded ? document.exitFullscreen() : root.current?.requestFullscreen())?.catch(() => {}); }}><Icon name="expand" /></button>}
      </div>
    </div>
    <div className="slam-health" aria-label="Mapping and sensor status">
      <span className={`slam-signal ${grid ? mapTone : ''}`}><i />{!grid ? 'No map yet' : mapState === 'stale' ? 'Map stale' : mapState === 'slow' ? 'Map delayed' : 'Map received'}<b>{grid && mapAge != null ? `${age(mapAge)} ago` : ''}</b></span>
      <span className={`slam-signal ${lidarFresh ? 'ok' : 'bad'}`}><i />{lidarFresh ? 'Lidar live' : 'Lidar unavailable'}</span>
      {status?.state && <span className={`slam-signal ${holding || !statusFresh ? 'warn' : ''}`}><i />{status.source === 'fcu' ? 'FCU mapping' : 'Scan matching'}<b>{status.state.replace(/_/g, ' ')}{!statusFresh ? ' · status old' : ''}</b></span>}
    </div>
    <MetricPlot key={showMap ? 'map' : 'scan'} scan={scan} grid={showMap ? grid : null}
      fresh={showMap ? mapState === 'live' : lidarFresh} scanFresh={lidarFresh} poseFresh={poseAge < 5 && !holding && statusFresh}
      pose={showMap && located ? pose : null} trail={showMap && located ? trail : undefined} theme={theme}
      scanRegistered={scanRegistered} scanTransform={scanTransform} workspace notice={notice} />
    {showMap && (holding || !located || !scanRegistered || mapState !== 'live') && <div className="slam-advisory" role="status">
      <span className="slam-advisory-dot" />{holding ? `Mapping ${status?.state?.replace(/_/g, ' ')}. ${status?.reason || 'Check scan overlap.'}` :
        !located ? 'Waiting for a SLAM pose.' :
        !lidarFresh ? 'Lidar unavailable: showing last data.' :
        !statusFresh ? 'Mapping status old: scan overlay hidden.' :
        !scanTransform ? 'Scan overlay needs lidar mounting calibration.' :
        !scanRegistered ? `Pose ${age(poseAge)} old: scan overlay hidden.` :
        `Map ${age(mapAge ?? Infinity)} old. Check mapping and link.`}
    </div>}
    <div className="slam-summary">
      <dl><dt>{showMap ? 'Map extent' : 'Scan returns'}</dt><dd>{showMap && grid ? `${(grid.w * grid.res).toFixed(1)} × ${(grid.h * grid.res).toFixed(1)} m` : `${scanPoints(scan).length} / ${scan?.ranges.length ?? 0}`}</dd></dl>
      <dl><dt>{showMap ? 'Resolution' : 'Display frame'}</dt><dd>{showMap && grid ? `${Number((grid.res * 100).toPrecision(3))} cm / cell` : 'Aircraft · nose up'}</dd></dl>
      <dl className="slam-pose"><dt>{showMap ? 'Position' : 'Range limit'}</dt><dd>{showMap ? located ? `X ${number(pose.x)} · Y ${number(pose.y)} m` : '—' : scan?.range_max ? `${scan.range_max} m` : '—'}</dd></dl>
      {showMap && <dl><dt>Pose age</dt><dd>{located ? age(poseAge) : '—'}</dd></dl>}
    </div>
    <div className="slam-footer"><div className="slam-legend">
      <span><i className="swatch free" />Free</span><span><i className="swatch occupied" />Occupied</span><span><i className="swatch unknown" />Unknown</span>
      <span><i className="swatch aircraft" />Aircraft</span>
    </div><span>Local frame, not GPS-aligned</span></div>
  </div>;
}
