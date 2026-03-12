import customtkinter as ctk
import json
import os
from backend.modbus_handler import ModbusHandler

CONFIG_FILE = "config.json"

class ConfigInterface(ctk.CTkToplevel):
    def __init__(self, master, modbus_handler):
        super().__init__(master)

        self.title("Configuração")
        self.geometry("700x550")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.modbus_handler = modbus_handler
        self.button_entries = {}

        tab_view = ctk.CTkTabview(self)
        tab_view.pack(expand=True, fill="both", padx=10, pady=10)

        tab_connection = tab_view.add("Conexão")
        tab_buttons = tab_view.add("Botões")

        self.create_connection_tab(tab_connection)
        self.create_buttons_tab(tab_buttons)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(bottom_frame, text="Status: Carregue ou salve uma configuração.")
        self.status_label.pack(side="left", padx=10)
        
        save_button = ctk.CTkButton(bottom_frame, text="Salvar Todas as Configurações", command=self.save_config)
        save_button.pack(side="right", padx=10)

        self.load_config()

    def create_connection_tab(self, tab):
        config_frame = ctk.CTkFrame(tab, fg_color="transparent")
        config_frame.pack(pady=15, padx=10, fill="x")
        config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(config_frame, text="Endereço IP:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.ip_entry = ctk.CTkEntry(config_frame)
        self.ip_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(config_frame, text="Porta:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.port_entry = ctk.CTkEntry(config_frame)
        self.port_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # The "Nova Senha" field has been removed.
        
        test_button = ctk.CTkButton(config_frame, text="Testar Conexão", command=self.test_connection)
        test_button.grid(row=2, column=0, columnspan=2, pady=10) # Moved up to row 2

        test_frame = ctk.CTkFrame(tab, border_width=1)
        test_frame.pack(pady=10, padx=10, fill="x")
        test_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(test_frame, text="Área de Teste Rápido", font=("Arial", 12, "italic")).grid(row=0, column=0, columnspan=2, pady=(5,10))
        ctk.CTkLabel(test_frame, text="Número do DO:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.do_entry = ctk.CTkEntry(test_frame, placeholder_text="Ex: 0")
        self.do_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(test_frame, text="Status:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.status_switch = ctk.CTkSwitch(test_frame, text="ON", onvalue=True, offvalue=False)
        self.status_switch.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        execute_button = ctk.CTkButton(test_frame, text="Executar Escrita", command=self.execute_write_coil)
        execute_button.grid(row=3, column=0, columnspan=2, pady=10)

    def create_buttons_tab(self, tab):
        scroll_frame = ctk.CTkScrollableFrame(tab, label_text="Configuração dos Botões Radiais (1-8)")
        scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        headers = ["Botão", "DO Subir", "DO Descer", "Tempo (s)"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(scroll_frame, text=header, font=("Arial", 12, "bold")).grid(row=0, column=col, padx=15, pady=5)

        for i in range(1, 9):
            ctk.CTkLabel(scroll_frame, text=f"{i}").grid(row=i, column=0)
            do_subir_entry = ctk.CTkEntry(scroll_frame)
            do_subir_entry.grid(row=i, column=1, padx=5, pady=5)
            do_descer_entry = ctk.CTkEntry(scroll_frame)
            do_descer_entry.grid(row=i, column=2, padx=5, pady=5)
            tempo_entry = ctk.CTkEntry(scroll_frame)
            tempo_entry.grid(row=i, column=3, padx=5, pady=5)
            self.button_entries[str(i)] = {"do_subir": do_subir_entry, "do_descer": do_descer_entry, "tempo": tempo_entry}

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.status_label.configure(text="Arquivo de configuração não encontrado.")
            return
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.ip_entry.insert(0, config.get("ip", ""))
                self.port_entry.insert(0, str(config.get("port", "")))
                button_configs = config.get("buttons", {})
                for btn_num, entries in self.button_entries.items():
                    cfg = button_configs.get(btn_num, {})
                    entries["do_subir"].insert(0, str(cfg.get("do_subir", "")))
                    entries["do_descer"].insert(0, str(cfg.get("do_descer", "")))
                    entries["tempo"].insert(0, str(cfg.get("tempo", "")))
                self.status_label.configure(text="Configuração carregada com sucesso.")
        except (json.JSONDecodeError, KeyError):
            self.status_label.configure(text="Erro: Formato de config.json inválido.")

    def save_config(self):
        # Load existing config to preserve the password
        existing_config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                try: existing_config = json.load(f)
                except json.JSONDecodeError: pass

        button_configs = {}
        for btn_num, entries in self.button_entries.items():
            button_configs[btn_num] = {
                "do_subir": entries["do_subir"].get(),
                "do_descer": entries["do_descer"].get(),
                "tempo": entries["tempo"].get()
            }
        
        config = {
            "ip": self.ip_entry.get(),
            "port": self.port_entry.get(),
            "password": existing_config.get("password", "admin"), # Preserve existing password
            "buttons": button_configs
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            self.status_label.configure(text="Configuração salva com sucesso.")
        except Exception as e:
            self.status_label.configure(text=f"Erro ao salvar: {e}")

    def test_connection(self):
        ip, port_str = self.ip_entry.get(), self.port_entry.get()
        if not ip or not port_str:
            self.status_label.configure(text="Erro: IP e Porta são obrigatórios.")
            return
        try:
            port = int(port_str)
            success, message = self.modbus_handler.test_connection(ip, port)
            self.status_label.configure(text=message)
        except ValueError:
            self.status_label.configure(text="Erro: A porta deve ser um número.")

    def execute_write_coil(self):
        ip, port_str, do_str = self.ip_entry.get(), self.port_entry.get(), self.do_entry.get()
        status = self.status_switch.get()
        if not ip or not port_str or not do_str:
            self.status_label.configure(text="Erro: IP, Porta e Número do DO são obrigatórios.")
            return
        try:
            port, do_number = int(port_str), int(do_str)
            success, message = self.modbus_handler.write_coil(ip, port, do_number, status)
            self.status_label.configure(text=message)
        except ValueError:
            self.status_label.configure(text="Erro: Porta e DO devem ser números inteiros.")
