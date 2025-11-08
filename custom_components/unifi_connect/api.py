import aiohttp
import async_timeout
import logging
from typing import Any

from .const import DEFAULT_PORT, CONTROLLER_UDMP, CONTROLLER_OTHER

_LOGGER = logging.getLogger(__name__)


class UnifiConnectAPI:
    def __init__(self, host: str, username: str, password: str, port: int = DEFAULT_PORT, controller_type: str = CONTROLLER_UDMP):
        self._host = host
        self._username = username
        self._password = password
        self._port = port
        self._controller_type = controller_type
        self._session = aiohttp.ClientSession()
        self._cookie = None
        self._csrf = None

    async def login(self) -> bool:
        """Login and store cookies/tokens."""
        login_url = self._get_login_url()
        payload = {
            "username": self._username,
            "password": self._password,
            "remember": True
        }

        try:
            async with async_timeout.timeout(10):
                async with self._session.post(login_url, json=payload, ssl=False) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Login failed: %s", resp.status)
                        return False

                    self._cookie = resp.cookies
                    headers = resp.headers
                    self._csrf = headers.get("x-csrf-token")
                    _LOGGER.debug("Login success. CSRF: %s", self._csrf)
                    return True
        except Exception as e:
            _LOGGER.exception("Login error: %s", e)
            return False

    async def get_devices(self) -> list[dict[str, Any]]:
        """Fetch list of devices."""
        url = self._get_api_url("api/v2/devices?shadow=true")

        headers = {
            "x-csrf-token": self._csrf,
        }

        try:
            async with async_timeout.timeout(10):
                async with self._session.get(url, headers=headers, cookies=self._cookie, ssl=False) as resp:
                    if resp.status == 401:
                        _LOGGER.warning("Session expired, trying to re-login.")
                        if await self.login():
                            return await self.get_devices()
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", data)
                    _LOGGER.error("Device fetch failed: %s", resp.status)
        except Exception as e:
            _LOGGER.exception("Error fetching devices: %s", e)
        return []

    async def perform_action(self, device_id: str, action_id: str, action_name: str, args: dict | None = None) -> bool:
        """Perform an action on a device."""
        path = f"api/v2/devices/{device_id}/status"
        url = self._get_api_url(path)

        payload = {
            "id": action_id,
            "name": action_name
        }

        if args:
            payload["args"] = args

        headers = {
            "x-csrf-token": self._csrf,
            "referer": f"https://{self._host}/connect/devices/all/{device_id}",
            "origin": f"https://{self._host}"
        }

        try:
            async with async_timeout.timeout(10):
                _LOGGER.debug("Sending action to %s: %s", url, payload)
                async with self._session.patch(url, json=payload, headers=headers, cookies=self._cookie, ssl=False) as resp:
                    if resp.status == 200:
                        _LOGGER.debug("Action %s on %s successful", action_name, device_id)
                        return True
                    else:
                        response_text = await resp.text()
                        _LOGGER.warning("Failed to perform %s on %s: %s - Response: %s", action_name, device_id, resp.status, response_text)
        except Exception as e:
            _LOGGER.exception("Error performing %s on %s: %s", action_name, device_id, e)
        return False

    def _get_login_url(self) -> str:
        if self._controller_type == CONTROLLER_UDMP:
            return f"https://{self._host}/api/auth/login"
        return f"https://{self._host}:{self._port}/api/login"

    def _get_api_url(self, path: str) -> str:
        if self._controller_type == CONTROLLER_UDMP:
            return f"https://{self._host}/proxy/connect/{path}"
        return f"https://{self._host}:{self._port}/{path}"

    async def close(self):
        """Close the session."""
        await self._session.close()
