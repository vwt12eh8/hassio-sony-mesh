from homeassistant.components.binary_sensor import (BinarySensorDeviceClass,
                                                    BinarySensorEntity)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MESHCore, MESHEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    core: MESHCore = hass.data[entry.entry_id]
    name: str = entry.data[CONF_NAME]
    if name.startswith("MESH-100MD"):
        async_add_entities([
            MESHMotionEntity(core, name),
        ])


class MESHMotionEntity(MESHEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = name

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.received, self.__received)

    def _connect_changed(self, connected: bool):
        self._attr_is_on = None
        super()._connect_changed(connected)

    def __received(self, data: bytes):
        if data[:2] != b"\x01\x00":
            return
        if data[3] == 1:
            self._attr_is_on = True
        elif data[3] == 2:
            self._attr_is_on = False
        else:
            self._attr_is_on = None
        self.async_write_ha_state()
