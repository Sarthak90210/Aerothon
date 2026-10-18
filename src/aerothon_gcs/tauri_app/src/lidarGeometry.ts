export interface Scan {
  ranges: (number | null)[];
  angle_min?: number; angle_step?: number;
  range_min?: number; range_max?: number; frame?: string; stamp?: number;
}
export interface Grid {
  w:number; h:number; res:number; ox:number; oy:number; yaw:number;
  frame:string; stamp:number; data:ArrayLike<number>;
}
export function decodeGrid(value: Grid & {encoding?:string; rle?:number[]}): Grid {
  const count=value.w*value.h;
  if(!Number.isInteger(value.w)||!Number.isInteger(value.h)||value.w<=0||value.h<=0||value.w>1024||value.h>1024)
    throw new Error('Invalid map dimensions');
  if(value.encoding==='rle') {
    if(!Array.isArray(value.rle)||value.rle.length%2)throw new Error('Invalid map run lengths');
    const data=new Int8Array(count);let offset=0;
    for(let i=0;i<value.rle.length;i+=2){
      const cell=value.rle[i],n=value.rle[i+1];
      if(!Number.isInteger(cell)||cell< -1||cell>100||!Number.isInteger(n)||n<=0||offset+n>count)
        throw new Error('Invalid map run lengths');
      data.fill(cell,offset,offset+n);offset+=n;
    }
    if(offset!==count)throw new Error('Incomplete map');
    return {...value,data};
  }
  if(!Array.isArray(value.data)||value.data.length!==count)throw new Error('Incomplete map');
  return value;
}
export function scanPoints(scan?: Scan): Array<[number, number]> {
  if (!scan) return [];
  const a0 = scan.angle_min ?? -Math.PI;
  const da = scan.angle_step ?? 2 * Math.PI / Math.max(1, scan.ranges.length);
  return scan.ranges.flatMap((r, i) => {
    if (r == null || !Number.isFinite(r) || r <= Math.max(0, scan.range_min ?? 0) || r > (scan.range_max ?? Infinity)) return [];
    const a = a0 + i * da;
    return [[r * Math.cos(a), r * Math.sin(a)] as [number, number]];
  });
}
/** Pose of the mapping base in the SLAM map frame (slam_toolbox /pose). */
export interface MapPose { x:number; y:number; yaw:number; }
/** Body-frame scan points (forward, left) placed in the map frame. */
export function scanInMap(points: Array<[number, number]>, pose: MapPose): Array<[number, number]> {
  const c = Math.cos(pose.yaw), s = Math.sin(pose.yaw);
  return points.map(([f, l]) => [pose.x + c*f - s*l, pose.y + s*f + c*l]);
}
export interface GridPalette { free:[number,number,number]; occupied:[number,number,number];
  unknown:[number,number,number]; uncertain:[number,number,number]; }
/**
 * RGBA pixels for an occupancy grid, top row first (image order), packed as
 * little-endian 32-bit words. One pass with no per-cell allocation: the old
 * per-cell array spread cost ~30 ms for a 900 x 700 map and ran at 10 Hz.
 */
export function rasterizeGrid(g: Grid, palette: GridPalette): Uint32Array {
  const pack = ([r, gr, b]: [number,number,number]) => ((255 << 24) | (b << 16) | (gr << 8) | r) >>> 0;
  const free = pack(palette.free), occupied = pack(palette.occupied),
    unknown = pack(palette.unknown), uncertain = pack(palette.uncertain);
  const out = new Uint32Array(g.w * g.h);
  for (let row = 0; row < g.h; row++) {
    const src = row * g.w, dst = (g.h - 1 - row) * g.w;
    for (let col = 0; col < g.w; col++) {
      const v = g.data[src + col];
      out[dst + col] = v < 0 ? unknown : v >= 65 ? occupied : v <= 25 ? free : uncertain;
    }
  }
  return out;
}
export function gridBounds(g: Grid) {
  const c = Math.cos(g.yaw || 0), s = Math.sin(g.yaw || 0);
  const corners = [[0,0],[g.w*g.res,0],[0,g.h*g.res],[g.w*g.res,g.h*g.res]]
    .map(([x,y]) => [g.ox+c*x-s*y,g.oy+s*x+c*y]);
  return { minX:Math.min(...corners.map(p=>p[0])), maxX:Math.max(...corners.map(p=>p[0])),
           minY:Math.min(...corners.map(p=>p[1])), maxY:Math.max(...corners.map(p=>p[1])) };
}
