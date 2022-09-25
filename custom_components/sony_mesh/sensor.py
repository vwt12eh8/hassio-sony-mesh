from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, PERCENTAGE
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
