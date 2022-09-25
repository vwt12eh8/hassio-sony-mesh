from typing import Any, Mapping

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from . import DOMAIN


class MESHConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    name = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        self.address = discovery_info.address
        self.name = discovery_info.advertisement.local_name
        if not self.name:
            return self.async_abort(reason="")
        await self.async_set_unique_id(self.name)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {
            CONF_NAME: self.name,
        }
        return self.async_show_form(step_id="setup")

    async def async_step_setup(self, user_input: Mapping[str, Any] = None):
        if user_input is not None:
            return self.async_create_entry(
                title=self.name,
                data={
                    CONF_ADDRESS: self.address,
                    CONF_NAME: self.name,
                },
            )
        return self.async_show_form(
            step_id="setup",
            description_placeholders={
                CONF_NAME: self.name,
            },
            last_step=True,
        )
