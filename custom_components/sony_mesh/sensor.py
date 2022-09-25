from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, LIGHT_LUX, PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MESHCore, MESHEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    core: MESHCore = hass.data[entry.entry_id]
    name: str = entry.data[CONF_NAME]
    async_add_entities([
        MESHBatteryEntity(core, name),
    ])
    if name.startswith("MESH-100AC"):
        async_add_entities([
            MESHOrientationEntity(core, name),
        ])
    elif name.startswith("MESH-100PA"):
        async_add_entities([
            MESHIlluminanceEntity(core, name),
            MESHProximityEntity(core, name),
        ])
    elif name.startswith("MESH-100TH"):
        async_add_entities([
            MESHHumidityEntity(core, name),
            MESHTempertureEntity(core, name),
        ])


class MESHBatteryEntity(MESHEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Battery"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-battery"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.battery, self.__battery_changed)

    def __battery_changed(self, value: int):
        self._attr_native_value = value
        self.async_write_ha_state()


class MESHHumidityEntity(MESHEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_name = "Humidity"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-humidity"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.received, self.__received)

    def _connect_changed(self, connected: bool):
        self._attr_native_value = None
        super()._connect_changed(connected)

    def __received(self, data: bytes):
        if data[:2] != b"\x01\x00":
            return
        self._attr_native_value = int.from_bytes(data[6:8], "little")
        self.async_write_ha_state()


class MESHIlluminanceEntity(MESHEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_name = "Illuminance"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = LIGHT_LUX

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-illuminance"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.received, self.__received)

    def _connect_changed(self, connected: bool):
        self._attr_native_value = None
        super()._connect_changed(connected)

    def __received(self, data: bytes):
        if data[:2] != b"\x01\x00":
            return
        self._attr_native_value = int.from_bytes(data[6:8], "little") * 10
        self.async_write_ha_state()


ORIENTATIONS = {
    1: "left",
    2: "bottom",
    3: "front",
    4: "back",
    5: "top",
    6: "right",
}


class MESHOrientationEntity(MESHEntity, SensorEntity):
    _attr_name = "Orientation"
    _attr_device_class = "sony_mesh__orientation"

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-orientation"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.received, self.__received)

    def _connect_changed(self, connected: bool):
        self._attr_native_value = None
        super()._connect_changed(connected)

    def __received(self, data: bytes):
        if data[:2] != b"\x01\x03":
            return
        self._attr_native_value = ORIENTATIONS.get(data[2])
        self.async_write_ha_state()


class MESHProximityEntity(MESHEntity, SensorEntity):
    _attr_name = "Proximity"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-proximity"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.received, self.__received)

    def _connect_changed(self, connected: bool):
        self._attr_native_value = None
        super()._connect_changed(connected)

    def __received(self, data: bytes):
        if data[:2] != b"\x01\x00":
            return
        self._attr_native_value = int.from_bytes(data[4:6], "little")
        self.async_write_ha_state()


class MESHTempertureEntity(MESHEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_name = "Temperture"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = TEMP_CELSIUS

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-temperture"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.received, self.__received)

    def _connect_changed(self, connected: bool):
        self._attr_native_value = None
        super()._connect_changed(connected)

    def __received(self, data: bytes):
        if data[:2] != b"\x01\x00":
            return
        self._attr_native_value = int.from_bytes(
            data[4:6], "little", signed=True) / 10
        self.async_write_ha_state()
