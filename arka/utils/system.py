import psutil
from typing import Dict

def get_system_stats() -> Dict[str, float]:
    """Return CPU, memory usage percent and temperature (if available)."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    mem_percent = memory.percent
    # Temperature: try to read from psutil.sensors_temperatures
    temp_c = None
    try:
        temps = psutil.sensors_temperatures()
        # Common sensor names on Raspberry Pi: 'cpu_thermal', 'cpu', etc.
        for name, entries in temps.items():
            if entries:
                # Take the first entry's current temperature
                temp_c = entries[0].current
                break
    except Exception:
        temp_c = None
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": mem_percent,
        "temperature_c": temp_c if temp_c is not None else 0.0,
    }