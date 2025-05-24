import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import cmath
import math
import numpy as np
import json 

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.colors as mcolors # Para cores do gráfico

class ACCircuitAnalyzerApp:
    def __init__(self, master_window):
        self.master = master_window
        master_window.title("Analisador de Circuito CA Avançado (CustomTkinter)")
        master_window.geometry("1250x900") 

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.angle_unit = tk.StringVar(value="degrees")
        
        # Variáveis para seleção de múltiplas curvas de MAGNITUDE
        self.magnitude_plot_vars = {
            "|Z_total|": tk.BooleanVar(value=True), # Plotar Z_total por padrão
            "|I_total|": tk.BooleanVar(value=False),
            "|V_R|": tk.BooleanVar(value=False),
            "|V_L|": tk.BooleanVar(value=False),
            "|V_C|": tk.BooleanVar(value=False),
        }
        self.plot_colors = list(mcolors.TABLEAU_COLORS.values()) + ['#FF00FF', '#A52A2A', '#00FFFF', '#FFD700', '#808080', '#008000', '#800080', '#FFC0CB']

        # Variável para seleção de UMA curva de FASE
        self.phase_plot_options = ["Nenhuma", "Fase(Z_total) (°)", "Fase(I_total) (°)", 
                                   "Fase(V_R) (°)", "Fase(V_L) (°)", "Fase(V_C) (°)"]
        self.selected_phase_plot_var = tk.StringVar(value=self.phase_plot_options[0])

        self.circuit_topology_var = tk.StringVar(value="Série") 
        self.decimal_places_var = tk.StringVar(value="3") 
        self.scientific_notation_var = tk.BooleanVar(value=False)

        # Checkboxes para incluir componentes
        self.include_r_var = tk.BooleanVar(value=True)
        self.include_l_var = tk.BooleanVar(value=True)
        self.include_c_var = tk.BooleanVar(value=True)

        self.about_dialog_window = None
        self.fig_embedded = None
        self.ax_embedded = None 
        self.ax2_embedded = None 
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
        panels_frame.grid_columnconfigure(0, weight=1, minsize=440) 
        panels_frame.grid_columnconfigure(1, weight=2) 
        panels_frame.grid_rowconfigure(0, weight=1)    

        left_panel_scroll_frame = ctk.CTkScrollableFrame(panels_frame, corner_radius=10)
        left_panel_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=(0,10), pady=0)

        config_io_frame = ctk.CTkFrame(left_panel_scroll_frame, fg_color="transparent")
        config_io_frame.pack(pady=(10,0), padx=10, fill="x")
        save_button = ctk.CTkButton(config_io_frame, text="Salvar Config.", command=self.save_configuration)
        save_button.pack(side="left", padx=5, expand=True)
        load_button = ctk.CTkButton(config_io_frame, text="Carregar Config.", command=self.load_configuration)
        load_button.pack(side="left", padx=5, expand=True)

        topology_main_label = ctk.CTkLabel(left_panel_scroll_frame, text="Configuração do Circuito",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        topology_main_label.pack(pady=(10,5), anchor="w", padx=10)
        
        topology_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        topology_frame.pack(pady=(0,10), padx=10, fill="x")
        ctk.CTkLabel(topology_frame, text="Topologia:").pack(side="left", padx=(10,10), pady=10)
        self.topology_selector = ctk.CTkSegmentedButton(
            topology_frame, values=["Série", "Paralelo"],
            variable=self.circuit_topology_var, command=self._on_parameter_change)
        self.topology_selector.pack(side="left", expand=True, fill="x", padx=10, pady=10)

        input_section_label = ctk.CTkLabel(left_panel_scroll_frame, text="Parâmetros do Circuito e Fonte",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        input_section_label.pack(pady=(10,5), anchor="w", padx=10)
        input_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        input_frame.pack(fill="x", padx=10, pady=(0,10))
        input_frame.grid_columnconfigure(2, weight=1) 
        entry_width = 130 
        
        self.r_check = ctk.CTkCheckBox(input_frame, text="R [Ω]:", variable=self.include_r_var, command=self._on_include_component_change)
        self.r_check.grid(row=0, column=0, columnspan=2, padx=(10,0), pady=8, sticky="w")
        self.r_entry = ctk.CTkEntry(input_frame, width=entry_width)
        self.r_entry.grid(row=0, column=2, padx=(0,10), pady=8, sticky="ew"); self.r_entry.insert(0, "10")
        self.r_entry.bind("<FocusOut>", self._on_parameter_change); self.r_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['r_val'] = self.r_entry

        self.l_check = ctk.CTkCheckBox(input_frame, text="L [H]:", variable=self.include_l_var, command=self._on_include_component_change)
        self.l_check.grid(row=1, column=0, columnspan=2, padx=(10,0), pady=8, sticky="w")
        self.l_entry = ctk.CTkEntry(input_frame, width=entry_width)
        self.l_entry.grid(row=1, column=2, padx=(0,10), pady=8, sticky="ew"); self.l_entry.insert(0, "0.01")
        self.l_entry.bind("<FocusOut>", self._on_parameter_change); self.l_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['l_val'] = self.l_entry
        
        self.c_check = ctk.CTkCheckBox(input_frame, text="C [F]:", variable=self.include_c_var, command=self._on_include_component_change)
        self.c_check.grid(row=2, column=0, columnspan=2, padx=(10,0), pady=8, sticky="w")
        self.c_entry = ctk.CTkEntry(input_frame, width=entry_width)
        self.c_entry.grid(row=2, column=2, padx=(0,10), pady=8, sticky="ew"); self.c_entry.insert(0, "0.00001")
        self.c_entry.bind("<FocusOut>", self._on_parameter_change); self.c_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['c_val'] = self.c_entry
        
        ctk.CTkLabel(input_frame, text="Tensão Fonte (Vmag) [V]:").grid(row=3, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        self.v_mag_entry = ctk.CTkEntry(input_frame, width=entry_width)
        self.v_mag_entry.grid(row=3, column=2, padx=(0,10), pady=8, sticky="ew"); self.v_mag_entry.insert(0, "10")
        self.v_mag_entry.bind("<FocusOut>", self._on_parameter_change); self.v_mag_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['v_mag'] = self.v_mag_entry
        
        ctk.CTkLabel(input_frame, text="Fase Fonte (θv) [°]:").grid(row=4, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        self.v_phase_entry = ctk.CTkEntry(input_frame, width=entry_width)
        self.v_phase_entry.grid(row=4, column=2, padx=(0,10), pady=8, sticky="ew"); self.v_phase_entry.insert(0, "0")
        self.v_phase_entry.bind("<FocusOut>", self._on_parameter_change); self.v_phase_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['v_phase_deg'] = self.v_phase_entry

        ctk.CTkLabel(input_frame, text="Freq. para Detalhes (Hz):").grid(row=5, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        self.freq_details_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Opcional")
        self.freq_details_entry.grid(row=5, column=2, padx=(0,10), pady=8, sticky="ew"); self.freq_details_entry.insert(0, "159")
        self.entry_widgets['freq_details'] = self.freq_details_entry
        
        output_format_label = ctk.CTkLabel(left_panel_scroll_frame, text="Formatação da Saída Textual", font=ctk.CTkFont(size=16, weight="bold"))
        output_format_label.pack(pady=(15,5), anchor="w", padx=10)
        output_format_frame_main = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10) 
        output_format_frame_main.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(output_format_frame_main, text="Casas Decimais:").pack(side="left", padx=(10,5), pady=10)
        self.decimal_places_menu = ctk.CTkOptionMenu(output_format_frame_main, variable=self.decimal_places_var, 
                                                     values=["2", "3", "4", "5", "6"],
                                                     command=self._on_formatting_change)
        self.decimal_places_menu.pack(side="left", padx=5, pady=10)
        self.sci_notation_checkbox = ctk.CTkCheckBox(output_format_frame_main, text="Not. Científica", 
                                                      variable=self.scientific_notation_var,
                                                      command=self._on_formatting_change)
        self.sci_notation_checkbox.pack(side="left", padx=10, pady=10)
        
        output_options_label = ctk.CTkLabel(left_panel_scroll_frame, text="Opções de Saída Angular", font=ctk.CTkFont(size=16, weight="bold"))
        output_options_label.pack(pady=(10,5), anchor="w", padx=10)
        output_options_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        output_options_frame.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(output_options_frame, text="Unidade Ângulo (Saída):").pack(side="left", padx=(10,5), pady=10)
        degrees_radio = ctk.CTkRadioButton(output_options_frame, text="Graus (°)", variable=self.angle_unit, value="degrees", command=self._on_parameter_change)
        degrees_radio.pack(side="left", padx=5, pady=10)
        radians_radio = ctk.CTkRadioButton(output_options_frame, text="Radianos (rad)", variable=self.angle_unit, value="radians", command=self._on_parameter_change)
        radians_radio.pack(side="left", padx=5, pady=10)

        sweep_section_label = ctk.CTkLabel(left_panel_scroll_frame, text="Parâmetros da Varredura de Frequência", font=ctk.CTkFont(size=16, weight="bold"))
        sweep_section_label.pack(pady=(15,5), anchor="w", padx=10)
        sweep_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        sweep_frame.pack(fill="x", padx=10, pady=(0,10))
        sweep_frame.grid_columnconfigure(1, weight=1); sweep_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(sweep_frame, text="Freq. Inicial (Hz):").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.freq_start_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 50")
        self.freq_start_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew"); self.freq_start_entry.insert(0, "50")
        self.freq_start_entry.bind("<FocusOut>", self._on_parameter_change); self.freq_start_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['freq_start'] = self.freq_start_entry

        ctk.CTkLabel(sweep_frame, text="Freq. Final (Hz):").grid(row=0, column=2, padx=10, pady=8, sticky="w")
        self.freq_end_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1000")
        self.freq_end_entry.grid(row=0, column=3, padx=10, pady=8, sticky="ew"); self.freq_end_entry.insert(0, "1000")
        self.freq_end_entry.bind("<FocusOut>", self._on_parameter_change); self.freq_end_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['freq_end'] = self.freq_end_entry

        ctk.CTkLabel(sweep_frame, text="Nº de Pontos:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.num_points_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 300")
        self.num_points_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew"); self.num_points_entry.insert(0, "300")
        self.num_points_entry.bind("<FocusOut>", self._on_parameter_change); self.num_points_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['num_points'] = self.num_points_entry

        # --- Seleção de Grandezas para Plotar (Múltiplas Curvas) ---
        plot_selection_label = ctk.CTkLabel(left_panel_scroll_frame, text="Grandezas para Plotar", font=ctk.CTkFont(size=16, weight="bold"))
        plot_selection_label.pack(pady=(15,5), anchor="w", padx=10)
        
        plot_magnitudes_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        plot_magnitudes_frame.pack(fill="x", padx=10, pady=(0,5))
        ctk.CTkLabel(plot_magnitudes_frame, text="Magnitudes (Eixo Y Primário):", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=10, pady=(5,2))
        
        self.magnitude_checkboxes_widgets = {}
        mag_check_frame_cols = ctk.CTkFrame(plot_magnitudes_frame, fg_color="transparent")
        mag_check_frame_cols.pack(fill="x", padx=5, pady=(0,5))
        mag_options_per_row = 2 
        for i, name in enumerate(self.magnitude_plot_vars.keys()):
            var = self.magnitude_plot_vars[name]
            cb = ctk.CTkCheckBox(mag_check_frame_cols, text=name, variable=var, command=self._on_parameter_change)
            cb.grid(row=i // mag_options_per_row, column=i % mag_options_per_row, padx=5, pady=2, sticky="w")
            self.magnitude_checkboxes_widgets[name] = cb
        
        plot_phase_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        plot_phase_frame.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(plot_phase_frame, text="Fase (Eixo Y Secundário):", font=ctk.CTkFont(size=13)).pack(side="left", padx=(10,5), pady=5)
        self.phase_plot_combobox = ctk.CTkComboBox(plot_phase_frame, values=self.phase_plot_options,
                                                    variable=self.selected_phase_plot_var, state="readonly",
                                                    command=lambda choice: self._on_parameter_change(from_combobox_value=choice), 
                                                    width=180)
        self.phase_plot_combobox.pack(side="left", padx=5, pady=5, expand=True, fill="x")

        action_buttons_frame = ctk.CTkFrame(left_panel_scroll_frame, fg_color="transparent")
        action_buttons_frame.pack(pady=20, fill="x")
        analyze_button = ctk.CTkButton(action_buttons_frame, text="Analisar e Plotar", command=self.analyze_circuit)
        analyze_button.pack(side="left", padx=5, expand=True)
        clear_button = ctk.CTkButton(action_buttons_frame, text="Limpar", command=self.clear_entries)
        clear_button.pack(side="left", padx=5, expand=True)
        about_button = ctk.CTkButton(action_buttons_frame, text="Sobre", command=self.show_about_dialog_ctk)
        about_button.pack(side="left", padx=5, expand=True)

        self.progress_bar_frame = ctk.CTkFrame(left_panel_scroll_frame, fg_color="transparent")
        self.progress_bar = ctk.CTkProgressBar(self.progress_bar_frame, orientation="horizontal", mode="indeterminate")
        
        self.note_label = ctk.CTkLabel(left_panel_scroll_frame, text="Nota: Analisa circuitos RLC Série ou Paralelo.", font=ctk.CTkFont(size=12), text_color="gray50")
        self.note_label.pack(pady=(10,10), side="bottom")

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
        
        self.plot_container_frame = ctk.CTkFrame(right_panel_frame, corner_radius=6)
        self.plot_container_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(40,10))
        self.plot_container_frame.grid_columnconfigure(0, weight=1)
        self.plot_container_frame.grid_rowconfigure(0, weight=1) 
        self.plot_container_frame.grid_rowconfigure(1, weight=0) 

        self.fig_embedded = Figure(figsize=(5, 3.5), dpi=100) 
        self.ax_embedded = self.fig_embedded.add_subplot(111)
        self.canvas_embedded = FigureCanvasTkAgg(self.fig_embedded, master=self.plot_container_frame)
        canvas_widget_embedded = self.canvas_embedded.get_tk_widget()
        canvas_widget_embedded.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        self.toolbar_embedded = NavigationToolbar2Tk(self.canvas_embedded, self.plot_container_frame, pack_toolbar=False)
        self.toolbar_embedded.update()
        self.toolbar_embedded.grid(row=1, column=0, sticky="ew", padx=2, pady=(0,2))
        
        self._clear_embedded_plot()
        # Adia a chamada inicial para garantir que todos os widgets estejam prontos
        self.master.after(10, self._on_include_component_change) 
        self.master.after(50, self._trigger_realtime_plot_update) 

    # ... (RESTANTE DOS MÉTODOS COMO NA VERSÃO ANTERIOR, COM AS CORREÇÕES JÁ APLICADAS) ...
    # Os métodos _validate_all_parameters, _calculate_sweep_data, _trigger_realtime_plot_update,
    # _find_extremum, _update_embedded_plot, _get_single_frequency_analysis_details
    # JÁ ESTÃO ADAPTADOS PARA MÚLTIPLAS CURVAS E COMPONENTES OPCIONAIS
    # E A LÓGICA DE Q, BW, POTÊNCIAS POR COMPONENTE JÁ FOI REVISADA.
    # O CÓDIGO DA SUA ÚLTIMA VERSÃO (QUE CAUSOU O AttributeError) É A BASE.
    # A CORREÇÃO PRINCIPAL É GARANTIR QUE _trigger_realtime_plot_update não seja chamado
    # por _on_include_component_change ANTES de todos os widgets de varredura existirem.
    
    def _on_parameter_change(self, event=None, from_combobox_value=None): # Renomeado e unificado
        self._trigger_realtime_plot_update(from_combobox_value=from_combobox_value)

    def _on_formatting_change(self, event_or_choice=None): # Renomeado
        # Se houver resultados textuais, reanalisa para atualizar a formatação
        if self.results_text.get("1.0", "end-1c").strip(): # Verifica se há texto
             self.analyze_circuit() # Força reanálise completa para atualizar o texto

    def _on_include_component_change(self, event=None): # event=None para compatibilidade
        self.r_entry.configure(state="normal" if self.include_r_var.get() else "disabled")
        if not self.include_r_var.get() and self.r_entry.get() != "0": # Zera apenas se não for já zero
            self.r_entry.delete(0,tk.END); self.r_entry.insert(0,"0")
        
        self.l_entry.configure(state="normal" if self.include_l_var.get() else "disabled")
        if not self.include_l_var.get() and self.l_entry.get() != "0": 
            self.l_entry.delete(0,tk.END); self.l_entry.insert(0,"0")

        self.c_entry.configure(state="normal" if self.include_c_var.get() else "disabled")
        if not self.include_c_var.get() and self.c_entry.get() != "0":
            self.c_entry.delete(0,tk.END); self.c_entry.insert(0,"0")
        
        # Só chama o trigger se o __init__ já completou a criação de todos os widgets de varredura
        if hasattr(self, 'freq_start_entry'): # Uma verificação simples
            self._trigger_realtime_plot_update()

    def _format_value(self, value, unit=""):
        if isinstance(value, str): return f"{value} {unit}".strip()
        if not isinstance(value, (int, float)): return f"{str(value)} {unit}".strip() 
        if math.isinf(value): return f"Infinito {unit}".strip()
        if math.isnan(value): return f"Indefinido {unit}".strip()
        try: dp = int(self.decimal_places_var.get())
        except ValueError: dp = 3 
        fmt_string = ""
        use_sci = self.scientific_notation_var.get()
        if use_sci: fmt_string = f"{{:.{dp}e}}"
        else:
            if abs(value) >= 1e7 or (abs(value) < 1e-4 and value != 0): fmt_string = f"{{:.{dp}e}}"
            else: fmt_string = f"{{:.{dp}f}}"
        if use_sci: fmt_string = f"{{:.{dp}e}}"
        return f"{fmt_string.format(value)} {unit}".strip()

    def save_configuration(self):
        selected_magnitudes_to_save = {name: var.get() for name, var in self.magnitude_plot_vars.items()}
        config_data = {
            'r_val': self.r_entry.get(), 'l_val': self.l_entry.get(), 'c_val': self.c_entry.get(),
            'include_r': self.include_r_var.get(), 'include_l': self.include_l_var.get(), 'include_c': self.include_c_var.get(),
            'v_mag': self.v_mag_entry.get(), 'v_phase_deg': self.v_phase_entry.get(),
            'freq_details': self.freq_details_entry.get(),
            'angle_unit': self.angle_unit.get(), 'topology': self.circuit_topology_var.get(),
            'freq_start': self.freq_start_entry.get(), 'freq_end': self.freq_end_entry.get(),
            'num_points': self.num_points_entry.get(), 
            'magnitude_plots': selected_magnitudes_to_save, 
            'phase_plot': self.selected_phase_plot_var.get(),
            'decimal_places': self.decimal_places_var.get(), 
            'scientific_notation': self.scientific_notation_var.get()
        }
        try:
            fp = filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json"),("All","*.*")],title="Salvar Config.")
            if fp:
                with open(fp,'w') as f: json.dump(config_data,f,indent=4)
                messagebox.showinfo("Salvar","Configuração salva!")
        except Exception as e: messagebox.showerror("Erro Salvar",f"Erro: {e}")

    def load_configuration(self):
        try:
            fp = filedialog.askopenfilename(defaultextension=".json",filetypes=[("JSON","*.json"),("All","*.*")],title="Carregar Config.")
            if fp:
                with open(fp,'r') as f: ld=json.load(f)
                self.r_entry.delete(0,tk.END); self.r_entry.insert(0,ld.get('r_val',"10"))
                self.l_entry.delete(0,tk.END); self.l_entry.insert(0,ld.get('l_val',"0.01"))
                self.c_entry.delete(0,tk.END); self.c_entry.insert(0,ld.get('c_val',"0.00001"))
                self.include_r_var.set(ld.get('include_r', True))
                self.include_l_var.set(ld.get('include_l', True))
                self.include_c_var.set(ld.get('include_c', True))
                self._on_include_component_change() 

                self.v_mag_entry.delete(0,tk.END); self.v_mag_entry.insert(0,ld.get('v_mag',"10"))
                self.v_phase_entry.delete(0,tk.END); self.v_phase_entry.insert(0,ld.get('v_phase_deg',"0"))
                self.freq_details_entry.delete(0,tk.END); self.freq_details_entry.insert(0,ld.get('freq_details',"159"))
                self.angle_unit.set(ld.get('angle_unit',"degrees")); self.circuit_topology_var.set(ld.get('topology',"Série"))
                self.freq_start_entry.delete(0,tk.END); self.freq_start_entry.insert(0,ld.get('freq_start',"50"))
                self.freq_end_entry.delete(0,tk.END); self.freq_end_entry.insert(0,ld.get('freq_end',"1000"))
                self.num_points_entry.delete(0,tk.END); self.num_points_entry.insert(0,ld.get('num_points',"300"))
                
                loaded_mag_plots = ld.get('magnitude_plots', {"|Z_total|": True})
                for name, var_obj in self.magnitude_plot_vars.items():
                    var_obj.set(loaded_mag_plots.get(name, False if name != "|Z_total|" else True))
                
                self.selected_phase_plot_var.set(ld.get('phase_plot', self.phase_plot_options[0]))
                
                self.decimal_places_var.set(ld.get('decimal_places',"3")); self.scientific_notation_var.set(ld.get('scientific_notation',False))
                messagebox.showinfo("Carregar","Configuração carregada!")
                self._trigger_realtime_plot_update(); 
                # self.analyze_circuit() 
        except FileNotFoundError: messagebox.showerror("Erro Carregar","Arquivo não encontrado.")
        except json.JSONDecodeError: messagebox.showerror("Erro Carregar","Arquivo inválido.")
        except Exception as e: messagebox.showerror("Erro Carregar",f"Erro: {e}")
    
    def _set_entry_error_style(self, entry_key, is_error=True):
        if entry_key in self.entry_widgets:
            widget=self.entry_widgets[entry_key]
            try: 
                dcs=ctk.ThemeManager.theme["CTkEntry"]["border_color"]; cm=ctk.get_appearance_mode().lower()
                nc=dcs[0] if isinstance(dcs,list) and cm=="light" else (dcs[1] if isinstance(dcs,list) else dcs)
                if nc is None: nc="#979797" if cm=="light" else "#565B5E"
            except: nc="gray50"
            tc=self.error_border_color if is_error else nc
            if isinstance(widget.cget("border_color"),list): widget.configure(border_color=[tc,tc])
            else: widget.configure(border_color=tc)
    
    def _clear_all_entry_error_styles(self):
        for wk in self.entry_widgets: self._set_entry_error_style(wk,is_error=False)

    def _validate_all_parameters(self, silent=True, check_detail_freq=False):
        self._clear_all_entry_error_styles(); params={}; error_messages=[]; error_fields=[]
        def gf(ew,pn,hn,include_var):
            if include_var is not None and not include_var.get(): params[pn]=0.0; return 0.0 
            try: v=float(ew.get());params[pn]=v;return v
            except ValueError: error_messages.append(f"{hn} inválido(a)."); error_fields.append(pn); return None
        def gi(ew,pn,hn):
            try: v=int(ew.get());params[pn]=v;return v
            except ValueError: error_messages.append(f"{hn} inválido(a)."); error_fields.append(pn); return None
        
        params['topology']=self.circuit_topology_var.get()
        gf(self.r_entry,'r_val',"Resistor (R)", self.include_r_var)
        gf(self.l_entry,'l_val',"Indutor (L)", self.include_l_var)
        gf(self.c_entry,'c_val',"Capacitor (C)", self.include_c_var)
        gf(self.v_mag_entry,'v_mag',"Tensão Fonte (Vmag)", None)
        gf(self.v_phase_entry,'v_phase_deg',"Fase Fonte (θv)", None)

        if self.include_r_var.get() and 'r_val' in params:
            if params['r_val']<0:error_messages.append("R não pode ser negativo.");error_fields.append('r_val')
            if params['r_val']==0 and params['topology']=="Paralelo" and not silent:error_messages.append("Atenção: R=0 em paralelo é curto.");error_fields.append('r_val')
        if self.include_l_var.get() and 'l_val' in params and params['l_val']<0:error_messages.append("L não pode ser negativo.");error_fields.append('l_val')
        if self.include_c_var.get() and 'c_val' in params and params['c_val']<0:error_messages.append("C não pode ser negativo.");error_fields.append('c_val')
        if 'v_mag' in params and params['v_mag']<0:error_messages.append("Vmag não pode ser negativa.");error_fields.append('v_mag')
        
        gf(self.freq_start_entry,'freq_start',"Frequência Inicial", None)
        gf(self.freq_end_entry,'freq_end',"Frequência Final", None)
        gi(self.num_points_entry,'num_points',"Número de Pontos")
        
        params['selected_magnitude_plots'] = [name for name, var in self.magnitude_plot_vars.items() if var.get()]
        params['selected_phase_plot'] = self.selected_phase_plot_var.get()
        if not params['selected_magnitude_plots'] and params['selected_phase_plot'] == "Nenhuma":
            error_messages.append("Selecione ao menos uma grandeza para plotar.")
            
        if 'freq_start' in params and params['freq_start']<=0:error_messages.append("Freq. Inicial > 0.");error_fields.append('freq_start')
        if 'freq_end' in params and 'freq_start' in params and params.get('freq_start') is not None and params['freq_end']<=params['freq_start']:error_messages.append("Freq. Final > Freq. Inicial.");error_fields.append('freq_end')
        if 'num_points' in params and params['num_points']<2:error_messages.append("Nº Pontos >= 2.");error_fields.append('num_points')
        
        params['freq_details']=None
        if check_detail_freq:
            fds=self.freq_details_entry.get()
            if fds:
                dfv=gf(self.freq_details_entry,'freq_details_val',"Freq. para Detalhes", None)
                if dfv is not None:
                    if dfv<=0:error_messages.append("Freq. para Detalhes > 0.");error_fields.append('freq_details')
                    else:params['freq_details']=dfv
        
        for fk in set(error_fields):self._set_entry_error_style(fk,is_error=True)
        if error_messages:
            uems=list(dict.fromkeys(error_messages))
            if not silent:messagebox.showerror("Erro Entrada","\n".join(uems))
            return None,uems
        return params,None

    def _calculate_sweep_data(self, params):
        f0_resonance=None; topology=params.get('topology',"Série")
        r_val = params.get('r_val',0) if self.include_r_var.get() else 0.0
        l_val = params.get('l_val',0) if self.include_l_var.get() else 0.0
        c_val = params.get('c_val',0) if self.include_c_var.get() else 0.0

        if l_val>1e-12 and c_val>1e-12:
            try: f0_resonance=1/(2*math.pi*math.sqrt(l_val*c_val))
            except ZeroDivisionError: f0_resonance=None
        
        freq_start=params.get('freq_start',1); freq_end=params.get('freq_end',1000); num_points=params.get('num_points',100)
        if freq_end > freq_start and freq_start > 0 :
             if freq_end / freq_start > 100:
                try: frequencies = np.logspace(np.log10(freq_start), np.log10(freq_end), num_points)
                except ValueError: frequencies = np.linspace(freq_start, freq_end, num_points)
             else: frequencies = np.linspace(freq_start, freq_end, num_points)
        else: frequencies = np.linspace(1, 1000, 100)
            
        all_plot_data_y = {} 
        for name in params['selected_magnitude_plots']: all_plot_data_y[name] = []
        if params['selected_phase_plot'] != "Nenhuma": all_plot_data_y[params['selected_phase_plot']] = []

        v_phase_rad=math.radians(params.get('v_phase_deg',0)); v_source_phasor_fixed=cmath.rect(params.get('v_mag',0),v_phase_rad)
        
        for freq_current in frequencies:
            # Define z_r, z_l, z_c com base na inclusão e topologia
            z_r = complex(r_val,0) if self.include_r_var.get() and r_val>1e-12 else \
                  (complex(1e-12,0) if topology=="Paralelo" and self.include_r_var.get() and r_val<=1e-12 else complex(0,0))
            if not self.include_r_var.get(): z_r = complex(float('inf'),0) if topology=="Paralelo" else complex(0,0)

            z_l = complex(0,2*cmath.pi*freq_current*l_val) if self.include_l_var.get() and l_val>1e-12 and freq_current>1e-12 else complex(0,0)
            if not self.include_l_var.get(): z_l = complex(float('inf'),0) if topology=="Paralelo" else complex(0,0)
            
            z_c = complex(0,-1/(2*cmath.pi*freq_current*c_val)) if self.include_c_var.get() and c_val>1e-12 and freq_current>1e-12 else complex(float('inf'),0)
            if not self.include_c_var.get(): z_c = complex(float('inf'),0)

            z_total_sweep,i_total_sweep_source=complex(0,0),complex(0,0)
            v_r_calc,v_l_calc,v_c_calc=complex(0,0),complex(0,0),complex(0,0)

            if topology=="Série":
                z_total_sweep = z_r + z_l + z_c 
                if abs(z_total_sweep)<1e-12: i_total_sweep_source=v_source_phasor_fixed/(1e-12+0j) if abs(v_source_phasor_fixed)>1e-12 else complex(0,0)
                elif abs(z_total_sweep)==float('inf'): i_total_sweep_source=complex(0,0)
                else: i_total_sweep_source=v_source_phasor_fixed/z_total_sweep
                
                v_r_calc=i_total_sweep_source*z_r if self.include_r_var.get() else complex(0,0)
                v_l_calc=i_total_sweep_source*z_l if self.include_l_var.get() else complex(0,0)
                if self.include_c_var.get():
                    v_c_calc=i_total_sweep_source*z_c if abs(z_c)!=float('inf') else \
                             (v_source_phasor_fixed-v_r_calc-v_l_calc if abs(i_total_sweep_source)<1e-9 else complex(0,0) )
                else: v_c_calc = complex(0,0)
            
            elif topology=="Paralelo":
                y_r=1/z_r if self.include_r_var.get() and abs(z_r)>1e-12 else complex(0,0) 
                y_l=1/z_l if self.include_l_var.get() and abs(z_l)>1e-12 else complex(0,0)
                y_c=1/z_c if self.include_c_var.get() and abs(z_c)>1e-12 and abs(z_c)!=float('inf') else complex(0,0)
                     
                y_total_sweep=y_r+y_l+y_c
                z_total_sweep=1/y_total_sweep if abs(y_total_sweep)>1e-12 else complex(float('inf'),0)
                i_total_sweep_source=v_source_phasor_fixed*y_total_sweep
                v_r_calc=v_l_calc=v_c_calc=v_source_phasor_fixed
            
            temp_val_map = {
                "|Z_total|": abs(z_total_sweep),
                "|I_total|": abs(i_total_sweep_source),
                "|V_R|": abs(v_r_calc) if self.include_r_var.get() else np.nan,
                "|V_L|": abs(v_l_calc) if self.include_l_var.get() else np.nan,
                "|V_C|": abs(v_c_calc) if self.include_c_var.get() else np.nan,
                "Fase(Z_total) (°)": math.degrees(cmath.phase(z_total_sweep)) if abs(z_total_sweep)!=float('inf') and abs(z_total_sweep)>1e-12 else 0.0,
                "Fase(I_total) (°)": math.degrees(cmath.phase(i_total_sweep_source)) if abs(i_total_sweep_source)>1e-12 else 0.0,
                "Fase(V_R) (°)": math.degrees(cmath.phase(v_r_calc)) if self.include_r_var.get() and abs(v_r_calc)>1e-12 else 0.0,
                "Fase(V_L) (°)": math.degrees(cmath.phase(v_l_calc)) if self.include_l_var.get() and abs(v_l_calc)>1e-12 else 0.0,
                "Fase(V_C) (°)": math.degrees(cmath.phase(v_c_calc)) if self.include_c_var.get() and abs(v_c_calc)>1e-12 else 0.0,
            }
            for name in all_plot_data_y.keys():
                if name in temp_val_map:
                    all_plot_data_y[name].append(temp_val_map[name])
                elif len(all_plot_data_y[name]) < len(frequencies): 
                     all_plot_data_y[name].append(np.nan)
        return frequencies, all_plot_data_y, f0_resonance

    def _trigger_realtime_plot_update(self, event=None, from_combobox_value=None):
        params, errors = self._validate_all_parameters(silent=True, check_detail_freq=False)
        if params:
            try:
                self.results_text.configure(state="normal"); self.results_text.delete("1.0", "end")
                self.results_text.insert("1.0", f"Atualizando gráfico..."); self.results_text.configure(state="disabled")
                self.master.update_idletasks()

                frequencies, all_plot_data_y, f0_calc = self._calculate_sweep_data(params)
                
                extremum_info_for_plot = None
                if params['selected_magnitude_plots']:
                    first_mag_plot = params['selected_magnitude_plots'][0]
                    if first_mag_plot in all_plot_data_y and all_plot_data_y[first_mag_plot]:
                        extremum_info_for_plot = self._find_extremum(frequencies, all_plot_data_y[first_mag_plot], first_mag_plot, params['topology'])

                self._update_embedded_plot(frequencies, all_plot_data_y, params, f0_resonance=f0_calc, extremum_info_main=extremum_info_for_plot)
                
                self.results_text.configure(state="normal"); self.results_text.delete("1.0", "end")
                plotted_vars_str = ", ".join(params['selected_magnitude_plots'])
                if params['selected_phase_plot'] != "Nenhuma":
                    if plotted_vars_str: plotted_vars_str += " & "
                    plotted_vars_str += params['selected_phase_plot']
                self.results_text.insert("1.0", f"Gráfico ({params['topology']}) atualizado: {plotted_vars_str or 'Nenhuma'}.\n(Pressione 'Analisar e Plotar' para resultados textuais)")
                self.results_text.configure(state="disabled")
            except Exception as e:
                print(f"Erro RT plot: {e}"); import traceback; traceback.print_exc()
                self._clear_embedded_plot(error_message="Erro ao atualizar gráfico.") 
        else:
            self._clear_embedded_plot(error_message=f"Parâmetros inválidos:\n{', '.join(errors if errors else [])}")
    
    def _find_extremum(self, frequencies, data_y_single_series, plot_choice_single, topology):
        # ... (Permanece o mesmo) ...
        if not data_y_single_series or not isinstance(data_y_single_series,(list,np.ndarray)) or len(data_y_single_series)==0:return None
        valid_data_y=[val for val in data_y_single_series if isinstance(val,(int,float)) and not (math.isinf(val) or math.isnan(val))]
        if not valid_data_y:return None
        extremum_type,extremum_value_raw,extremum_freq = None,None,None 
        if "|" in plot_choice_single: 
            if topology=="Série":
                if "Z_total" in plot_choice_single:extremum_type="min"
                else:extremum_type="max" 
            elif topology=="Paralelo":
                if "I_total" in plot_choice_single:extremum_type="min" 
                elif "Z_total" in plot_choice_single:extremum_type="max" 
                else:extremum_type="max" 
            if extremum_type=="min":extremum_value_raw=min(valid_data_y) if valid_data_y else None
            elif extremum_type=="max":extremum_value_raw=max(valid_data_y) if valid_data_y else None
            else:return None 
            if extremum_value_raw is None:return None
            try:
                original_indices=[i for i,val in enumerate(data_y_single_series) if math.isclose(val,extremum_value_raw,rel_tol=1e-9)]
                if original_indices: 
                    extremum_index=original_indices[0]
                    extremum_freq=frequencies[extremum_index]
                    unit_base=""
                    if "Z_total" in plot_choice_single:unit_base="Ω"
                    elif "I_total" in plot_choice_single:unit_base="A"
                    elif "V_" in plot_choice_single:unit_base="V"
                    extremum_value_formatted=self._format_value(extremum_value_raw,unit_base)
                    return extremum_type,extremum_freq,extremum_value_raw,extremum_value_formatted
                else:return None
            except (ValueError,IndexError):return None
        return None
            
    def _clear_embedded_plot(self, error_message=None): 
        if self.ax_embedded: self.ax_embedded.clear()
        if hasattr(self,'ax2_embedded') and self.ax2_embedded and self.ax2_embedded.figure : 
            self.ax2_embedded.clear(); self.ax2_embedded.set_visible(False)
        if error_message:
            fontsize=9 if len(error_message)<70 else 7
            self.ax_embedded.text(0.5,0.5,error_message,ha='center',va='center',fontsize=fontsize,color='red',wrap=True)
            self.ax_embedded.set_title("Erro de Plotagem",fontsize=10)
        else: self.ax_embedded.set_title("Aguardando Análise / Configuração",fontsize=10)
        self.ax_embedded.set_xlabel("Frequência (Hz)",fontsize=9); self.ax_embedded.set_ylabel("Magnitude",fontsize=9)
        self.ax_embedded.grid(True,which="both",linestyle="--",linewidth=0.5)
        self.ax_embedded.tick_params(axis='both',which='major',labelsize=8)
        self.ax_embedded.set_xscale('linear'); self.ax_embedded.set_yscale('linear')
        if self.fig_embedded: 
            try: self.fig_embedded.tight_layout(pad=0.5)
            except Exception: 
                try: self.fig_embedded.subplots_adjust(left=0.15,bottom=0.20,right=0.85 if self.ax2_embedded and self.ax2_embedded.get_visible() else 0.95,top=0.90)
                except Exception:pass
        if self.canvas_embedded: self.canvas_embedded.draw()
            
    def clear_entries(self):
        self._clear_all_entry_error_styles()
        self.r_entry.delete(0,"end"); self.r_entry.insert(0,"10") 
        self.l_entry.delete(0,"end"); self.l_entry.insert(0,"0.01")
        self.c_entry.delete(0,"end"); self.c_entry.insert(0,"0.00001")
        self.include_r_var.set(True); self.include_l_var.set(True); self.include_c_var.set(True)
        self._on_include_component_change()
        self.v_mag_entry.delete(0,"end"); self.v_mag_entry.insert(0,"10")
        self.v_phase_entry.delete(0,"end"); self.v_phase_entry.insert(0,"0")
        self.freq_details_entry.delete(0,"end"); self.freq_details_entry.insert(0,"159") 
        self.freq_start_entry.delete(0,"end"); self.freq_start_entry.insert(0,"50")
        self.freq_end_entry.delete(0,"end"); self.freq_end_entry.insert(0,"1000")
        self.num_points_entry.delete(0,"end"); self.num_points_entry.insert(0,"300")
        for name, var in self.magnitude_plot_vars.items(): var.set(True if name == "|Z_total|" else False)
        self.selected_phase_plot_var.set(self.phase_plot_options[0])
        self.angle_unit.set("degrees"); self.circuit_topology_var.set("Série")
        self.decimal_places_var.set("3"); self.scientific_notation_var.set(False)
        self.results_text.configure(state="normal"); self.results_text.delete("1.0","end"); self.results_text.configure(state="disabled")
        self._trigger_realtime_plot_update()

    def _grab_toplevel_safely(self, toplevel_window): # NOVO MÉTODO AUXILIAR
        if toplevel_window and toplevel_window.winfo_exists():
            try:
                toplevel_window.grab_set()
            except tk.TclError as e:
                print(f"Alerta TclError final em grab_set (após delay): {e}")

    def show_about_dialog_ctk(self): # CORRIGIDO E EXPANDIDO
        if self.about_dialog_window and self.about_dialog_window.winfo_exists():
            self.about_dialog_window.lift(); self.about_dialog_window.focus_set(); return
            
        self.about_dialog_window = ctk.CTkToplevel(self.master)
        self.about_dialog_window.title("Sobre Analisador de Circuito CA")
        self.about_dialog_window.geometry("500x650") 
        self.about_dialog_window.transient(self.master) 
        
        self.about_dialog_window.after(50, self._grab_toplevel_safely, self.about_dialog_window) # Usa o método auxiliar

        about_scroll_frame = ctk.CTkScrollableFrame(self.about_dialog_window, corner_radius=0, fg_color="transparent")
        about_scroll_frame.pack(expand=True, fill="both", padx=0, pady=0)
        
        content_frame = ctk.CTkFrame(about_scroll_frame) 
        content_frame.pack(expand=True, fill="x", padx=15, pady=15)

        ctk.CTkLabel(content_frame, text="Analisador de Circuito CA", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0,15))
        
        info_text = (
            "**Versão:** 2.0.0 (Super Sprint)\n\n"
            "Ferramenta para análise de circuitos RLC CA.\n\n"
            "**Funcionalidades Implementadas:**\n"
            "- Análise de circuitos RLC **Série** e **Paralelo**.\n"
            "- Seleção explícita de componentes (R, L, C) para análise.\n"
            "- Varredura de frequência com plotagem gráfica incorporada:\n"
            "  - Múltiplas curvas de magnitude no mesmo gráfico.\n"
            "  - Plotagem de uma curva de fase em eixo Y secundário.\n"
            "- Atualização do gráfico em tempo real ao modificar parâmetros.\n"
            "- Escala do gráfico (X e Y) determinada automaticamente (Log/Linear).\n"
            "- Exibição da frequência de ressonância (f0) teórica no gráfico.\n"
            "- Marcação de pontos de máximo/mínimo na curva plotada.\n"
            "- Cálculo e exibição do Fator de Qualidade (Q) e Largura de Banda (BW).\n"
            "- Análise detalhada para uma frequência específica, incluindo:\n"
            "  - Impedâncias (Z_R, Z_L, Z_C, Z_Total)\n" 
            "  - Correntes (I_Total, I_R, I_L, I_C)\n" 
            "  - Tensões (V_R, V_L, V_C)\n" 
            "  - Potências Totais (Aparente, Ativa, Reativa).\n"
            "  - Potências por Componente (P_R, Q_L, Q_C).\n" 
            "  - Fator de Potência (FP) total.\n"
            "- Tratamento de casos RL e RC (L=0 ou C=0), com f0, Q, BW como N/A.\n"
            "- Validação de entradas com feedback visual (bordas vermelhas).\n"
            "- Interface gráfica com painéis para configuração e resultados.\n"
            "- Barra de ferramentas Matplotlib no gráfico (Zoom, Pan, Salvar Imagem).\n"
            "- Salvar e Carregar configurações da análise em arquivos JSON.\n"
            "- Mensagem de erro/status no gráfico se parâmetros de plotagem forem inválidos.\n"
            "- Feedback textual ('Calculando...') e barra de progresso para varreduras.\n"
            "- Opções de formatação de saída (casas decimais, notação científica).\n\n"
            "**Próximos Passos (Ideias):**\n"
            "- Entrada de circuito via Netlist (simplificada).\n"
            "- Barra de progresso visual mais granular para varreduras longas.\n"
            "- Suporte a mais topologias / Análise Nodal.\n\n"
            "Agradecimentos por utilizar!"
        )
        ctk.CTkLabel(content_frame, text=info_text, justify="left", wraplength=420).pack(pady=10, padx=5, anchor="w")
        
        close_button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        close_button_frame.pack(pady=(15,5), fill="x")
        close_button = ctk.CTkButton(close_button_frame, text="Fechar", command=self.about_dialog_window.destroy, width=100)
        close_button.pack()

        self.about_dialog_window.after(10, self._center_toplevel_after_draw, self.about_dialog_window)
        self.about_dialog_window.focus_set()

    def _center_toplevel_after_draw(self, toplevel_window):
        # ... (Permanece o mesmo) ...
        toplevel_window.update_idletasks()
        master_x=self.master.winfo_x(); master_y=self.master.winfo_y()
        master_width=self.master.winfo_width(); master_height=self.master.winfo_height()
        popup_width=toplevel_window.winfo_width(); popup_height=toplevel_window.winfo_height()
        if popup_width<=1 or popup_height<=1: 
            try:
                geom_str = str(toplevel_window.geometry()); size_part = geom_str.split('+')[0]
                popup_width,popup_height = map(int, size_part.split('x'))
            except: 
                try: popup_width=int(toplevel_window.cget("width"));popup_height=int(toplevel_window.cget("height"))
                except: popup_width,popup_height=500,650 
        center_x=master_x+(master_width-popup_width)//2; center_y=master_y+(master_height-popup_height)//2
        toplevel_window.geometry(f"{popup_width}x{popup_height}+{center_x}+{center_y}")

    def analyze_circuit(self): 
        self.results_text.configure(state="normal"); self.results_text.delete("1.0","end"); self._clear_all_entry_error_styles()
        params,errors=self._validate_all_parameters(silent=False,check_detail_freq=True)
        if not params:
            self.results_text.insert("1.0","Erro de entrada:\n"+"\n".join(errors if errors else ["Valores inválidos."]))
            self._clear_embedded_plot(error_message="Parâmetros de análise inválidos.")
            self.results_text.configure(state="disabled"); return
        
        self.progress_bar_frame.pack(pady=(5,0),padx=10,fill="x",before=self.note_label) # CORRIGIDO: before=self.note_label
        self.progress_bar.pack(pady=5,padx=0,fill="x"); self.progress_bar.start(); self.master.update_idletasks()
        output_text=""
        try:
            frequencies,all_plot_data_y,f0_calc=self._calculate_sweep_data(params)
            extremum_info_for_plot=None
            if params['selected_magnitude_plots']:
                first_mag_plot=params['selected_magnitude_plots'][0]
                if first_mag_plot in all_plot_data_y and all_plot_data_y[first_mag_plot]:
                    extremum_info_for_plot=self._find_extremum(frequencies,all_plot_data_y[first_mag_plot],first_mag_plot,params['topology'])
            self._update_embedded_plot(frequencies,all_plot_data_y,params,f0_resonance=f0_calc,extremum_info_main=extremum_info_for_plot)
            self.results_text.delete("1.0","end")
            output_text+=f"--- Resumo da Varredura ({params['topology']}) ---\n"
            output_text+=f"  Componentes Incluídos: R={'S' if self.include_r_var.get() else 'N'}, L={'S' if self.include_l_var.get() else 'N'}, C={'S' if self.include_c_var.get() else 'N'}\n"
            output_text+=f"  Intervalo: {self._format_value(params['freq_start'])} Hz a {self._format_value(params['freq_end'])} Hz ({params['num_points']} pontos).\n"
            plot_selection_str=", ".join(params['selected_magnitude_plots'])
            if params['selected_phase_plot']!="Nenhuma":
                if plot_selection_str:plot_selection_str+=" & "
                plot_selection_str+=params['selected_phase_plot']
            output_text+=f"  Grandezas Plotadas: {plot_selection_str or 'Nenhuma'}\n"
            q_factor_str,bandwidth_str,f0_calc_str="N/A","N/A","N/A"
            if f0_calc is not None:
                f0_calc_str=self._format_value(f0_calc,"Hz")
                omega_0=2*math.pi*f0_calc
                r_val_q = params.get('r_val',0) if self.include_r_var.get() else 0
                l_val_q = params.get('l_val',0) if self.include_l_var.get() else 0
                c_val_q = params.get('c_val',0) if self.include_c_var.get() else 0
                q_factor_val=None
                if l_val_q>1e-12 and c_val_q>1e-12:
                    if params['topology']=="Série":
                        if r_val_q>1e-12:q_factor_val=(omega_0*l_val_q)/r_val_q
                        else:q_factor_val=float('inf')
                    elif params['topology']=="Paralelo":
                        if r_val_q>1e-12:
                            if l_val_q>1e-12 and omega_0>1e-9:q_factor_val=r_val_q/(omega_0*l_val_q)
                            elif c_val_q>1e-12 and omega_0>1e-9:q_factor_val=omega_0*c_val_q*r_val_q
                        else:q_factor_val=float('inf') 
                elif self.include_r_var.get() and r_val_q > 1e-12: 
                     if self.include_l_var.get() and l_val_q > 1e-12 and not self.include_c_var.get() and freq_current > 1e-12: # freq_current não definido aqui
                          # Q para RL série é X_L/R na frequência de interesse. Não f0.
                          pass 
                     elif self.include_c_var.get() and c_val_q > 1e-12 and not self.include_l_var.get() and freq_current > 1e-12: # freq_current não definido aqui
                          # Q para RC série é X_C/R na frequência de interesse. Não f0.
                          pass
                if q_factor_val is not None:
                    if q_factor_val==float('inf'):q_factor_str,bandwidth_str="Infinito",self._format_value(0.0,"Hz")
                    elif q_factor_val>1e-9:q_factor_str=self._format_value(q_factor_val);bandwidth_str=self._format_value(f0_calc/q_factor_val,"Hz") if f0_calc else "N/A"
                    else:q_factor_str,bandwidth_str=self._format_value(q_factor_val)+" (Baixo)","Muito Larga" if f0_calc else "N/A"
            output_text+=f"  Frequência de Ressonância (f0): {f0_calc_str}\n"
            output_text+=f"    Fator de Qualidade (Q): {q_factor_str}\n"
            output_text+=f"    Largura de Banda (BW): {bandwidth_str}\n"
            if extremum_info_for_plot:
                 output_text+=f"  Ponto Extremo ({extremum_info_for_plot[0]} em {params['selected_magnitude_plots'][0] if params['selected_magnitude_plots'] else 'N/A'}): {extremum_info_for_plot[3]} @ {self._format_value(extremum_info_for_plot[1],'Hz')}\n"
            output_text+="-------------------------------------------\n\n"
            if params.get('freq_details') is not None:
                output_text+=self._get_single_frequency_analysis_details(params,params['freq_details'])
            else:output_text+="Nenhuma frequência para análise detalhada foi fornecida ou era inválida.\n"
            self.results_text.insert("1.0",output_text)
        except Exception as e:
            self.results_text.delete("1.0","end");error_msg=f"Erro inesperado: {str(e)}"
            messagebox.showerror("Erro Inesperado",error_msg);self.results_text.insert("1.0",error_msg)
            self._clear_embedded_plot(error_message="Erro na análise.")
            import traceback;traceback.print_exc()
        finally:
            self.progress_bar.stop();self.progress_bar.pack_forget();self.progress_bar_frame.pack_forget()
            self.results_text.configure(state="disabled")

    def _get_single_frequency_analysis_details(self, circuit_params, specific_freq):
        # ... (Permanece o mesmo da última versão) ...
        output = ""
        try:
            include_r = self.include_r_var.get(); include_l = self.include_l_var.get(); include_c = self.include_c_var.get()
            r_val = circuit_params.get('r_val',0) if include_r else 0.0
            l_val = circuit_params.get('l_val',0) if include_l else 0.0
            c_val = circuit_params.get('c_val',0) if include_c else 0.0
            v_mag=circuit_params.get('v_mag',0); v_phase_deg=circuit_params.get('v_phase_deg',0)
            topology=circuit_params.get('topology',"Série"); freq=specific_freq
            v_phase_rad=math.radians(v_phase_deg); v_source_phasor=cmath.rect(v_mag,v_phase_rad)
            z_r_val,z_l_val,z_c_val,xl_val,xc_val=complex(0,0),complex(0,0),complex(0,0),0.0,0.0
            if include_r:
                if r_val > 1e-12 : z_r_val = complex(r_val,0)
                elif r_val < 1e-12 and topology=="Paralelo": z_r_val = complex(1e-12,0)
                else: z_r_val = complex(0,0) 
            else: z_r_val = complex(float('inf'),0) if topology=="Paralelo" else complex(0,0) 
            if include_l:
                if l_val > 1e-12 and freq > 1e-12: xl_val=2*cmath.pi*freq*l_val; z_l_val=complex(0,xl_val)
                else: z_l_val=complex(0,0)
            else: z_l_val = complex(float('inf'),0) if topology=="Paralelo" else complex(0,0)
            if include_c:
                if c_val > 1e-12 and freq > 1e-12: xc_val=-1/(2*cmath.pi*freq*c_val); z_c_val=complex(0,xc_val)
                else: z_c_val=complex(float('inf'),0)
            else: z_c_val=complex(float('inf'),0) 
            z_total,i_total_source_phasor=complex(0,0),complex(0,0)
            v_r_phasor,v_l_phasor,v_c_phasor=complex(0,0),complex(0,0),complex(0,0)
            i_r_phasor,i_l_phasor,i_c_phasor=complex(0,0),complex(0,0),complex(0,0)
            p_r_comp,q_l_comp,q_c_comp=0.0,0.0,0.0
            if topology == "Série":
                z_total=z_r_val+z_l_val+z_c_val
                if abs(z_total)<1e-12:i_total_source_phasor=v_source_phasor/(1e-12+0j) if abs(v_source_phasor)>1e-12 else complex(0,0)
                elif abs(z_total)==float('inf'):i_total_source_phasor=complex(0,0)
                else:i_total_source_phasor=v_source_phasor/z_total
                if include_r:v_r_phasor=i_total_source_phasor*z_r_val
                if include_l:v_l_phasor=i_total_source_phasor*z_l_val
                if include_c:v_c_phasor=i_total_source_phasor*z_c_val if abs(z_c_val)!=float('inf') else (v_source_phasor-v_r_phasor-v_l_phasor if abs(i_total_source_phasor)<1e-9 else i_total_source_phasor*z_c_val)
                i_r_phasor=i_total_source_phasor if include_r else complex(0,0)
                i_l_phasor=i_total_source_phasor if include_l else complex(0,0)
                i_c_phasor=i_total_source_phasor if include_c and abs(z_c_val)!=float('inf') else complex(0,0)
                if include_r and r_val > 1e-12:p_r_comp=(abs(i_r_phasor)**2)*r_val
                if include_l and l_val>1e-12 and freq>1e-12 and abs(xl_val)>1e-12:q_l_comp=(abs(i_l_phasor)**2)*xl_val
                if include_c and c_val>1e-12 and freq>1e-12 and abs(xc_val)>1e-12:q_c_comp=(abs(i_c_phasor)**2)*xc_val 
            elif topology == "Paralelo":
                y_r=1/z_r_val if include_r and abs(z_r_val)>1e-12 else complex(0,0)
                y_l=1/z_l_val if include_l and abs(z_l_val)>1e-12 else complex(0,0)
                y_c=1/z_c_val if include_c and abs(z_c_val)>1e-12 and abs(z_c_val)!=float('inf') else complex(0,0)
                y_total=y_r+y_l+y_c
                z_total=1/y_total if abs(y_total)>1e-12 else complex(float('inf'),0)
                i_total_source_phasor=v_source_phasor*y_total 
                v_r_phasor=v_l_phasor=v_c_phasor=v_source_phasor
                if include_r:i_r_phasor=v_source_phasor*y_r 
                if include_l:i_l_phasor=v_source_phasor*y_l
                if include_c:i_c_phasor=v_source_phasor*y_c
                if include_r and r_val > 1e-12: p_r_comp=(abs(v_source_phasor)**2)/r_val
                elif include_r and r_val < 1e-12 and abs(i_r_phasor) != float('inf') : p_r_comp = abs(v_source_phasor * i_r_phasor.conjugate()).real 
                if include_l and l_val > 1e-12 and freq > 1e-12 and abs(xl_val) > 1e-12 : q_l_comp=(abs(v_source_phasor)**2)/xl_val
                elif include_l and l_val < 1e-12 and freq > 1e-12 and abs(i_l_phasor) != float('inf'): q_l_comp = (v_source_phasor * i_l_phasor.conjugate()).imag 
                if include_c and c_val > 1e-12 and freq > 1e-12 and abs(xc_val) > 1e-12 : q_c_comp=(abs(v_source_phasor)**2)/xc_val
            output += f"--- Detalhes para Frequência: {self._format_value(freq, 'Hz')} ({topology}) ---\n"
            output += f"  Componentes Incluídos: R={'S' if self.include_r_var.get() else 'N'}, L={'S' if self.include_l_var.get() else 'N'}, C={'S' if self.include_c_var.get() else 'N'}\n"
            if abs(z_total)==float('inf') and not (self.include_r_var.get() or self.include_l_var.get() or self.include_c_var.get()):
                 output += f"  Impedância Total (Z_total): {self._format_value(float('inf'), 'Ω')} (Circuito totalmente aberto)\n"
                 output += f"  Corrente Total (I_total Fonte): {self.format_phasor(complex(0,0), 'A')}\n"
            elif abs(z_total)==float('inf'):
                 output += f"  Impedância Total (Z_total): {self._format_value(float('inf'), 'Ω')}\n"
                 output += f"  Corrente Total (I_total Fonte): {self.format_phasor(i_total_source_phasor, 'A')}\n"
            else:
                output += f"  Impedância Total (Z_total): {self.format_phasor(z_total, 'Ω')}\n"
                output += f"  Corrente Total (I_total Fonte): {self.format_phasor(i_total_source_phasor, 'A')}\n"
            output += "  ---------------------------\n"
            if topology=="Série":
                if self.include_r_var.get(): output += f"  Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                if self.include_l_var.get(): output += f"  Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                if self.include_c_var.get(): output += f"  Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
            elif topology=="Paralelo":
                output += f"  Tensão nos Componentes (V_fonte): {self.format_phasor(v_source_phasor, 'V')}\n"
                if self.include_r_var.get(): output += f"  Corrente em R (I_R): {self.format_phasor(i_r_phasor, 'A')}\n"
                if self.include_l_var.get(): output += f"  Corrente em L (I_L): {self.format_phasor(i_l_phasor, 'A')}\n"
                if self.include_c_var.get(): output += f"  Corrente em C (I_C): {self.format_phasor(i_c_phasor, 'A')}\n"
            output += "  ---------------------------\n  Análise de Potência (Total da Fonte):\n"
            s_complex=v_source_phasor*i_total_source_phasor.conjugate()
            p_real,q_reactive,s_apparent_mag=s_complex.real,s_complex.imag,abs(s_complex)
            power_factor=p_real/s_apparent_mag if s_apparent_mag>1e-9 else (1.0 if abs(p_real)>1e-9 and abs(q_reactive)<1e-9 else 0.0)
            fp_type,epsilon="(N/A)",1e-9
            if abs(s_apparent_mag)<epsilon: fp_type="(N/A - sem potência significante)"
            elif abs(q_reactive)<epsilon: fp_type="(unitário)"
            elif q_reactive > 0: fp_type="(atrasado - indutivo)"
            else: fp_type="(adiantado - capacitivo)"
            output += f"    Potência Aparente (|S|): {self._format_value(s_apparent_mag, 'VA')}\n    Potência Ativa (P): {self._format_value(p_real, 'W')}\n"
            output += f"    Potência Reativa (Q): {self._format_value(q_reactive, 'VAR')}\n    Fator de Potência (FP): {self._format_value(power_factor)} {fp_type}\n"
            output += "  ---------------------------\n  Potências nos Componentes:\n"
            if self.include_r_var.get(): output += f"    Potência Ativa no Resistor (P_R): {self._format_value(p_r_comp, 'W')}\n"
            else: output += "    P_R: N/A (R não incluído)\n"
            if self.include_l_var.get(): output += f"    Potência Reativa no Indutor (Q_L): {self._format_value(q_l_comp, 'VAR')}\n"
            else: output += "    Q_L: N/A (L não incluído)\n"
            if self.include_c_var.get(): output += f"    Potência Reativa no Capacitor (Q_C): {self._format_value(q_c_comp, 'VAR')}\n"
            else: output += "    Q_C: N/A (C não incluído)\n"
            if self.include_r_var.get() and not (math.isinf(p_r_comp) or math.isinf(p_real) or math.isnan(p_r_comp) or math.isnan(p_real)):
                 if abs(p_real)>1e-6 or abs(p_r_comp)>1e-6 :
                    output += f"    (Verificação P_R ≈ P_total: {'Sim' if math.isclose(p_r_comp, p_real, rel_tol=1e-2, abs_tol=1e-3) else 'Não'})\n"
            q_sum_comp_valid = True; q_sum_comp = 0
            if self.include_l_var.get():
                if math.isinf(q_l_comp) or math.isnan(q_l_comp): q_sum_comp_valid = False
                else: q_sum_comp += q_l_comp
            if self.include_c_var.get():
                if math.isinf(q_c_comp) or math.isnan(q_c_comp): q_sum_comp_valid = False
                else: q_sum_comp += q_c_comp
            if q_sum_comp_valid and not (math.isinf(q_reactive) or math.isnan(q_reactive)):
                if abs(q_reactive)>1e-6 or abs(q_sum_comp)>1e-6:
                    abs_tol_q_sum = max(1e-3, abs(q_l_comp)*1e-2 if self.include_l_var.get() and not math.isinf(q_l_comp) else 0, \
                                          abs(q_c_comp)*1e-2 if self.include_c_var.get() and not math.isinf(q_c_comp) else 0) 
                    output += f"    (Verificação Q_L+Q_C ≈ Q_total: {'Sim' if math.isclose(q_sum_comp, q_reactive, rel_tol=1e-2, abs_tol=abs_tol_q_sum) else 'Não'})\n"
            return output
        except Exception as e:
            import traceback; traceback.print_exc()
            return f"  Erro ao calcular detalhes para {self._format_value(specific_freq, 'Hz')} ({topology}): {e}\n"

    def _update_embedded_plot(self, frequencies, all_plot_data_y, params, f0_resonance=None, extremum_info_main=None):
        # ... (Permanece o mesmo da última versão) ...
        if not (self.fig_embedded and self.ax_embedded and self.canvas_embedded): return 
        self.ax_embedded.clear()
        if hasattr(self,'ax2_embedded') and self.ax2_embedded and self.ax2_embedded.figure : self.ax2_embedded.clear(); self.ax2_embedded.set_visible(False)
        else: self.ax2_embedded = None 
        use_log_x = False
        if len(frequencies) > 1 and frequencies[0] > 0 and frequencies[-1]/frequencies[0] > 100: use_log_x = True
        self.ax_embedded.set_xscale('log' if use_log_x else 'linear')
        lines_plotted = []; labels_plotted = []; color_index = 0; primary_y_log_needed = False
        if params['selected_magnitude_plots']:
            all_mag_data_flat = []
            for name in params['selected_magnitude_plots']:
                if name in all_plot_data_y and all_plot_data_y[name]: all_mag_data_flat.extend(filter(lambda x: isinstance(x,(int,float)) and not math.isinf(x) and not math.isnan(x) and x > 1e-9, all_plot_data_y[name]))
            if all_mag_data_flat:
                min_val,max_val=min(all_mag_data_flat),max(all_mag_data_flat)
                if min_val>0 and max_val/min_val>1000:primary_y_log_needed=True
        self.ax_embedded.set_yscale('log' if primary_y_log_needed else 'linear')
        first_line_color = None
        for name in params['selected_magnitude_plots']:
            if name in all_plot_data_y and all_plot_data_y[name]:
                current_color = self.plot_colors[color_index % len(self.plot_colors)]
                if first_line_color is None: first_line_color = current_color
                line, = self.ax_embedded.plot(frequencies, all_plot_data_y[name], marker='.', linestyle='-', markersize=2, color=current_color, label=name)
                lines_plotted.append(line); labels_plotted.append(name); color_index += 1
        self.ax_embedded.set_ylabel("Magnitude", fontsize=9, color=first_line_color if first_line_color else 'black')
        self.ax_embedded.tick_params(axis='y', labelcolor=first_line_color if first_line_color else 'black')
        selected_phase_name = params['selected_phase_plot']
        if selected_phase_name != "Nenhuma" and selected_phase_name in all_plot_data_y and all_plot_data_y[selected_phase_name]:
            if not self.ax2_embedded or not hasattr(self.ax2_embedded,'plot'): self.ax2_embedded = self.ax_embedded.twinx()
            else: self.ax2_embedded.clear()
            self.ax2_embedded.set_visible(True); phase_color=self.plot_colors[color_index % len(self.plot_colors)]
            line_phase, = self.ax2_embedded.plot(frequencies,all_plot_data_y[selected_phase_name],marker='.',linestyle=':',markersize=2,color=phase_color,label=selected_phase_name)
            self.ax2_embedded.set_ylabel(selected_phase_name,fontsize=9,color=phase_color); self.ax2_embedded.tick_params(axis='y',labelcolor=phase_color)
            self.ax2_embedded.set_yscale('linear'); lines_plotted.append(line_phase); labels_plotted.append(selected_phase_name)
        title_parts = []
        if params['selected_magnitude_plots']: title_parts.extend(params['selected_magnitude_plots'])
        if params['selected_phase_plot'] != "Nenhuma": title_parts.append(params['selected_phase_plot'])
        plot_title = (", ".join(title_parts) if title_parts else "Resposta") + f" vs Frequência ({params['topology']})"
        self.ax_embedded.set_title(plot_title, fontsize=10); self.ax_embedded.set_xlabel("Frequência (Hz)", fontsize=9)
        self.ax_embedded.grid(True, which="both", linestyle="--", linewidth=0.5); self.ax_embedded.tick_params(axis='both', which='major', labelsize=8)
        if f0_resonance is not None and len(frequencies)>0 and frequencies[0]<=f0_resonance<=frequencies[-1]:
            line_f0 = self.ax_embedded.axvline(x=f0_resonance, color='dimgray', linestyle='-.', linewidth=1.2)
            if not any(l.get_label() == f'$f_0 \\approx$ {self._format_value(f0_resonance, "Hz")}' for l in lines_plotted if hasattr(l, 'get_label')):
                 lines_plotted.append(line_f0); labels_plotted.append(f'$f_0 \\approx$ {self._format_value(f0_resonance, "Hz")}')
        if extremum_info_main and params['selected_magnitude_plots']:
            etype, efreq, evalue_raw, evalue_formatted = extremum_info_main
            first_mag_plot_name = params['selected_magnitude_plots'][0]
            text_label=f"{etype.capitalize()} ({first_mag_plot_name}):\n{evalue_formatted}\n@ {self._format_value(efreq, 'Hz')}"
            marker_color='darkgreen' if etype=='max' else 'indigo'
            self.ax_embedded.plot(efreq, evalue_raw, marker='o', color=marker_color, markersize=5, fillstyle='none', markeredgewidth=1.2)
            y_lim=self.ax_embedded.get_ylim();x_lim=self.ax_embedded.get_xlim()
            y_range_plot=y_lim[1]-y_lim[0] if y_lim[1]>y_lim[0] else 1.0
            if y_range_plot==0 or math.isinf(y_range_plot) or math.isnan(y_range_plot):y_range_plot=abs(evalue_raw) if evalue_raw!=0 else 1.0
            offset_y_factor=0.05; offset_y=y_range_plot*offset_y_factor
            text_y_pos=evalue_raw+(offset_y if etype=='max' else -offset_y*2.4)
            ha_align='center';va_align='bottom' if etype=='max' else 'top'
            if text_y_pos>y_lim[1]*0.95 and etype=='max':text_y_pos=evalue_raw-offset_y*2.4;va_align='top'
            if text_y_pos<y_lim[0]+0.05*y_range_plot and etype=='min':text_y_pos=evalue_raw+offset_y;va_align='bottom'
            self.ax_embedded.annotate(text_label,xy=(efreq,evalue_raw),xytext=(efreq,text_y_pos),arrowprops=dict(arrowstyle="-",connectionstyle="arc3,rad=0.1",color='gray',lw=0.7),fontsize=6,ha=ha_align,va=va_align,bbox=dict(boxstyle="round,pad=0.2",fc="whitesmoke",ec="lightgray",alpha=0.7))
        if lines_plotted: self.ax_embedded.legend(lines_plotted, labels_plotted, loc='best', fontsize='xx-small')
        try: self.fig_embedded.tight_layout(pad=0.5)
        except Exception: 
            try: self.fig_embedded.subplots_adjust(left=0.12, bottom=0.15, right=0.88 if self.ax2_embedded and self.ax2_embedded.get_visible() else 0.95, top=0.92)
            except Exception: pass
        self.canvas_embedded.draw()

    def format_phasor(self, complex_val, unit=""):
        if abs(complex_val) == float('inf'): return f"Infinito {unit}"
        mag = abs(complex_val); phase_rad = cmath.phase(complex_val)
        if mag < 1e-12: phase_rad = 0.0
        mag_formatted = self._format_value(mag) 
        if self.angle_unit.get() == "degrees":
            phase_display = math.degrees(phase_rad); angle_symbol = "°"
        else: 
            phase_display = phase_rad; angle_symbol = " rad"
        phase_formatted = self._format_value(phase_display) 
        return f"{mag_formatted} {unit} ∠ {phase_formatted}{angle_symbol}"

if __name__ == '__main__':
    root = ctk.CTk()
    app = ACCircuitAnalyzerApp(root)
    root.mainloop()