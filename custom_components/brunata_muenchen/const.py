"""Constants for the Brunata München integration."""

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfVolume

DOMAIN = "brunata_muenchen"

# Scan interval settings
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = timedelta(hours=12)

# Mapping der SAP-Präfixe auf HA-Klassen
METER_MAPPING = {
    "HZ": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "name": "Heizung",
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "WW": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.CUBIC_METERS,
        "name": "Warmwasser",
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "KW": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.CUBIC_METERS,
        "name": "Kaltwasser",
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
}

# Sensor-Typen die erstellt werden
SENSOR_TYPE_METER = "meter"
SENSOR_TYPE_MONTHLY = "monthly"
SENSOR_TYPE_CUMULATIVE = "cumulative"