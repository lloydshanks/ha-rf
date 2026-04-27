"""Background RX listener for the ha_rf integration.

Listens for edge transitions on a GPIO RX line using libgpiod v2 edge
events and decodes pulse trains against the same protocol table the
TX side uses. Decoded codes are logged at INFO level so users can
verify what their existing remotes broadcast and what the integration
itself is producing over the air.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gpiod
    from gpiod.line import Bias, Direction, Edge

    HAS_GPIOD = True
else:
    try:
        import gpiod
        from gpiod.line import Bias, Direction, Edge

        HAS_GPIOD = True
    except ImportError:
        gpiod = None
        Bias = Direction = Edge = None
        HAS_GPIOD = False

from .rf_device import MAX_CHANGES, PROTOCOLS

_LOGGER = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_S = 2.0


class RFReceiver:
    """Decodes RF pulse trains arriving on a GPIO line."""

    def __init__(self, gpio: int, chip_path: str, tolerance: int = 80) -> None:
        if not HAS_GPIOD:
            raise RuntimeError("gpiod is not available; cannot start RX listener")
        self._gpio = gpio
        self._chip_path = chip_path
        self._tolerance = tolerance
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._request: gpiod.LineRequest | None = None
        self._timings = [0] * (MAX_CHANGES + 1)
        self._last_ts = 0
        self._change_count = 0
        self._repeat_count = 0
        self._edges_since_heartbeat = 0
        self._next_heartbeat = 0.0

    def start(self) -> None:
        """Open the line and spawn the decoder thread."""
        if self._thread is not None:
            return
        self._request = gpiod.request_lines(
            self._chip_path,
            consumer="ha-rf-rx",
            config={
                self._gpio: gpiod.LineSettings(
                    direction=Direction.INPUT,
                    edge_detection=Edge.BOTH,
                    bias=Bias.DISABLED,
                )
            },
        )
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ha-rf-rx")
        self._thread.start()
        _LOGGER.info("RX listener started on GPIO %d", self._gpio)

    def stop(self) -> None:
        """Stop the decoder thread and release the line."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._request is not None:
            self._request.release()
            self._request = None
        _LOGGER.debug("RX listener stopped")

    def _loop(self) -> None:
        assert self._request is not None  # set in start() before this thread runs
        request = self._request
        self._next_heartbeat = time.monotonic() + HEARTBEAT_INTERVAL_S
        while not self._stop.is_set():
            try:
                if request.wait_edge_events(timeout=0.5):
                    for event in request.read_edge_events():
                        self._edges_since_heartbeat += 1
                        self._feed(event.timestamp_ns // 1000)
                now = time.monotonic()
                if now >= self._next_heartbeat:
                    if self._edges_since_heartbeat > 0:
                        _LOGGER.info(
                            "RX heartbeat: %d edges in last %.0fs",
                            self._edges_since_heartbeat,
                            HEARTBEAT_INTERVAL_S,
                        )
                    self._edges_since_heartbeat = 0
                    self._next_heartbeat = now + HEARTBEAT_INTERVAL_S
            except Exception:
                _LOGGER.exception("RX loop error; thread exiting")
                return

    def _feed(self, ts_us: int) -> None:
        if self._last_ts == 0:
            self._last_ts = ts_us
            return
        duration = ts_us - self._last_ts
        if duration > 5000:
            if abs(duration - self._timings[0]) < 200:
                self._repeat_count += 1
                self._change_count -= 1
                if self._repeat_count == 2:
                    self._try_decode(self._change_count)
                    self._repeat_count = 0
            self._change_count = 0
        if self._change_count >= MAX_CHANGES:
            self._change_count = 0
            self._repeat_count = 0
        self._timings[self._change_count] = duration
        self._change_count += 1
        self._last_ts = ts_us

    def _try_decode(self, change_count: int) -> None:
        for pnum in range(1, len(PROTOCOLS)):
            decoded = self._decode(pnum, change_count)
            if decoded is not None:
                code, bits, pulse = decoded
                _LOGGER.info(
                    "RX decoded code=%d bits=%d protocol=%d pulselength=%dus",
                    code,
                    bits,
                    pnum,
                    pulse,
                )
                return
        _LOGGER.debug(
            "RX undecoded frame (%d edges, sync=%dus)",
            change_count,
            self._timings[0],
        )

    def _decode(self, pnum: int, change_count: int) -> tuple[int, int, int] | None:
        proto = PROTOCOLS[pnum]
        delay = self._timings[0] // proto.sync_low
        if delay <= 0:
            return None
        delay_tol = delay * self._tolerance // 100
        code = 0
        for i in range(1, change_count, 2):
            t_high = self._timings[i]
            t_low = self._timings[i + 1] if (i + 1) <= change_count else 0
            if (
                abs(t_high - delay * proto.zero_high) < delay_tol
                and abs(t_low - delay * proto.zero_low) < delay_tol
            ):
                code <<= 1
            elif (
                abs(t_high - delay * proto.one_high) < delay_tol
                and abs(t_low - delay * proto.one_low) < delay_tol
            ):
                code = (code << 1) | 1
            else:
                return None
        if change_count > 6 and code != 0:
            return code, change_count // 2, delay
        return None
