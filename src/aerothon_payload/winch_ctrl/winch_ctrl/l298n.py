"""L298N H-bridge payload motor on the Pi's GPIO (no encoder).

The team's bench test (ESP32 + L298N, 24 Oct 2026) drove the motor with
three lines: ENA enables (full speed when high), IN1/IN2 set the direction.

    forward   IN1 high, IN2 low,  ENA on
    reverse   IN1 low,  IN2 high, ENA on
    stop      ENA low,  IN1 low,  IN2 low

The Pi does the same through lgpio. Pins are BCM numbers from the node's
parameters (defaults ENA 18, IN1 23, IN2 24: never GPIO 4/5, the old TELEM3
UART, or 14/15, the FC UART0). `duty_pct` below 100 drives ENA with PWM at
`pwm_hz`; 100 holds it high as the bench test did.

There is no encoder: the line paid out is the node's timed ESTIMATE, not a
measurement.
"""

FORWARD, STOP, REVERSE = 1, 0, -1


class L298NDriver:
    """lgpio-backed L298N. `lg` may be injected for tests."""

    def __init__(self, chip, ena, in1, in2, pwm_hz=1000.0, duty_pct=100.0, lg=None):
        pins = (int(ena), int(in1), int(in2))
        if len(set(pins)) != 3:
            raise ValueError("ENA, IN1 and IN2 must be three different pins")
        reserved = {4, 5, 14, 15}
        if reserved & set(pins):
            raise ValueError(f"GPIO {sorted(reserved & set(pins))} are reserved for FC UARTs")
        if not 0 < float(duty_pct) <= 100:
            raise ValueError("duty must be within 0-100 %")
        if lg is None:
            import lgpio as lg
        self.lg = lg
        self.ena, self.in1, self.in2 = pins
        self.pwm_hz = float(pwm_hz)
        self.duty = float(duty_pct)
        self.h = lg.gpiochip_open(int(chip))
        for pin in pins:
            lg.gpio_claim_output(self.h, pin, 0)
        self.direction = STOP

    def drive(self, direction):
        """FORWARD, REVERSE or STOP. Direction lines change only with ENA off,
        so the bridge never sees both inputs high under drive."""
        lg, h = self.lg, self.h
        self._enable(False)
        lg.gpio_write(h, self.in1, 0)
        lg.gpio_write(h, self.in2, 0)
        if direction == FORWARD:
            lg.gpio_write(h, self.in1, 1)
        elif direction == REVERSE:
            lg.gpio_write(h, self.in2, 1)
        else:
            self.direction = STOP
            return
        self.direction = direction
        self._enable(True)

    def _enable(self, on):
        lg, h = self.lg, self.h
        if on and self.duty < 100:
            lg.tx_pwm(h, self.ena, self.pwm_hz, self.duty)
            return
        if not on and self.duty < 100:
            lg.tx_pwm(h, self.ena, 0, 0)
        lg.gpio_write(h, self.ena, 1 if on else 0)

    def close(self):
        try:
            self.drive(STOP)
        finally:
            for pin in (self.ena, self.in1, self.in2):
                try:
                    self.lg.gpio_free(self.h, pin)
                except Exception:  # noqa: BLE001 - best effort on shutdown
                    pass
            self.lg.gpiochip_close(self.h)
