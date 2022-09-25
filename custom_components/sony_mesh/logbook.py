from typing import Callable

from homeassistant.components.logbook import (LOGBOOK_ENTRY_MESSAGE,
                                              LOGBOOK_ENTRY_NAME)
from homeassistant.const import CONF_NAME
from homeassistant.core import Event, HomeAssistant

from . import DOMAIN

MESSAGES = {
    "single": "single pressed",
    "double": "double pressed",
    "long": "long pressed",
}


def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
):
    def sony_mesh_button(event: Event):
        data = event.data
        return {
            LOGBOOK_ENTRY_NAME: data[CONF_NAME],
            LOGBOOK_ENTRY_MESSAGE: MESSAGES[data["type"]],
        }

    def sony_mesh_icon(event: Event):
        data = event.data
        return {
            LOGBOOK_ENTRY_NAME: data[CONF_NAME],
            LOGBOOK_ENTRY_MESSAGE: "icon pressed",
        }

    def sony_mesh_move(event: Event):
        data = event.data
        return {
            LOGBOOK_ENTRY_NAME: data[CONF_NAME],
            LOGBOOK_ENTRY_MESSAGE: "flipped",
        }

    async_describe_event(DOMAIN, "sony_mesh_button", sony_mesh_button)
    async_describe_event(DOMAIN, "sony_mesh_icon", sony_mesh_icon)
    async_describe_event(DOMAIN, "sony_mesh_move", sony_mesh_move)
