"""Tests for rf_device module."""

import time
from unittest.mock import Mock, patch, MagicMock
import pytest

from custom_components.ha_rf.rf_device import RFDevice, PROTOCOLS, MAX_PROTOCOL, MIN_PROTOCOL


class TestRFDevice:
    """Test RFDevice class."""

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_init_with_gpiod_available(self, mock_gpiod):
        """Test RFDevice initialization with gpiod available."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_info.num_lines = 54
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17)
        
        assert device.gpio == 17
        assert device.tx_enabled is False
        assert device.rx_enabled is False
        assert device.tx_proto == 1
        assert device.tx_pulselength == PROTOCOLS[1].pulselength
        assert device.tx_repeat == 10
        assert device.tx_length == 24

    @patch('custom_components.ha_rf.rf_device.gpiod', None)
    def test_init_without_gpiod(self):
        """Test RFDevice initialization fails without gpiod."""
        with pytest.raises(RuntimeError, match="gpiod is not available"):
            RFDevice(gpio=17)

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_init_custom_parameters(self, mock_gpiod):
        """Test RFDevice initialization with custom parameters."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(
            gpio=18,
            tx_proto=2,
            tx_pulselength=500,
            tx_repeat=15,
            tx_length=32,
            rx_tolerance=90
        )
        
        assert device.gpio == 18
        assert device.tx_proto == 2
        assert device.tx_pulselength == 500
        assert device.tx_repeat == 15
        assert device.tx_length == 32
        assert device.rx_tolerance == 90

    def test_validate_protocol_valid(self):
        """Test protocol validation with valid protocols."""
        with patch('custom_components.ha_rf.rf_device.gpiod'):
            device = RFDevice(gpio=17)
            
        for protocol in range(MIN_PROTOCOL, MAX_PROTOCOL + 1):
            assert device._validate_protocol(protocol) is True

    def test_validate_protocol_invalid(self):
        """Test protocol validation with invalid protocols."""
        with patch('custom_components.ha_rf.rf_device.gpiod'):
            device = RFDevice(gpio=17)
            
        assert device._validate_protocol(0) is False
        assert device._validate_protocol(7) is False
        assert device._validate_protocol(-1) is False

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_find_gpio_chip_success(self, mock_gpiod):
        """Test GPIO chip detection success."""
        # Mock successful chip detection
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_info.num_lines = 54
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17)
        result = device._find_gpio_chip()
        
        assert result == "/dev/gpiochip0"

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_find_gpio_chip_failure(self, mock_gpiod):
        """Test GPIO chip detection failure."""
        # Mock chip detection failure
        mock_gpiod.Chip.side_effect = Exception("No chip found")
        
        with pytest.raises(RuntimeError, match="No suitable GPIO chip found"):
            RFDevice(gpio=17)

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_enable_tx_success(self, mock_gpiod):
        """Test TX enable success."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        result = device.enable_tx()
        
        assert result is True
        assert device.tx_enabled is True
        assert device._gpio_request == mock_request

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_enable_tx_with_rx_enabled(self, mock_gpiod):
        """Test TX enable fails when RX is enabled."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17)
        device.rx_enabled = True
        
        result = device.enable_tx()
        
        assert result is False
        assert device.tx_enabled is False

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_disable_tx(self, mock_gpiod):
        """Test TX disable."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        result = device.disable_tx()
        
        assert result is True
        assert device.tx_enabled is False

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_tx_code_basic(self, mock_gpiod):
        """Test basic code transmission."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        with patch.object(device, 'tx_bin', return_value=True) as mock_tx_bin:
            result = device.tx_code(1234567)
            
        assert result is True
        mock_tx_bin.assert_called_once()

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_tx_code_with_parameters(self, mock_gpiod):
        """Test code transmission with custom parameters."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        with patch.object(device, 'tx_bin', return_value=True):
            result = device.tx_code(
                code=1234567,
                tx_proto=2,
                tx_pulselength=500,
                tx_length=32
            )
            
        assert result is True
        assert device.tx_proto == 2
        assert device.tx_pulselength == 500
        assert device.tx_length == 32

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_tx_waveform_success(self, mock_gpiod):
        """Test waveform transmission success."""
        # Mock gpiod components and Value enum
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        # Mock the Value enum
        from unittest.mock import Mock
        mock_value = Mock()
        mock_value.ACTIVE = "ACTIVE"
        mock_value.INACTIVE = "INACTIVE"
        
        with patch('custom_components.ha_rf.rf_device.Value', mock_value):
            device = RFDevice(gpio=17)
            device.enable_tx()
            
            with patch.object(device, '_sleep') as mock_sleep:
                result = device.tx_waveform(highpulses=3, lowpulses=1)
                
        assert result is True
        assert mock_request.set_value.call_count == 2
        assert mock_sleep.call_count == 2

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_tx_waveform_not_enabled(self, mock_gpiod):
        """Test waveform transmission when TX not enabled."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17)
        # Don't enable TX
        
        result = device.tx_waveform(highpulses=3, lowpulses=1)
        
        assert result is False

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_cleanup(self, mock_gpiod):
        """Test cleanup method."""
        # Mock gpiod components
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        device.cleanup()
        
        assert device.tx_enabled is False
        mock_request.release.assert_called_once()

    def test_sleep_method(self):
        """Test _sleep method timing."""
        with patch('custom_components.ha_rf.rf_device.gpiod'):
            device = RFDevice(gpio=17)
            
        start_time = time.perf_counter()
        device._sleep(0.001)  # 1ms
        end_time = time.perf_counter()
        
        # Should sleep for approximately 1ms (allow some tolerance)
        elapsed = end_time - start_time
        assert 0.0009 <= elapsed <= 0.002  # 0.9ms to 2ms tolerance


class TestProtocols:
    """Test RF protocol definitions."""

    def test_protocols_structure(self):
        """Test that protocols are properly defined."""
        assert PROTOCOLS[0] is None  # Protocol 0 should be None
        
        for i in range(1, 7):
            protocol = PROTOCOLS[i]
            assert protocol is not None
            assert hasattr(protocol, 'pulselength')
            assert hasattr(protocol, 'sync_high')
            assert hasattr(protocol, 'sync_low')
            assert hasattr(protocol, 'zero_high')
            assert hasattr(protocol, 'zero_low')
            assert hasattr(protocol, 'one_high')
            assert hasattr(protocol, 'one_low')
            
            # All values should be positive integers
            assert protocol.pulselength > 0
            assert protocol.sync_high > 0
            assert protocol.sync_low > 0
            assert protocol.zero_high > 0
            assert protocol.zero_low > 0
            assert protocol.one_high > 0
            assert protocol.one_low > 0

    def test_protocol_constants(self):
        """Test protocol constants."""
        assert MIN_PROTOCOL == 1
        assert MAX_PROTOCOL == 6
        assert len(PROTOCOLS) == 7  # 0-6 inclusive