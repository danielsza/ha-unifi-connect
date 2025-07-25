from .api import UnifiConnectAPI

class UnifiConnectHub:
    """Manages connection and data coordination with UniFi Connect."""

    def __init__(self, hass, entry):
        from .coordinator import UnifiConnectCoordinator  # ⬅️ Moved inside to break circular import

        self.hass = hass
        self.entry = entry

        self.api = UnifiConnectAPI(
            host=entry.data["host"],
            username=entry.data["username"],
            password=entry.data["password"],
            port=entry.data.get("port", 7443),
            controller_type=entry.data.get("controller_type"),
        )

        self.coordinator = UnifiConnectCoordinator(
            hass=hass,
            api=self.api,
        )

    async def async_initialize(self):
        """Log in and perform initial data fetch."""
        if not await self.api.login():
            raise Exception("Unable to log in to UniFi Connect")
        await self.coordinator.async_config_entry_first_refresh()
