from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MESHGP, MESHCore, MESHEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    core: MESHCore = hass.data[entry.entry_id]
    name: str = entry.data[CONF_NAME]
    async_add_entities([
        MESHPowerEntity(core, name),
    ])
    if type(core) is MESHGP:
        async_add_entities([
            MESHDigitalOutputEntity(core, name, 1),
            MESHDigitalOutputEntity(core, name, 2),
            MESHDigitalOutputEntity(core, name, 3),
            MESHPowerOutputEntity(core, name),
        ])


class MESHOutputEntity(MESHEntity, SwitchEntity):
    core: MESHGP
    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_is_on = False


class MESHDigitalOutputEntity(MESHOutputEntity):
    def __init__(self, core: MESHGP, name: str, pin: int):
        super().__init__(core)
        self.pin = pin
        self._attr_name = f"DOUT{pin}"
        self._attr_unique_id = f"{name}-dout{pin}"

    @property
    def is_on(self):
        return self.core.dout[self.pin]

    async def async_turn_off(self, **kwargs):
        self.core.dout[self.pin] = False
        await self.core.send_config()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        self.core.dout[self.pin] = True
        await self.core.send_config()
        self.async_write_ha_state()


class MESHPowerOutputEntity(MESHOutputEntity):
    _attr_name = "VOUT"

    def __init__(self, core: MESHGP, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-vout"

    @property
    def is_on(self):
        return self.core.power

    async def async_turn_off(self, **kwargs):
        self.core.power = False
        await self.core.send_config()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        self.core.power = True
        await self.core.send_config()
        self.async_write_ha_state()


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
