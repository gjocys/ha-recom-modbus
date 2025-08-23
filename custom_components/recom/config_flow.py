import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from typing import Any, Dict

import logging
_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_NAME,
)


class DomainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    @property
    def schema(self):
        return vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
            )

        return self.async_show_form(step_id="user", data_schema=self.schema)

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            # Save options (host/port/scan only)
            return self.async_create_entry(title="", data=user_input)

        # Defaults prefer existing options; fall back to original data
        data = self._entry.data
        opt = self._entry.options

        host = opt.get(CONF_HOST, data.get(CONF_HOST, ""))
        port = opt.get(CONF_PORT, data.get(CONF_PORT, DEFAULT_PORT))
        scan = opt.get(CONF_SCAN_INTERVAL, data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

        options_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=host): str,
                vol.Required(CONF_PORT, default=port): int,
                vol.Required(CONF_SCAN_INTERVAL, default=scan): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
