"""Support for a switch using a 433MHz module via GPIO on a Raspberry Pi."""

from __future__ import annotations

import logging
from threading import RLock

import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (
    CONF_NAME,
    CONF_UNIQUE_ID,
    CONF_PROTOCOL,
    CONF_SWITCHES,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .rf_device import RFDevice
from .rf_receiver import RFReceiver

_LOGGER = logging.getLogger(__name__)

CONF_CODE_OFF = "code_off"
CONF_CODE_ON = "code_on"
CONF_GPIO = "gpio"
CONF_RX_GPIO = "rx_gpio"
CONF_PULSELENGTH = "pulselength"
CONF_SIGNAL_REPETITIONS = "signal_repetitions"
CONF_LENGTH = "length"

DEFAULT_PROTOCOL = 1
DEFAULT_SIGNAL_REPETITIONS = 10
DEFAULT_LENGTH = 24

SWITCH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CODE_OFF): vol.All(cv.ensure_list_csv, [cv.positive_int]),
        vol.Required(CONF_CODE_ON): vol.All(cv.ensure_list_csv, [cv.positive_int]),
        vol.Optional(CONF_PULSELENGTH): cv.positive_int,
        vol.Optional(
            CONF_SIGNAL_REPETITIONS, default=DEFAULT_SIGNAL_REPETITIONS
        ): cv.positive_int,
        vol.Optional(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.All(
            cv.positive_int, vol.Range(min=1, max=6)
        ),
        vol.Optional(CONF_LENGTH, default=DEFAULT_LENGTH): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_GPIO): cv.positive_int,
        vol.Optional(CONF_RX_GPIO): cv.positive_int,
        vol.Required(CONF_SWITCHES): vol.Schema({cv.string: SWITCH_SCHEMA}),
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Find and return switches controlled by a generic RF device via GPIO."""
    gpio = config[CONF_GPIO]
    _LOGGER.info("Setting up ha_rf platform with GPIO %d", gpio)

    try:
        rfdevice = RFDevice(gpio)
        _LOGGER.info("RFDevice initialized successfully")
    except Exception as err:
        _LOGGER.error(
            "Failed to initialize RFDevice: %s "
            "(likely gpiod missing or GPIO permissions insufficient)",
            err,
        )
        return

    rfdevice_lock = RLock()
    switches = config[CONF_SWITCHES]

    devices = []
    for dev_name, properties in switches.items():
        _LOGGER.info("Creating switch: %s", dev_name)
        devices.append(
            RPiRFSwitch(
                properties.get(CONF_NAME, dev_name),
                properties.get(CONF_UNIQUE_ID),
                rfdevice,
                rfdevice_lock,
                properties.get(CONF_PROTOCOL),
                properties.get(CONF_PULSELENGTH),
                properties.get(CONF_LENGTH),
                properties.get(CONF_SIGNAL_REPETITIONS),
                properties.get(CONF_CODE_ON),
                properties.get(CONF_CODE_OFF),
            )
        )

    if not devices:
        return

    _LOGGER.info("Enabling TX for %d devices", len(devices))
    try:
        if not rfdevice.enable_tx():
            _LOGGER.error("enable_tx() returned False; aborting platform setup")
            return
    except Exception as err:
        _LOGGER.error("Failed to enable TX: %s", err)
        return

    _LOGGER.info("Adding %d entities to Home Assistant", len(devices))
    add_entities(devices)

    receiver: RFReceiver | None = None
    rx_gpio = config.get(CONF_RX_GPIO)
    if rx_gpio is not None:
        try:
            receiver = RFReceiver(rx_gpio, rfdevice._gpio_chip_path)
            receiver.start()
        except Exception as err:
            _LOGGER.error("Failed to start RX listener on GPIO %d: %s", rx_gpio, err)
            receiver = None

    def _shutdown(event) -> None:
        if receiver is not None:
            receiver.stop()
        rfdevice.cleanup()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown)


class RPiRFSwitch(SwitchEntity):
    """Representation of a GPIO RF switch."""

    _attr_assumed_state = True
    _attr_should_poll = False

    def __init__(
        self,
        name: str,
        unique_id: str | None,
        rfdevice: RFDevice,
        lock: RLock,
        protocol: int | None,
        pulselength: int | None,
        length: int | None,
        signal_repetitions: int | None,
        code_on: list[int],
        code_off: list[int],
    ) -> None:
        """Initialize the switch."""
        self._name = name
        self._attr_unique_id = (
            unique_id if unique_id else "{}_{}".format(code_on, code_off)
        )
        self._state = False
        self._rfdevice = rfdevice
        self._lock = lock
        self._protocol = protocol
        self._pulselength = pulselength
        self._length = length
        self._signal_repetitions = signal_repetitions
        self._code_on = code_on
        self._code_off = code_off

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._state

    def _send_code(self, code_list: list[int]) -> bool:
        """Send the code(s) using this switch's configured parameters."""
        with self._lock:
            _LOGGER.info("Sending code(s): %s", code_list)
            for code in code_list:
                if not self._rfdevice.tx_code(
                    code,
                    tx_proto=self._protocol,
                    tx_pulselength=self._pulselength,
                    tx_length=self._length,
                    tx_repeat=self._signal_repetitions,
                ):
                    _LOGGER.error("Failed to send code: %s", code)
                    return False
        return True

    def turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        if self._send_code(self._code_on):
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        if self._send_code(self._code_off):
            self._state = False
            self.schedule_update_ha_state()
