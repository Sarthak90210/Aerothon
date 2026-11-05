"""Order the existing camera vantage set from the measured observer position.

The unchanged LegRouter still validates each executed leg against exclusions.
Distance here ranks observations only; it is not a flight-clearance certificate.
"""
import math
from return_banner_vantage_candidate_20261007 import ObservedVantageReturnBanner

def route_length(origin, points):
    return sum(math.dist(a[:2],b[:2]) for a,b in zip([origin]+list(points),points))

def adjacent_observation_order(origin, points):
    if len(points)<3:return list(points)
    # Preserve the original first observation nearest the measured corridor exit.
    remaining=list(enumerate(points[1:],start=1))
    ordered=[points[0]]
    while remaining:
        choice=min(remaining,key=lambda iv:(math.dist(ordered[-1][:2],iv[1][:2]),iv[0]))
        remaining.remove(choice);ordered.append(choice[1])
    # Open-route 2-opt, retaining all coordinates, outward headings and first point.
    for _ in range(len(points)):
        best=route_length(origin,ordered);replacement=None
        for i in range(1,len(ordered)-1):
            for j in range(i+1,len(ordered)):
                candidate=ordered[:i]+ordered[i:j+1][::-1]+ordered[j+1:]
                distance=route_length(origin,candidate)
                if distance<best-1e-9:
                    best=distance;replacement=candidate
        if replacement is None:break
        ordered=replacement
    return ordered if route_length(origin,ordered)<route_length(origin,points)-1e-9 else list(points)

class AdjacentVantageReturnBanner(ObservedVantageReturnBanner):
    def _perimeter_vantages(self):
        points=super()._perimeter_vantages()
        origin=self.mav.pos()[:2]
        ordered=adjacent_observation_order(origin,points)
        self.mav.log(f'FindReturnBanner: {len(points)} existing viewpoints ordered from measured pose; '
                     f'geometric travel {route_length(origin,points):.1f} -> {route_length(origin,ordered):.1f} m; '
                     'every flight leg still requires exclusion-aware routing')
        return ordered
