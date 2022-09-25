import voluptuous as vol
from homeassistant.components.device_automation import \
    DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import \
    event as event_trigger
from homeassistant.const import (CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM,
                                 CONF_TYPE)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from . import DOMAIN

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In({
            "core_icon",
            "button_single",
            "button_double",
            "button_long",
            "move_flip",
        }),
    }
)


async def async_get_triggers(hass: HomeAssistant, device_id: str):
    dr = device_registry.async_get(hass)
    device = dr.async_get(device_id)
    name = next(x[1] for x in device.identifiers if x[0] == DOMAIN)
    triggers = [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: "core_icon",
        },
    ]
    if name.startswith("MESH-100BU"):
        triggers.extend([
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: "button_single",
            },
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: "button_double",
            },
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: "button_long",
            },
        ])
    return triggers


async def async_attach_trigger(hass: HomeAssistant, config: ConfigType, action: TriggerActionType, trigger_info: TriggerInfo):
    if config[CONF_TYPE] == "core_icon":
        event_config = event_trigger.TRIGGER_SCHEMA(
            {
                event_trigger.CONF_PLATFORM: "event",
                event_trigger.CONF_EVENT_TYPE: "sony_mesh_icon",
                event_trigger.CONF_EVENT_DATA: {
                    CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                },
            }
        )
    elif config[CONF_TYPE] == "button_single":
        event_config = event_trigger.TRIGGER_SCHEMA(
            {
                event_trigger.CONF_PLATFORM: "event",
                event_trigger.CONF_EVENT_TYPE: "sony_mesh_button",
                event_trigger.CONF_EVENT_DATA: {
                    CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                    CONF_TYPE: "single",
                },
            }
        )
    elif config[CONF_TYPE] == "button_double":
        event_config = event_trigger.TRIGGER_SCHEMA(
            {
                event_trigger.CONF_PLATFORM: "event",
                event_trigger.CONF_EVENT_TYPE: "sony_mesh_button",
                event_trigger.CONF_EVENT_DATA: {
                    CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                    CONF_TYPE: "double",
                },
            }
        )
    elif config[CONF_TYPE] == "button_long":
        event_config = event_trigger.TRIGGER_SCHEMA(
            {
                event_trigger.CONF_PLATFORM: "event",
                event_trigger.CONF_EVENT_TYPE: "sony_mesh_button",
                event_trigger.CONF_EVENT_DATA: {
                    CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                    CONF_TYPE: "long",
                },
            }
        )
    else:
        raise ValueError()
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
