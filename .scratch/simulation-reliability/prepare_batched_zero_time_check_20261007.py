"""Compare identical fixture timing while retaining the rejected initial result."""
from pathlib import Path
here=Path(__file__).parent
source=(here/'check_batched_certificate_20261007.py').read_text()
source=source.replace('reliability_batched_certificate_equivalence_20261007','reliability_batched_certificate_zero_time_20261007')
anchor="install(VelocityController,out/'source_override')"
assert source.count(anchor)==1
source=source.replace(anchor,'''original_initialize=VelocityController.__init__
def initialize(node,*a,**kw):
    original_initialize(node,*a,**kw)
    from rclpy.parameter import Parameter
    node.set_parameters([Parameter('motion_computation_budget_s',value=0.)])
VelocityController.__init__=initialize
'''+anchor)
(here/'check_batched_certificate_zero_time_20261007.py').write_bytes(source.encode())
