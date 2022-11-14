from logging import getLogger
from struct import pack

import voluptuous as vol
from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform, event, selector, service
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MESHCore, MESHEntity

PATTERN_BLINK = "Blink"
PATTERN_FIREFLY = "Firefly"

_LED_PATTERNS = {
    PATTERN_BLINK: 1,
    PATTERN_FIREFLY: 2,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    platform = entity_platform.async_get_current_platform()
    core: MESHCore = hass.data[entry.entry_id]
    name: str = entry.data[CONF_NAME]
    async_add_entities([
        MESHStatusLedEntity(core, name),
    ])
    platform.async_register_entity_service("status_turn_on", vol.Schema({
        vol.Required("red"): cv.boolean,
        vol.Required("green"): cv.boolean,
        vol.Required("blue"): cv.boolean,
    }), _service_status_turn_on)
    platform.async_register_entity_service(
        "status_turn_off", {}, _service_status_turn_off)
    if name.startswith("MESH-100LE"):
        async_add_entities([
            MESHLedEntity(core, name),
        ])
        platform.async_register_entity_service("led_turn_on", vol.Schema({
            vol.Required("color"): selector.ColorRGBSelector(),
            vol.Optional("duration"): vol.Range(0, 0xFFFF),
            vol.Optional("on_cycle"): vol.Range(0, 0xFFFF),
            vol.Optional("off_cycle"): vol.Range(0, 0xFFFF),
            vol.Optional("pattern"): vol.In(list(_LED_PATTERNS.keys())),
        }), _service_led_turn_on)


class MESHLedEntity(MESHEntity, LightEntity):
    _attr_brightness = 255
    _attr_color_mode = ColorMode.RGB
    _attr_device_class = "sony_mesh__led"
    _attr_icon = "mdi:alarm-light"
    _attr_is_on = False
    _attr_rgb_color = (255, 255, 255)
    _attr_supported_color_modes = {ColorMode.RGB}
    __duration_cancel = None

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = name

    async def async_turn_off(self, **kwargs):
        data = pack('<BBBBBBBHHHB',
                    1, 0,
                    0, 0, 0, 0, 0,
                    0, 0, 0, 1)
        await self.core.send_cmd(data)
        if self.__duration_cancel:
            self.__duration_cancel()
            self.__duration_cancel = None
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_turn_on(self, brightness: int | None = None, rgb_color: tuple[int, int, int] | None = None, **kwargs):
        if brightness is not None:
            self._attr_brightness = brightness
        if rgb_color is not None:
            self._attr_rgb_color = rgb_color

        await self._set_led()

    async def async_will_remove_from_hass(self):
        if self.__duration_cancel:
            self.__duration_cancel()
            self.__duration_cancel = None
        return await super().async_will_remove_from_hass()

    def _connect_changed(self, connected: bool):
        self._attr_is_on = False
        super()._connect_changed(connected)

    async def _set_led(self, duration=0xFFFF, on=0xFFFF, off=0, pattern=1):
        brightness = self.brightness or 0
        rgb_color = self.rgb_color or (0, 0, 0)
        red = rgb_color[0] * brightness * 127 / 255 / 255
        green = rgb_color[1] * brightness * 127 / 255 / 255
        blue = rgb_color[2] * brightness * 127 / 255 / 255
        data = pack('<BBBBBBBHHHB',
                    1, 0,
                    round(red), 0, round(green), 0, round(blue),
                    duration, on, off, pattern)
        await self.core.send_cmd(data)
        self._attr_is_on = duration > 0 and on > 0
        if self.__duration_cancel:
            self.__duration_cancel()
        if self._attr_is_on:
            self.__duration_cancel = event.async_call_later(
                self.hass, duration / 1000.0, self.__duration_end)
        else:
            self.__duration_cancel = None
        self.async_write_ha_state()

    def __duration_end(self, *args):
        self._attr_is_on = False
        self.async_write_ha_state()


class MESHStatusLedEntity(MESHEntity, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_device_class = "sony_mesh__status"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:bluetooth-transfer"
    _attr_name = "Status LED"
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, core: MESHCore, name: str):
        super().__init__(core)
        self._attr_unique_id = f"{name}-status-led"

    async def async_turn_off(self, **kwargs):
        await self.core.send(b"\x00\x04\x01\x05")
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        await self.core.send(b"\x00\x04\x00\x04")
        self._attr_is_on = True
        self.async_write_ha_state()

    def _connect_changed(self, connected: bool):
        self._attr_is_on = None
        super()._connect_changed(connected)


async def _service_status_turn_off(entity: MESHEntity, call: service.ServiceCall):
    if type(entity) is not MESHStatusLedEntity:
        return
    await entity.core.send(b"\x00\x00\x00\x00\x00\x00\x00")


async def _service_status_turn_on(entity: MESHEntity, call: service.ServiceCall):
    if type(entity) is not MESHStatusLedEntity:
        return
    getLogger(__name__).warn(call.data)
    await entity.core.send_cmd(pack(
        "<BBBBBB",
        0, 0,
        1 if call.data["red"] else 0,
        1 if call.data["green"] else 0,
        1 if call.data["blue"] else 0,
        1,
    ))


async def _service_led_turn_on(entity: MESHEntity, call: service.ServiceCall):
    if type(entity) is not MESHLedEntity:
        return
    entity._attr_rgb_color = call.data["color"]
    entity._attr_brightness = 255
    await entity._set_led(
        call.data.get("duration", 0xFFFF),
        call.data.get("on_cycle", 0xFFFF),
        call.data.get("off_cycle", 0),
        _LED_PATTERNS.get(call.data.get("pattern", ""), 1),
    )
