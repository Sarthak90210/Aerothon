# Resolve the off-axis chicane outside the navigator's envelope

Status: ready-for-agent
Resolution: geometric infeasibility established; connected planner implemented
Parent: ../spec.md

The fifth return-corridor obstacle in `sim/worlds/my_world_offaxis.json`
leaves 1.21 m past it. The tightest passage offers 0.45 m either side,
below the navigator's 0.70 m half-width requirement. Validation warns it
will stop in front of this chicane.
The watchdog now terminates that stall, but full mission grading still fails.

Investigate a planner improvement against the preserved world before
changing venue geometry or aircraft-clearance requirements. Such changes
need measured venue/airframe data and an explicit design choice.

Acceptance: feasible courses complete with at least 0.70 m clearance in
planning, recovery and independent trajectory grading. The unchanged
off-axis course remains an infeasibility regression when the 0.70 m expanded
polygons block traversal. Its hash and geometry must remain unchanged; a
geometrically blocked course cannot be reported as a traversal pass.
Evidence: `logs/campaign_spec/my_world_offaxis_spec_s1`,
`logs/continue_stall_20261003/my_world_offaxis_spec_s1`.

## Comments

2026-10-03 rendered seed-1 rerun: banner search and alignment recovered,
but return-corridor recovery backed out through the entrance. The mission
reported FAILED at 796.8 simulated seconds, then RTL landed and disarmed.
Full-flight grading remains FAIL, with no obstacle contact. Recorded video
and complete trace: `logs/custom/my_world_offaxis_calm_s1.mp4` and
`logs/custom/my_world_offaxis_calm_s1_full_grade.txt`.

2026-10-05: The original world hash remains
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
