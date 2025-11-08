# Unifi Connect for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub](https://img.shields.io/github/license/iamslan/ha-unifi-connect)](LICENSE)

This is a custom [Home Assistant](https://www.home-assistant.io/) integration to support **Unifi Connect** devices (e.g., SE 21) using the [UniFi Connect Flow SDK API](https://ubntwiki.com/products/software/unifi-connect).

## ⚠️ Notice

This integration **does not support UniFi accounts with 2FA or cloud-only login**.

To use this integration:

1. You **must create a local UniFi OS account** on your console (e.g., Dream Machine Pro).
2. Go to your UniFi Console:
   - `Settings` → `Admin Settings` → `Accounts`
   - Click **Add User**
   - Select **Local Access Only**
   - Assign the user **Full Management** privileges to UniFi Connect
3. Use this local user account for login in the integration setup.

## Features

- Local polling for UniFi Connect devices
- Support for **Unifi Connect SE 21**, including:
  - Power control
  - Brightness control
  - Volume control
  - Mode switching (Web, App) with URL selection, App Selection
  - Other settings like reload, sleep, etc...
- Support for **UniFi EV Station Lite**, including:
  - Charging status monitoring
  - Charging enable/disable control
  - Max output amperage control (6-40A)
  - Display brightness control
  - Status light control
  - Station mode selection (Plug & Charge, No Access, Access with UniFi Identity)
  - Fallback security settings
  - Display label and admin message
  - Locating mode
  - Device reboot

## Installation

### HACS (Recommended)

1. In Home Assistant, go to **HACS > Integrations**.
2. Click **⋮ > Custom repositories**.
3. Add:
   - **Repository:** `https://github.com/iamslan/ha-unifi-connect`
   - **Category:** Integration
4. Click **Add**, then search for **Unifi Connect** and install.

### Manual

1. Download this repository and extract it.
2. Copy the `unifi_connect` folder to `custom_components/` in your Home Assistant configuration directory.
3. Restart Home Assistant.

## Configuration

1. Go to **Settings > Devices & Services > Integrations**.
2. Click **Add Integration** and search for **Unifi Connect**.
3. Enter your UniFi Console IP address (e.g., Dream Machine Pro), username, and password.
4. Complete the configuration flow.

> This integration uses local polling and does not require cloud access.

## Troubleshooting

- Make sure your UniFi OS version is up-to-date.
- Ensure your Home Assistant instance can reach your UniFi Console on the local network.
- Check logs in **Settings > System > Logs** for integration errors.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the [MIT License](LICENSE).

---

**Maintainer**: [@iamslan](https://github.com/iamslan)
