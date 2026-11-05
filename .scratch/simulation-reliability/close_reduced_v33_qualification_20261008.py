"""Accept only the complete reduced scope, preserving all historical failures."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'sim'), str(root/'scripts')]
from campaign_record import source_manifest
from qualification_evidence import recorded_disarm
from recording_metrics import recording_metrics
from run_navigation_campaign import verify_targeted_runs

version = 'v33'
source = root/f'logs/reliability_reduced_scope_{version}_source_20261008'
manifest = json.loads((root/f'.scratch/reduced_scope_{version}_candidate_20261008/source_manifest.json').read_text())
source_manifest.cache_clear()
assert source_manifest(root) == manifest
provenance = json.loads((source/'provenance.json').read_text())
archive = source/'frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == provenance['archive_sha256']
with zipfile.ZipFile(archive) as frozen:
    assert all(hashlib.sha256(frozen.read(name)).hexdigest() == sha for name, sha in manifest.items())
assert json.loads((source/'targeted_closed_review.json').read_text())['pass_navigation']
startup = json.loads((source/'installed_startup_imports.json').read_text())
assert len(startup) == 11
for record in startup.values():
    path = Path(record['file']).resolve()
    name = str(path.relative_to(root)).replace('\\', '/')
    assert record['sha256'] == manifest[name]
offline = json.loads((source/'full_offline_closed_review.json').read_text())
assert offline['all_offline_checks_pass'] and offline['source_unchanged']
assert offline['reduced_scope'] and not offline['original_full_suite_qualified']
scope_path=source/'offline_scope_exclusions.json'
assert hashlib.sha256(scope_path.read_bytes()).hexdigest()==offline['scope_ledger_sha256']
assert offline['deferred_test_count']==5 and offline['empty_photograph_test_count']==3
trials = [('my_world',20261003),('my_world',1001),('shipped',20261003),('rb_rotated',20261003),('split_corridors',20261003)]
rendered = [root/f'logs/reliability_reduced_{version}_render_{world}_s{seed}_20261008' for world,seed in trials]
gate = verify_targeted_runs(rendered, root)

def files_at(directory):
    return {p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            for p in directory.iterdir() if p.is_file()}

native = []
tools_manifest = None
for run in rendered:
    tools = json.loads((run/'qualification_tools_manifest.json').read_text())
    if tools_manifest is None: tools_manifest = tools
    assert tools == tools_manifest
    assert all(hashlib.sha256((root/name).read_bytes()).hexdigest() == sha for name,sha in tools.items())
    rows = [json.loads(line) for line in (run/'onboard.jsonl').read_text().splitlines()]
    disarm = recorded_disarm(rows)
    assert disarm
    native.append(dict(path=str(run.relative_to(root)),summary=json.loads((run/'summary.json').read_text()),
                       grade=json.loads((run/'grade.json').read_text()),connected_disarm=disarm,files=files_at(run)))

campaign = root/f'logs/reliability_reduced_{version}_campaign_20261008'
report = json.loads((campaign/'report.json').read_text())
assert report['source_unchanged'] and report['reduced_scope'] and not report['original_200_case_qualified']
assert (report['requested_trials'],report['executed_trials'],report['excluded_trials'],report['classified_without_flight']) == (120,96,80,24)
assert report['navigation_passes'] == 96 and not report['failures'] and report['injected_command_delay_s'] == 0
assert json.loads((campaign/'source_manifest.json').read_text()) == manifest
classification = json.loads((campaign/'classification.json').read_text())
exclusions = json.loads((campaign/'exclusions.json').read_text())
worlds = {item['world'] for item in classification}
assert len(worlds) == 10 and len(classification) == 10
negative_geometry = [item for item in classification if item['classification'] != 'navigation trial required']
assert {(item['world'],item['classification']) for item in negative_geometry} == {
    ('editor_test.json','invalid fixture'),('my_world_offaxis.json','infeasible at 0.70 m')}
expected_exclusions = {(world,'worst',seed) for world in worlds for seed in range(1,6)} | {
    (world,'random',seed) for world in worlds for seed in (1,2,5)}
assert len(exclusions) == 80 and {(item['world'],item['preset'],item['seed']) for item in exclusions} == expected_exclusions
assert all(item['mean_wind_mps'] > 4. or item['gust_mps'] > 2. for item in exclusions)
cases = json.loads((campaign/'summary.json').read_text())
assert len(cases) == 96 and len({case['run'] for case in cases}) == 96
campaign_evidence = []
landing_quality = []
targeted = json.loads((source/'targeted_closed_review.json').read_text())
targeted_rates = []
for item in targeted['results']:
    run = root/item['path']
    targeted_rates.append(dict(path=item['path'],detector_rates=recording_metrics(run),
        fidelity='object-level detector outputs; no rendered images or camera capture qualification'))
    precision = json.loads((run/'run.json').read_text()).get('result',{}).get('landing_precision','UNKNOWN')
    if not precision.startswith('PRECISE'):
        landing_quality.append(dict(path=item['path'],precision=precision,navigation_pass=True,qualification='targeted navigation only'))
for case in cases:
    run = campaign/case['run']
    cfg = json.loads((run/'configuration.json').read_text())
    assert cfg['navigation_only'] and not cfg['artificial_transport_delay_injected']
    assert cfg['injected_command_delay_s'] == 0 and cfg['vel_response_s'] == .6
    assert cfg['camera_capture_hz'] == 20 and cfg['lidar_scan_hz'] == 10 and cfg['rtf'] == 2
    assert json.loads((run/'source_manifest.json').read_text()) == manifest
    grade = json.loads((run/'navigation_grade.json').read_text())
    assert grade['pass_navigation'] and len(grade['checks']) == 13 and all(grade['checks'].values())
    fixture = json.loads((run/'run.json').read_text())
    assert fixture['contacts'] == [] and fixture['fence_breaches'] == 0
    disarm = recorded_disarm([json.loads(line) for line in (run/'onboard.jsonl').read_text().splitlines()])
    assert disarm
    precision = (fixture.get('result') or {}).get('landing_precision','UNKNOWN')
    if not precision.startswith('PRECISE'):
        landing_quality.append(dict(path=str(run.relative_to(root)),precision=precision,navigation_pass=True,qualification='campaign navigation only'))
    campaign_evidence.append(dict(path=str(run.relative_to(root)),configuration=cfg,grade=grade,
                                  connected_disarm=disarm,detector_rates=recording_metrics(run),
                                  detector_fidelity='object-level detector outputs, not rendered perception',files=files_at(run)))

# No completion marker is written until every source, case and artifact is checked.
review = dict(qualification_complete=True,accepted_source=provenance['archive_sha256'],source_files=len(manifest),
              original_200_case_qualified=False,original_full_offline_suite_qualified=False,offline=offline,offline_scope_exclusions=json.loads(scope_path.read_text()),normal_startup_imports=startup,targeted_gate=gate,rendered=native,
              campaign=report,campaign_evidence=campaign_evidence,files=files_at(campaign),
              targeted_detector_rates=targeted_rates,
              weather_exclusion_details=exclusions,negative_geometry_details=negative_geometry,
              landing_quality_limitations=landing_quality,
              unresolved_excluded=['strong gusts','artificially delayed control'],
              unresolved_cleanup=['post-disarm headless duplicate rcl_shutdown exception; original stderr preserved',
                                  'V16 native contact recorder pybind11 GIL shutdown abort after disarm; original stderr preserved'],
              skipped_real_photograph_tests=dict(count=3,reason='empty QR/banner photograph corpus',path='tests/perception/corpus/',physical_camera_qualified=False),
              negative_geometry_cases=24,weather_exclusions=80)
with (source/'final_reduced_scope_closed_review.json').open('x') as stream:
    json.dump(review,stream,indent=2)
base = root/'.scratch/simulation-reliability'
current = base/'evidence_report_20261007.md'
historical = current.read_text(encoding='utf-8')
with (base/'evidence_report_before_final_v33_20261008.md').open('x',encoding='utf-8') as stream:
    stream.write(historical)
lines = ['# Reduced scope qualification evidence: passed','',
         f'Accepted archive SHA256: `{provenance["archive_sha256"]}` ({len(manifest)} controlled files).',
         'All five targeted navigation cases, the final reduced-scope offline suite, five full rendered acceptances and 96 campaign navigation flights passed on this source.',
         'The original 200-case qualification is not claimed. Strong-gust and artificially delayed-control failures remain unresolved, preserved and excluded.', '',
         '## Offline verification','',f'{offline["pytest_passed"]} tests passed; {offline["pytest_skipped"]} skipped. Python and shell syntax, configuration parsing and the frontend build passed. The complete log and its SHA256 are preserved.', '',
         'Five offline flight tests using mean wind 8 m/s and gust 4 m/s are explicitly skipped under the user-deferred scope. Their original V32 failures remain archived and are not passes. The other three skips are the empty real-photograph QR/banner corpus in `tests/perception/corpus/`. They are not passes; physical camera performance remains unverified.', '',
         '## Targeted navigation','', 'Field seeds 1, 2 and 3 and retained random seeds 3 and 4 passed all 13 navigation checks, with actual disarm and zero contacts/fence breaches. Their closed review includes exact clearances, airborne time, configurations and artifact hashes.', '',
         '## Rendered acceptance','', '| Course | Seed | Checks | Airborne seconds | Corridor metres |', '|---|---:|---:|---:|---:|']
for (world,seed),record in zip(trials,native):
    grade=record['grade'];summary=record['summary']
    clearance=grade.get('measured_corridor_clearance_m',grade.get('corridor_clearance_m'))
    lines.append(f'| {world} | {seed} | {len(grade["checks"])}/{len(grade["checks"])} | {summary["flight_time_s"]} | {clearance} |')
lines += ['', '## Measured detector rates', '',
          '| Course / seed | Camera ledger Hz sim | QR Hz sim / host | Red Hz sim / host | QR / red p95 latency seconds sim |',
          '|---|---:|---:|---:|---:|']
for (world,seed),record in zip(trials,native):
    rates=record['summary']['detector_rates'];qr=rates['search']['qr_timing'];red=rates['search']['red_timing']
    lines.append(f'| {world} / {seed} | {rates["camera"]["capture_hz"]:.4f} | {qr["capture_hz"]:.4f} / {qr["delivered_wall_hz"]:.4f} | {red["capture_hz"]:.4f} / {red["delivered_wall_hz"]:.4f} | {qr["latency_sim_p95_s"]:.4f} / {red["latency_sim_p95_s"]:.4f} |')
lines += ['', 'Rates use distinct captures. Camera ledger rates describe the recorder subscription; exported video keeps its normal 5 Hz sampling. Search QR/red rates and host delivery rates come from the detector-event journal. Exact counts, maximum gaps and processing times remain in each summary.', '']
lines += ['The closed review also contains measured detector-output rates for every targeted and campaign navigation flight. Those object fixtures do not render images; an empty camera ledger is unmeasured, not evidence of a camera rate or physical perception qualification.', '',
          'Every rendered run completed, confirmed motor delivery, passed independent aircraft-contact evidence, preserved camera recordings through actual disarm, and passed both decision-input audits.',
          'Detector rates, configurations, calibration, recordings, telemetry and per-artifact SHA256 values are stored in `final_reduced_scope_closed_review.json` and each run directory.', '',
          '## Reduced campaign','', '120 selected entries: 96 navigation flights passed and 24 existing invalid/infeasible geometry cases were negatively classified. Eighty original weather entries were excluded. Every executed flight used zero added transport delay and normal actuator behaviour. Object fixtures qualify navigation; rendered motor-delivery evidence is supplied by the five acceptance runs.', '',
          '## Preserved failures and unresolved exclusions','',
          historical.split('## Closed evidence and remaining failures',1)[1].split('## Work still required',1)[0]]
lines += ['', '## Source and configuration history', '',
          'Normal startup resolves all 11 checked decision modules to the accepted source. Exact module hashes, the complete source manifest, archive, calibrated delivery profile, nested runtime configuration manifest and qualification-tool hashes are archived.', '',
          'The object LAND model retains estimated horizontal position control, matching the archived ArduPilot source review. The actual physical response, wind and controller timing remain unchanged. The model is not a replacement for the five native aircraft runs.', '',
          'V17 lower-load and V18 targeted failures remain closed with their original grades, disarms, RTL receipts and per-artifact hashes. The complete pre-acceptance report is preserved in `evidence_report_before_final_v33_20261008.md`; all source-specific failures remain available through the evidence index.', '']
lines += ['## Exact reduced campaign and exclusions', '',
          '| Preset | Selected cases | Navigation flights | Negative geometry classifications |',
          '|---|---:|---:|---:|',
          '| calm, seeds 1-5 | 50 | 40 | 10 |',
          '| field, seeds 1-5 | 50 | 40 | 10 |',
          '| random, seeds 3 and 4 | 20 | 16 | 4 |',
          '| Total | 120 | 96 | 24 |', '',
          'Across all ten original worlds, worst seeds 1-5 are excluded (50 cases), as are random seeds 1, 2 and 5 (30 cases). Each concrete weather configuration exceeds mean wind 4 m/s or gust 2 m/s. The full 80-case configuration ledger is preserved in exclusions.json and the closed review.', '',
          'editor_test.json is invalid and my_world_offaxis.json is geometrically infeasible at the unchanged 0.70 m clearance. Each contributes twelve selected negative classifications: calm 1-5, field 1-5 and random 3/4. These 24 cases were not flown and are not navigation passes. Their exact validation and geometric proofs are retained in classification.json. The accepted navigation claim covers the 96 eligible flights on eight valid worlds.', '',
          'Every eligible flight uses normal .6 s actuator response, zero injected transport queue, .20 s computation budget, camera 20 Hz/lidar 10 Hz and RTF2. Earlier artificially delayed-control trials remain separate unresolved failures and do not count toward this campaign.', '',
          '## Remaining limitations', '',
          '* Strong-gust and artificially delayed-control contacts remain unresolved and excluded.',
          '* The 24 invalid/infeasible geometry cases remain negative classifications, never qualified navigation.',
          '* Five strong-gust offline flight tests remain explicitly excluded and unresolved; their original failures are preserved.',
          '* Three empty real-photograph corpus checks remain skipped; physical camera qualification is absent.',
          '* Previously recorded post-disarm cleanup exceptions remain unresolved and archived; actual disarm and recording coverage are separately verified.',
          '* Object fixtures qualify navigation only. Their payload and motor delivery checks remain unmeasured; motor delivery qualification comes from the five native runs.', '']
if landing_quality:
    lines += ['The following navigation passes retained degraded or unknown visual landing quality. Their actual disarm and home-distance checks passed; this does not upgrade their precision label.', '',
              '| Run | Recorded landing precision |', '|---|---|']
    lines += [f'| {item["path"]} | {item["precision"]} |' for item in landing_quality]
    lines += ['']
current.write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
index_path=base/'evidence_index_20261007.json'
index=json.loads(index_path.read_text(encoding='utf-8'))
index.update(accepted_source=provenance['archive_sha256'],qualification_complete=True,campaign_200_qualified=False,active_runs=[])
index['current_continuation'].update(source='V33 accepted for reduced scope',remaining=[])
index['verification']['final_reduced_scope_closed_review']=str((source/'final_reduced_scope_closed_review.json').relative_to(root))
index_path.write_text(json.dumps(index,indent=2),encoding='utf-8')
status=base/'status.md'
status.write_text(f'# Reduced qualification complete: V33\n\nAccepted archive SHA256 {provenance["archive_sha256"]}.\nFive targeted navigation cases, the final complete reduced-scope offline suite, five full rendered\nacceptances and 96 campaign navigation flights passed on this source.\n24 negative geometry classifications and 80 weather exclusions are not passes.\nStrong gusts and artificially delayed control remain unresolved/excluded; the\noriginal 200-case qualification is not claimed.\n\n## Prior checkpoints\n\n'+status.read_text(encoding='utf-8'),encoding='utf-8')
print('Reduced scope verified and report closed; original 200-case qualification not claimed')
