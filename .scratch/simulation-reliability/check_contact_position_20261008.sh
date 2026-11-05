#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
/usr/bin/python3 - <<'PY'
from gz.msgs10.contact_pb2 import Contact
c=Contact();p=c.position.add();p.x=1.;p.y=2.;p.z=0.
assert len(c.position)==1 and c.position[0].x==1.
print('Native Contact.position metadata supported')
PY
