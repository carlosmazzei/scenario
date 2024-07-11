# Integration Blueprint

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]
[![Community Forum][forum-shield]][forum]

_Integration to integrate with Scenario Automation._

**This integration will set up the following platforms.**

| Platform | Description                                                      |
| -------- | ---------------------------------------------------------------- |
| `light`  | Integrate with lights controlled by IFSEI                        |
| `cover`  | Integrate with covers and shades controlled by scenes with IFSEI |

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `scenario`.
1. Download _all_ the files from the `custom_components/scenario/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Integration blueprint"

## Configuration is done in the UI

<!---->

## Contributions are welcome

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[commits-shield]: https://img.shields.io/github/commit-activity/y/carlosmazzei/scenario.svg?style=for-the-badge
[commits]: https://github.com/carlosmazzei/scenario/commits/main
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/carlosmazzei/scenario.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Carlos%20Mazzei-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/carlosmazzei/scenario.svg?style=for-the-badge
[releases]: https://github.com/carlosmazzei/scenario/releases
