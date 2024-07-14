"""Constants for the Scenario IFSEI integration."""

from typing import Final

DOMAIN = "scenario"

CONF_CONTROLLER_UNIQUE_ID = "conf_controller_unique_id"

MANUFACTURER = "Scenario Automation"
CONTROLLER_ENTRY = "ifsei"
LIGHTS_ENTRY = "lights"
COVERS_ENTRY = "covers"

DEFAULT_PORT = 28000
MIN_PORT_NUMBER = 0
MAX_PORT_NUMBER = 65535
DEFAULT_IP = "192.168.15.22"
YAML_DEVICES = "scenario_device_config.yaml"

IFSEI_CONF_RECONNECT: Final = "reconnect"
IFSEI_CONF_RECONNECT_DELAY: Final = "reconnect_delay"

DEFAULT_RECONNECT_DELAY = 30
DEFAULT_RECONNECT = True
DEFAULT_SEND_DELAY = 0.2
