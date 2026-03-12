from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

class ModbusHandler:
    """
    This handler adopts a connect-on-demand strategy to avoid server timeouts.
    Each action establishes a new, temporary connection.
    """
    def __init__(self):
        # No persistent client is stored to prevent stale connections.
        pass

    def test_connection(self, ip, port):
        """Tests the connection by connecting and immediately disconnecting."""
        try:
            client = ModbusTcpClient(ip, port=port, timeout=3)
            if client.connect():
                client.close()
                return True, f"Sucesso ao conectar em {ip}:{port}"
            else:
                return False, "Falha na conexão. Verifique o IP e a Porta."
        except Exception as e:
            return False, f"Erro de conexão: {e}"

    def write_coil(self, ip, port, address, value):
        """Connects, writes a value to a coil, and disconnects."""
        try:
            client = ModbusTcpClient(ip, port=port, timeout=3)
            if not client.connect():
                return False, "Falha na conexão ao tentar escrever."

            # Perform the write operation
            result = client.write_coil(address, value)
            client.close() # Disconnect immediately after the action

            if result.isError():
                return False, f"Erro Modbus ao escrever no endereço {address}."
            else:
                return True, f"Sucesso: Endereço {address} definido como {value}."
        except Exception as e:
            return False, f"Erro durante a escrita: {e}"

    # The is_connected and close_connection methods are no longer needed
    # as we are not maintaining a persistent connection.
