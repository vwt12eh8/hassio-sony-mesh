from homeassistant.components.number import NumberEntity, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_NAME, ELECTRIC_POTENTIAL_VOLT,
                                 TIME_MILLISECONDS)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MESHGP, MESHMD, MESHCore, MESHEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    core: MESHCore = hass.data[entry.entry_id]
    name: str = entry.data[CONF_NAME]
    if name.startswith("MESH-100GP"):
        async_add_entities([
            MESHAnalogOutputEntity(core, name),
        ])
    elif name.startswith("MESH-100MD"):
        async_add_entities([
            MESHMotionDelayEntity(core, name),
            MESHMotionHoldEntity(core, name),
        ])


class MESHAnalogOutputEntity(MESHEntity, NumberEntity):
    core: MESHGP
    _attr_device_class = "voltage"
    _attr_icon = "mdi:square-wave"
    _attr_name = "PWM"
    _attr_native_max_value = 3.0
    _attr_native_min_value = 0.0
    _attr_native_step = 0.01
    _attr_native_unit_of_measurement = ELECTRIC_POTENTIAL_VOLT

    @property
    def native_value(self):
        return round(self.core.aout * 3.0 / 255, 2)

    async def set_native_value(self, value: float):
        self.core.aout = round(value * 255 / 3.0)
        await self.core.send_config()
        self.async_write_ha_state()


class MESHMotionEntity(MESHEntity, RestoreNumber):
    core: MESHMD
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-settings"
    _attr_native_max_value = 60000
    _attr_native_min_value = 500
    _attr_native_unit_of_measurement = TIME_MILLISECONDS


class MESHMotionDelayEntity(MESHMotionEntity):
    def __init__(self, core: MESHMD, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-delay"

    @property
    def native_value(self):
        return self.core.delay_time

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if data := await self.async_get_last_number_data():
            self.core.delay_time = int(data.native_value)
            await self.core.send_config()

    async def async_set_native_value(self, value: float):
        self.core.delay_time = int(value)
        await self.core.send_config()
        self.async_write_ha_state()


class MESHMotionHoldEntity(MESHMotionEntity):
    _attr_native_min_value = 200

    def __init__(self, core: MESHMD, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-hold"

    @property
    def native_value(self):
        return self.core.hold_time

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if data := await self.async_get_last_number_data():
            self.core.hold_time = int(data.native_value)
            await self.core.send_config()

    async def async_set_native_value(self, value: float):
        self.core.hold_time = int(value)
        await self.core.send_config()
        self.async_write_ha_state()
