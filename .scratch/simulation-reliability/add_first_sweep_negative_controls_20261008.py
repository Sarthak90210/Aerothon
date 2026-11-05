"""Reuse the rejected prototype's capture controls for delayed promotion."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=root/'.scratch/simulation-reliability/rejected_v21_test_return_green_lead_latency_20261008.py'
s=source.read_text()
s=s.replace('test_stable_whole_fresh_lead_starts_guarded_orbit_before_repeated_sweep',
            'test_stable_whole_lead_does_not_interrupt_initial_sweep')
s=s.replace("    assert leaf.phase=='transit', 'stable observed lead waits for two complete sweeps'", 
            "    assert leaf.phase=='sweep', 'initial sweep must complete before an orbit'\n    assert leaf._first_sweep_lead is not None\n    leaf.hi=len(leaf.headings)\n    leaf.update()\n    assert leaf.phase=='transit'")
s=s.replace("assert leaf.phase=='sweep' and leaf._orbit is None and leaf._hits==0",
            "assert leaf.phase=='sweep' and leaf._orbit is None and leaf._hits==0\n    assert leaf._first_sweep_lead is None")
s=s.replace("assert leaf.phase=='sweep' and leaf._orbit is None\n",
            "assert leaf.phase=='sweep' and leaf._orbit is None\n    assert leaf._first_sweep_lead is None\n")
(root/'sim/test_return_first_sweep_capture_controls.py').write_text(s,encoding='utf-8',newline='\n')
