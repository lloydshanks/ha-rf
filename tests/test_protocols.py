"""Tests for RF protocol logic and timing."""

import pytest
import time
from unittest.mock import Mock, patch

from custom_components.ha_rf.rf_device import RFDevice, PROTOCOLS


class TestRFProtocols:
    """Test RF protocol behavior and timing."""

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_protocol_1_princeton(self, mock_gpiod):
        """Test Protocol 1 (Princeton/PT2262) characteristics."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17, tx_proto=1)
        
        protocol = PROTOCOLS[1]
        
        # Princeton protocol characteristics
        assert protocol.pulselength == 350  # Default pulse length
        assert protocol.sync_high == 1
        assert protocol.sync_low == 31  # Sync ratio 1:31
        assert protocol.zero_high == 1
        assert protocol.zero_low == 3  # Zero ratio 1:3
        assert protocol.one_high == 3
        assert protocol.one_low == 1  # One ratio 3:1

    @patch('custom_components.ha_rf.rf_device.gpiod')  
    def test_protocol_timing_calculation(self, mock_gpiod):
        """Test timing calculations for different protocols."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17, tx_proto=1, tx_pulselength=410)
        
        # Protocol 1 with 410µs pulse length (from Flipper analysis)
        # Zero bit: high=1×410µs, low=3×410µs = 410µs high, 1230µs low
        # One bit: high=3×410µs, low=1×410µs = 1230µs high, 410µs low
        # Sync: high=1×410µs, low=31×410µs = 410µs high, 12710µs low
        
        protocol = PROTOCOLS[1]
        
        zero_high_time = protocol.zero_high * 410 / 1_000_000  # Convert to seconds
        zero_low_time = protocol.zero_low * 410 / 1_000_000
        one_high_time = protocol.one_high * 410 / 1_000_000  
        one_low_time = protocol.one_low * 410 / 1_000_000
        sync_high_time = protocol.sync_high * 410 / 1_000_000
        sync_low_time = protocol.sync_low * 410 / 1_000_000
        
        # Verify timing calculations
        assert abs(zero_high_time - 0.000410) < 0.000001  # 410µs
        assert abs(zero_low_time - 0.001230) < 0.000001   # 1230µs  
        assert abs(one_high_time - 0.001230) < 0.000001   # 1230µs
        assert abs(one_low_time - 0.000410) < 0.000001    # 410µs
        assert abs(sync_high_time - 0.000410) < 0.000001  # 410µs
        assert abs(sync_low_time - 0.012710) < 0.000001   # 12710µs

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_code_length_detection(self, mock_gpiod):
        """Test automatic code length detection."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        # Test 24-bit code (fits in 24 bits)
        with patch.object(device, 'tx_bin', return_value=True) as mock_tx_bin:
            device.tx_code(7860097)  # 0x77EF81, fits in 24 bits
            
        assert device.tx_length == 24
        
        # Test 32-bit code (exceeds 24 bits)
        with patch.object(device, 'tx_bin', return_value=True) as mock_tx_bin:
            device.tx_code(16777217)  # Exceeds 24-bit range
            
        assert device.tx_length == 32

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_protocol_6_nexa(self, mock_gpiod):
        """Test Protocol 6 (Nexa format) special handling."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        # Protocol 6 has special encoding and length handling
        with patch.object(device, 'tx_bin', return_value=True) as mock_tx_bin:
            device.tx_code(1234567, tx_proto=6)
            
        # Protocol 6 forces 32-bit length and doubles it for encoding
        assert device.tx_length == 64
        assert device.tx_proto == 6

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_binary_encoding(self, mock_gpiod):
        """Test binary code encoding.""" 
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        # Test that decimal codes are properly converted to binary
        test_code = 7860097  # 0x77EF81 in hex
        expected_binary = format(test_code, f"#0{24 + 2}b")[2:]  # 24-bit binary
        
        with patch.object(device, 'tx_bin', return_value=True) as mock_tx_bin:
            device.tx_code(test_code, tx_length=24)
            
        # Should call tx_bin with correct binary representation
        mock_tx_bin.assert_called_once_with(expected_binary)

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_nexa_encoding(self, mock_gpiod):
        """Test Nexa protocol special encoding."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        # Protocol 6 converts each bit: 0 -> "01", 1 -> "10"
        test_code = 5  # Binary: 101, should become: 10 01 10 -> 100110
        
        with patch.object(device, 'tx_bin', return_value=True) as mock_tx_bin:
            device.tx_code(test_code, tx_proto=6)
            
        # Extract the call argument to check Nexa encoding
        call_args = mock_tx_bin.call_args[0][0]
        
        # For a 32-bit representation of 5, each bit gets doubled
        # The encoding should follow the Nexa pattern
        assert len(call_args) == 64  # Doubled length
        assert "01" in call_args and "10" in call_args  # Should contain both patterns


class TestTimingAccuracy:
    """Test timing accuracy and sleep behavior."""

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_sleep_accuracy(self, mock_gpiod):
        """Test _sleep method accuracy."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17)
        
        # Test microsecond-level sleep
        target_sleep = 0.000410  # 410 microseconds
        
        start_time = time.perf_counter()
        device._sleep(target_sleep)
        end_time = time.perf_counter()
        
        actual_sleep = end_time - start_time
        
        # Should be reasonably close (within 1ms tolerance for current implementation)
        assert actual_sleep >= target_sleep
        assert actual_sleep <= target_sleep + 0.001  # 1ms tolerance

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_waveform_timing(self, mock_gpiod):
        """Test waveform timing calls."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        # Mock Value enum
        mock_value = Mock()
        mock_value.ACTIVE = "ACTIVE"
        mock_value.INACTIVE = "INACTIVE"
        
        with patch('custom_components.ha_rf.rf_device.Value', mock_value):
            device = RFDevice(gpio=17, tx_pulselength=410)
            device.enable_tx()
            
            with patch.object(device, '_sleep') as mock_sleep:
                device.tx_waveform(highpulses=3, lowpulses=1)
                
            # Should call _sleep twice with correct timing
            assert mock_sleep.call_count == 2
            
            # First call: high pulse timing (3 × 410µs)
            high_time = mock_sleep.call_args_list[0][0][0]
            assert abs(high_time - 0.00123) < 0.000001  # 1230µs
            
            # Second call: low pulse timing (1 × 410µs)
            low_time = mock_sleep.call_args_list[1][0][0]
            assert abs(low_time - 0.00041) < 0.000001   # 410µs


class TestTransmissionReliability:
    """Test transmission reliability features."""

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_transmission_repetition(self, mock_gpiod):
        """Test transmission repetition."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17, tx_repeat=5)  # 5 repetitions
        device.enable_tx()
        
        # Mock the actual transmission methods
        with patch.object(device, 'tx_sync', return_value=True) as mock_sync, \
             patch.object(device, 'tx_l0', return_value=True) as mock_l0, \
             patch.object(device, 'tx_l1', return_value=True) as mock_l1:
            
            # Transmit a simple 2-bit code "10"
            device.tx_bin("10")
            
            # Should repeat 5 times: each repetition sends sync + bits + sync
            # tx_sync called: 5 times at start of each repetition + 5 times at end = 10 total
            # tx_l1 called: 5 times (first bit "1")
            # tx_l0 called: 5 times (second bit "0")
            assert mock_sync.call_count == 10  # 2 sync calls per repetition × 5 repetitions
            assert mock_l1.call_count == 5    # First bit "1" × 5 repetitions
            assert mock_l0.call_count == 5    # Second bit "0" × 5 repetitions

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_error_handling_during_transmission(self, mock_gpiod):
        """Test error handling during transmission."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        # Mock transmission failure
        with patch.object(device, 'tx_sync', return_value=False):
            result = device.tx_bin("10")
            
        # Should return False when sync fails
        assert result is False

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_invalid_protocol_handling(self, mock_gpiod):
        """Test handling of invalid protocols during transmission."""
        # Mock gpiod
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        device = RFDevice(gpio=17)
        device.enable_tx()
        
        # Set invalid protocol
        device.tx_proto = 99  # Invalid protocol
        
        # Should fail validation
        assert device.tx_l0() is False
        assert device.tx_l1() is False
        assert device.tx_sync() is False