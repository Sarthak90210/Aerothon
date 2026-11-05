from pathlib import Path
p=Path('src/aerothon_gcs/tauri_app/tests/runtime.test.mjs');s=p.read_text()
s=s.replace('  safety: { ready: true, fcu_connected: true },','  safety: { ready: true, fcu_connected: true },\n  runtime_health: {fresh:true},')
a=s.index('test("browser tasks map');b=s.index('test("flight starts require',a)
s=s[:a]+'''test("browser tasks use the shared production supervisor registry", () => {
  const source = readFileSync(new URL("../../../aerothon_runtime/aerothon_runtime/contracts.py", import.meta.url),"utf8");
  for(const task of tasks) {
    assert.ok(source.includes(`'${task.id}':`));
    const c=taskCommand(task.id,'stow',{height:5});
    assert.equal(c.cmd,'start'); assert.equal(c.args.task, task.id);
  }
  assert.deepEqual(taskCommand('mechanism','release'), {cmd:'start',args:{task:'mechanism',params:{action:'release'}}});
  assert.throws(()=>taskCommand('manual_joystick','stow'));
  assert.throws(()=>taskCommand('mechanism','unsupported'));
});
'''+s[b:]
s=s.replace('GUIDED and exclusive execution','exclusive execution')
s=s.replace('    t.mission.state = phase;', "    t.execution = {task:'mission',state:'Running',stage:phase};")
s=s.replace('  t.mission.state = "IDLE";\n  t.mission.mode = "AUTO";', '  delete t.execution;\n  t.runtime_health.fresh=false;')
s=s.replace("  t.sample_age_s.winch = .1; t.winch = { state: 'STOWED' };", '  t.devices={winch_actuator:{ok:true}};')
s=s.replace('taskCommand("mechanism", "lower").cmd, "winch"','taskCommand("mechanism", "lower").cmd, "start"')
s=s.replace('"http://192.168.0.100:8080/stream?topic=%2Fpercep%2Foverlay&type=mjpeg"','"/video/stream?topic=%2Fpercep%2Foverlay&type=mjpeg"')
p.write_text(s)
