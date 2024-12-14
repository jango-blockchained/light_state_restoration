# Light State Restoration

## Overview

This Home Assistant custom component provides functionality to restore light states after a system restart or power outage.

## Features

- Automatically saves light states before system shutdown
- Restores light states on system startup
- Configurable restoration behavior
- Supports multiple light entities

## Installation

1. Copy the `light_state_restoration` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Configure the component in your `configuration.yaml`

## Configuration Example

```yaml
light_state_restoration:
  enabled: true
  entities:
    - light.living_room
    - light.kitchen
```

## Requirements

- Home Assistant 2023.x or later
- Compatible with most light entities

## Contributions

Contributions and bug reports are welcome on the GitHub repository.

## License

MIT License
