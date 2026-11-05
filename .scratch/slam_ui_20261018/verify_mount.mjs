import fs from 'node:fs';
import assert from 'node:assert/strict';
import {scanInBody,scanMountTransform} from '../../src/aerothon_gcs/tauri_app/src/lidarGeometry.ts';
const cases=JSON.parse(fs.readFileSync(new URL('mount_reference.json',import.meta.url),'utf8'));
let maxError=0;
for(const {mount,point,expected} of cases){
  const [actual]=scanInBody([point],scanMountTransform('lidar_calibrated',mount));
  maxError=Math.max(maxError,Math.hypot(actual[0]-expected[0],actual[1]-expected[1]));
}
assert.ok(maxError<1e-10);
console.log(JSON.stringify({cases:cases.length,maxError_m:maxError}));
