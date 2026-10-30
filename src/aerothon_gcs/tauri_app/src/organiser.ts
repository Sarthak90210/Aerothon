// The organisers' six coordinates (venue survey, 30 Oct 2026): two fence
// points behind take-off and the delivery zone's four corners. The fence
// round the whole flying area is the outline of all six; the aircraft
// searches only inside the four corners. Typed without corners, the fence
// box is the judges' polygon as before.
export type LatLon = { lat: number; lon: number };

// Andrew's monotone chain, counter-clockwise in (lon, lat). Convexity
// survives the lat/lon scaling (an affine map), so no projection is needed.
export function convexHull(points: LatLon[]): LatLon[] {
  const pts = [...new Map(points.map((p) => [`${p.lat},${p.lon}`, p])).values()]
    .sort((a, b) => a.lon - b.lon || a.lat - b.lat);
  if (pts.length <= 2) return pts;
  const cross = (o: LatLon, a: LatLon, b: LatLon) =>
    (a.lon - o.lon) * (b.lat - o.lat) - (a.lat - o.lat) * (b.lon - o.lon);
  const half = (list: LatLon[]) => {
    const out: LatLon[] = [];
    for (const p of list) {
      while (out.length >= 2 && cross(out[out.length - 2], out[out.length - 1], p) <= 0)
        out.pop();
      out.push(p);
    }
    out.pop();
    return out;
  };
  return [...half(pts), ...half([...pts].reverse())];
}

// What Apply geofence sends: the outline of the fence points and the zone
// corners when four corners are given, else the fence points as typed.
export function organiserFence(fence: LatLon[], zone: LatLon[]): LatLon[] {
  return zone.length === 4 ? convexHull([...fence, ...zone]) : fence;
}
