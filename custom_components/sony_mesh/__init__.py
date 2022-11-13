from __future__ import annotations

from asyncio import Future, create_task, wait_for
from logging import getLogger
from struct import pack
from typing import Callable, Iterable

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (BluetoothChange,
                                                BluetoothServiceInfoBleak)
from homeassistant.components.bluetooth.models import HaBleakClientWrapper
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_ADDRESS, CONF_DEVICE_ID, CONF_NAME,
                                 CONF_TYPE, Platform)
from homeassistant.core import EventOrigin, HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo, Entity
from reactivex import Observable, Subject
from reactivex import operators as ops
from reactivex.subject.behaviorsubject import BehaviorSubject

DOMAIN = "sony_mesh"

CORE_INDICATE_UUID = ('72c90005-57a9-4d40-b746-534e22ec9f9e')
CORE_NOTIFY_UUID = ('72c90003-57a9-4d40-b746-534e22ec9f9e')
CORE_WRITE_UUID = ('72c90004-57a9-4d40-b746-534e22ec9f9e')

CMD_FEATURE_ENABLE = b"\x00\x02\x01\x03"

_PLATFORMS = {
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
}


BUTTON_PUSH_TYPES = {
    1: "single",
    2: "long",
    3: "double",
}

_LOGGER = getLogger(__name__)


class MESHCore:
    client = None
    info = None
    __task = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.name = entry.data[CONF_NAME]
        self.entry_id = entry.entry_id
        self.dr = device_registry.async_get(hass)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.name)},
            manufacturer="Sony",
            model=self.name[:10],
            name=self.name,
        )
        self.received = Subject[bytes]()
        self.battery = BehaviorSubject[int | None](None)
        self.connect_changed = BehaviorSubject[bool](False)

    def close(self):
        self.client = None
        if self.__task is not None:
            self.__task.cancel()

    def on_found(self, service: BluetoothServiceInfoBleak, change: BluetoothChange):
        if not service.connectable:
            return
        if self.__task is not None:
            return
        self.__task = create_task(self.__loop(service.device))

    async def send_cmd(self, data: bytes):
        await self.send(add_checksum(data))

    async def send(self, data: bytes):
        if not self.client:
            raise Exception(self.name + " is not connected")
        await self.client.write_gatt_char(CORE_WRITE_UUID, data, True)

    async def _connected(self):
        pass

    def _received(self, sender, data: bytearray):
        data = bytes(data)
        self.received.on_next(data)
        if data[:2] == b"\x00\x02":
            self.battery.on_next(data[14] * 10)
            self.device_info["sw_version"] = ".".join(
                str(x) for x in data[7:10])
            self.device_id = self.dr.async_get_or_create(
                config_entry_id=self.entry_id,
                identifiers=self.device_info["identifiers"],
                sw_version=self.device_info["sw_version"],
            ).id
            if self.info is not None and not self.info.done():
                self.info.set_result(None)
        elif data[:2] == b"\x00\x01":
            self.hass.bus.async_fire("sony_mesh_icon", {
                CONF_DEVICE_ID: self.device_id,
                CONF_NAME: self.name,
            }, EventOrigin.remote)
        elif data[:2] == b"\x00\x00":
            self.battery.on_next(data[2] * 10)

    def __disconnected(self, client: BleakClient):
        client.set_disconnected_callback(None)
        self.connect_changed.on_next(False)
        self.battery.on_next(None)

    async def __loop(self, device: BLEDevice):
        try:
            _LOGGER.debug(f"Connecting {device.name}")
            async with HaBleakClientWrapper(device, self.__disconnected) as client:
                self.info = Future()
                _LOGGER.debug(f"Enable {device.name} indicate")
                await client.start_notify(CORE_INDICATE_UUID, self._received, force_indicate=True)
                _LOGGER.debug(f"Waiting {device.name} indicate")
                await wait_for(self.info, 10)
                _LOGGER.debug(f"Enable {device.name} notify")
                await client.start_notify(CORE_NOTIFY_UUID, self._received)
                self.client = client
                _LOGGER.debug(f"Enable {device.name} feature")
                await wait_for(self.send(CMD_FEATURE_ENABLE), 5)
                _LOGGER.debug(f"Configure {device.name}")
                await self._connected()

                if not client.is_connected:
                    return
                self.connect_changed.on_next(True)
                _LOGGER.debug(f"Connected {device.name}")
                await self.connect_changed.pipe(
                    ops.first(lambda x: x is not True),
                )
        finally:
            _LOGGER.debug(f"Disconnected {device.name}")
            self.client = None
            self.__task = None
            bluetooth._get_manager(self.hass)._connectable_history.pop(
                device.address, None)


