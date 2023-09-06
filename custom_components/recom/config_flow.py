import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL

import logging
_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_NAME
)


class DomainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    @property
    def schema(self):
        return vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int
            }
        )
        

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input
            )
            
    
        return self.async_show_form(step_id="user", data_schema=self.schema)