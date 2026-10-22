import type { MapPose } from './lidarGeometry';

export interface MetricView { x: number; y: number; span: number; }
export type ViewportSize = readonly [number, number];

export function fitMetricView(b: { minX: number; maxX: number; minY: number; maxY: number } | null,
  [width, height]: ViewportSize): MetricView {
  if (!b) return { x: 0, y: 0, span: 16 };
  return {
    x: (b.minX + b.maxX) / 2, y: (b.minY + b.maxY) / 2,
    span: Math.max(2, b.maxY - b.minY, (b.maxX - b.minX) * height / width) * 1.18,
  };
}

/** Keep a full-range scan centred on the aircraft, including sideways returns. */
export function scanBounds(points: Array<[number, number]>, rangeMax?: number) {
  const measured = points.reduce((max, [x, y]) => Math.max(max, Math.hypot(x, y)), 0);
  const radius = Math.ceil(Number.isFinite(rangeMax) && rangeMax! > 0 ? rangeMax! : measured);
  return radius > 0 ? { minX: -radius, maxX: radius, minY: -radius, maxY: radius } : null;
}

export function worldAt(view: MetricView, [width, height]: ViewportSize, px: number, py: number): [number, number] {
  return [view.x + (px - width / 2) * view.span / height,
    view.y - (py - height / 2) * view.span / height];
}

/** Keep the world point under the mouse fixed while zooming. */
export function zoomMetricView(view: MetricView, size: ViewportSize, factor: number,
  px = size[0] / 2, py = size[1] / 2): MetricView {
  const span = Math.max(.5, Math.min(4000, view.span * factor));
  const [x, y] = worldAt(view, size, px, py);
  return { x: x + (view.x - x) * span / view.span,
    y: y + (view.y - y) * span / view.span, span };
}

/** A readable 1 / 2 / 5 metric distance that fits on small screens. */
export function metricScale(view: MetricView, [width, height]: ViewportSize) {
  const target = Math.min(100, width * .22) * view.span / height;
  const power = 10 ** Math.floor(Math.log10(target));
  const distance = [5, 2, 1].map(n => n * power).find(n => n <= target) ?? power / 2;
  return { distance, pixels: distance * height / view.span,
    label: distance < 1 ? `${Number((distance * 100).toPrecision(3))} cm` : `${Number(distance.toPrecision(3))} m` };
}

export function usablePose(pose?: MapPose | null, frame?: string): pose is MapPose {
  return !!pose && [pose.x, pose.y, pose.yaw].every(Number.isFinite) &&
    (!frame || !pose.frame || pose.frame === frame);
}

/** Fresh returns must not appear registered to an old or held mapping pose. */
export function mapScanAvailable(pose: MapPose | null | undefined, poseAge: number, scanFresh: boolean, state = '', frame?: string, statusFresh = true) {
  return usablePose(pose, frame) && Number.isFinite(poseAge) && poseAge < 5 && scanFresh && statusFresh &&
    !/held|lost|fail|wait|degrad|reset|initial/i.test(state);
}
