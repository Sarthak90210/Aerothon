#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=224 ROS_LOCALHOST_ONLY=1
out=logs/reliability_recent_reserve_coupled_retry_20261007
[[ ! -e "$out" ]] || exit 2
mkdir "$out"
cp .scratch/simulation-reliability/probe_gust_recent_reserve_20261007.py "$out/runner_source.py"
cp .scratch/simulation-reliability/probe_gust_empirical_profile_reserve_20261007.py "$out/baseline_policy_source.py"
cp .scratch/simulation-reliability/probe_gust_margin.py "$out/physical_probe_source.py"
rc=0
for kind in dirty late; do
    seed=0
    [[ "$kind" != late ]] || seed=1
    /usr/bin/python3 .scratch/simulation-reliability/probe_gust_recent_reserve_20261007.py --kind "$kind" --seed "$seed" --wind default --out "$out/${kind}_gust.json" > "$out/${kind}_gust.log" 2>&1 || rc=1
done
/usr/bin/python3 .scratch/simulation-reliability/probe_gust_recent_reserve_20261007.py --kind dirty --seed 0 --wind calm --out "$out/dirty_calm.json" > "$out/dirty_calm.log" 2>&1 || rc=1
exit "$rc"
