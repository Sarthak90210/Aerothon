from pathlib import Path
p=Path('src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py')
s=p.read_text()
s=s.replace("p('drift_filter_s', 0.4)","p('drift_filter_s', 0.15)").replace("p('drift_comp_gain', 0.8)","p('drift_comp_gain', 1.0)").replace("p('max_drift_comp', 0.5)","p('max_drift_comp', 1.0)")
a=s.index('    def _reset_drift(self):')
b=s.index('        sp = PositionTarget()',a)
s=s[:a]+'''    def _reset_drift(self):
        self._drift = 0.0
        self._expect_world = np.zeros(2)
        self._wind_world = np.zeros(2)
        self._ground_world = np.zeros(2)
        self._drift_prev = None
        self._drift_ticks = 0

    def _drift_comp(self, vy):
        # Kept for callers that inspect lateral compensation.
        return self._compensated(0.0,vy)[1]

    def _compensated(self, vx, vy):
        if self._pos is None or self._yaw is None:
            return vx,vy
        dt = 1.0/float(self._g('rate_hz'))
        self._drift_ticks += 1
        if self._drift_prev is None:
            self._drift_prev,self._drift_ticks = self._pos,0
        elif self._pos != self._drift_prev:
            span = self._drift_ticks*dt
            self._ground_world = (np.array(self._pos)-self._drift_prev)/span
            residual = self._ground_world-self._expect_world
            f = min(1.0,span/float(self._g('drift_filter_s')))
            self._wind_world += (residual-self._wind_world)*f
            self._drift_prev,self._drift_ticks = self._pos,0
        c,s = math.cos(self._yaw),math.sin(self._yaw)
        wind = np.array([[c,s],[-s,c]]) @ self._wind_world
        self._drift = float(wind[1])
        compensation = float(self._g('drift_comp_gain'))*wind
        cap = float(self._g('max_drift_comp'))
        compensation *= min(1.0,cap/max(1e-6,float(np.linalg.norm(compensation))))
        return vx-float(compensation[0]),vy-float(compensation[1])

    def _publish(self, vx, vy, front, bearing, extra):
        fresh = 'fault' not in extra and self.state != 'STUCK'
        desired = (vx,vy)
        if fresh:
            vx,vy = self._compensated(vx,vy)
            c,s = math.cos(self._yaw or 0.0),math.sin(self._yaw or 0.0)
            rotation = np.array([[c,s],[-s,c]])
            ground = rotation @ self._ground_world
            wind = rotation @ self._wind_world
            def motion_clear(command):
                # Predict velocity-loop lag from measured ground velocity,
                # followed by braking. Motor compensation is not travel.
                target = np.array(command)+wind
                velocity = ground.copy()
                point = np.zeros(2)
                dt = .05
                tau = float(self._g('vel_response_s'))
                duration = tau+float(np.linalg.norm(target))/float(self._g('braking_accel_mps2'))
                for t in np.arange(0,max(.1,duration),dt):
                    goal = target if t<tau else np.zeros(2)
                    velocity += (goal-velocity)*min(1.0,dt/tau)
                    nxt = point+velocity*dt
                    if not self._planner.segment_clear(point,nxt):
                        return False
                    point = nxt
                return True
            if abs(desired[0])+abs(desired[1])>1e-6 and not motion_clear((vx,vy)):
                # Reduce travel while retaining the disturbance cancellation.
                accepted = False
                for scale in (.75,.5,.25,0.0):
                    candidate = (vx-desired[0]*(1-scale),vy-desired[1]*(1-scale))
                    if motion_clear(candidate):
                        vx,vy = candidate
                        accepted = True
                        break
                if not accepted:
                    vx,vy = vx-desired[0],vy-desired[1]
                extra['recovery_reason'] = 'travel limited by observed braking clearance'
            # Update the actuator model with the command actually published.
            command_world = np.array([[c,-s],[s,c]]) @ np.array([vx,vy])
            dt = 1.0/float(self._g('rate_hz'))
            self._expect_world += (command_world-self._expect_world)*min(1.0,dt/float(self._g('vel_response_s')))
        else:
            vx=vy=0.0
            self._reset_drift()
''' + s[b:]
p.write_text(s)
