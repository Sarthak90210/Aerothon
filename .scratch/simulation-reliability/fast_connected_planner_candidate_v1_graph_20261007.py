"""Compiled graph search candidate; unchanged observed-space clearance checks."""
import math
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from avoidance.local_planner import LocalPlanner


class FastConnectedPlanner(LocalPlanner):
    def plan(self, axis_bearing=0.):
        self.path=[]
        if not self.segment_clear((0,0),(0,0)):
            self.reason='aircraft lacks required surface clearance'
            return []
        straight=(self.lookahead*math.cos(axis_bearing),self.lookahead*math.sin(axis_bearing))
        if self.segment_clear((0,0),straight):
            self.path,self.reason=[(0,0),straight],'connected lidar path'
            return self.path
        step=self.resolution
        n=int(self.lookahead/step)
        side=2*n+1
        ij=np.indices((side,side)).reshape(2,-1).T-n
        rotation=np.array([[math.cos(axis_bearing),math.sin(axis_bearing)],
                           [-math.sin(axis_bearing),math.cos(axis_bearing)]])
        xy=ij*step @ rotation
        distances=self.distances(xy)
        free=self.known(xy) & (distances>=self.clearance+.025) & (ij[:,0]*step>=-.3)
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
            j=len(raw)-1
            def preserves(j):
                samples=np.linspace(raw[k],raw[j],max(2,int(math.dist(raw[k],raw[j])/.05)+2))
                return self.segment_clear(raw[k],raw[j]) and min(self.distances(samples))>=min(raw_clearance[k:j+1])-.025
            while j>k+1 and not preserves(j):j-=1
            if not self.segment_clear(raw[k],raw[j]):
                self.reason='segment failed continuous clearance check'
                return []
            path.append(raw[j]);k=j
        self.path,self.reason=path,'connected lidar path'
        return path
