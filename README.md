# Home Assistant RF Integration

**A modern Home Assistant custom integration for controlling 433/315MHz RF devices via Raspberry Pi GPIO.**

This integration provides a `ha_rf` switch platform that allows you to control devices over 433/315MHz LPD/SRD signals with generic low-cost GPIO RF modules on a [Raspberry Pi](https://www.raspberrypi.org/).

## Features

- **Python 3.13 Ready**: Updated for modern Python versions and Home Assistant Core 2025.8+
- **Embedded RF Module**: No external rpi-rf dependency - all RF functionality built-in
- **Modern GPIO Support**: Uses rpi-lgpio for better compatibility
- **Unique Entity IDs**: Full Home Assistant entity customization support
- **Multiple Protocols**: Support for various RF protocols and configurations

## Requirements

- Home Assistant Core 2025.8.0 or later
- Raspberry Pi with GPIO access
- Python 3.12+ (recommended 3.13+)
- 433/315MHz RF transmitter module

## Installation

### HACS (Recommended)

The recommended way to install `ha_rf` is through [HACS](https://hacs.xyz/).

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL
5. Install the "Home Assistant RF" integration

### Manual Installation

1. Download the latest release
2. Copy the `ha_rf` folder to your Home Assistant's `custom_components` folder
3. The folder structure should be: `custom_components/ha_rf/`
4. Restart Home Assistant

## Configuration

Add the following to your `configuration.yaml`:

```yaml
# Example configuration.yaml entry
switch:
  - platform: ha_rf
    gpio: 17
    switches:
      bedroom_light:
        code_on: 1234567
        code_off: 1234568
        unique_id: "bedroom_light_rf"
      ambilight:
        pulselength: 200
        code_on: 987654
        code_off: 133742
        length: 24
      living_room_light:
        protocol: 5
        code_on: 654321,565874,233555,149874
        code_off: 654320,565873,233554,149873
        signal_repetitions: 15
```

### Configuration Options

| Key                  | Required | Default | Type    | Description                                                                                                                   |
| -------------------- | -------- | ------- | ------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `gpio`               | yes      |         | integer | GPIO pin number for the RF transmitter data line                                                                             |
| `switches`           | yes      |         | map     | Dictionary of switch configurations                                                                                           |
| `code_on`            | yes      |         | integer/list | Decimal code(s) to switch the device on. Use commas for multiple codes: `123,456,789`                                    |
| `code_off`           | yes      |         | integer/list | Decimal code(s) to switch the device off. Use commas for multiple codes: `123,456,789`                                   |
| `protocol`           | no       | `1`     | integer | RF Protocol (1-6)                                                                                                            |
| `pulselength`        | no       | protocol default | integer | Pulse length in microseconds                                                                                    |
| `signal_repetitions` | no       | `10`    | integer | Number of times to repeat transmission                                                                                        |
| `length`             | no       | `24`    | integer | Code length in bits                                                                                                          |
| `unique_id`          | no       | auto-generated | string | Unique identifier for the entity. Auto-generated from codes if not specified                                          |

## RF Protocols

The integration supports multiple RF protocols:

- **Protocol 1** (default): 350μs pulse length
- **Protocol 2**: 650μs pulse length  
- **Protocol 3**: 100μs pulse length
- **Protocol 4**: 380μs pulse length
- **Protocol 5**: 500μs pulse length
- **Protocol 6**: 200μs pulse length (Nexa format)

## Entity Customization

Thanks to unique ID support, you can fully customize your switch entities in Home Assistant:

- Custom icons and names
- Assign to areas
- Modify entity IDs
- Set device classes

To customize: Go to **Settings** → **Devices & Services** → **Entities**, find your switch, and click on it to access customization options.

### Important Notes on Unique IDs

- If not manually set, unique IDs are auto-generated from `code_on` and `code_off` values
- Changing RF codes will create a new entity (old entity becomes "restored")
- Changing the `unique_id` in configuration will also create a new entity
- It's safe to remove old/restored entities, but customizations will be lost

## Hardware Setup

1. Connect your 433/315MHz RF transmitter to your Raspberry Pi:
   - **VCC** → 3.3V or 5V
   - **GND** → Ground  
   - **DATA** → GPIO pin (specified in configuration)

2. Ensure your Home Assistant installation has GPIO access (typically requires running as root or in the `gpio` group)

## Troubleshooting

### Common Issues

- **ImportError about GPIO**: Ensure you're running on a Raspberry Pi with GPIO support
- **Permission denied on GPIO**: Home Assistant needs GPIO access permissions
- **Device not responding**: Check wiring and RF codes
- **Entity not appearing**: Verify configuration syntax and restart Home Assistant

### Getting RF Codes

You can capture RF codes using tools like:
- **Flipper Zero** - Use the Sub-GHz app to capture and analyze RF signals
- [rc-switch](https://github.com/sui77/rc-switch) with Arduino
- RTL-SDR dongles with software like rtl_433

### Hardware Modules

You can purchase 433MHz RF modules from various suppliers:
- [433MHz RF Wireless Transmitter Receiver Kit FS1000A](https://zaitronics.com.au/products/433mhz-rf-wireless-transmitter-receiver-kit-fs1000a) - Example kit from Zaitronics

## Development

This integration uses modern Python development practices:

```bash
# Setup development environment
uv sync

# Run linting and formatting  
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy custom_components/
```

## Compatibility

- **Home Assistant**: 2025.8.0+
- **Python**: 3.12+ (recommended 3.13+)
- **Hardware**: Raspberry Pi with GPIO
- **RF Modules**: 433MHz/315MHz transmitters

## Migration from Original rpi_rf

If migrating from the original `rpi_rf` integration:

1. Change platform name from `rpi_rf` to `ha_rf` in configuration
2. Update any automations referencing the old entity names
3. The RF codes and functionality remain the same

## License

This project is licensed under the same terms as the original Home Assistant rpi_rf integration.

## Credits

- Based on the original Home Assistant `rpi_rf` integration
- Forked from [@markvader's ha-rpi_rf](https://github.com/markvader/ha-rpi_rf) project
- RF functionality inspired by the [rpi-rf](https://pypi.org/project/rpi-rf/) Python module
- Entity customization improvements by [@oskargert](https://github.com/oskargert)