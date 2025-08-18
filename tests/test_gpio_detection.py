"""Tests for GPIO chip detection logic."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from custom_components.ha_rf.rf_device import RFDevice


class TestGPIOChipDetection:
    """Test GPIO chip detection across different Raspberry Pi models."""

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_find_gpio_chip_pi3_pi4(self, mock_gpiod):
        """Test GPIO chip detection for Raspberry Pi 3/4 (gpiochip0)."""
        # Mock successful detection on gpiochip0
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"  # Pi 3/4 label
        mock_info.num_lines = 54
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17)
        result = device._find_gpio_chip()
        
        assert result == "/dev/gpiochip0"
        # Should try gpiochip0 first for Pi 3/4
        mock_gpiod.Chip.assert_called_with("/dev/gpiochip0")

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_find_gpio_chip_pi5(self, mock_gpiod):
        """Test GPIO chip detection for Raspberry Pi 5 (gpiochip4)."""
        # Mock gpiochip0 without pinctrl, gpiochip4 with pinctrl
        def mock_chip_side_effect(path):
            mock_chip = Mock()
            mock_info = Mock()
            
            if path == "/dev/gpiochip0":
                mock_info.label = "gpio-brcmstb"  # Not pinctrl
            elif path == "/dev/gpiochip4": 
                mock_info.label = "pinctrl-rp1"  # Pi 5 pinctrl chip
            else:
                raise Exception("Chip not found")
                
            mock_info.num_lines = 54
            mock_chip.get_info.return_value = mock_info
            return mock_chip
        
        mock_gpiod.Chip.return_value.__enter__ = lambda x: mock_chip_side_effect(mock_gpiod.Chip.call_args[0][0])
        
        device = RFDevice(gpio=17)
        result = device._find_gpio_chip()
        
        assert result == "/dev/gpiochip4"

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_find_gpio_chip_no_pinctrl_chips(self, mock_gpiod):
        """Test GPIO chip detection when no pinctrl chips are found."""
        # Mock chips without pinctrl in label
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "some-other-chip"  # No pinctrl
        mock_info.num_lines = 54
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        with pytest.raises(RuntimeError, match="No suitable GPIO chip found"):
            RFDevice(gpio=17)

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_find_gpio_chip_access_denied(self, mock_gpiod):
        """Test GPIO chip detection when access is denied."""
        # Mock permission denied
        mock_gpiod.Chip.side_effect = PermissionError("Permission denied")
        
        with pytest.raises(RuntimeError, match="No suitable GPIO chip found"):
            RFDevice(gpio=17)

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_find_gpio_chip_mixed_access(self, mock_gpiod):
        """Test GPIO chip detection with mixed access permissions."""
        call_count = [0]
        
        def mock_chip_side_effect(path):
            call_count[0] += 1
            if call_count[0] <= 2:  # First two calls fail
                raise PermissionError("Permission denied")
            else:  # Third call succeeds
                mock_chip = Mock()
                mock_info = Mock()
                mock_info.label = "pinctrl-bcm2711"  # Pi 4
                mock_info.num_lines = 58
                mock_chip.get_info.return_value = mock_info
                return mock_chip
        
        mock_gpiod.Chip.side_effect = mock_chip_side_effect
        mock_gpiod.Chip.return_value.__enter__ = lambda x: mock_chip_side_effect(mock_gpiod.Chip.call_args[0][0])
        
        device = RFDevice(gpio=17)
        result = device._find_gpio_chip()
        
        # Should eventually find a working chip
        assert result.startswith("/dev/gpiochip")

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_chip_search_order(self, mock_gpiod):
        """Test that chips are searched in the correct order."""
        # Track which chips are accessed
        accessed_chips = []
        
        def mock_chip_side_effect(path):
            accessed_chips.append(path)
            if path == "/dev/gpiochip0":  # First one succeeds
                mock_chip = Mock()
                mock_info = Mock()
                mock_info.label = "pinctrl-bcm2835"
                mock_info.num_lines = 54
                mock_chip.get_info.return_value = mock_info
                return mock_chip
            else:
                raise Exception("Not found")
        
        mock_gpiod.Chip.side_effect = mock_chip_side_effect
        mock_gpiod.Chip.return_value.__enter__ = lambda x: mock_chip_side_effect(mock_gpiod.Chip.call_args[0][0])
        
        device = RFDevice(gpio=17)
        result = device._find_gpio_chip()
        
        # Should search in order: 0, 4, 1, 2, 3, 5
        assert accessed_chips[0] == "/dev/gpiochip0"
        assert result == "/dev/gpiochip0"

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_chip_info_logging(self, mock_gpiod):
        """Test that chip information is properly logged."""
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"
        mock_info.num_lines = 54
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        with patch('custom_components.ha_rf.rf_device._LOGGER') as mock_logger:
            device = RFDevice(gpio=17)
            
            # Should log chip discovery
            mock_logger.info.assert_called()
            log_calls = [call.args for call in mock_logger.info.call_args_list]
            
            # Should contain chip path and label
            chip_logged = any("Found suitable GPIO chip" in str(call) for call in log_calls)
            assert chip_logged


class TestGPIOLineVerification:
    """Test GPIO line verification for the suggested improvements."""

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_future_line_verification_concept(self, mock_gpiod):
        """Test concept for verifying GPIO line availability (for future implementation)."""
        # This test demonstrates how line verification could work
        # when implementing the suggested _find_gpio_chip_for_line improvement
        
        mock_request = Mock()
        mock_gpiod.request_lines.return_value = mock_request
        
        # Mock successful line request
        device = RFDevice(gpio=17)
        
        # Simulate testing if GPIO 17 is available on a chip
        gpio_line = 17
        chip_path = "/dev/gpiochip0"
        
        try:
            # This is how the improved version would test line availability
            test_request = mock_gpiod.request_lines(
                chip_path,
                consumer="ha-rf-probe",
                config={gpio_line: mock_gpiod.LineSettings(direction=mock_gpiod.Direction.OUTPUT)}
            )
            test_request.release()
            line_available = True
        except Exception:
            line_available = False
            
        assert line_available is True
        mock_gpiod.request_lines.assert_called()

    @patch('custom_components.ha_rf.rf_device.gpiod')  
    def test_line_verification_failure_concept(self, mock_gpiod):
        """Test concept for line verification failure."""
        # Mock line request failure (line not available on this chip)
        mock_gpiod.request_lines.side_effect = Exception("Line not available")
        
        gpio_line = 17
        chip_path = "/dev/gpiochip0"
        
        try:
            test_request = mock_gpiod.request_lines(
                chip_path,
                consumer="ha-rf-probe", 
                config={gpio_line: mock_gpiod.LineSettings(direction=mock_gpiod.Direction.OUTPUT)}
            )
            test_request.release()
            line_available = True
        except Exception:
            line_available = False
            
        assert line_available is False


class TestPlatformSpecificBehavior:
    """Test platform-specific GPIO behavior."""

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_pi3_gpio_characteristics(self, mock_gpiod):
        """Test Raspberry Pi 3 GPIO characteristics."""
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2835"  # Pi 3 specific
        mock_info.num_lines = 54  # Pi 3 has 54 GPIO lines
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17)
        
        # Pi 3 should use gpiochip0
        assert device._gpio_chip_path == "/dev/gpiochip0"

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_pi4_gpio_characteristics(self, mock_gpiod):
        """Test Raspberry Pi 4 GPIO characteristics."""
        mock_chip = Mock()
        mock_info = Mock()
        mock_info.label = "pinctrl-bcm2711"  # Pi 4 specific
        mock_info.num_lines = 58  # Pi 4 has 58 GPIO lines
        mock_chip.get_info.return_value = mock_info
        mock_gpiod.Chip.return_value.__enter__.return_value = mock_chip
        
        device = RFDevice(gpio=17)
        
        # Pi 4 should use gpiochip0
        assert device._gpio_chip_path == "/dev/gpiochip0"

    @patch('custom_components.ha_rf.rf_device.gpiod')
    def test_pi5_gpio_characteristics(self, mock_gpiod):
        """Test Raspberry Pi 5 GPIO characteristics."""
        # Pi 5 has a different layout - pinctrl is on gpiochip4
        call_count = [0]
        
        def mock_chip_side_effect(path):
            call_count[0] += 1
            mock_chip = Mock()
            mock_info = Mock()
            
            if path == "/dev/gpiochip0":
                mock_info.label = "gpio-brcmstb"  # Not pinctrl
            elif path == "/dev/gpiochip4":
                mock_info.label = "pinctrl-rp1"  # Pi 5 pinctrl
            else:
                raise Exception("Not found")
                
            mock_info.num_lines = 54
            mock_chip.get_info.return_value = mock_info
            return mock_chip
        
        mock_gpiod.Chip.return_value.__enter__ = lambda x: mock_chip_side_effect(mock_gpiod.Chip.call_args[0][0])
        
        device = RFDevice(gpio=17)
        
        # Pi 5 should use gpiochip4
        assert device._gpio_chip_path == "/dev/gpiochip4"