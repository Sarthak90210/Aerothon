import test from 'node:test';
import assert from 'node:assert/strict';
import { fitMetricView, worldAt, zoomMetricView, metricScale, scanBounds, mapScanAvailable } from '../src/slamViewport.ts';
import { gridBounds } from '../src/lidarGeometry.ts';

const grid = { w: 800, h: 120, res: .05, ox: -8, oy: -3, yaw: Math.PI / 2, frame: 'map', stamp: 1, data: [] };

test('fit contains every rotated map corner in a narrow viewport with equal metric axes', () => {
  const size = [340, 430], v = fitMetricView(gridBounds(grid), size);
  for (const [x, y] of [[-8, -3], [-8, 37], [-14, -3], [-14, 37]]) {
    assert.ok(Math.abs(x - v.x) < v.span * size[0] / size[1] / 2);
    assert.ok(Math.abs(y - v.y) < v.span / 2);
  }
});

test('mouse zoom preserves the coordinate under the pointer, including at zoom limits', () => {
  const size = [800, 500], v = { x: 3, y: -7, span: 20 }, point = [127, 391];
  for (const factor of [.001, .8, 1.4, 10000]) {
    const result = zoomMetricView(v, size, factor, ...point);
    const before = worldAt(v, size, ...point), after = worldAt(result, size, ...point);
    assert.ok(before.every((n, i) => Math.abs(n - after[i]) < 1e-9));
    assert.ok(result.span >= .5 && result.span <= 4000);
  }
});

test('Fit scan includes a sideways return beyond the former fixed 16m view on a phone', () => {
  const size = [340, 390], v = fitMetricView(scanBounds([[0, 8], [0, -8]], 12), size);
  assert.ok(v.span * size[0] / size[1] / 2 > 12);
  assert.deepEqual([v.x, v.y], [0, 0]);
});

test('scale stays readable and inside a phone viewport over the whole zoom range', () => {
  for (const width of [270, 340, 900]) for (const span of [.5, 1, 16, 87, 4000]) {
    const scale = metricScale({ x: 0, y: 0, span }, [width, 430]);
    assert.ok(scale.pixels > 20 && scale.pixels <= Math.min(100, width * .22) + 1e-9);
    assert.match(scale.label, /^\d+(\.\d+)? (cm|m)$/);
  }
});

test('fresh lidar cannot paint an apparently live registered scan over a held or old pose', () => {
  const pose = { x: 1, y: 2, yaw: 0 };
  assert.equal(mapScanAvailable(pose, .3, true, 'tracking'), true);
  for (const state of ['held', 'registration_failed', 'waiting', 'degraded', 'reset_required'])
    assert.equal(mapScanAvailable(pose, .3, true, state), false);
  assert.equal(mapScanAvailable(pose, 8, true, 'tracking'), false);
  assert.equal(mapScanAvailable(pose, .3, false, 'tracking'), false);
  assert.equal(mapScanAvailable({ ...pose, yaw: NaN }, .3, true), false);
  assert.equal(mapScanAvailable(null, 0, true), false);
  assert.equal(mapScanAvailable({ ...pose, frame: 'old_map' }, .3, true, 'tracking', 'map'), false);
  assert.equal(mapScanAvailable({ ...pose, frame: 'map' }, .3, true, 'tracking', 'map'), true);
  assert.equal(mapScanAvailable(pose, 3.2, true, 'Held', 'map', false), false);
  assert.equal(mapScanAvailable(pose, .2, true, 'tracking', 'map', false), false);
});
