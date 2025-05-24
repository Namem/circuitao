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
        master_window.geometry("1250x850") # Aumentado para o novo layout

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.angle_unit = tk.StringVar(value="degrees")
        self.plot_variable_options = ["|Z_total|", "|I_total|", "|V_R|", "|V_L|", "|V_C|",
                                      "Fase(Z_total) (°)", "Fase(I_total) (°)",
                                      "Fase(V_R) (°)", "Fase(V_L) (°)", "Fase(V_C) (°)"]
        self.plot_variable_selected = tk.StringVar(value=self.plot_variable_options[0])
        
        self.about_dialog_window = None
        
        # Atributos para o gráfico EMBUTIDO
        self.fig_embedded = None
        self.ax_embedded = None
        self.canvas_embedded = None
        self.toolbar_embedded = None # Para a barra de ferramentas do gráfico embutido

        self.error_border_color = "red"
        try:
            default_entry_color = ctk.ThemeManager.theme["CTkEntry"]["border_color"]
            current_mode = ctk.get_appearance_mode().lower()
            self.normal_border_color = default_entry_color[0] if isinstance(default_entry_color, list) and current_mode == "light" else (default_entry_color[1] if isinstance(default_entry_color, list) else default_entry_color)
        except KeyError: 
            self.normal_border_color = "gray50" 
        self.entry_widgets = {}

        # Frame principal que ocupa toda a janela
        main_app_frame = ctk.CTkFrame(master_window, fg_color="transparent")
        main_app_frame.pack(expand=True, fill="both", padx=5, pady=5)

        # Título principal
        title_label = ctk.CTkLabel(main_app_frame, text="Analisador de Circuito CA",
                                   font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(5, 10))

        # Frame para dividir a área abaixo do título em duas colunas
        panels_frame = ctk.CTkFrame(main_app_frame, fg_color="transparent")
        panels_frame.pack(expand=True, fill="both", padx=5, pady=5)
        panels_frame.grid_columnconfigure(0, weight=1, minsize=420) # Painel esquerdo (configurações)
        panels_frame.grid_columnconfigure(1, weight=2) # Painel direito (resultados e gráfico)
        panels_frame.grid_rowconfigure(0, weight=1)

        # --- PAINEL ESQUERDO (Configurações - Rolável) ---
        left_panel_scroll_frame = ctk.CTkScrollableFrame(panels_frame, corner_radius=10)
        left_panel_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=(0,10), pady=0)

        # --- Seletor de Topologia do Circuito ---
        topology_main_label = ctk.CTkLabel(left_panel_scroll_frame, text="Configuração do Circuito",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        topology_main_label.pack(pady=(10,5), anchor="w", padx=10)
        
        topology_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        topology_frame.pack(pady=(0,10), padx=10, fill="x")

        ctk.CTkLabel(topology_frame, text="Topologia:").pack(side="left", padx=(10,10), pady=10)
        self.circuit_topology_var = tk.StringVar(value="Série") # Valor padrão
        self.topology_selector = ctk.CTkSegmentedButton(
            topology_frame,
            values=["Série", "Paralelo"],
            variable=self.circuit_topology_var,
            command=self._trigger_realtime_plot_update 
        )
        self.topology_selector.pack(side="left", expand=True, fill="x", padx=10, pady=10)


        # --- Seção de Entradas ---
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
        
        ctk.CTkLabel(sweep_frame, text="Freq. Inicial (Hz):").grid(row=0, column=0, padx=10, pady=8, sticky="w") # Mudou para row 0
        self.freq_start_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 50")
        self.freq_start_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew"); self.freq_start_entry.insert(0, "50")
        self.freq_start_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.freq_start_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['freq_start'] = self.freq_start_entry

        ctk.CTkLabel(sweep_frame, text="Freq. Final (Hz):").grid(row=0, column=2, padx=10, pady=8, sticky="w") # Mudou para row 0
        self.freq_end_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1000")
        self.freq_end_entry.grid(row=0, column=3, padx=10, pady=8, sticky="ew"); self.freq_end_entry.insert(0, "1000")
        self.freq_end_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.freq_end_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['freq_end'] = self.freq_end_entry

        ctk.CTkLabel(sweep_frame, text="Nº de Pontos:").grid(row=1, column=0, padx=10, pady=8, sticky="w") # Mudou para row 1
        self.num_points_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 200")
        self.num_points_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew"); self.num_points_entry.insert(0, "300")
        self.num_points_entry.bind("<FocusOut>", self._trigger_realtime_plot_update); self.num_points_entry.bind("<Return>", self._trigger_realtime_plot_update)
        self.entry_widgets['num_points'] = self.num_points_entry

        ctk.CTkLabel(sweep_frame, text="Plotar Grandeza:").grid(row=1, column=2, padx=10, pady=8, sticky="w") # Mudou para row 1
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

        # --- PAINEL DIREITO ---
        right_panel_frame = ctk.CTkFrame(panels_frame, corner_radius=10)
        right_panel_frame.grid(row=0, column=1, sticky="nsew", padx=(10,0), pady=0) # padx para separar do painel esquerdo
        right_panel_frame.grid_rowconfigure(0, weight=1, minsize=200) 
        right_panel_frame.grid_rowconfigure(1, weight=3) # Mais peso para o gráfico
        right_panel_frame.grid_columnconfigure(0, weight=1)

        results_section_label_text = ctk.CTkLabel(right_panel_frame, text="Resultados da Análise", font=ctk.CTkFont(size=16, weight="bold"))
        results_section_label_text.grid(row=0, column=0, pady=(10,0), padx=10, sticky="nw")
        self.results_text = ctk.CTkTextbox(right_panel_frame, corner_radius=6, wrap="word", font=ctk.CTkFont(family="monospace", size=12)) # Fonte menor
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
        self._trigger_realtime_plot_update() # Plot inicial

    # --- MÉTODOS PARA FEEDBACK VISUAL --- (Permanecem iguais)
    def _set_entry_error_style(self, entry_key, is_error=True):
        if entry_key in self.entry_widgets:
            widget = self.entry_widgets[entry_key]
            target_color = self.error_border_color if is_error else self.normal_border_color
            # Garante que a cor seja uma string válida (alguns temas podem ter None ou listas)
            if not isinstance(target_color, str): 
                current_mode = ctk.get_appearance_mode().lower()
                if isinstance(ctk.ThemeManager.theme["CTkEntry"]["border_color"], list):
                    default_theme_color = ctk.ThemeManager.theme["CTkEntry"]["border_color"]
                    target_color = default_theme_color[0] if current_mode == "light" else default_theme_color[1]
                else: # Fallback
                    target_color = "gray50" if not is_error else "red"

            widget.configure(border_color=target_color)
    
    def _clear_all_entry_error_styles(self):
        for widget_key in self.entry_widgets: # Itera sobre chaves
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
        
        params['topology'] = self.circuit_topology_var.get() # Pega a topologia

        get_float_param(self.r_entry, 'r_val', "Resistor (R)")
        get_float_param(self.l_entry, 'l_val', "Indutor (L)")
        get_float_param(self.c_entry, 'c_val', "Capacitor (C)")
        get_float_param(self.v_mag_entry, 'v_mag', "Tensão Fonte (Vmag)")
        get_float_param(self.v_phase_entry, 'v_phase_deg', "Fase Fonte (θv)")

        if 'r_val' in params and params['r_val'] <= 0 and params['topology'] == "Paralelo": # R não pode ser 0 ou negativo para cálculo de 1/R
             error_messages.append("Resistor (R) deve ser > 0 para topologia paralela."); error_fields.append('r_val')
        elif 'r_val' in params and params['r_val'] < 0: # Para série, R>=0 é ok (R=0 é curto)
             error_messages.append("Resistor (R) não pode ser negativo."); error_fields.append('r_val')

        if 'l_val' in params and params['l_val'] < 0: error_messages.append("Indutor (L) não pode ser negativo."); error_fields.append('l_val')
        if 'c_val' in params and params['c_val'] < 0: error_messages.append("Capacitor (C) não pode ser negativo."); error_fields.append('c_val')
        if 'v_mag' in params and params['v_mag'] < 0: error_messages.append("Tensão Fonte (Vmag) não pode ser negativa."); error_fields.append('v_mag')

        # Parâmetros da Varredura (sempre validados para o gráfico)
        get_float_param(self.freq_start_entry, 'freq_start', "Frequência Inicial")
        get_float_param(self.freq_end_entry, 'freq_end', "Frequência Final")
        get_int_param(self.num_points_entry, 'num_points', "Número de Pontos")
        params['plot_choice'] = self.plot_variable_selected.get()

        if 'freq_start' in params and params['freq_start'] <= 0: error_messages.append("Frequência Inicial deve ser > 0."); error_fields.append('freq_start')
        if 'freq_end' in params and 'freq_start' in params and params.get('freq_start') is not None and params['freq_end'] <= params['freq_start']: 
            error_messages.append("Frequência Final deve ser > Frequência Inicial."); error_fields.append('freq_end')
        if 'num_points' in params and params['num_points'] < 2: error_messages.append("Número de Pontos deve ser >= 2."); error_fields.append('num_points')
        
        params['freq_details'] = None
        if check_detail_freq: # Valida freq_details apenas se solicitado (pelo botão Analisar)
            freq_details_str = self.freq_details_entry.get()
            if freq_details_str:
                detail_freq_val = get_float_param(self.freq_details_entry, 'freq_details_val', "Frequência para Detalhes") # Usa chave diferente para não sobrescrever
                if detail_freq_val is not None: # Se a conversão foi bem-sucedida
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
        # Cálculo de f0 (mesmo para série e paralelo ideal)
        if params.get('l_val', 0) > 0 and params.get('c_val', 0) > 0:
            try: f0_resonance = 1 / (2 * math.pi * math.sqrt(params['l_val'] * params['c_val']))
            except ZeroDivisionError: f0_resonance = None
        
        if params['freq_end'] / params['freq_start'] > 50: 
            try: frequencies = np.logspace(np.log10(params['freq_start']), np.log10(params['freq_end']), params['num_points'])
            except ValueError: frequencies = np.linspace(params['freq_start'], params['freq_end'], params['num_points'])
        else: frequencies = np.linspace(params['freq_start'], params['freq_end'], params['num_points'])
            
        plot_data_y = []
        v_phase_rad = math.radians(params.get('v_phase_deg', 0))
        v_source_phasor_fixed = cmath.rect(params.get('v_mag', 0), v_phase_rad)
        topology = params.get('topology', "Série")

        for freq_current in frequencies:
            r_val = params.get('r_val', 0)
            l_val = params.get('l_val', 0)
            c_val = params.get('c_val', 0)

            z_r, z_l, z_c = complex(r_val, 0), complex(0,0), complex(0,0)
            if l_val > 0 and freq_current > 0: z_l = complex(0, 2 * cmath.pi * freq_current * l_val)
            if c_val > 0 and freq_current > 0: z_c = complex(0, -1 / (2 * cmath.pi * freq_current * c_val))
            elif c_val == 0: z_c = complex(float('inf'),0) # Capacitor 0F = aberto

            if r_val == 0 and topology == "Paralelo": # Evitar divisão por zero para Yr se R=0
                yr_val = complex(float('inf'),0) # Admitância do resistor é infinita se R=0 (curto)
            elif r_val > 0 :
                 yr_val = 1/z_r
            else: # R < 0 (inválido, mas por segurança) ou R=0 para série
                 yr_val = complex(float('inf'),0) if r_val==0 else 1/z_r # Default para série onde R=0 é ok

            yl_val = 1/z_l if l_val > 0 and freq_current > 0 else complex(0,0) # Admitância do indutor (se L=0, ZL=0, YL=inf, mas tratamos L=0 como ZL=0)
                                                                              # Se L > 0 e freq = 0, ZL=0, YL=inf (curto DC)
                                                                              # Se l_val = 0, z_l = 0. Y_L é infinito.
            if l_val == 0: yl_val = complex(float('inf'),0)


            yc_val = 1/z_c if c_val > 0 and freq_current > 0 else complex(0,0) # Admitância do capacitor
                                                                              # Se C=0, ZC=inf, YC=0 (aberto)
                                                                              # Se C > 0 e freq=0, ZC=inf, YC=0 (aberto DC)
            if c_val == 0: yc_val = complex(0,0)


            z_total_sweep, i_total_sweep = complex(0,0), complex(0,0)
            v_r_sweep, v_l_sweep, v_c_sweep = complex(0,0), complex(0,0), complex(0,0)


            if topology == "Série":
                z_total_sweep = z_r + z_l + z_c
                i_total_sweep = v_source_phasor_fixed / z_total_sweep if abs(z_total_sweep) != float('inf') else complex(0,0)
                v_r_sweep = i_total_sweep * z_r
                v_l_sweep = i_total_sweep * z_l
                v_c_sweep = i_total_sweep * z_c if abs(z_c) != float('inf') else v_source_phasor_fixed # Se C é aberto, Vc=Vfonte
            
            elif topology == "Paralelo":
                y_total_sweep = complex(0,0)
                if r_val > 0: y_total_sweep += yr_val
                else: y_total_sweep += yr_val # Caso R=0, Yr é infinito (curto)

                if l_val > 0 and freq_current > 0: y_total_sweep += yl_val
                elif l_val == 0: y_total_sweep += yl_val # Se L=0, YL é infinito (curto)
                
                if c_val > 0 and freq_current > 0: y_total_sweep += yc_val
                # Se C=0, YC=0, não adiciona nada (aberto)

                z_total_sweep = 1 / y_total_sweep if abs(y_total_sweep) > 1e-12 else complex(float('inf'),0)
                i_total_sweep = v_source_phasor_fixed * y_total_sweep # I = V * Y
                
                # Em paralelo, a tensão é a mesma em todos os componentes
                v_r_sweep = v_l_sweep = v_c_sweep = v_source_phasor_fixed
                # As correntes nos ramos seriam I_branch = V_source * Y_branch, mas não estamos plotando diretamente
                # Para |V_R|, |V_L|, |V_C| no plot, elas serão a tensão da fonte.

            val_map = {
                "|Z_total|": lambda i, vr, vl, vc, zr, zl, zc, zt, vs: abs(zt),
                "|I_total|": lambda i, vr, vl, vc, zr, zl, zc, zt, vs: abs(i), # Corrente total da fonte
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
                current_value_to_plot = val_map[params['plot_choice']](i_total_sweep, 
                                                             v_r_sweep, v_l_sweep, v_c_sweep, # Passa as tensões calculadas
                                                             z_r, z_l, z_c, # Impedâncias individuais
                                                             z_total_sweep, v_source_phasor_fixed)
            plot_data_y.append(current_value_to_plot)
        return frequencies, plot_data_y, f0_resonance

    def _trigger_realtime_plot_update(self, event=None, from_combobox_value=None): # Renomeado
        # Este método agora sempre tenta atualizar o gráfico da varredura
        params, errors = self._validate_all_parameters(silent=True, check_detail_freq=False)

        if params:
            try:
                frequencies, plot_data_y, f0_calc = self._calculate_sweep_data(params)
                extremum_info = self._find_extremum(frequencies, plot_data_y, params['plot_choice'], params['topology']) # Passa topologia
                self._update_embedded_plot(frequencies, plot_data_y, params['plot_choice'], f0_resonance=f0_calc, extremum_info=extremum_info)
                self.results_text.configure(state="normal")
                self.results_text.delete("1.0", "end")
                self.results_text.insert("1.0", f"Gráfico ({params['topology']}) atualizado: {params['plot_choice']}.\n(Pressione 'Analisar e Plotar' para resultados textuais)")
                self.results_text.configure(state="disabled")
            except Exception as e:
                print(f"Erro ao recalcular varredura em tempo real: {e}")
                import traceback
                traceback.print_exc()
                self._clear_embedded_plot() 
        else:
            print(f"Parâmetros inválidos para atualização em tempo real (input change): {errors}")
            self._clear_embedded_plot()

    def _find_extremum(self, frequencies, data_y, plot_choice, topology): # Adicionado topology
        if not data_y or not isinstance(data_y, (list, np.ndarray)) or len(data_y) == 0:
            return None
        valid_data_y = [val for val in data_y if isinstance(val, (int, float)) and not (math.isinf(val) or math.isnan(val))]
        if not valid_data_y: return None

        extremum_type, extremum_value, extremum_freq = None, None, None

        if "|" in plot_choice: # Magnitude plot
            if topology == "Série":
                if "Z_total" in plot_choice: extremum_type = "min"
                else: extremum_type = "max" # Para |I|, |V_R|, |V_L|, |V_C| em série
            elif topology == "Paralelo":
                if "I_total" in plot_choice: extremum_type = "min" # Corrente da fonte mínima na ressonância paralela
                elif "Z_total" in plot_choice: extremum_type = "max" # Impedância máxima na ressonância paralela
                else: extremum_type = "max" # Para |V_R|, |V_L|, |V_C| que são V_fonte, ou correntes de ramo

            if extremum_type == "min": extremum_value = min(valid_data_y)
            elif extremum_type == "max": extremum_value = max(valid_data_y)
            else: return None # Se a lógica acima não cobrir um caso para magnitude

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
        # ... (Permanece o mesmo) ...
        if self.ax_embedded:
            self.ax_embedded.clear()
            self.ax_embedded.set_title("Aguardando Análise")
            self.ax_embedded.set_xlabel("Frequência (Hz)")
            self.ax_embedded.set_ylabel("Grandeza")
            self.ax_embedded.grid(True, which="both", linestyle="--", linewidth=0.5)
            if self.fig_embedded: self.fig_embedded.tight_layout()
            if self.canvas_embedded: self.canvas_embedded.draw()
            
    def clear_entries(self):
        # ... (Permanece o mesmo, mas chama _trigger_realtime_plot_update) ...
        self._clear_all_entry_error_styles()
        self.r_entry.delete(0, "end"); self.r_entry.insert(0, "10") # Valores do exemplo de ressonância
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
        self.circuit_topology_var.set("Série") # Resetar topologia
        
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.configure(state="disabled")
        self._trigger_realtime_plot_update()

    def show_about_dialog_ctk(self):
        # ... (Permanece o mesmo, mas atualize a versão e funcionalidades se quiser) ...
        if self.about_dialog_window and self.about_dialog_window.winfo_exists():
            self.about_dialog_window.lift(); self.about_dialog_window.focus_set(); return
        self.about_dialog_window = ctk.CTkToplevel(self.master)
        self.about_dialog_window.title("Sobre Analisador de Circuito CA")
        self.about_dialog_window.geometry("450x400") # Aumentar altura
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
                     "- Análise de circuito RLC Série e Paralelo.\n" # ATUALIZADO
                     "- Varredura de frequência com plotagem em tempo real (incorporada).\n"
                     "- Exibição da frequência de ressonância no gráfico.\n"
                     "- Marcadores de pico/mínimo no gráfico.\n"
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
            
            output_text += f"--- Resumo da Varredura ({params['topology']}) ---\n" # Adiciona topologia
            output_text += f"Intervalo: {params['freq_start']:.2f} Hz a {params['freq_end']:.2f} Hz ({params['num_points']} pontos).\n"
            output_text += f"Grandeza Plotada: {params['plot_choice']}\n"
            if f0_calc is not None:
                output_text += f"Frequência de Ressonância (Teórica): {f0_calc:.2f} Hz\n" # Label mais clara
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
            topology = circuit_params.get('topology', "Série")
            freq = specific_freq

            v_phase_rad = math.radians(v_phase_deg)
            v_source_phasor = cmath.rect(v_mag, v_phase_rad)
            
            # Impedâncias individuais (sempre calculadas da mesma forma)
            z_r = complex(r_val, 0) if r_val > 0 else (complex(0,0) if r_val == 0 and topology == "Série" else complex(1e-12,0) ) # Evita 1/0 para R=0 no paralelo, considera R muito pequeno
            if r_val == 0 and topology == "Paralelo": z_r = complex(1e-12,0) # R = 0 em paralelo é curto, impedância muito baixa

            z_l = complex(0, 2*cmath.pi*freq*l_val) if l_val > 0 and freq > 0 else (complex(0,0) if l_val == 0 or freq == 0 else complex(float('inf'),0))
            if l_val == 0 : z_l = complex(0,0) # Curto para indutor L=0

            z_c = complex(0, -1/(2*cmath.pi*freq*c_val)) if c_val > 0 and freq > 0 else complex(float('inf'), 0)
            if c_val == 0: z_c = complex(float('inf'),0) # Aberto para capacitor C=0


            z_total, i_total_phasor = complex(0,0), complex(0,0)
            v_r, v_l, v_c = complex(0,0), complex(0,0), complex(0,0)
            i_r, i_l, i_c = complex(0,0), complex(0,0), complex(0,0)


            if topology == "Série":
                z_total = z_r + z_l + z_c
                if abs(z_total) == float('inf') or abs(z_total) < 1e-12 : # Evita divisão por zero ou Z muito pequeno
                    i_total_phasor = complex(0,0) if abs(z_total) == float('inf') else v_source_phasor / (1e-12 if abs(z_total) < 1e-12 else z_total)
                else:
                    i_total_phasor = v_source_phasor / z_total
                
                v_r = i_total_phasor * z_r
                v_l = i_total_phasor * z_l
                v_c = i_total_phasor * z_c if abs(z_c) != float('inf') else (v_source_phasor - v_r - v_l)
            
            elif topology == "Paralelo":
                y_r = 1/z_r if abs(z_r) > 1e-12 else complex(float('inf'),0) # Admissão do resistor
                y_l = 1/z_l if abs(z_l) > 1e-12 else complex(float('inf'),0) # Admissão do indutor
                y_c = 1/z_c if abs(z_c) > 1e-12 else complex(0,0)       # Admissão do capacitor (se Zc=inf, Yc=0)

                y_total = y_r + y_l + y_c
                z_total = 1/y_total if abs(y_total) > 1e-12 else complex(float('inf'),0)
                i_total_phasor = v_source_phasor * y_total # Corrente total da fonte

                # Tensão é a mesma para todos em paralelo
                v_r = v_l = v_c = v_source_phasor
                
                # Correntes nos ramos
                i_r = v_source_phasor * y_r if abs(z_r) > 1e-12 else (v_source_phasor / (1e-12) if r_val==0 else 0)
                i_l = v_source_phasor * y_l if abs(z_l) > 1e-12 else (v_source_phasor / (1e-12) if l_val==0 else 0)
                i_c = v_source_phasor * y_c if abs(z_c) > 1e-12 else 0

            output += f"--- Detalhes para Frequência: {freq:.2f} Hz ({topology}) ---\n"
            if abs(z_total) == float('inf'):
                output += f"  Impedância Total (Z_total): Infinita (Circuito Aberto)\n"
                output += f"  Corrente Total (I_total Fonte): {self.format_phasor(i_total_phasor, 'A')}\n"
                # Para paralelo, V em cada componente é Vfonte. Correntes nos ramos são zero se Ztotal é inf.
                if topology == "Paralelo":
                     output += f"  Tensão (V_R=V_L=V_C): {self.format_phasor(v_source_phasor, 'V')}\n"
                     output += f"  Corrente em R (I_R): {self.format_phasor(i_r, 'A')}\n" # Pode ser grande se R for pequeno
                     output += f"  Corrente em L (I_L): {self.format_phasor(i_l, 'A')}\n"
                     output += f"  Corrente em C (I_C): {self.format_phasor(i_c, 'A')}\n"

            else: 
                output += f"  Impedância Total (Z_total): {self.format_phasor(z_total, 'Ω')}\n"
                output += f"  Corrente Total (I_total Fonte): {self.format_phasor(i_total_phasor, 'A')}\n"
                output += "  ---------------------------\n"
                if topology == "Série":
                    output += f"  Tensão no Resistor (V_R): {self.format_phasor(v_r, 'V')}\n"
                    output += f"  Tensão no Indutor (V_L): {self.format_phasor(v_l, 'V')}\n"
                    output += f"  Tensão no Capacitor (V_C): {self.format_phasor(v_c, 'V')}\n"
                elif topology == "Paralelo":
                    output += f"  Tensão (V_R=V_L=V_C): {self.format_phasor(v_source_phasor, 'V')}\n"
                    output += f"  Corrente em R (I_R): {self.format_phasor(i_r, 'A')}\n"
                    output += f"  Corrente em L (I_L): {self.format_phasor(i_l, 'A')}\n"
                    output += f"  Corrente em C (I_C): {self.format_phasor(i_c, 'A')}\n"
                
                output += "  ---------------------------\n  Análise de Potência (Total da Fonte):\n"
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
            import traceback
            traceback.print_exc()
            return f"  Erro ao calcular detalhes para {specific_freq} Hz: {e}\n"

    def _update_embedded_plot(self, frequencies, plot_data_y, y_label_choice, f0_resonance=None, extremum_info=None):
        # ... (Este método permanece o mesmo da versão anterior) ...
        if not (self.fig_embedded and self.ax_embedded and self.canvas_embedded):
            print("Erro: Componentes do gráfico embutido não foram devidamente inicializados.")
            return 
        self.ax_embedded.clear() 
        line, = self.ax_embedded.plot(frequencies, plot_data_y, marker='.', linestyle='-', markersize=3)
        self.ax_embedded.set_title(f"{y_label_choice} vs Frequência ({self.circuit_topology_var.get()})") # Adiciona topologia ao título
        self.ax_embedded.set_xlabel("Frequência (Hz)")
        self.ax_embedded.set_ylabel(y_label_choice)
        self.ax_embedded.grid(True, which="both", linestyle="--", linewidth=0.5)
        legend_handles, legend_labels = [], []
        if f0_resonance is not None and len(frequencies) > 0 and frequencies[0] <= f0_resonance <= frequencies[-1]:
            line_f0 = self.ax_embedded.axvline(x=f0_resonance, color='red', linestyle='--', linewidth=1.2)
            legend_handles.append(line_f0); legend_labels.append(f'$f_0 \\approx$ {f0_resonance:.2f} Hz')
        if extremum_info:
            etype, efreq, evalue = extremum_info
            marker_color = 'green' if etype == 'max' else 'purple'
            text_label = f"{etype.capitalize()}: {evalue:.3f}\n@ {efreq:.2f} Hz"
            self.ax_embedded.plot(efreq, evalue, marker='o', color=marker_color, markersize=7, fillstyle='none', markeredgewidth=1.5)
            y_range = np.max(plot_data_y)-np.min(plot_data_y) if len(plot_data_y)>1 and any(plot_data_y) else 1.0
            if y_range==0: y_range=abs(evalue) if evalue!=0 else 1.0
            offset_y_factor = 0.1 if etype == 'max' else -0.2; offset_y = y_range * offset_y_factor
            if abs(offset_y)<1e-6 and evalue!=0: offset_y=evalue*offset_y_factor*5
            elif abs(offset_y)<1e-6 and evalue==0: offset_y=0.1
            offset_x_factor = 0.05*(frequencies[-1]-frequencies[0]) if len(frequencies)>1 else 1
            ha_align='left'; efreq_text = efreq
            if f0_resonance and abs(efreq-f0_resonance) < offset_x_factor/5 : efreq_text=efreq+offset_x_factor
            self.ax_embedded.annotate(text_label, xy=(efreq, evalue), xytext=(efreq_text, evalue+offset_y),
                                      arrowprops=dict(facecolor='black',shrink=0.05,width=0.5,headwidth=4,headlength=5),
                                      fontsize=8,ha=ha_align,va='center',bbox=dict(boxstyle="round,pad=0.3",fc="white",ec="gray",alpha=0.7))
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
        self.fig_embedded.tight_layout(); self.canvas_embedded.draw()

    def format_phasor(self, complex_val, unit=""):
        # ... (Permanece o mesmo) ...
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