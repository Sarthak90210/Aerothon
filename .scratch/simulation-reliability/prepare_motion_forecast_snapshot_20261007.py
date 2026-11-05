"""Separate diagnostic snapshot while the qualified candidate stays frozen."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/motion_forecast_candidate_20261007';snapshot.mkdir(exist_ok=False)
base=root/'logs/reliability_corrected_headless_focus_20261007/frozen_source.zip'
qualified=root/'logs/reliability_live_clock_navigation_candidate_fixed_20261007'
for archive_path in (base,qualified/'frozen_source.zip'):
    with zipfile.ZipFile(archive_path) as archive:
        manifest=json.loads(archive.read('source_manifest.json'))
        for name,sha in manifest.items():
            target=(snapshot/name).resolve();assert target.is_relative_to(snapshot.resolve())
            data=archive.read(name);assert hashlib.sha256(data).hexdigest()==sha,name
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
package=snapshot/'src/aerothon_avoidance/avoidance/avoidance'
helper=Path(__file__).with_name('motion_forecast_trace_candidate_20261007.py')
(package/'motion_forecast_trace.py').write_bytes(helper.read_bytes())
controller=package/'velocity_controller.py';source=controller.read_text()
needle='    clock_driver = IndependentRosClock(node)\n'
assert source.count(needle)==1
source=source.replace(needle,needle+
    "    import os\n    from avoidance.motion_forecast_trace import MotionForecastTrace\n"
    "    trace = MotionForecastTrace(node,os.environ['AEROTHON_MOTION_FORECAST_OUT'])\n")
needle='        clock_driver.close()\n';assert source.count(needle)==1
source=source.replace(needle,'        trace.close()\n'+needle);controller.write_text(source)
runner=snapshot/'sim/run_braked_navigation_probe.py';source=runner.read_text()
source=source.replace('reliability_live_clock_navigation_candidate_fixed_20261007','reliability_motion_forecast_navigation_s3_20261007')
source=source.replace("(out/'candidate_provenance.json').write_bytes", "os.environ['AEROTHON_MOTION_FORECAST_OUT']=str(out/'motion_forecasts.json')\n(out/'candidate_provenance.json').write_bytes")
source=source.replace("'calm',1,out,4.,1200.,228", "'calm',3,out,2.,1200.,228")
assert "'calm',3,out,2.,1200.,228" in source
runner.write_text(source)
record=json.loads((qualified/'candidate_provenance.json').read_text())
record.update(scope='Prediction instrumentation only; same controller numerical decisions and physical fixture',
    rendered_qualified=False,production_modified=False)
for p in (controller,runner,package/'motion_forecast_trace.py'):
    record['modified'][str(p.relative_to(snapshot))]=hashlib.sha256(p.read_bytes()).hexdigest()
(snapshot/'candidate_provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(snapshot=str(snapshot),physical_changed=False,controller_decisions_changed=False)))
