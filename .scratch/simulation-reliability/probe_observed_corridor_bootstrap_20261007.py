"""Scratch handover identification; original certificate and physics retained."""
from pathlib import Path
path=Path(__file__).with_name('check_clock_candidate_coupled_20261007.py')
source=path.read_text()
source=source.replace("out=root/'logs/reliability_clock_candidate_coupled_20261007'",
    "out=root/'logs/reliability_observed_corridor_bootstrap_20261007'")
needle='    case.node._publish=capture\n'
assert source.count(needle)==1
hook='''    import math, numpy as np
    unmodified_publish=original
    bootstrap=dict(origin=None,started=None,first=None,last=None,count=0,ready=False)
    def identified_publish(vx,vy,front,bearing,extra):
        now=case.node._now()
        if bootstrap['origin'] is None and case.node._pos is not None:
            bootstrap['origin']=tuple(case.node._pos);bootstrap['started']=now
        if not bootstrap['ready'] and bootstrap['origin'] is not None and 'fault' not in extra:
            error=np.array(bootstrap['origin'])-np.array(case.node._pos)
            velocity=case.node._fcu_velocity
            stamp=case.node._fcu_velocity_t
            settled=(case.node._velocity_fresh() and velocity is not None and
                     np.linalg.norm(velocity)<=.08 and np.linalg.norm(error)<=.15)
            if not settled:
                bootstrap['first']=bootstrap['last']=None;bootstrap['count']=0
            elif stamp!=bootstrap['last']:
                if bootstrap['first'] is None:bootstrap['first']=stamp
                bootstrap['last']=stamp;bootstrap['count']+=1
            if settled and now-bootstrap['started']>=1. and bootstrap['count']>=3 and stamp-bootstrap['first']>=.3:
                bootstrap['ready']=True
                case.node._progress_ref,case.node._progress_t=case.node._pos,now
            else:
                # Position-error feedback supplies a desired ground velocity,
                # not an invented physical position hold or actuator response.
                desired=.8*error
                desired*=min(1.,.25/max(1e-9,float(np.linalg.norm(desired))))
                c,s=math.cos(case.node._yaw),math.sin(case.node._yaw)
                vx,vy=c*desired[0]+s*desired[1],-s*desired[0]+c*desired[1]
                bearing=0.
                extra=dict(extra,bootstrap='identifying response from fresh observed velocity',
                           bootstrap_age_s=now-bootstrap['started'])
                case.node._progress_ref,case.node._progress_t=case.node._pos,now
        return unmodified_publish(vx,vy,front,bearing,extra)
    original=identified_publish
'''
source=source.replace(needle,hook+needle)
source=source.replace("physical_fixture_changed=False,", "physical_fixture_changed=False,bootstrap_observer=bootstrap,")
exec(compile(source,str(path),'exec'),dict(__file__=str(path),__name__='__main__'))
