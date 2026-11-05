from pathlib import Path
# Historical positive perception fixtures now provide their printed shades,
# exactly as an operator must. Missing-configuration tests remain separate.
names=['test_banner_identity.py','test_banner_capture_contract.py','test_camera_gate.py','test_phase2_arena.py','test_perception_corruption.py','test_provisional_red_entry_20261007.py']
mapping="{'green':'#07A03D','orange':'#EB5A0A','red':'#C4161C'}"
for name in names:
 p=Path('sim')/name;s=p.read_text();lines=[]
 for line in s.splitlines():
  lines.append(line)
  if ' = BannerNode()' in line or '=BannerNode();' in line:
   lhs=line.strip().split('=')[0].strip()
   lines.append(' '*(len(line)-len(line.lstrip()))+f'{lhs}._colours = {mapping}')
  if '= RedZoneNode()' in line:
   lhs=line.strip().split('=')[0].strip()
   indent=' '*(len(line)-len(line.lstrip()))
   lines.append(indent+f'{lhs}._supplied = {mapping}')
   lines.append(indent+f"{lhs}._red_hex = '#C4161C'")
 p.write_text('\n'.join(lines)+'\n')
p=Path('sim/test_gcs_aggregator.py');s=p.read_text()
s=s.replace('{"green": "#07a03d", "orange": "#EB5A0A"}', '{"green": "#07a03d", "orange": "#EB5A0A", "red": "#C4161C"}')
s=s.replace('{"green": "#07A03D", "orange": "#EB5A0A"})','{"green": "#07A03D", "orange": "#EB5A0A", "red": "#C4161C"})')
p.write_text(s)
