"""Close the already over-budget simulator acceptance through its abort guard."""
import json
import time
from pathlib import Path
import rclpy
from std_msgs.msg import Bool
from rclpy.node import Node

out = Path('logs/reliability_render_rb_rotated_s20261003_early_red_clipped_bearing_fixture_clock_20261007')
assert json.loads((out/'configuration.json').read_text())['ros_domain'] == 218
with (out/'onboard.jsonl').open() as handle:
    rows = [json.loads(line) for line in handle]
armed = [row for row in rows if row.get('flight', {}).get('data', {}).get('armed')]
assert armed[-1]['stamp']-armed[0]['stamp'] > 900
assert armed[-1]['mission'] in ('RETURN_GATE_SEARCH', 'BANNER_ALIGN')
record = dict(reason='Recorded aircraft remains in return alignment beyond the unchanged 900 s airborne limit',
    command='/mission/abort true', airborne_elapsed_at_intervention_s=armed[-1]['stamp']-armed[0]['stamp'],
    simulated_stamp=armed[-1]['stamp'], wall_epoch=time.time(), acceptance_pass=False,
    source='Operator simulator closure after demonstrated time failure')
with (out/'operator_recovery_20261007.json').open('x') as handle:
    json.dump(record, handle, indent=2)
rclpy.init()
node = Node('close_overbudget_acceptance')
pub = node.create_publisher(Bool, '/mission/abort', 10)
until = time.monotonic()+3
while time.monotonic() < until:
    pub.publish(Bool(data=True))
    rclpy.spin_once(node, timeout_sec=.1)
node.destroy_node()
rclpy.shutdown()
print(json.dumps(record))
