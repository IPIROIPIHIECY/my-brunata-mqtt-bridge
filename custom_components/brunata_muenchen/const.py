from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfVolume

DOMAIN = "brunata_muenchen"

# Mapping der SAP-Präfixe auf HA-Klassen
METER_MAPPING = {
    "HZ": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.MEGAWATT_HOUR,
        "name": "Heizung",
    },
    "WW": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.CUBIC_METERS,
        "name": "Warmwasser",
    },
    "KW": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.CUBIC_METERS,
        "name": "Kaltwasser",
    },
}