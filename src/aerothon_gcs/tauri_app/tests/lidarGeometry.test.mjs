import test from 'node:test';
import assert from 'node:assert/strict';
import {scanPoints,gridBounds,decodeGrid,rasterizeGrid,scanInMap} from '../src/lidarGeometry.ts';

test('full C1 scan keeps a narrow obstacle between former decimation bins',()=>{
  const scan={angle_min:0,angle_step:Math.PI/360,ranges:Array(720).fill(3)};
  scan.ranges[13]=.7;
  const points=scanPoints(scan);
  assert.equal(points.length,720);
  assert.ok(Math.abs(Math.hypot(...points[13])-.7)<1e-12);
});
test('scan coordinates preserve nose and left conventions in either scan direction',()=>{
  const p=scanPoints({angle_min:0,angle_step:Math.PI/2,ranges:[1,2]});
  assert.deepEqual(p[0],[1,0]);assert.ok(Math.abs(p[1][0])<1e-12);assert.equal(p[1][1],2);
  assert.equal(scanPoints({angle_min:0,angle_step:-Math.PI/2,ranges:[1,2]})[1][1],-2);
});
test('invalid scan points stay absent without clipping them into fake circles',()=>{
  assert.equal(scanPoints({ranges:[null,NaN,Infinity,-1,0,.1,2,20],range_min:.2,range_max:12}).length,1);
});
test('rotated occupancy grids keep their metric origin, dimensions and aspect ratio',()=>{
  const b=gridBounds({w:200,h:100,res:.05,ox:3,oy:4,yaw:Math.PI/2});
  assert.ok(Math.abs(b.minX-(-2))<1e-12);assert.ok(Math.abs(b.maxX-3)<1e-12);
  assert.ok(Math.abs(b.minY-4)<1e-12);assert.ok(Math.abs(b.maxY-14)<1e-12);
});
test('lossless map runs preserve free, occupied and unknown cells at native resolution',()=>{
  const value={w:4,h:2,res:.05,ox:-1,oy:2,yaw:0,frame:'map',stamp:1,encoding:'rle',rle:[-1,2,0,3,100,3]};
  const grid=decodeGrid(value);
  assert.deepEqual(Array.from(grid.data),[-1,-1,0,0,0,100,100,100]);assert.equal(grid.res,.05);
  assert.throws(()=>decodeGrid({...value,rle:[0,9]}));
  assert.throws(()=>decodeGrid({...value,rle:[0,2]}));
  assert.throws(()=>decodeGrid({...value,rle:[100,-1]}));
});
test('grid pixels flip to image rows and classify free, occupied, uncertain and unknown',()=>{
  const palette={free:[1,1,1],occupied:[2,2,2],unknown:[3,3,3],uncertain:[4,4,4]};
  // Bottom row (row 0 in the map) is free then occupied; top row unknown then uncertain.
  const px=rasterizeGrid({w:2,h:2,res:1,ox:0,oy:0,yaw:0,frame:'map',stamp:0,data:Int8Array.from([0,100,-1,50])},palette);
  const red=v=>v&255;
  assert.deepEqual(Array.from(px,red),[3,4,1,2]);
  assert.equal(px[0]>>>24,255);
});
test('scan points are placed in the map from the SLAM pose, nose along its heading',()=>{
  const [p]=scanInMap([[2,0]],{x:1,y:1,yaw:Math.PI/2});
  assert.ok(Math.abs(p[0]-1)<1e-12);assert.ok(Math.abs(p[1]-3)<1e-12);
  const [q]=scanInMap([[0,1]],{x:0,y:0,yaw:0});
  assert.deepEqual(q,[0,1]);
});
