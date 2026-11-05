"""Exercise the actual recorder callback and unchanged native contact grader."""
import ast
import copy
import io
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from test_native_contact_evidence import recording, evaluate, deployed_hook

def callback(values,stamp,trace):
    tree=ast.parse((root/'sim/record_delivery.py').read_text())
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    detail=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='detail')
    scope=dict(values=values,now=lambda:stamp,trace=trace,detector_events=io.StringIO(),json=json,time=time)
    exec(compile(ast.Module(body=[detail],type_ignores=[]),'actual_record_delivery_detail','exec'),scope)
    return scope['detail']

def test_winches_are_recorded_at_actual_arrival_before_next_video_tick(recording):
    row=deployed_hook(recording)
    # Recorded V16 times translated by 270.112 s; no physical tolerance changes.
    row['stamp']=3.189
    snapshot=recording[2][1]
    snapshot['winch_capture']['received_stamp']=2.888
    values=copy.deepcopy({k:v for k,v in snapshot.items() if k!='stamp'})
    values['winch']=copy.deepcopy(snapshot['winch_capture']['data'])
    stream=io.StringIO()
    callback(values,3.088,stream)('winch',SimpleNamespace(data=json.dumps(values['winch'])))
    entries=[json.loads(line) for line in stream.getvalue().splitlines()]
    recording[2].extend(entries);recording[2].sort(key=lambda r:r['stamp'])
    result=evaluate(recording)
    assert result['valid'] and result['contact_free'],result
    assert entries[0]['stamp']==entries[0]['winch_capture']['received_stamp']==3.088
