from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MESHCore, MESHEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    core: MESHCore = hass.data[entry.entry_id]
    async_add_entities([
        MESHPowerEntity(core, entry.data[CONF_NAME]),
    ])


class MESHPowerEntity(MESHEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:power"
    _attr_is_on = True
    _attr_name = "Power"

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-power"

    async def async_turn_off(self, **kwargs):
        await self.core.send(b"\x00\x05\x00\x05")

    async def async_turn_on(self, **kwargs):
        pass
