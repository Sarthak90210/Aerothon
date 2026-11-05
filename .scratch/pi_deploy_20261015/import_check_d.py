import importlib
mods = ["perception_qr.qr_appearance", "perception_qr.qr_match", "perception_qr.qr_node",
        "mission_bt.arena_dimensions", "mission_bt.mission_tree", "mission_bt.decode_hover",
        "mission_bt.mav_commander", "gcs_aggregator.readiness", "gcs_aggregator.readiness_node",
        "gcs_aggregator.aggregator", "aerothon_runtime.web", "aerothon_runtime.contracts",
        "aerothon_runtime.execution_node", "aerothon_runtime.remote_devices",
        "winch_ctrl.winch_node", "winch_ctrl.gpio_winch",
        "avoidance.fast_connected_planner_candidate"]
for m in mods:
    importlib.import_module(m)
print("imports ok:", len(mods))
