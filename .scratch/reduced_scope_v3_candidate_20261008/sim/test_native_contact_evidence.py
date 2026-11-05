import json,sys
from pathlib import Path
import pytest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sim'))
from record_vehicle_contacts import sensor_channels
from native_contact_evidence import qualify_vehicle_contacts


@pytest.fixture
def recording(tmp_path):
    sdf=ET.Element('sdf',version='1.9');model=ET.SubElement(sdf,'model',name='aerothon_iris')
    for name in ('base_link','rotor_0','rotor_1','rotor_2','rotor_3','claw_jaw_a','claw_jaw_b'):
        link=ET.SubElement(model,'link',name=name)
        for collider in ('core','arm_0','skid_0','skid_1') if name=='base_link' else ('collider',):
            ET.SubElement(link,'collision',name=collider)
        sensor=ET.SubElement(link,'sensor',name='qualification_vehicle_contact',type='contact')
        contact=ET.SubElement(sensor,'contact')
        for c in link.findall('collision'):ET.SubElement(contact,'collision').text=c.get('name')
    ET.ElementTree(sdf).write(tmp_path/'flight_vehicle.sdf')
    channels=sensor_channels(tmp_path/'flight_vehicle.sdf')
    (tmp_path/'vehicle_contact_ready.json').write_text(json.dumps(dict(channels=channels,all_topics_advertised=True)))
    rows=[dict(kind='heartbeat',stamp=i/2,channels=channels,advertised_topics=[c['topic'] for c in channels]) for i in range(2,11)]
    body=next(c for c in channels if c['link']=='base_link')
    rows.append(dict(kind='contacts',stamp=1.,link='base_link',topic=body['topic'],contacts=[dict(collision1='aerothon_iris::base_link::skid_0',collision2='takeoff_landing_zone::pad::collision',depth=[.001])]))
    poses=[dict(stamp=i/10,x=0,y=0,z=.25 if i<20 or i>=48 else 3.) for i in range(5,56)]
    onboard=[dict(stamp=t,flight=dict(data=dict(armed=t<5))) for t in (2.,3.,4.,5.)]
    return tmp_path,rows,onboard,poses,dict(home_world=[0,0])


def evaluate(recording):
    out,rows,onboard,poses,layout=recording
    (out/'evaluation_vehicle_contacts.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return qualify_vehicle_contacts(out,onboard,poses,layout)


def test_native_ground_canary_and_live_empty_airborne_channels_pass(recording):
    assert evaluate(recording)['contact_free']


@pytest.mark.parametrize('collider',['core','arm_0','skid_1'])
def test_board_contact_overrides_geometry_for_each_body_collider(recording,collider):
    row=dict(recording[1][-1]);row.update(stamp=3.,contacts=[dict(collision1=f'aerothon_iris::base_link::{collider}',collision2='return_banner::board::collision',depth=[.001])])
    recording[1].append(row)
    result=evaluate(recording)
    assert result['valid'] and not result['contact_free']
    assert result['unexpected_contacts'][0]['stamp']==3.


@pytest.mark.parametrize('fault',['missing_publisher','gap','missing_canary','wrong_collider','bad_stamp','late_start'])
def test_incomplete_or_malformed_native_evidence_fails_closed(recording,fault):
    rows=recording[1]
    if fault=='missing_publisher':rows[2]['advertised_topics']=[]
    elif fault=='gap':rows[:]=[rows[0],rows[-2],rows[-1]]
    elif fault=='missing_canary':rows.pop()
    elif fault=='wrong_collider':rows[-1]['contacts'][0]['collision1']='other_aircraft::base_link::skid_0'
    elif fault=='bad_stamp':rows[-1]['stamp']=float('nan')
    elif fault=='late_start':rows[:]=[r for r in rows if r['stamp']>=3.]
    result=evaluate(recording)
    assert not result['valid'] and not result['contact_free']


def test_ground_contact_in_corridor_is_not_normal_home_landing(recording):
    for pose in recording[3]:pose.update(x=8,z=.25)
    result=evaluate(recording)
    assert not result['contact_free']


def test_claw_payload_contact_is_expected_but_core_payload_impact_is_not(recording):
    row=dict(recording[1][-1]);row.update(stamp=3.)
    row['contacts']=[dict(collision1='aerothon_iris::base_link::core',collision2='aerothon_payload::body::body_collision',depth=[.001])]
    recording[1].append(row)
    assert not evaluate(recording)['contact_free']
