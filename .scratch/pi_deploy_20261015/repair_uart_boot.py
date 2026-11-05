"""Restore the preserved pre-UART Pi configuration and re-enable its FC UART."""
import hashlib
import json
from pathlib import Path

target = Path('/boot/firmware/config.txt')
previous = Path('/boot/firmware/config.txt.before-pixhawk-uart')
assert target.stat().st_size == 0, 'Unexpected current boot config: inspect before repair'
text = previous.read_text()
assert len(text) > 1000 and '[all]' in text and 'arm_boost=1' in text
assert 'usb_max_current_enable' not in text, 'Review power overrides separately'
replacement = text.rstrip() + '\n\n[pi5]\n# Flight controller UART on GPIO14/15. serial0 stays the debug console.\ndtoverlay=uart0-pi5\n[all]\n'
staged = target.with_name('config.txt.aerothon-staged')
staged.write_text(replacement)
staged.replace(target)
receipt = dict(original_bytes=0, baseline_sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),
               new_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
               overlay='uart0-pi5', gpio_tx=14, gpio_rx=15, reboot_required=True,
               fcu_parameters_written=False, power_overrides_added=False)
Path('/home/pi5/aerothon-deploy/boot_uart_repair.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt))
