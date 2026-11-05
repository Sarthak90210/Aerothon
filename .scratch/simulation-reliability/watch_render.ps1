param([Parameter(Mandatory=$true)][string]$RunDirectory)
$lines = @(Get-Content -LiteralPath (Join-Path $RunDirectory 'onboard.jsonl') -Tail 3)
$sample = $null
for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    try { $sample = $lines[$i] | ConvertFrom-Json -ErrorAction Stop; break }
    catch { }
}
if ($null -eq $sample) { throw 'No complete onboard row is available' }
$p = $sample.pose.data.pose.position
't={0:F3} phase={1} armed={2} pos=({3:F2},{4:F2},{5:F2}) red={6} exclusions={7} qr={8} matched={9} cap={10}' -f $sample.stamp,$sample.mission,$sample.flight.data.armed,$p.x,$p.y,$p.z,$sample.red_timing.status,@($sample.red_timing.exclusions).Count,$sample.qr_timing.accepted,$sample.qr_timing.matched,$sample.search_timing.speed_cap_mps
if ($sample.avoidance.planner_state) {
    'planner={0} clearance={1} progress={2} recovery={3}' -f $sample.avoidance.planner_state,$sample.avoidance.observed_clearance_m,$sample.avoidance.axis_progress_m,$sample.avoidance.recovery_reason
}
if ($sample.mission -eq 'WINCH_DROP') {
    $o = $sample.observation
    'delivery={0} attempt={1} touchdown={2} detached={3} confirmed={4} payout_estimate={5} effort={6} stable={7} reason={8}' -f $o.state,$o.attempt,$o.touchdown_inferred,$o.detachment_inferred,$o.delivery_confirmed,$o.payout_estimate_m,$o.decision_telemetry.effort,$o.telemetry_stable,$o.reason
}
