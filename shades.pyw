import sys
import os

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
sys.path.insert(0, project_root)

from interfaces.main_interface import MainInterface
from backend.modbus_handler import ModbusHandler

if __name__ == "__main__":
    modbus_handler = ModbusHandler()
    app = MainInterface(modbus_handler)
    app.mainloop()
