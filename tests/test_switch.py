"""Tests for switch platform."""

import pytest
from unittest.mock import Mock, patch
from threading import RLock

from custom_components.ha_rf.switch import setup_platform, RPiRFSwitch


class TestSetupPlatform:
    """Test setup_platform function."""

    @patch("custom_components.ha_rf.switch.RFDevice")
    def test_setup_platform_success(self, mock_rfdevice_class):
        """Test successful platform setup."""
        # Mock Home Assistant components
        mock_hass = Mock()
        mock_add_entities = Mock()

        # Mock RFDevice
        mock_rfdevice = Mock()
        mock_rfdevice.enable_tx.return_value = True
        mock_rfdevice_class.return_value = mock_rfdevice

        # Test configuration
        config = {
            "gpio": 17,
            "switches": {
                "test_switch": {
                    "name": "Test Switch",
                    "code_on": 1234567,
                    "code_off": 1234568,
                    "unique_id": "test_switch_rf",
                }
            },
        }

        setup_platform(mock_hass, config, mock_add_entities)

        # Verify RFDevice was created with correct GPIO
        mock_rfdevice_class.assert_called_once_with(17)

        # Verify TX was enabled
        mock_rfdevice.enable_tx.assert_called_once()

        # Verify entities were added
        mock_add_entities.assert_called_once()
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], RPiRFSwitch)

    @patch("custom_components.ha_rf.switch.RFDevice")
    def test_setup_platform_rfdevice_failure(self, mock_rfdevice_class):
        """Test platform setup when RFDevice initialization fails."""
        # Mock Home Assistant components
        mock_hass = Mock()
        mock_add_entities = Mock()

        # Mock RFDevice initialization failure
        mock_rfdevice_class.side_effect = RuntimeError("GPIO not available")

        config = {
            "gpio": 17,
            "switches": {"test_switch": {"code_on": 1234567, "code_off": 1234568}},
        }

        # Should not raise exception, but should return early
        setup_platform(mock_hass, config, mock_add_entities)

        # Verify add_entities was not called
        mock_add_entities.assert_not_called()

    @patch("custom_components.ha_rf.switch.RFDevice")
    def test_setup_platform_tx_enable_failure(self, mock_rfdevice_class):
        """Test platform setup when TX enable fails."""
        # Mock Home Assistant components
        mock_hass = Mock()
        mock_add_entities = Mock()

        # Mock RFDevice with TX enable failure
        mock_rfdevice = Mock()
        mock_rfdevice.enable_tx.return_value = False
        mock_rfdevice_class.return_value = mock_rfdevice

        config = {
            "gpio": 17,
            "switches": {"test_switch": {"code_on": 1234567, "code_off": 1234568}},
        }

        setup_platform(mock_hass, config, mock_add_entities)

        # Should return early, not call add_entities
        mock_add_entities.assert_not_called()

    @patch("custom_components.ha_rf.switch.RFDevice")
    def test_setup_platform_multiple_switches(self, mock_rfdevice_class):
        """Test platform setup with multiple switches."""
        # Mock Home Assistant components
        mock_hass = Mock()
        mock_add_entities = Mock()

        # Mock RFDevice
        mock_rfdevice = Mock()
        mock_rfdevice.enable_tx.return_value = True
        mock_rfdevice_class.return_value = mock_rfdevice

        config = {
            "gpio": 17,
            "switches": {
                "switch1": {
                    "name": "Switch 1",
                    "code_on": 1111111,
                    "code_off": 1111112,
                },
                "switch2": {
                    "name": "Switch 2",
                    "code_on": 2222221,
                    "code_off": 2222222,
                },
                "switch3": {"code_on": 3333331, "code_off": 3333332},
            },
        }

        setup_platform(mock_hass, config, mock_add_entities)

        # Verify 3 entities were created
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) == 3


