import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import cmath
import math
import numpy as np
import json 

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
        
        # Novas variáveis para formatação de saída
        self.decimal_places_var = tk.StringVar(value="3") # Padrão 3 casas decimais
        self.scientific_notation_var = tk.BooleanVar(value=False) # Padrão não usar notação científica

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
            variable=self.circuit_topology_var, command=self._trigger_realtime_plot_update)
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

        # --- Novas Opções de Formatação de Saída ---
        output_format_label = ctk.CTkLabel(left_panel_scroll_frame, text="Formatação da Saída Textual", font=ctk.CTkFont(size=16, weight="bold"))
        output_format_label.pack(pady=(15,5), anchor="w", padx=10)
        output_format_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        output_format_frame.pack(fill="x", padx=10, pady=(0,10))
        
        ctk.CTkLabel(output_format_frame, text="Casas Decimais:").pack(side="left", padx=(10,5), pady=10)
        self.decimal_places_menu = ctk.CTkOptionMenu(output_format_frame, variable=self.decimal_places_var, 
                                                     values=["2", "3", "4", "5", "6"],
                                                     command=lambda x: self.analyze_circuit() if self.results_text.get("1.0", "end-1c") else None) # Reanalisa se já houver resultados
        self.decimal_places_menu.pack(side="left", padx=5, pady=10)
        
        self.sci_notation_checkbox = ctk.CTkCheckBox(output_format_frame, text="Notação Científica", 
                                                      variable=self.scientific_notation_var,
                                                      command=lambda: self.analyze_circuit() if self.results_text.get("1.0", "end-1c") else None) # Reanalisa
        self.sci_notation_checkbox.pack(side="left", padx=10, pady=10)
        
        # --- Opções de Unidade Angular (Movido para consistência) ---
        output_options_label = ctk.CTkLabel(left_panel_scroll_frame, text="Opções de Saída Angular", font=ctk.CTkFont(size=16, weight="bold"))
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
        self._trigger_realtime_plot_update()

    def _format_number(self, value, unit=""):
        """Formata um número de acordo com as configurações de casas decimais e notação científica."""
        if not isinstance(value, (int, float)):
            return str(value) # Retorna como string se não for número (ex: "N/A")
        if math.isinf(value):
            return f"Infinito {unit}".strip()
        if math.isnan(value):
            return f"Indefinido {unit}".strip()

        try:
            dp = int(self.decimal_places_var.get())
        except ValueError:
            dp = 3 # Padrão se a variável não for um inteiro válido

        if self.scientific_notation_var.get():
            # Formato: .<dp>e (ex: 1.234e+05)
            return f"{value:.{dp}e} {unit}".strip()
        else:
            # Formato: .<dp>f (ex: 123456.789)
            return f"{value:.{dp}f} {unit}".strip()

    def save_configuration(self):
        config_data = {
            'r_val': self.r_entry.get(), 'l_val': self.l_entry.get(), 'c_val': self.c_entry.get(),
            'v_mag': self.v_mag_entry.get(), 'v_phase_deg': self.v_phase_entry.get(),
            'freq_details': self.freq_details_entry.get(),
            'angle_unit': self.angle_unit.get(),
            'topology': self.circuit_topology_var.get(),
            'freq_start': self.freq_start_entry.get(), 'freq_end': self.freq_end_entry.get(),
            'num_points': self.num_points_entry.get(),
            'plot_choice': self.plot_variable_selected.get(),
            'decimal_places': self.decimal_places_var.get(), # Salva config de formatação
            'scientific_notation': self.scientific_notation_var.get() # Salva config de formatação
        }
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Salvar Configuração do Analisador"
            )
            if file_path:
                with open(file_path, 'w') as f: json.dump(config_data, f, indent=4)
                messagebox.showinfo("Salvar Configuração", f"Configuração salva em:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar a configuração:\n{e}")

    def load_configuration(self):
        try:
            file_path = filedialog.askopenfilename(
                defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Carregar Configuração do Analisador"
            )
            if file_path:
                with open(file_path, 'r') as f: loaded_data = json.load(f)
                
                self.r_entry.delete(0, tk.END); self.r_entry.insert(0, loaded_data.get('r_val', "10"))
                self.l_entry.delete(0, tk.END); self.l_entry.insert(0, loaded_data.get('l_val', "0.01"))
                self.c_entry.delete(0, tk.END); self.c_entry.insert(0, loaded_data.get('c_val', "0.00001"))
                self.v_mag_entry.delete(0, tk.END); self.v_mag_entry.insert(0, loaded_data.get('v_mag', "10"))
                self.v_phase_entry.delete(0, tk.END); self.v_phase_entry.insert(0, loaded_data.get('v_phase_deg', "0"))
                self.freq_details_entry.delete(0, tk.END); self.freq_details_entry.insert(0, loaded_data.get('freq_details', "159"))
                self.angle_unit.set(loaded_data.get('angle_unit', "degrees"))
                self.circuit_topology_var.set(loaded_data.get('topology', "Série"))
                self.freq_start_entry.delete(0, tk.END); self.freq_start_entry.insert(0, loaded_data.get('freq_start', "50"))
                self.freq_end_entry.delete(0, tk.END); self.freq_end_entry.insert(0, loaded_data.get('freq_end', "1000"))
                self.num_points_entry.delete(0, tk.END); self.num_points_entry.insert(0, loaded_data.get('num_points', "300"))
                self.plot_variable_selected.set(loaded_data.get('plot_choice', self.plot_variable_options[0]))
                self.decimal_places_var.set(loaded_data.get('decimal_places', "3")) # Carrega config de formatação
                self.scientific_notation_var.set(loaded_data.get('scientific_notation', False)) # Carrega config de formatação

                messagebox.showinfo("Carregar Configuração", f"Configuração carregada de:\n{file_path}")
                self._trigger_realtime_plot_update() 
                self.analyze_circuit() 
        except FileNotFoundError: messagebox.showerror("Erro ao Carregar", "Arquivo não encontrado.")
        except json.JSONDecodeError: messagebox.showerror("Erro ao Carregar", "Arquivo de configuração inválido.")
        except Exception as e: messagebox.showerror("Erro ao Carregar", f"Não foi possível carregar:\n{e}")

    def _set_entry_error_style(self, entry_key, is_error=True):
        if entry_key in self.entry_widgets:
            widget = self.entry_widgets[entry_key]
            try: 
                default_colors = ctk.ThemeManager.theme["CTkEntry"]["border_color"]
                current_mode = ctk.get_appearance_mode().lower()
                normal_c = default_colors[0] if isinstance(default_colors, list) and current_mode == "light" else (default_colors[1] if isinstance(default_colors, list) else default_colors)
            except: normal_c = "gray50"
            target_color = self.error_border_color if is_error else normal_c
            if target_color is None: target_color = "red" if is_error else ("#979797" if ctk.get_appearance_mode().lower() == "light" else "#565B5E")
            if isinstance(widget.cget("border_color"), list): widget.configure(border_color=[target_color, target_color])
            else: widget.configure(border_color=target_color)
    
    def _clear_all_entry_error_styles(self):
        for widget_key in self.entry_widgets: self._set_entry_error_style(widget_key, is_error=False)

    def _validate_all_parameters(self, silent=True, check_detail_freq=False):
        self._clear_all_entry_error_styles(); params={}; error_messages=[]; error_fields=[]
        def get_float_param(ew,pn,hn):
            try: v=float(ew.get()); params[pn]=v; return v
            except ValueError: error_messages.append(f"{hn} inválido(a)."); error_fields.append(pn); return None
        def get_int_param(ew,pn,hn):
            try: v=int(ew.get()); params[pn]=v; return v
            except ValueError: error_messages.append(f"{hn} inválido(a)."); error_fields.append(pn); return None
        params['topology']=self.circuit_topology_var.get()
        get_float_param(self.r_entry,'r_val',"Resistor (R)"); get_float_param(self.l_entry,'l_val',"Indutor (L)")
        get_float_param(self.c_entry,'c_val',"Capacitor (C)"); get_float_param(self.v_mag_entry,'v_mag',"Tensão Fonte (Vmag)")
        get_float_param(self.v_phase_entry,'v_phase_deg',"Fase Fonte (θv)")
        if 'r_val' in params:
            if params['r_val']<0: error_messages.append("R não pode ser negativo."); error_fields.append('r_val')
            if params['r_val']==0 and params['topology']=="Paralelo" and not silent: error_messages.append("Atenção: R=0 em paralelo é curto.");error_fields.append('r_val')
        if 'l_val' in params and params['l_val']<0: error_messages.append("L não pode ser negativo."); error_fields.append('l_val')
        if 'c_val' in params and params['c_val']<0: error_messages.append("C não pode ser negativo."); error_fields.append('c_val')
        if 'v_mag' in params and params['v_mag']<0: error_messages.append("Vmag não pode ser negativa."); error_fields.append('v_mag')
        get_float_param(self.freq_start_entry,'freq_start',"Frequência Inicial")
        get_float_param(self.freq_end_entry,'freq_end',"Frequência Final")
        get_int_param(self.num_points_entry,'num_points',"Número de Pontos")
        params['plot_choice']=self.plot_variable_selected.get()
        if 'freq_start' in params and params['freq_start']<=0: error_messages.append("Freq. Inicial > 0."); error_fields.append('freq_start')
        if 'freq_end' in params and 'freq_start' in params and params.get('freq_start') is not None and params['freq_end']<=params['freq_start']: error_messages.append("Freq. Final > Freq. Inicial."); error_fields.append('freq_end')
        if 'num_points' in params and params['num_points']<2: error_messages.append("Nº de Pontos >= 2."); error_fields.append('num_points')
        params['freq_details']=None
        if check_detail_freq:
            fds=self.freq_details_entry.get()
            if fds:
                dfv=get_float_param(self.freq_details_entry,'freq_details_val',"Freq. para Detalhes")
                if dfv is not None:
                    if dfv<=0:error_messages.append("Freq. para Detalhes > 0.");error_fields.append('freq_details')
                    else: params['freq_details']=dfv
        for fk in set(error_fields): self._set_entry_error_style(fk,is_error=True)
        if error_messages:
            uems=list(dict.fromkeys(error_messages))
            if not silent: messagebox.showerror("Erro de Entrada","\n".join(uems))
            return None,uems
        return params,None

    def _calculate_sweep_data(self, params):
        # ... (Lógica interna permanece a mesma, retorna 3 valores) ...
        f0_resonance=None; topology=params.get('topology',"Série"); r_val=params.get('r_val',0)
        l_val=params.get('l_val',0); c_val=params.get('c_val',0)
        if l_val>0 and c_val>0:
            try: f0_resonance=1/(2*math.pi*math.sqrt(l_val*c_val))
            except ZeroDivisionError: f0_resonance=None
        freq_start=params.get('freq_start',1); freq_end=params.get('freq_end',1000); num_points=params.get('num_points',100)
        if freq_end > freq_start and freq_start > 0 :
             if freq_end / freq_start > 50:
                try: frequencies = np.logspace(np.log10(freq_start), np.log10(freq_end), num_points)
                except ValueError: frequencies = np.linspace(freq_start, freq_end, num_points)
             else: frequencies = np.linspace(freq_start, freq_end, num_points)
        else: frequencies = np.linspace(1, 1000, 100)
        plot_data_y=[]
        v_phase_rad=math.radians(params.get('v_phase_deg',0)); v_source_phasor_fixed=cmath.rect(params.get('v_mag',0),v_phase_rad)
        for freq_current in frequencies:
            z_r=complex(r_val,0) if r_val>0 else (complex(1e-12,0) if topology=="Paralelo" and r_val==0 else complex(0,0))
            z_l=complex(0,2*cmath.pi*freq_current*l_val) if l_val>0 and freq_current>0 else (complex(0,0) if l_val==0 else complex(0,1e-12 if freq_current==0 and l_val > 0 else float('inf')))
            if l_val==0:z_l=complex(0,0)
            z_c=complex(0,-1/(2*cmath.pi*freq_current*c_val)) if c_val>0 and freq_current>0 else complex(float('inf'),0)
            if c_val==0:z_c=complex(float('inf'),0)
            z_total_sweep,i_total_sweep_source=complex(0,0),complex(0,0)
            v_r_calc,v_l_calc,v_c_calc=complex(0,0),complex(0,0),complex(0,0)
            if topology=="Série":
                z_total_sweep=z_r+z_l+z_c
                i_total_sweep_source=v_source_phasor_fixed/z_total_sweep if abs(z_total_sweep)>1e-12 else (v_source_phasor_fixed/(1e-12+0j) if abs(z_total_sweep)<1e-12 and abs(v_source_phasor_fixed)>1e-12 else complex(0,0))
                if abs(z_total_sweep)==float('inf'): i_total_sweep_source=complex(0,0)
                v_r_calc=i_total_sweep_source*z_r; v_l_calc=i_total_sweep_source*z_l
                v_c_calc=i_total_sweep_source*z_c if abs(z_c)!=float('inf') else (v_source_phasor_fixed-v_r_calc-v_l_calc if abs(i_total_sweep_source)<1e-9 else i_total_sweep_source*z_c)
            elif topology=="Paralelo":
                y_r=1/z_r if abs(z_r)>1e-12 else complex(float('inf'),0) 
                y_l=1/z_l if abs(z_l)>1e-12 else (complex(float('inf'),0) if l_val>0 and freq_current>0 else complex(0,0))
                if l_val==0 and freq_current > 0: y_l=complex(float('inf'),0) 
                elif l_val==0 and freq_current == 0: y_l=complex(float('inf'),0)
                y_c=1/z_c if abs(z_c)>1e-12 else complex(0,0)
                if c_val==0 : y_c=complex(0,0)     
                y_total_sweep=y_r+y_l+y_c
                z_total_sweep=1/y_total_sweep if abs(y_total_sweep)>1e-12 else complex(float('inf'),0)
                i_total_sweep_source=v_source_phasor_fixed*y_total_sweep
                v_r_calc=v_l_calc=v_c_calc=v_source_phasor_fixed
            val_map = {
                "|Z_total|": lambda i,vr,vl,vc,zr,zl,zc,zt,vs: abs(zt),"|I_total|": lambda i,vr,vl,vc,zr,zl,zc,zt,vs: abs(i),
                "|V_R|":     lambda i,vr,vl,vc,zr,zl,zc,zt,vs: abs(vr),"|V_L|":     lambda i,vr,vl,vc,zr,zl,zc,zt,vs: abs(vl),
                "|V_C|":     lambda i,vr,vl,vc,zr,zl,zc,zt,vs: abs(vc),
                "Fase(Z_total) (°)":lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(zt)) if abs(zt)!=float('inf') and abs(zt)>1e-12 else 0.0,
                "Fase(I_total) (°)":lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(i)) if abs(i)>1e-12 else 0.0,
                "Fase(V_R) (°)":    lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(vr)) if abs(vr)>1e-12 else 0.0,
                "Fase(V_L) (°)":    lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(vl)) if abs(vl)>1e-12 else 0.0,
                "Fase(V_C) (°)":    lambda i,vr,vl,vc,zr,zl,zc,zt,vs: math.degrees(cmath.phase(vc)) if abs(vc)>1e-12 else 0.0
            }
            current_value_to_plot=0.0
            if params.get('plot_choice') in val_map:
                current_value_to_plot=val_map[params['plot_choice']](i_total_sweep_source,v_r_calc,v_l_calc,v_c_calc,z_r,z_l,z_c,z_total_sweep,v_source_phasor_fixed)
            plot_data_y.append(current_value_to_plot)
        return frequencies, plot_data_y, f0_resonance

    def _trigger_realtime_plot_update(self, event=None, from_combobox_value=None):
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
                self._clear_embedded_plot(error_message="Erro ao atualizar gráfico.")
        else:
            self._clear_embedded_plot(error_message=f"Parâmetros inválidos:\n{', '.join(errors if errors else [])}")


    def _find_extremum(self, frequencies, data_y, plot_choice, topology):
        # ... (Lógica interna permanece a mesma) ...
        if not data_y or not isinstance(data_y,(list, np.ndarray)) or len(data_y)==0: return None
        valid_data_y=[val for val in data_y if isinstance(val,(int,float)) and not (math.isinf(val) or math.isnan(val))]
        if not valid_data_y: return None
        extremum_type,extremum_value,extremum_freq = None,None,None
        if "|" in plot_choice: 
            if topology=="Série":
                if "Z_total" in plot_choice: extremum_type="min"
                else: extremum_type="max" 
            elif topology=="Paralelo":
                if "I_total" in plot_choice: extremum_type="min" 
                elif "Z_total" in plot_choice: extremum_type="max" 
                else: extremum_type="max" 
            if extremum_type=="min": extremum_value=min(valid_data_y) if valid_data_y else None
            elif extremum_type=="max": extremum_value=max(valid_data_y) if valid_data_y else None
            else: return None 
            if extremum_value is None: return None
            try:
                original_indices=[i for i,val in enumerate(data_y) if math.isclose(val,extremum_value,rel_tol=1e-9)]
                if original_indices: extremum_index=original_indices[0]; extremum_freq=frequencies[extremum_index]
                else: return None
            except (ValueError,IndexError): return None
            # Formata o valor do extremo para a anotação no gráfico
            formatted_extremum_value = self._format_number(extremum_value)
            return extremum_type, frequencies[extremum_index], extremum_value, formatted_extremum_value
        return None
            
    def _clear_embedded_plot(self, error_message=None): 
        if self.ax_embedded:
            self.ax_embedded.clear()
            if error_message:
                self.ax_embedded.text(0.5,0.5,error_message,ha='center',va='center',fontsize=9,color='red',wrap=True)
                self.ax_embedded.set_title("Erro de Plotagem")
            else: self.ax_embedded.set_title("Aguardando Análise")
            self.ax_embedded.set_xlabel("Frequência (Hz)", fontsize=9)
            self.ax_embedded.set_ylabel("Grandeza", fontsize=9)
            self.ax_embedded.grid(True,which="both",linestyle="--",linewidth=0.5)
            self.ax_embedded.tick_params(axis='both', which='major', labelsize=8)
            self.ax_embedded.set_xscale('linear'); self.ax_embedded.set_yscale('linear')
            if self.fig_embedded: 
                try: self.fig_embedded.tight_layout(pad=0.5)
                except Exception: 
                    try: self.fig_embedded.subplots_adjust(left=0.15, bottom=0.20, right=0.90, top=0.88)
                    except: pass
            if self.canvas_embedded: self.canvas_embedded.draw()
            
    def clear_entries(self):
        self._clear_all_entry_error_styles()
        self.r_entry.delete(0,"end"); self.r_entry.insert(0,"10") 
        self.l_entry.delete(0,"end"); self.l_entry.insert(0,"0.01")
        self.c_entry.delete(0,"end"); self.c_entry.insert(0,"0.00001")
        self.v_mag_entry.delete(0,"end"); self.v_mag_entry.insert(0,"10")
        self.v_phase_entry.delete(0,"end"); self.v_phase_entry.insert(0,"0")
        self.freq_details_entry.delete(0,"end"); self.freq_details_entry.insert(0,"159") 
        self.freq_start_entry.delete(0,"end"); self.freq_start_entry.insert(0,"50")
        self.freq_end_entry.delete(0,"end"); self.freq_end_entry.insert(0,"1000")
        self.num_points_entry.delete(0,"end"); self.num_points_entry.insert(0,"300")
        self.plot_variable_combobox.set(self.plot_variable_options[0])
        self.angle_unit.set("degrees"); self.circuit_topology_var.set("Série")
        self.decimal_places_var.set("3"); self.scientific_notation_var.set(False) # Reseta formatação
        self.results_text.configure(state="normal"); self.results_text.delete("1.0","end"); self.results_text.configure(state="disabled")
        self._trigger_realtime_plot_update()

    def show_about_dialog_ctk(self): # Corrigido para usar texto plano
        if self.about_dialog_window and self.about_dialog_window.winfo_exists():
            self.about_dialog_window.lift(); self.about_dialog_window.focus_set(); return
        self.about_dialog_window = ctk.CTkToplevel(self.master)
        self.about_dialog_window.title("Sobre Analisador de Circuito CA")
        self.about_dialog_window.geometry("500x550") 
        self.about_dialog_window.transient(self.master); self.about_dialog_window.grab_set()
        
        about_scroll_frame = ctk.CTkScrollableFrame(self.about_dialog_window, corner_radius=10)
        about_scroll_frame.pack(expand=True, fill="both", padx=15, pady=15)
        
        ctk.CTkLabel(about_scroll_frame, text="Analisador de Circuito CA", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10,15))
        
        info_text = (
            "Versão: 1.9.0 (CustomTkinter)\n\n"
            "Desenvolvido como uma ferramenta educacional e de análise para circuitos RLC CA.\n\n"
            "**Funcionalidades Implementadas:**\n"
            "- Análise de circuitos RLC Série e Paralelo.\n"
            "- Varredura de frequência com plotagem gráfica.\n"
            "- Atualização do gráfico em tempo real ao modificar parâmetros.\n"
            "- Escala do gráfico (X e Y) determinada automaticamente (Log/Linear).\n"
            "- Exibição da frequência de ressonância (f0) teórica no gráfico.\n"
            "- Marcação de pontos de máximo/mínimo na curva plotada.\n"
            "- Cálculo e exibição do Fator de Qualidade (Q) e Largura de Banda (BW).\n"
            "- Análise detalhada para uma frequência específica, incluindo:\n"
            "  - Impedâncias (Z_R, Z_L, Z_C, Z_Total)\n" # Texto plano
            "  - Correntes (I_Total, I_R, I_L, I_C)\n" # Texto plano
            "  - Tensões (V_R, V_L, V_C)\n" # Texto plano
            "  - Potências (Aparente, Ativa, Reativa) totais e por componente (P_R, Q_L, Q_C).\n" # Texto plano
            "  - Fator de Potência.\n"
            "- Tratamento de casos RL e RC (L=0 ou C=0), com f0, Q, BW como N/A.\n"
            "- Validação de entradas numéricas com feedback visual (bordas vermelhas).\n"
            "- Interface gráfica com painéis para configuração e resultados.\n"
            "- Barra de ferramentas Matplotlib no gráfico (Zoom, Pan, Salvar Imagem).\n"
            "- Salvar e Carregar configurações da análise em arquivos JSON.\n"
            "- Mensagem de erro/status no gráfico se parâmetros de plotagem forem inválidos.\n"
            "- Feedback textual simplificado ('Calculando...') para varreduras.\n"
            "- Opções de formatação de saída (casas decimais, notação científica).\n\n"
            "**Próximos Passos (Ideias):**\n"
            "- Barra de progresso visual para varreduras longas.\n"
            "- Suporte a mais topologias ou entrada via netlist (conforme artigo de referência).\n\n"
            "Agradecimentos por utilizar!"
        )
        ctk.CTkLabel(about_scroll_frame, text=info_text, justify="left", wraplength=420).pack(pady=10, padx=10)
        
        close_button_frame = ctk.CTkFrame(about_scroll_frame, fg_color="transparent")
        close_button_frame.pack(pady=(15,5))
        close_button = ctk.CTkButton(close_button_frame, text="Fechar", command=self.about_dialog_window.destroy, width=100)
        close_button.pack()
        # ... (código de centralização da janela)
        self.master.update_idletasks()
        master_x=self.master.winfo_x(); master_y=self.master.winfo_y()
        master_width=self.master.winfo_width(); master_height=self.master.winfo_height()
        self.about_dialog_window.update_idletasks()
        popup_width=self.about_dialog_window.winfo_width(); popup_height=self.about_dialog_window.winfo_height()
        if popup_width<=1 or popup_height<=1: 
            try:
                geom_parts=self.about_dialog_window.geometry().split('+')[0].split('x')
                popup_width,popup_height=int(geom_parts[0]),int(geom_parts[1])
            except: popup_width,popup_height=500,550
        center_x=master_x+(master_width-popup_width)//2; center_y=master_y+(master_height-popup_height)//2
        self.about_dialog_window.geometry(f"{popup_width}x{popup_height}+{center_x}+{center_y}")


    def analyze_circuit(self): 
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end") 
        self._clear_all_entry_error_styles()

        params, errors = self._validate_all_parameters(silent=False, check_detail_freq=True)
        
        if not params:
            self.results_text.insert("1.0", "Erro de entrada:\n" + "\n".join(errors if errors else ["Valores inválidos."]))
            self._clear_embedded_plot(error_message="Parâmetros de análise inválidos.")
            self.results_text.configure(state="disabled")
            return

        self.results_text.insert("1.0", "Calculando varredura e análise, por favor aguarde...\n\n")
        self.master.update_idletasks()

        output_text = ""
        try:
            frequencies, plot_data_y, f0_calc = self._calculate_sweep_data(params)
            extremum_info_tuple = self._find_extremum(frequencies, plot_data_y, params['plot_choice'], params['topology'])
            self._update_embedded_plot(frequencies, plot_data_y, params['plot_choice'], f0_resonance=f0_calc, extremum_info_tuple=extremum_info_tuple)
            
            self.results_text.delete("1.0", "end")
            output_text += f"--- Resumo da Varredura ({params['topology']}) ---\n"
            output_text += f"Intervalo: {self._format_number(params['freq_start'])} Hz a {self._format_number(params['freq_end'])} Hz ({params['num_points']} pontos).\n"
            output_text += f"Grandeza Plotada: {params['plot_choice']}\n"
            q_factor_str, bandwidth_str, f0_calc_str = "N/A", "N/A", "N/A"

            if f0_calc is not None:
                f0_calc_str = self._format_number(f0_calc, "Hz")
                omega_0 = 2 * math.pi * f0_calc
                r_val = params.get('r_val', 0); l_val = params.get('l_val', 0); c_val = params.get('c_val', 0)
                q_factor_val = None
                # Revisão da lógica de Q para RL/RC
                if params['topology'] == "Série":
                    if r_val > 1e-12 : 
                        if l_val > 1e-12 and c_val > 1e-12: # RLC
                            q_factor_val = (omega_0 * l_val) / r_val
                        elif l_val > 1e-12 and c_val < 1e-12: # RL
                             q_factor_val = (omega_0 * l_val) / r_val # Q de uma bobina em série com R
                        elif c_val > 1e-12 and l_val < 1e-12 and omega_0 > 1e-9: # RC
                             q_factor_val = 1 / (omega_0 * c_val * r_val) # Q de um capacitor em série com R
                    elif l_val > 1e-12 and c_val > 1e-12: q_factor_val = float('inf') # LC Série ideal
                elif params['topology'] == "Paralelo":
                    if r_val > 1e-12: 
                        if l_val > 1e-12 and c_val > 1e-12 and omega_0 > 1e-9: # RLC
                            q_factor_val = r_val / (omega_0 * l_val)
                        elif l_val > 1e-12 and c_val < 1e-12 and omega_0 > 1e-9: # RL
                            q_factor_val = r_val / (omega_0 * l_val) # Q de uma bobina em paralelo com R
                        elif c_val > 1e-12 and l_val < 1e-12 and omega_0 > 1e-9: # RC
                            q_factor_val = omega_0 * c_val * r_val # Q de um capacitor em paralelo com R
                    elif (l_val > 1e-9 or c_val > 1e-9): q_factor_val = 0 # Curto R=0
                
                if q_factor_val is not None:
                    if q_factor_val == float('inf'): q_factor_str, bandwidth_str = "Infinito", self._format_number(0.0, "Hz")
                    elif q_factor_val > 1e-9:
                        q_factor_str = self._format_number(q_factor_val); bandwidth_str = self._format_number(f0_calc / q_factor_val, "Hz")
                    else: q_factor_str, bandwidth_str = self._format_number(q_factor_val) + " (Baixo)", "Muito Larga"
            
            output_text += f"Frequência de Ressonância (f0): {f0_calc_str}\n" # Movido para sempre aparecer
            output_text += f"    Fator de Qualidade (Q): {q_factor_str}\n"
            output_text += f"    Largura de Banda (BW): {bandwidth_str}\n"
            
            if extremum_info_tuple:
                 # extremum_info_tuple é (etype, efreq, evalue_raw, evalue_formatted)
                 output_text += f"Ponto Extremo ({extremum_info_tuple[0]}): {extremum_info_tuple[3]} em {self._format_number(extremum_info_tuple[1], 'Hz')}\n"

            output_text += "-------------------------------------------\n\n"
            if params.get('freq_details') is not None:
                output_text += self._get_single_frequency_analysis_details(params, params['freq_details'])
            else:
                output_text += "Nenhuma frequência para análise detalhada foi fornecida ou era inválida.\n"
            self.results_text.insert("1.0", output_text)
        except Exception as e:
            self.results_text.delete("1.0", "end")
            error_msg = f"Erro inesperado durante a análise: {str(e)}"
            messagebox.showerror("Erro Inesperado", error_msg)
            self.results_text.insert("1.0", error_msg)
            self._clear_embedded_plot(error_message="Erro na análise.")
            import traceback; traceback.print_exc()
        self.results_text.configure(state="disabled")

    def _get_single_frequency_analysis_details(self, circuit_params, specific_freq):
        output = ""
        try:
            r_val = circuit_params.get('r_val',0); l_val = circuit_params.get('l_val',0); c_val = circuit_params.get('c_val',0)
            v_mag = circuit_params.get('v_mag',0); v_phase_deg = circuit_params.get('v_phase_deg',0)
            topology = circuit_params.get('topology',"Série"); freq = specific_freq
            v_phase_rad = math.radians(v_phase_deg); v_source_phasor = cmath.rect(v_mag, v_phase_rad)
            z_r_val, z_l_val, z_c_val, xl_val, xc_val = complex(0,0), complex(0,0), complex(0,0), 0.0, 0.0
            if r_val > 1e-12 : z_r_val = complex(r_val,0) # R > 0
            elif r_val < 1e-12 and topology=="Paralelo": z_r_val = complex(1e-12,0) # R=0 em paralelo é curto ideal, Z_R muito baixo
            else: z_r_val = complex(0,0) # R=0 em série
            if l_val > 1e-12 and freq > 1e-12: xl_val=2*cmath.pi*freq*l_val; z_l_val=complex(0,xl_val)
            elif l_val < 1e-12 : z_l_val=complex(0,0) # L=0 é curto
            else: z_l_val=complex(0,1e-12) # L > 0, freq = 0 (DC) -> Z_L muito baixo (curto)
            if c_val > 1e-12 and freq > 1e-12: xc_val=-1/(2*cmath.pi*freq*c_val); z_c_val=complex(0,xc_val)
            elif c_val < 1e-12 : z_c_val=complex(float('inf'),0) # C=0 é aberto
            else: z_c_val=complex(float('inf'),0) # C > 0, freq = 0 (DC) -> Z_C infinito (aberto)

            z_total,i_total_source_phasor = complex(0,0),complex(0,0)
            v_r_phasor,v_l_phasor,v_c_phasor = complex(0,0),complex(0,0),complex(0,0)
            i_r_phasor,i_l_phasor,i_c_phasor = complex(0,0),complex(0,0),complex(0,0)
            p_r_comp,q_l_comp,q_c_comp = 0.0,0.0,0.0
            if topology == "Série":
                # ... (lógica série como antes, mas robustecida para componentes zero) ...
                z_total=z_r_val+z_l_val+z_c_val
                if abs(z_total)<1e-12 and abs(v_source_phasor)>1e-12 : i_total_source_phasor=v_source_phasor/(1e-12+0j) 
                elif abs(z_total)==float('inf'): i_total_source_phasor=complex(0,0)
                elif abs(z_total)>1e-12: i_total_source_phasor=v_source_phasor/z_total
                else: i_total_source_phasor = complex(0,0) # Ex: V_source = 0

                v_r_phasor=i_total_source_phasor*z_r_val
                v_l_phasor=i_total_source_phasor*z_l_val
                if abs(z_c_val) == float('inf'): # C é aberto
                    v_c_phasor = v_source_phasor - v_r_phasor - v_l_phasor if (l_val > 1e-12 or r_val > 1e-12) else v_source_phasor
                    if c_val < 1e-12 and l_val < 1e-12 and r_val < 1e-12 : v_c_phasor = v_source_phasor # Curto total
                else: v_c_phasor=i_total_source_phasor*z_c_val
                
                i_r_phasor=i_l_phasor=i_c_phasor=i_total_source_phasor
                p_r_comp=(abs(i_r_phasor)**2)*r_val if r_val > 1e-12 else 0.0
                if l_val > 1e-12 and freq > 1e-12 and abs(xl_val)>1e-12: q_l_comp=(abs(i_l_phasor)**2)*xl_val
                else: q_l_comp = 0.0
                if c_val > 1e-12 and freq > 1e-12 and abs(xc_val)>1e-12: q_c_comp=(abs(i_c_phasor)**2)*xc_val 
                else: q_c_comp = 0.0

            elif topology == "Paralelo":
                # ... (lógica paralelo como antes, mas robustecida para componentes zero) ...
                y_r=1/z_r_val if abs(z_r_val)>1e-12 else complex(float('inf'),0) 
                y_l=1/z_l_val if abs(z_l_val)>1e-12 else (complex(float('inf'),0) if l_val > 1e-12 and freq > 1e-12 else complex(0,0) )
                if l_val < 1e-12 and freq > 1e-12 : y_l=complex(float('inf'),0) # L=0 é curto
                elif l_val < 1e-12 and freq < 1e-12 : y_l=complex(float('inf'),0) # L=0 em DC é curto

                y_c=1/z_c_val if abs(z_c_val)>1e-12 else complex(0,0)
                if c_val < 1e-12 : y_c=complex(0,0) # C=0 é aberto, Yc=0
                
                y_total=y_r+y_l+y_c
                z_total=1/y_total if abs(y_total)>1e-12 else complex(float('inf'),0)
                i_total_source_phasor=v_source_phasor*y_total 
                v_r_phasor=v_l_phasor=v_c_phasor=v_source_phasor

                i_r_phasor=v_source_phasor*y_r if r_val > 1e-12 else (v_source_phasor/complex(1e-12,0) if r_val < 1e-12 and abs(v_source_phasor)>1e-9 else complex(0,0))
                i_l_phasor=v_source_phasor*y_l if l_val > 1e-12 and freq > 1e-12 and abs(z_l_val)>1e-12 else (v_source_phasor/complex(1e-12,0) if l_val < 1e-12 and freq > 1e-12 and abs(v_source_phasor)>1e-9 else complex(0,0))
                i_c_phasor=v_source_phasor*y_c if c_val > 1e-12 and freq > 1e-12 and abs(z_c_val)>1e-12 else complex(0,0)

                if r_val > 1e-12: p_r_comp=(abs(v_source_phasor)**2)/r_val
                elif r_val < 1e-12 and abs(i_r_phasor) != float('inf') : p_r_comp = abs(v_source_phasor * i_r_phasor.conjugate()).real 
                else: p_r_comp = float('inf') if abs(v_source_phasor) > 1e-9 else 0.0 # Potência infinita em curto ideal com V != 0
                
                if l_val > 1e-12 and freq > 1e-12 and abs(xl_val) > 1e-12 : q_l_comp=(abs(v_source_phasor)**2)/xl_val
                elif l_val < 1e-12 and freq > 1e-12 and abs(i_l_phasor) != float('inf'): q_l_comp = (v_source_phasor * i_l_phasor.conjugate()).imag 
                else: q_l_comp = float('inf') if l_val < 1e-12 and abs(v_source_phasor) > 1e-9 else 0.0
                
                if c_val > 1e-12 and freq > 1e-12 and abs(xc_val) > 1e-12 : q_c_comp=(abs(v_source_phasor)**2)/xc_val
                else: q_c_comp = 0.0
            
            output += f"--- Detalhes para Frequência: {self._format_number(freq, 'Hz')} ({topology}) ---\n"
            # ... (formatação da saída como antes, usando self._format_number e self.format_phasor)
            if abs(z_total)==float('inf') and topology=="Série" and c_val < 1e-12 and l_val < 1e-12 and r_val < 1e-12 : # Circuito completamente aberto
                 output += f"  Impedância Total (Z_total): Infinita (Circuito Aberto Total)\n"
                 output += f"  Corrente Total (I_total Fonte): {self.format_phasor(complex(0,0), 'A')}\n"
                 output += f"  Tensão no Resistor (V_R): {self.format_phasor(complex(0,0), 'V')}\n"
                 output += f"  Tensão no Indutor (V_L): {self.format_phasor(complex(0,0), 'V')}\n"
                 output += f"  Tensão no Capacitor (V_C): {self.format_phasor(v_source_phasor, 'V')} (Tensão da fonte, pois circuito aberto)\n" # Ou V_C = V_S se só tiver C
            elif abs(z_total)==float('inf') and topology=="Série":
                 output += f"  Impedância Total (Z_total): Infinita (Circuito Aberto)\n"
                 output += f"  Corrente Total (I_total Fonte): {self.format_phasor(i_total_source_phasor, 'A')}\n"
            else:
                output += f"  Impedância Total (Z_total): {self.format_phasor(z_total, 'Ω')}\n"
                output += f"  Corrente Total (I_total Fonte): {self.format_phasor(i_total_source_phasor, 'A')}\n"

            output += "  ---------------------------\n"
            if topology=="Série":
                output += f"  Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                output += f"  Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                output += f"  Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
            elif topology=="Paralelo":
                output += f"  Tensão (V_R=V_L=V_C): {self.format_phasor(v_source_phasor, 'V')}\n"
                output += f"  Corrente em R (I_R): {self.format_phasor(i_r_phasor, 'A')}\n"
                output += f"  Corrente em L (I_L): {self.format_phasor(i_l_phasor, 'A')}\n"
                output += f"  Corrente em C (I_C): {self.format_phasor(i_c_phasor, 'A')}\n"

            output += "  ---------------------------\n  Análise de Potência (Total da Fonte):\n"
            s_complex=v_source_phasor*i_total_source_phasor.conjugate()
            p_real,q_reactive,s_apparent_mag=s_complex.real,s_complex.imag,abs(s_complex)
            power_factor=p_real/s_apparent_mag if s_apparent_mag>1e-9 else (1.0 if abs(p_real)>1e-9 else 0.0) # FP=1 se puramente resistivo
            fp_type,epsilon="(N/A)",1e-9
            if abs(s_apparent_mag)<epsilon: fp_type="(N/A - sem potência significante)"
            elif abs(q_reactive)<epsilon: fp_type="(unitário)"
            elif q_reactive > 0: fp_type="(atrasado - indutivo)"
            else: fp_type="(adiantado - capacitivo)"
            output += f"    Potência Aparente (|S|): {self._format_number(s_apparent_mag, 'VA')}\n    Potência Ativa (P): {self._format_number(p_real, 'W')}\n"
            output += f"    Potência Reativa (Q): {self._format_number(q_reactive, 'VAR')}\n    Fator de Potência (FP): {self._format_number(power_factor)} {fp_type}\n"
            
            output += "  ---------------------------\n  Potências nos Componentes:\n"
            output += f"    Potência Ativa no Resistor (P_R): {self._format_number(p_r_comp, 'W')}\n"
            output += f"    Potência Reativa no Indutor (Q_L): {self._format_number(q_l_comp, 'VAR')}\n"
            output += f"    Potência Reativa no Capacitor (Q_C): {self._format_number(q_c_comp, 'VAR')}\n"
            
            # Verificações de consistência
            if not (math.isinf(p_r_comp) or math.isinf(p_real)):
                 if abs(p_real)>1e-6 or abs(p_r_comp)>1e-6 :
                    output += f"    (Verificação P_R ≈ P_total: {'Sim' if math.isclose(p_r_comp, p_real, rel_tol=1e-2, abs_tol=1e-3) else 'Não'})\n"
            
            q_sum_comp = q_l_comp + q_c_comp
            if not (math.isinf(q_sum_comp) or math.isinf(q_reactive)):
                if abs(q_reactive)>1e-6 or abs(q_sum_comp)>1e-6:
                    abs_tol_q_sum = max(1e-3, abs(q_l_comp)*1e-2, abs(q_c_comp)*1e-2) 
                    output += f"    (Verificação Q_L+Q_C ≈ Q_total: {'Sim' if math.isclose(q_sum_comp, q_reactive, rel_tol=1e-2, abs_tol=abs_tol_q_sum) else 'Não'})\n"
            return output
        except Exception as e:
            import traceback; traceback.print_exc()
            return f"  Erro ao calcular detalhes para {self._format_number(specific_freq, 'Hz')} ({topology}): {e}\n"

    def format_phasor(self, complex_val, unit=""): # Agora usa _format_number internamente
        if abs(complex_val) == float('inf'): return f"Infinito {unit}"
        mag = abs(complex_val); phase_rad = cmath.phase(complex_val)
        if mag < 1e-12: phase_rad = 0.0 # Evita fases estranhas para magnitudes muito pequenas
        
        mag_formatted = self._format_number(mag) # Formata magnitude
        
        if self.angle_unit.get() == "degrees":
            phase_display = math.degrees(phase_rad); angle_symbol = "°"
        else: 
            phase_display = phase_rad; angle_symbol = " rad"
        phase_formatted = self._format_number(phase_display) # Formata fase
        
        return f"{mag_formatted} {unit} ∠ {phase_formatted}{angle_symbol}"


    def _update_embedded_plot(self, frequencies, plot_data_y, y_label_choice, f0_resonance=None, extremum_info_tuple=None):
        # ... (Lógica de plotagem como antes, mas usa _format_number para anotações)
        if not (self.fig_embedded and self.ax_embedded and self.canvas_embedded): return 
        self.ax_embedded.clear(); legend_handles, legend_labels = [], []
        
        if len(frequencies) > 1 and frequencies[0] > 0 and frequencies[-1]/frequencies[0] > 50: # freq[0] > 0 for log
             self.ax_embedded.set_xscale('log')
        else:
             self.ax_embedded.set_xscale('linear')
        
        is_magnitude_plot = "|" in y_label_choice
        if is_magnitude_plot and len(plot_data_y) > 1:
            positive_values = [d for d in plot_data_y if isinstance(d,(int,float)) and d > 1e-9 and not math.isinf(d) and not math.isnan(d)]
            if positive_values:
                min_val=min(positive_values); max_val=max(d for d in plot_data_y if isinstance(d,(int,float)) and not math.isinf(d) and not math.isnan(d))
                if min_val > 0 and max_val/min_val > 1000: self.ax_embedded.set_yscale('log')
                else: self.ax_embedded.set_yscale('linear')
            else: self.ax_embedded.set_yscale('linear')
        elif "Fase" in y_label_choice: self.ax_embedded.set_yscale('linear')
        else: self.ax_embedded.set_yscale('linear')

        self.ax_embedded.plot(frequencies, plot_data_y, marker='.', linestyle='-', markersize=3)
        self.ax_embedded.set_title(f"{y_label_choice} vs Frequência ({self.circuit_topology_var.get()})", fontsize=10)
        self.ax_embedded.set_xlabel("Frequência (Hz)", fontsize=9); self.ax_embedded.set_ylabel(y_label_choice, fontsize=9)
        self.ax_embedded.grid(True, which="both", linestyle="--", linewidth=0.5)
        self.ax_embedded.tick_params(axis='both', which='major', labelsize=8)

        if f0_resonance is not None and len(frequencies)>0 and frequencies[0]<=f0_resonance<=frequencies[-1]:
            line_f0 = self.ax_embedded.axvline(x=f0_resonance, color='red', linestyle='--', linewidth=1.2)
            legend_handles.append(line_f0); legend_labels.append(f'f0 ≈ {self._format_number(f0_resonance, "Hz")}')
        
        if extremum_info_tuple:
            etype, efreq, evalue_raw, evalue_formatted = extremum_info_tuple # Unpack
            # evalue_formatted já está formatado por _format_number chamado em _find_extremum
            text_label=f"{etype.capitalize()}: {evalue_formatted}\n@ {self._format_number(efreq, 'Hz')}"
            
            marker_color='green' if etype=='max' else 'purple'
            self.ax_embedded.plot(efreq, evalue_raw, marker='o', color=marker_color, markersize=6, fillstyle='none', markeredgewidth=1.2)
            
            # Lógica de posicionamento da anotação (pode ser complexa para evitar sobreposições)
            y_min_plot, y_max_plot = self.ax_embedded.get_ylim()
            y_range_plot = y_max_plot - y_min_plot if y_max_plot > y_min_plot else 1.0
            if y_range_plot == 0 : y_range_plot = abs(evalue_raw) if evalue_raw != 0 else 1.0
            
            offset_y_factor = 0.05 if etype == 'max' else -0.15 # Ajuste para mais espaço abaixo se for min
            offset_y = y_range_plot * offset_y_factor
            if abs(offset_y) < 1e-6 and evalue_raw != 0 : offset_y = evalue_raw * offset_y_factor * 5 
            elif abs(offset_y) < 1e-6 and evalue_raw == 0: offset_y = (y_max_plot - y_min_plot) * 0.05 if y_max_plot > y_min_plot else 0.1

            x_min_plot, x_max_plot = self.ax_embedded.get_xlim()
            offset_x_factor = 0.03*(x_max_plot-x_min_plot) if self.ax_embedded.get_xscale()=='linear' else efreq*0.2 
            ha_align='left'; va_align = 'bottom' if etype == 'max' else 'top'
            efreq_text = efreq + offset_x_factor

            if f0_resonance and abs(efreq-f0_resonance)<offset_x_factor*1.5 : # Se perto de f0
                efreq_text=efreq-offset_x_factor*1.5; ha_align='right'
            
            if efreq_text > x_max_plot*0.90 : ha_align='right'; efreq_text=efreq-offset_x_factor # Perto da borda direita
            if efreq_text < x_min_plot*1.10 and self.ax_embedded.get_xscale()=='linear' : ha_align='left'; efreq_text=efreq+offset_x_factor # Perto da borda esquerda
            
            # Verifica se a anotação vai sair do topo/fundo
            text_y_pos = evalue_raw + offset_y
            if text_y_pos > y_max_plot * 0.95 and etype == 'max': va_align = 'top'; offset_y *= -1.2 # Inverte se perto do topo
            if text_y_pos < y_min_plot * 1.05 and y_min_plot < 0 and etype == 'min': va_align = 'bottom'; offset_y *= -1.2 # Inverte se perto do fundo (e fundo < 0)
            elif text_y_pos < y_min_plot + 0.05 * y_range_plot and etype == 'min': va_align = 'bottom'; offset_y *= -1.2


            self.ax_embedded.annotate(text_label, xy=(efreq, evalue_raw), xytext=(efreq_text, evalue_raw + offset_y),
                                      arrowprops=dict(arrowstyle="-|>",connectionstyle="arc3,rad=.15", fc="black", ec="black", lw=0.7),
                                      fontsize=7, ha=ha_align, va=va_align,
                                      bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.6))
        if legend_handles: self.ax_embedded.legend(handles=legend_handles, labels=legend_labels, fontsize='x-small', loc='best')
        
        try: self.fig_embedded.tight_layout(pad=0.5)
        except Exception: 
            try: self.fig_embedded.subplots_adjust(left=0.15, bottom=0.20, right=0.90, top=0.88)
            except Exception: pass
        self.canvas_embedded.draw()

if __name__ == '__main__':
    root = ctk.CTk()
    app = ACCircuitAnalyzerApp(root)
    root.mainloop()