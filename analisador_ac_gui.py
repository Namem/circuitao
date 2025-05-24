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
        master_window.title("Analisador de Circuito CA (CustomTkinter)")
        master_window.geometry("1250x850") 

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.angle_unit = tk.StringVar(value="degrees")
        self.plot_variable_options = ["|Z_total|", "|I_total|", "|V_R|", "|V_L|", "|V_C|",
                                      "Fase(Z_total) (°)", "Fase(I_total) (°)",
                                      "Fase(V_R) (°)", "Fase(V_L) (°)", "Fase(V_C) (°)"]
        self.plot_variable_selected = tk.StringVar(value=self.plot_variable_options[0])
        
        self.circuit_topology_var = tk.StringVar(value="Série") 

        self.about_dialog_window = None
        self.fig_embedded = None
        self.ax_embedded = None
        self.canvas_embedded = None
        self.toolbar_embedded = None

        self.error_border_color = "red"
        try:
            default_entry_color = ctk.ThemeManager.theme["CTkEntry"]["border_color"]
            current_mode = ctk.get_appearance_mode().lower()
            self.normal_border_color = default_entry_color[0] if isinstance(default_entry_color, list) and current_mode == "light" else (default_entry_color[1] if isinstance(default_entry_color, list) else default_entry_color)
        except KeyError: 
            self.normal_border_color = "gray50" 
        self.entry_widgets = {}

        main_app_frame = ctk.CTkFrame(master_window, fg_color="transparent")
        main_app_frame.pack(expand=True, fill="both", padx=5, pady=5)

        title_label = ctk.CTkLabel(main_app_frame, text="Analisador de Circuito CA",
                                   font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(5, 10))

        panels_frame = ctk.CTkFrame(main_app_frame, fg_color="transparent")
        panels_frame.pack(expand=True, fill="both", padx=5, pady=5)
        panels_frame.grid_columnconfigure(0, weight=1, minsize=420) 
        panels_frame.grid_columnconfigure(1, weight=2) 
        panels_frame.grid_rowconfigure(0, weight=1)    

        left_panel_scroll_frame = ctk.CTkScrollableFrame(panels_frame, corner_radius=10)
        left_panel_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=(0,10), pady=0)

        topology_main_label = ctk.CTkLabel(left_panel_scroll_frame, text="Configuração do Circuito",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        topology_main_label.pack(pady=(10,5), anchor="w", padx=10)
        
        topology_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        topology_frame.pack(pady=(0,10), padx=10, fill="x")
        ctk.CTkLabel(topology_frame, text="Topologia:").pack(side="left", padx=(10,10), pady=10)
        self.topology_selector = ctk.CTkSegmentedButton(
            topology_frame,
            values=["Série", "Paralelo"],
            variable=self.circuit_topology_var,
            command=self._trigger_realtime_plot_update 
        )
        self.topology_selector.pack(side="left", expand=True, fill="x", padx=10, pady=10)

        input_section_label = ctk.CTkLabel(left_panel_scroll_frame, text="Parâmetros do Circuito e Fonte",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        input_section_label.pack(pady=(10,5), anchor="w", padx=10)
        input_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        input_frame.pack(fill="x", padx=10, pady=(0,10))
        input_frame.grid_columnconfigure(1, weight=1)
        entry_width = 150 
        
        ctk.CTkLabel(input_frame, text="Resistor (R) [Ω]:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.r_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 100")
        self.r_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew"); self.r_entry.insert(0, "10")
        self.r_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.r_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['r_val'] = self.r_entry

        ctk.CTkLabel(input_frame, text="Indutor (L) [H]:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.l_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0.01")
        self.l_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew"); self.l_entry.insert(0, "0.01")
        self.l_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.l_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['l_val'] = self.l_entry

        ctk.CTkLabel(input_frame, text="Capacitor (C) [F]:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.c_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0.00001")
        self.c_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew"); self.c_entry.insert(0, "0.00001")
        self.c_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.c_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['c_val'] = self.c_entry

        ctk.CTkLabel(input_frame, text="Tensão Fonte (Vmag) [V]:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.v_mag_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 10")
        self.v_mag_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew"); self.v_mag_entry.insert(0, "10")
        self.v_mag_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.v_mag_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['v_mag'] = self.v_mag_entry
        
        ctk.CTkLabel(input_frame, text="Fase Fonte (θv) [°]:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.v_phase_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0")
        self.v_phase_entry.grid(row=4, column=1, padx=10, pady=8, sticky="ew"); self.v_phase_entry.insert(0, "0")
        self.v_phase_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.v_phase_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['v_phase_deg'] = self.v_phase_entry

        ctk.CTkLabel(input_frame, text="Freq. para Detalhes (Hz):").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.freq_details_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Opcional (Ex: 159)")
        self.freq_details_entry.grid(row=5, column=1, padx=10, pady=8, sticky="ew"); self.freq_details_entry.insert(0, "159")
        self.entry_widgets['freq_details'] = self.freq_details_entry

        output_options_label = ctk.CTkLabel(left_panel_scroll_frame, text="Opções de Saída", font=ctk.CTkFont(size=16, weight="bold"))
        output_options_label.pack(pady=(10,5), anchor="w", padx=10)
        output_options_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        output_options_frame.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(output_options_frame, text="Unidade Ângulo (Saída):").pack(side="left", padx=(10,5), pady=10)
        degrees_radio = ctk.CTkRadioButton(output_options_frame, text="Graus (°)", variable=self.angle_unit, value="degrees", command=self._trigger_realtime_plot_update)
        degrees_radio.pack(side="left", padx=5, pady=10)
        radians_radio = ctk.CTkRadioButton(output_options_frame, text="Radianos (rad)", variable=self.angle_unit, value="radians", command=self._trigger_realtime_plot_update)
        radians_radio.pack(side="left", padx=5, pady=10)

        sweep_section_label = ctk.CTkLabel(left_panel_scroll_frame, text="Parâmetros da Varredura de Frequência", font=ctk.CTkFont(size=16, weight="bold"))
        sweep_section_label.pack(pady=(15,5), anchor="w", padx=10)
        sweep_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        sweep_frame.pack(fill="x", padx=10, pady=(0,10))
        sweep_frame.grid_columnconfigure(1, weight=1); sweep_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(sweep_frame, text="Freq. Inicial (Hz):").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.freq_start_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 50")
        self.freq_start_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew"); self.freq_start_entry.insert(0, "50")
        self.freq_start_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.freq_start_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['freq_start'] = self.freq_start_entry

        ctk.CTkLabel(sweep_frame, text="Freq. Final (Hz):").grid(row=0, column=2, padx=10, pady=8, sticky="w")
        self.freq_end_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1000")
        self.freq_end_entry.grid(row=0, column=3, padx=10, pady=8, sticky="ew"); self.freq_end_entry.insert(0, "1000")
        self.freq_end_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.freq_end_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['freq_end'] = self.freq_end_entry

        ctk.CTkLabel(sweep_frame, text="Nº de Pontos:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.num_points_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 300")
        self.num_points_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew"); self.num_points_entry.insert(0, "300")
        self.num_points_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.num_points_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['num_points'] = self.num_points_entry

        ctk.CTkLabel(sweep_frame, text="Plotar Grandeza:").grid(row=1, column=2, padx=10, pady=8, sticky="w")
        self.plot_variable_combobox = ctk.CTkComboBox(sweep_frame, values=self.plot_variable_options,
                                                      variable=self.plot_variable_selected, state="readonly",
                                                      command=lambda choice: self._trigger_realtime_plot_update(from_combobox_value=choice))
        self.plot_variable_combobox.grid(row=1, column=3, padx=10, pady=8, sticky="ew")

        action_buttons_frame = ctk.CTkFrame(left_panel_scroll_frame, fg_color="transparent")
        action_buttons_frame.pack(pady=20, fill="x")
        analyze_button = ctk.CTkButton(action_buttons_frame, text="Analisar e Plotar", command=self.analyze_circuit)
        analyze_button.pack(side="left", padx=5, expand=True)
        clear_button = ctk.CTkButton(action_buttons_frame, text="Limpar", command=self.clear_entries)
        clear_button.pack(side="left", padx=5, expand=True)
        about_button = ctk.CTkButton(action_buttons_frame, text="Sobre", command=self.show_about_dialog_ctk)
        about_button.pack(side="left", padx=5, expand=True)

        note_label = ctk.CTkLabel(left_panel_scroll_frame, text="Nota: Analisa circuitos RLC Série ou Paralelo.", font=ctk.CTkFont(size=12), text_color="gray50")
        note_label.pack(pady=(20,10), side="bottom")

        right_panel_frame = ctk.CTkFrame(panels_frame, corner_radius=10)
        right_panel_frame.grid(row=0, column=1, sticky="nsew", padx=(10,0), pady=0)
        right_panel_frame.grid_rowconfigure(0, weight=1, minsize=200) 
        right_panel_frame.grid_rowconfigure(1, weight=3) 
        right_panel_frame.grid_columnconfigure(0, weight=1)

        results_section_label_text = ctk.CTkLabel(right_panel_frame, text="Resultados da Análise", font=ctk.CTkFont(size=16, weight="bold"))
        results_section_label_text.grid(row=0, column=0, pady=(10,0), padx=10, sticky="nw")
        self.results_text = ctk.CTkTextbox(right_panel_frame, corner_radius=6, wrap="word", font=ctk.CTkFont(family="monospace", size=12))
        self.results_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=(40,10))
        self.results_text.configure(state="disabled")

        plot_frame_label = ctk.CTkLabel(right_panel_frame, text="Gráfico da Varredura de Frequência", font=ctk.CTkFont(size=16, weight="bold"))
        plot_frame_label.grid(row=1, column=0, pady=(10,0), padx=10, sticky="nw")
        self.plot_frame_embedded = ctk.CTkFrame(right_panel_frame, corner_radius=6)
        self.plot_frame_embedded.grid(row=1, column=0, sticky="nsew", padx=10, pady=(40,10))
        self.plot_frame_embedded.grid_rowconfigure(0, weight=1) 
        self.plot_frame_embedded.grid_columnconfigure(0, weight=1)
        
        self.fig_embedded = Figure(figsize=(5, 3.5), dpi=100) 
        self.ax_embedded = self.fig_embedded.add_subplot(111)
        self.canvas_embedded = FigureCanvasTkAgg(self.fig_embedded, master=self.plot_frame_embedded)
        canvas_widget_embedded = self.canvas_embedded.get_tk_widget()
        canvas_widget_embedded.pack(side="top", fill="both", expand=True, padx=2, pady=2)
        
        self.toolbar_embedded = NavigationToolbar2Tk(self.canvas_embedded, self.plot_frame_embedded, pack_toolbar=False)
        self.toolbar_embedded.update()
        self.toolbar_embedded.pack(side="bottom", fill="x")
        
        self._clear_embedded_plot()
        self._trigger_realtime_plot_update()

    def _set_entry_error_style(self, entry_key, is_error=True):
        if entry_key in self.entry_widgets:
            widget = self.entry_widgets[entry_key]
            target_color = self.error_border_color if is_error else self.normal_border_color
            if not isinstance(target_color, str): 
                current_mode = ctk.get_appearance_mode().lower()
                if isinstance(ctk.ThemeManager.theme["CTkEntry"]["border_color"], list):
                    default_theme_color = ctk.ThemeManager.theme["CTkEntry"]["border_color"]
                    target_color = default_theme_color[0] if current_mode == "light" else default_theme_color[1]
                else: 
                    target_color = "gray50" if not is_error else "red"
            widget.configure(border_color=target_color)
    
    def _clear_all_entry_error_styles(self):
        for widget_key in self.entry_widgets: 
            self._set_entry_error_style(widget_key, is_error=False)

    def _validate_all_parameters(self, silent=True, check_detail_freq=False):
        self._clear_all_entry_error_styles()
        params = {}
        error_messages = []
        error_fields = [] 

        def get_float_param(entry_widget, param_name, human_name):
            try:
                val = float(entry_widget.get())
                params[param_name] = val; return val
            except ValueError:
                error_messages.append(f"{human_name} inválido(a)."); error_fields.append(param_name); return None

        def get_int_param(entry_widget, param_name, human_name):
            try:
                val = int(entry_widget.get())
                params[param_name] = val; return val
            except ValueError:
                error_messages.append(f"{human_name} inválido(a)."); error_fields.append(param_name); return None
        
        params['topology'] = self.circuit_topology_var.get()

        get_float_param(self.r_entry, 'r_val', "Resistor (R)")
        get_float_param(self.l_entry, 'l_val', "Indutor (L)")
        get_float_param(self.c_entry, 'c_val', "Capacitor (C)")
        get_float_param(self.v_mag_entry, 'v_mag', "Tensão Fonte (Vmag)")
        get_float_param(self.v_phase_entry, 'v_phase_deg', "Fase Fonte (θv)")

        if 'r_val' in params:
            if params['r_val'] < 0: 
                error_messages.append("Resistor (R) não pode ser negativo."); error_fields.append('r_val')
            # R=0 é problemático para paralelo, mas Z_R=0 é ok para série (curto)
            # A lógica de cálculo de Y_R tratará R=0 para paralelo
            if params['r_val'] == 0 and params['topology'] == "Paralelo" and not silent: # Aviso específico para usuário
                 error_messages.append("Atenção: R=0 em paralelo representa um curto-circuito total."); error_fields.append('r_val')


        if 'l_val' in params and params['l_val'] < 0: error_messages.append("Indutor (L) não pode ser negativo."); error_fields.append('l_val')
        if 'c_val' in params and params['c_val'] < 0: error_messages.append("Capacitor (C) não pode ser negativo."); error_fields.append('c_val')
        if 'v_mag' in params and params['v_mag'] < 0: error_messages.append("Tensão da Fonte (Vmag) não pode ser negativa."); error_fields.append('v_mag')

        get_float_param(self.freq_start_entry, 'freq_start', "Frequência Inicial")
        get_float_param(self.freq_end_entry, 'freq_end', "Frequência Final")
        get_int_param(self.num_points_entry, 'num_points', "Número de Pontos")
        params['plot_choice'] = self.plot_variable_selected.get()

        if 'freq_start' in params and params['freq_start'] <= 0: error_messages.append("Frequência Inicial deve ser > 0."); error_fields.append('freq_start')
        if 'freq_end' in params and 'freq_start' in params and params.get('freq_start') is not None and params['freq_end'] <= params['freq_start']: 
            error_messages.append("Frequência Final deve ser > Frequência Inicial."); error_fields.append('freq_end')
        if 'num_points' in params and params['num_points'] < 2: error_messages.append("Número de Pontos deve ser >= 2."); error_fields.append('num_points')
        
        params['freq_details'] = None
        if check_detail_freq:
            freq_details_str = self.freq_details_entry.get()
            if freq_details_str: # Apenas tenta converter e validar se não estiver vazio
                detail_freq_val = get_float_param(self.freq_details_entry, 'freq_details_val', "Frequência para Detalhes") 
                if detail_freq_val is not None: 
                    if detail_freq_val <= 0:
                        error_messages.append("Frequência para Detalhes deve ser > 0."); error_fields.append('freq_details')
                    else:
                        params['freq_details'] = detail_freq_val 
        
        for field_key in set(error_fields): self._set_entry_error_style(field_key, is_error=True)
        if error_messages:
            unique_error_messages = list(dict.fromkeys(error_messages))
            if not silent: messagebox.showerror("Erro de Entrada", "\n".join(unique_error_messages))
            return None, unique_error_messages
        return params, None

    def _calculate_sweep_data(self, params):
        f0_resonance = None
        topology = params.get('topology', "Série")
        r_val = params.get('r_val', 0)
        l_val = params.get('l_val', 0)
        c_val = params.get('c_val', 0)

        if l_val > 0 and c_val > 0:
            try: f0_resonance = 1 / (2 * math.pi * math.sqrt(l_val * c_val))
            except ZeroDivisionError: f0_resonance = None
        
        freq_start = params.get('freq_start', 1)
        freq_end = params.get('freq_end', 1000)
        num_points = params.get('num_points', 100)

        if freq_end > freq_start and freq_start > 0 and freq_end / freq_start > 50 : 
            try: frequencies = np.logspace(np.log10(freq_start), np.log10(freq_end), num_points)
            except ValueError: frequencies = np.linspace(freq_start, freq_end, num_points)
        else: frequencies = np.linspace(freq_start, freq_end, num_points)
            
        plot_data_y = []
        v_phase_rad = math.radians(params.get('v_phase_deg', 0))
        v_source_phasor_fixed = cmath.rect(params.get('v_mag', 0), v_phase_rad)

        for freq_current in frequencies:
            # Impedâncias individuais
            z_r = complex(r_val, 0) if r_val > 0 else (complex(1e-12,0) if topology == "Paralelo" and r_val == 0 else complex(0,0))
            z_l = complex(0, 2*cmath.pi*freq_current*l_val) if l_val > 0 and freq_current > 0 else (complex(0,0) if l_val == 0 else complex(0, 1e-12 if freq_current == 0 and l_val > 0 else float('inf'))) # L=0 é curto; L>0 e f=0 é curto
            if l_val == 0: z_l = complex(0,0)

            z_c = complex(0, -1/(2*cmath.pi*freq_current*c_val)) if c_val > 0 and freq_current > 0 else complex(float('inf'), 0)
            if c_val == 0 : z_c = complex(float('inf'),0)


            z_total_sweep, i_total_sweep_source = complex(0,0), complex(0,0)
            v_r_calc, v_l_calc, v_c_calc = complex(0,0), complex(0,0), complex(0,0)

            if topology == "Série":
                z_total_sweep = z_r + z_l + z_c
                i_total_sweep_source = v_source_phasor_fixed / z_total_sweep if abs(z_total_sweep) > 1e-12 else (v_source_phasor_fixed / (1e-12 +0j) if abs(z_total_sweep) < 1e-12 and abs(v_source_phasor_fixed) > 1e-12 else complex(0,0))
                if abs(z_total_sweep) == float('inf'): i_total_sweep_source = complex(0,0)
                v_r_calc = i_total_sweep_source * z_r
                v_l_calc = i_total_sweep_source * z_l
                v_c_calc = i_total_sweep_source * z_c if abs(z_c) != float('inf') else (v_source_phasor_fixed - v_r_calc - v_l_calc if abs(i_total_sweep_source) < 1e-9 else i_total_sweep_source * z_c) # Ajuste para Vc
            
            elif topology == "Paralelo":
                y_r = 1/z_r if abs(z_r) > 1e-12 else complex(float('inf'),0) 
                y_l = 1/z_l if abs(z_l) > 1e-12 else (complex(float('inf'),0) if l_val > 0 else complex(0,0))
                y_c = 1/z_c if abs(z_c) > 1e-12 else complex(0,0)       

                y_total_sweep = y_r + y_l + y_c
                z_total_sweep = 1/y_total_sweep if abs(y_total_sweep) > 1e-12 else complex(float('inf'),0)
                i_total_sweep_source = v_source_phasor_fixed * y_total_sweep
                v_r_calc = v_l_calc = v_c_calc = v_source_phasor_fixed # Tensão é a mesma
            
            val_map = {
                "|Z_total|": lambda i, vr, vl, vc, zr, zl, zc, zt, vs: abs(zt),
                "|I_total|": lambda i, vr, vl, vc, zr, zl, zc, zt, vs: abs(i),
                "|V_R|":     lambda i, vr, vl, vc, zr, zl, zc, zt, vs: abs(vr),
                "|V_L|":     lambda i, vr, vl, vc, zr, zl, zc, zt, vs: abs(vl),
                "|V_C|":     lambda i, vr, vl, vc, zr, zl, zc, zt, vs: abs(vc),
                "Fase(Z_total) (°)": lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(zt)) if abs(zt)!=float('inf') and abs(zt) > 1e-12 else 0.0,
                "Fase(I_total) (°)": lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(i)) if abs(i) > 1e-12 else 0.0,
                "Fase(V_R) (°)":     lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(vr)) if abs(vr) > 1e-12 else 0.0,
                "Fase(V_L) (°)":     lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(vl)) if abs(vl) > 1e-12 else 0.0,
                "Fase(V_C) (°)":     lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(vc)) if abs(vc) > 1e-12 else 0.0
            }
            current_value_to_plot = 0.0
            if params.get('plot_choice') in val_map:
                current_value_to_plot = val_map[params['plot_choice']](i_total_sweep_source, 
                                                             v_r_calc, v_l_calc, v_c_calc,
                                                             z_r, z_l, z_c, 
                                                             z_total_sweep, v_source_phasor_fixed)
            plot_data_y.append(current_value_to_plot)
        return frequencies, plot_data_y, f0_resonance

    def _trigger_realtime_plot_update(self, event=None, from_combobox_value=None): # Renomeado
        params, errors = self._validate_all_parameters(silent=True, check_detail_freq=False)
        if params:
            try:
                frequencies, plot_data_y, f0_calc = self._calculate_sweep_data(params)
                extremum_info = self._find_extremum(frequencies, plot_data_y, params['plot_choice'], params['topology'])
                self._update_embedded_plot(frequencies, plot_data_y, params['plot_choice'], f0_resonance=f0_calc, extremum_info=extremum_info)
                self.results_text.configure(state="normal")
                self.results_text.delete("1.0", "end")
                self.results_text.insert("1.0", f"Gráfico ({params['topology']}) atualizado: {params['plot_choice']}.\n(Pressione 'Analisar e Plotar' para resultados textuais)")
                self.results_text.configure(state="disabled")
            except Exception as e:
                print(f"Erro ao recalcular varredura em tempo real: {e}")
                import traceback; traceback.print_exc()
                self._clear_embedded_plot() 
        else:
            print(f"Parâmetros inválidos para atualização em tempo real (trigger): {errors}")
            self._clear_embedded_plot()

    def _find_extremum(self, frequencies, data_y, plot_choice, topology):
        # ... (Permanece o mesmo da versão anterior, mas usa topology) ...
        if not data_y or not isinstance(data_y, (list, np.ndarray)) or len(data_y) == 0: return None
        valid_data_y = [val for val in data_y if isinstance(val, (int, float)) and not (math.isinf(val) or math.isnan(val))]
        if not valid_data_y: return None
        extremum_type, extremum_value, extremum_freq = None, None, None
        if "|" in plot_choice: 
            if topology == "Série":
                if "Z_total" in plot_choice: extremum_type = "min"
                else: extremum_type = "max" 
            elif topology == "Paralelo":
                if "I_total" in plot_choice: extremum_type = "min" 
                elif "Z_total" in plot_choice: extremum_type = "max" 
                else: extremum_type = "max" 
            if extremum_type == "min": extremum_value = min(valid_data_y) if valid_data_y else None
            elif extremum_type == "max": extremum_value = max(valid_data_y) if valid_data_y else None
            else: return None 
            if extremum_value is None: return None
            try:
                original_indices = [i for i, val in enumerate(data_y) if val == extremum_value]
                if original_indices:
                     extremum_index = original_indices[0] 
                     extremum_freq = frequencies[extremum_index]
                else: return None
            except (ValueError, IndexError): return None
            return extremum_type, extremum_freq, extremum_value
        return None
            
    def _clear_embedded_plot(self): 
        if self.ax_embedded:
            self.ax_embedded.clear()
            self.ax_embedded.set_title("Aguardando Análise")
            self.ax_embedded.set_xlabel("Frequência (Hz)")
            self.ax_embedded.set_ylabel("Grandeza")
            self.ax_embedded.grid(True, which="both", linestyle="--", linewidth=0.5)
            if self.fig_embedded: self.fig_embedded.tight_layout()
            if self.canvas_embedded: self.canvas_embedded.draw()
            
    def clear_entries(self):
        # ... (Atualizado para novos valores padrão de teste) ...
        self._clear_all_entry_error_styles()
        self.r_entry.delete(0, "end"); self.r_entry.insert(0, "10") 
        self.l_entry.delete(0, "end"); self.l_entry.insert(0, "0.01")
        self.c_entry.delete(0, "end"); self.c_entry.insert(0, "0.00001")
        self.v_mag_entry.delete(0, "end"); self.v_mag_entry.insert(0, "10")
        self.v_phase_entry.delete(0, "end"); self.v_phase_entry.insert(0, "0")
        self.freq_details_entry.delete(0, "end"); self.freq_details_entry.insert(0, "159") 
        self.freq_start_entry.delete(0, "end"); self.freq_start_entry.insert(0, "50")
        self.freq_end_entry.delete(0, "end"); self.freq_end_entry.insert(0, "1000")
        self.num_points_entry.delete(0, "end"); self.num_points_entry.insert(0, "300")
        self.plot_variable_combobox.set(self.plot_variable_options[0])
        self.angle_unit.set("degrees")
        self.circuit_topology_var.set("Série")
        
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.configure(state="disabled")
        self._trigger_realtime_plot_update()

    def show_about_dialog_ctk(self):
        # ... (Atualizar versão e funcionalidades) ...
        if self.about_dialog_window and self.about_dialog_window.winfo_exists():
            self.about_dialog_window.lift(); self.about_dialog_window.focus_set(); return
        self.about_dialog_window = ctk.CTkToplevel(self.master)
        self.about_dialog_window.title("Sobre Analisador de Circuito CA")
        self.about_dialog_window.geometry("450x400")
        self.about_dialog_window.transient(self.master) 
        self.about_dialog_window.update_idletasks() 
        try: self.about_dialog_window.grab_set() 
        except tk.TclError: self.about_dialog_window.after(100, self.about_dialog_window.grab_set)
        about_frame = ctk.CTkFrame(self.about_dialog_window, corner_radius=10)
        about_frame.pack(expand=True, fill="both", padx=15, pady=15)
        ctk.CTkLabel(about_frame, text="Analisador de Circuito CA", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,10))
        info_text = ("Versão: 1.6.0 (CustomTkinter)\n\n" 
                     "Desenvolvido como exemplo de aplicação.\n\n"
                     "Funcionalidades:\n"
                     "- Análise de circuito RLC Série e Paralelo.\n" 
                     "- Varredura de frequência com plotagem em tempo real (incorporada).\n"
                     "- Exibição da frequência de ressonância no gráfico.\n"
                     "- Marcadores de pico/mínimo no gráfico.\n"
                     "- Cálculo de impedâncias, correntes, tensões e potências (total e por componente).\n" # ATUALIZADO
                     "- Barra de ferramentas no gráfico (Zoom, Pan, Salvar).\n"
                     "- Análise de texto e gráfico simultâneos (layout de painéis).\n" # ATUALIZADO
                     "- Feedback visual para entradas inválidas.") 
        ctk.CTkLabel(about_frame, text=info_text, justify="left", wraplength=380).pack(pady=10)
        close_button = ctk.CTkButton(about_frame, text="Fechar", command=self.about_dialog_window.destroy, width=100)
        close_button.pack(pady=20)
        self.master.update_idletasks()
        master_x=self.master.winfo_x(); master_y=self.master.winfo_y()
        master_width=self.master.winfo_width(); master_height=self.master.winfo_height()
        self.about_dialog_window.update_idletasks()
        popup_width=self.about_dialog_window.winfo_width(); popup_height=self.about_dialog_window.winfo_height()
        if popup_width<=1 or popup_height<=1: 
            try:
                geom_parts=self.about_dialog_window.geometry().split('+')[0].split('x')
                popup_width,popup_height=int(geom_parts[0]),int(geom_parts[1])
            except: popup_width,popup_height=450,400
        center_x=master_x+(master_width-popup_width)//2; center_y=master_y+(master_height-popup_height)//2
        self.about_dialog_window.geometry(f"{popup_width}x{popup_height}+{center_x}+{center_y}")
        self.about_dialog_window.focus_set()

    def analyze_circuit(self): 
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end") 
        self._clear_all_entry_error_styles()

        params, errors = self._validate_all_parameters(silent=False, check_detail_freq=True)
        
        if not params:
            self.results_text.insert("1.0", "Erro de entrada:\n" + "\n".join(errors if errors else ["Valores inválidos."]))
            self._clear_embedded_plot() 
            self.results_text.configure(state="disabled")
            return

        output_text = ""
        try:
            frequencies, plot_data_y, f0_calc = self._calculate_sweep_data(params)
            extremum_info = self._find_extremum(frequencies, plot_data_y, params['plot_choice'], params['topology'])
            self._update_embedded_plot(frequencies, plot_data_y, params['plot_choice'], f0_resonance=f0_calc, extremum_info=extremum_info)
            
            output_text += f"--- Resumo da Varredura ({params['topology']}) ---\n"
            output_text += f"Intervalo: {params['freq_start']:.2f} Hz a {params['freq_end']:.2f} Hz ({params['num_points']} pontos).\n"
            output_text += f"Grandeza Plotada: {params['plot_choice']}\n"
            if f0_calc is not None:
                output_text += f"Frequência de Ressonância (Teórica): {f0_calc:.2f} Hz\n"
            if extremum_info:
                 output_text += f"Ponto Extremo ({extremum_info[0]}): {extremum_info[2]:.3f} em {extremum_info[1]:.2f} Hz\n"
            output_text += "-------------------------------------------\n\n"

            if params.get('freq_details') is not None:
                output_text += self._get_single_frequency_analysis_details(params, params['freq_details'])
            else:
                output_text += "Nenhuma frequência para análise detalhada foi fornecida ou era inválida.\n"
            
            self.results_text.insert("1.0", output_text)

        except Exception as e:
            error_msg = f"Erro inesperado durante a análise: {str(e)}"
            messagebox.showerror("Erro Inesperado", error_msg)
            self.results_text.insert("1.0", error_msg)
            import traceback 
            traceback.print_exc()
        
        self.results_text.configure(state="disabled")

    def _get_single_frequency_analysis_details(self, circuit_params, specific_freq):
        output = ""
        try:
            r_val = circuit_params.get('r_val', 0)
            l_val = circuit_params.get('l_val', 0)
            c_val = circuit_params.get('c_val', 0)
            v_mag = circuit_params.get('v_mag', 0)
            v_phase_deg = circuit_params.get('v_phase_deg', 0)
            topology = circuit_params.get('topology', "Série")
            freq = specific_freq

            v_phase_rad = math.radians(v_phase_deg)
            v_source_phasor = cmath.rect(v_mag, v_phase_rad)
            
            # Impedâncias individuais
            if r_val == 0:
                z_r = complex(0,0) if topology == "Série" else complex(1e-12, 0) # Evita 1/0 em Y_R para paralelo
            else:
                z_r = complex(r_val, 0)

            xl = 0.0
            if l_val > 0 and freq > 0: 
                xl = 2 * cmath.pi * freq * l_val
                z_l = complex(0, xl)
            elif l_val == 0: 
                z_l = complex(0,0) # Curto para L=0
            else: # L > 0 e freq = 0
                z_l = complex(0,0) # Curto para L em DC

            xc = 0.0 # Xc em si (reatância)
            if c_val > 0 and freq > 0:
                xc = -1 / (2 * cmath.pi * freq * c_val) # Xc é negativo
                z_c = complex(0, xc)
            else: # C=0 ou freq=0 para C>0
                z_c = complex(float('inf'), 0) # Aberto

            z_total, i_total_source_phasor = complex(0,0), complex(0,0) # Renomeado para clareza
            v_r_phasor, v_l_phasor, v_c_phasor = complex(0,0), complex(0,0), complex(0,0)
            i_r_phasor, i_l_phasor, i_c_phasor = complex(0,0), complex(0,0), complex(0,0)
            p_r_comp, q_l_comp, q_c_comp = 0.0, 0.0, 0.0

            if topology == "Série":
                z_total = z_r + z_l + z_c
                if abs(z_total) < 1e-12: 
                     i_total_source_phasor = v_source_phasor / (1e-12 + 0j) if abs(v_source_phasor)>1e-12 else complex(0,0)
                elif abs(z_total) == float('inf'): i_total_source_phasor = complex(0,0)
                else: i_total_source_phasor = v_source_phasor / z_total
                
                v_r_phasor = i_total_source_phasor * z_r
                v_l_phasor = i_total_source_phasor * z_l
                v_c_phasor = i_total_source_phasor * z_c if abs(z_c) != float('inf') else (v_source_phasor - v_r_phasor - v_l_phasor if abs(i_total_source_phasor) < 1e-9 else i_total_source_phasor * z_c)
                i_r_phasor = i_l_phasor = i_c_phasor = i_total_source_phasor
                
                p_r_comp = (abs(i_total_source_phasor)**2) * r_val if r_val > 0 else 0.0
                if l_val > 0 and freq > 0: q_l_comp = (abs(i_total_source_phasor)**2) * xl
                if c_val > 0 and freq > 0: q_c_comp = (abs(i_total_source_phasor)**2) * xc 
            
            elif topology == "Paralelo":
                y_r = 1/z_r if abs(z_r) > 1e-12 else complex(float('inf'),0) 
                y_l = 1/z_l if abs(z_l) > 1e-12 else (complex(float('inf'),0) if l_val > 0 and freq > 0 else complex(0,0)) # Se L=0 ou freq=0 e L>0, ZL=0, YL=inf (curto)
                if l_val == 0: y_l = complex(float('inf'),0) # L=0 é curto, YL é infinito

                y_c = 1/z_c if abs(z_c) > 1e-12 else complex(0,0)
                if c_val == 0 : y_c = complex(0,0) # C=0 é aberto, YC=0

                y_total = y_r + y_l + y_c
                z_total = 1/y_total if abs(y_total) > 1e-12 else complex(float('inf'),0)
                i_total_source_phasor = v_source_phasor * y_total 
                v_r_phasor = v_l_phasor = v_c_phasor = v_source_phasor
                
                i_r_phasor = v_source_phasor * y_r if r_val > 0 else (v_source_phasor / z_r if r_val == 0 else complex(0,0)) # Corrente no R se R=0 é V/infinitesimal
                i_l_phasor = v_source_phasor * y_l if l_val > 0 and freq > 0 else (v_source_phasor / z_l if l_val == 0 and freq > 0 else complex(0,0))
                i_c_phasor = v_source_phasor * y_c if c_val > 0 and freq > 0 else complex(0,0)

                if r_val > 0: p_r_comp = (abs(v_source_phasor)**2) / r_val
                else: p_r_comp = abs(v_source_phasor * i_r_phasor.conjugate()).real # P = V I* se R=0 (curto ideal)
                
                if l_val > 0 and freq > 0: q_l_comp = (abs(v_source_phasor)**2) / xl if xl != 0 else (v_source_phasor * i_l_phasor.conjugate()).imag
                if c_val > 0 and freq > 0: q_c_comp = (abs(v_source_phasor)**2) / xc if xc != 0 else (v_source_phasor * i_c_phasor.conjugate()).imag
            
            output += f"--- Detalhes para Frequência: {freq:.2f} Hz ({topology}) ---\n"
            if abs(z_total) == float('inf') and topology == "Série": # Ajuste para evitar N/A se I_total_source_phasor for definido
                 output += f"  Impedância Total (Z_total): Infinita (Circuito Aberto)\n"
                 output += f"  Corrente Total (I_total Fonte): {self.format_phasor(i_total_source_phasor, 'A')}\n"
                 # ... (saída para tensões e potências como antes para circuito aberto série)
            else:
                output += f"  Impedância Total (Z_total): {self.format_phasor(z_total, 'Ω')}\n"
                output += f"  Corrente Total (I_total Fonte): {self.format_phasor(i_total_source_phasor, 'A')}\n"
                output += "  ---------------------------\n"
                if topology == "Série":
                    output += f"  Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                    output += f"  Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                    output += f"  Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                elif topology == "Paralelo":
                    output += f"  Tensão (V_R=V_L=V_C): {self.format_phasor(v_source_phasor, 'V')}\n"
                    output += f"  Corrente em R (I_R): {self.format_phasor(i_r_phasor, 'A')}\n"
                    output += f"  Corrente em L (I_L): {self.format_phasor(i_l_phasor, 'A')}\n"
                    output += f"  Corrente em C (I_C): {self.format_phasor(i_c_phasor, 'A')}\n"
            
            output += "  ---------------------------\n  Análise de Potência (Total da Fonte):\n"
            s_complex = v_source_phasor * i_total_source_phasor.conjugate()
            p_real,q_reactive,s_apparent_mag = s_complex.real,s_complex.imag,abs(s_complex)
            power_factor = p_real / s_apparent_mag if s_apparent_mag > 1e-9 else 0.0 # Evita divisão por S muito pequeno
            fp_type,epsilon = "(N/A)",1e-9
            if abs(s_apparent_mag) < epsilon: fp_type = "(N/A - sem potência significante)"
            elif abs(q_reactive) < epsilon: fp_type = "(unitário)"
            elif q_reactive > 0: fp_type = "(atrasado - indutivo)"
            else: fp_type = "(adiantado - capacitivo)"
            output += f"    Potência Aparente (|S|): {s_apparent_mag:.3f} VA\n    Potência Ativa (P): {p_real:.3f} W\n"
            output += f"    Potência Reativa (Q): {q_reactive:.3f} VAR\n    Fator de Potência (FP): {power_factor:.3f} {fp_type}\n"

            output += "  ---------------------------\n  Potências nos Componentes:\n"
            if abs(z_total) == float('inf') and topology == "Série":
                output += "    P_R: 0.000 W\n    Q_L: 0.000 VAR\n    Q_C: 0.000 VAR\n"
            else:
                output += f"    Potência Ativa no Resistor (P_R): {p_r_comp:.3f} W\n"
                output += f"    Potência Reativa no Indutor (Q_L): {q_l_comp:.3f} VAR\n"
                output += f"    Potência Reativa no Capacitor (Q_C): {q_c_comp:.3f} VAR\n"
                if abs(p_real) > 1e-9 or abs(p_r_comp) > 1e-9 : # Só verifica se P não for trivialmente zero
                    output += f"    (Verificação: P_R ≈ P_total? {'Sim' if math.isclose(p_r_comp, p_real, rel_tol=1e-3, abs_tol=1e-5) else 'Não'})\n"
                if abs(q_reactive) > 1e-9 or abs(q_l_comp + q_c_comp) > 1e-9: # Só verifica se Q não for trivialmente zero
                    output += f"    (Verificação: Q_L+Q_C ≈ Q_total? {'Sim' if math.isclose(q_l_comp + q_c_comp, q_reactive, rel_tol=1e-3, abs_tol=1e-5) else 'Não'})\n"
            return output
        except Exception as e:
            import traceback; traceback.print_exc()
            return f"  Erro ao calcular detalhes para {specific_freq} Hz ({topology}): {e}\n"

    def _update_embedded_plot(self, frequencies, plot_data_y, y_label_choice, f0_resonance=None, extremum_info=None):
        if not (self.fig_embedded and self.ax_embedded and self.canvas_embedded):
            print("Erro: Componentes do gráfico embutido não foram devidamente inicializados.")
            return 
        self.ax_embedded.clear(); legend_handles, legend_labels = [], []
        self.ax_embedded.plot(frequencies, plot_data_y, marker='.', linestyle='-', markersize=3)
        self.ax_embedded.set_title(f"{y_label_choice} vs Frequência ({self.circuit_topology_var.get()})")
        self.ax_embedded.set_xlabel("Frequência (Hz)"); self.ax_embedded.set_ylabel(y_label_choice)
        self.ax_embedded.grid(True, which="both", linestyle="--", linewidth=0.5)
        if f0_resonance is not None and len(frequencies)>0 and frequencies[0]<=f0_resonance<=frequencies[-1]:
            line_f0 = self.ax_embedded.axvline(x=f0_resonance, color='red', linestyle='--', linewidth=1.2)
            legend_handles.append(line_f0); legend_labels.append(f'$f_0 \\approx$ {f0_resonance:.2f} Hz')
        if extremum_info:
            etype, efreq, evalue = extremum_info
            marker_color='green' if etype=='max' else 'purple'; text_label=f"{etype.capitalize()}: {evalue:.3f}\n@ {efreq:.2f} Hz"
            self.ax_embedded.plot(efreq, evalue, marker='o', color=marker_color, markersize=7, fillstyle='none', markeredgewidth=1.5)
            y_min_plot, y_max_plot = self.ax_embedded.get_ylim()
            y_range_plot = y_max_plot - y_min_plot if y_max_plot > y_min_plot else 1.0
            offset_y_factor = 0.05 if etype == 'max' else -0.10
            offset_y = y_range_plot * offset_y_factor
            x_min_plot, x_max_plot = self.ax_embedded.get_xlim()
            offset_x_factor = 0.02 * (x_max_plot - x_min_plot) if self.ax_embedded.get_xscale() == 'linear' else efreq * 0.1 # Ajuste para log
            ha_align = 'left'; efreq_text = efreq + offset_x_factor
            if f0_resonance and abs(efreq - f0_resonance) < offset_x_factor : efreq_text = efreq - offset_x_factor * 2 ; ha_align = 'right'
            if efreq_text > x_max_plot * 0.9 : ha_align = 'right' ; efreq_text = efreq - offset_x_factor
            if efreq_text < x_min_plot * 1.1 and self.ax_embedded.get_xscale() == 'linear' : ha_align = 'left' ; efreq_text = efreq + offset_x_factor
            self.ax_embedded.annotate(text_label, xy=(efreq, evalue), xytext=(efreq_text, evalue + offset_y),
                                      arrowprops=dict(arrowstyle="->",connectionstyle="arc3,rad=.2"),
                                      fontsize=8, ha=ha_align, va='bottom' if etype == 'max' else 'top',
                                      bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7))
        if legend_handles: self.ax_embedded.legend(handles=legend_handles, labels=legend_labels, fontsize='small', loc='best')
        if len(frequencies) > 1 and frequencies[-1]/frequencies[0] > 50: self.ax_embedded.set_xscale('log')
        else: self.ax_embedded.set_xscale('linear')
        is_magnitude_plot = "|" in y_label_choice
        if is_magnitude_plot and len(plot_data_y) > 1:
            positive_values = [d for d in plot_data_y if isinstance(d,(int,float)) and d > 1e-9 and d != float('inf')]
            if positive_values:
                min_val=min(positive_values); max_val=max(d for d in plot_data_y if isinstance(d,(int,float)) and d != float('inf'))
                if min_val > 0 and max_val/min_val > 1000: self.ax_embedded.set_yscale('log')
                else: self.ax_embedded.set_yscale('linear')
            else: self.ax_embedded.set_yscale('linear')
        elif "Fase" not in y_label_choice: self.ax_embedded.set_yscale('linear')
        try: self.fig_embedded.tight_layout()
        except Exception: pass # Ignora erros do tight_layout que podem ocorrer transitoriamente
        self.canvas_embedded.draw()

    def format_phasor(self, complex_val, unit=""):
        if abs(complex_val) == float('inf'): return f"Infinito {unit}"
        mag = abs(complex_val); phase_rad = cmath.phase(complex_val)
        if mag < 1e-12: phase_rad = 0.0
        if self.angle_unit.get() == "degrees":
            phase_display = math.degrees(phase_rad); angle_symbol = "°"
        else: 
            phase_display = phase_rad; angle_symbol = " rad"
        return f"{mag:.3f} {unit} ∠ {phase_display:.3f}{angle_symbol}"

if __name__ == '__main__':
    root = ctk.CTk()
    app = ACCircuitAnalyzerApp(root)
    root.mainloop()