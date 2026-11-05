from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=(root/'.scratch/simulation-reliability/prepare_v34_gate_replay_20261008.py').read_text().replace('792.31','804.81').replace('gate_v34_replay_fixture','brake_v34_replay_fixture').replace('gate_v34_replay_trace','brake_v34_replay_trace').replace('test_v34_gate_physics_seam','test_v34_brake_physics_seam')
exec(compile(source,__file__,'exec'))
p=root/'.scratch/simulation-reliability/test_v34_brake_physics_seam_20261008.py'
source=p.read_text().replace("minimum=float('inf')", "leaf._phase='BRAKE';leaf._brake_hold=(15.701924400676067,-15.18325590426256,f['flight_alt']);leaf._brake_yaw=w.yaw;w.speed_cap=.35\n    minimum=float('inf')")
p.write_text(source)
