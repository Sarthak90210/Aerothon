"""Compiled graph search candidate; unchanged observed-space clearance checks."""
import math
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from avoidance.local_planner import LocalPlanner


# Clearance the PLANNED route keeps beyond the hard limit when the space
# allows it. A route planned at the limit plus the 2.5 cm sampling reserve
# was flown 0.664 and 0.698 m from return-corridor obstacles against the
# 0.70 m floor: following the route costs a few centimetres. The hard limit
# and every certificate are unchanged; only route choice prefers the reserve,
# and a gap too narrow for it is still flown on the sampling reserve alone.
TRACKING_RESERVE=.10
SAMPLING_RESERVE=.025
# An aircraft at most this far INSIDE the hard clearance is not refused
# outright: the planner reports the way back out (the measured clearance
# gradient) and the controller sidesteps along it. World 'shipped''s return
# slalom leaves a 0.98 m slot against a 2 x 0.45 m requirement, so 4 cm of
# drift put the aircraft 1 cm inside, and every tick read "aircraft lacks
# required surface clearance" until the navigator gave up STUCK
# (shipped_20kmh_r9b). Nothing is flown inside the clearance: the sidestep
# only ever increases it, and every planned segment is still certified.
RECENTRE_SLACK=.03


class FastConnectedPlanner(LocalPlanner):
    def plan(self, axis_bearing=0.):
        self.path=[]
        self.recentre=None
        if not self.segment_clear((0,0),(0,0)):
            self.reason='aircraft lacks required surface clearance'
            self.recentre=self._recentre_direction()
            return []
        straight=(self.lookahead*math.cos(axis_bearing),self.lookahead*math.sin(axis_bearing))
        straight_clear=self.segment_clear((0,0),straight)
        if straight_clear and self._least_clearance((0,0),straight)>=self.clearance+TRACKING_RESERVE:
            self.path,self.reason=[(0,0),straight],'connected lidar path'
            return self.path
        path=self._plan_graph(axis_bearing,TRACKING_RESERVE)
        if path:
            return path
        if straight_clear:
            self.path,self.reason=[(0,0),straight],'connected lidar path'
            return self.path
        path=self._plan_graph(axis_bearing,SAMPLING_RESERVE)
        if path:
            return path
        # A slot narrower than 2 x (clearance + sampling reserve) has no
        # lattice cell inside the reserve band. Search at the hard clearance
        # itself; the shortcut pass still certifies every segment against it.
        return self._plan_graph(axis_bearing,0.)

    def _recentre_direction(self, h=.03):
        """Unit body-frame direction of increasing clearance when the origin
        is within RECENTRE_SLACK inside the hard clearance; else None."""
        here=float(self.distances([(0.,0.)])[0])
        if not (self.clearance-RECENTRE_SLACK <= here < self.clearance):
            return None
        d=self.distances([(h,0.),(-h,0.),(0.,h),(0.,-h)])
        gx,gy=float(d[0]-d[1]),float(d[2]-d[3])
        norm=math.hypot(gx,gy)
        if norm<1e-6:
            return None
        ux,uy=gx/norm,gy/norm
        if float(self.distances([(h*ux,h*uy)])[0])<=here:
            return None
        return ux,uy

    def _least_clearance(self, start, end):
        samples=np.linspace(start,end,max(2,int(math.dist(start,end)/.05)+2))
        return float(self.distances(samples).min())

    def _plan_graph(self, axis_bearing, reserve):
        self.path=[]
        step=self.resolution
        n=int(self.lookahead/step)
        side=2*n+1
        ij=np.indices((side,side)).reshape(2,-1).T-n
        rotation=np.array([[math.cos(axis_bearing),math.sin(axis_bearing)],
                           [-math.sin(axis_bearing),math.cos(axis_bearing)]])
        xy=ij*step @ rotation
        distances=self.distances(xy)
        free=self.known(xy) & (distances>=self.clearance+reserve) & (ij[:,0]*step>=-.3)
        origin=n*side+n
        free[origin]=True
        cost=1.+.10/np.maximum(.05,distances-self.clearance)**2
        ids=np.arange(side*side).reshape(side,side)
        sources=[];targets=[];weights=[]
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            left=ids[max(0,-di):min(side,side-di),max(0,-dj):min(side,side-dj)].ravel()
            right=left+di*side+dj
            legal=free[left] & free[right]
            if di and dj:
                legal &= free[left+di*side] & free[left+dj]
            left,right=left[legal],right[legal]
            sources.append(left);targets.append(right)
            weights.append(step*math.hypot(di,dj)*cost[right])
        bridge=min(self.occupied_radius,float(np.linalg.norm(self.sensor_origin))+2*step)
        bridge_ids=[]
        if np.linalg.norm(self.sensor_origin)>.025 and bridge>.025:
            for index in np.flatnonzero(free & (np.linalg.norm(ij,axis=1)*step<=bridge)):
                if index!=origin and self.segment_clear((0,0),xy[index]):
                    bridge_ids.append(index)
                    sources.append(np.array([origin]));targets.append(np.array([index]))
                    weights.append(np.array([np.linalg.norm(xy[index])*cost[index]]))
        # CSR sums duplicate edges. Each certified origin bridge replaces
        # the equivalent ordinary edge instead of doubling its travel cost.
        if bridge_ids:
            for index in range(8):
                keep=~((sources[index]==origin) & np.isin(targets[index],bridge_ids))
                sources[index]=sources[index][keep]
                targets[index]=targets[index][keep]
                weights[index]=weights[index][keep]
        graph=csr_matrix((np.concatenate(weights),(np.concatenate(sources),np.concatenate(targets))),
                         shape=(side*side,side*side))
        costs,parent=dijkstra(graph,directed=True,indices=origin,return_predecessors=True)
        merit=ij[:,0]*step-.08*step*np.linalg.norm(ij,axis=1)
        merit[~np.isfinite(costs)]=-np.inf
        maximum=merit.max()
        choices=np.flatnonzero(merit==maximum)
        best=choices[np.argmin(costs[choices])]
        if best==origin or maximum<.3:
            self.reason='no connected observed path with required clearance'
            return []
        chain=[int(best)]
        while chain[-1]!=origin:
            previous=int(parent[chain[-1]])
            if previous<0 or len(chain)>side*side:
                raise RuntimeError('Invalid compiled graph predecessor chain')
            chain.append(previous)
        raw=[tuple(xy[index]) for index in reversed(chain)]
        path,k=[raw[0]],0
        raw_clearance=self.distances(raw)
        while k<len(raw)-1:
            # Evaluate the original <=5 cm samples for every possible
            # shortcut in one tree query. Repeated Python/scipy calls during
            # shortening otherwise block the ROS clock and sensor executor.
            endpoints=np.asarray(raw[k+1:])
            vectors=endpoints-np.asarray(raw[k])
            counts=np.maximum(2,(np.linalg.norm(vectors,axis=1)/.05).astype(int)+2)
            starts=np.r_[0,np.cumsum(counts)[:-1]]
            fractions=np.concatenate([np.linspace(0.,1.,count) for count in counts])
            samples=np.asarray(raw[k])+np.repeat(vectors,counts,axis=0)*fractions[:,None]
            nearest=np.minimum.reduceat(self.distances(samples),starts)
            observed=np.logical_and.reduceat(self.known(samples),starts)
            preserved=np.minimum.accumulate(raw_clearance[k:])[1:]
            thresholds=np.maximum(self.clearance+reserve,preserved-.025)
            qualified=np.flatnonzero(observed & (nearest>=thresholds))
            if not len(qualified):
                # A safe origin can be inside the grid's sampling reserve.
                # Keep the normal batch shortcut; when it rejects every
                # option, require the shared continuous certificate instead
                # of declaring that occupied origin unreachable. Retain the
                # same raw-path preservation and unknown-space checks.
                #
                # Giving away clearance from an origin already inside the
                # reserve is what walks a route onto an obstacle corner: the
                # airframe's own response is then left with nothing. Take the
                # longest shortcut that gives away none first, and keep the
                # original allowance only as the last resort that stops such
                # an origin becoming unreachable.
                for give_away in (0.,.025):
                    for index in range(len(endpoints)-1,-1,-1):
                        if (observed[index] and nearest[index]>=preserved[index]-give_away
                                and self.segment_clear(raw[k],raw[k+1+index])):
                            qualified=np.array([index])
                            break
                    if len(qualified):
                        break
            if not len(qualified):
                self.reason='segment failed continuous clearance check'
                return []
            j=k+1+int(qualified[-1])
            path.append(raw[j]);k=j
        self.path,self.reason=path,'connected lidar path'
        return path
