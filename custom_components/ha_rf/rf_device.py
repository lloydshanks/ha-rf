"""RF device module for 433/315MHz communication.

Embedded version of rpi-rf for sending and receiving 433/315Mhz signals
with low-cost GPIO RF Modules on a Raspberry Pi.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import namedtuple

try:
    import rpi_lgpio.GPIO as GPIO
except ImportError:
    raise ImportError(
        "rpi-lgpio is required but not available. Install with: pip install rpi-lgpio"
    )

MAX_CHANGES = 67
MIN_PROTOCOL = 1
MAX_PROTOCOL = 6

_LOGGER = logging.getLogger(__name__)

Protocol = namedtuple(
    "Protocol",
    [
        "pulselength",
        "sync_high",
        "sync_low",
        "zero_high",
        "zero_low",
        "one_high",
        "one_low",
    ],
)
PROTOCOLS = (
    None,
    Protocol(350, 1, 31, 1, 3, 3, 1),
    Protocol(650, 1, 10, 1, 2, 2, 1),
    Protocol(100, 30, 71, 4, 11, 9, 6),
    Protocol(380, 1, 6, 1, 3, 3, 1),
    Protocol(500, 6, 14, 1, 2, 2, 1),
    Protocol(200, 1, 10, 1, 5, 1, 1),
)


class RFDevice:
    """Representation of a GPIO RF device."""

    _gpio_lock = threading.RLock()
    _gpio_initialized = False

    def __init__(
        self,
        gpio: int,
        tx_proto: int = 1,
        tx_pulselength: int | None = None,
        tx_repeat: int = 10,
        tx_length: int = 24,
        rx_tolerance: int = 80,
    ) -> None:
        """Initialize the RF device."""
        self.gpio = gpio
        self.tx_enabled = False
        self.tx_proto = tx_proto
        if tx_pulselength:
            self.tx_pulselength = tx_pulselength
        else:
            self.tx_pulselength = PROTOCOLS[tx_proto].pulselength
        self.tx_repeat = tx_repeat
        self.tx_length = tx_length
        self.rx_enabled = False
        self.rx_tolerance = rx_tolerance
        # internal values
        self._rx_timings = [0] * (MAX_CHANGES + 1)
        self._rx_last_timestamp = 0
        self._rx_change_count = 0
        self._rx_repeat_count = 0
        # successful RX values
        self.rx_code = None
        self.rx_code_timestamp = None
        self.rx_proto = None
        self.rx_bitlength = None
        self.rx_pulselength = None

        with self._gpio_lock:
            if not self._gpio_initialized:
                GPIO.setmode(GPIO.BCM)
                RFDevice._gpio_initialized = True
        _LOGGER.debug("Using GPIO %d", gpio)

    def _validate_protocol(self, protocol: int) -> bool:
        """Validate protocol is in supported range."""
        if not MIN_PROTOCOL <= protocol <= MAX_PROTOCOL:
            _LOGGER.error(
                "Protocol %d not supported. Must be between %d and %d",
                protocol,
                MIN_PROTOCOL,
                MAX_PROTOCOL,
            )
            return False
        return True

    def cleanup(self) -> None:
        """Disable TX and RX and clean up GPIO."""
        if self.tx_enabled:
            self.disable_tx()
        if self.rx_enabled:
            self.disable_rx()
        _LOGGER.debug("Cleanup")
        GPIO.cleanup()

    def enable_tx(self) -> bool:
        """Enable TX, set up GPIO."""
        if self.rx_enabled:
            _LOGGER.error("RX is enabled, not enabling TX")
            return False
        if not self.tx_enabled:
            self.tx_enabled = True
            GPIO.setup(self.gpio, GPIO.OUT)
            _LOGGER.debug("TX enabled")
        return True

    def disable_tx(self) -> bool:
        """Disable TX, reset GPIO."""
        if self.tx_enabled:
            # set up GPIO pin as input for safety (only if RX isn't using it)
            if not self.rx_enabled:
                GPIO.setup(self.gpio, GPIO.IN)
            self.tx_enabled = False
            _LOGGER.debug("TX disabled")
        return True

    def tx_code(
        self,
        code: int,
        tx_proto: int | None = None,
        tx_pulselength: int | None = None,
        tx_length: int | None = None,
    ) -> bool:
        """Send a decimal code.

        Optionally set protocol, pulselength and code length.
        When none given reset to default protocol, default pulselength and set code length to 24 bits.
        """
        if tx_proto:
            self.tx_proto = tx_proto
        else:
            self.tx_proto = 1
        if tx_pulselength:
            self.tx_pulselength = tx_pulselength
        elif not self.tx_pulselength:
            self.tx_pulselength = PROTOCOLS[self.tx_proto].pulselength
        if tx_length:
            self.tx_length = tx_length
        elif self.tx_proto == 6:
            self.tx_length = 32
        elif code > 16777216:
            self.tx_length = 32
        else:
            self.tx_length = 24
        rawcode = format(code, f"#0{self.tx_length + 2}b")[2:]
        if self.tx_proto == 6:
            nexacode = ""
            for b in rawcode:
                if b == "0":
                    nexacode = nexacode + "01"
                if b == "1":
                    nexacode = nexacode + "10"
            rawcode = nexacode
            self.tx_length = 64
        _LOGGER.debug("TX code: %d", code)
        return self.tx_bin(rawcode)

    def tx_bin(self, rawcode: str) -> bool:
        """Send a binary code."""
        _LOGGER.debug("TX bin: %s", rawcode)
        for _ in range(0, self.tx_repeat):
            if self.tx_proto == 6:
                if not self.tx_sync():
                    return False
            for byte in range(0, self.tx_length):
                if rawcode[byte] == "0":
                    if not self.tx_l0():
                        return False
                else:
                    if not self.tx_l1():
                        return False
            if not self.tx_sync():
                return False

        return True

    def tx_l0(self) -> bool:
        """Send a '0' bit."""
        if not self._validate_protocol(self.tx_proto):
            return False
        return self.tx_waveform(
            PROTOCOLS[self.tx_proto].zero_high, PROTOCOLS[self.tx_proto].zero_low
        )

    def tx_l1(self) -> bool:
        """Send a '1' bit."""
        if not self._validate_protocol(self.tx_proto):
            return False
        return self.tx_waveform(
            PROTOCOLS[self.tx_proto].one_high, PROTOCOLS[self.tx_proto].one_low
        )

    def tx_sync(self) -> bool:
        """Send a sync."""
        if not self._validate_protocol(self.tx_proto):
            return False
        return self.tx_waveform(
            PROTOCOLS[self.tx_proto].sync_high, PROTOCOLS[self.tx_proto].sync_low
        )

    def tx_waveform(self, highpulses: int, lowpulses: int) -> bool:
        """Send basic waveform."""
        if not self.tx_enabled:
            _LOGGER.error("TX is not enabled, not sending data")
            return False
        GPIO.output(self.gpio, GPIO.HIGH)
        self._sleep((highpulses * self.tx_pulselength) / 1000000)
        GPIO.output(self.gpio, GPIO.LOW)
        self._sleep((lowpulses * self.tx_pulselength) / 1000000)
        return True

    def enable_rx(self) -> bool:
        """Enable RX, set up GPIO and add event detection."""
        if self.tx_enabled:
            _LOGGER.error("TX is enabled, not enabling RX")
            return False
        if not self.rx_enabled:
            self.rx_enabled = True
            GPIO.setup(self.gpio, GPIO.IN)
            GPIO.add_event_detect(self.gpio, GPIO.BOTH)
            GPIO.add_event_callback(self.gpio, self.rx_callback)
            _LOGGER.debug("RX enabled")
        return True

    def disable_rx(self) -> bool:
        """Disable RX, remove GPIO event detection."""
        if self.rx_enabled:
            GPIO.remove_event_detect(self.gpio)
            self.rx_enabled = False
            _LOGGER.debug("RX disabled")
        return True

    def rx_callback(self, gpio: int) -> None:
        """RX callback for GPIO event detection. Handle basic signal detection."""
        timestamp = int(time.perf_counter() * 1000000)
        duration = timestamp - self._rx_last_timestamp

        if duration > 5000:
            if abs(duration - self._rx_timings[0]) < 200:
                self._rx_repeat_count += 1
                self._rx_change_count -= 1
                if self._rx_repeat_count == 2:
                    for pnum in range(1, len(PROTOCOLS)):
                        if self._rx_waveform(pnum, self._rx_change_count, timestamp):
                            _LOGGER.debug("RX code %d", self.rx_code)
                            break
                    self._rx_repeat_count = 0
            self._rx_change_count = 0

        if self._rx_change_count >= MAX_CHANGES:
            self._rx_change_count = 0
            self._rx_repeat_count = 0
        self._rx_timings[self._rx_change_count] = duration
        self._rx_change_count += 1
        self._rx_last_timestamp = timestamp

    def _rx_waveform(self, pnum: int, change_count: int, timestamp: int) -> bool:
        """Detect waveform and format code."""
        code = 0
        delay = int(self._rx_timings[0] / PROTOCOLS[pnum].sync_low)
        delay_tolerance = delay * self.rx_tolerance / 100

        for i in range(1, change_count, 2):
            if (
                abs(self._rx_timings[i] - delay * PROTOCOLS[pnum].zero_high)
                < delay_tolerance
                and abs(self._rx_timings[i + 1] - delay * PROTOCOLS[pnum].zero_low)
                < delay_tolerance
            ):
                code <<= 1
            elif (
                abs(self._rx_timings[i] - delay * PROTOCOLS[pnum].one_high)
                < delay_tolerance
                and abs(self._rx_timings[i + 1] - delay * PROTOCOLS[pnum].one_low)
                < delay_tolerance
            ):
                code <<= 1
                code |= 1
            else:
                return False

        if self._rx_change_count > 6 and code != 0:
            self.rx_code = code
            self.rx_code_timestamp = timestamp
            self.rx_bitlength = int(change_count / 2)
            self.rx_pulselength = delay
            self.rx_proto = pnum
            return True

        return False

    def _sleep(self, delay: float) -> None:
        """High precision sleep function."""
        _delay = delay / 100
        end = time.time() + delay - _delay
        while time.time() < end:
            time.sleep(_delay)
