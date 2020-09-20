"""Support for Firmata light output."""

import logging
from typing import Type

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAXIMUM, CONF_MINIMUM, CONF_NAME, CONF_PIN
from homeassistant.core import HomeAssistant

from .board import FirmataPinType
from .const import CONF_INITIAL_STATE, CONF_PIN_MODE, DOMAIN
from .entity import FirmataPinEntity
from .pin import FirmataBoardPin, FirmataPinUsedException, FirmataPWMOutput

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Firmata lights."""
    new_entities = []

    board = hass.data[DOMAIN][config_entry.entry_id]
    for light in board.lights:
        pin = light[CONF_PIN]
        pin_mode = light[CONF_PIN_MODE]
        initial = light[CONF_INITIAL_STATE]
        minimum = light[CONF_MINIMUM]
        maximum = light[CONF_MAXIMUM]
        api = FirmataPWMOutput(board, pin, pin_mode, initial, minimum, maximum)
        try:
            api.setup()
        except FirmataPinUsedException:
            _LOGGER.error(
                "Could not setup light on pin %s since pin already in use.",
                light[CONF_PIN],
            )
            continue
        name = light[CONF_NAME]
        light_entity = FirmataLight(api, config_entry, name, pin)
        new_entities.append(light_entity)

    if new_entities:
        async_add_entities(new_entities)


class FirmataLight(FirmataPinEntity, LightEntity):
    """Representation of a light on a Firmata board."""

    def __init__(
        self,
        api: Type[FirmataBoardPin],
        config_entry: ConfigEntry,
        name: str,
        pin: FirmataPinType,
    ):
        """Initialize the light pin entity."""
        super().__init__(api, config_entry, name, pin)

        # Default first turn on to max
        self._last_on_level = 255

    async def async_added_to_hass(self) -> None:
        """Set up a light."""
        await self._api.start_pin()
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._api.state > 0

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return self._api.state

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on light."""
        _LOGGER.debug("Turning light %s on", self._name)
        level = kwargs.get(ATTR_BRIGHTNESS, self._last_on_level)
        await self._api.set_level(level)
        self.async_write_ha_state()
        self._last_on_level = level

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off light."""
        _LOGGER.debug("Turning light %s off", self._name)
        await self._api.set_level(0)
        self.async_write_ha_state()
