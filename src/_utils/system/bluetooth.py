import wmi

IGNORE_ADAPTERS = [
    "Intel(R) Wireless Bluetooth(R) Reset Device",
    "Intel(R) Wireless Bluetooth(R)",
    "Bluetooth",
]


def bluetooth_is_enabled(search_name="Standard Serial over Bluetooth link"):
    """Extendable function to check if bluetooth is enabled."""
    c = wmi.WMI()
    bluetooth_adapter = [
        adapter for adapter in c.Win32_PNPEntity() if "Bluetooth" in str(adapter.Name)
    ]
    adapter_infos = []
    for adapter in bluetooth_adapter:
        adapter_info = {
            "Name": adapter.Name,
            "Status": adapter.Status,
            "PNPDeviceID": adapter.PNPDeviceID,
            "Service": adapter.Service,
        }
        if adapter_info["Name"] not in IGNORE_ADAPTERS:
            adapter_infos.append(adapter_info)
        if search_name in adapter_info["Name"]:
            return True
    return False


if __name__ == "__main__":
    print(f"Bluetooth is enabled: {bluetooth_is_enabled()}")
