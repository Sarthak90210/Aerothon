import time
from gz.transport13 import Node
n=Node();time.sleep(3)
for topic in n.topic_list():
 if 'vehicle_contacts' in topic or 'clock' in topic:
  print(topic)
