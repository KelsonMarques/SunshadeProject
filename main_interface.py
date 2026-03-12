import customtkinter as ctk
import math
import json
import os
import threading
import time
from datetime import timedelta
from interfaces.config_interface import ConfigInterface
from backend.modbus_handler import ModbusHandler

CONFIG_FILE = "config.json"

class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Senha")
        self.geometry("300x150")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.password = ""
        ctk.CTkLabel(self, text="Digite a senha de acesso:").pack(pady=10)
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.pack(padx=20, fill="x")
        self.password_entry.bind("<Return>", self.on_ok)
        ctk.CTkButton(self, text="OK", command=self.on_ok).pack(pady=10)
        self.password_entry.focus()
    def on_ok(self, event=None):
        self.password = self.password_entry.get()
        self.destroy()
    def get_password(self):
        self.master.wait_window(self)
        return self.password

class MainInterface(ctk.CTk):
    def __init__(self, modbus_handler):
        super().__init__()

        self.modbus_handler = modbus_handler
        self.config_window = None
        
        self.app_config = {}
        self.active_timers = {}
        self.load_app_config()
        self.is_checking_connection = False
        self.overlay_is_active = False
        self.current_direction = "PARA"
        self.start_time = time.time()

        self.normal_style = {"fg_color": "#565B5E", "hover_color": "#6A7175", "border_width": 1, "border_color": "#4A4D50"}
        self.selected_style = {"fg_color": "#4A90E2", "hover_color": "#63A3E9", "border_width": 2, "border_color": "#FFFFFF"}
        
        self.radial_buttons = []
        self.direction_buttons = {}
        self.main_controls = []

        self.title("Sunshades Standalone")
        self.geometry("900x500")
        self.resizable(False, False)
        
        self.protocol("WM_DELETE_WINDOW", lambda: None) 
        self.bind("<Control-F1>", self.on_closing_event)

        self.create_widgets()
        
        self.connection_overlay = ctk.CTkFrame(self, fg_color="#2B2B2B")
        ctk.CTkLabel(self.connection_overlay, text="NO CONNECTION", font=("Arial", 32, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        self.handle_direction_selection(self.direction_buttons["PARA"])
        self.start_connection_check()
        self.update_runtime_clock()

    def create_widgets(self):
        center_x, center_y = (900 / 2) - 70, 500 / 2
        circle_radius, button_diameter, center_button_diameter = 175, 90, 80

        for i in range(8):
            angle = math.radians((i * 45) - 90)
            btn = ctk.CTkButton(self, text=str(i + 1), width=button_diameter, height=button_diameter, corner_radius=button_diameter / 2, **self.normal_style)
            btn.place(x=center_x + circle_radius * math.cos(angle), y=center_y + circle_radius * math.sin(angle), anchor="center")
            btn.configure(command=lambda b=btn: self.toggle_button_style(b))
            btn._is_selected = False
            self.radial_buttons.append(btn)
            self.main_controls.append(btn)

        all_button = ctk.CTkButton(self, text="ALL", width=center_button_diameter, height=center_button_diameter, corner_radius=center_button_diameter / 2, **self.normal_style)
        all_button.place(x=center_x, y=center_y, anchor="center")
        all_button.configure(command=self.toggle_all_radial)
        all_button._is_selected = False
        self.main_controls.append(all_button)

        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.place(relx=0.88, rely=0.5, anchor="center")
        
        button_width, button_height = 150, 50
        for text in ["SOBE", "PARA", "DESCE"]:
            btn = ctk.CTkButton(right_frame, text=text, width=button_width, height=button_height, **self.normal_style)
            btn.pack(pady=12)
            btn.configure(command=lambda b=btn: self.handle_direction_selection(b))
            self.direction_buttons[text] = btn
            self.main_controls.append(btn)
        
        self.config_button = ctk.CTkButton(self, text="Config", width=100, command=self.prompt_for_password)
        self.config_button.place(relx=0.98, rely=0.96, anchor="se")

    def toggle_button_style(self, button):
        """Toggles the style of a button, preventing deselection if it's active."""
        curtain_num = button.cget("text")
        is_radial_button = curtain_num.isdigit()

        # If trying to deselect a moving radial button, block the action.
        if is_radial_button and button._is_selected and curtain_num in self.active_timers:
            return # Ignore the click

        # Otherwise, proceed with the toggle.
        button._is_selected = not button._is_selected
        button.configure(**self.selected_style if button._is_selected else self.normal_style)

    def prompt_for_password(self):
        dialog = PasswordDialog(self)
        entered_password = dialog.get_password()
        correct_password = self.app_config.get("password", "admin")
        if entered_password == correct_password:
            self.open_config_window()

    def update_runtime_clock(self):
        elapsed_seconds = int(time.time() - self.start_time)
        runtime_str = str(timedelta(seconds=elapsed_seconds))
        self.title(f"Sunshades Standalone - {runtime_str}")
        self.after(1000, self.update_runtime_clock)

    def handle_direction_selection(self, clicked_button):
        command_text = clicked_button.cget("text")
        if command_text == "PARA":
            if self.current_direction == "PARA": return
            self.current_direction = "PARA"
            self.run_command("parar")
        elif self.current_direction == "PARA":
            self.current_direction = command_text
            if command_text == "SOBE": self.run_command("subir")
            elif command_text == "DESCE": self.run_command("descer")
        else: return
        for text, btn in self.direction_buttons.items():
            btn.configure(**self.selected_style if text == self.current_direction else self.normal_style)

    def start_connection_check(self):
        if self.is_checking_connection: return
        self.is_checking_connection = True
        threading.Thread(target=self.run_connection_check_thread, daemon=True).start()

    def run_connection_check_thread(self):
        ip, port_str = self.app_config.get("ip"), self.app_config.get("port")
        is_connected = False
        if ip and port_str:
            try: is_connected, _ = self.modbus_handler.test_connection(ip, int(port_str))
            except (ValueError, TypeError): is_connected = False
        self.after(0, self.update_overlay_status, is_connected)
        time.sleep(3)
        self.is_checking_connection = False
        self.start_connection_check()

    def update_overlay_status(self, is_connected):
        if is_connected:
            if self.overlay_is_active:
                self.connection_overlay.place_forget()
                for control in self.main_controls: control.configure(state="normal")
                self.overlay_is_active = False
        else:
            if not self.overlay_is_active:
                self.connection_overlay.place(relwidth=1, relheight=1, relx=0, rely=0)
                self.connection_overlay.lift()
                self.config_button.lift()
                for control in self.main_controls: control.configure(state="disabled")
                self.overlay_is_active = True

    def toggle_all_radial(self):
        all_button_widget = self.main_controls[8]
        self.toggle_button_style(all_button_widget)
        is_all_selected = all_button_widget._is_selected
        for btn in self.radial_buttons:
            if btn._is_selected != is_all_selected: self.toggle_button_style(btn)

    def run_command(self, direction):
        self.cancel_all_timers()
        selected_curtains = [b for b in self.radial_buttons if b._is_selected]
        if not selected_curtains: return
        ip, port = self.app_config.get("ip"), self.app_config.get("port")
        if not ip or not port: return
        for curtain_button in selected_curtains:
            curtain_num = curtain_button.cget("text")
            config = self.app_config.get("buttons", {}).get(curtain_num, {})
            do_subir, do_descer = config.get("do_subir"), config.get("do_descer")
            if direction == "parar":
                if do_subir: self.modbus_handler.write_coil(ip, int(port), int(do_subir), False)
                if do_descer: self.modbus_handler.write_coil(ip, int(port), int(do_descer), False)
                continue
            do_to_run = do_subir if direction == "subir" else do_descer
            tempo_str = config.get("tempo")
            if not do_to_run or not tempo_str: continue
            try:
                do_addr, tempo = int(do_to_run), float(tempo_str)
                self.modbus_handler.write_coil(ip, int(port), do_addr, True)
                timer = threading.Timer(tempo, self.auto_stop_curtain, args=[curtain_num, do_addr])
                self.active_timers[curtain_num] = timer
                timer.start()
            except (ValueError, TypeError): continue

    def auto_stop_curtain(self, curtain_num, do_address):
        ip, port = self.app_config.get("ip"), self.app_config.get("port")
        if ip and port: self.modbus_handler.write_coil(ip, int(port), do_address, False)
        if curtain_num in self.active_timers: del self.active_timers[curtain_num]
        if not self.active_timers: self.after(0, self.handle_direction_selection, self.direction_buttons["PARA"])

    def load_app_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f: self.app_config = json.load(f)

    def open_config_window(self):
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = ConfigInterface(self, self.modbus_handler)
            self.config_window.protocol("WM_DELETE_WINDOW", self.on_config_close)
        self.config_window.focus()

    def on_config_close(self):
        self.load_app_config()
        self.config_window.destroy()
        self.config_window = None

    def cancel_all_timers(self):
        for timer in self.active_timers.values(): timer.cancel()
        self.active_timers.clear()

    def on_closing_event(self, event=None):
        self.cancel_all_timers()
        self.destroy()

if __name__ == "__main__":
    modbus_handler = ModbusHandler()
    app = MainInterface(modbus_handler)
    app.mainloop()
