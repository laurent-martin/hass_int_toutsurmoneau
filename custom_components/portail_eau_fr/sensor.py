"""Sensor for water provider portal."""
from datetime import datetime, timedelta
import logging
import toutsurmoneau
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# for hass
SCAN_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the meter sensor."""
    _LOGGER.debug("async_setup_entry")
    # API object stored here by __init__.py
    api: toutsurmoneau.AsyncClient = hass.data[DOMAIN][entry.entry_id]
    account = (await api.async_contracts())[0]

    async_add_entities([ToutSurMonEauEntity(api, account)])


class ToutSurMonEauEntity(SensorEntity):
    """Implementation of the meter sensor."""

    def __init__(self, api: toutsurmoneau.AsyncClient, account):
        """Initialize the ToutSurMonEauEntity class."""
        _LOGGER.debug("__init__")
        self._name = f"{account['brandCode']} meter {api._id}"
        self._unit_of_measurement = UnitOfVolume.LITERS
        self._state = None
        self._attr_attribution = account["brandCode"]
        self._attr_should_poll = True
        self._api = api

    @property
    def device_class(self):
        """Return the device class."""
        _LOGGER.debug("device_class")
        return SensorDeviceClass.WATER

    @property
    def state_class(self):
        """Return the state class."""
        _LOGGER.debug("state_class")
        return SensorStateClass.TOTAL_INCREASING

    @property
    def name(self):
        """Return the name of the sensor."""
        _LOGGER.debug("name")
        return self._name

    @property
    def unique_id(self):
        """Return sensor unique_id."""
        _LOGGER.debug("unique_id")
        return "unique_id_with_meter"

    @property
    def native_value(self):
        """Return the state of the device."""
        _LOGGER.debug("native_value")
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        _LOGGER.debug("native_unit_of_measurement")
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return icon."""
        _LOGGER.debug("icon")
        return "mdi:water-pump"

    @property
    def usage(self):
        """Return ???."""
        _LOGGER.debug("usage")
        return None

    @property
    def available(self):
        """Return if entity is available."""
        _LOGGER.debug("available")
        # true is last update was successful (api available)
        return True

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        _LOGGER.debug("async_added_to_hass")

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        _LOGGER.debug("async_update")
        self._state = (await self._api.async_latest_meter_reading())['volume']
