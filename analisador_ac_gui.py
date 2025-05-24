import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import cmath
import math
import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class ACCircuitAnalyzerApp:
    def __init__(self, master_window):
        self.master = master_window
        master_window.title("Analisador de Circuito CA Série RLC (CustomTkinter)")
        # Aumentando um pouco a altura padrão, mas a rolagem cuidará do resto
        master_window.geometry("800x850") 

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.angle_unit = tk.StringVar(value="degrees")
        self.sweep_enabled_var = tk.BooleanVar(value=False)
        self.plot_variable_options = ["|Z_total|", "|I_total|", "|V_R|", "|V_L|", "|V_C|",
                                      "Fase(Z_total) (°)", "Fase(I_total) (°)",
                                      "Fase(V_R) (°)", "Fase(V_L) (°)", "Fase(V_C) (°)"]
        self.plot_variable_selected = tk.StringVar(value=self.plot_variable_options[0])
        
        self.plot_popup_window = None
        self.about_dialog_window = None
        self.fig_popup = None
        self.ax_popup = None
        self.canvas_popup = None

        # Frame principal (ocupa toda a janela)
        main_app_frame = ctk.CTkFrame(master_window, fg_color="transparent") # Usar fg_color do tema
        main_app_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Título principal (FIXO, FORA DA ÁREA DE ROLAGEM)
        title_label = ctk.CTkLabel(main_app_frame, text="Análise de Circuito CA Série RLC",
                                   font=ctk.CTkFont(size=24, weight="bold")) # Fonte maior
        title_label.pack(pady=(10, 15))

        # --- FRAME ROLÁVEL PARA TODO O CONTEÚDO ABAIXO DO TÍTULO ---
        content_scroll_frame = ctk.CTkScrollableFrame(main_app_frame, corner_radius=10)
        # O scrollable frame preenche o espaço restante no main_app_frame
        content_scroll_frame.pack(expand=True, fill="both", padx=5, pady=5)


        # --- Seção de Entradas (DENTRO DO FRAME ROLÁVEL) ---
        input_section_label = ctk.CTkLabel(content_scroll_frame, text="Parâmetros do Circuito e da Fonte",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        input_section_label.pack(pady=(10,5), anchor="w", padx=10) # Adicionado pady superior

        input_frame = ctk.CTkFrame(content_scroll_frame, corner_radius=10)
        input_frame.pack(fill="x", padx=10, pady=(0,10))
        input_frame.grid_columnconfigure(1, weight=1)
        entry_width = 200
        
        ctk.CTkLabel(input_frame, text="Resistor (R) [Ω]:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.r_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 100")
        self.r_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.r_entry.insert(0, "100")
        self.r_entry.bind("<FocusOut>", self._handle_sweep_param_or_circuit_change)
        self.r_entry.bind("<Return>", self._handle_sweep_param_or_circuit_change)

        ctk.CTkLabel(input_frame, text="Indutor (L) [H]:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.l_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0.1")
        self.l_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.l_entry.insert(0, "0.1")
        self.l_entry.bind("<FocusOut>", self._handle_sweep_param_or_circuit_change)
        self.l_entry.bind("<Return>", self._handle_sweep_param_or_circuit_change)

        ctk.CTkLabel(input_frame, text="Capacitor (C) [F]:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.c_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0.00001")
        self.c_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        self.c_entry.insert(0, "0.00001")
        self.c_entry.bind("<FocusOut>", self._handle_sweep_param_or_circuit_change)
        self.c_entry.bind("<Return>", self._handle_sweep_param_or_circuit_change)

        ctk.CTkLabel(input_frame, text="Tensão Fonte (Vmag) [V]:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.v_mag_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 10")
        self.v_mag_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")
        self.v_mag_entry.insert(0, "10")
        self.v_mag_entry.bind("<FocusOut>", self._handle_sweep_param_or_circuit_change)
        self.v_mag_entry.bind("<Return>", self._handle_sweep_param_or_circuit_change)
        
        ctk.CTkLabel(input_frame, text="Fase Fonte (θv) [°]:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.v_phase_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0")
        self.v_phase_entry.grid(row=4, column=1, padx=10, pady=8, sticky="ew")
        self.v_phase_entry.insert(0, "0")
        self.v_phase_entry.bind("<FocusOut>", self._handle_sweep_param_or_circuit_change)
        self.v_phase_entry.bind("<Return>", self._handle_sweep_param_or_circuit_change)

        ctk.CTkLabel(input_frame, text="Frequência Única (f) [Hz]:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.freq_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 60")
        self.freq_entry.grid(row=5, column=1, padx=10, pady=8, sticky="ew")
        self.freq_entry.insert(0, "60")

        # --- Seção de Opções de Saída (DENTRO DO FRAME ROLÁVEL) ---
        output_options_label = ctk.CTkLabel(content_scroll_frame, text="Opções de Saída",
                                            font=ctk.CTkFont(size=16, weight="bold"))
        output_options_label.pack(pady=(10,5), anchor="w", padx=10)
        output_options_frame = ctk.CTkFrame(content_scroll_frame, corner_radius=10)
        output_options_frame.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(output_options_frame, text="Unidade do Ângulo (Saída):").pack(side="left", padx=(10,5), pady=10)
        degrees_radio = ctk.CTkRadioButton(output_options_frame, text="Graus (°)", variable=self.angle_unit, value="degrees", command=self._handle_sweep_param_or_circuit_change)
        degrees_radio.pack(side="left", padx=5, pady=10)
        radians_radio = ctk.CTkRadioButton(output_options_frame, text="Radianos (rad)", variable=self.angle_unit, value="radians", command=self._handle_sweep_param_or_circuit_change)
        radians_radio.pack(side="left", padx=5, pady=10)

        # --- Seção de Varredura de Frequência (DENTRO DO FRAME ROLÁVEL) ---
        sweep_section_label = ctk.CTkLabel(content_scroll_frame, text="Configurações da Varredura de Frequência",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        sweep_section_label.pack(pady=(15,5), anchor="w", padx=10)
        sweep_frame = ctk.CTkFrame(content_scroll_frame, corner_radius=10)
        sweep_frame.pack(fill="x", padx=10, pady=(0,10))
        sweep_frame.grid_columnconfigure(1, weight=1); sweep_frame.grid_columnconfigure(3, weight=1)
        self.sweep_switch = ctk.CTkSwitch(sweep_frame, text="Habilitar Varredura", variable=self.sweep_enabled_var, command=self.toggle_sweep_entries_state)
        self.sweep_switch.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")
        ctk.CTkLabel(sweep_frame, text="Frequência Inicial (Hz):").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.freq_start_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1")
        self.freq_start_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew"); self.freq_start_entry.insert(0, "1")
        self.freq_start_entry.bind("<FocusOut>", self._handle_sweep_param_or_circuit_change)
        self.freq_start_entry.bind("<Return>", self._handle_sweep_param_or_circuit_change)
        ctk.CTkLabel(sweep_frame, text="Frequência Final (Hz):").grid(row=1, column=2, padx=10, pady=8, sticky="w")
        self.freq_end_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1000")
        self.freq_end_entry.grid(row=1, column=3, padx=10, pady=8, sticky="ew"); self.freq_end_entry.insert(0, "1000")
        self.freq_end_entry.bind("<FocusOut>", self._handle_sweep_param_or_circuit_change)
        self.freq_end_entry.bind("<Return>", self._handle_sweep_param_or_circuit_change)
        ctk.CTkLabel(sweep_frame, text="Número de Pontos:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.num_points_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 200")
        self.num_points_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew"); self.num_points_entry.insert(0, "200")
        self.num_points_entry.bind("<FocusOut>", self._handle_sweep_param_or_circuit_change)
        self.num_points_entry.bind("<Return>", self._handle_sweep_param_or_circuit_change)
        ctk.CTkLabel(sweep_frame, text="Plotar Grandeza:").grid(row=2, column=2, padx=10, pady=8, sticky="w")
        self.plot_variable_combobox = ctk.CTkComboBox(sweep_frame, values=self.plot_variable_options,
                                                      variable=self.plot_variable_selected, state="readonly",
                                                      command=lambda choice: self._handle_sweep_param_or_circuit_change(from_combobox_value=choice))
        self.plot_variable_combobox.grid(row=2, column=3, padx=10, pady=8, sticky="ew")

        # Frame para os botões de ação (DENTRO DO FRAME ROLÁVEL)
        action_buttons_frame = ctk.CTkFrame(content_scroll_frame, fg_color="transparent")
        action_buttons_frame.pack(pady=15)
        analyze_button = ctk.CTkButton(action_buttons_frame, text="Analisar Circuito", command=self.analyze_circuit, font=ctk.CTkFont(size=14, weight="bold"))
        analyze_button.pack(side="left", padx=10)
        clear_button = ctk.CTkButton(action_buttons_frame, text="Limpar Entradas", command=self.clear_entries, fg_color="gray50", hover_color="gray30")
        clear_button.pack(side="left", padx=10)
        about_button = ctk.CTkButton(action_buttons_frame, text="Sobre", command=self.show_about_dialog_ctk, width=80)
        about_button.pack(side="left", padx=10)

        # --- Seção de Saídas em Texto (DENTRO DO FRAME ROLÁVEL) ---
        results_section_label_text = ctk.CTkLabel(content_scroll_frame, text="Resultados da Análise (Texto)",
                                             font=ctk.CTkFont(size=16, weight="bold"))
        results_section_label_text.pack(pady=(20,5), anchor="w", padx=10)
        self.results_text = ctk.CTkTextbox(content_scroll_frame, height=250, corner_radius=10, wrap="word",
                                           font=ctk.CTkFont(family="monospace", size=13))
        # Modificado para fill="both" e expand=True para usar o espaço vertical disponível na área rolável
        self.results_text.pack(fill="both", expand=True, padx=10, pady=(0,10)) 
        self.results_text.configure(state="disabled")

        # Nota sobre a limitação (DENTRO DO FRAME ROLÁVEL, no final do conteúdo rolável)
        note_label = ctk.CTkLabel(content_scroll_frame, text="Nota: Esta ferramenta analisa um circuito RLC série fixo.",
                                  font=ctk.CTkFont(size=12), text_color="gray50")
        note_label.pack(pady=(10,10), side="bottom") 

        self.toggle_sweep_entries_state()

    # ... (todos os outros métodos: _validate_all_parameters, _calculate_sweep_data, etc. permanecem os mesmos)
    def _validate_all_parameters(self, for_sweep_mode, silent=True):
        params = {}
        error_messages = []
        try:
            params['r_val'] = float(self.r_entry.get())
            params['l_val'] = float(self.l_entry.get())
            params['c_val'] = float(self.c_entry.get())
            params['v_mag'] = float(self.v_mag_entry.get())
            params['v_phase_deg'] = float(self.v_phase_entry.get())

            if params['r_val'] < 0: error_messages.append("Resistor (R) não pode ser negativo.")
            if params['l_val'] < 0: error_messages.append("Indutor (L) não pode ser negativo.")
            if params['c_val'] < 0: error_messages.append("Capacitor (C) não pode ser negativo.")
            if params['v_mag'] < 0: error_messages.append("Tensão da Fonte (Vmag) não pode ser negativa.")

            if for_sweep_mode:
                params['freq_start'] = float(self.freq_start_entry.get())
                params['freq_end'] = float(self.freq_end_entry.get())
                params['num_points'] = int(self.num_points_entry.get())
                params['plot_choice'] = self.plot_variable_selected.get()

                if params['freq_start'] <= 0: error_messages.append("Frequência Inicial deve ser > 0.")
                if params['freq_end'] <= params['freq_start']: error_messages.append("Frequência Final deve ser > Frequência Inicial.")
                if params['num_points'] < 2: error_messages.append("Número de Pontos deve ser >= 2.")
            else: # Single frequency mode
                params['freq'] = float(self.freq_entry.get())
                if params['freq'] <= 0: error_messages.append("Frequência Única (f) deve ser maior que zero.")

            if error_messages:
                if not silent:
                    messagebox.showerror("Erro de Entrada", "\n".join(error_messages))
                return None, error_messages
            return params, None

        except ValueError:
            error_msg = "Valores numéricos inválidos detectados."
            if not silent:
                messagebox.showerror("Erro de Entrada", error_msg)
            return None, [error_msg]

    def _calculate_sweep_data(self, params):
        f0_resonance = None
        if params['l_val'] > 0 and params['c_val'] > 0:
            try:
                f0_resonance = 1 / (2 * math.pi * math.sqrt(params['l_val'] * params['c_val']))
            except ZeroDivisionError: 
                f0_resonance = None
        
        if params['freq_end'] / params['freq_start'] > 50: 
            try:
                frequencies = np.logspace(np.log10(params['freq_start']), np.log10(params['freq_end']), params['num_points'])
            except ValueError: 
                frequencies = np.linspace(params['freq_start'], params['freq_end'], params['num_points'])
        else:
            frequencies = np.linspace(params['freq_start'], params['freq_end'], params['num_points'])
            
        plot_data_y = []
        v_phase_rad = math.radians(params['v_phase_deg'])
        v_source_phasor_fixed = cmath.rect(params['v_mag'], v_phase_rad)

        for freq_current in frequencies:
            z_r_sweep = complex(params['r_val'], 0)
            z_l_sweep = complex(0, 2 * cmath.pi * freq_current * params['l_val']) if params['l_val'] > 0 else complex(0,0)
            if params['c_val'] > 0 and freq_current > 0 :
                 z_c_sweep = complex(0, -1 / (2 * cmath.pi * freq_current * params['c_val']))
            else: 
                 z_c_sweep = complex(float('inf'), 0)
            z_total_sweep = z_r_sweep + z_l_sweep + z_c_sweep
            i_total_sweep = v_source_phasor_fixed / z_total_sweep if abs(z_total_sweep) != float('inf') else complex(0,0)
            
            val_map = {
                "|Z_total|": lambda i, zr, zl, zc, zt, vs: abs(zt),
                "|I_total|": lambda i, zr, zl, zc, zt, vs: abs(i),
                "|V_R|":     lambda i, zr, zl, zc, zt, vs: abs(i * zr),
                "|V_L|":     lambda i, zr, zl, zc, zt, vs: abs(i * zl),
                "|V_C|":     lambda i, zr, zl, zc, zt, vs: abs(vs) if abs(zc) == float('inf') else abs(i * zc),
                "Fase(Z_total) (°)": lambda i, zr, zl, zc, zt, vs: math.degrees(cmath.phase(zt)) if abs(zt) != float('inf') else 0.0,
                "Fase(I_total) (°)": lambda i, zr, zl, zc, zt, vs: math.degrees(cmath.phase(i)) if abs(i) > 1e-12 else 0.0,
                "Fase(V_R) (°)":     lambda i, zr, zl, zc, zt, vs: math.degrees(cmath.phase(i * zr)) if abs(i * zr) > 1e-12 else 0.0,
                "Fase(V_L) (°)":     lambda i, zr, zl, zc, zt, vs: math.degrees(cmath.phase(i * zl)) if abs(i * zl) > 1e-12 else 0.0,
                "Fase(V_C) (°)":     lambda i, zr, zl, zc, zt, vs: math.degrees(cmath.phase(vs if abs(zc) == float('inf') else i * zc)) \
                                                                                  if abs(vs if abs(zc) == float('inf') else i * zc) > 1e-12 else 0.0
            }
            current_value_to_plot = 0.0
            if params['plot_choice'] in val_map:
                current_value_to_plot = val_map[params['plot_choice']](i_total_sweep, 
                                                             z_r_sweep, z_l_sweep, z_c_sweep, 
                                                             z_total_sweep, v_source_phasor_fixed)
            plot_data_y.append(current_value_to_plot)
        return frequencies, plot_data_y, f0_resonance

    def _handle_sweep_param_or_circuit_change(self, event=None, from_combobox_value=None):
        if not self.sweep_enabled_var.get():
            return

        params, errors = self._validate_all_parameters(for_sweep_mode=True, silent=True)

        if params:
            try:
                frequencies, plot_data_y, f0_calc = self._calculate_sweep_data(params)
                self.display_plot_in_popup(frequencies, plot_data_y, params['plot_choice'], f0_resonance=f0_calc)
                self.results_text.configure(state="normal")
                self.results_text.delete("1.0", "end")
                self.results_text.insert("1.0", f"Gráfico atualizado automaticamente: {params['plot_choice']}.")
                self.results_text.configure(state="disabled")
            except Exception as e:
                print(f"Erro ao recalcular varredura em tempo real: {e}")
        else:
            print(f"Parâmetros inválidos para atualização em tempo real: {errors}")

    def toggle_sweep_entries_state(self):
        if self.sweep_enabled_var.get():
            sweep_state = "normal"; single_freq_state = "disabled"
            self.results_text.configure(state="normal"); self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", "Modo de varredura habilitado. Configure e clique em Analisar, ou altere parâmetros para atualização automática do gráfico.")
            self.results_text.configure(state="disabled")
            self._handle_sweep_param_or_circuit_change() 
        else:
            sweep_state = "disabled"; single_freq_state = "normal"
            self.results_text.configure(state="normal"); self.results_text.delete("1.0", "end")
            self.results_text.configure(state="disabled")
            self.clear_plot_popup()
        
        self.freq_entry.configure(state=single_freq_state)
        self.freq_start_entry.configure(state=sweep_state)
        self.freq_end_entry.configure(state=sweep_state)
        self.num_points_entry.configure(state=sweep_state)
        self.plot_variable_combobox.configure(state=sweep_state)

    def clear_plot_popup(self):
        if self.plot_popup_window and self.plot_popup_window.winfo_exists():
            self.plot_popup_window.destroy()
        self.plot_popup_window = None
        self.fig_popup = None 
        self.ax_popup = None
        self.canvas_popup = None
            
    def clear_entries(self):
        self.r_entry.delete(0, "end"); self.r_entry.insert(0, "100")
        self.l_entry.delete(0, "end"); self.l_entry.insert(0, "0.1")
        self.c_entry.delete(0, "end"); self.c_entry.insert(0, "0.00001")
        self.v_mag_entry.delete(0, "end"); self.v_mag_entry.insert(0, "10")
        self.v_phase_entry.delete(0, "end"); self.v_phase_entry.insert(0, "0")
        self.freq_entry.delete(0, "end"); self.freq_entry.insert(0, "60")
        self.freq_start_entry.delete(0, "end"); self.freq_start_entry.insert(0, "1")
        self.freq_end_entry.delete(0, "end"); self.freq_end_entry.insert(0, "1000")
        self.num_points_entry.delete(0, "end"); self.num_points_entry.insert(0, "200")
        self.plot_variable_combobox.set(self.plot_variable_options[0])
        
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.configure(state="disabled")
        
        if self.sweep_enabled_var.get():
             self._handle_sweep_param_or_circuit_change()
        else:
            self.clear_plot_popup()

    def show_about_dialog_ctk(self):
        if self.about_dialog_window and self.about_dialog_window.winfo_exists():
            self.about_dialog_window.lift() 
            self.about_dialog_window.focus_set() 
            return
            
        self.about_dialog_window = ctk.CTkToplevel(self.master)
        self.about_dialog_window.title("Sobre Analisador de Circuito CA")
        self.about_dialog_window.geometry("450x340")
        self.about_dialog_window.transient(self.master) 
        self.about_dialog_window.update_idletasks() 
        try: 
            self.about_dialog_window.grab_set() 
        except tk.TclError as e: 
            print(f"Aviso: Falha ao executar grab_set imediatamente para 'Sobre': {e}.")
            self.about_dialog_window.after(100, self.about_dialog_window.grab_set)
        
        about_frame = ctk.CTkFrame(self.about_dialog_window, corner_radius=10)
        about_frame.pack(expand=True, fill="both", padx=15, pady=15)
        ctk.CTkLabel(about_frame, text="Analisador de Circuito CA Série RLC", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,10))
        info_text = ("Versão: 1.4.1 (CustomTkinter)\n\n" 
                     "Desenvolvido como exemplo de aplicação.\n\n"
                     "Funcionalidades:\n"
                     "- Análise de circuito RLC série em CA.\n"
                     "- Varredura de frequência com plotagem em tempo real (popup).\n"
                     "- Exibição da frequência de ressonância no gráfico.\n" 
                     "- Cálculo de impedâncias, correntes, tensões e potências.\n"
                     "- Barra de ferramentas no gráfico (Zoom, Pan, Salvar).") 
        ctk.CTkLabel(about_frame, text=info_text, justify="left", wraplength=380).pack(pady=10)
        close_button = ctk.CTkButton(about_frame, text="Fechar", command=self.about_dialog_window.destroy, width=100)
        close_button.pack(pady=20)
        
        self.master.update_idletasks()
        master_x = self.master.winfo_x(); master_y = self.master.winfo_y()
        master_width = self.master.winfo_width(); master_height = self.master.winfo_height()
        self.about_dialog_window.update_idletasks()
        popup_width = self.about_dialog_window.winfo_width(); popup_height = self.about_dialog_window.winfo_height()
        if popup_width <= 1 or popup_height <= 1: 
            try:
                geom_parts = self.about_dialog_window.geometry().split('+')[0].split('x')
                popup_width, popup_height = int(geom_parts[0]), int(geom_parts[1])
            except: popup_width, popup_height = 450, 340
        center_x = master_x + (master_width - popup_width) // 2
        center_y = master_y + (master_height - popup_height) // 2
        self.about_dialog_window.geometry(f"{popup_width}x{popup_height}+{center_x}+{center_y}")
        self.about_dialog_window.focus_set()

    def analyze_circuit(self): 
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end") 
        if self.sweep_enabled_var.get():
            self.perform_frequency_sweep(show_results_in_textbox=True)
        else:
            self.perform_single_frequency_analysis()
        self.results_text.configure(state="disabled")

    def perform_single_frequency_analysis(self):
        params, errors = self._validate_all_parameters(for_sweep_mode=False, silent=False)
        if not params:
            self.results_text.insert("1.0", "Erro de entrada:\n" + "\n".join(errors if errors else ["Valores inválidos."]))
            return

        output = ""
        try:
            r_val, l_val, c_val = params['r_val'], params['l_val'], params['c_val']
            v_mag, v_phase_deg, freq = params['v_mag'], params['v_phase_deg'], params['freq']
            v_phase_rad = math.radians(v_phase_deg)
            v_source_phasor = cmath.rect(v_mag, v_phase_rad)
            z_r = complex(r_val, 0)
            z_l = complex(0, 2 * cmath.pi * freq * l_val) if l_val > 0 else complex(0,0)
            z_c = complex(0, -1 / (2 * cmath.pi * freq * c_val)) if c_val > 0 and freq > 0 else complex(float('inf'), 0)
            z_total = z_r + z_l + z_c
            output = f"--- Análise em Frequência Única: {freq:.2f} Hz ---\n"
            output += f"R: {r_val} Ω, L: {l_val} H, C: {c_val} F\n"
            output += f"Fonte: {v_mag:.2f} V ∠ {v_phase_deg:.2f}°\n\n--- Resultados ---\n"
            i_total_phasor = complex(0,0)
            if abs(z_total) == float('inf'):
                output += f"Impedância Total (Z_total): Infinita (Circuito Aberto)\n"
                output += f"Corrente Total (I_total): {self.format_phasor(i_total_phasor, 'A')}\n"
                v_r_phasor, v_l_phasor = complex(0,0), complex(0,0); v_c_phasor = v_source_phasor
                output += f"Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                output += f"Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                output += f"Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                output += "---------------------------\nAnálise de Potência (Total):\n"
                output += "  Potência Aparente (|S|): 0.000 VA\n  Potência Ativa (P): 0.000 W\n"
                output += "  Potência Reativa (Q): 0.000 VAR\n  Fator de Potência (FP): N/A (circuito aberto)\n"
                output += "---------------------------\nVerificação LKT:\n"
                output += f"  Soma Fasorial (V_R+V_L+V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                output += f"  (Deveria ser igual à Tensão da Fonte: {self.format_phasor(v_source_phasor, 'V')})\n"
            else: 
                i_total_phasor = v_source_phasor / z_total 
                v_r_phasor = i_total_phasor * z_r; v_l_phasor = i_total_phasor * z_l; v_c_phasor = i_total_phasor * z_c
                output += f"Impedância Total (Z_total): {self.format_phasor(z_total, 'Ω')}\n"
                output += f"Corrente Total (I_total): {self.format_phasor(i_total_phasor, 'A')}\n"
                output += "---------------------------\n"
                output += f"Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                output += f"Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                output += f"Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                output += "---------------------------\nAnálise de Potência (Total):\n"
                s_complex = v_source_phasor * i_total_phasor.conjugate()
                p_real, q_reactive, s_apparent_mag = s_complex.real, s_complex.imag, abs(s_complex)
                power_factor = p_real / s_apparent_mag if s_apparent_mag != 0 else 0.0
                fp_type, epsilon = "(N/A)", 1e-9
                if abs(s_apparent_mag) < epsilon: fp_type = "(N/A - sem potência)"
                elif abs(q_reactive) < epsilon: fp_type = "(unitário)"
                elif q_reactive > 0: fp_type = "(atrasado - indutivo)"
                else: fp_type = "(adiantado - capacitivo)"
                output += f"  Potência Aparente (|S|): {s_apparent_mag:.3f} VA\n  Potência Ativa (P): {p_real:.3f} W\n"
                output += f"  Potência Reativa (Q): {q_reactive:.3f} VAR\n  Fator de Potência (FP): {power_factor:.3f} {fp_type}\n"
                v_sum_phasor = v_r_phasor + v_l_phasor + v_c_phasor
                output += "---------------------------\nVerificação LKT:\n"
                output += f"  Soma Fasorial (V_R+V_L+V_C): {self.format_phasor(v_sum_phasor, 'V')}\n"
                output += f"  (Deveria ser igual à Tensão da Fonte: {self.format_phasor(v_source_phasor, 'V')})\n"
            self.results_text.insert("1.0", output)
            self.clear_plot_popup()
        except Exception as e: 
            error_msg = f"Erro inesperado (Freq. Única): {str(e)}"
            messagebox.showerror("Erro Inesperado", error_msg)
            self.results_text.insert("1.0", error_msg)
            import traceback 
            traceback.print_exc()

    def perform_frequency_sweep(self, show_results_in_textbox=False):
        params, errors = self._validate_all_parameters(for_sweep_mode=True, silent=(not show_results_in_textbox))
        if not params:
            if show_results_in_textbox:
                 self.results_text.insert("1.0", "Erro de entrada na varredura:\n" + "\n".join(errors if errors else ["Valores inválidos."]))
            return

        output_summary = f"--- Varredura de Frequência ---\n"
        output_summary += f"Varrendo de {params['freq_start']:.2f} Hz a {params['freq_end']:.2f} Hz ({params['num_points']} pontos).\n"
        output_summary += f"Plotando: {params['plot_choice']}\n\n"
        
        try:
            frequencies, plot_data_y, f0_calc = self._calculate_sweep_data(params)
            self.display_plot_in_popup(frequencies, plot_data_y, params['plot_choice'], f0_resonance=f0_calc)
            
            if show_results_in_textbox:
                output_summary += "Varredura concluída. Gráfico exibido em nova janela.\n"
                if f0_calc is not None:
                    output_summary += f"Frequência de Ressonância (calculada): {f0_calc:.2f} Hz\n"
                self.results_text.insert("1.0", output_summary)
        except Exception as e:
            error_msg = f"Erro inesperado na varredura: {str(e)}"
            if show_results_in_textbox:
                messagebox.showerror("Erro Inesperado na Varredura", error_msg)
                self.results_text.insert("1.0", error_msg)
            else:
                print(error_msg)
            import traceback
            traceback.print_exc()

    def display_plot_in_popup(self, frequencies, plot_data_y, y_label_choice, f0_resonance=None):
        # Reutiliza ou cria a janela de plot e seus componentes matplotlib
        if not (self.plot_popup_window and self.plot_popup_window.winfo_exists()):
            self.plot_popup_window = ctk.CTkToplevel(self.master)
            self.plot_popup_window.title(f"Gráfico: {y_label_choice} vs Frequência")
            self.plot_popup_window.geometry("750x600")
            self.plot_popup_window.transient(self.master)
            self.plot_popup_window.protocol("WM_DELETE_WINDOW", self.clear_plot_popup)

            popup_main_frame = ctk.CTkFrame(self.plot_popup_window)
            popup_main_frame.pack(expand=True, fill="both", padx=5, pady=5)
            
            canvas_frame = ctk.CTkFrame(popup_main_frame, fg_color="transparent")
            canvas_frame.pack(side="top", fill="both", expand=True)

            self.fig_popup = Figure(figsize=(7, 5), dpi=100)
            self.ax_popup = self.fig_popup.add_subplot(111)
            self.canvas_popup = FigureCanvasTkAgg(self.fig_popup, master=canvas_frame)
            canvas_widget = self.canvas_popup.get_tk_widget()
            canvas_widget.pack(side="top", fill="both", expand=True)
            
            toolbar = NavigationToolbar2Tk(self.canvas_popup, popup_main_frame, pack_toolbar=False)
            toolbar.update()
            toolbar.pack(side="bottom", fill="x", pady=(5,0), padx=5)
        
        self.ax_popup.clear() # Limpa eixos para novo plot
        self.ax_popup.plot(frequencies, plot_data_y, marker='.', linestyle='-', markersize=3)
        self.ax_popup.set_title(f"{y_label_choice} vs Frequência")
        self.ax_popup.set_xlabel("Frequência (Hz)")
        self.ax_popup.set_ylabel(y_label_choice)
        self.ax_popup.grid(True, which="both", linestyle="--", linewidth=0.5)
        
        legend_handles = []
        if f0_resonance is not None and len(frequencies) > 0 and frequencies[0] <= f0_resonance <= frequencies[-1]:
            line_f0 = self.ax_popup.axvline(x=f0_resonance, color='red', linestyle='--', linewidth=1.2, label=f'$f_0 \\approx$ {f0_resonance:.2f} Hz')
            legend_handles.append(line_f0)
        
        if legend_handles:
            self.ax_popup.legend(handles=legend_handles, fontsize='small')

        if len(frequencies) > 1 and frequencies[-1] / frequencies[0] > 50:
             self.ax_popup.set_xscale('log')
        else:
             self.ax_popup.set_xscale('linear')
        
        is_magnitude_plot = "|" in y_label_choice
        if is_magnitude_plot and len(plot_data_y) > 1:
            positive_values = [d for d in plot_data_y if isinstance(d, (int, float)) and d > 1e-9 and d != float('inf')]
            if positive_values:
                min_val = min(positive_values)
                max_val = max(d for d in plot_data_y if isinstance(d, (int, float)) and d != float('inf'))
                if min_val > 0 and max_val / min_val > 1000:
                    self.ax_popup.set_yscale('log')
                else:
                    self.ax_popup.set_yscale('linear')
            else:
                self.ax_popup.set_yscale('linear')
        elif "Fase" not in y_label_choice :
             self.ax_popup.set_yscale('linear')

        self.fig_popup.tight_layout()
        self.canvas_popup.draw()

        if not self.plot_popup_window.winfo_viewable():
            self.plot_popup_window.deiconify()
        self.plot_popup_window.focus_set()
        self.plot_popup_window.lift()

    def format_phasor(self, complex_val, unit=""):
        if abs(complex_val) == float('inf'):
            return f"Infinito {unit}"
        mag = abs(complex_val)
        phase_rad = cmath.phase(complex_val)
        if mag < 1e-12: phase_rad = 0.0
        if self.angle_unit.get() == "degrees":
            phase_display = math.degrees(phase_rad)
            angle_symbol = "°"
        else: 
            phase_display = phase_rad
            angle_symbol = " rad"
        return f"{mag:.3f} {unit} ∠ {phase_display:.3f}{angle_symbol}"

if __name__ == '__main__':
    root = ctk.CTk()
    app = ACCircuitAnalyzerApp(root)
    root.mainloop()