class TestRPiRFSwitch:
    """Test RPiRFSwitch class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_rfdevice = Mock()
        self.mock_lock = RLock()

        self.switch = RPiRFSwitch(
            name="Test Switch",
            unique_id="test_switch_rf",
            rfdevice=self.mock_rfdevice,
            lock=self.mock_lock,
            protocol=1,
            pulselength=350,
            length=24,
            signal_repetitions=10,
            code_on=[1234567],
            code_off=[1234568],
        )
        # Stub out the HA-side state update so unit tests don't need a hass instance
        self.switch.schedule_update_ha_state = Mock()

    def test_switch_initialization(self):
        """Test switch initialization."""
        assert self.switch.name == "Test Switch"
        assert self.switch.unique_id == "test_switch_rf"
        assert self.switch._protocol == 1
        assert self.switch._pulselength == 350
        assert self.switch._length == 24
        assert self.switch._signal_repetitions == 10
        assert self.switch._code_on == [1234567]
        assert self.switch._code_off == [1234568]

    def test_switch_initialization_with_defaults(self):
        """Test switch initialization with default values."""
        switch = RPiRFSwitch(
            name="Default Switch",
            unique_id=None,
            rfdevice=self.mock_rfdevice,
            lock=self.mock_lock,
            protocol=None,
            pulselength=None,
            length=None,
            signal_repetitions=None,
            code_on=[9999999],
            code_off=[9999998],
        )

        assert switch.name == "Default Switch"
        # When unique_id is not provided, it's auto-generated from the codes
        assert switch.unique_id == "[9999999]_[9999998]"
        assert switch._protocol is None
        assert switch._pulselength is None
        assert switch._length is None
        assert switch._signal_repetitions is None

    def test_switch_multiple_codes(self):
        """Test switch with multiple codes."""
        switch = RPiRFSwitch(
            name="Multi Switch",
            unique_id="multi_switch_rf",
            rfdevice=self.mock_rfdevice,
            lock=self.mock_lock,
            protocol=1,
            pulselength=350,
            length=24,
            signal_repetitions=10,
            code_on=[1111111, 1111112, 1111113],
            code_off=[2222221, 2222222, 2222223],
        )

        assert switch._code_on == [1111111, 1111112, 1111113]
        assert switch._code_off == [2222221, 2222222, 2222223]

    def test_turn_on_success(self):
        """Test successful turn on."""
        self.mock_rfdevice.tx_code.return_value = True

        self.switch.turn_on()

        # Should send the on code with all configured parameters as kwargs
        self.mock_rfdevice.tx_code.assert_called_with(
            1234567,
            tx_proto=1,
            tx_pulselength=350,
            tx_length=24,
            tx_repeat=10,
        )

    def test_turn_on_multiple_codes(self):
        """Test turn on with multiple codes."""
        switch = RPiRFSwitch(
            name="Multi Switch",
            unique_id="multi_switch_rf",
            rfdevice=self.mock_rfdevice,
            lock=self.mock_lock,
            protocol=1,
            pulselength=350,
            length=24,
            signal_repetitions=10,
            code_on=[1111111, 1111112],
            code_off=[2222221, 2222222],
        )
        switch.schedule_update_ha_state = Mock()

        self.mock_rfdevice.tx_code.return_value = True

        switch.turn_on()

        assert self.mock_rfdevice.tx_code.call_count == 2
        self.mock_rfdevice.tx_code.assert_any_call(
            1111111, tx_proto=1, tx_pulselength=350, tx_length=24, tx_repeat=10
        )
        self.mock_rfdevice.tx_code.assert_any_call(
            1111112, tx_proto=1, tx_pulselength=350, tx_length=24, tx_repeat=10
        )

    def test_turn_off_success(self):
        """Test successful turn off."""
        self.mock_rfdevice.tx_code.return_value = True

        self.switch.turn_off()

        self.mock_rfdevice.tx_code.assert_called_with(
            1234568,
            tx_proto=1,
            tx_pulselength=350,
            tx_length=24,
            tx_repeat=10,
        )

    def test_turn_on_failure(self):
        """Test turn on when RF transmission fails."""
        self.mock_rfdevice.tx_code.return_value = False

        with patch("custom_components.ha_rf.switch._LOGGER") as mock_logger:
            self.switch.turn_on()
            mock_logger.error.assert_called()

    def test_turn_off_failure(self):
        """Test turn off when RF transmission fails."""
        self.mock_rfdevice.tx_code.return_value = False

        with patch("custom_components.ha_rf.switch._LOGGER") as mock_logger:
            self.switch.turn_off()
            mock_logger.error.assert_called()

    def test_send_code_with_repetitions(self):
        """Test _send_code passes signal_repetitions through to tx_code."""
        self.switch._signal_repetitions = 3
        self.mock_rfdevice.tx_code.return_value = True

        result = self.switch._send_code([9999999])

        assert result is True
        # tx_code is called once per code; repetitions are handled inside the
        # device by the tx_repeat kwarg.
        assert self.mock_rfdevice.tx_code.call_count == 1
        self.mock_rfdevice.tx_code.assert_called_with(
            9999999, tx_proto=1, tx_pulselength=350, tx_length=24, tx_repeat=3
        )

    def test_send_code_with_none_repetitions(self):
        """Test _send_code with None repetitions (device falls back to default)."""
        self.switch._signal_repetitions = None
        self.mock_rfdevice.tx_code.return_value = True

        result = self.switch._send_code([8888888])

        assert result is True
        assert self.mock_rfdevice.tx_code.call_count == 1
        self.mock_rfdevice.tx_code.assert_called_with(
            8888888, tx_proto=1, tx_pulselength=350, tx_length=24, tx_repeat=None
        )

    def test_assumed_state(self):
        """Test that switch has assumed state."""
        # RF switches should always have assumed state since we can't read their state
        assert self.switch.assumed_state is True

    def test_should_poll(self):
        """Test that switch should not poll."""
        # RF switches don't support polling
        assert self.switch.should_poll is False


class TestSwitchConfiguration:
    """Test switch configuration validation."""

    def test_configuration_schema(self):
        """Test configuration schema validation."""
        from custom_components.ha_rf.switch import PLATFORM_SCHEMA

        # Valid configuration
        # Note: SWITCH_SCHEMA doesn't accept a 'name' key directly — entity
        # names come from the switch dict key.
        valid_config = {
            "platform": "ha_rf",
            "gpio": 17,
            "switches": {
                "test_switch": {
                    "code_on": 1234567,
                    "code_off": 1234568,
                    "protocol": 1,
                    "pulselength": 350,
                    "length": 24,
                    "signal_repetitions": 10,
                    "unique_id": "test_switch_rf",
                }
            },
        }

        # Should not raise exception
        validated = PLATFORM_SCHEMA(valid_config)
        assert validated["gpio"] == 17
        assert "test_switch" in validated["switches"]

    def test_configuration_schema_minimal(self):
        """Test configuration schema with minimal config."""
        from custom_components.ha_rf.switch import PLATFORM_SCHEMA

        # Minimal valid configuration
        minimal_config = {
            "platform": "ha_rf",
            "gpio": 17,
            "switches": {"minimal_switch": {"code_on": 1111111, "code_off": 1111112}},
        }

        # Should not raise exception
        validated = PLATFORM_SCHEMA(minimal_config)
        assert validated["gpio"] == 17

    def test_configuration_schema_invalid_gpio(self):
        """Test configuration schema with invalid GPIO."""
        from custom_components.ha_rf.switch import PLATFORM_SCHEMA
        import voluptuous as vol

        invalid_config = {
            "platform": "ha_rf",
            "gpio": -1,  # Invalid GPIO
            "switches": {"test_switch": {"code_on": 1234567, "code_off": 1234568}},
        }

        with pytest.raises(vol.Invalid):
            PLATFORM_SCHEMA(invalid_config)

    def test_configuration_schema_invalid_protocol(self):
        """Test configuration schema rejects out-of-range protocol."""
        from custom_components.ha_rf.switch import PLATFORM_SCHEMA
        import voluptuous as vol

        invalid_config = {
            "platform": "ha_rf",
            "gpio": 17,
            "switches": {
                "test_switch": {
                    "code_on": 1234567,
                    "code_off": 1234568,
                    "protocol": 7,  # only 1..6 are valid
                }
            },
        }

        with pytest.raises(vol.Invalid):
            PLATFORM_SCHEMA(invalid_config)

    def test_configuration_schema_with_rx_gpio(self):
        """Test configuration schema accepts the optional rx_gpio key."""
        from custom_components.ha_rf.switch import PLATFORM_SCHEMA

        config = {
            "platform": "ha_rf",
            "gpio": 17,
            "rx_gpio": 27,
            "switches": {
                "test_switch": {
                    "code_on": 1234567,
                    "code_off": 1234568,
                }
            },
        }

        validated = PLATFORM_SCHEMA(config)
        assert validated["rx_gpio"] == 27
