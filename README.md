# Scenario Automation Integration

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]
[![Community Forum][forum-shield]][forum]
![Codecov][coverage-shield]


A Home Assistant custom integration to monitor and control devices connected using Scenario Automation IFSEI Classic.

**This integration will set up the following platforms:**

| Platform | Description                      |
| -------- | -------------------------------- |
| `light`  | Common, dimmable, and RGB lights |
| `cover`  | Covers connected through scenes  |

## Installation

You can install this component in two ways: via [HACS](https://github.com/hacs/integration) or manually.

### Prerequisites

You must have a YAML configuration file to set up the devices. The default path and filename for this file is `<ha_configuration_path>/scenario_device_config.yaml`. You can find an example in [`config/scenario_device_config.yaml`](config/scenario_device_config.yaml).

This file has three optional sections:

* Zones
* Lights
* Shades

**Each section has its own requirements. Please refer to [pyscenario](https://github.com/carlosmazzei/pyscenario) for more information about each.**

### Option A: Installing via HACS

If you have HACS installed, follow these steps:

1. Go to the HACS menu.
2. Select the three dots and choose "Custom Repositories".
3. Copy and paste the URL: `https://github.com/carlosmazzei/scenario`.
4. Select "Integration" in the Category dropdown.
5. Reboot Home Assistant.

### Option B: Manual Installation (custom_component)

Prerequisite: SSH into your server. [Home Assistant Add-on: SSH server](https://github.com/home-assistant/hassio-addons/tree/master/ssh)

1. Clone the repository: `git clone https://github.com/carlosmazzei/scenario`.
2. If it doesn't exist, create a `custom_components` directory where your `configuration.yaml` file resides. This is usually in the config directory of Home Assistant: `mkdir ~/.homeassistant/custom_components`.
3. Copy the `scenario` directory within the `custom_components` directory of your Home Assistant installation: `cp -R scenario/custom_components/scenario/ ~/.homeassistant/custom_components`.
4. (Optional) Delete the git repository: `rm -Rf scenario/`.

    After a correct installation, your configuration directory should look like the following:

    ```shell
    └── ...
    └── configuration.yaml
    └── secrets.yaml
    └── custom_components
        └── scenario
            └── __init__.py
            └── config_flow.py
            └── const.py
            └── ...
    ```

5. Reboot Home Assistant.

## Component Configuration

Once the component has been installed, you need to configure it using the web interface:

1. Go to "Settings -> Devices & Services".
2. Perform a hard refresh in your browser (Shift + Reload).
3. Click "+ Add Integration".
4. Search for "Scenario Automation (IFSEI Classic)".
5. Select the integration and follow the setup workflow.

**Important**: This integration uses [pyscenario](https://github.com/carlosmazzei/pyscenario) to connect to the IFSEI device, and currently only the TCP protocol is implemented.

### Options Flow

This component implements an options flow with three parameters that can be configured:

| Parameter       | Description                                                             | Default Value |
| --------------- | ----------------------------------------------------------------------- | ------------- |
| Send delay      | Set the delay between messages. Usually, IFSEI needs at least 200ms     | 200 ms        |
| Reconnect       | Boolean to set if reconnection will start after a failed first connect. | True          |
| Reconnect Delay | Set the reconnect delay between retries                                 | 30s           |

**Important**: if reconnect is set to True it will only try to reconnect at the first failed connection, since the reconnection task will start if it connects succesfully and fails after.

## Usage

After installation and configuration, you can start using the integration to control and monitor your connected devices. You will be able to manage lights and covers directly from the Home Assistant interface. Use the automation capabilities of Home Assistant to create complex scenarios and routines involving your devices.

## Troubleshooting

If you encounter any issues, ensure that:

1. Your YAML configuration file is correctly formatted and located in the specified path.
2. Your Home Assistant instance is up to date.
3. The devices are properly connected and reachable over the network.

Refer to the [pyscenario documentation](https://github.com/carlosmazzei/pyscenario) for detailed information on device requirements and configurations.

## Contributions Are Welcome

If you want to contribute to this project, please read the [Contribution Guidelines](CONTRIBUTING.md).

***

[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/carlosmazzei/scenario.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Carlos%20Mazzei-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/carlosmazzei/scenario.svg?style=for-the-badge
[releases]: https://github.com/carlosmazzei/scenario/releases
[coverage-shield]: https://img.shields.io/codecov/c/github/carlosmazzei/scenario?style=for-the-badge
