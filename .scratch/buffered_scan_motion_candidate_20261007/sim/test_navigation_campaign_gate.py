"""A historical pass cannot qualify a changed drone for a broad campaign."""
import hashlib
import json
from pathlib import Path
import pytest
from run_navigation_campaign import verify_targeted_runs


@pytest.fixture
def qualified(tmp_path):
    source = tmp_path/'src/controller.py'
    source.parent.mkdir()
    source.write_text('qualified drone code\n')
    manifest = {'src/controller.py': hashlib.sha256(source.read_bytes()).hexdigest()}
    paths = []
    for seed in (20261003, 1001):
        out = tmp_path/str(seed)
        out.mkdir()
        (out/'summary.json').write_text(json.dumps(dict(acceptance_pass=True,
            motor_delivery_qualified=True, final_armed=False,
            configuration=dict(seed=seed, conditions='calm', world='sim/worlds/my_world.json'))))
        (out/'source_manifest.json').write_text(json.dumps(manifest))
        paths.append(out)
    return tmp_path, paths, source


def test_current_qualified_source_can_start_campaign(qualified):
    root, paths, _ = qualified
    assert verify_targeted_runs(paths, root)['drone_source_files_verified'] == 1


def test_changed_drone_is_rejected_even_with_passing_summaries(qualified):
    root, paths, source = qualified
    source.write_text('changed drone code\n')
    with pytest.raises(ValueError, match='changed since'):
        verify_targeted_runs(paths, root)


def test_duplicate_seed_cannot_satisfy_two_required_trials(qualified):
    root, paths, _ = qualified
    with pytest.raises(ValueError, match='seeds'):
        verify_targeted_runs([paths[0], paths[0]], root)


def test_navigation_only_grade_cannot_qualify_delivery(qualified):
    root, paths, _ = qualified
    summary = json.loads((paths[0]/'summary.json').read_text())
    summary['motor_delivery_qualified'] = False
    (paths[0]/'summary.json').write_text(json.dumps(summary))
    with pytest.raises(ValueError, match='full acceptances'):
        verify_targeted_runs(paths, root)