class MESHAC(MESHCore):
    def _received(self, sender, data: bytearray):
        super()._received(sender, data)
        if data[0] == 1:
            if data[1] == 2:
                self.hass.bus.async_fire("sony_mesh_move", {
                    CONF_DEVICE_ID: self.device_id,
                    CONF_NAME: self.name,
                    CONF_TYPE: "flip",
                }, EventOrigin.remote)


class MESHBU(MESHCore):
    def _received(self, sender, data: bytearray):
        super()._received(sender, data)
        if data[0] == 1:
            if data[1] == 0:
                self.hass.bus.async_fire("sony_mesh_button", {
                    CONF_DEVICE_ID: self.device_id,
                    CONF_NAME: self.name,
                    "type": BUTTON_PUSH_TYPES[data[2]],
                }, EventOrigin.remote)


class MESHGP(MESHCore):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        super().__init__(hass, entry)
        self.ain = False
        self.din = [False, False, False]
        self._reset_output()

    async def send_config(self):
        if not self.client:
            return
        din = sum(1 << i for i in range(3) if self.din[i])
        dout = sum(1 << i for i in range(3) if self.dout[i])
        await self.send_cmd(pack(
            "<BBBBBBBBBB",
            1, 1,
            din, din,
            dout, self.aout,
            1 if self.power else 2,
            255, 0,
            0x22 if self.ain else 0x00,
        ))

    async def _connected(self):
        self._reset_output()
        await self.send_config(True)

    def _reset_output(self):
        self.aout = 0
        self.dout = [False, False, False]
        self.power = False


class MESHMD(MESHCore):
    delay_time = 500
    hold_time = 500

    async def send_config(self, init=False):
        if not self.client:
            return
        mode = 0x03
        if init:
            mode |= 0x10
        await self.send_cmd(pack("<BBBBHH", 1, 0, 0, mode, self.hold_time, self.delay_time))

    async def _connected(self):
        await self.send_config(True)


class MESHPA(MESHCore):
    async def _connected(self):
        await self.send_cmd(pack("<BBBQHBBBB", 1, 0, 0, 0, 0, 2, 2, 2, 0x1C))


class MESHTH(MESHCore):
    async def _connected(self):
        await self.send_cmd(pack("<BBBQHB", 1, 0, 0, 0, 0, 0x1C))


class MESHEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, core: MESHCore):
        super().__init__()
        self.core = core

    @property
    def device_info(self):
        return self.core.device_info

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._subscribe(self.core.connect_changed, self._connect_changed)

    def _connect_changed(self, connected: bool):
        self._attr_available = connected
        self.async_write_ha_state()

    def _subscribe(self, src: Observable, func: Callable):
        self.async_on_remove(src.subscribe(func).dispose)


def add_checksum(data: Iterable[int]):
    data = bytearray(data)
    data.append(sum(data) & 0xFF)
    return bytes(data)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    name: str = entry.data[CONF_NAME]
    if name.startswith("MESH-100AC"):
        core = MESHAC(hass, entry)
    elif name.startswith("MESH-100BU"):
        core = MESHBU(hass, entry)
    elif name.startswith("MESH-100GP"):
        core = MESHGP(hass, entry)
    elif name.startswith("MESH-100MD"):
        core = MESHMD(hass, entry)
    elif name.startswith("MESH-100PA"):
        core = MESHPA(hass, entry)
    elif name.startswith("MESH-100TH"):
        core = MESHTH(hass, entry)
    else:
        core = MESHCore(hass, entry)
    entry.async_on_unload(bluetooth.async_register_callback(hass, core.on_found, {
        "address": entry.data[CONF_ADDRESS],
    }, bluetooth.BluetoothScanningMode.PASSIVE))
    hass.data[entry.entry_id] = core
    hass.config_entries.async_setup_platforms(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False
    if client := hass.data.pop(entry.entry_id, None):
        client.close()
    bluetooth.async_rediscover_address(hass, entry.data[CONF_ADDRESS])
    return True
