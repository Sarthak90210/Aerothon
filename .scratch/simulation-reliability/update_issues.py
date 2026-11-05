from pathlib import Path
p=Path('.scratch/simulation-reliability/issues/03-offaxis-corridor-envelope.md')
s=p.read_text().replace('Resolution: open','Resolution: geometric infeasibility established; connected planner implemented')
s+='''\n2026-10-05: The original world hash remains
`bd842c00f4918857094f6d669910142143903cf5c1385b686c98c011bc2b3537`.
Exact Euclidean Minkowski expansion of walls and obstacle polygons by
0.70 m connects the upper wall to obstacle 5 and then the lower wall.
The unexpanded polygon gaps are 1.21 m and 1.09 m, each below 1.40 m.
This blocks a through path at the requested clearance. Grid maximin results
remain 0.4500 m at 5 cm and 0.4375 m at 2.5 cm.
Evidence: `logs/offaxis_clearance_audit_20261005.json`.
The current acceptance explicitly retains this course as an infeasibility
regression. No traversal pass is claimed and no world geometry was changed.
The new lidar-only connected planner enforces the 0.70 m minimum; recorded
rendered acceptance and broader campaigns remain pending at this update.
'''
p.write_bytes(s.encode())
p=Path('.scratch/simulation-reliability/issues/04-rendered-camera-rate-validation.md')
s=p.read_text()+'''\n2026-10-05: Regrading the saved standard-world track reproduced the entry
into `restricted_red_zone_3` at simulation 214.38 s in SEARCH_QR, with
0.29 m closest clearance. Evidence: `logs/restricted_zone_reproduced_20261005.txt`.
The new production pacing counts distinct capture timestamps, requires
both detectors fresh, includes latency and braking, and waits for speed ACK.
Active segments are checked against changed exclusions from measured pose;
a blocked segment cancels the previously streamed destination. A stalled
heading cannot authorize camera-blind travel. Red ground projection now
requires an aircraft pose near camera capture time.
These changes have focused test evidence. They are not yet a rendered pass.
'''
p.write_bytes(s.encode())
