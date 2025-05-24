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
        master_window.geometry("1200x800") 

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.angle_unit = tk.StringVar(value="degrees")
        self.plot_variable_options = ["|Z_total|", "|I_total|", "|V_R|", "|V_L|", "|V_C|",
                                      "Fase(Z_total) (°)", "Fase(I_total) (°)",
                                      "Fase(V_R) (°)", "Fase(V_L) (°)", "Fase(V_C) (°)"]
        self.plot_variable_selected = tk.StringVar(value=self.plot_variable_options[0])
        
        self.about_dialog_window = None
        self.fig_embedded = None
        self.ax_embedded = None
        self.canvas_embedded = None
        self.toolbar_embedded = None

        self.error_border_color = "red"
        try:
            # Tenta obter a cor da borda do tema atual
            # Isso pode variar dependendo da versão do CTk e do tema
            default_entry_color = ctk.ThemeManager.theme["CTkEntry"]["border_color"]
            if isinstance(default_entry_color, list): # Se for uma lista [light_color, dark_color]
                 current_mode = ctk.get_appearance_mode().lower()
                 self.normal_border_color = default_entry_color[0] if current_mode == "light" else default_entry_color[1]
            else: # Se for uma string única
                 self.normal_border_color = default_entry_color
        except KeyError: # Fallback se a cor não puder ser determinada pelo tema
            self.normal_border_color = "gray50" 


        self.entry_widgets = {}

        main_app_frame = ctk.CTkFrame(master_window, fg_color="transparent")
        main_app_frame.pack(expand=True, fill="both", padx=5, pady=5)

        title_label = ctk.CTkLabel(main_app_frame, text="Analisador de Circuito CA Série RLC",
                                   font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(5, 10))

        panels_frame = ctk.CTkFrame(main_app_frame, fg_color="transparent")
        panels_frame.pack(expand=True, fill="both", padx=5, pady=5)
        panels_frame.grid_columnconfigure(0, weight=1, minsize=400) 
        panels_frame.grid_columnconfigure(1, weight=2) 
        panels_frame.grid_rowconfigure(0, weight=1)    

        left_panel_scroll_frame = ctk.CTkScrollableFrame(panels_frame, corner_radius=10)
        left_panel_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5), pady=0)

        input_section_label = ctk.CTkLabel(left_panel_scroll_frame, text="Parâmetros do Circuito e Fonte",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        input_section_label.pack(pady=(10,5), anchor="w", padx=10)
        input_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        input_frame.pack(fill="x", padx=10, pady=(0,10))
        input_frame.grid_columnconfigure(1, weight=1)
        entry_width = 150 
        
        ctk.CTkLabel(input_frame, text="Resistor (R) [Ω]:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.r_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 100")
        self.r_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.r_entry.insert(0, "100")
        self.r_entry.bind("<FocusOut>", self._handle_input_change_for_plot)
        self.r_entry.bind("<Return>", self._handle_input_change_for_plot)
        self.entry_widgets['r_val'] = self.r_entry

        ctk.CTkLabel(input_frame, text="Indutor (L) [H]:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.l_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0.1")
        self.l_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.l_entry.insert(0, "0.1")
        self.l_entry.bind("<FocusOut>", self._handle_input_change_for_plot)
        self.l_entry.bind("<Return>", self._handle_input_change_for_plot)
        self.entry_widgets['l_val'] = self.l_entry

        ctk.CTkLabel(input_frame, text="Capacitor (C) [F]:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.c_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0.00001")
        self.c_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        self.c_entry.insert(0, "0.00001")
        self.c_entry.bind("<FocusOut>", self._handle_input_change_for_plot)
        self.c_entry.bind("<Return>", self._handle_input_change_for_plot)
        self.entry_widgets['c_val'] = self.c_entry

        ctk.CTkLabel(input_frame, text="Tensão Fonte (Vmag) [V]:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.v_mag_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 10")
        self.v_mag_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")
        self.v_mag_entry.insert(0, "10")
        self.v_mag_entry.bind("<FocusOut>", self._handle_input_change_for_plot)
        self.v_mag_entry.bind("<Return>", self._handle_input_change_for_plot)
        self.entry_widgets['v_mag'] = self.v_mag_entry
        
        ctk.CTkLabel(input_frame, text="Fase Fonte (θv) [°]:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.v_phase_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0")
        self.v_phase_entry.grid(row=4, column=1, padx=10, pady=8, sticky="ew")
        self.v_phase_entry.insert(0, "0")
        self.v_phase_entry.bind("<FocusOut>", self._handle_input_change_for_plot)
        self.v_phase_entry.bind("<Return>", self._handle_input_change_for_plot)
        self.entry_widgets['v_phase_deg'] = self.v_phase_entry

        ctk.CTkLabel(input_frame, text="Freq. para Detalhes (Hz):").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.freq_details_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Opcional (Ex: 60)")
        self.freq_details_entry.grid(row=5, column=1, padx=10, pady=8, sticky="ew")
        self.freq_details_entry.insert(0, "60")
        self.entry_widgets['freq_details'] = self.freq_details_entry

        output_options_label = ctk.CTkLabel(left_panel_scroll_frame, text="Opções de Saída", font=ctk.CTkFont(size=16, weight="bold"))
        output_options_label.pack(pady=(10,5), anchor="w", padx=10)
        output_options_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        output_options_frame.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(output_options_frame, text="Unidade Ângulo (Saída):").pack(side="left", padx=(10,5), pady=10)
        degrees_radio = ctk.CTkRadioButton(output_options_frame, text="Graus (°)", variable=self.angle_unit, value="degrees", command=self._handle_input_change_for_plot)
        degrees_radio.pack(side="left", padx=5, pady=10)
        radians_radio = ctk.CTkRadioButton(output_options_frame, text="Radianos (rad)", variable=self.angle_unit, value="radians", command=self._handle_input_change_for_plot)
        radians_radio.pack(side="left", padx=5, pady=10)

        sweep_section_label = ctk.CTkLabel(left_panel_scroll_frame, text="Parâmetros da Varredura de Frequência", font=ctk.CTkFont(size=16, weight="bold"))
        sweep_section_label.pack(pady=(15,5), anchor="w", padx=10)
        sweep_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        sweep_frame.pack(fill="x", padx=10, pady=(0,10))
        sweep_frame.grid_columnconfigure(1, weight=1); sweep_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(sweep_frame, text="Freq. Inicial (Hz):").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.freq_start_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1")
        self.freq_start_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew"); self.freq_start_entry.insert(0, "1")
        self.freq_start_entry.bind("<FocusOut>", self._handle_input_change_for_plot)
        self.freq_start_entry.bind("<Return>", self._handle_input_change_for_plot)
        self.entry_widgets['freq_start'] = self.freq_start_entry

        ctk.CTkLabel(sweep_frame, text="Freq. Final (Hz):").grid(row=1, column=2, padx=10, pady=8, sticky="w")
        self.freq_end_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1000")
        self.freq_end_entry.grid(row=1, column=3, padx=10, pady=8, sticky="ew"); self.freq_end_entry.insert(0, "1000")
        self.freq_end_entry.bind("<FocusOut>", self._handle_input_change_for_plot)
        self.freq_end_entry.bind("<Return>", self._handle_input_change_for_plot)
        self.entry_widgets['freq_end'] = self.freq_end_entry

        ctk.CTkLabel(sweep_frame, text="Nº de Pontos:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.num_points_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 200")
        self.num_points_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew"); self.num_points_entry.insert(0, "200")
        self.num_points_entry.bind("<FocusOut>", self._handle_input_change_for_plot)
        self.num_points_entry.bind("<Return>", self._handle_input_change_for_plot)
        self.entry_widgets['num_points'] = self.num_points_entry

        ctk.CTkLabel(sweep_frame, text="Plotar Grandeza:").grid(row=2, column=2, padx=10, pady=8, sticky="w")
        self.plot_variable_combobox = ctk.CTkComboBox(sweep_frame, values=self.plot_variable_options,
                                                      variable=self.plot_variable_selected, state="readonly",
                                                      command=lambda choice: self._handle_input_change_for_plot(from_combobox_value=choice))
        self.plot_variable_combobox.grid(row=2, column=3, padx=10, pady=8, sticky="ew")

        action_buttons_frame = ctk.CTkFrame(left_panel_scroll_frame, fg_color="transparent")
        action_buttons_frame.pack(pady=20, fill="x")
        analyze_button = ctk.CTkButton(action_buttons_frame, text="Analisar e Plotar", command=self.analyze_circuit)
        analyze_button.pack(side="left", padx=5, expand=True)
        clear_button = ctk.CTkButton(action_buttons_frame, text="Limpar", command=self.clear_entries)
        clear_button.pack(side="left", padx=5, expand=True)
        about_button = ctk.CTkButton(action_buttons_frame, text="Sobre", command=self.show_about_dialog_ctk)
        about_button.pack(side="left", padx=5, expand=True)

        note_label = ctk.CTkLabel(left_panel_scroll_frame, text="Nota: Analisa circuito RLC série.", font=ctk.CTkFont(size=12), text_color="gray50")
        note_label.pack(pady=(20,10), side="bottom")

        right_panel_frame = ctk.CTkFrame(panels_frame, corner_radius=10)
        right_panel_frame.grid(row=0, column=1, sticky="nsew", padx=(5,0), pady=0)
        right_panel_frame.grid_rowconfigure(0, weight=1, minsize=200) 
        right_panel_frame.grid_rowconfigure(1, weight=2) 
        right_panel_frame.grid_columnconfigure(0, weight=1)

        results_section_label_text = ctk.CTkLabel(right_panel_frame, text="Resultados da Análise", font=ctk.CTkFont(size=16, weight="bold"))
        results_section_label_text.grid(row=0, column=0, pady=(10,0), padx=10, sticky="nw")
        self.results_text = ctk.CTkTextbox(right_panel_frame, corner_radius=10, wrap="word", font=ctk.CTkFont(family="monospace", size=13))
        self.results_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=(40,10))
        self.results_text.configure(state="disabled")

        plot_frame_label = ctk.CTkLabel(right_panel_frame, text="Gráfico da Varredura de Frequência", font=ctk.CTkFont(size=16, weight="bold"))
        plot_frame_label.grid(row=1, column=0, pady=(10,0), padx=10, sticky="nw")
        self.plot_frame_embedded = ctk.CTkFrame(right_panel_frame, corner_radius=10)
        self.plot_frame_embedded.grid(row=1, column=0, sticky="nsew", padx=10, pady=(40,10))
        self.plot_frame_embedded.grid_rowconfigure(0, weight=1) 
        self.plot_frame_embedded.grid_columnconfigure(0, weight=1)
        
        self.fig_embedded = Figure(figsize=(5, 3.5), dpi=100) 
        self.ax_embedded = self.fig_embedded.add_subplot(111)
        self.canvas_embedded = FigureCanvasTkAgg(self.fig_embedded, master=self.plot_frame_embedded)
        canvas_widget_embedded = self.canvas_embedded.get_tk_widget()
        canvas_widget_embedded.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        self.toolbar_embedded = NavigationToolbar2Tk(self.canvas_embedded, self.plot_frame_embedded, pack_toolbar=False)
        self.toolbar_embedded.update()
        self.toolbar_embedded.pack(side="bottom", fill="x")
        
        self._clear_embedded_plot()
        self._handle_input_change_for_plot() # Tenta um plot inicial com valores padrão

    def _set_entry_error_style(self, entry_key, is_error=True):
        if entry_key in self.entry_widgets:
            widget = self.entry_widgets[entry_key]
            if is_error:
                widget.configure(border_color=self.error_border_color)
            else:
                widget.configure(border_color=self.normal_border_color)
    
    def _clear_all_entry_error_styles(self):
        for widget in self.entry_widgets.values():
            widget.configure(border_color=self.normal_border_color)

    def _validate_all_parameters(self, silent=True, check_detail_freq=False):
        self._clear_all_entry_error_styles()
        params = {}
        error_messages = []
        error_fields = [] 

        # Helper para tentar converter e registrar erros
        def get_float_param(entry_widget, param_name, human_name):
            try:
                val = float(entry_widget.get())
                params[param_name] = val
                return val # Retorna o valor para validações subsequentes
            except ValueError:
                error_messages.append(f"{human_name} inválido(a).")
                error_fields.append(param_name)
                return None # Indica falha na conversão

        def get_int_param(entry_widget, param_name, human_name):
            try:
                val = int(entry_widget.get())
                params[param_name] = val
                return val
            except ValueError:
                error_messages.append(f"{human_name} inválido(a).")
                error_fields.append(param_name)
                return None
        
        get_float_param(self.r_entry, 'r_val', "Resistor (R)")
        get_float_param(self.l_entry, 'l_val', "Indutor (L)")
        get_float_param(self.c_entry, 'c_val', "Capacitor (C)")
        get_float_param(self.v_mag_entry, 'v_mag', "Tensão Fonte (Vmag)")
        get_float_param(self.v_phase_entry, 'v_phase_deg', "Fase Fonte (θv)")

        if 'r_val' in params and params['r_val'] < 0: error_messages.append("Resistor (R) não pode ser negativo."); error_fields.append('r_val')
        if 'l_val' in params and params['l_val'] < 0: error_messages.append("Indutor (L) não pode ser negativo."); error_fields.append('l_val')
        if 'c_val' in params and params['c_val'] < 0: error_messages.append("Capacitor (C) não pode ser negativo."); error_fields.append('c_val')
        if 'v_mag' in params and params['v_mag'] < 0: error_messages.append("Tensão Fonte (Vmag) não pode ser negativa."); error_fields.append('v_mag')

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
            if freq_details_str:
                detail_freq_val = get_float_param(self.freq_details_entry, 'freq_details_val', "Frequência para Detalhes")
                if detail_freq_val is not None:
                    if detail_freq_val <= 0:
                        error_messages.append("Frequência para Detalhes deve ser > 0."); error_fields.append('freq_details')
                    else:
                        params['freq_details'] = detail_freq_val # Só atribui se válido
        
        # Aplicar estilo de erro aos campos identificados
        # Usar um set para evitar aplicar múltiplas vezes ao mesmo campo se diferentes validações falharem para ele
        for field_key in set(error_fields): 
            self._set_entry_error_style(field_key, is_error=True)

        if error_messages:
            # Remove duplicatas mantendo a ordem (aproximadamente)
            unique_error_messages = list(dict.fromkeys(error_messages))
            if not silent:
                messagebox.showerror("Erro de Entrada", "\n".join(unique_error_messages))
            return None, unique_error_messages
        return params, None

    def _calculate_sweep_data(self, params):
        f0_resonance = None
        if params.get('l_val', 0) > 0 and params.get('c_val', 0) > 0: # Usar .get com default
            try: f0_resonance = 1 / (2 * math.pi * math.sqrt(params['l_val'] * params['c_val']))
            except ZeroDivisionError: f0_resonance = None
        
        freq_start = params.get('freq_start', 1) # Default para evitar erros se não presente
        freq_end = params.get('freq_end', 1000)
        num_points = params.get('num_points', 100)

        if freq_end / freq_start > 50: 
            try: frequencies = np.logspace(np.log10(freq_start), np.log10(freq_end), num_points)
            except ValueError: frequencies = np.linspace(freq_start, freq_end, num_points)
        else: frequencies = np.linspace(freq_start, freq_end, num_points)
            
        plot_data_y = []
        v_phase_rad = math.radians(params.get('v_phase_deg', 0))
        v_source_phasor_fixed = cmath.rect(params.get('v_mag', 0), v_phase_rad)

        for freq_current in frequencies:
            r_val = params.get('r_val', 0)
            l_val = params.get('l_val', 0)
            c_val = params.get('c_val', 0)

            z_r_sweep = complex(r_val, 0)
            z_l_sweep = complex(0, 2*cmath.pi*freq_current*l_val) if l_val > 0 else complex(0,0)
            if c_val > 0 and freq_current > 0 : z_c_sweep = complex(0, -1 / (2*cmath.pi*freq_current*c_val))
            else: z_c_sweep = complex(float('inf'), 0)
            z_total_sweep = z_r_sweep + z_l_sweep + z_c_sweep
            i_total_sweep = v_source_phasor_fixed / z_total_sweep if abs(z_total_sweep) != float('inf') else complex(0,0)
            
            val_map = {
                "|Z_total|": lambda i, zr, zl, zc, zt, vs: abs(zt), "|I_total|": lambda i, zr, zl, zc, zt, vs: abs(i),
                "|V_R|":     lambda i, zr, zl, zc, zt, vs: abs(i * zr), "|V_L|":     lambda i, zr, zl, zc, zt, vs: abs(i * zl),
                "|V_C|":     lambda i, zr, zl, zc, zt, vs: abs(vs) if abs(zc) == float('inf') else abs(i * zc),
                "Fase(Z_total) (°)": lambda i,zr,zl,zc,zt,vs: math.degrees(cmath.phase(zt)) if abs(zt)!=float('inf') else 0.0,
                "Fase(I_total) (°)": lambda i,zr,zl,zc,zt,vs: math.degrees(cmath.phase(i)) if abs(i) > 1e-12 else 0.0,
                "Fase(V_R) (°)":     lambda i,zr,zl,zc,zt,vs: math.degrees(cmath.phase(i*zr)) if abs(i*zr) > 1e-12 else 0.0,
                "Fase(V_L) (°)":     lambda i,zr,zl,zc,zt,vs: math.degrees(cmath.phase(i*zl)) if abs(i*zl) > 1e-12 else 0.0,
                "Fase(V_C) (°)":     lambda i,zr,zl,zc,zt,vs: math.degrees(cmath.phase(vs if abs(zc)==float('inf') else i*zc)) if abs(vs if abs(zc)==float('inf') else i*zc) > 1e-12 else 0.0
            }
            current_value_to_plot = 0.0
            if params.get('plot_choice') in val_map:
                current_value_to_plot = val_map[params['plot_choice']](i_total_sweep, z_r_sweep, z_l_sweep, z_c_sweep, z_total_sweep, v_source_phasor_fixed)
            plot_data_y.append(current_value_to_plot)
        return frequencies, plot_data_y, f0_resonance

    def _handle_input_change_for_plot(self, event=None, from_combobox_value=None):
        params, errors = self._validate_all_parameters(silent=True, check_detail_freq=False)
        if params:
            try:
                frequencies, plot_data_y, f0_calc = self._calculate_sweep_data(params)
                self._update_embedded_plot(frequencies, plot_data_y, params['plot_choice'], f0_resonance=f0_calc, extremum_info=self._find_extremum(frequencies, plot_data_y, params['plot_choice']))
                self.results_text.configure(state="normal")
                self.results_text.delete("1.0", "end")
                self.results_text.insert("1.0", f"Gráfico atualizado: {params['plot_choice']}.\n(Pressione 'Analisar e Plotar' para resultados textuais)")
                self.results_text.configure(state="disabled")
            except Exception as e:
                print(f"Erro ao recalcular varredura em tempo real: {e}")
                import traceback
                traceback.print_exc()
                self._clear_embedded_plot() 
        else:
            print(f"Parâmetros inválidos para atualização em tempo real (input change): {errors}")
            self._clear_embedded_plot()

    def _find_extremum(self, frequencies, data_y, plot_choice):
        if not data_y or not isinstance(data_y, (list, np.ndarray)) or len(data_y) == 0:
            return None
        
        # Remove infs e NaNs para cálculo de max/min
        valid_data_y = [val for val in data_y if isinstance(val, (int, float)) and not (math.isinf(val) or math.isnan(val))]
        if not valid_data_y:
            return None

        extremum_type = None
        extremum_value = None
        extremum_freq = None

        if "|" in plot_choice: # É um gráfico de magnitude
            if "Z_total" in plot_choice:
                extremum_type = "min"
                extremum_value = min(valid_data_y)
            else: # Para |I|, |V_R|, |V_L|, |V_C|
                extremum_type = "max"
                extremum_value = max(valid_data_y)
            
            # Encontra o índice do valor extremo na lista original (pode ter inf/nan)
            # Isso pode ser problemático se valid_data_y for diferente em tamanho/ordem.
            # É melhor encontrar o índice na lista que corresponde a valid_data_y
            # Ou, mais simples, encontrar o índice do valor extremo na lista original que não é inf/nan
            try:
                original_indices = [i for i, val in enumerate(data_y) if val == extremum_value]
                if original_indices:
                     extremum_index = original_indices[0] # Pega o primeiro se houver múltiplos
                     extremum_freq = frequencies[extremum_index]
                else: # Caso raro onde min/max de valid_data não está em data_y (não deveria acontecer)
                    return None

            except (ValueError, IndexError): # Se o valor não for encontrado ou índice fora
                return None

            return extremum_type, extremum_freq, extremum_value
        return None


    def toggle_sweep_entries_state(self): # Removido, pois não há mais switch
        pass 

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
        self._clear_all_entry_error_styles()
        self.r_entry.delete(0, "end"); self.r_entry.insert(0, "100")
        self.l_entry.delete(0, "end"); self.l_entry.insert(0, "0.1")
        self.c_entry.delete(0, "end"); self.c_entry.insert(0, "0.00001")
        self.v_mag_entry.delete(0, "end"); self.v_mag_entry.insert(0, "10")
        self.v_phase_entry.delete(0, "end"); self.v_phase_entry.insert(0, "0")
        self.freq_details_entry.delete(0, "end"); self.freq_details_entry.insert(0, "60")
        self.freq_start_entry.delete(0, "end"); self.freq_start_entry.insert(0, "1")
        self.freq_end_entry.delete(0, "end"); self.freq_end_entry.insert(0, "1000")
        self.num_points_entry.delete(0, "end"); self.num_points_entry.insert(0, "200")
        self.plot_variable_combobox.set(self.plot_variable_options[0])
        self.angle_unit.set("degrees") # Resetar unidade do angulo
        
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.configure(state="disabled")
        self._handle_input_change_for_plot()

    def show_about_dialog_ctk(self):
        if self.about_dialog_window and self.about_dialog_window.winfo_exists():
            self.about_dialog_window.lift(); self.about_dialog_window.focus_set(); return
        self.about_dialog_window = ctk.CTkToplevel(self.master)
        self.about_dialog_window.title("Sobre Analisador de Circuito CA")
        self.about_dialog_window.geometry("450x380") # Aumentar altura para novo texto
        self.about_dialog_window.transient(self.master) 
        self.about_dialog_window.update_idletasks() 
        try: self.about_dialog_window.grab_set() 
        except tk.TclError: self.about_dialog_window.after(100, self.about_dialog_window.grab_set)
        about_frame = ctk.CTkFrame(self.about_dialog_window, corner_radius=10)
        about_frame.pack(expand=True, fill="both", padx=15, pady=15)
        ctk.CTkLabel(about_frame, text="Analisador de Circuito CA Série RLC", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,10))
        info_text = ("Versão: 1.5.2 (CustomTkinter)\n\n" 
                     "Desenvolvido como exemplo de aplicação.\n\n"
                     "Funcionalidades:\n"
                     "- Análise de circuito RLC série.\n"
                     "- Varredura de frequência com plotagem em tempo real (incorporada).\n"
                     "- Exibição da frequência de ressonância no gráfico.\n"
                     "- Marcadores de pico/mínimo no gráfico.\n" # NOVO
                     "- Cálculo de impedâncias, correntes, tensões e potências.\n"
                     "- Barra de ferramentas no gráfico (Zoom, Pan, Salvar).\n"
                     "- Análise de texto e gráfico simultâneos.\n"
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
            except: popup_width,popup_height=450,380
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
            extremum_info = self._find_extremum(frequencies, plot_data_y, params['plot_choice'])
            self._update_embedded_plot(frequencies, plot_data_y, params['plot_choice'], f0_resonance=f0_calc, extremum_info=extremum_info)
            
            output_text += f"--- Resumo da Varredura de Frequência ---\n"
            output_text += f"Intervalo: {params['freq_start']:.2f} Hz a {params['freq_end']:.2f} Hz ({params['num_points']} pontos).\n"
            output_text += f"Grandeza Plotada: {params['plot_choice']}\n"
            if f0_calc is not None:
                output_text += f"Frequência de Ressonância (calculada): {f0_calc:.2f} Hz\n"
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
            r_val, l_val, c_val = circuit_params['r_val'], circuit_params['l_val'], circuit_params['c_val']
            v_mag, v_phase_deg = circuit_params['v_mag'], circuit_params['v_phase_deg']
            freq = specific_freq

            v_phase_rad = math.radians(v_phase_deg)
            v_source_phasor = cmath.rect(v_mag, v_phase_rad)
            z_r = complex(r_val, 0)
            z_l = complex(0, 2*cmath.pi*freq*l_val) if l_val > 0 else complex(0,0)
            z_c = complex(0, -1/(2*cmath.pi*freq*c_val)) if c_val > 0 and freq > 0 else complex(float('inf'), 0)
            z_total = z_r + z_l + z_c
            
            output += f"--- Detalhes para Frequência: {freq:.2f} Hz ---\n"
            i_total_phasor = complex(0,0)

            if abs(z_total) == float('inf'):
                output += f"  Impedância Total (Z_total): Infinita (Circuito Aberto)\n"
                # ... (resto da saída de erro como antes) ...
                output += f"  Corrente Total (I_total): {self.format_phasor(i_total_phasor, 'A')}\n"
                v_r_phasor, v_l_phasor = complex(0,0), complex(0,0); v_c_phasor = v_source_phasor
                output += f"  Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                output += f"  Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                output += f"  Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                output += "  ---------------------------\n  Análise de Potência (Total):\n"
                output += "    Potência Aparente (|S|): 0.000 VA\n    Potência Ativa (P): 0.000 W\n"
                output += "    Potência Reativa (Q): 0.000 VAR\n    Fator de Potência (FP): N/A (circuito aberto)\n"

            else: 
                i_total_phasor = v_source_phasor / z_total 
                # ... (resto da lógica de cálculo e output como antes) ...
                v_r_phasor = i_total_phasor * z_r; v_l_phasor = i_total_phasor * z_l; v_c_phasor = i_total_phasor * z_c
                output += f"  Impedância Total (Z_total): {self.format_phasor(z_total, 'Ω')}\n"
                output += f"  Corrente Total (I_total): {self.format_phasor(i_total_phasor, 'A')}\n"
                output += "  ---------------------------\n"
                output += f"  Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                output += f"  Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                output += f"  Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                output += "  ---------------------------\n  Análise de Potência (Total):\n"
                s_complex = v_source_phasor * i_total_phasor.conjugate()
                p_real,q_reactive,s_apparent_mag = s_complex.real,s_complex.imag,abs(s_complex)
                power_factor = p_real / s_apparent_mag if s_apparent_mag != 0 else 0.0
                fp_type,epsilon = "(N/A)",1e-9
                if abs(s_apparent_mag) < epsilon: fp_type = "(N/A - sem potência)"
                elif abs(q_reactive) < epsilon: fp_type = "(unitário)"
                elif q_reactive > 0: fp_type = "(atrasado - indutivo)"
                else: fp_type = "(adiantado - capacitivo)"
                output += f"    Potência Aparente (|S|): {s_apparent_mag:.3f} VA\n    Potência Ativa (P): {p_real:.3f} W\n"
                output += f"    Potência Reativa (Q): {q_reactive:.3f} VAR\n    Fator de Potência (FP): {power_factor:.3f} {fp_type}\n"
            return output
        except Exception as e:
            return f"  Erro ao calcular detalhes para {specific_freq} Hz: {e}\n"

    def _update_embedded_plot(self, frequencies, plot_data_y, y_label_choice, f0_resonance=None, extremum_info=None): # Novo parâmetro extremum_info
        if not (self.fig_embedded and self.ax_embedded and self.canvas_embedded):
            print("Erro: Componentes do gráfico embutido não foram devidamente inicializados.")
            return 

        self.ax_embedded.clear() 
        line, = self.ax_embedded.plot(frequencies, plot_data_y, marker='.', linestyle='-', markersize=3) # Guarda a linha principal
        self.ax_embedded.set_title(f"{y_label_choice} vs Frequência")
        self.ax_embedded.set_xlabel("Frequência (Hz)")
        self.ax_embedded.set_ylabel(y_label_choice)
        self.ax_embedded.grid(True, which="both", linestyle="--", linewidth=0.5)
        
        legend_handles = []
        legend_labels = []

        if f0_resonance is not None and len(frequencies) > 0 and frequencies[0] <= f0_resonance <= frequencies[-1]:
            line_f0 = self.ax_embedded.axvline(x=f0_resonance, color='red', linestyle='--', linewidth=1.2)
            legend_handles.append(line_f0)
            legend_labels.append(f'$f_0 \\approx$ {f0_resonance:.2f} Hz')
        
        if extremum_info:
            etype, efreq, evalue = extremum_info
            marker_color = 'green' if etype == 'max' else 'purple'
            text_label = f"{etype.capitalize()}: {evalue:.3f}\n@ {efreq:.2f} Hz"
            
            # Marcador no ponto
            self.ax_embedded.plot(efreq, evalue, marker='o', color=marker_color, markersize=7, fillstyle='none', markeredgewidth=1.5)
            
            # Anotação
            # Ajustar offset para melhor posicionamento da anotação
            y_range = np.max(plot_data_y) - np.min(plot_data_y) if len(plot_data_y) > 1 and any(plot_data_y) else 1.0
            if y_range == 0 : y_range = abs(evalue) if evalue != 0 else 1.0 # Evitar divisão por zero se todos os y forem iguais

            offset_y_factor = 0.1 if etype == 'max' else -0.2 # Ajuste para max (acima) ou min (abaixo)
            offset_y = y_range * offset_y_factor
            if abs(offset_y) < 1e-6 and evalue != 0 : # Se y_range for muito pequeno, mas evalue não
                 offset_y = evalue * offset_y_factor * 5 # Aumenta o offset relativo
            elif abs(offset_y) < 1e-6 and evalue == 0:
                 offset_y = 0.1 # Um pequeno offset absoluto

            # Ajuste horizontal da anotação para não sobrepor a linha f0
            offset_x_factor = 0.05 * (frequencies[-1] - frequencies[0]) if len(frequencies) > 1 else 1
            ha_align = 'left'
            if f0_resonance and abs(efreq - f0_resonance) < offset_x_factor / 5 : # Se estiver muito perto de f0
                efreq_text = efreq + offset_x_factor
            else:
                efreq_text = efreq
            
            self.ax_embedded.annotate(text_label, 
                                      xy=(efreq, evalue), 
                                      xytext=(efreq_text, evalue + offset_y),
                                      arrowprops=dict(facecolor='black', shrink=0.05, width=0.5, headwidth=4, headlength=5),
                                      fontsize=8, ha=ha_align, va='center',
                                      bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7))


        if legend_handles: # Só mostra a legenda se houver algo para legendar (como f0)
            self.ax_embedded.legend(handles=legend_handles, labels=legend_labels, fontsize='small', loc='best')

        if len(frequencies) > 1 and frequencies[-1] / frequencies[0] > 50:
             self.ax_embedded.set_xscale('log')
        else:
             self.ax_embedded.set_xscale('linear')
        is_magnitude_plot = "|" in y_label_choice
        if is_magnitude_plot and len(plot_data_y) > 1:
            positive_values = [d for d in plot_data_y if isinstance(d, (int, float)) and d > 1e-9 and d != float('inf')]
            if positive_values:
                min_val = min(positive_values); max_val = max(d for d in plot_data_y if isinstance(d, (int,float)) and d != float('inf'))
                if min_val > 0 and max_val / min_val > 1000: self.ax_embedded.set_yscale('log')
                else: self.ax_embedded.set_yscale('linear')
            else: self.ax_embedded.set_yscale('linear')
        elif "Fase" not in y_label_choice: self.ax_embedded.set_yscale('linear')

        self.fig_embedded.tight_layout()
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