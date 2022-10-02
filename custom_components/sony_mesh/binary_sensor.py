from struct import pack

from homeassistant.components.binary_sensor import (BinarySensorDeviceClass,
                                                    BinarySensorEntity)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MESHGP, MESHCore, MESHEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    core: MESHCore = hass.data[entry.entry_id]
    name: str = entry.data[CONF_NAME]
    if name.startswith("MESH-100GP"):
        async_add_entities([
            MESHDigitalInputEntity(core, name, 1),
            MESHDigitalInputEntity(core, name, 2),
            MESHDigitalInputEntity(core, name, 3),
        ])
    elif name.startswith("MESH-100MD"):
        async_add_entities([
            MESHMotionEntity(core, name),
        ])


class MESHBinarySensorEntity(MESHEntity, BinarySensorEntity):
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.received, self._received)

    def _connect_changed(self, connected: bool):
        self._attr_is_on = None
        super()._connect_changed(connected)


class MESHDigitalInputEntity(MESHBinarySensorEntity):
    core: MESHGP
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(self, core: MESHCore, name: str, pin: int):
        super().__init__(core)
        self.pin = pin
        self._attr_unique_id = f"{name}-din{pin}"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.core.din[self.pin] = True

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()
        self.core.din[self.pin] = False

    def _connect_changed(self, connected: bool):
        if connected:
            self.hass.loop.create_task(self.core.send_cmd(
                pack("<HHHH", 1, 2, 0, self.pin - 1)))
        if self._attr_available:
            self._attr_available = False
            self.async_write_ha_state()

    def _received(self, data: bytes):
        if data[:2] == b"\x01\x00":
            if data[2] != self.pin - 1:
                return
            self._attr_is_on = data[3] == 1
        elif data[:2] == b"\x01\x02":
            if data[3] != self.pin - 1:
                return
            self._attr_is_on = data[4] == 0
        else:
            return
        self._attr_available = True
        self.async_write_ha_state()


class MESHMotionEntity(MESHBinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = name

    def _received(self, data: bytes):
        if data[:2] != b"\x01\x00":
            return
        if data[3] == 1:
            self._attr_is_on = True
        elif data[3] == 2:
            self._attr_is_on = False
        else:
            self._attr_is_on = None
        self.async_write_ha_state()
