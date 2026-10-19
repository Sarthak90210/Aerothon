import math

import numpy as np
import pytest

from mission_bringup.lidar_odometry import ScanOdometry, rotation


def room():
    t = np.linspace(0., 1., 180)
    return np.concatenate((np.c_[-4+9*t, np.full(180,-3.)],
                           np.c_[-4+9*t, np.full(180,4.)],
                           np.c_[np.full(180,-4.), -3+7*t],
                           np.c_[np.full(180,5.), -3+7*t]))


def test_no_gps_scan_matching_recovers_measured_translation_and_rotation():
    engine=ScanOdometry();world=room()
    engine.update(world, 100.)
    actual=np.array([.14,-.08,math.radians(3)])
    current=(world-actual[:2]) @ rotation(actual[2])
    pose,quality=engine.update(current, 100.1)
    np.testing.assert_allclose(pose,actual,atol=.003)
    assert quality['rmse_m'] < .003


def test_stationary_noise_does_not_accumulate_into_a_rotating_map():
    engine=ScanOdometry();world=room();rng=np.random.default_rng(17)
    engine.update(world,100.)
    for i in range(1,21):
        pose,_=engine.update(world+rng.normal(0,.003,world.shape),100+i*.1)
    assert np.linalg.norm(pose[:2]) < .005
    assert abs(pose[2]) < math.radians(.1)


def test_moving_clutter_does_not_drag_the_map():
    engine=ScanOdometry();world=room();rng=np.random.default_rng(18)
    engine.update(world,100.)
    actual=np.array([.12,.04,.02])
    current=(world-actual[:2]) @ rotation(actual[2])
    current=np.concatenate((current,rng.uniform([-3,-2],[4,3],(70,2))))
    pose,_=engine.update(current,100.1)
    np.testing.assert_allclose(pose,actual,atol=.006)


def test_a_single_wall_is_rejected_instead_of_inventing_odometry():
    engine=ScanOdometry()
    with pytest.raises(ValueError,match='constrain'):
        engine.update(np.c_[np.linspace(-5,5,300),np.ones(300)],100.)


def test_capture_gaps_do_not_get_integrated_as_fresh_motion():
    engine=ScanOdometry();engine.update(room(),100.)
    with pytest.raises(ValueError,match='gap'):
        engine.update(room(),102.)


def test_stationary_scene_can_recover_after_a_gap_without_inventing_motion():
    engine=ScanOdometry();engine.update(room(),100.)
    with pytest.raises(ValueError,match='gap'):engine.update(room(),102.)
    pose,_=engine.update(room(),102.1)
    np.testing.assert_allclose(pose,0,atol=1e-8)


def test_a_moved_scene_is_not_accepted_as_stationary_gap_recovery():
    engine=ScanOdometry();engine.update(room(),100.)
    with pytest.raises(ValueError,match='gap'):engine.update(room(),102.)
    with pytest.raises(ValueError,match='revalidated'):
        engine.update(room()-[.2,0.],102.1)


def test_a_noisy_real_sensor_is_held_to_its_own_noise_floor_not_a_simulated_one():
    # RPLIDAR C1 scatter about wall lines is ~20 mm, so a stationary pair
    # misaligns by ~37 mm RMS; a fixed 40 mm gate rejected a third of them.
    engine=ScanOdometry();world=room();rng=np.random.default_rng(19)
    engine.update(world+rng.normal(0,.02,world.shape),100.)
    for i in range(1,31):
        pose,quality=engine.update(world+rng.normal(0,.02,world.shape),100+i*.1)
    assert quality['noise_m'] > .02
    assert np.linalg.norm(pose[:2]) < .03
    assert abs(pose[2]) < math.radians(.5)


def field_scans():
    import base64, json, zlib
    from pathlib import Path
    record=json.loads((Path(__file__).parent/'fixtures/lidar_held_poshold_drift_20261019.json').read_text())
    ranges=np.frombuffer(zlib.decompress(base64.b64decode(record['ranges'])),dtype='<u2')
    ranges=ranges.reshape(-1,record['beams'])/1000.
    assert record['mount_parent']=='base_link' and record['mount_rotation_xyzw']==[0.,0.,0.,1.]
    bearings=record['angle_min']+np.arange(record['beams'])*record['angle_increment']
    for row,stamp in zip(ranges,record['stamps']):
        valid=(row>max(.15,record['range_min']))&(row<min(12.,record['range_max']))
        yield np.c_[np.cos(bearings[valid])*row[valid],np.sin(bearings[valid])*row[valid]]+record['mount_translation'][:2],stamp


def test_real_poshold_drift_resumes_mapping_instead_of_holding_for_the_rest_of_the_flight():
    # Captured on the Pi: the aircraft drifted ~1.4 m forward while pitching
    # +3..-6 degrees; the old mapper held from the drift onwards.
    engine=ScanOdometry();states=[]
    for points,stamp in field_scans():
        try:
            pose,_=engine.update(points,stamp);states.append('T')
        except ValueError:
            states.append('H')
    assert states.count('T') >= 80, ''.join(states)
    assert set(states[-30:])=={'T'}, ''.join(states)
    assert .8 < pose[0] < 2.


def test_held_motion_faster_than_the_scan_matching_bound_is_never_accepted():
    # Every 2.4 m/s step registers, so only the speed bound can hold it.
    engine=ScanOdometry();world=room();engine.update(world,100.)
    for i in range(1,6):
        with pytest.raises(ValueError,match='bound'):
            engine.update(world-[.24*i,0.],100+i*.1)


def test_unmeasured_motion_during_a_long_hold_still_needs_revalidation():
    engine=ScanOdometry();engine.update(room(),100.)
    wall=np.c_[np.linspace(-5,5,300),np.ones(300)]
    for i in range(1,13):
        with pytest.raises(ValueError):
            engine.update(wall,100+i*.1)
    assert engine.uncertainty is None
    with pytest.raises(ValueError):
        engine.update(room()-[.5,0.],101.3)
    with pytest.raises(ValueError):
        engine.update(room()-[.5,0.],101.4)
    pose,_=engine.update(room(),101.5)
    np.testing.assert_allclose(pose,0,atol=1e-8)
