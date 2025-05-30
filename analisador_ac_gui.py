import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import cmath
import math
import numpy as np
import json
import re
import copy # Added for deepcopying diagram data

import warnings
# To ignore the specific constrained_layout warning that occurs when drawing empty plots
warnings.filterwarnings("ignore", category=UserWarning, message="constrained_layout not applied because axes sizes collapsed to zero.*")

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class ACCircuitAnalyzerApp:
    def __init__(self, master_window):
        self.master = master_window
        master_window.title("Analisador de Circuito CA (CustomTkinter) - Análise Nodal")
        master_window.geometry("1100x850") # Increased height a bit

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.angle_unit = tk.StringVar(value="degrees")
        self.circuit_topology_var = tk.StringVar(value="Série") # Kept for potential future use or alternative analysis mode
        self.decimal_places_var = tk.StringVar(value="3")
        self.scientific_notation_var = tk.BooleanVar(value=False)

        # These are less relevant if primary analysis is nodal from netlist
        self.include_r_var = tk.BooleanVar(value=True)
        self.include_l_var = tk.BooleanVar(value=True)
        self.include_c_var = tk.BooleanVar(value=True)

        self.about_dialog_window = None

        self.fig_main_plot = None
        self.ax_main_plot = None
        self.ax_main_plot_twin = None
        self.canvas_main_plot = None
        self.toolbar_main_plot = None

        self.fig_waveforms = None
        self.ax_waveforms = None
        self.canvas_waveforms_figure_agg = None # To store the FigureCanvasTkAgg instance
        self.ax_waveforms_current_twin = None # For secondary Y-axis for currents
        self.canvas_waveforms_widget = None # O widget Tk do canvas
        self.toolbar_waveforms = None
        # --- Waveform Selection ---
        self.scrollable_waveform_controls_area = None # Frame to hold selection UI, now scrollable
        self.waveform_selection_vars = {
            "nodal_voltages": {},   # Key: node_name (str), Value: tk.BooleanVar
            "component_currents": {}, # Key: comp_name (str), Value: tk.BooleanVar
            "component_voltages": {},  # Key: comp_name (str), Value: tk.BooleanVar
            "three_phase_source_phase_voltages": {}, # Key: (parent_name, phase_char 'A'/'B'/'C'), Value: tk.BooleanVar
            "three_phase_source_line_currents": {},  # Key: (parent_name, phase_char 'A'/'B'/'C'), Value: tk.BooleanVar
            "three_phase_source_line_voltages": {}   # Key: (parent_name, pair_char 'AB'/'BC'/'CA'), Value: tk.BooleanVar
        }
        self.waveform_selection_scroll_frames = {} # To keep references to scrollable frames
        self.num_periods_to_plot_var = tk.StringVar(value="3") # Padrão de 3 períodos
        self.show_waveform_grid_var = tk.BooleanVar(value=True) # Grade visível por padrão

        # --- Waveform Plotting Aesthetics ---
        self.waveform_plot_colors = ['tab:blue', 'tab:red', 'tab:green', 'tab:orange',
                                     'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray',
                                     'tab:olive', 'tab:cyan']
        self.waveform_plot_linestyles = ['-', '--', '-.', ':']

        self.circuit_diagram_canvas = None
        self.circuit_diagram_frame = None

        self.plot_container_frame = None

        self.error_border_color = "red"
        try:
            default_entry_color = ctk.ThemeManager.theme["CTkEntry"]["border_color"]
            current_mode = ctk.get_appearance_mode().lower()
            self.normal_border_color = default_entry_color[0] if isinstance(default_entry_color, list) and current_mode == "light" else (default_entry_color[1] if isinstance(default_entry_color, list) else default_entry_color)
        except KeyError:
            self.normal_border_color = "gray50"
        self.entry_widgets = {}

        self.analysis_results = {}
        self.analysis_performed_successfully = False
        self.parsed_components_for_plotting = [] # Store parsed components for plotter

        # --- Current analysis values for PF correction ---
        self.current_p_real = None
        self.current_q_reactive = None
        self.current_s_apparent = None
        self.current_fp_actual = None
        self.current_v_load_mag = None
        self.current_freq = None
        # ---
        # --- Editor State Variables ---
        self.selected_component_tool = None
        self.circuit_elements_on_canvas = []
        self.next_element_id = 0
        self.currently_selected_element_id = None
        self.selection_outline_color = "blue" # Or use a CTk theme color
        self.default_outline_color = "black" # Default outline for symbols
        # --- Drag State Variables ---
        self.is_dragging = False
        self.drag_start_mouse_x = 0
        self.drag_start_mouse_y = 0
        # ---
        # --- Terminal Visual Properties ---
        self.terminal_radius = 3
        self.terminal_fill_color = "black"
        self.terminal_outline_color = "black" # Or self.default_outline_color
        # --- Wire Drawing State ---
        self.is_drawing_wire = False
        self.wire_start_info = None # Will store {'element_id': str, 'terminal_name': str, 'abs_x': float, 'abs_y': float}
        self.wire_preview_line_id = None
        self.wires_on_canvas = [] # Stores successfully drawn wires
        self.next_wire_id = 0
        self.currently_selected_wire_id = None
        self.wire_selection_color = "red" 
        self.wire_default_color = "black"

        self.wire_hit_radius = 10 # Pixel radius for detecting a click on a terminal
        # --- Grid and Snap Settings ---
        self.grid_spacing = 20  # Espaçamento da grade em pixels
        self.grid_color = "lightgrey" # Cor das linhas da grade
        self.snap_to_grid_enabled = tk.BooleanVar(value=True) # Flag para habilitar/desabilitar o snap
        # --- Zoom Settings ---
        self.current_zoom_level = 1.0
        self.zoom_factor_increment = 1.1 # Fator para zoom in (ex: 10% de aumento)
        self.zoom_factor_decrement = 1 / 1.1 # Fator para zoom out (ex: 10% de redução)
        # --- Pan Settings ---
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        # self.grid_line_ids = [] # Using tags is generally better for managing grid lines
        
        # --- Three-Phase Source Details ---
        self.three_phase_source_details_map = {} # Stores original node names for VSY/VSD

        main_app_frame = ctk.CTkFrame(master_window, fg_color="transparent")
        main_app_frame.pack(expand=True, fill="both", padx=5, pady=5)

        title_label = ctk.CTkLabel(main_app_frame, text="Analisador de Circuito CA (Análise Nodal via Netlist)",
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

        netlist_main_label = ctk.CTkLabel(left_panel_scroll_frame, text="Entrada via Netlist (Nodal)", font=ctk.CTkFont(size=16, weight="bold"))
        netlist_main_label.pack(pady=(15,5), anchor="w", padx=10)
        netlist_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        netlist_frame.pack(pady=(0,10), padx=10, fill="x")
        self.netlist_textbox = ctk.CTkTextbox(netlist_frame, height=200, wrap="word", font=ctk.CTkFont(family="monospace", size=11)) # Increased height
        self.netlist_textbox.pack(expand=True, fill="x", padx=5, pady=5)
        self.netlist_textbox.insert("1.0",
            "# Exemplo Netlist para Análise Nodal:\n"
            "# VS1 1 0 AC 10 0  # Fonte: Nome, Nó+, Nó-, Tipo, Vmag, Vfase_graus\n"
            "# IS1 2 0 AC 2 30  # Fonte Corrente: Nome, Nó_Saída(->), Nó_Entrada(<-), Tipo, Imag, Ifase_graus\n"
            "# R1 1 2 100       # Resistor: Nome, Nó1, Nó2, Valor_Ohms\n"
            "# L1 2 0 0.05      # Indutor: Nome, Nó1, Nó2, Valor_Henries\n"
            "# C1 1 2 1e-4      # Capacitor: Nome, Nó1, Nó2, Valor_Farads\n"
            "# FREQ 60          # Frequência de análise em Hz\n"
            "# --- Fontes Controladas ---\n"
            "# E1 3 0 1 2 2.0      # VCVS: E<nome> <nó+> <nó-> <nó_ctrl+> <nó_ctrl-> <ganho_V>\n"
            "# G1 4 0 1 2 0.1      # VCCS: G<nome> <nó_saída> <nó_entrada> <nó_ctrl+> <nó_ctrl-> <transcond_Gm>\n"
            "# VS_monitor 5 0 AC 1 0 # Fonte VS para monitorar corrente para H e F\n"
            "# H1 6 0 VS_monitor 50  # CCVS: H<nome> <nó+> <nó-> <nome_VS_monitor> <ganho_Rm>\n"
            "# F1 7 0 VS_monitor 100 # CCCS: F<nome> <nó_saída> <nó_entrada> <nome_VS_monitor> <ganho_beta>\n"
            "\nVS1 1 0 AC 220 0\n"
            "R1 1 2 10\n"
            "IS1 2 0 AC 1 0 # Exemplo de fonte de corrente\n"
            "L1 2 0 0.02122\n" # Approx 8 Ohms at 60Hz
            "FREQ 60\n"
        )
        process_netlist_button = ctk.CTkButton(netlist_frame, text="Processar Netlist e Analisar", command=self._process_netlist_button_command)
        process_netlist_button.pack(pady=5, padx=5)

        # --- Manual Input Section (Kept for now, but less central for nodal) ---
        topology_main_label = ctk.CTkLabel(left_panel_scroll_frame, text="Config. Manual (RLC Equivalente - Opcional)",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        topology_main_label.pack(pady=(10,5), anchor="w", padx=10)
        topology_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        topology_frame.pack(pady=(0,10), padx=10, fill="x")
        ctk.CTkLabel(topology_frame, text="Topologia (Manual):").pack(side="left", padx=(10,10), pady=10)
        self.topology_selector = ctk.CTkSegmentedButton(
            topology_frame, values=["Série", "Paralelo"],
            variable=self.circuit_topology_var, command=self._on_parameter_change)
        self.topology_selector.pack(side="left", expand=True, fill="x", padx=10, pady=10)

        input_section_label = ctk.CTkLabel(left_panel_scroll_frame, text="Parâmetros (Manual - Opcional)",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        input_section_label.pack(pady=(10,5), anchor="w", padx=10)
        input_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        input_frame.pack(fill="x", padx=10, pady=(0,10))
        input_frame.grid_columnconfigure(2, weight=1)
        entry_width = 130

        self.r_check = ctk.CTkCheckBox(input_frame, text="R_eq [Ω]:", variable=self.include_r_var, command=self._on_include_component_change)
        self.r_check.grid(row=0, column=0, columnspan=2, padx=(10,0), pady=8, sticky="w")
        self.r_entry = ctk.CTkEntry(input_frame, width=entry_width); self.r_entry.insert(0, "10")
        self.r_entry.grid(row=0, column=2, padx=(0,10), pady=8, sticky="ew")
        self.r_entry.bind("<FocusOut>", self._on_parameter_change); self.r_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['r_val'] = self.r_entry

        self.l_check = ctk.CTkCheckBox(input_frame, text="L_eq [H]:", variable=self.include_l_var, command=self._on_include_component_change)
        self.l_check.grid(row=1, column=0, columnspan=2, padx=(10,0), pady=8, sticky="w")
        self.l_entry = ctk.CTkEntry(input_frame, width=entry_width); self.l_entry.insert(0, "0.02122")
        self.l_entry.grid(row=1, column=2, padx=(0,10), pady=8, sticky="ew")
        self.l_entry.bind("<FocusOut>", self._on_parameter_change); self.l_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['l_val'] = self.l_entry

        self.c_check = ctk.CTkCheckBox(input_frame, text="C_eq [F]:", variable=self.include_c_var, command=self._on_include_component_change)
        self.c_check.grid(row=2, column=0, columnspan=2, padx=(10,0), pady=8, sticky="w")
        self.c_entry = ctk.CTkEntry(input_frame, width=entry_width); self.c_entry.insert(0, "0")
        self.c_entry.grid(row=2, column=2, padx=(0,10), pady=8, sticky="ew")
        self.c_entry.bind("<FocusOut>", self._on_parameter_change); self.c_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['c_val'] = self.c_entry
        self.include_c_var.set(False)

        ctk.CTkLabel(input_frame, text="Tensão Fonte (Vmag) [V]:").grid(row=3, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        self.v_mag_entry = ctk.CTkEntry(input_frame, width=entry_width); self.v_mag_entry.insert(0, "220")
        self.v_mag_entry.grid(row=3, column=2, padx=(0,10), pady=8, sticky="ew")
        self.v_mag_entry.bind("<FocusOut>", self._on_parameter_change); self.v_mag_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['v_mag'] = self.v_mag_entry

        ctk.CTkLabel(input_frame, text="Fase Fonte (θv) [°]:").grid(row=4, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        self.v_phase_entry = ctk.CTkEntry(input_frame, width=entry_width); self.v_phase_entry.insert(0, "0")
        self.v_phase_entry.grid(row=4, column=2, padx=(0,10), pady=8, sticky="ew")
        self.v_phase_entry.bind("<FocusOut>", self._on_parameter_change); self.v_phase_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['v_phase_deg'] = self.v_phase_entry

        ctk.CTkLabel(input_frame, text="Frequência (Manual/Fallback) [Hz]:").grid(row=5, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        self.freq_details_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 60"); self.freq_details_entry.insert(0, "60")
        self.freq_details_entry.grid(row=5, column=2, padx=(0,10), pady=8, sticky="ew")
        self.freq_details_entry.bind("<FocusOut>", self._on_parameter_change); self.freq_details_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['freq_details'] = self.freq_details_entry
        # --- End Manual Input Section ---

        output_format_label = ctk.CTkLabel(left_panel_scroll_frame, text="Formatação da Saída Textual", font=ctk.CTkFont(size=16, weight="bold"))
        output_format_label.pack(pady=(15,5), anchor="w", padx=10)
        output_format_frame_main = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        output_format_frame_main.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(output_format_frame_main, text="Casas Decimais:").pack(side="left", padx=(10,5), pady=10)
        self.decimal_places_menu = ctk.CTkOptionMenu(output_format_frame_main, variable=self.decimal_places_var,
                                                     values=["2", "3", "4", "5", "6"], command=self._on_formatting_change)
        self.decimal_places_menu.pack(side="left", padx=5, pady=10)
        self.sci_notation_checkbox = ctk.CTkCheckBox(output_format_frame_main, text="Not. Científica",
                                                      variable=self.scientific_notation_var, command=self._on_formatting_change)
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

        pf_correction_label = ctk.CTkLabel(left_panel_scroll_frame, text="Correção de Fator de Potência", font=ctk.CTkFont(size=16, weight="bold"))
        pf_correction_label.pack(pady=(15,5), anchor="w", padx=10)
        pf_correction_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        pf_correction_frame.pack(fill="x", padx=10, pady=(0,10))
        pf_correction_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pf_correction_frame, text="FP Desejado (0.01-1):").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.fp_desired_entry = ctk.CTkEntry(pf_correction_frame, placeholder_text="Ex: 0.95")
        self.fp_desired_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.entry_widgets['fp_desired'] = self.fp_desired_entry
        calculate_pf_button = ctk.CTkButton(pf_correction_frame, text="Calcular Capacitor de Correção", command=self._calculate_and_display_pf_correction)
        calculate_pf_button.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        action_buttons_frame = ctk.CTkFrame(left_panel_scroll_frame, fg_color="transparent")
        action_buttons_frame.pack(pady=(20,10), fill="x")
        analyze_button = ctk.CTkButton(action_buttons_frame, text="Analisar (Principal)", command=self.analyze_circuit) # This button now triggers nodal if netlist present
        analyze_button.pack(side="left", padx=5, expand=True)
        clear_button = ctk.CTkButton(action_buttons_frame, text="Limpar Entradas e Netlist", command=self.clear_entries)
        clear_button.pack(side="left", padx=5, expand=True)
        about_button = ctk.CTkButton(action_buttons_frame, text="Sobre", command=self.show_about_dialog_ctk)
        about_button.pack(side="left", padx=5, expand=True)

        self.progress_bar_frame = ctk.CTkFrame(left_panel_scroll_frame, fg_color="transparent")
        self.progress_bar = ctk.CTkProgressBar(self.progress_bar_frame, orientation="horizontal", mode="indeterminate")
        self.note_label = ctk.CTkLabel(left_panel_scroll_frame, text="Nota: Análise primária via Netlist (Nodal).\nEntradas manuais para RLC eq. são opcionais/alternativas.", font=ctk.CTkFont(size=12), text_color="gray50")
        self.note_label.pack(pady=(10,10), side="bottom")

        right_panel_frame = ctk.CTkFrame(panels_frame, corner_radius=10)
        right_panel_frame.grid(row=0, column=1, sticky="nsew", padx=(10,0), pady=0)
        right_panel_frame.grid_rowconfigure(0, weight=1)
        right_panel_frame.grid_columnconfigure(0, weight=1)

        tab_view = ctk.CTkTabview(right_panel_frame, corner_radius=8)
        tab_view.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        tab_results = tab_view.add("Resultados")
        tab_circuit = tab_view.add("Circuito")
        tab_phasors = tab_view.add("Fasores")
        tab_editor = tab_view.add("Editor") # Nova aba
        tab_waveforms = tab_view.add("Formas de Onda")

        tab_results.grid_columnconfigure(0, weight=1)
        tab_results.grid_rowconfigure(0, weight=1)
        tab_circuit.grid_columnconfigure(0, weight=1)
        tab_circuit.grid_rowconfigure(0, weight=1)
        tab_phasors.grid_columnconfigure(0, weight=1)
        tab_phasors.grid_rowconfigure(0, weight=1)
        tab_waveforms.grid_columnconfigure(0, weight=1) # Frame principal dentro da aba
        tab_waveforms.grid_rowconfigure(0, weight=0)    # Para controles de seleção (futuro)
        tab_waveforms.grid_rowconfigure(1, weight=1)    # Para o gráfico

        # Configurar grid para a aba Editor
        tab_editor.grid_columnconfigure(0, weight=0) # Coluna da paleta (largura ~150px)
        tab_editor.grid_columnconfigure(1, weight=1) # Coluna do canvas (expansível)
        tab_editor.grid_rowconfigure(0, weight=1)    # Linha única expansível


        self.results_text = ctk.CTkTextbox(tab_results, corner_radius=6, wrap="word", font=ctk.CTkFont(family="monospace", size=11))
        self.results_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.results_text.configure(state="disabled")

        self.circuit_diagram_frame = ctk.CTkFrame(tab_circuit, corner_radius=6)
        self.circuit_diagram_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.circuit_diagram_frame.grid_columnconfigure(0, weight=1)
        self.circuit_diagram_frame.grid_rowconfigure(0, weight=1)

        self.circuit_diagram_canvas = tk.Canvas(self.circuit_diagram_frame, bg=self._get_ctk_bg_color(), highlightthickness=0)
        self.circuit_diagram_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.plot_container_frame = ctk.CTkFrame(tab_phasors, corner_radius=6)
        self.plot_container_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.plot_container_frame.grid_columnconfigure(0, weight=1)
        self.plot_container_frame.grid_rowconfigure(0, weight=1)
        self.plot_container_frame.grid_rowconfigure(1, weight=0)

        self.fig_main_plot = Figure(figsize=(5, 4), dpi=100, constrained_layout=True)
        self.ax_main_plot = self.fig_main_plot.add_subplot(111)
        self.canvas_main_plot = FigureCanvasTkAgg(self.fig_main_plot, master=self.plot_container_frame)
        canvas_widget = self.canvas_main_plot.get_tk_widget()
        canvas_widget.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.toolbar_main_plot = NavigationToolbar2Tk(self.canvas_main_plot, self.plot_container_frame, pack_toolbar=False)
        self.toolbar_main_plot.update()
        self.toolbar_main_plot.grid(row=1, column=0, sticky="ew", padx=2, pady=(0,2))

        # --- Estrutura da Aba "Formas de Onda" ---
        # NOVO: Frame de controles principal agora é rolável
        self.scrollable_waveform_controls_area = ctk.CTkScrollableFrame(
            master=tab_waveforms,
            height=220 # Altura fixa para a área de controles
        )
        self.scrollable_waveform_controls_area.grid(row=0, column=0, sticky="new", padx=5, pady=5)

        # Placeholder label, will be replaced by _update_waveform_selection_ui
        ctk.CTkLabel(self.scrollable_waveform_controls_area, text="Execute uma análise para selecionar formas de onda.").pack(padx=10, pady=5)
        
        waveform_plot_frame = ctk.CTkFrame(tab_waveforms, corner_radius=6)
        waveform_plot_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        # waveform_plot_frame já tem grid configurado pela tab_waveforms

        self.fig_waveforms = Figure(figsize=(5, 4), dpi=100, constrained_layout=True)
        self.ax_waveforms = self.fig_waveforms.add_subplot(111)

        self.canvas_waveforms_figure_agg = FigureCanvasTkAgg(self.fig_waveforms, master=waveform_plot_frame)
        self.canvas_waveforms_widget = self.canvas_waveforms_figure_agg.get_tk_widget()
        self.canvas_waveforms_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.toolbar_waveforms = NavigationToolbar2Tk(self.canvas_waveforms_figure_agg, waveform_plot_frame, pack_toolbar=False)
        self.toolbar_waveforms.update()
        self.toolbar_waveforms.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=0)

        # --- Painel da Paleta de Componentes (Esquerda) para a aba Editor ---
        palette_frame = ctk.CTkFrame(tab_editor, width=180, corner_radius=0) # Ajuste a largura conforme necessário
        palette_frame.grid(row=0, column=0, sticky="nsw", padx=(5,0), pady=5)
        palette_frame.grid_propagate(False) # Impede que os botões redimensionem o frame além do width

        ctk.CTkLabel(palette_frame, text="Componentes", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, padx=10)

        # Botões da Paleta (a lógica de comando virá depois)
        self.btn_resistor_tool = ctk.CTkButton(palette_frame, text="Resistor (R)", command=lambda: self._select_tool("RESISTOR"))
        self.btn_resistor_tool.pack(pady=5, padx=10, fill="x")

        self.btn_capacitor_tool = ctk.CTkButton(palette_frame, text="Capacitor (C)", command=lambda: self._select_tool("CAPACITOR"))
        self.btn_capacitor_tool.pack(pady=5, padx=10, fill="x")

        self.btn_inductor_tool = ctk.CTkButton(palette_frame, text="Indutor (L)", command=lambda: self._select_tool("INDUCTOR"))
        self.btn_inductor_tool.pack(pady=5, padx=10, fill="x")

        self.btn_vs_tool = ctk.CTkButton(palette_frame, text="Fonte de Tensão (VS)", command=lambda: self._select_tool("VS"))
        self.btn_vs_tool.pack(pady=5, padx=10, fill="x")

        self.btn_is_tool = ctk.CTkButton(palette_frame, text="Fonte de Corrente (IS)", command=lambda: self._select_tool("IS"))
        self.btn_is_tool.pack(pady=5, padx=10, fill="x")

        self.btn_gnd_tool = ctk.CTkButton(palette_frame, text="Terra (GND)", command=lambda: self._select_tool("GND"))
        self.btn_gnd_tool.pack(pady=5, padx=10, fill="x")

        self.btn_vcvs_tool = ctk.CTkButton(palette_frame, text="VCVS (E)", command=lambda: self._select_tool("VCVS"))
        self.btn_vcvs_tool.pack(pady=5, padx=10, fill="x")

        self.btn_vccs_tool = ctk.CTkButton(palette_frame, text="VCCS (G)", command=lambda: self._select_tool("VCCS"))
        self.btn_vccs_tool.pack(pady=5, padx=10, fill="x")

        self.btn_ccvs_tool = ctk.CTkButton(palette_frame, text="CCVS (H)", command=lambda: self._select_tool("CCVS"))
        self.btn_ccvs_tool.pack(pady=5, padx=10, fill="x")

        self.btn_cccs_tool = ctk.CTkButton(palette_frame, text="CCCS (F)", command=lambda: self._select_tool("CCCS"))
        self.btn_cccs_tool.pack(pady=5, padx=10, fill="x")

        # Wire tool will be handled later
        self.btn_wire_tool = ctk.CTkButton(palette_frame, text="Fio (Wire)", command=lambda: self._select_tool("WIRE"))
        self.btn_wire_tool.pack(pady=5, padx=10, fill="x")

        # Botão para Gerar Netlist
        self.btn_generate_netlist = ctk.CTkButton(palette_frame, text="Gerar Netlist", command=self._initiate_netlist_generation)
        self.btn_generate_netlist.pack(pady=(20,5), padx=10, fill="x")

        # Botão para Salvar Diagrama
        self.btn_save_diagram = ctk.CTkButton(palette_frame, text="Salvar Diagrama", command=self._prompt_save_diagram_as)
        self.btn_save_diagram.pack(pady=5, padx=10, fill="x")

        # Botão para Carregar Diagrama
        self.btn_load_diagram = ctk.CTkButton(palette_frame, text="Carregar Diagrama", command=self._prompt_load_diagram)
        self.btn_load_diagram.pack(pady=5, padx=10, fill="x")

        # Checkbox para Snap-to-Grid
        self.snap_to_grid_checkbox = ctk.CTkCheckBox(palette_frame, text="Snap à Grade", variable=self.snap_to_grid_enabled,
                                                     onvalue=True, offvalue=False)
        self.snap_to_grid_checkbox.pack(pady=(10,5), padx=10, fill="x")

        # --- Painel do Canvas de Desenho (Direita) para a aba Editor ---
        canvas_frame = ctk.CTkFrame(tab_editor, corner_radius=0, fg_color="transparent")
        canvas_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)

        self.editor_canvas = tk.Canvas(canvas_frame, bg=self._get_ctk_bg_color(), highlightthickness=0) # Usar cor de fundo do tema
        self.editor_canvas.grid(row=0, column=0, sticky="nsew")
        # self.editor_canvas.bind("<Button-1>", self._handle_canvas_left_click) # Replaced by ButtonPress-1
        self.editor_canvas.bind("<ButtonPress-1>", self._on_canvas_drag_start)
        self.editor_canvas.bind("<B1-Motion>", self._on_canvas_drag_motion)
        self.editor_canvas.bind("<ButtonRelease-1>", self._on_canvas_drag_release)
        self.editor_canvas.bind("<Double-Button-1>", self._on_canvas_double_click) 
        self.editor_canvas.bind("<Escape>", self._on_escape_key_press)
        self.editor_canvas.bind("<Delete>", self._on_delete_key_press)
        self.editor_canvas.bind("<Motion>", self._update_wire_preview) # For wire preview
        self.editor_canvas.bind("<Configure>", lambda event: self._draw_editor_grid()) # Redraw grid on resize
        # Bind mouse wheel events for zoom
        self.editor_canvas.bind("<MouseWheel>", self._handle_mouse_zoom)  # For Windows and macOS
        self.editor_canvas.bind("<Button-4>", self._handle_mouse_zoom)    # For Linux (scroll up)
        self.editor_canvas.bind("<Button-5>", self._handle_mouse_zoom)    # For Linux (scroll down)
        # Bind middle mouse button events for panning
        self.editor_canvas.bind("<ButtonPress-2>", self._on_pan_start)
        self.editor_canvas.bind("<B2-Motion>", self._on_pan_motion)
        self.editor_canvas.bind("<ButtonRelease-2>", self._on_pan_release)
        # You might need to test <ButtonPress-3> etc. if <Button-2> doesn't work for your middle mouse button


        self._clear_main_plot(initial_message="Diagrama Fasorial: Insira netlist e analise.")
        self._clear_static_circuit_diagram(initial_message="Diagrama do Circuito: Aguardando análise via netlist.")
        self._clear_waveforms_plot(initial_message="Execute uma análise para ver as formas de onda.")

        self.master.after(10, self._on_include_component_change)
        self._on_include_component_change()
        self.master.after(50, self._draw_editor_grid) # Initial grid draw after UI is likely settled
        self._update_waveform_selection_ui() # Initial call to setup placeholder

    def _draw_editor_grid(self):
        """Draws the grid on the editor canvas."""
        self.editor_canvas.delete("grid_line_tag") # Clear previous grid lines

        # It's important to call update_idletasks to ensure winfo_width/height are accurate
        # especially if called early or from <Configure> before full layout.
        self.editor_canvas.update_idletasks()
        
        canvas_width = self.editor_canvas.winfo_width()
        canvas_height = self.editor_canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1: # Canvas not yet sized
            return

        # Draw vertical lines
        for x_grid in range(0, canvas_width, self.grid_spacing):
            self.editor_canvas.create_line(x_grid, 0, x_grid, canvas_height,
                                           fill=self.grid_color, tags="grid_line_tag")
        # Draw horizontal lines
        for y_grid in range(0, canvas_height, self.grid_spacing):
            self.editor_canvas.create_line(0, y_grid, canvas_width, y_grid,
                                           fill=self.grid_color, tags="grid_line_tag")

        self.editor_canvas.tag_lower("grid_line_tag") # Send grid lines to the bottom

    def _snap_to_grid_coords(self, x, y):
        """Snaps the given x, y coordinates to the nearest grid intersection."""
        if not self.snap_to_grid_enabled.get() or self.grid_spacing <= 0:
            return int(x), int(y) # Return as int even if not snapping
        
        snapped_x = round(x / self.grid_spacing) * self.grid_spacing
        snapped_y = round(y / self.grid_spacing) * self.grid_spacing
        return int(snapped_x), int(snapped_y)

    def _handle_mouse_zoom(self, event):
        """Handles mouse wheel scrolling for zooming the editor canvas."""
        scale_factor = 1.0
        
        # Determine scroll direction and set scale_factor
        if event.num == 4 or event.delta > 0:  # Linux scroll up or Windows/macOS scroll up
            scale_factor = self.zoom_factor_increment
        elif event.num == 5 or event.delta < 0:  # Linux scroll down or Windows/macOS scroll down
            scale_factor = self.zoom_factor_decrement
        else: # Unrecognized event
            return

        if scale_factor != 1.0:
            # The canvas coordinates (event.x, event.y) are the origin for scaling
            # Need to convert widget-relative (event.x, event.y) to canvas-relative if canvas is scrolled (panning)
            # For now, assuming no panning, event.x, event.y are fine.
            # If panning is implemented, use:
            # canvas_x = self.editor_canvas.canvasx(event.x)
            # canvas_y = self.editor_canvas.canvasy(event.y)
            # self.editor_canvas.scale("all", canvas_x, canvas_y, scale_factor, scale_factor)
            
            self.editor_canvas.scale("all", event.x, event.y, scale_factor, scale_factor)
            self.current_zoom_level *= scale_factor
            
            # print(f"Zoom Level: {self.current_zoom_level:.2f} at ({event.x}, {event.y})") # For debugging

            # The grid lines (tagged "grid_line_tag") are scaled by "all".
            # If more sophisticated grid behavior is needed (e.g., constant visual spacing),
            # then _draw_editor_grid would need to be called and made zoom-aware.

    def _on_pan_start(self, event):
        """Handles the start of a canvas pan operation (middle mouse button press)."""
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.editor_canvas.scan_mark(event.x, event.y)
        self.editor_canvas.config(cursor="fleur") # Change cursor to indicate panning

    def _on_pan_motion(self, event):
        """Handles the canvas pan operation during mouse motion."""
        if self.is_panning:
            self.editor_canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_pan_release(self, event):
        """Handles the end of a canvas pan operation (middle mouse button release)."""
        if self.is_panning:
            self.is_panning = False
            self.editor_canvas.config(cursor="") # Reset cursor to default


    # --- Canvas Interaction Methods (Click, Drag, etc.) ---

    def _on_canvas_drag_start(self, event):
        self.editor_canvas.focus_set() # Ensure canvas has focus for keyboard events

        if self.selected_component_tool == "WIRE":
            if not self.is_drawing_wire: # Trying to start a new wire
                if self._start_wire_drawing(event.x, event.y):
                    # Wire started successfully, do nothing more on this click
                    return
                # If _start_wire_drawing returned False, it means no terminal was clicked.
                # Allow user to try again without deselecting the tool.
            else:
                # If self.is_drawing_wire is True, this is the second click to finalize or cancel.
                self._try_finalize_wire(event.x, event.y)
            return # Prevent further processing if WIRE tool is active
        elif self.selected_component_tool is not None: # Note: elif here
            # Snap the initial click position for adding an element
            snapped_x, snapped_y = self._snap_to_grid_coords(event.x, event.y)
            self._add_element_on_canvas(snapped_x, snapped_y) # Pass snapped coords
            self.is_dragging = False # Ensure not dragging a newly added component
        else:
            # No tool active, try to select an existing component
            self._handle_selection(event) # This updates self.currently_selected_element_id
            if self.currently_selected_element_id is not None:
                self.is_dragging = True
                self.drag_start_mouse_x = event.x
                self.drag_start_mouse_y = event.y
                
                # Optional: Lift the selected element's items to the top
                selected_element = next((el for el in self.circuit_elements_on_canvas if el["id"] == self.currently_selected_element_id), None)
                if selected_element:
                    for item_id in selected_element["canvas_item_ids"]:
                        self.editor_canvas.lift(item_id)
            else:
                self.is_dragging = False

    def _on_canvas_drag_motion(self, event):
        if self.is_dragging and self.currently_selected_element_id:
            dx = event.x - self.drag_start_mouse_x
            dy = event.y - self.drag_start_mouse_y

            element_to_move = None
            for el in self.circuit_elements_on_canvas:
                if el["id"] == self.currently_selected_element_id:
                    element_to_move = el
                    break
            
            if not element_to_move: return

            current_center_x, current_center_y = element_to_move['x'], element_to_move['y']

            # Mouse displacement since the last motion event
            mouse_dx = event.x - self.drag_start_mouse_x
            mouse_dy = event.y - self.drag_start_mouse_y

            # New theoretical position (element's current center + mouse delta)
            new_theoretical_x = current_center_x + mouse_dx
            new_theoretical_y = current_center_y + mouse_dy

            # Apply snap to the new theoretical position
            snapped_x, snapped_y = self._snap_to_grid_coords(new_theoretical_x, new_theoretical_y)

            # Calculate the actual delta to move canvas items (from old snapped position to new snapped position)
            actual_dx_to_move_items = snapped_x - current_center_x
            actual_dy_to_move_items = snapped_y - current_center_y

            if actual_dx_to_move_items != 0 or actual_dy_to_move_items != 0:
                for item_canvas_id in element_to_move["canvas_item_ids"]:
                    self.editor_canvas.move(item_canvas_id, actual_dx_to_move_items, actual_dy_to_move_items)
                
                element_to_move["x"] = snapped_x
                element_to_move["y"] = snapped_y

                # Update connected wires (this logic was already part of the original method)
                wires_to_update_ids = set()
                for terminal in element_to_move.get("terminals", []):
                    for wire_id in terminal.get("connected_wire_ids", []):
                        wires_to_update_ids.add(wire_id)
                for wire_id_to_update in wires_to_update_ids:
                    wire_object = next((w for w in self.wires_on_canvas if w["id"] == wire_id_to_update), None)
                    if wire_object:
                        start_coords = self._get_terminal_absolute_coords(wire_object['start_element_id'], wire_object['start_terminal_name'])
                        end_coords = self._get_terminal_absolute_coords(wire_object['end_element_id'], wire_object['end_terminal_name'])

                        if start_coords and end_coords:
                            self.editor_canvas.coords(wire_object['canvas_line_id'],
                                                      start_coords[0], start_coords[1], end_coords[0], end_coords[1])
            # Update the reference mouse position for the next motion event calculation
            self.drag_start_mouse_x = event.x
            self.drag_start_mouse_y = event.y

    def _on_canvas_drag_release(self, event):
        if self.is_dragging:
            self.is_dragging = False
            if self.currently_selected_element_id:
                element = next((el for el in self.circuit_elements_on_canvas if el["id"] == self.currently_selected_element_id), None)
                if element:
                    print(f"Elemento '{element['id']}' movido para ({element['x']}, {element['y']})")
        # Deselection on empty click is handled by _handle_selection called in _on_canvas_drag_start

    def _start_wire_drawing(self, click_x, click_y):
        hit_radius_sq = self.wire_hit_radius ** 2 # Use squared distance for efficiency

        for element in self.circuit_elements_on_canvas:
            if not element.get("terminals"): # Skip elements without terminals
                continue
            for terminal_info in element["terminals"]:
                abs_term_x = element['x'] + terminal_info['x_offset']
                abs_term_y = element['y'] + terminal_info['y_offset']

                # Calculate squared distance from click to terminal center
                dist_sq = (click_x - abs_term_x)**2 + (click_y - abs_term_y)**2

                if dist_sq < hit_radius_sq:
                    self.is_drawing_wire = True
                    self.wire_start_info = {
                        'element_id': element['id'],
                        'terminal_name': terminal_info['name'],
                        'abs_x': abs_term_x,
                        'abs_y': abs_term_y
                    }
                    # Create the preview line, initially from start point to the same start point (or click point)
                    self.wire_preview_line_id = self.editor_canvas.create_line(
                        abs_term_x, abs_term_y,
                        click_x, click_y, # End of line will follow mouse
                        fill="gray", dash=(2, 2), tags=("wire_preview")
                    )
                    print(f"Iniciando fio de {element['id']}/{terminal_info['name']} em ({abs_term_x:.2f},{abs_term_y:.2f})")
                    return True # Wire successfully started
        
        print("Nenhum terminal encontrado no ponto de clique para iniciar fio.")
        return False # No terminal found at click location

    def _update_wire_preview(self, event):
        if self.is_drawing_wire and self.wire_preview_line_id is not None and self.wire_start_info:
            mouse_x, mouse_y = event.x, event.y
            start_x = self.wire_start_info['abs_x']
            start_y = self.wire_start_info['abs_y']
            
            # Update the coordinates of the preview line
            self.editor_canvas.coords(self.wire_preview_line_id, start_x, start_y, mouse_x, mouse_y)

    def _try_finalize_wire(self, click_x, click_y):
        hit_radius_sq = self.wire_hit_radius ** 2
        found_end_terminal = False

        for end_element in self.circuit_elements_on_canvas:
            if not end_element.get("terminals"):
                continue
            for end_terminal_info in end_element["terminals"]:
                abs_end_term_x = end_element['x'] + end_terminal_info['x_offset']
                abs_end_term_y = end_element['y'] + end_terminal_info['y_offset']

                dist_sq = (click_x - abs_end_term_x)**2 + (click_y - abs_end_term_y)**2

                if dist_sq < hit_radius_sq:
                    # Check if it's the same terminal as the start
                    if (end_element['id'] == self.wire_start_info['element_id'] and
                        end_terminal_info['name'] == self.wire_start_info['terminal_name']):
                        print("Tentativa de conectar fio ao mesmo terminal de início. Cancelando.")
                        self._cancel_wire_drawing()
                        return

                    # Valid end terminal found
                    found_end_terminal = True

                    # Delete preview line
                    if self.wire_preview_line_id:
                        self.editor_canvas.delete(self.wire_preview_line_id)
                        self.wire_preview_line_id = None

                    # Draw permanent wire
                    wire_id_str = f"wire_{self.next_wire_id}"
                    permanent_line_id = self.editor_canvas.create_line(
                        self.wire_start_info['abs_x'], self.wire_start_info['abs_y'],
                        abs_end_term_x, abs_end_term_y,
                        fill="black", width=2, tags=("wire", wire_id_str)
                    )

                    new_wire = {
                        "id": wire_id_str,
                        "start_element_id": self.wire_start_info['element_id'],
                        "start_terminal_name": self.wire_start_info['terminal_name'],
                        "end_element_id": end_element['id'],
                        "end_terminal_name": end_terminal_info['name'],
                        "canvas_line_id": permanent_line_id
                    }
                    self.wires_on_canvas.append(new_wire)
                    self.next_wire_id += 1

                    # Update connected_wire_ids in terminals
                    # Start terminal
                    start_el_ref = next((el for el in self.circuit_elements_on_canvas if el["id"] == new_wire["start_element_id"]), None)
                    if start_el_ref:
                        start_term_ref = next((t for t in start_el_ref.get("terminals", []) if t["name"] == new_wire["start_terminal_name"]), None)
                        if start_term_ref:
                            start_term_ref.setdefault("connected_wire_ids", []).append(new_wire["id"])

                    # End terminal
                    end_el_ref = next((el for el in self.circuit_elements_on_canvas if el["id"] == new_wire["end_element_id"]), None)
                    if end_el_ref:
                        end_term_ref = next((t for t in end_el_ref.get("terminals", []) if t["name"] == new_wire["end_terminal_name"]), None)
                        if end_term_ref:
                            end_term_ref.setdefault("connected_wire_ids", []).append(new_wire["id"])

                    print(f"Fio {new_wire['id']} conectado de {new_wire['start_element_id']}/{new_wire['start_terminal_name']} para {new_wire['end_element_id']}/{new_wire['end_terminal_name']}")
                    break # Break from inner loop (terminals)
            if found_end_terminal:
                break # Break from outer loop (elements)

        if not found_end_terminal:
            print("Nenhum terminal de destino encontrado. Cancelando desenho do fio.")
            self._cancel_wire_drawing() # This will also reset state
            return # Explicit return after cancel

        # Reset state after successful wire creation
        self.is_drawing_wire = False
        self.wire_start_info = None
        # self.wire_preview_line_id should already be None or deleted
        # Do not reset self.selected_component_tool to allow drawing multiple wires

    def _cancel_wire_drawing(self):
        if self.is_drawing_wire: # Check if we are actually in drawing mode
            if self.wire_preview_line_id:
                self.editor_canvas.delete(self.wire_preview_line_id)
                self.wire_preview_line_id = None
            
            self.is_drawing_wire = False
            self.wire_start_info = None
            # self.wire_preview_line_id is already handled
            print("Desenho de fio cancelado.")
        # No need to reset selected_component_tool here, user might want to try again.

    def _on_escape_key_press(self, event=None): # event is optional
        print("Tecla Escape pressionada.")
        if self.is_drawing_wire:
            self._cancel_wire_drawing()
            
    def _get_terminal_absolute_coords(self, element_id, terminal_name):
        target_element = next((el for el in self.circuit_elements_on_canvas if el["id"] == element_id), None)
        if not target_element:
            print(f"Debug: Element {element_id} not found in _get_terminal_absolute_coords")
            return None

        target_terminal_info = next((term for term in target_element.get("terminals", []) if term["name"] == terminal_name), None)
        if not target_terminal_info:
            print(f"Debug: Terminal {terminal_name} on element {element_id} not found in _get_terminal_absolute_coords")
            return None

        abs_x = target_element['x'] + target_terminal_info['x_offset']
        abs_y = target_element['y'] + target_terminal_info['y_offset']
        return abs_x, abs_y


    def _on_canvas_double_click(self, event):
        # Find the item clicked, similar to _handle_selection
        items_nearby = self.editor_canvas.find_closest(event.x, event.y, halo=5)
        
        element_id_to_edit = None
        if items_nearby:
            item_id = items_nearby[0] # Get the ID of the closest graphical item
            tags = self.editor_canvas.gettags(item_id)
            
            # Check if the item belongs to a component symbol and has a valid ID
            # We check for "component_symbol" as the primary tag for hit detection on the main body
            if tags and "component_symbol" in tags:
                potential_element_id = tags[0] # By convention, the first tag is the unique element ID
                # Verify this ID corresponds to a managed element
                if any(element["id"] == potential_element_id for element in self.circuit_elements_on_canvas):
                    element_id_to_edit = potential_element_id
        
        if element_id_to_edit:
            self._edit_element_properties(element_id_to_edit)

    def _handle_selection(self, event):
        items_nearby_comp = self.editor_canvas.find_closest(event.x, event.y, halo=5) # For components
        
        element_id_to_select = None
        if items_nearby_comp:
            item_id = items_nearby_comp[0] # Get the ID of the closest graphical item
            tags = self.editor_canvas.gettags(item_id)
            
            # Check if the item is a main component symbol and has a valid ID
            if tags and "component_symbol" in tags:
                potential_element_id = tags[0] # By convention, the first tag is the unique element ID
                # Verify this ID corresponds to a managed element
                if any(element["id"] == potential_element_id for element in self.circuit_elements_on_canvas):
                    element_id_to_select = potential_element_id
        
        if element_id_to_select:
            self._deselect_all_wires() 
            self._select_element(element_id_to_select)
        else:
            # No component selected, try to select a wire
            items_nearby_wire = self.editor_canvas.find_closest(event.x, event.y, halo=3) # Smaller halo for wires
            wire_id_to_select = None
            if items_nearby_wire:
                item_id = items_nearby_wire[0]
                tags = self.editor_canvas.gettags(item_id)
                if "wire" in tags:
                    # The second tag should be the unique wire ID
                    for tag_idx, tag_val in enumerate(tags):
                        if tag_idx == 1 and tag_val.startswith("wire_") and any(w["id"] == tag_val for w in self.wires_on_canvas):
                            wire_id_to_select = tag_val
                            break
            
            if wire_id_to_select:
                self._deselect_all_elements() 
                self._select_wire(wire_id_to_select)
            else: # Clicked on empty space
                self._deselect_all_elements()
                self._deselect_all_wires()

    def _select_element(self, element_id_to_select):
        self._deselect_all_wires() # Ensure no wire is selected

        if self.currently_selected_element_id == element_id_to_select:
            return # Already selected

        if self.currently_selected_element_id:
            self._deselect_all_elements() # Deselect the old one

        self.currently_selected_element_id = element_id_to_select
        
        for element in self.circuit_elements_on_canvas:
            if element["id"] == self.currently_selected_element_id:
                for item_canvas_id in element["canvas_item_ids"]:
                    item_type = self.editor_canvas.type(item_canvas_id)
                    # Apply selection style to main visual parts
                    if item_type in ["rectangle", "oval", "line"]: 
                        try:
                            self.editor_canvas.itemconfig(item_canvas_id, outline=self.selection_outline_color, width=2)
                        except tk.TclError: # Some items might not have 'outline' (e.g., text)
                            pass
                print(f"Elemento selecionado: {element['id']}")
                break

    def _deselect_all_elements(self):
        if self.currently_selected_element_id:
            element_id_to_deselect = self.currently_selected_element_id
            self.currently_selected_element_id = None # Clear selection first
            
            for element in self.circuit_elements_on_canvas:
                if element["id"] == element_id_to_deselect:
                    for item_canvas_id in element["canvas_item_ids"]:
                        item_type = self.editor_canvas.type(item_canvas_id)
                        if item_type in ["rectangle", "oval", "line"]:
                            try:
                                # Restore default appearance
                                self.editor_canvas.itemconfig(item_canvas_id, outline=self.default_outline_color, width=1)
                                # Note: This sets width to 1. If original widths varied and need exact restoration,
                                # this part would need to be more complex (e.g., store original widths).
                                # For capacitor plates (orig width 2), inductor arcs (orig 1.5), GND (orig 1.5)
                                # this will make them thinner when deselected. This is acceptable for a clear visual cue.
                            except tk.TclError:
                                pass
                    print(f"Elemento deselecionado: {element_id_to_deselect}")
                    break

    def _select_wire(self, wire_id_to_select):
        self._deselect_all_elements() # Ensure no component is selected

        if self.currently_selected_wire_id == wire_id_to_select:
            return # Already selected

        if self.currently_selected_wire_id:
            self._deselect_all_wires() # Deselect the old one

        self.currently_selected_wire_id = wire_id_to_select
        
        wire_object = next((w for w in self.wires_on_canvas if w["id"] == self.currently_selected_wire_id), None)
        if wire_object:
            try:
                self.editor_canvas.itemconfig(wire_object['canvas_line_id'], 
                                              fill=self.wire_selection_color, 
                                              width=3) # Make selected wire thicker
                print(f"Fio selecionado: {wire_object['id']}")
            except tk.TclError as e:
                print(f"Erro ao tentar destacar o fio {wire_object['id']}: {e}")
        else:
            print(f"Erro: Fio com ID '{self.currently_selected_wire_id}' não encontrado para seleção.")
            self.currently_selected_wire_id = None # Reset if not found

    def _deselect_all_wires(self):
        if self.currently_selected_wire_id:
            wire_id_to_deselect = self.currently_selected_wire_id
            self.currently_selected_wire_id = None 
            
            wire_object = next((w for w in self.wires_on_canvas if w["id"] == wire_id_to_deselect), None)
            if wire_object:
                try:
                    self.editor_canvas.itemconfig(wire_object['canvas_line_id'], fill=self.wire_default_color, width=2)
                    print(f"Fio deselecionado: {wire_id_to_deselect}")
                except tk.TclError as e:
                    print(f"Aviso: Erro ao tentar restaurar aparência do fio {wire_id_to_deselect} (pode já ter sido deletado): {e}")

    def _edit_element_properties(self, element_id):
        element = next((el for el in self.circuit_elements_on_canvas if el["id"] == element_id), None)
        if not element:
            print(f"Erro: Elemento com ID '{element_id}' não encontrado para edição.")
            return

        element_type = element['type']
        current_value = element['properties'].get('value', '') # Get current value for potential display in prompt or default

        prompt_title = "Editar Propriedade"
        # Default prompt_text, will be overridden by specific types
        prompt_text = f"Novo valor para {element_type} ({element_id}):" 

        # Customize prompt based on component type
        if element_type == "RESISTOR":
            prompt_text = f"Valor da Resistência ({element_id}) [Ex: 1k, 100, 2.2M]:"
        elif element_type == "CAPACITOR":
            prompt_text = f"Valor da Capacitância ({element_id}) [Ex: 1u, 100n, 47p]:"
        elif element_type == "INDUCTOR":
            prompt_text = f"Valor da Indutância ({element_id}) [Ex: 1m, 100u, 2.2]:"
        elif element_type == "VS":
            # For VS, we might want mag and phase later, but for now just magnitude string
            prompt_text = f"Valor da Tensão ({element_id}) [Ex: 10V, 220V 0deg]:"
        elif element_type == "IS":
            # For IS, just magnitude string for now
            prompt_text = f"Valor da Corrente ({element_id}) [Ex: 1A, 0.5A 30deg]:"
        elif element_type == "VCVS":
            # For VCVS, we'll handle multiple properties sequentially
            pass # Special handling below
        elif element_type == "VCCS":
            # For VCCS, similar multi-property handling
            pass # Special handling below
        elif element_type == "CCVS":
            # For CCVS, multi-property handling
            pass # Special handling below
        elif element_type == "GND":
            print(f"Não é possível editar propriedades de um elemento {element_type}.")
            return # GND has no editable value in this context
            print(f"Não é possível editar propriedades de um elemento {element_type}.")
            return # GND has no editable value in this context
        else:
             print(f"Edição de propriedades não implementada para o tipo '{element_type}'.")
             return

        if element_type == "VCVS":
            # Get Gain
            gain_dialog = ctk.CTkInputDialog(text=f"Ganho de Tensão (V/V) para {element_id}:", title="Editar Ganho VCVS")
            new_gain_str = gain_dialog.get_input()
            if new_gain_str is not None and new_gain_str.strip() != "":
                element['properties']['value'] = new_gain_str.strip() # 'value' stores gain for VCVS
            else: # Cancelled or empty
                print(f"Edição do ganho para '{element_id}' cancelada ou vazia.")
                return # Stop if gain is not provided

            # Get Control Node Positive
            ctrl_p_dialog = ctk.CTkInputDialog(text=f"Nó de Controle Positivo (+) para {element_id}:", title="Editar Nó Controle VCVS")
            new_ctrl_p_str = ctrl_p_dialog.get_input()
            if new_ctrl_p_str is not None and new_ctrl_p_str.strip() != "":
                element['properties']['ctrl_node_p'] = new_ctrl_p_str.strip()
            else:
                print(f"Edição do nó de controle '+' para '{element_id}' cancelada ou vazia.")
                return

            # Get Control Node Negative
            ctrl_n_dialog = ctk.CTkInputDialog(text=f"Nó de Controle Negativo (-) para {element_id}:", title="Editar Nó Controle VCVS")
            new_ctrl_n_str = ctrl_n_dialog.get_input()
            if new_ctrl_n_str is not None and new_ctrl_n_str.strip() != "":
                element['properties']['ctrl_node_n'] = new_ctrl_n_str.strip()
            else:
                print(f"Edição do nó de controle '-' para '{element_id}' cancelada ou vazia.")
                return
            
            self._update_element_label(element_id)
            print(f"Propriedades de '{element_id}' (VCVS) atualizadas: Ganho='{element['properties']['value']}', Ctrl+='{element['properties']['ctrl_node_p']}', Ctrl-='{element['properties']['ctrl_node_n']}'")

        elif element_type == "VCCS":
            # Get Transconductance (Gm)
            gm_dialog = ctk.CTkInputDialog(text=f"Transcondutância (Gm - Siemens) para {element_id}:", title="Editar Gm VCCS")
            new_gm_str = gm_dialog.get_input()
            if new_gm_str is not None and new_gm_str.strip() != "":
                element['properties']['value'] = new_gm_str.strip() # 'value' stores Gm for VCCS
            else:
                print(f"Edição da transcondutância para '{element_id}' cancelada ou vazia.")
                return

            # Get Control Node Positive
            ctrl_p_dialog_vccs = ctk.CTkInputDialog(text=f"Nó de Controle Positivo (+) para {element_id}:", title="Editar Nó Controle VCCS")
            new_ctrl_p_vccs_str = ctrl_p_dialog_vccs.get_input()
            if new_ctrl_p_vccs_str is not None and new_ctrl_p_vccs_str.strip() != "":
                element['properties']['ctrl_node_p'] = new_ctrl_p_vccs_str.strip()
            else:
                print(f"Edição do nó de controle '+' para '{element_id}' (VCCS) cancelada ou vazia.")
                return

            # Get Control Node Negative
            ctrl_n_dialog_vccs = ctk.CTkInputDialog(text=f"Nó de Controle Negativo (-) para {element_id}:", title="Editar Nó Controle VCCS")
            new_ctrl_n_vccs_str = ctrl_n_dialog_vccs.get_input()
            if new_ctrl_n_vccs_str is not None and new_ctrl_n_vccs_str.strip() != "":
                element['properties']['ctrl_node_n'] = new_ctrl_n_vccs_str.strip()
            else:
                print(f"Edição do nó de controle '-' para '{element_id}' (VCCS) cancelada ou vazia.")
                return
            
            self._update_element_label(element_id)
            print(f"Propriedades de '{element_id}' (VCCS) atualizadas: Gm='{element['properties']['value']}', Ctrl+='{element['properties']['ctrl_node_p']}', Ctrl-='{element['properties']['ctrl_node_n']}'")

        elif element_type == "CCVS":
            # Get Transresistance (Rm)
            rm_dialog = ctk.CTkInputDialog(text=f"Transresistência (Rm - Ohms) para {element_id}:", title="Editar Rm CCVS")
            new_rm_str = rm_dialog.get_input()
            if new_rm_str is not None and new_rm_str.strip() != "":
                element['properties']['value'] = new_rm_str.strip() # 'value' stores Rm for CCVS
            else:
                print(f"Edição da transresistência para '{element_id}' (CCVS) cancelada ou vazia.")
                return

            # Get Control Source Name (VS name)
            ctrl_src_dialog_ccvs = ctk.CTkInputDialog(text=f"Nome da Fonte VS de Controle para {element_id} (Ex: VS1):", title="Editar Fonte Controle CCVS")
            new_ctrl_src_ccvs_str = ctrl_src_dialog_ccvs.get_input()
            if new_ctrl_src_ccvs_str is not None and new_ctrl_src_ccvs_str.strip() != "":
                element['properties']['control_source_name'] = new_ctrl_src_ccvs_str.strip()
            else:
                print(f"Edição do nome da fonte de controle para '{element_id}' (CCVS) cancelada ou vazia.")
                return
            
            self._update_element_label(element_id)
            print(f"Propriedades de '{element_id}' (CCVS) atualizadas: Rm='{element['properties']['value']}', CtrlVS='{element['properties']['control_source_name']}'")

        elif element_type == "CCCS":
            # Editar Ganho de Corrente (Beta)
            current_beta = str(element['properties'].get('value', '100'))
            gain_dialog_cccs = ctk.CTkInputDialog(
                text=f"Novo Ganho de Corrente (Beta) para {element_id}:",
                title="Editar Ganho CCCS"
            )
            gain_dialog_cccs.entry.insert(0, current_beta)
            new_gain_str_cccs = gain_dialog_cccs.get_input()
            if new_gain_str_cccs is not None and new_gain_str_cccs.strip() != "":
                element['properties']['value'] = new_gain_str_cccs.strip()
            # else: User cancelled or entered empty, keep current_beta

            # Editar Nome da Fonte VS de Controle
            current_ctrl_src_cccs = str(element['properties'].get('control_source_name', 'VS_monitor?'))
            ctrl_src_dialog_cccs = ctk.CTkInputDialog(
                text=f"Nome da Fonte VS de Controle para {element_id} (Ex: VS1):",
                title="Editar Fonte de Controle CCCS"
            )
            ctrl_src_dialog_cccs.entry.insert(0, current_ctrl_src_cccs)
            new_ctrl_src_name_cccs = ctrl_src_dialog_cccs.get_input()
            if new_ctrl_src_name_cccs is not None and new_ctrl_src_name_cccs.strip() != "":
                element['properties']['control_source_name'] = new_ctrl_src_name_cccs.strip()
            # else: User cancelled or entered empty, keep current_ctrl_src_cccs
            
            self._update_element_label(element_id)
            print(f"Propriedades de '{element_id}' (CCCS) atualizadas: Beta='{element['properties']['value']}', CtrlVS='{element['properties']['control_source_name']}'")
        else: # For other components
            # Use CTkInputDialog to get the new value
            dialog = ctk.CTkInputDialog(text=prompt_text, title=prompt_title)
            dialog.entry.insert(0, str(current_value)) # Pre-fill with current value
            # To pre-fill the dialog (optional): dialog.entry.insert(0, current_value)
            new_value_str = dialog.get_input()

            if new_value_str is not None: # User didn't cancel
                new_value_str = new_value_str.strip()
                if new_value_str != "":
                    # Store the new value (basic string storage for now)
                    element['properties']['value'] = new_value_str
                    self._update_element_label(element_id)
                    print(f"Propriedade 'value' de '{element_id}' atualizada para: '{new_value_str}'")
                else:
                    # User entered empty string, could choose to clear value or ignore
                    print(f"Entrada vazia para '{element_id}'. Valor não alterado (ou poderia ser limpo).")
            # else: User cancelled the dialog

        # Common update call if not a controlled source (they update label inside their blocks)
        if element_type not in ["VCVS", "VCCS", "CCVS", "CCCS"]:
                self._update_element_label(element_id)

    def _delete_selected_element(self):
        if self.currently_selected_element_id is None:
            print("Nenhum elemento selecionado para deletar.")
            return

        element_to_delete = None
        element_index = -1
        for i, el in enumerate(self.circuit_elements_on_canvas):
            if el["id"] == self.currently_selected_element_id:
                element_to_delete = el
                element_index = i
                break
        
        if element_to_delete:
            # --- Wire Deletion Logic ---
            terminals_of_deleted_element = element_to_delete.get("terminals", [])
            wires_to_remove_from_canvas_and_list_ids = set()
            for terminal in terminals_of_deleted_element:
                for wire_id in terminal.get("connected_wire_ids", []):
                    wires_to_remove_from_canvas_and_list_ids.add(wire_id)

            for wire_id_to_remove in list(wires_to_remove_from_canvas_and_list_ids): # Iterate over a copy
                wire_object_idx = -1
                wire_object = None
                for i_w, w_obj in enumerate(self.wires_on_canvas):
                    if w_obj["id"] == wire_id_to_remove:
                        wire_object = w_obj
                        wire_object_idx = i_w
                        break
                
                if wire_object:
                    # Delete visual wire from canvas
                    self.editor_canvas.delete(wire_object['canvas_line_id'])

                    # Remove wire reference from the OTHER connected terminal
                    other_element_id = None
                    other_terminal_name = None
                    if wire_object['start_element_id'] == element_to_delete['id']:
                        other_element_id = wire_object['end_element_id']
                        other_terminal_name = wire_object['end_terminal_name']
                    else:
                        other_element_id = wire_object['start_element_id']
                        other_terminal_name = wire_object['start_terminal_name']
                    
                    other_element = next((el for el in self.circuit_elements_on_canvas if el["id"] == other_element_id), None)
                    if other_element and other_element['id'] != element_to_delete['id']: # Ensure other element is not the one being deleted
                        other_terminal = next((term for term in other_element.get("terminals", []) if term["name"] == other_terminal_name), None)
                        if other_terminal and wire_id_to_remove in other_terminal.get("connected_wire_ids", []):
                            other_terminal["connected_wire_ids"].remove(wire_id_to_remove)
                    
                    # Remove wire from the main list
                    if wire_object_idx != -1:
                        self.wires_on_canvas.pop(wire_object_idx)
            # --- End Wire Deletion Logic ---

            # Delete all associated graphical items from the canvas
            for item_id in element_to_delete.get("canvas_item_ids", []):
                self.editor_canvas.delete(item_id)
            # Remove the element from the internal list
            self.circuit_elements_on_canvas.pop(element_index)
            print(f"Elemento '{self.currently_selected_element_id}' deletado.")
            self.currently_selected_element_id = None # Clear selection
        else:
            # This case should ideally not happen if currently_selected_element_id is valid
            print(f"Erro: Elemento selecionado com ID '{self.currently_selected_element_id}' não encontrado na lista para deleção.")
            self.currently_selected_element_id = None # Clear the invalid selection ID

    def _delete_selected_wire(self):
        if self.currently_selected_wire_id is None:
            print("Nenhum fio selecionado para deletar.")
            return

        wire_to_delete = None
        wire_index = -1
        for i, w_obj in enumerate(self.wires_on_canvas):
            if w_obj["id"] == self.currently_selected_wire_id:
                wire_to_delete = w_obj
                wire_index = i
                break
        
        if wire_to_delete:
            # 1. Delete visual wire from canvas
            self.editor_canvas.delete(wire_to_delete['canvas_line_id'])

            # 2. Remove wire reference from connected terminals
            # Start terminal
            start_el = next((el for el in self.circuit_elements_on_canvas if el["id"] == wire_to_delete['start_element_id']), None)
            if start_el:
                start_term = next((t for t in start_el.get("terminals", []) if t["name"] == wire_to_delete['start_terminal_name']), None)
                if start_term and wire_to_delete['id'] in start_term.get("connected_wire_ids", []):
                    start_term["connected_wire_ids"].remove(wire_to_delete['id'])
            
            # End terminal
            end_el = next((el for el in self.circuit_elements_on_canvas if el["id"] == wire_to_delete['end_element_id']), None)
            if end_el:
                end_term = next((t for t in end_el.get("terminals", []) if t["name"] == wire_to_delete['end_terminal_name']), None)
                if end_term and wire_to_delete['id'] in end_term.get("connected_wire_ids", []):
                    end_term["connected_wire_ids"].remove(wire_to_delete['id'])
            
            # 3. Remove wire from the main list
            self.wires_on_canvas.pop(wire_index)
            
            print(f"Fio '{self.currently_selected_wire_id}' deletado.")
            self.currently_selected_wire_id = None # Clear selection
        else:
            print(f"Erro: Fio selecionado com ID '{self.currently_selected_wire_id}' não encontrado na lista para deleção.")
            self.currently_selected_wire_id = None

    def _select_tool(self, tool_type):
        self.selected_component_tool = tool_type
        print(f"Ferramenta selecionada: {self.selected_component_tool}")
        # Optional: Update UI to show selected tool (e.g., change button color, cursor)
    def _add_element_on_canvas(self, x, y): # x, y are already snapped
        # Deselect any currently selected element when trying to add a new one
        if self.currently_selected_element_id:
            self._deselect_all_elements()
            

        if self.selected_component_tool is None or self.selected_component_tool == "WIRE": # Wire handled differently
            if self.selected_component_tool == "WIRE":
                print("Modo Fio selecionado - lógica de desenho de fio a ser implementada.")
            return

        # x, y are now passed as arguments, already snapped
        element_id_str = f"{self.selected_component_tool.lower()}_{self.next_element_id}"
        self.next_element_id += 1

        # Define default values for properties
        default_value = "1" # Generic default, should be overridden
        if self.selected_component_tool == "RESISTOR": default_value = "1kΩ"
        elif self.selected_component_tool == "CAPACITOR": default_value = "1µF"
        elif self.selected_component_tool == "INDUCTOR": default_value = "1mH"
        elif self.selected_component_tool == "VS": default_value = "10V" # Example, could be "10V 0deg"
        elif self.selected_component_tool == "IS": default_value = "1A"  # Example, could be "1A 0deg"
        elif self.selected_component_tool == "GND": default_value = "" # GND has no value label
        elif self.selected_component_tool == "VCVS": default_value = "2.0" # Default gain
        elif self.selected_component_tool == "VCCS": default_value = "0.1" # Default Gm
        elif self.selected_component_tool == "CCVS": default_value = "10"  # Default Rm


        canvas_item_ids = []
        terminals_data = [] # Initialize to empty list

        if self.selected_component_tool == "RESISTOR":
            canvas_item_ids, terminals_data = self._draw_resistor(x, y, element_id_str)
        elif self.selected_component_tool == "CAPACITOR":
            canvas_item_ids, terminals_data = self._draw_capacitor(x, y, element_id_str)
        elif self.selected_component_tool == "INDUCTOR":
            canvas_item_ids, terminals_data = self._draw_inductor(x, y, element_id_str)
        elif self.selected_component_tool == "VS":
            canvas_item_ids, terminals_data = self._draw_voltage_source(x, y, element_id_str)
        elif self.selected_component_tool == "IS":
            canvas_item_ids, terminals_data = self._draw_current_source(x, y, element_id_str)
        elif self.selected_component_tool == "GND":
            canvas_item_ids, terminals_data = self._draw_ground(x, y, element_id_str)
        elif self.selected_component_tool == "VCVS":
            canvas_item_ids, terminals_data = self._draw_vcvs(x, y, element_id_str)
        elif self.selected_component_tool == "VCCS":
            canvas_item_ids, terminals_data = self._draw_vccs(x, y, element_id_str)
        elif self.selected_component_tool == "CCVS":
            canvas_item_ids, terminals_data = self._draw_ccvs(x, y, element_id_str)
        elif self.selected_component_tool == "CCCS":
            canvas_item_ids, terminals_data = self._draw_cccs(x, y, element_id_str)

        if canvas_item_ids: # If symbol items were drawn
            new_element = {
                "id": element_id_str,
                "type": self.selected_component_tool,
                "x": x, 
                "y": y,
                "canvas_item_ids": canvas_item_ids, # Now includes all visual parts including terminals
                "terminals": terminals_data,       # Stores the list of terminal information
                "properties": {} # Initialize empty, will be populated below
            }
            if self.selected_component_tool in ["VCVS", "VCCS"]:
                new_element["properties"] = {"value": default_value, "ctrl_node_p": "?", "ctrl_node_n": "?", "label_id": None}
            elif self.selected_component_tool == "CCVS":
                new_element["properties"] = {"value": default_value, "control_source_name": "VS_ctrl?", "label_id": None}
            elif self.selected_component_tool == "CCCS":
                new_element["properties"] = {"value": default_value, "control_source_name": "VS_monitor?", "label_id": None} # Default Beta = 100
            else:
                new_element["properties"] = {"value": default_value, "label_id": None}

            # Add to list BEFORE drawing the label, as _update_element_label looks it up
            self.circuit_elements_on_canvas.append(new_element) 

            if new_element['type'] not in ["GND"]: # Don't draw value label for GND
                 self._update_element_label(new_element['id']) # Draw the initial value label
            
            print(f"Adicionado: {new_element}")

        self.selected_component_tool = None # Resetar ferramenta após adicionar
        print("Ferramenta resetada.")

    def _update_element_label(self, element_id):
        element = next((el for el in self.circuit_elements_on_canvas if el["id"] == element_id), None)
        if not element or 'properties' not in element or 'value' not in element['properties']:
            print(f"Erro: Elemento '{element_id}' ou suas propriedades não encontradas para atualizar rótulo.")
            return

        current_label_id = element['properties'].get('label_id')
        
        text_to_display = ""
        if element['type'] in ["RESISTOR", "CAPACITOR", "INDUCTOR"]:
            text_to_display = str(element['properties'].get('value', ''))
        elif element['type'] in ["VS", "IS"]:
            mag = element['properties'].get('value', '')
            # Phase display could be added if 'phase' property exists
            text_to_display = str(mag)
        elif element['type'] == "VCVS":
            text_to_display = f"E: Ganho={element['properties'].get('value', '?')}" # Display gain for VCVS
        elif element['type'] == "VCCS":
            text_to_display = f"G: Gm={element['properties'].get('value', '?')}S" # Display Gm for VCCS
        elif element['type'] == "CCVS":
            rm_val = element['properties'].get('value', '?')
            ctrl_src = element['properties'].get('control_source_name', '?')
            text_to_display = f"H: Rm={rm_val}Ω\nCtrl: {ctrl_src}" # Display Rm and control source for CCVS
        elif element['type'] == "CCCS":
            beta_val = element['properties'].get('value', '?')
            ctrl_src = element['properties'].get('control_source_name', '?')
            text_to_display = f"F: Beta={beta_val}\nCtrl: {ctrl_src}" # Display Beta and control source for CCCS

        # Check if the current_label_id is valid and exists on canvas
        if current_label_id is not None and self.editor_canvas.find_withtag(str(current_label_id)): # Ensure tag is string
            self.editor_canvas.itemconfig(current_label_id, text=text_to_display)
        elif text_to_display: # Create new label only if there's text to display
            # Position the label relative to the element's center (x, y)
            label_x = element['x'] # For multi-line, consider if x needs adjustment or use justify
            label_y = element['y'] + 20 # Example: 20px below the center of the symbol

            new_label_id = self.editor_canvas.create_text(
                label_x, label_y,
                text=text_to_display, # Use text_to_display here
                tags=(element_id, "property_label", str(element_id)+"_prop_label"), # Ensure unique tag for label
                anchor="n" # Anchor to the north (top center of the text)
            )
            element['properties']['label_id'] = new_label_id
            # Add the new label item ID to the element's list of canvas items so it moves with the component
            if new_label_id not in element['canvas_item_ids']: # Avoid duplicates if logic ever re-runs
                element['canvas_item_ids'].append(new_label_id)

    def _on_delete_key_press(self, event):
        # The 'event' argument is passed by Tkinter but not used in this method.
        print("Tecla Delete pressionada.") # For debugging
        if self.currently_selected_element_id is not None:
            self._delete_selected_element()
        elif self.currently_selected_wire_id is not None:
            self._delete_selected_wire()
        else:
            print("Nada selecionado para deletar.")

    def _draw_resistor(self, x, y, element_id_tag):
        size_w, size_h = 60, 20; term_len = 5
        all_visual_item_ids = []
        terminals_data = []

        # 1. Draw resistor body
        body_id = self.editor_canvas.create_rectangle(
            x - size_w // 2, y - size_h // 2, x + size_w // 2, y + size_h // 2,
            outline=self.default_outline_color, fill="white", tags=(element_id_tag, "component_symbol", "RESISTOR"))
        all_visual_item_ids.append(body_id)

        # 2. Type Label "R"
        label_id = self.editor_canvas.create_text(x, y, text="R", tags=(element_id_tag, "label", "RESISTOR_label"))
        all_visual_item_ids.append(label_id)

        # 3. Terminals and Legs
        # Terminal 1 (Left)
        term1_x_offset = -(size_w / 2 + term_len + self.terminal_radius)
        term1_y_offset = 0
        term1_abs_x, term1_abs_y = x + term1_x_offset, y + term1_y_offset
        term1_canvas_id = self.editor_canvas.create_oval(
            term1_abs_x - self.terminal_radius, term1_abs_y - self.terminal_radius,
            term1_abs_x + self.terminal_radius, term1_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "T1", "connectable")
        )
        all_visual_item_ids.append(term1_canvas_id)
        terminals_data.append({
            "name": "T1", "x_offset": term1_x_offset, "y_offset": term1_y_offset,
            "canvas_item_id": term1_canvas_id, "connected_wire_ids": []
        })
        leg1_id = self.editor_canvas.create_line(
            x - size_w // 2, y, term1_abs_x + self.terminal_radius, term1_abs_y, # Connects body to edge of terminal circle
            fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg1_id)

        # Terminal 2 (Right)
        term2_x_offset = (size_w / 2 + term_len + self.terminal_radius)
        term2_y_offset = 0
        term2_abs_x, term2_abs_y = x + term2_x_offset, y + term2_y_offset
        term2_canvas_id = self.editor_canvas.create_oval(
            term2_abs_x - self.terminal_radius, term2_abs_y - self.terminal_radius,
            term2_abs_x + self.terminal_radius, term2_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "T2", "connectable")
        )
        all_visual_item_ids.append(term2_canvas_id)
        terminals_data.append({
            "name": "T2", "x_offset": term2_x_offset, "y_offset": term2_y_offset,
            "canvas_item_id": term2_canvas_id, "connected_wire_ids": []
        })
        leg2_id = self.editor_canvas.create_line(
            x + size_w // 2, y, term2_abs_x - self.terminal_radius, term2_abs_y, # Connects body to edge of terminal circle
            fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg2_id)
        
        return all_visual_item_ids, terminals_data

    def _draw_capacitor(self, x, y, element_id_tag):
        plate_w, plate_gap, plate_h = 15, 8, 20; term_len = 15
        all_visual_item_ids = []
        terminals_data = []

        # Capacitor Plates
        plate1_id = self.editor_canvas.create_line(x - plate_gap // 2, y - plate_h // 2, x - plate_gap // 2, y + plate_h // 2, width=2, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol", "CAPACITOR"))
        all_visual_item_ids.append(plate1_id)
        plate2_id = self.editor_canvas.create_line(x + plate_gap // 2, y - plate_h // 2, x + plate_gap // 2, y + plate_h // 2, width=2, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol", "CAPACITOR"))
        all_visual_item_ids.append(plate2_id)

        # Type label 'C' is drawn above the component
        label_id = self.editor_canvas.create_text(x, y - plate_h, text="C", tags=(element_id_tag, "label", "CAPACITOR_label"))
        all_visual_item_ids.append(label_id)

        # Terminals and Legs
        # Terminal 1 (Left)
        term1_x_offset = -(plate_gap / 2 + term_len + self.terminal_radius)
        term1_y_offset = 0
        term1_abs_x, term1_abs_y = x + term1_x_offset, y + term1_y_offset
        term1_canvas_id = self.editor_canvas.create_oval(
            term1_abs_x - self.terminal_radius, term1_abs_y - self.terminal_radius,
            term1_abs_x + self.terminal_radius, term1_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "T1", "connectable"))
        all_visual_item_ids.append(term1_canvas_id)
        terminals_data.append({"name": "T1", "x_offset": term1_x_offset, "y_offset": term1_y_offset, "canvas_item_id": term1_canvas_id, "connected_wire_ids": []})
        leg1_id = self.editor_canvas.create_line(x - plate_gap // 2, y, term1_abs_x + self.terminal_radius, term1_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg1_id)

        # Terminal 2 (Right)
        term2_x_offset = (plate_gap / 2 + term_len + self.terminal_radius)
        term2_y_offset = 0
        term2_abs_x, term2_abs_y = x + term2_x_offset, y + term2_y_offset
        term2_canvas_id = self.editor_canvas.create_oval(
            term2_abs_x - self.terminal_radius, term2_abs_y - self.terminal_radius,
            term2_abs_x + self.terminal_radius, term2_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "T2", "connectable"))
        all_visual_item_ids.append(term2_canvas_id)
        terminals_data.append({"name": "T2", "x_offset": term2_x_offset, "y_offset": term2_y_offset, "canvas_item_id": term2_canvas_id, "connected_wire_ids": []})
        leg2_id = self.editor_canvas.create_line(x + plate_gap // 2, y, term2_abs_x - self.terminal_radius, term2_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg2_id)

        return all_visual_item_ids, terminals_data

    def _draw_inductor(self, x, y, element_id_tag):
        num_loops = 3; loop_radius = 8; total_width = num_loops * loop_radius * 1.5; term_len = 5
        all_visual_item_ids = []
        terminals_data = []

        # Inductor Loops
        start_x_body = x - total_width / 2
        for i in range(num_loops):
            cx = start_x_body + i * (loop_radius * 1.5) + loop_radius / 2
            arc_id = self.editor_canvas.create_arc(
                cx - loop_radius, y - loop_radius, cx + loop_radius, y + loop_radius,
                start=0, extent=180, style=tk.ARC, outline=self.default_outline_color, width=1.5, tags=(element_id_tag, "component_symbol", "INDUCTOR"))
            all_visual_item_ids.append(arc_id)
        
        # Type label 'L'
        label_id = self.editor_canvas.create_text(x, y - loop_radius - 5, text="L", tags=(element_id_tag, "label", "INDUCTOR_label"))
        all_visual_item_ids.append(label_id)

        # Terminals and Legs
        # Terminal 1 (Left)
        term1_x_offset = -(total_width / 2 + term_len + self.terminal_radius)
        term1_y_offset = 0
        term1_abs_x, term1_abs_y = x + term1_x_offset, y + term1_y_offset
        term1_canvas_id = self.editor_canvas.create_oval(
            term1_abs_x - self.terminal_radius, term1_abs_y - self.terminal_radius,
            term1_abs_x + self.terminal_radius, term1_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "T1", "connectable"))
        all_visual_item_ids.append(term1_canvas_id)
        terminals_data.append({"name": "T1", "x_offset": term1_x_offset, "y_offset": term1_y_offset, "canvas_item_id": term1_canvas_id, "connected_wire_ids": []})
        leg1_id = self.editor_canvas.create_line(start_x_body, y, term1_abs_x + self.terminal_radius, term1_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg1_id)

        # Terminal 2 (Right)
        term2_x_offset = (total_width / 2 + term_len + self.terminal_radius)
        term2_y_offset = 0
        term2_abs_x, term2_abs_y = x + term2_x_offset, y + term2_y_offset
        term2_canvas_id = self.editor_canvas.create_oval(
            term2_abs_x - self.terminal_radius, term2_abs_y - self.terminal_radius,
            term2_abs_x + self.terminal_radius, term2_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "T2", "connectable"))
        all_visual_item_ids.append(term2_canvas_id)
        terminals_data.append({"name": "T2", "x_offset": term2_x_offset, "y_offset": term2_y_offset, "canvas_item_id": term2_canvas_id, "connected_wire_ids": []})
        leg2_id = self.editor_canvas.create_line(start_x_body + total_width, y, term2_abs_x - self.terminal_radius, term2_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg2_id)

        return all_visual_item_ids, terminals_data

    def _draw_voltage_source(self, x, y, element_id_tag):
        body_radius = 15; term_len = 10
        all_visual_item_ids = []
        terminals_data = []

        # Source Body
        body_id = self.editor_canvas.create_oval(x - body_radius, y - body_radius, x + body_radius, y + body_radius, outline=self.default_outline_color, fill="white", tags=(element_id_tag, "component_symbol", "VS"))
        all_visual_item_ids.append(body_id)
        plus_id = self.editor_canvas.create_text(x, y - body_radius / 3, text="+", font=("Arial", 10), tags=(element_id_tag, "label_detail", "VS_label"))
        all_visual_item_ids.append(plus_id)
        minus_id = self.editor_canvas.create_text(x, y + body_radius / 3, text="-", font=("Arial", 12), tags=(element_id_tag, "label_detail", "VS_label"))
        all_visual_item_ids.append(minus_id)

        # Terminals and Legs
        # Terminal 1 (Positive, Top)
        term1_name = "P"
        term1_x_offset = 0
        term1_y_offset = -(body_radius + term_len + self.terminal_radius)
        term1_abs_x, term1_abs_y = x + term1_x_offset, y + term1_y_offset
        term1_canvas_id = self.editor_canvas.create_oval(
            term1_abs_x - self.terminal_radius, term1_abs_y - self.terminal_radius,
            term1_abs_x + self.terminal_radius, term1_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", term1_name, "connectable"))
        all_visual_item_ids.append(term1_canvas_id)
        terminals_data.append({"name": term1_name, "x_offset": term1_x_offset, "y_offset": term1_y_offset, "canvas_item_id": term1_canvas_id, "connected_wire_ids": []})
        leg1_id = self.editor_canvas.create_line(x, y - body_radius, term1_abs_x, term1_abs_y + self.terminal_radius, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg1_id)

        # Terminal 2 (Negative, Bottom)
        term2_name = "N"
        term2_x_offset = 0
        term2_y_offset = (body_radius + term_len + self.terminal_radius)
        term2_abs_x, term2_abs_y = x + term2_x_offset, y + term2_y_offset
        term2_canvas_id = self.editor_canvas.create_oval(
            term2_abs_x - self.terminal_radius, term2_abs_y - self.terminal_radius,
            term2_abs_x + self.terminal_radius, term2_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", term2_name, "connectable"))
        all_visual_item_ids.append(term2_canvas_id)
        terminals_data.append({"name": term2_name, "x_offset": term2_x_offset, "y_offset": term2_y_offset, "canvas_item_id": term2_canvas_id, "connected_wire_ids": []})
        leg2_id = self.editor_canvas.create_line(x, y + body_radius, term2_abs_x, term2_abs_y - self.terminal_radius, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg2_id)

        return all_visual_item_ids, terminals_data

    def _draw_current_source(self, x, y, element_id_tag):
        body_radius = 15; term_len = 10; arrow_len = body_radius * 0.6
        all_visual_item_ids = []
        terminals_data = []

        # Source Body
        body_id = self.editor_canvas.create_oval(x - body_radius, y - body_radius, x + body_radius, y + body_radius, outline=self.default_outline_color, fill="white", tags=(element_id_tag, "component_symbol", "IS"))
        all_visual_item_ids.append(body_id)
        arrow_id = self.editor_canvas.create_line(x, y + arrow_len / 2, x, y - arrow_len / 2, arrow=tk.LAST, fill=self.default_outline_color, tags=(element_id_tag, "label_detail", "IS_label"))
        all_visual_item_ids.append(arrow_id)

        # Terminals and Legs
        # Terminal 1 (Output, Top)
        term1_name = "OUT"
        term1_x_offset = 0
        term1_y_offset = -(body_radius + term_len + self.terminal_radius)
        term1_abs_x, term1_abs_y = x + term1_x_offset, y + term1_y_offset
        term1_canvas_id = self.editor_canvas.create_oval(
            term1_abs_x - self.terminal_radius, term1_abs_y - self.terminal_radius,
            term1_abs_x + self.terminal_radius, term1_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", term1_name, "connectable"))
        all_visual_item_ids.append(term1_canvas_id)
        terminals_data.append({"name": term1_name, "x_offset": term1_x_offset, "y_offset": term1_y_offset, "canvas_item_id": term1_canvas_id, "connected_wire_ids": []})
        leg1_id = self.editor_canvas.create_line(x, y - body_radius, term1_abs_x, term1_abs_y + self.terminal_radius, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg1_id)

        # Terminal 2 (Input, Bottom)
        term2_name = "IN"
        term2_x_offset = 0
        term2_y_offset = (body_radius + term_len + self.terminal_radius)
        term2_abs_x, term2_abs_y = x + term2_x_offset, y + term2_y_offset
        term2_canvas_id = self.editor_canvas.create_oval(
            term2_abs_x - self.terminal_radius, term2_abs_y - self.terminal_radius,
            term2_abs_x + self.terminal_radius, term2_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", term2_name, "connectable"))
        all_visual_item_ids.append(term2_canvas_id)
        terminals_data.append({"name": term2_name, "x_offset": term2_x_offset, "y_offset": term2_y_offset, "canvas_item_id": term2_canvas_id, "connected_wire_ids": []})
        leg2_id = self.editor_canvas.create_line(x, y + body_radius, term2_abs_x, term2_abs_y - self.terminal_radius, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg2_id)

        return all_visual_item_ids, terminals_data

    def _draw_ground(self, x, y, element_id_tag):
        all_visual_item_ids = []
        terminals_data = []
        connection_point_y_offset = -10 # Relative to y, this is where the symbol connects

        # Ground symbol lines
        all_visual_item_ids.append(self.editor_canvas.create_line(x, y + connection_point_y_offset, x, y, width=1.5, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol", "GND")))
        all_visual_item_ids.append(self.editor_canvas.create_line(x - 10, y, x + 10, y, width=1.5, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol", "GND")))
        all_visual_item_ids.append(self.editor_canvas.create_line(x - 6, y + 3, x + 6, y + 3, width=1.5, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol", "GND")))
        all_visual_item_ids.append(self.editor_canvas.create_line(x - 3, y + 6, x + 3, y + 6, width=1.5, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol", "GND")))

        # Terminal
        term1_name = "T1"
        # The terminal circle is centered self.terminal_radius above the connection_point_y_offset
        term1_x_offset = 0
        term1_y_offset = connection_point_y_offset - self.terminal_radius 
        term1_abs_x, term1_abs_y = x + term1_x_offset, y + term1_y_offset
        
        term1_canvas_id = self.editor_canvas.create_oval(
            term1_abs_x - self.terminal_radius, term1_abs_y - self.terminal_radius,
            term1_abs_x + self.terminal_radius, term1_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", term1_name, "connectable"))
        all_visual_item_ids.append(term1_canvas_id)
        terminals_data.append({"name": term1_name, "x_offset": term1_x_offset, "y_offset": term1_y_offset, "canvas_item_id": term1_canvas_id, "connected_wire_ids": []})
        
        # Leg connecting the symbol's connection point to the terminal circle
        # The symbol's connection point is at (x, y + connection_point_y_offset)
        # The terminal circle's bottom edge is at (term1_abs_x, term1_abs_y + self.terminal_radius)
        leg1_id = self.editor_canvas.create_line(
            x, y + connection_point_y_offset, 
            term1_abs_x, term1_abs_y + self.terminal_radius, 
            fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_item_ids.append(leg1_id)

        return all_visual_item_ids, terminals_data

    def _draw_vcvs(self, x, y, element_id_tag):
        size = 20 # Metade da diagonal maior/menor do losango
        term_len = 10 # Comprimento da perna do terminal
        # self.terminal_radius is already defined
        all_visual_ids = []
        terminals_data = []

        # Corpo do Losango
        points = [x, y - size, x + size, y, x, y + size, x - size, y]
        body_id = self.editor_canvas.create_polygon(points, outline=self.default_outline_color, fill="white", width=2, tags=(element_id_tag, "component_symbol", "VCVS"))
        all_visual_ids.append(body_id)

        # Type Label "E" (for VCVS)
        type_label_id = self.editor_canvas.create_text(x, y, text="E", font=("Arial", 10, "bold"), tags=(element_id_tag, "label_detail", "VCVS_type_label"))
        all_visual_ids.append(type_label_id)

        # Terminal de Saída Positivo (OUT+) - Ex: Direita
        term_out_p_x_offset = size + term_len + self.terminal_radius # Adjusted for terminal radius
        term_out_p_y_offset = 0
        term_out_p_abs_x, term_out_p_abs_y = x + term_out_p_x_offset, y + term_out_p_y_offset
        # Linha da perna
        leg_out_p_id = self.editor_canvas.create_line(x + size, y, term_out_p_abs_x - self.terminal_radius, term_out_p_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_ids.append(leg_out_p_id)
        # Círculo do terminal
        term_out_p_canvas_id = self.editor_canvas.create_oval(
            term_out_p_abs_x - self.terminal_radius, term_out_p_abs_y - self.terminal_radius,
            term_out_p_abs_x + self.terminal_radius, term_out_p_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "OUT+", "connectable"))
        all_visual_ids.append(term_out_p_canvas_id)
        terminals_data.append({"name": "OUT+", "x_offset": term_out_p_x_offset, "y_offset": term_out_p_y_offset, "canvas_item_id": term_out_p_canvas_id, "connected_wire_ids": []})

        # Terminal de Saída Negativo (OUT-) - Ex: Esquerda
        term_out_n_x_offset = -(size + term_len + self.terminal_radius) # Adjusted for terminal radius
        term_out_n_y_offset = 0
        term_out_n_abs_x, term_out_n_abs_y = x + term_out_n_x_offset, y + term_out_n_y_offset
        # Linha da perna
        leg_out_n_id = self.editor_canvas.create_line(x - size, y, term_out_n_abs_x + self.terminal_radius, term_out_n_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_ids.append(leg_out_n_id)
        # Círculo do terminal
        term_out_n_canvas_id = self.editor_canvas.create_oval(
            term_out_n_abs_x - self.terminal_radius, term_out_n_abs_y - self.terminal_radius,
            term_out_n_abs_x + self.terminal_radius, term_out_n_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "OUT-", "connectable"))
        all_visual_ids.append(term_out_n_canvas_id)
        terminals_data.append({"name": "OUT-", "x_offset": term_out_n_x_offset, "y_offset": term_out_n_y_offset, "canvas_item_id": term_out_n_canvas_id, "connected_wire_ids": []})

        return all_visual_ids, terminals_data

    def _draw_vccs(self, x, y, element_id_tag):
        size = 20 # Metade da diagonal
        term_len = 10
        # self.terminal_radius is already defined
        all_visual_ids = []
        terminals_data = []

        # Corpo do Losango
        points = [x, y - size, x + size, y, x, y + size, x - size, y]
        body_id = self.editor_canvas.create_polygon(points, outline=self.default_outline_color, fill="white", width=2, tags=(element_id_tag, "component_symbol", "VCCS"))
        all_visual_ids.append(body_id)

        # Seta interna (ex: da esquerda para a direita, se corrente sai à direita)
        arrow_start_x, arrow_start_y = x - size * 0.6, y
        arrow_end_x, arrow_end_y = x + size * 0.6, y
        arrow_id = self.editor_canvas.create_line(
            arrow_start_x, arrow_start_y, arrow_end_x, arrow_end_y,
            arrow=tk.LAST, width=1.5, fill=self.default_outline_color, tags=(element_id_tag, "internal_symbol", "VCCS_arrow")
        )
        all_visual_ids.append(arrow_id)

        # Terminal de Saída (OUT) - Ex: Direita (onde a corrente sai da fonte)
        term_out_x_offset = size + term_len + self.terminal_radius
        term_out_y_offset = 0
        term_out_abs_x, term_out_abs_y = x + term_out_x_offset, y + term_out_y_offset
        leg_out_id = self.editor_canvas.create_line(x + size, y, term_out_abs_x - self.terminal_radius, term_out_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_ids.append(leg_out_id)
        term_out_canvas_id = self.editor_canvas.create_oval(
            term_out_abs_x - self.terminal_radius, term_out_abs_y - self.terminal_radius,
            term_out_abs_x + self.terminal_radius, term_out_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "OUT", "connectable"))
        all_visual_ids.append(term_out_canvas_id)
        terminals_data.append({"name": "OUT", "x_offset": term_out_x_offset, "y_offset": term_out_y_offset, "canvas_item_id": term_out_canvas_id, "connected_wire_ids": []})

        # Terminal de Entrada (IN) - Ex: Esquerda (onde a corrente entra na fonte vinda do circuito)
        term_in_x_offset = -(size + term_len + self.terminal_radius)
        term_in_y_offset = 0
        term_in_abs_x, term_in_abs_y = x + term_in_x_offset, y + term_in_y_offset
        leg_in_id = self.editor_canvas.create_line(x - size, y, term_in_abs_x + self.terminal_radius, term_in_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_ids.append(leg_in_id)
        term_in_canvas_id = self.editor_canvas.create_oval(
            term_in_abs_x - self.terminal_radius, term_in_abs_y - self.terminal_radius,
            term_in_abs_x + self.terminal_radius, term_in_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "IN", "connectable"))
        all_visual_ids.append(term_in_canvas_id)
        terminals_data.append({"name": "IN", "x_offset": term_in_x_offset, "y_offset": term_in_y_offset, "canvas_item_id": term_in_canvas_id, "connected_wire_ids": []})

        return all_visual_ids, terminals_data

    def _draw_ccvs(self, x, y, element_id_tag):
        size = 20 # Metade da diagonal
        term_len = 10
        # self.terminal_radius is already defined
        all_visual_ids = []
        terminals_data = []

        # Corpo do Losango
        points = [x, y - size, x + size, y, x, y + size, x - size, y]
        body_id = self.editor_canvas.create_polygon(points, outline=self.default_outline_color, fill="white", width=2, tags=(element_id_tag, "component_symbol", "CCVS"))
        all_visual_ids.append(body_id)

        # Type Label "H" (for CCVS)
        type_label_id = self.editor_canvas.create_text(x, y, text="H", font=("Arial", 10, "bold"), tags=(element_id_tag, "label_detail", "CCVS_type_label"))
        all_visual_ids.append(type_label_id)

        # Terminal de Saída Positivo (OUT+) - Ex: Direita
        term_out_p_x_offset = size + term_len + self.terminal_radius
        term_out_p_y_offset = 0
        term_out_p_abs_x, term_out_p_abs_y = x + term_out_p_x_offset, y + term_out_p_y_offset
        leg_out_p_id = self.editor_canvas.create_line(x + size, y, term_out_p_abs_x - self.terminal_radius, term_out_p_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_ids.append(leg_out_p_id)
        term_out_p_canvas_id = self.editor_canvas.create_oval(
            term_out_p_abs_x - self.terminal_radius, term_out_p_abs_y - self.terminal_radius,
            term_out_p_abs_x + self.terminal_radius, term_out_p_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "OUT+", "connectable"))
        all_visual_ids.append(term_out_p_canvas_id)
        terminals_data.append({"name": "OUT+", "x_offset": term_out_p_x_offset, "y_offset": term_out_p_y_offset, "canvas_item_id": term_out_p_canvas_id, "connected_wire_ids": []})

        # Terminal de Saída Negativo (OUT-) - Ex: Esquerda
        term_out_n_x_offset = -(size + term_len + self.terminal_radius)
        term_out_n_y_offset = 0
        term_out_n_abs_x, term_out_n_abs_y = x + term_out_n_x_offset, y + term_out_n_y_offset
        leg_out_n_id = self.editor_canvas.create_line(x - size, y, term_out_n_abs_x + self.terminal_radius, term_out_n_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_ids.append(leg_out_n_id)
        term_out_n_canvas_id = self.editor_canvas.create_oval(
            term_out_n_abs_x - self.terminal_radius, term_out_n_abs_y - self.terminal_radius,
            term_out_n_abs_x + self.terminal_radius, term_out_n_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "OUT-", "connectable"))
        all_visual_ids.append(term_out_n_canvas_id)
        terminals_data.append({"name": "OUT-", "x_offset": term_out_n_x_offset, "y_offset": term_out_n_y_offset, "canvas_item_id": term_out_n_canvas_id, "connected_wire_ids": []})

        return all_visual_ids, terminals_data

    def _draw_cccs(self, x, y, element_id_tag):
        size = 20 # Metade da diagonal
        term_len = 10
        all_visual_ids = []
        terminals_data = []

        # Corpo do Losango
        points = [x, y - size, x + size, y, x, y + size, x - size, y]
        body_id = self.editor_canvas.create_polygon(points, outline=self.default_outline_color, fill="white", width=2, tags=(element_id_tag, "component_symbol", "CCCS"))
        all_visual_ids.append(body_id)

        # Seta interna (ex: da esquerda para a direita, se corrente sai à direita)
        # Assumindo que a corrente controlada flui de "IN" para "OUT" (convencional),
        # e "OUT" é o terminal de onde a corrente sai do componente.
        # Se "OUT" está à direita, a seta aponta para a direita.
        arrow_start_x, arrow_start_y = x - size * 0.6, y
        arrow_end_x, arrow_end_y = x + size * 0.6, y
        arrow_id = self.editor_canvas.create_line(
            arrow_start_x, arrow_start_y, arrow_end_x, arrow_end_y,
            arrow=tk.LAST, width=1.5, fill=self.default_outline_color, tags=(element_id_tag, "internal_symbol", "CCCS_arrow")
        )
        all_visual_ids.append(arrow_id)

        # Terminal de Saída (OUT) - Ex: Direita (onde a corrente sai da fonte)
        term_out_x_offset = size + term_len + self.terminal_radius
        term_out_y_offset = 0
        term_out_abs_x, term_out_abs_y = x + term_out_x_offset, y + term_out_y_offset
        leg_out_id = self.editor_canvas.create_line(x + size, y, term_out_abs_x - self.terminal_radius, term_out_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_ids.append(leg_out_id)
        term_out_canvas_id = self.editor_canvas.create_oval(
            term_out_abs_x - self.terminal_radius, term_out_abs_y - self.terminal_radius,
            term_out_abs_x + self.terminal_radius, term_out_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "OUT", "connectable"))
        all_visual_ids.append(term_out_canvas_id)
        terminals_data.append({"name": "OUT", "x_offset": term_out_x_offset, "y_offset": term_out_y_offset, "canvas_item_id": term_out_canvas_id, "connected_wire_ids": []})

        # Terminal de Entrada (IN) - Ex: Esquerda (onde a corrente entra na fonte vinda do circuito)
        term_in_x_offset = -(size + term_len + self.terminal_radius)
        term_in_y_offset = 0
        term_in_abs_x, term_in_abs_y = x + term_in_x_offset, y + term_in_y_offset
        leg_in_id = self.editor_canvas.create_line(x - size, y, term_in_abs_x + self.terminal_radius, term_in_abs_y, fill=self.default_outline_color, tags=(element_id_tag, "component_symbol"))
        all_visual_ids.append(leg_in_id)
        term_in_canvas_id = self.editor_canvas.create_oval(
            term_in_abs_x - self.terminal_radius, term_in_abs_y - self.terminal_radius,
            term_in_abs_x + self.terminal_radius, term_in_abs_y + self.terminal_radius,
            fill=self.terminal_fill_color, outline=self.terminal_outline_color, tags=(element_id_tag, "terminal", "IN", "connectable"))
        all_visual_ids.append(term_in_canvas_id)
        terminals_data.append({"name": "IN", "x_offset": term_in_x_offset, "y_offset": term_in_y_offset, "canvas_item_id": term_in_canvas_id, "connected_wire_ids": []})

        return all_visual_ids, terminals_data

    def _parse_numeric_value(self, value_str):
        value_str = str(value_str).strip().lower()
        original_value_for_error = value_str # Keep original for error return

        # Remove common units from the end to isolate prefix and number
        units_to_strip = ["kω", "ω", "kf", "f", "kh", "h",
                          "kohms", "ohms", "kfarads", "farads", "khenries", "henries",
                          "kv", "v", "ka", "a"]
        for unit in units_to_strip:
            if value_str.endswith(unit):
                value_str = value_str[:-len(unit)]
                break # Avoid stripping parts of prefixes like 'm' from 'mF' if 'F' is stripped first

        # More specific unit handling for single letter units after number
        # (e.g. 10u, 10m, 10k)
        # This part is tricky because 'm' can be milli or mega, 'k' is kilo.
        # The order of checks for suffixes is important.

        val_num_part = ""
        suffix = ""

        # Try to separate numeric part from potential single-letter suffix
        for i, char in enumerate(reversed(value_str)):
            if not char.isdigit() and char != '.':
                val_num_part = value_str[:len(value_str)-1-i]
                suffix = value_str[len(value_str)-1-i:]
                break
        if not suffix and value_str.replace('.', '', 1).isdigit(): # No suffix found, all numeric
            val_num_part = value_str
            suffix = ""
        elif not val_num_part and suffix: # Only suffix found (e.g. "k") - invalid
             return "VALOR_INVALIDO"
        elif not val_num_part and not suffix and value_str: # Non-empty, non-numeric, no suffix (e.g. "abc")
            return "VALOR_INVALIDO"
        elif not value_str: # Empty string
            return "VALOR_INVALIDO"


        multiplier = 1.0
        if suffix == 't': # Tera
            multiplier = 1e12
        elif suffix == 'g': # Giga
            multiplier = 1e9
        elif suffix == 'meg' or suffix == 'ma': # Mega (ma for mega-ohms sometimes)
            multiplier = 1e6
        elif suffix == 'k': # kilo
            multiplier = 1e3
        elif suffix == 'm': # milli
            multiplier = 1e-3
        elif suffix == 'u' or suffix == 'µ': # micro
            multiplier = 1e-6
        elif suffix == 'n': # nano
            multiplier = 1e-9
        elif suffix == 'p': # pico
            multiplier = 1e-12
        elif suffix == 'f': # femto
            multiplier = 1e-15
        elif suffix != "": # Unknown suffix if not empty
            # If suffix is not recognized, it might be part of the number or invalid
            # For now, assume it's invalid if it's not one of the above and not empty
            # This means "100ohms" would have "ohms" stripped, then "100" processed.
            # "100x" would have "x" as suffix and be invalid.
            # If suffix is empty, it's fine.
            pass

        try:
            val = float(val_num_part) * multiplier
            # Standard format for netlist values, avoid excessive precision for simple numbers
            if 1e-4 <= abs(val) < 1e7 and val == int(val):
                return f"{int(val)}"
            return f"{val:.6g}" # General format, scientific for large/small
        except ValueError:
            return "VALOR_INVALIDO"

    def _parse_source_ac_value(self, value_str, default_phase="0"):
        value_str = str(value_str).lower().replace("v", "").replace("a", "").replace("deg", "").strip()
        parts = re.split(r'\s+|,|\s*∠\s*', value_str) # Split by space, comma, or angle symbol
        parts = [p for p in parts if p] # Remove empty strings

        magnitude_str = "VALOR_INVALIDO"
        phase_str = default_phase

        if len(parts) >= 1:
            try:
                mag_val = float(parts[0])
                magnitude_str = f"{mag_val:.6g}"
            except ValueError:
                pass # magnitude_str remains VALOR_INVALIDO

        if len(parts) >= 2:
            try:
                phase_val = float(parts[1])
                phase_str = f"{phase_val:.6g}"
            except ValueError:
                pass # phase_str remains default_phase

        return magnitude_str, phase_str

    def _build_netlist_from_node_map(self, terminals_to_nodes_map):
        netlist_lines = ["* Netlist Gerada pelo Editor de Circuito Interativo"]
        element_counts = {} # To generate names like R1, R2, C1, etc.

        for element in self.circuit_elements_on_canvas:
            if element['type'] == "GND":
                continue

            type_prefix = element['type'][0].upper()
            if element['type'] == "VS" or element['type'] == "IS":
                type_prefix = element['type'] # VS, IS

            element_counts[type_prefix] = element_counts.get(type_prefix, 0) + 1
            component_name_for_netlist = f"{type_prefix}{element_counts[type_prefix]}"

            # Get node labels for terminals
            node_labels = []
            terminal_names_ordered = []
            if element['type'] in ["RESISTOR", "CAPACITOR", "INDUCTOR"]:
                terminal_names_ordered = ["T1", "T2"]
            elif element['type'] == "VS":
                terminal_names_ordered = ["P", "N"] # Positive, Negative
            elif element['type'] == "IS":
                terminal_names_ordered = ["OUT", "IN"] # Current exits OUT, enters IN
            elif element['type'] == "VCVS":
                terminal_names_ordered = ["OUT+", "OUT-"] # Output terminals
            elif element['type'] == "VCCS":
                terminal_names_ordered = ["OUT", "IN"] # Current exits OUT, enters IN
            elif element['type'] == "CCVS": 
                terminal_names_ordered = ["OUT+", "OUT-"] # Output terminals
            elif element['type'] == "CCCS": 
                terminal_names_ordered = ["OUT", "IN"] # Output current path for CCCS
            # Add more for controlled sources if they are drawn

            for term_name in terminal_names_ordered:
                terminal_key = (element['id'], term_name)
                node_label = terminals_to_nodes_map.get(terminal_key, f"NODO_DESCONHECIDO_{element['id']}_{term_name}")
                node_labels.append(node_label)

            if len(node_labels) < 2 and element['type'] not in ["GND"]: # Most components need at least 2 nodes
                netlist_lines.append(f"* ERRO: {component_name_for_netlist} ({element['id']}) - Terminais insuficientes ou não mapeados.")
                continue

            value_str_prop = str(element['properties'].get('value', 'VALOR_PADRAO'))
            line = ""

            if element['type'] in ["RESISTOR", "CAPACITOR", "INDUCTOR"]:
                parsed_val = self._parse_numeric_value(value_str_prop)
                line = f"{component_name_for_netlist} {node_labels[0]} {node_labels[1]} {parsed_val}"
            elif element['type'] == "VS":
                mag, phase = self._parse_source_ac_value(value_str_prop)
                line = f"{component_name_for_netlist} {node_labels[0]} {node_labels[1]} AC {mag} {phase}" # Node P, Node N
            elif element['type'] == "IS":
                mag, phase = self._parse_source_ac_value(value_str_prop)
                line = f"{component_name_for_netlist} {node_labels[0]} {node_labels[1]} AC {mag} {phase}" # Node OUT, Node IN
            elif element['type'] == "VCVS":
                gain_str = self._parse_numeric_value(element['properties'].get('value', '1')) # Gain
                ctrl_p_val = element['properties'].get('ctrl_node_p', 'NODO_CTRL_P_DESCONHECIDO')
                ctrl_n_val = element['properties'].get('ctrl_node_n', 'NODO_CTRL_N_DESCONHECIDO')
                if gain_str == "VALOR_INVALIDO" or "?" in ctrl_p_val or "?" in ctrl_n_val:
                    line = f"* ERRO_VCVS: {component_name_for_netlist} ({element['id']}) - Ganho ou nós de controle inválidos/não definidos. Ganho: {gain_str}, Ctrl+: {ctrl_p_val}, Ctrl-: {ctrl_n_val}"
                else:
                    line = f"{component_name_for_netlist} {node_labels[0]} {node_labels[1]} {ctrl_p_val} {ctrl_n_val} {gain_str}"
            elif element['type'] == "VCCS":
                gm_str = self._parse_numeric_value(element['properties'].get('value', '0.1')) # Gm
                ctrl_p_val = element['properties'].get('ctrl_node_p', 'NODO_CTRL_P_DESCONHECIDO')
                ctrl_n_val = element['properties'].get('ctrl_node_n', 'NODO_CTRL_N_DESCONHECIDO')
                if gm_str == "VALOR_INVALIDO" or "?" in ctrl_p_val or "?" in ctrl_n_val:
                    line = f"* ERRO_VCCS: {component_name_for_netlist} ({element['id']}) - Gm ou nós de controle inválidos/não definidos. Gm: {gm_str}, Ctrl+: {ctrl_p_val}, Ctrl-: {ctrl_n_val}"
                else:
                    line = f"{component_name_for_netlist} {node_labels[0]} {node_labels[1]} {ctrl_p_val} {ctrl_n_val} {gm_str}" # OUT, IN, CTRL+, CTRL-, Gm
            elif element['type'] == "CCVS":
                rm_str = self._parse_numeric_value(element['properties'].get('value', '10')) # Rm
                control_vs_name = element['properties'].get('control_source_name', 'VS_CONTROLE_DESCONHECIDO')
                if rm_str == "VALOR_INVALIDO" or "?" in control_vs_name or not control_vs_name.upper().startswith("VS"):
                    line = f"* ERRO_CCVS: {component_name_for_netlist} ({element['id']}) - Rm ou nome da fonte VS de controle inválidos/não definidos. Rm: {rm_str}, CtrlVS: {control_vs_name}"
                else:
                    # Netlist format: H<name> <out+> <out-> <VS_control_name> <Rm_value>
                    line = f"{component_name_for_netlist} {node_labels[0]} {node_labels[1]} {control_vs_name} {rm_str}"
            elif element['type'] == "CCCS":
                beta_str = self._parse_numeric_value(element['properties'].get('value', '100')) # Beta
                control_vs_name_cccs_prop = element['properties'].get('control_source_name', 'VS_CONTROLE_DESCONHECIDO')
                
                error_in_cccs = False
                if " " in control_vs_name_cccs_prop:
                    netlist_lines.append(f"* AVISO_CCCS: {component_name_for_netlist} ({element['id']}) - Nome da fonte de controle '{control_vs_name_cccs_prop}' contém espaços. Usando '{control_vs_name_cccs_prop.split(' ')[0]}'.")
                    control_vs_name_cccs_prop = control_vs_name_cccs_prop.split(" ")[0] # Attempt to fix
                if beta_str == "VALOR_INVALIDO" or "?" in control_vs_name_cccs_prop or not control_vs_name_cccs_prop.upper().startswith("VS"):
                    line = f"* ERRO_CCCS: {component_name_for_netlist} ({element['id']}) - Beta ou nome da fonte VS de controle inválidos/não definidos. Beta: {beta_str}, CtrlVS: {control_vs_name_cccs_prop}"
                else:
                    # Netlist format: F<name> <out> <in> <VS_control_name> <Beta_value>
                    line = f"{component_name_for_netlist} {node_labels[0]} {node_labels[1]} {control_vs_name_cccs_prop} {beta_str}"
            else:
                line = f"* TIPO_NAO_SUPORTADO_PARA_NETLIST: {component_name_for_netlist} ({element['type']})"

            netlist_lines.append(line)

        # Add Frequency line (optional, or from a dedicated input)
        # For now, let's assume it's taken from the manual frequency input as a fallback
        freq_val_str = self.freq_details_entry.get()
        parsed_freq = self._parse_numeric_value(freq_val_str if freq_val_str else "60") # Default to 60Hz if empty
        if parsed_freq != "VALOR_INVALIDO":
            netlist_lines.append(f"FREQ {parsed_freq}")
        else:
            netlist_lines.append(f"FREQ 60 * Frequência padrão, valor da entrada manual inválido: {freq_val_str}")

        return "\n".join(netlist_lines)

    def _display_netlist_dialog(self, netlist_string):
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Netlist Gerada")
        dialog.geometry("450x500")
        dialog.transient(self.master)

        textbox = ctk.CTkTextbox(dialog, wrap="word", font=ctk.CTkFont(family="monospace", size=11))
        textbox.pack(expand=True, fill="both", padx=10, pady=(10,5))
        textbox.insert("1.0", netlist_string)
        textbox.configure(state="disabled")

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(0,10))

        def copy_to_clipboard():
            self.master.clipboard_clear()
            self.master.clipboard_append(netlist_string)
            messagebox.showinfo("Copiado", "Netlist copiada para a área de transferência!", parent=dialog)

        def load_to_analyzer():
            self.netlist_textbox.delete("1.0", tk.END)
            self.netlist_textbox.insert("1.0", netlist_string)
            dialog.destroy()

        copy_button = ctk.CTkButton(button_frame, text="Copiar", command=copy_to_clipboard)
        copy_button.pack(side="left", padx=5, expand=True)

        load_button = ctk.CTkButton(button_frame, text="Carregar no Analisador", command=load_to_analyzer)
        load_button.pack(side="left", padx=5, expand=True)

        close_button = ctk.CTkButton(button_frame, text="Fechar", command=dialog.destroy)
        close_button.pack(side="left", padx=5, expand=True)

        # Delay grab_set until the window is likely viewable
        dialog.after(30, self._grab_toplevel_safely, dialog) # Adjusted delay, can be 50ms too
        dialog.after(50, dialog.lift) # Ensure it's on top
        dialog.after(100, self._center_toplevel_after_draw, dialog) # Center it

    def _initiate_netlist_generation(self):
        if not self.circuit_elements_on_canvas:
            messagebox.showinfo("Gerar Netlist", "O editor de circuito está vazio. Adicione componentes e fios para gerar uma netlist.")
            return

        terminals_to_nodes_map = self._discover_and_assign_nodes()

        if not terminals_to_nodes_map:
            messagebox.showerror("Erro na Netlist", "Falha ao descobrir ou mapear os nós do circuito.")
            return

        # Verificar se todos os terminais de todos os componentes (exceto GND) foram mapeados
        all_terminals_mapped_successfully = True
        for element in self.circuit_elements_on_canvas:
            if element['type'] == "GND":
                continue
            if not element.get('terminals'):
                messagebox.showerror("Erro na Netlist", f"Componente '{element['id']}' ({element['type']}) não possui terminais definidos na estrutura de dados interna.")
                all_terminals_mapped_successfully = False
                break
            for term_info in element['terminals']:
                if (element['id'], term_info['name']) not in terminals_to_nodes_map:
                    messagebox.showerror("Erro na Netlist", f"Terminal '{term_info['name']}' do componente '{element['id']}' ({element['type']}) não foi mapeado para um nó. Verifique conexões.")
                    all_terminals_mapped_successfully = False
                    break
            if not all_terminals_mapped_successfully:
                break

        if not all_terminals_mapped_successfully:
            return

        netlist_string = self._build_netlist_from_node_map(terminals_to_nodes_map)

        if "VALOR_INVALIDO" in netlist_string or "NODO_DESCONHECIDO" in netlist_string:
             messagebox.showwarning("Netlist Gerada com Avisos",
                                    "A netlist foi gerada, mas contém valores inválidos ou nós desconhecidos. "
                                    "Verifique os valores dos componentes e as conexões no editor.\n\n"
                                    "A netlist será exibida, mas pode não ser analisável.",
                                    parent=self.master) # Ensure warning is on top

        self._display_netlist_dialog(netlist_string)

    def _discover_and_assign_nodes(self):
        terminals_to_nodes_map = {}
        visited_terminals = set() # Tuplas: (element_id, terminal_name)
        current_node_label_counter = 1 # Começa em 1 para nós não-terra

        # Passo 1: Processar GND
        for element in self.circuit_elements_on_canvas:
            if element.get("type") == "GND":
                for terminal_gnd in element.get("terminals", []):
                    start_key = (element['id'], terminal_gnd['name'])
                    if start_key not in visited_terminals:
                        self._traverse_connected_terminals(element['id'], terminal_gnd['name'], "0", 
                                                           terminals_to_nodes_map, visited_terminals)
        
        # Passo 2: Processar terminais restantes
        for element in self.circuit_elements_on_canvas:
            # GND já foi processado e seus terminais adicionados a visited_terminals
            # Não precisamos pular o tipo GND aqui explicitamente, pois a checagem `if terminal_key not in visited_terminals`
            # cuidará disso se todos os terminais GND já foram visitados.
            for terminal_info in element.get("terminals", []):
                terminal_key = (element['id'], terminal_info['name'])
                if terminal_key not in visited_terminals:
                    current_node_label = str(current_node_label_counter)
                    self._traverse_connected_terminals(element['id'], terminal_info['name'], current_node_label,
                                                       terminals_to_nodes_map, visited_terminals)
                    current_node_label_counter += 1
                    
        return terminals_to_nodes_map

    def _traverse_connected_terminals(self, start_el_id, start_term_name, 
                                     node_label_to_assign, terminals_to_nodes_map, visited_terminals):
        
        queue = [(start_el_id, start_term_name)] # Usando BFS com uma lista como fila
        head = 0 # Pointer for the front of the queue

        while head < len(queue):
            current_el_id, current_term_name = queue[head]
            head += 1

            current_key = (current_el_id, current_term_name)
            if current_key in visited_terminals:
                continue
            
            visited_terminals.add(current_key)
            terminals_to_nodes_map[current_key] = node_label_to_assign

            current_element = next((el for el in self.circuit_elements_on_canvas if el["id"] == current_el_id), None)
            if not current_element: continue
            current_terminal_obj = next((term for term in current_element.get("terminals", []) if term["name"] == current_term_name), None)
            if not current_terminal_obj: continue

            for wire_id in current_terminal_obj.get("connected_wire_ids", []):
                wire = next((w for w in self.wires_on_canvas if w["id"] == wire_id), None)
                if not wire: continue

                other_el_id, other_term_name = (None, None)
                if wire['start_element_id'] == current_el_id and wire['start_terminal_name'] == current_term_name:
                    other_el_id = wire['end_element_id']
                    other_term_name = wire['end_terminal_name']
                elif wire['end_element_id'] == current_el_id and wire['end_terminal_name'] == current_term_name:
                    other_el_id = wire['start_element_id']
                    other_term_name = wire['start_terminal_name']
                
                if other_el_id and other_term_name:
                    other_key = (other_el_id, other_term_name)
                    if other_key not in visited_terminals:
                        # Check if already in queue to avoid redundant processing, though visited_terminals handles correctness
                        # For simple list queue, direct check is O(N). For now, rely on visited_terminals.
                        # If performance becomes an issue with very large connected components,
                        # a set for `in_queue` check alongside collections.deque could be used.
                        queue.append((other_el_id, other_term_name))

    def _prompt_load_diagram(self):
        """Opens a file dialog to ask the user to select a diagram file to load."""
        filepath = filedialog.askopenfilename(
            master=self.master,
            title="Carregar Diagrama",
            filetypes=[("Diagrama AC Analyzer JSON", "*.acdiag.json"),
                       ("Arquivos JSON", "*.json"),
                       ("Todos os Arquivos", "*.*")]
        )
        if not filepath:
            return  # User cancelled

        self._load_diagram_from_file(filepath)

    def _clear_editor_canvas_and_data(self):
        """Clears the entire state of the circuit editor canvas and its data structures."""
        # Delete all visual items from the canvas
        self.editor_canvas.delete("all")

        # Clear data structures
        self.circuit_elements_on_canvas = []
        self.wires_on_canvas = []

        # Reset selection states and ID counters
        self.currently_selected_element_id = None
        self.currently_selected_wire_id = None
        self.next_element_id = 0 # Will be overwritten by loaded file if successful
        self.next_wire_id = 0  # Will be overwritten by loaded file if successful

        # Reset wire drawing state
        # self.wire_preview_line_id is already deleted by canvas.delete("all")
        self.is_drawing_wire = False
        self.wire_start_info = None
        self.wire_preview_line_id = None

        print("Editor limpo e dados resetados.")

    def _load_diagram_from_file(self, filepath):
        """Loads a circuit diagram from a JSON file into the editor."""
        self._clear_editor_canvas_and_data() # Clear current editor state first

        try:
            with open(filepath, 'r') as f:
                diagram_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Erro ao Carregar Diagrama", f"Não foi possível carregar ou ler o arquivo do diagrama:\n{e}", parent=self.master)
            return

        # Restore ID counters
        self.next_element_id = diagram_data.get("next_element_id", 0)
        self.next_wire_id = diagram_data.get("next_wire_id", 0)

        # Recreate Elements
        elements_data_from_file = diagram_data.get("elements", [])
        for element_data in elements_data_from_file:
            element_id = element_data['id']
            element_type = element_data['type']
            x, y = element_data['x'], element_data['y']
            properties_data = element_data.get('properties', {}) # label_id is not in here
            terminals_structure_from_file = element_data.get('terminals', [])

            # Call the appropriate drawing function (these return new canvas IDs)
            draw_func_name = f"_draw_{element_type.lower()}"
            if hasattr(self, draw_func_name) and callable(getattr(self, draw_func_name)):
                draw_func = getattr(self, draw_func_name)
                all_new_visual_ids, new_terminals_data_with_canvas_ids = draw_func(x, y, element_id)
            else:
                messagebox.showwarning("Carregar Diagrama", f"Tipo de elemento desconhecido '{element_type}' encontrado no arquivo. Elemento '{element_id}' será ignorado.", parent=self.master)
                continue

            loaded_element = {
                "id": element_id, "type": element_type, "x": x, "y": y,
                "canvas_item_ids": all_new_visual_ids,
                "properties": properties_data, # Properties from file (value, etc.)
                "terminals": new_terminals_data_with_canvas_ids # Terminals with new canvas_item_ids
            }

            # Restore connected_wire_ids for each terminal
            for term_new_info in loaded_element["terminals"]:
                original_term_info = next((t_orig for t_orig in terminals_structure_from_file if t_orig["name"] == term_new_info["name"]), None)
                if original_term_info:
                    term_new_info["connected_wire_ids"] = original_term_info.get("connected_wire_ids", [])
                else: # Should not happen if data is consistent
                    term_new_info["connected_wire_ids"] = []

            self.circuit_elements_on_canvas.append(loaded_element)
            if loaded_element['type'] not in ["GND"]: # GND has no value label
                self._update_element_label(element_id) # This will create a new label_id in properties

        # Recreate Wires
        wires_data_from_file = diagram_data.get("wires", [])
        for wire_data in wires_data_from_file:
            wire_id = wire_data['id']
            start_el_id, start_term_name = wire_data['start_element_id'], wire_data['start_terminal_name']
            end_el_id, end_term_name = wire_data['end_element_id'], wire_data['end_terminal_name']

            start_coords = self._get_terminal_absolute_coords(start_el_id, start_term_name)
            end_coords = self._get_terminal_absolute_coords(end_el_id, end_term_name)

            if start_coords and end_coords:
                new_line_id = self.editor_canvas.create_line(start_coords[0], start_coords[1], end_coords[0], end_coords[1], fill=self.wire_default_color, width=2, tags=("wire", wire_id))
                self.wires_on_canvas.append({"id": wire_id, "start_element_id": start_el_id, "start_terminal_name": start_term_name, "end_element_id": end_el_id, "end_terminal_name": end_term_name, "canvas_line_id": new_line_id})
            else:
                messagebox.showwarning("Carregar Diagrama", f"Não foi possível recriar o fio '{wire_id}'. Terminais não encontrados.", parent=self.master)

        messagebox.showinfo("Carregar Diagrama", f"Diagrama carregado com sucesso de:\n{filepath}", parent=self.master)

    def _prompt_save_diagram_as(self):
        """Opens a file dialog to ask the user where to save the current diagram."""
        filepath = filedialog.asksaveasfilename(
            master=self.master, # Ensure dialog is parented to main window or a relevant toplevel
            title="Salvar Diagrama Como",
            defaultextension=".acdiag.json",
            filetypes=[("Diagrama AC Analyzer JSON", "*.acdiag.json"),
                       ("Arquivos JSON", "*.json"),
                       ("Todos os Arquivos", "*.*")]
        )
        if not filepath:
            return  # User cancelled

        self._save_diagram_to_file(filepath)

    def _save_diagram_to_file(self, filepath):
        """Saves the current state of the circuit diagram editor to a JSON file."""
        diagram_data = {
            "elements": [],
            "wires": [],
            "next_element_id": self.next_element_id,
            "next_wire_id": self.next_wire_id,
            # Future: "zoom_level": self.editor_canvas_zoom, "pan_offset": (self.pan_x, self.pan_y)
        }

        # Serialize Elements
        for element_orig in self.circuit_elements_on_canvas:
            element_copy = copy.deepcopy(element_orig)  # Use deepcopy to avoid modifying live data

            element_copy.pop('canvas_item_ids', None) # Remove list of visual Tkinter IDs

            if 'terminals' in element_copy and isinstance(element_copy['terminals'], list):
                for terminal_data in element_copy['terminals']: # terminal_data is a dict
                    terminal_data.pop('canvas_item_id', None) # Remove individual terminal's visual Tkinter ID

            if 'properties' in element_copy and isinstance(element_copy['properties'], dict):
                element_copy['properties'].pop('label_id', None) # Remove property label's Tkinter ID

            diagram_data["elements"].append(element_copy)

        # Serialize Wires
        for wire_orig in self.wires_on_canvas:
            wire_copy = copy.deepcopy(wire_orig) # Use deepcopy
            wire_copy.pop('canvas_line_id', None) # Remove wire's visual Tkinter ID
            diagram_data["wires"].append(wire_copy)

        try:
            with open(filepath, 'w') as f:
                json.dump(diagram_data, f, indent=4)
            messagebox.showinfo("Salvar Diagrama", f"Diagrama salvo com sucesso em:\n{filepath}", parent=self.master)
        except Exception as e:
            messagebox.showerror("Erro ao Salvar Diagrama", f"Não foi possível salvar o diagrama:\n{e}", parent=self.master)


    def _clear_waveforms_plot(self, initial_message=None, error_message=None):
        if not self.ax_waveforms: return # pragma: no cover
        
        # Surgical clear
        for line in list(self.ax_waveforms.get_lines()): # Iterate over a copy
            line.remove()
        # Clear and remove twin axis if it exists
        if hasattr(self, 'ax_waveforms_current_twin') and self.ax_waveforms_current_twin:
            if self.ax_waveforms_current_twin.figure: # Check if it's part of a figure
                self.fig_waveforms.delaxes(self.ax_waveforms_current_twin)
            self.ax_waveforms_current_twin = None

        if self.ax_waveforms.get_legend():
            self.ax_waveforms.get_legend().remove()
        for text_obj in list(self.ax_waveforms.texts): # Iterate over a copy
            text_obj.remove()
        
        bg_color = self._get_ctk_bg_color()
        text_color = self._get_ctk_text_color()
        self.ax_waveforms.set_facecolor(bg_color)
        self.fig_waveforms.patch.set_facecolor(bg_color)

        message_to_display = initial_message or "Aguardando dados..."
        title = "Formas de Onda no Tempo"
        if error_message:
            message_to_display = error_message
            text_color = 'red'

        self.ax_waveforms.text(0.5, 0.5, message_to_display, ha='center', va='center', fontsize=10, color=text_color, wrap=True)
        self.ax_waveforms.set_title(title, fontsize=12, color=text_color)
        self.ax_waveforms.set_xticks([])
        self.ax_waveforms.set_yticks([])
        self.ax_waveforms.grid(False)
        # try:
        #     self.fig_waveforms.tight_layout() # Not needed with constrained_layout
        # except Exception: pass # pragma: no cover
        if self.canvas_waveforms_figure_agg:
             self.canvas_waveforms_figure_agg.draw_idle()

    def _update_waveform_selection_ui(self):
        # Limpar widgets antigos do frame de controles
        for widget in self.scrollable_waveform_controls_area.winfo_children(): # Alterado para self.scrollable_waveform_controls_area
            widget.destroy()
        # self.waveform_selection_scroll_frames.clear() # Não é mais necessário

        # Preserve existing selections by not fully re-initializing self.waveform_selection_vars
        # Only initialize the sub-dictionaries if they don't exist
        if "nodal_voltages" not in self.waveform_selection_vars: self.waveform_selection_vars["nodal_voltages"] = {}
        if "component_currents" not in self.waveform_selection_vars: self.waveform_selection_vars["component_currents"] = {}
        if "component_voltages" not in self.waveform_selection_vars: self.waveform_selection_vars["component_voltages"] = {}
        if "three_phase_source_phase_voltages" not in self.waveform_selection_vars: self.waveform_selection_vars["three_phase_source_phase_voltages"] = {}
        if "three_phase_source_line_currents" not in self.waveform_selection_vars: self.waveform_selection_vars["three_phase_source_line_currents"] = {}
        if "three_phase_source_line_voltages" not in self.waveform_selection_vars: self.waveform_selection_vars["three_phase_source_line_voltages"] = {}

        if not self.analysis_performed_successfully or not self.analysis_results:
            ctk.CTkLabel(self.scrollable_waveform_controls_area, text="Execute uma análise para selecionar formas de onda.").pack(pady=10, anchor="w", padx=5)
            return

        # --- Controle de Número de Períodos ---
        periods_frame = ctk.CTkFrame(self.scrollable_waveform_controls_area, fg_color="transparent")
        periods_frame.pack(fill="x", padx=5, pady=(5,10)) # Added more pady bottom
        ctk.CTkLabel(periods_frame, text="Nº de Períodos:").pack(side="left", padx=(0,5))
        periods_entry = ctk.CTkEntry(periods_frame, textvariable=self.num_periods_to_plot_var, width=50)
        periods_entry.pack(side="left")
        
        # --- Controle de Visibilidade da Grade ---
        grid_toggle_cb = ctk.CTkCheckBox(
            self.scrollable_waveform_controls_area, # Adicionado ao frame rolável
            text="Mostrar Grade no Gráfico",
            variable=self.show_waveform_grid_var,
            command=self._plot_time_domain_waveforms # Re-plotar para aplicar a mudança
        )
        grid_toggle_cb.pack(anchor="w", padx=10, pady=5) # pady=5 para espaçamento

        # --- Botão Principal para Plotar ---
        ctk.CTkButton(self.scrollable_waveform_controls_area, text="Plotar Selecionadas", command=self._plot_time_domain_waveforms).pack(pady=(5,10), fill="x", padx=5)

        # --- Seção de Tensões Nodais ---
        ctk.CTkLabel(self.scrollable_waveform_controls_area, text="Tensões Nodais:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(5,0))
        
        nv_buttons_frame = ctk.CTkFrame(self.scrollable_waveform_controls_area, fg_color="transparent")
        nv_buttons_frame.pack(fill="x", padx=10, pady=(0,2))

        def select_all_nodal_voltages():
            for var in self.waveform_selection_vars["nodal_voltages"].values():
                var.set(True)

        def clear_all_nodal_voltages():
            for var in self.waveform_selection_vars["nodal_voltages"].values():
                var.set(False)

        ctk.CTkButton(nv_buttons_frame, text="Todos", width=70, command=select_all_nodal_voltages).pack(side="left", padx=(0,5))
        ctk.CTkButton(nv_buttons_frame, text="Nenhum", width=70, command=clear_all_nodal_voltages).pack(side="left")

        nodal_voltages = self.analysis_results.get('nodal_voltages_phasors', {})
        if not nodal_voltages:
            ctk.CTkLabel(self.scrollable_waveform_controls_area, text="- Nenhuma disponível -").pack(anchor="w", padx=10)
        else:
            for node_name in sorted(nodal_voltages.keys(), key=lambda x: int(x) if x.isdigit() and x != '0' else (-1 if x == '0' else float('inf'))):
                if node_name == '0': continue # Normalmente não plotamos V(0)
                # Preserve existing selection if var already exists, otherwise default to False
                existing_var = self.waveform_selection_vars["nodal_voltages"].get(node_name)
                var = existing_var if existing_var is not None else tk.BooleanVar(value=False)
                self.waveform_selection_vars["nodal_voltages"][node_name] = var
                # Checkbox é filho direto do scrollable_waveform_controls_area
                cb = ctk.CTkCheckBox(self.scrollable_waveform_controls_area, text=f"V({node_name})", variable=var)
                cb.pack(anchor="w", padx=10, pady=1) # Ajuste o pady para compactar

        # --- Seção de Correntes em Componentes ---
        ctk.CTkLabel(self.scrollable_waveform_controls_area, text="Correntes em Componentes:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(10,0))
        
        cc_buttons_frame = ctk.CTkFrame(self.scrollable_waveform_controls_area, fg_color="transparent")
        cc_buttons_frame.pack(fill="x", padx=10, pady=(0,2))

        def select_all_component_currents():
            for var in self.waveform_selection_vars["component_currents"].values():
                var.set(True)

        def clear_all_component_currents():
            for var in self.waveform_selection_vars["component_currents"].values():
                var.set(False)

        ctk.CTkButton(cc_buttons_frame, text="Todos", width=70, command=select_all_component_currents).pack(side="left", padx=(0,5))
        ctk.CTkButton(cc_buttons_frame, text="Nenhum", width=70, command=clear_all_component_currents).pack(side="left")

        comp_currents = self.analysis_results.get('component_currents_phasors', {})
        if not comp_currents:
            ctk.CTkLabel(self.scrollable_waveform_controls_area, text="- Nenhuma disponível -").pack(anchor="w", padx=10)
        else:
            for comp_name in sorted(comp_currents.keys()):
                existing_var = self.waveform_selection_vars["component_currents"].get(comp_name)
                var = existing_var if existing_var is not None else tk.BooleanVar(value=False)
                self.waveform_selection_vars["component_currents"][comp_name] = var
                cb = ctk.CTkCheckBox(self.scrollable_waveform_controls_area, text=f"I({comp_name})", variable=var)
                cb.pack(anchor="w", padx=10, pady=1)
            
        # --- Seção de Tensões em Componentes (Vdrop) ---
        ctk.CTkLabel(self.scrollable_waveform_controls_area, text="Tensões em Componentes (Vqueda):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(10,0))

        cv_buttons_frame = ctk.CTkFrame(self.scrollable_waveform_controls_area, fg_color="transparent")
        cv_buttons_frame.pack(fill="x", padx=10, pady=(0,2))

        def select_all_component_voltages():
            for var in self.waveform_selection_vars["component_voltages"].values():
                var.set(True)

        def clear_all_component_voltages():
            for var in self.waveform_selection_vars["component_voltages"].values():
                var.set(False)

        ctk.CTkButton(cv_buttons_frame, text="Todos", width=70, command=select_all_component_voltages).pack(side="left", padx=(0,5))
        ctk.CTkButton(cv_buttons_frame, text="Nenhum", width=70, command=clear_all_component_voltages).pack(side="left")

        comp_voltages = self.analysis_results.get('component_voltages_phasors', {})
        if not comp_voltages:
            ctk.CTkLabel(self.scrollable_waveform_controls_area, text="- Nenhuma disponível -").pack(anchor="w", padx=10)
        else:
            for comp_name in sorted(comp_voltages.keys()):
                existing_var = self.waveform_selection_vars["component_voltages"].get(comp_name)
                var = existing_var if existing_var is not None else tk.BooleanVar(value=False)
                self.waveform_selection_vars["component_voltages"][comp_name] = var
                cb = ctk.CTkCheckBox(self.scrollable_waveform_controls_area, text=f"V_queda({comp_name})", variable=var)
                cb.pack(anchor="w", padx=10, pady=1)

        # --- Seção de Grandezas Trifásicas de Fontes ---
        if hasattr(self, 'three_phase_source_details_map') and self.three_phase_source_details_map:
            ctk.CTkLabel(self.scrollable_waveform_controls_area, text="Grandezas Trifásicas de Fontes:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(15,0))

            for parent_name, details in self.three_phase_source_details_map.items():
                # Ensure this parent_name corresponds to a source that was actually part of the analysis
                # (e.g. it has decomposed components in analysis_results)
                # A simple check: if any decomposed component exists.
                is_source_in_analysis = any(
                    comp_spec.get('three_phase_parent') == parent_name
                    for comp_spec in getattr(self, 'parsed_components_for_plotting', [])
                )
                if not is_source_in_analysis:
                    continue

                ctk.CTkLabel(self.scrollable_waveform_controls_area, text=f"Fonte: {parent_name} ({details['type']})", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=(5,2))
                
                # Tensões de Fase (ex: VAN, VBN, VCN para VSY)
                if details['type'] == 'VSY':
                    ctk.CTkLabel(self.scrollable_waveform_controls_area, text="  Tensões de Fase (Vφ):").pack(anchor="w", padx=15, pady=(0,0))
                    for phase_char in ['A', 'B', 'C']:
                        key = (parent_name, phase_char) # Using phase_char as part of key for V_phase
                        var = self.waveform_selection_vars["three_phase_source_phase_voltages"].get(key, tk.BooleanVar(value=False))
                        self.waveform_selection_vars["three_phase_source_phase_voltages"][key] = var
                        cb = ctk.CTkCheckBox(self.scrollable_waveform_controls_area, text=f"V_{phase_char}N ({parent_name})", variable=var)
                        cb.pack(anchor="w", padx=20, pady=1)
                
                # Correntes de Linha (IA, IB, IC)
                ctk.CTkLabel(self.scrollable_waveform_controls_area, text="  Correntes de Linha (IL):").pack(anchor="w", padx=15, pady=(2,0))
                for phase_char in ['A', 'B', 'C']:
                    key = (parent_name, phase_char) # Using phase_char as part of key for I_line
                    var = self.waveform_selection_vars["three_phase_source_line_currents"].get(key, tk.BooleanVar(value=False))
                    self.waveform_selection_vars["three_phase_source_line_currents"][key] = var
                    cb = ctk.CTkCheckBox(self.scrollable_waveform_controls_area, text=f"I_{phase_char} ({parent_name})", variable=var)
                    cb.pack(anchor="w", padx=20, pady=1)

                # Tensões de Linha (VAB, VBC, VCA)
                ctk.CTkLabel(self.scrollable_waveform_controls_area, text="  Tensões de Linha (VL-L):").pack(anchor="w", padx=15, pady=(2,0))
                line_voltage_pairs = [("A", "B"), ("B", "C"), ("C", "A")]
                for p1_char, p2_char in line_voltage_pairs:
                    pair_str = f"{p1_char}{p2_char}"
                    key = (parent_name, pair_str) # Using pair_str as part of key for V_line
                    var = self.waveform_selection_vars["three_phase_source_line_voltages"].get(key, tk.BooleanVar(value=False))
                    self.waveform_selection_vars["three_phase_source_line_voltages"][key] = var
                    cb = ctk.CTkCheckBox(self.scrollable_waveform_controls_area, text=f"V_{pair_str} ({parent_name})", variable=var)
                    cb.pack(anchor="w", padx=20, pady=1)

        # Add a little space at the bottom of the scrollable area
        ctk.CTkLabel(self.scrollable_waveform_controls_area, text="").pack()


    def _plot_time_domain_waveforms(self):
        try:
            num_periods = int(self.num_periods_to_plot_var.get())
            if num_periods <= 0:
                num_periods = 3 # Fallback para valor positivo
        except ValueError:
            num_periods = 3 # Fallback se a entrada não for um inteiro válido
            self.num_periods_to_plot_var.set("3") # Reset invalid entry

        if not self.analysis_performed_successfully or not self.analysis_results or \
           self.analysis_results.get('freq') is None or self.analysis_results.get('freq') <= 0:
            self._clear_waveforms_plot(error_message="Análise não realizada ou frequência inválida.")
            return


        # Surgical clear before plotting new data
        if not self.ax_waveforms: return # pragma: no cover

        for line in list(self.ax_waveforms.get_lines()): 
            line.remove()
        if self.ax_waveforms.get_legend(): 
            self.ax_waveforms.get_legend().remove()
        # Clear only non-title texts if needed, or clear all and reset title
        # For simplicity, let's clear all texts and re-set the title.
        for text_obj in list(self.ax_waveforms.texts): text_obj.remove()

        self.ax_waveforms.set_title("Formas de Onda no Tempo", fontsize=12, color=self._get_ctk_text_color()) # Reset title
        self.ax_waveforms.set_xticks([]) # Will be overridden if data is plotted
        self.ax_waveforms.set_yticks([]) # Will be overridden if data is plotted
        self.ax_waveforms.grid(False)   # Will be overridden if data is plotted

        freq = self.analysis_results['freq']
        if freq is None or freq <= 0: # Should have been caught earlier, but as a safeguard
            self._clear_waveforms_plot(error_message="Frequência inválida para plotar formas de onda.")
            return
        omega = 2 * math.pi * freq
        # Em _plot_time_domain_waveforms, antes dos loops de plotagem
        voltage_plot_idx_counter = 0
        current_plot_idx_counter = 0

        period = 1 / freq
        t_values = np.linspace(0, num_periods * period, 500) # Usar num_periods

        # Iterar sobre as Tensões Nodais selecionadas
        for node_name, var in self.waveform_selection_vars["nodal_voltages"].items():
            if var.get(): # Se o checkbox estiver marcado
                phasor = self.analysis_results['nodal_voltages_phasors'].get(node_name)
                if phasor is not None:
                    mag = abs(phasor)
                    phase_rad = cmath.phase(phasor)
                    if not (math.isfinite(mag) and math.isfinite(phase_rad)):
                        print(f"[DEBUG] Pulando forma de onda para V({node_name}) devido a valores não finitos: mag={mag}, phase={phase_rad}")
                        continue # Pula esta forma de onda

                    color = self.waveform_plot_colors[voltage_plot_idx_counter % len(self.waveform_plot_colors)]
                    linestyle_idx = (voltage_plot_idx_counter // len(self.waveform_plot_colors)) % len(self.waveform_plot_linestyles)
                    linestyle = self.waveform_plot_linestyles[linestyle_idx]
                    y_values = mag * np.cos(omega * t_values + phase_rad)
                    self.ax_waveforms.plot(t_values, y_values, label=f"V({node_name})(t)", color=color, linestyle=linestyle)
                    voltage_plot_idx_counter += 1

        # Iterar sobre as Correntes em Componentes selecionadas
        for comp_name, var in self.waveform_selection_vars["component_currents"].items():
            if var.get():
                phasor = self.analysis_results['component_currents_phasors'].get(comp_name)
                if phasor is not None:
                    mag = abs(phasor)
                    phase_rad = cmath.phase(phasor)
                    if not (math.isfinite(mag) and math.isfinite(phase_rad)):
                        print(f"[DEBUG] Pulando forma de onda para I({comp_name}) devido a valores não finitos: mag={mag}, phase={phase_rad}")
                        continue

                    effective_current_plot_index = voltage_plot_idx_counter + current_plot_idx_counter # Simplesmente continua o ciclo geral
                    color = self.waveform_plot_colors[effective_current_plot_index % len(self.waveform_plot_colors)]
                    linestyle_idx = (effective_current_plot_index // len(self.waveform_plot_colors)) % len(self.waveform_plot_linestyles)
                    linestyle = self.waveform_plot_linestyles[linestyle_idx]
                    y_values = mag * np.cos(omega * t_values + phase_rad)
                    target_axis_for_currents = self.ax_waveforms # Default to main axis
                    target_axis_for_currents.plot(t_values, y_values, label=f"I({comp_name})(t)", color=color, linestyle=linestyle)
                    current_plot_idx_counter += 1

        # Iterar sobre as Tensões em Componentes selecionadas
        for comp_name, var in self.waveform_selection_vars["component_voltages"].items():
            if var.get():
                phasor = self.analysis_results['component_voltages_phasors'].get(comp_name)
                if phasor is not None:
                    mag = abs(phasor)
                    phase_rad = cmath.phase(phasor)
                    if not (math.isfinite(mag) and math.isfinite(phase_rad)):
                        print(f"[DEBUG] Pulando forma de onda para V_queda({comp_name}) devido a valores não finitos: mag={mag}, phase={phase_rad}")
                        continue
                    # Component voltages continue the voltage color/style cycle
                    color = self.waveform_plot_colors[voltage_plot_idx_counter % len(self.waveform_plot_colors)]
                    linestyle_idx = (voltage_plot_idx_counter // len(self.waveform_plot_colors)) % len(self.waveform_plot_linestyles)
                    linestyle = self.waveform_plot_linestyles[linestyle_idx]
                    y_values = mag * np.cos(omega * t_values + phase_rad)
                    self.ax_waveforms.plot(t_values, y_values, label=f"V_queda({comp_name})(t)", color=color, linestyle=linestyle)
                    voltage_plot_idx_counter += 1

        # --- Plotar Grandezas Trifásicas Selecionadas ---

        # Plotar Tensões de Fase de Fontes Trifásicas (VSY)
        for key, var in self.waveform_selection_vars.get("three_phase_source_phase_voltages", {}).items():
            if var.get():
                parent_name, phase_char = key
                phasor_to_plot = None
                label_text = f"V_{phase_char}N({parent_name})(t)"
                
                source_details = self.three_phase_source_details_map.get(parent_name)
                if not source_details or source_details['type'] != 'VSY':
                    continue

                decomposed_comp_name = f"{parent_name}_{phase_char}"
                phasor_to_plot = self.analysis_results['component_voltages_phasors'].get(decomposed_comp_name)
                
                if phasor_to_plot is not None:
                    mag, phase_rad = abs(phasor_to_plot), cmath.phase(phasor_to_plot)
                    if not (math.isfinite(mag) and math.isfinite(phase_rad)): continue
                    color = self.waveform_plot_colors[voltage_plot_idx_counter % len(self.waveform_plot_colors)]
                    linestyle_idx = (voltage_plot_idx_counter // len(self.waveform_plot_colors)) % len(self.waveform_plot_linestyles)
                    linestyle = self.waveform_plot_linestyles[linestyle_idx]
                    y_values = mag * np.cos(omega * t_values + phase_rad)
                    self.ax_waveforms.plot(t_values, y_values, label=label_text, color=color, linestyle=linestyle)
                    voltage_plot_idx_counter += 1

        # Plotar Correntes de Linha de Fontes Trifásicas
        for key, var in self.waveform_selection_vars.get("three_phase_source_line_currents", {}).items():
            if var.get():
                parent_name, phase_char = key
                phasor_to_plot = None
                label_text = f"I_{phase_char}({parent_name})(t)"

                source_details = self.three_phase_source_details_map.get(parent_name)
                if not source_details: continue

                if source_details['type'] == 'VSY':
                    decomposed_comp_name = f"{parent_name}_{phase_char}"
                    phasor_to_plot = self.analysis_results['component_currents_phasors'].get(decomposed_comp_name)
                elif source_details['type'] == 'VSD':
                    all_comp_currents = self.analysis_results.get('component_currents_phasors', {})
                    i_ab = all_comp_currents.get(f"{parent_name}_AB")
                    i_bc = all_comp_currents.get(f"{parent_name}_BC")
                    i_ca = all_comp_currents.get(f"{parent_name}_CA")
                    if phase_char == 'A' and i_ab is not None and i_ca is not None: phasor_to_plot = i_ab - i_ca
                    elif phase_char == 'B' and i_bc is not None and i_ab is not None: phasor_to_plot = i_bc - i_ab
                    elif phase_char == 'C' and i_ca is not None and i_bc is not None: phasor_to_plot = i_ca - i_bc
                
                if phasor_to_plot is not None:
                    mag, phase_rad = abs(phasor_to_plot), cmath.phase(phasor_to_plot)
                    if not (math.isfinite(mag) and math.isfinite(phase_rad)): continue
                    effective_current_plot_index = voltage_plot_idx_counter + current_plot_idx_counter
                    color = self.waveform_plot_colors[effective_current_plot_index % len(self.waveform_plot_colors)]
                    linestyle_idx = (effective_current_plot_index // len(self.waveform_plot_colors)) % len(self.waveform_plot_linestyles)
                    linestyle = self.waveform_plot_linestyles[linestyle_idx]
                    y_values = mag * np.cos(omega * t_values + phase_rad)
                    self.ax_waveforms.plot(t_values, y_values, label=label_text, color=color, linestyle=linestyle) # Plot on main axis for now
                    current_plot_idx_counter += 1

        # Plotar Tensões de Linha de Fontes Trifásicas
        for key, var in self.waveform_selection_vars.get("three_phase_source_line_voltages", {}).items():
            if var.get():
                parent_name, pair_char = key # e.g., "AB"
                phasor_to_plot = None
                label_text = f"V_{pair_char}({parent_name})(t)"

                source_details = self.three_phase_source_details_map.get(parent_name)
                if not source_details: continue

                node1_orig_label = source_details.get(f'n{pair_char[0].lower()}') # e.g., 'nA'
                node2_orig_label = source_details.get(f'n{pair_char[1].lower()}') # e.g., 'nB'

                if node1_orig_label and node2_orig_label:
                    v_node1 = self.analysis_results['nodal_voltages_phasors'].get(node1_orig_label)
                    v_node2 = self.analysis_results['nodal_voltages_phasors'].get(node2_orig_label)
                    if v_node1 is not None and v_node2 is not None:
                        phasor_to_plot = v_node1 - v_node2
                
                if phasor_to_plot is not None:
                    mag, phase_rad = abs(phasor_to_plot), cmath.phase(phasor_to_plot)
                    if not (math.isfinite(mag) and math.isfinite(phase_rad)): continue
                    color = self.waveform_plot_colors[voltage_plot_idx_counter % len(self.waveform_plot_colors)]
                    linestyle_idx = (voltage_plot_idx_counter // len(self.waveform_plot_colors)) % len(self.waveform_plot_linestyles)
                    linestyle = self.waveform_plot_linestyles[linestyle_idx]
                    y_values = mag * np.cos(omega * t_values + phase_rad)
                    self.ax_waveforms.plot(t_values, y_values, label=label_text, color=color, linestyle=linestyle)
                    voltage_plot_idx_counter += 1

        if not self.ax_waveforms.lines: # Se nada foi plotado
             self._clear_waveforms_plot(initial_message="Nenhuma forma de onda selecionada para plotar.")
             return
        
        # Configurações finais do gráfico
        self.ax_waveforms.set_xlabel("Tempo (s)")
        self.ax_waveforms.set_ylabel("Amplitude (V ou A)")
        
        show_grid = self.show_waveform_grid_var.get()
        self.ax_waveforms.grid(show_grid, linestyle=':', alpha=0.7)
        if hasattr(self, 'ax_waveforms_current_twin') and self.ax_waveforms_current_twin and self.ax_waveforms_current_twin.get_visible():
            # A grade do eixo X principal geralmente é compartilhada.
            # Para consistência visual, aplicamos também ao eixo Y secundário se ele estiver visível.
            self.ax_waveforms_current_twin.grid(show_grid, linestyle=':', alpha=0.7)
            
        self.ax_waveforms.legend(loc='best', fontsize='small')
        self.ax_waveforms.set_xlim(0, num_periods * period) # Usar num_periods
        # try:
        #     self.fig_waveforms.tight_layout() # Not needed with constrained_layout
        # except Exception: pass # pragma: no cover
        if self.canvas_waveforms_figure_agg:
            self.canvas_waveforms_figure_agg.draw_idle()

    # --- Utility methods for UI theming and color ---


    def _tkinter_gray_to_hex(self, gray_string):
        """Converts Tkinter grayXX string to a hex color string."""
        if isinstance(gray_string, str):
            match = re.fullmatch(r"gray(\d{1,3})", gray_string, re.IGNORECASE)
            if match:
                percentage = int(match.group(1))
                if 0 <= percentage <= 100:
                    value = round(255 * percentage / 100)
                    hex_val = format(value, '02x')
                    return f"#{hex_val}{hex_val}{hex_val}"
        return gray_string # Return original if not a grayXX string or not a string

    def _get_ctk_bg_color(self):
        try:
            bg_color_tuple = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
            current_mode = ctk.get_appearance_mode()
            color_val = ""
            if isinstance(bg_color_tuple, (list, tuple)) and len(bg_color_tuple) == 2:
                color_val = bg_color_tuple[0] if current_mode == "Light" else bg_color_tuple[1]
            else:
                color_val = bg_color_tuple
            return self._tkinter_gray_to_hex(color_val)
        except Exception:
            return "white" if ctk.get_appearance_mode() == "Light" else "#2B2B2B"

    def _get_ctk_text_color(self):
        try:
            text_color_tuple = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
            current_mode = ctk.get_appearance_mode()
            color_val = ""
            if isinstance(text_color_tuple, (list, tuple)) and len(text_color_tuple) == 2:
                color_val = text_color_tuple[0] if current_mode == "Light" else text_color_tuple[1]
            else:
                color_val = text_color_tuple
            return self._tkinter_gray_to_hex(color_val)
        except Exception:
            return "black" if ctk.get_appearance_mode() == "Light" else "white"

    def _process_netlist_button_command(self):
        # This function is called by the "Processar Netlist e Analisar" button.
        # It simply triggers the main analysis routine, which now handles netlist parsing.
        self.analyze_circuit()
        # Optionally, provide feedback that the netlist is being processed.
        # messagebox.showinfo("Netlist Processing", "Netlist submetido para Análise Nodal. Verifique a aba 'Resultados'.")

    def _parse_netlist_for_nodal_analysis(self, netlist_content):
        parsed_components_list = []
        freq_from_netlist = None
        error_log = []

        # Regex patterns
        # VS<name_optional> <node+> <node-> AC <Vmag> <Vphase_deg_optional>
        vs_pattern = re.compile(r"VS([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+AC\s+([\d\.\-eE+]+)\s*([\d\.\-eE+]*)", re.IGNORECASE)
        # <R|L|C><name_optional> <node1> <node2> <value>
        comp_pattern = re.compile(r"([RCL])([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+([\d\.eE\-+]+)", re.IGNORECASE)
        # IS<name_optional> <node_out> <node_in> AC <Imag> <Iphase_deg_optional>
        is_pattern = re.compile(r"IS([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+AC\s+([\d\.\-eE+]+)\s*([\d\.\-eE+]*)", re.IGNORECASE)
        freq_pattern = re.compile(r"FREQ\s+([\d\.\-eE+]+)", re.IGNORECASE)
        # Controlled Sources
        vcvs_pattern = re.compile(r"E([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+([\d\.\-eE+]+)", re.IGNORECASE)
        vccs_pattern = re.compile(r"G([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+([\d\.\-eE+]+)", re.IGNORECASE)
        # For CCVS/CCCS, control_source_name is VS<suffix>
        ccvs_pattern = re.compile(r"H([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+VS([A-Z0-9_]+)\s+([\d\.\-eE+]+)", re.IGNORECASE)
        cccs_pattern = re.compile(r"F([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+VS([A-Z0-9_]+)\s+([\d\.\-eE+]+)", re.IGNORECASE)
        # Trifásico - Fontes
        vs_y_pattern = re.compile(r"VSY\s*([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+AC\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)\s+(ABC|ACB)", re.IGNORECASE)
        vs_d_pattern = re.compile(r"VSD\s*([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+AC\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)\s+(ABC|ACB)", re.IGNORECASE)
        # Trifásico - Cargas
        load_y_pattern = re.compile(r"LOADY\s*([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)", re.IGNORECASE) # Nome NA NB NC NN R L C
        load_d_pattern = re.compile(r"LOADD\s*([A-Z0-9_]*)\s+([\w_]+)\s+([\w_]+)\s+([\w_]+)\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)", re.IGNORECASE)    # Nome NA NB NC R L C




        vs_source_defined_count = 0 # For auto-naming VS
        is_source_defined_count = 0 # For auto-naming IS
        e_source_count = 0 # For VCVS
        g_source_count = 0 # For VCCS
        h_source_count = 0 # For CCVS
        f_source_count = 0 # For CCCS
        load_defined_count = 0 # For LOADY/LOADD auto-naming

        for line_num, line_full in enumerate(netlist_content.splitlines(), 1):
            line = line_full.strip()
            L_PREFIX = f"L{line_num}: "

            if not line or line.startswith("#") or line.startswith("*"):
                continue

            m_vs = vs_pattern.match(line)
            m_comp = comp_pattern.match(line)
            m_is = is_pattern.match(line)
            m_freq = freq_pattern.match(line)
            m_vcvs = vcvs_pattern.match(line)
            m_vccs = vccs_pattern.match(line)
            m_ccvs = ccvs_pattern.match(line)
            m_cccs = cccs_pattern.match(line)
            m_vsy = vs_y_pattern.match(line)
            m_vsd = vs_d_pattern.match(line)
            m_loady = load_y_pattern.match(line)
            m_loadd = load_d_pattern.match(line)

            if m_vs:
                vs_source_defined_count += 1
                name_suffix = m_vs.group(1)
                name = "VS" + name_suffix if name_suffix else f"VS_auto{vs_source_defined_count}"
                node1, node2 = m_vs.group(2), m_vs.group(3)
                try:
                    v_mag = float(m_vs.group(4))
                    v_phase_deg_str = m_vs.group(5)
                    v_phase_deg = float(v_phase_deg_str) if v_phase_deg_str and v_phase_deg_str.strip() else 0.0

                    if v_mag < 0: # Conventionally, Vmag is positive.
                        error_log.append(L_PREFIX + f"VS {name} magnitude was negative. Making positive and inverting phase.")
                        v_mag = abs(v_mag)
                        v_phase_deg = (v_phase_deg + 180)
                    # Normalize phase to be within a common range e.g. -180 to 180
                    v_phase_deg = (v_phase_deg + 180) % 360 - 180


                    parsed_components_list.append({
                        'type': 'VS', 'name': name, 'nodes': (node1, node2),
                        'v_mag': v_mag, 'v_phase_deg': v_phase_deg,
                        'value': v_mag, # 'value' for consistency, might represent magnitude
                        'original_line': f"# Original: {line_full}"
                    })
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for VS {name}.")
                    continue
            elif m_comp:
                comp_type_char = m_comp.group(1).upper()
                name_suffix = m_comp.group(2)
                name = comp_type_char + name_suffix if name_suffix else f"{comp_type_char}_auto{len(parsed_components_list)}"
                node1, node2 = m_comp.group(3), m_comp.group(4)
                try:
                    value = float(m_comp.group(5))
                    if value < 0:
                        error_log.append(L_PREFIX + f"Component {comp_type_char} {name} value ({value}) cannot be negative. Using absolute value.")
                        value = abs(value) # Or error out depending on strictness
                    parsed_components_list.append({
                        'type': comp_type_char, 'name': name, 'nodes': (node1, node2), 'value': value,
                        'original_line': f"# Original: {line_full}"
                    })
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for {comp_type_char} {name}.")
                    continue
            elif m_is:
                is_source_defined_count += 1
                name_suffix = m_is.group(1)
                name = "IS" + name_suffix if name_suffix else f"IS_auto{is_source_defined_count}"
                node_out, node_in = m_is.group(2), m_is.group(3) # node_out: current exits source, node_in: current enters source
                try:
                    i_mag = float(m_is.group(4))
                    i_phase_deg_str = m_is.group(5)
                    i_phase_deg = float(i_phase_deg_str) if i_phase_deg_str and i_phase_deg_str.strip() else 0.0

                    if i_mag < 0:
                        error_log.append(L_PREFIX + f"IS {name} magnitude was negative. Making positive and inverting phase.")
                        i_mag = abs(i_mag)
                        i_phase_deg = (i_phase_deg + 180)
                    # Normalize phase
                    i_phase_deg = (i_phase_deg + 180) % 360 - 180

                    parsed_components_list.append({
                        'type': 'IS', 'name': name, 'nodes': (node_out, node_in),
                        'i_mag': i_mag, 'i_phase_deg': i_phase_deg,
                        'value': i_mag, # 'value' for consistency, represents magnitude
                        'original_line': f"# Original: {line_full}"
                    })
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for IS {name}.")
                    continue
            elif m_freq:
                if freq_from_netlist is not None:
                    error_log.append(L_PREFIX + "Multiple FREQ definitions. Using the last one.")
                try:
                    freq_val = float(m_freq.group(1))
                    if freq_val <= 0:
                        error_log.append(L_PREFIX + "Frequency must be positive.")
                    else:
                        freq_from_netlist = freq_val
                except ValueError:
                    error_log.append(L_PREFIX + "Invalid numeric value for FREQ.")
                    continue
            elif m_vcvs:
                e_source_count += 1
                name_suffix = m_vcvs.group(1)
                name = "E" + name_suffix if name_suffix else f"E_auto{e_source_count}"
                node_p, node_n = m_vcvs.group(2), m_vcvs.group(3)
                ctrl_node_p, ctrl_node_n = m_vcvs.group(4), m_vcvs.group(5)
                try:
                    gain = float(m_vcvs.group(6))
                    parsed_components_list.append({
                        'type': 'VCVS', 'name': name,
                        'nodes': (node_p, node_n),
                        'control_nodes': (ctrl_node_p, ctrl_node_n),
                        'control_source_name': None,
                        'gain': gain, 'value': gain,
                        'original_line': f"# Original: {line_full}"
                    })
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for gain of VCVS {name}.")
                    continue
            elif m_vccs:
                g_source_count += 1
                name_suffix = m_vccs.group(1)
                name = "G" + name_suffix if name_suffix else f"G_auto{g_source_count}"
                node_out, node_in = m_vccs.group(2), m_vccs.group(3)
                ctrl_node_p, ctrl_node_n = m_vccs.group(4), m_vccs.group(5)
                try:
                    gain = float(m_vccs.group(6)) # Transconductance
                    parsed_components_list.append({
                        'type': 'VCCS', 'name': name,
                        'nodes': (node_out, node_in),
                        'control_nodes': (ctrl_node_p, ctrl_node_n),
                        'control_source_name': None,
                        'gain': gain, 'value': gain,
                        'original_line': f"# Original: {line_full}"
                    })
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for gain (transconductance) of VCCS {name}.")
                    continue
            elif m_ccvs:
                h_source_count += 1
                name_suffix = m_ccvs.group(1)
                name = "H" + name_suffix if name_suffix else f"H_auto{h_source_count}"
                node_p, node_n = m_ccvs.group(2), m_ccvs.group(3)
                control_vs_suffix = m_ccvs.group(4)
                control_source_fullname = f"VS{control_vs_suffix}"
                try:
                    gain = float(m_ccvs.group(5)) # Transresistance
                    parsed_components_list.append({
                        'type': 'CCVS', 'name': name,
                        'nodes': (node_p, node_n),
                        'control_nodes': None,
                        'control_source_name': control_source_fullname,
                        'gain': gain, 'value': gain,
                        'original_line': f"# Original: {line_full}"
                    })
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for gain (transresistance) of CCVS {name}.")
                    continue
            elif m_cccs:
                f_source_count += 1
                name_suffix = m_cccs.group(1)
                name = "F" + name_suffix if name_suffix else f"F_auto{f_source_count}"
                node_out, node_in = m_cccs.group(2), m_cccs.group(3)
                control_vs_suffix = m_cccs.group(4)
                control_source_fullname = f"VS{control_vs_suffix}"
                try:
                    gain = float(m_cccs.group(5)) # Current gain
                    parsed_components_list.append({
                        'type': 'CCCS', 'name': name,
                        'nodes': (node_out, node_in),
                        'control_nodes': None,
                        'control_source_name': control_source_fullname,
                        'gain': gain, 'value': gain,
                        'original_line': f"# Original: {line_full}"
                    })
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for gain (current gain) of CCCS {name}.")
                    continue
            elif m_vsy:
                name_suffix = m_vsy.group(1)
                base_name = "VSY" + name_suffix if name_suffix else f"VSY_auto{vs_source_defined_count + is_source_defined_count + 1}" # Make it unique
                vs_source_defined_count +=1 # Consumes a "source" name
                node_a_str, node_b_str, node_c_str, node_n_str = m_vsy.group(2), m_vsy.group(3), m_vsy.group(4), m_vsy.group(5)
                try:
                    # Store original node names for VSY
                    self.three_phase_source_details_map[base_name] = {
                        'type': 'VSY', 'nA': node_a_str, 'nB': node_b_str, 'nC': node_c_str, 'nN': node_n_str
                    }
                    v_mag = float(m_vsy.group(6))
                    v_phase_a_deg = float(m_vsy.group(7))
                    sequence = m_vsy.group(8).upper()
                    original_line_info = f"# Original: {line_full}"

                    # Fase A
                    parsed_components_list.append({
                        'type': 'VS', 'name': f"{base_name}_A", 'nodes': (node_a_str, node_n_str),
                        'v_mag': v_mag, 'v_phase_deg': v_phase_a_deg, 'value': v_mag, 
                        'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'VSY'
                    })
                    # Fase B
                    phase_b_offset = -120 if sequence == "ABC" else 120
                    parsed_components_list.append({
                        'type': 'VS', 'name': f"{base_name}_B", 'nodes': (node_b_str, node_n_str),
                        'v_mag': v_mag, 'v_phase_deg': v_phase_a_deg + phase_b_offset, 'value': v_mag, 
                        'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'VSY'
                    })
                    # Fase C
                    phase_c_offset = 120 if sequence == "ABC" else -120
                    parsed_components_list.append({'type': 'VS', 'name': f"{base_name}_C", 'nodes': (node_c_str, node_n_str),
                                                   'v_mag': v_mag, 'v_phase_deg': v_phase_a_deg + phase_c_offset, 'value': v_mag, 'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'VSY'})
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for VSY {base_name}.")
                    continue
            elif m_vsd:
                name_suffix = m_vsd.group(1)
                base_name = "VSD" + name_suffix if name_suffix else f"VSD_auto{vs_source_defined_count + is_source_defined_count + 1}"
                vs_source_defined_count +=1
                node_a_str, node_b_str, node_c_str = m_vsd.group(2), m_vsd.group(3), m_vsd.group(4) # Nodes for Vab, Vbc, Vca connections
                try:
                    # Store original node names for VSD
                    self.three_phase_source_details_map[base_name] = {
                        'type': 'VSD', 'nA': node_a_str, 'nB': node_b_str, 'nC': node_c_str
                    }
                    v_linha_mag = float(m_vsd.group(5))
                    v_linha_fase_ab_deg = float(m_vsd.group(6))
                    sequence = m_vsd.group(7).upper()
                    original_line_info = f"# Original: {line_full}"

                    # Fonte AB
                    parsed_components_list.append({
                        'type': 'VS', 'name': f"{base_name}_AB", 'nodes': (node_a_str, node_b_str),
                        'v_mag': v_linha_mag, 'v_phase_deg': v_linha_fase_ab_deg, 'value': v_linha_mag, 
                        'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'VSD'
                    })
                    # Fonte BC
                    phase_bc_offset = -120 if sequence == "ABC" else 120
                    parsed_components_list.append({
                        'type': 'VS', 'name': f"{base_name}_BC", 'nodes': (node_b_str, node_c_str),
                        'v_mag': v_linha_mag, 'v_phase_deg': v_linha_fase_ab_deg + phase_bc_offset, 'value': v_linha_mag, 
                        'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'VSD'
                    })
                    # Fonte CA
                    phase_ca_offset = 120 if sequence == "ABC" else -120
                    parsed_components_list.append({'type': 'VS', 'name': f"{base_name}_CA", 'nodes': (node_c_str, node_a_str),
                                                   'v_mag': v_linha_mag, 'v_phase_deg': v_linha_fase_ab_deg + phase_ca_offset, 'value': v_linha_mag, 'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'VSD'})
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for VSD {base_name}.")
                    continue
            elif m_loady:
                name_suffix = m_loady.group(1)
                load_defined_count += 1
                base_name = "LOADY" + name_suffix if name_suffix else f"LOADY_auto{load_defined_count}"
                node_a_str, node_b_str, node_c_str, node_n_str = m_loady.group(2), m_loady.group(3), m_loady.group(4), m_loady.group(5)
                try:
                    r_f = float(m_loady.group(6))
                    l_f = float(m_loady.group(7))
                    c_f = float(m_loady.group(8))
                    original_line_info = f"# Original: {line_full}"

                    # nodes_phase_str = [node_a_str, node_b_str, node_c_str]
                    # phase_labels = ['A', 'B', 'C']
                    # for i in range(3):
                    #    current_phase_node_str = nodes_phase_str[i]
                    #    current_phase_label = phase_labels[i]
                    for current_phase_label, current_phase_node_str in [('A', node_a_str), ('B', node_b_str), ('C', node_c_str)]:
                        if r_f > 1e-12: # Per prompt, or 1e-9 from previous diff
                            parsed_components_list.append({
                                'type': 'R', 'name': f"R_{base_name}_{current_phase_label}", 'nodes': (current_phase_node_str, node_n_str),
                                'value': r_f, 'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'LOADY'})
                        if l_f > 1e-12: 
                            parsed_components_list.append({
                                'type': 'L', 'name': f"L_{base_name}_{current_phase_label}", 'nodes': (current_phase_node_str, node_n_str),
                                'value': l_f, 'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'LOADY'})
                        if c_f > 1e-15: 
                            parsed_components_list.append({
                                'type': 'C', 'name': f"C_{base_name}_{current_phase_label}", 'nodes': (current_phase_node_str, node_n_str),
                                'value': c_f, 'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'LOADY'})
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for LOADY {base_name}.")
                    continue
            elif m_loadd:
                name_suffix = m_loadd.group(1)
                load_defined_count += 1
                base_name = "LOADD" + name_suffix if name_suffix else f"LOADD_auto{load_defined_count}"
                node_a_str, node_b_str, node_c_str = m_loadd.group(2), m_loadd.group(3), m_loadd.group(4) # Nodes for Z_AB, Z_BC, Z_CA
                try:
                    r_fd = float(m_loadd.group(5))
                    l_fd = float(m_loadd.group(6))
                    c_fd = float(m_loadd.group(7))
                    original_line_info = f"# Original: {line_full}"

                    delta_connections = [
                        (node_a_str, node_b_str, "AB"), # node1_str, node2_str, phase_pair_label
                        (node_b_str, node_c_str, "BC"),
                        (node_c_str, node_a_str, "CA") 
                    ]
                    for node1_str_conn, node2_str_conn, phase_pair_label in delta_connections:
                        if r_fd > 1e-12: # Per prompt, or 1e-9 from previous diff
                            parsed_components_list.append({
                                'type': 'R', 'name': f"R_{base_name}_{phase_pair_label}", 'nodes': (node1_str_conn, node2_str_conn),
                                'value': r_fd, 'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'LOADD'})
                        if l_fd > 1e-12:
                            parsed_components_list.append({
                                'type': 'L', 'name': f"L_{base_name}_{phase_pair_label}", 'nodes': (node1_str_conn, node2_str_conn),
                                'value': l_fd, 'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'LOADD'})
                        if c_fd > 1e-15:
                            parsed_components_list.append({
                                'type': 'C', 'name': f"C_{base_name}_{phase_pair_label}", 'nodes': (node1_str_conn, node2_str_conn),
                                'value': c_fd, 'original_line': original_line_info, 'three_phase_parent': base_name, 'three_phase_type': 'LOADD'}) 
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for LOADD {base_name}.")
                    continue
            else:
                error_log.append(L_PREFIX + f"Unrecognized netlist syntax: '{line_full}'")


        all_circuit_nodes = set()
        has_vs_components = any(comp['type'] == 'VS' for comp in parsed_components_list)
        has_is_components = any(comp['type'] == 'IS' for comp in parsed_components_list)
        has_controlled_sources = any(c['type'] in ['VCVS', 'VCCS', 'CCVS', 'CCCS'] for c in parsed_components_list)
        has_passive_components = any(c['type'] in ['R', 'L', 'C'] for c in parsed_components_list)
        ground_connected_vs_exists = False

        for comp_idx, comp_item in enumerate(parsed_components_list): # Use enumerate for unique auto-names if needed
            n1, n2 = comp_item['nodes']
            # Basic node name validation (alphanumeric or underscore)
            if not (n1 == '0' or (n1.replace('_', '').isalnum() and n1[0].isalpha() if '_' in n1 else n1.isalnum())):
                 error_log.append(f"Component {comp_item['name']} has invalid node name '{n1}'. Must be '0' or alphanumeric/underscore (starting letter if underscore used).")
            if not (n2 == '0' or (n2.replace('_', '').isalnum() and n2[0].isalpha() if '_' in n2 else n2.isalnum())):
                 error_log.append(f"Component {comp_item['name']} has invalid node name '{n2}'. Must be '0' or alphanumeric/underscore (starting letter if underscore used).")

            # Validate control nodes for VCVS and VCCS
            if comp_item.get('control_nodes'):
                cn1, cn2 = comp_item['control_nodes']
                if not (cn1 == '0' or (cn1.replace('_', '').isalnum() and cn1[0].isalpha() if '_' in cn1 else cn1.isalnum())):
                    error_log.append(f"Component {comp_item['name']} has invalid control node name '{cn1}'.")
                if not (cn2 == '0' or (cn2.replace('_', '').isalnum() and cn2[0].isalpha() if '_' in cn2 else cn2.isalnum())):
                    error_log.append(f"Component {comp_item['name']} has invalid control node name '{cn2}'.")
            all_circuit_nodes.add(n1)
            all_circuit_nodes.add(n2)
            if comp_item['type'] == 'VS' and ('0' in comp_item['nodes']):
                ground_connected_vs_exists = True

        # Post-loop checks
        if not parsed_components_list and netlist_content: # If content existed but nothing parsed
            error_log.append("Netlist has content, but no valid components or sources were parsed.")

        if not (has_vs_components or has_is_components or has_controlled_sources) and has_passive_components:
            error_log.append("Passive components found, but no voltage (VS) or current (IS) source defined in the netlist.")

        if '0' not in all_circuit_nodes and parsed_components_list : # If components exist but none connect to ground
            error_log.append("No component is connected to the reference node '0' (ground). Circuit analysis requires a ground reference.")

        if has_vs_components and not ground_connected_vs_exists:
            # Check if any VS is floating (both nodes non-zero)
            is_floating_vs_case = any(comp['type'] == 'VS' and '0' not in comp['nodes'] for comp in parsed_components_list)
            if is_floating_vs_case:
                error_log.append("Circuit contains voltage sources, but none are directly connected to ground '0', or some are floating. Floating VS requires supernode analysis (not fully supported in this version).")

        numeric_node_ids = set()
        for node_id_str in all_circuit_nodes:
            if node_id_str == '0':
                continue
            if not node_id_str.isdigit() or int(node_id_str) <= 0:
                error_log.append(f"Invalid node ID: '{node_id_str}'. Non-reference nodes must be positive integers (e.g., 1, 2, 3...).")
            else:
                numeric_node_ids.add(int(node_id_str))

        if not numeric_node_ids and any(c['type'] != 'VS' for c in parsed_components_list) and parsed_components_list:
             error_log.append("No valid numeric non-reference nodes (1, 2, ...) found for matrix construction, but passive components exist.")


        if freq_from_netlist is None:
            try:
                manual_freq_str = self.freq_details_entry.get()
                if manual_freq_str and manual_freq_str.strip():
                    manual_freq = float(manual_freq_str)
                    if manual_freq > 0:
                        freq_from_netlist = manual_freq
                        error_log.append("Note: Using frequency from manual entry as FREQ not found in netlist.")
                    else:
                        error_log.append("Manual frequency entry is not positive. Please define a valid FREQ in netlist or provide positive manual entry.")
                elif parsed_components_list: # Only error if components exist that need a freq
                     error_log.append("Frequency not defined in netlist or manual entry. Required for analysis.")
            except ValueError:
                error_log.append("Manual frequency entry is not a valid number. Please define FREQ in netlist.")
            except AttributeError:
                error_log.append("Frequency not defined in netlist and manual entry widget not accessible.")

        # Remove duplicate error messages
        if error_log:
            error_log = sorted(list(set(error_log)))

        return parsed_components_list, freq_from_netlist, error_log

    def _calculate_three_phase_results(self, analysis_results_mono, parsed_components_list):
        three_phase_summary = {}
        if not analysis_results_mono or not parsed_components_list:
            return three_phase_summary

        # 1. Group components by their three_phase_parent
        grouped_by_parent = {}
        for comp_mono in parsed_components_list:
            parent_name = comp_mono.get('three_phase_parent')
            if parent_name:
                if parent_name not in grouped_by_parent:
                    grouped_by_parent[parent_name] = {
                        'type': comp_mono.get('three_phase_type'),
                        'components_mono': [],
                        'original_line': comp_mono.get('original_line', "N/A") # Store once
                    }
                grouped_by_parent[parent_name]['components_mono'].append(comp_mono)
        
        nodal_voltages = analysis_results_mono.get('nodal_voltages_phasors', {})
        comp_currents_mono = analysis_results_mono.get('component_currents_phasors', {})
        comp_voltages_mono = analysis_results_mono.get('component_voltages_phasors', {})

        for parent_name, data in grouped_by_parent.items():
            parent_type = data['type']
            summary_data = {'type': parent_type, 'P3ph': 0.0, 'Q3ph': 0.0, 'S3ph_mag': 0.0, 'PF3ph': 1.0, 'errors': []}
            
            s_3ph_total_complex = 0j

            if parent_type == 'VSY':
                vs_a = next((c for c in data['components_mono'] if c['name'].endswith("_A")), None)
                vs_b = next((c for c in data['components_mono'] if c['name'].endswith("_B")), None)
                vs_c = next((c for c in data['components_mono'] if c['name'].endswith("_C")), None)

                if vs_a and vs_b and vs_c:
                    v_an = comp_voltages_mono.get(vs_a['name'], 0j) # Voltage across the source itself
                    v_bn = comp_voltages_mono.get(vs_b['name'], 0j)
                    v_cn = comp_voltages_mono.get(vs_c['name'], 0j)
                    i_a = comp_currents_mono.get(vs_a['name'], 0j)
                    i_b = comp_currents_mono.get(vs_b['name'], 0j)
                    i_c = comp_currents_mono.get(vs_c['name'], 0j)

                    s_3ph_total_complex = (v_an * i_a.conjugate() + 
                                           v_bn * i_b.conjugate() + 
                                           v_cn * i_c.conjugate())
                    
                    summary_data['Vph_avg_mag'] = (abs(v_an) + abs(v_bn) + abs(v_cn)) / 3.0
                    v_ab, v_bc, v_ca = v_an - v_bn, v_bn - v_cn, v_cn - v_an
                    summary_data['Vln_avg_mag'] = (abs(v_ab) + abs(v_bc) + abs(v_ca)) / 3.0
                    summary_data['Il_avg_mag'] = (abs(i_a) + abs(i_b) + abs(i_c)) / 3.0
                else: summary_data['errors'].append("Fases decompostas da VSY não encontradas.")

            elif parent_type == 'VSD':
                vs_ab = next((c for c in data['components_mono'] if c['name'].endswith("_AB")), None)
                vs_bc = next((c for c in data['components_mono'] if c['name'].endswith("_BC")), None)
                vs_ca = next((c for c in data['components_mono'] if c['name'].endswith("_CA")), None)

                if vs_ab and vs_bc and vs_ca:
                    v_ab_src = comp_voltages_mono.get(vs_ab['name'], 0j)
                    v_bc_src = comp_voltages_mono.get(vs_bc['name'], 0j)
                    v_ca_src = comp_voltages_mono.get(vs_ca['name'], 0j)
                    i_ab_src = comp_currents_mono.get(vs_ab['name'], 0j) # Current through internal delta source AB
                    i_bc_src = comp_currents_mono.get(vs_bc['name'], 0j)
                    i_ca_src = comp_currents_mono.get(vs_ca['name'], 0j)

                    s_3ph_total_complex = (v_ab_src * i_ab_src.conjugate() +
                                           v_bc_src * i_bc_src.conjugate() +
                                           v_ca_src * i_ca_src.conjugate())

                    summary_data['Vln_avg_mag'] = (abs(v_ab_src) + abs(v_bc_src) + abs(v_ca_src)) / 3.0
                    i_la, i_lb, i_lc = i_ab_src - i_ca_src, i_bc_src - i_ab_src, i_ca_src - i_bc_src
                    summary_data['Il_avg_mag'] = (abs(i_la) + abs(i_lb) + abs(i_lc)) / 3.0
                else: summary_data['errors'].append("Fases decompostas da VSD não encontradas.")

            elif parent_type == 'LOADY':
                # Assume balanced load for Z_phase display, but calculate power from individual phases
                v_phases, i_phases, z_phases = [], [], []
                for phase_label in ['A', 'B', 'C']:
                    # Find nodes for this phase of the LOADY
                    # Example: R_LOADY1_A has nodes (nA, nN)
                    comp_r = next((c for c in data['components_mono'] if c['name'] == f"R_{parent_name}_{phase_label}"), None)
                    comp_l = next((c for c in data['components_mono'] if c['name'] == f"L_{parent_name}_{phase_label}"), None)
                    comp_c = next((c for c in data['components_mono'] if c['name'] == f"C_{parent_name}_{phase_label}"), None)
                    
                    # Determine phase node and neutral node from any of the components
                    ref_comp_for_nodes = comp_r or comp_l or comp_c
                    if not ref_comp_for_nodes: continue # Skip phase if no components

                    node_phase_str, node_neutral_str = ref_comp_for_nodes['nodes']
                    v_ph = nodal_voltages.get(node_phase_str, 0j) - nodal_voltages.get(node_neutral_str, 0j)
                    
                    i_ph_total = 0j
                    if comp_r: i_ph_total += comp_currents_mono.get(comp_r['name'], 0j)
                    if comp_l: i_ph_total += comp_currents_mono.get(comp_l['name'], 0j)
                    if comp_c: i_ph_total += comp_currents_mono.get(comp_c['name'], 0j)

                    v_phases.append(v_ph); i_phases.append(i_ph_total)
                    if abs(i_ph_total) > 1e-9: z_phases.append(v_ph / i_ph_total)
                    s_3ph_total_complex += v_ph * i_ph_total.conjugate()

                if v_phases and i_phases:
                    summary_data['Vph_avg_mag'] = sum(abs(v) for v in v_phases) / len(v_phases)
                    summary_data['Il_avg_mag'] = sum(abs(i) for i in i_phases) / len(i_phases) # For Y, I_line = I_phase
                    if z_phases: summary_data['Zph_avg_phasor'] = sum(z_phases) / len(z_phases) # Average Z

            elif parent_type == 'LOADD':
                v_lines, i_deltas, z_deltas = [], [], []
                line_currents_at_nodes = {'A':0j, 'B':0j, 'C':0j} # To sum for I_La, I_Lb, I_Lc

                for phase_pair_label, nodes_str_pair in [("AB", ('A','B')), ("BC",('B','C')), ("CA",('C','A'))]:
                    # Find nodes for this phase of the LOADD
                    # Example: R_LOADD1_AB has nodes (nA, nB)
                    comp_r = next((c for c in data['components_mono'] if c['name'] == f"R_{parent_name}_{phase_pair_label}"), None)
                    comp_l = next((c for c in data['components_mono'] if c['name'] == f"L_{parent_name}_{phase_pair_label}"), None)
                    comp_c = next((c for c in data['components_mono'] if c['name'] == f"C_{parent_name}_{phase_pair_label}"), None)

                    ref_comp_for_nodes = comp_r or comp_l or comp_c
                    if not ref_comp_for_nodes: continue

                    node1_str, node2_str = ref_comp_for_nodes['nodes']
                    v_line = nodal_voltages.get(node1_str, 0j) - nodal_voltages.get(node2_str, 0j)
                    
                    i_delta_total = 0j
                    if comp_r: i_delta_total += comp_currents_mono.get(comp_r['name'], 0j)
                    if comp_l: i_delta_total += comp_currents_mono.get(comp_l['name'], 0j)
                    if comp_c: i_delta_total += comp_currents_mono.get(comp_c['name'], 0j)

                    v_lines.append(v_line); i_deltas.append(i_delta_total)
                    if abs(i_delta_total) > 1e-9: z_deltas.append(v_line / i_delta_total)
                    s_3ph_total_complex += v_line * i_delta_total.conjugate()

                    # Accumulate for line currents: I_La = I_AB - I_CA, etc.
                    # Node labels A, B, C are from the original LOADD definition (e.g. LOADD1 NA NB NC R L C)
                    # We need to map phase_pair_label (AB, BC, CA) to the actual node names.
                    # This requires parsing the original_line or storing nodes with the parent.
                    # For now, assume a simple mapping if possible, or skip detailed line current calculation here.
                    # The power calculation is correct based on internal delta currents and voltages.

                if v_lines and i_deltas:
                    summary_data['Vln_avg_mag'] = sum(abs(v) for v in v_lines) / len(v_lines) # For Delta, V_line = V_phase
                    # Line current calculation for Delta is more involved if not directly available.
                    # For now, report average delta current as "Iph_avg_mag"
                    summary_data['Iph_avg_mag'] = sum(abs(i) for i in i_deltas) / len(i_deltas)
                    if z_deltas: summary_data['Zph_avg_phasor'] = sum(z_deltas) / len(z_deltas)

            summary_data['P3ph'] = s_3ph_total_complex.real
            summary_data['Q3ph'] = s_3ph_total_complex.imag
            summary_data['S3ph_mag'] = abs(s_3ph_total_complex)
            if summary_data['S3ph_mag'] > 1e-9:
                summary_data['PF3ph'] = summary_data['P3ph'] / summary_data['S3ph_mag']
                summary_data['PF3ph'] = max(-1.0, min(1.0, summary_data['PF3ph'])) # Clamp
            else:
                summary_data['PF3ph'] = 1.0 if abs(summary_data['P3ph']) < 1e-9 else 0.0

            three_phase_summary[parent_name] = summary_data
        return three_phase_summary

    def _on_parameter_change(self, event=None, from_combobox_value=None):
        self.analysis_performed_successfully = False
        # This might trigger RLC equivalent analysis if we want to keep that path.
        # For now, it just flags that parameters changed.

    def _on_formatting_change(self, event_or_choice=None):
        if self.results_text.get("1.0", "end-1c").strip() and self.analysis_performed_successfully:
             self.analyze_circuit() # Re-run analysis to reformat output

    def _on_include_component_change(self, event=None):
        # This is for the manual RLC equivalent input, less critical for nodal
        self.r_entry.configure(state="normal" if self.include_r_var.get() else "disabled")
        self.l_entry.configure(state="normal" if self.include_l_var.get() else "disabled")
        self.c_entry.configure(state="normal" if self.include_c_var.get() else "disabled")
        self.analysis_performed_successfully = False

    def _format_value(self, value, unit=""):
        # (Original _format_value method - assumed to be correct and kept as is)
        if isinstance(value, str): return f"{value} {unit}".strip()
        if not isinstance(value, (int, float, complex)): return f"{str(value)} {unit}".strip()
        if isinstance(value, complex):
            if math.isinf(value.real) or math.isinf(value.imag) or math.isnan(value.real) or math.isnan(value.imag): return f"Indefinido/Infinito {unit}".strip()
            value_to_format = abs(value)
        else: value_to_format = value
        if math.isinf(value_to_format): return f"Infinito {unit}".strip()
        if math.isnan(value_to_format): return f"Indefinido {unit}".strip()
        try: dp = int(self.decimal_places_var.get())
        except ValueError: dp = 3
        fmt_string = f"{{:.{dp}e}}" if self.scientific_notation_var.get() or (abs(value_to_format) >= 1e7 or (abs(value_to_format) < 1e-4 and value_to_format != 0)) else f"{{:.{dp}f}}"
        try: return f"{fmt_string.format(value_to_format)} {unit}".strip()
        except: return f"{value_to_format:.{dp}e} {unit}".strip()


    def save_configuration(self):
        # (Original save_configuration method - kept as is)
        config_data = {
            'r_val': self.r_entry.get(), 'l_val': self.l_entry.get(), 'c_val': self.c_entry.get(),
            'include_r': self.include_r_var.get(), 'include_l': self.include_l_var.get(), 'include_c': self.include_c_var.get(),
            'v_mag': self.v_mag_entry.get(), 'v_phase_deg': self.v_phase_entry.get(),
            'freq_details': self.freq_details_entry.get(),
            'angle_unit': self.angle_unit.get(), 'topology': self.circuit_topology_var.get(),
            'decimal_places': self.decimal_places_var.get(),
            'scientific_notation': self.scientific_notation_var.get(),
            'netlist_content': self.netlist_textbox.get("1.0", tk.END).strip(),
            'fp_desired': self.fp_desired_entry.get()
        }
        try:
            fp_path = filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json"),("All","*.*")],title="Salvar Config.")
            if fp_path:
                with open(fp_path,'w') as f: json.dump(config_data,f,indent=4)
                messagebox.showinfo("Salvar","Configuração salva!")
        except Exception as e: messagebox.showerror("Erro Salvar",f"Erro: {e}")

    def load_configuration(self):
        # (Original load_configuration method - kept as is)
        try:
            fp_path = filedialog.askopenfilename(defaultextension=".json",filetypes=[("JSON","*.json"),("All","*.*")],title="Carregar Config.")
            if fp_path:
                with open(fp_path,'r') as f: ld=json.load(f)
                self.r_entry.delete(0,tk.END); self.r_entry.insert(0,ld.get('r_val',"10"))
                self.l_entry.delete(0,tk.END); self.l_entry.insert(0,ld.get('l_val',"0.01"))
                self.c_entry.delete(0,tk.END); self.c_entry.insert(0,ld.get('c_val',"0.00001"))
                self.include_r_var.set(ld.get('include_r', True)); self.include_l_var.set(ld.get('include_l', True)); self.include_c_var.set(ld.get('include_c', True))
                self._on_include_component_change()
                self.v_mag_entry.delete(0,tk.END); self.v_mag_entry.insert(0,ld.get('v_mag',"10"))
                self.v_phase_entry.delete(0,tk.END); self.v_phase_entry.insert(0,ld.get('v_phase_deg',"0"))
                self.freq_details_entry.delete(0,tk.END); self.freq_details_entry.insert(0,ld.get('freq_details',"60")) # Default freq 60
                self.angle_unit.set(ld.get('angle_unit',"degrees")); self.circuit_topology_var.set(ld.get('topology',"Série"))
                self.decimal_places_var.set(ld.get('decimal_places',"3")); self.scientific_notation_var.set(ld.get('scientific_notation',False))
                self.netlist_textbox.delete("1.0", tk.END); self.netlist_textbox.insert("1.0", ld.get('netlist_content', "# Insira netlist para análise nodal"))
                self.fp_desired_entry.delete(0, tk.END); self.fp_desired_entry.insert(0, ld.get('fp_desired', ""))
                messagebox.showinfo("Carregar","Configuração carregada!")
                self._on_parameter_change(); self.analysis_performed_successfully = False
                self._clear_main_plot(initial_message="Diagrama Fasorial: Configuração carregada, analise novamente.")
                self._clear_static_circuit_diagram(initial_message="Diagrama do Circuito: Configuração carregada.")
        except Exception as e: messagebox.showerror("Erro Carregar",f"Erro: {e}")


    def _set_entry_error_style(self, entry_key, is_error=True):
        # (Original _set_entry_error_style method - kept as is)
        if entry_key in self.entry_widgets:
            widget=self.entry_widgets[entry_key]
            try:
                dcs=ctk.ThemeManager.theme["CTkEntry"]["border_color"]; cm=ctk.get_appearance_mode().lower()
                nc=dcs[0] if isinstance(dcs,list) and cm=="light" else (dcs[1] if isinstance(dcs,list) else dcs)
                if nc is None: nc="#979797" if cm=="light" else "#565B5E"
            except: nc="gray50"
            tc=self.error_border_color if is_error else nc
            current_border_color = widget.cget("border_color")
            if isinstance(current_border_color, (list, tuple)) and len(current_border_color) == 2: widget.configure(border_color=[tc,tc])
            elif isinstance(current_border_color, str): widget.configure(border_color=tc)

    def _clear_all_entry_error_styles(self):
        # (Original _clear_all_entry_error_styles method - kept as is)
        for wk in self.entry_widgets: self._set_entry_error_style(wk,is_error=False)

    def _validate_all_parameters(self, silent=True): # This validates manual RLC eq. fields
        # (Original _validate_all_parameters method - kept as is for manual RLC path)
        self._clear_all_entry_error_styles(); params={}; error_messages=[]; error_fields=[]
        def gf(ew,pn,hn,include_var,is_optional=False):
            val_str=ew.get()
            if is_optional and not val_str: params[pn]=None; return None
            if include_var is not None and not include_var.get(): params[pn]=0.0; return 0.0
            try: v=float('inf') if val_str.lower()=='inf' else float(val_str); params[pn]=v; return v
            except ValueError:
                if not is_optional and (include_var is None or include_var.get()): error_messages.append(f"{hn} inválido(a)."); error_fields.append(pn)
                params[pn]=0.0 if not is_optional else None; return None
        params['topology']=self.circuit_topology_var.get()
        gf(self.r_entry,'r_val',"R_eq",self.include_r_var); gf(self.l_entry,'l_val',"L_eq",self.include_l_var); gf(self.c_entry,'c_val',"C_eq",self.include_c_var)
        gf(self.v_mag_entry,'v_mag',"Vmag",None); gf(self.v_phase_entry,'v_phase_deg',"Fase Fonte",None)
        if params.get('r_val') is not None and params['r_val']<0 and self.include_r_var.get(): error_messages.append("R_eq >=0."); error_fields.append('r_val')
        if params.get('l_val') is not None and params['l_val']<0 and self.include_l_var.get(): error_messages.append("L_eq >=0."); error_fields.append('l_val')
        if params.get('c_val') is not None and params['c_val']<0 and self.include_c_var.get(): error_messages.append("C_eq >=0."); error_fields.append('c_val')
        if params.get('v_mag') is not None and params['v_mag']<0: error_messages.append("Vmag >=0."); error_fields.append('v_mag')
        params['freq_details']=None; fds_val=gf(self.freq_details_entry,'freq_details_val',"Freq. Análise",None)
        if fds_val is not None and fds_val<=0: error_messages.append("Freq. Análise >0."); error_fields.append('freq_details')
        elif fds_val is not None: params['freq_details']=fds_val
        for fk in set(error_fields): self._set_entry_error_style(fk,True)
        if error_messages:
            if not silent: messagebox.showerror("Erro Entrada (Manual)","\n".join(list(dict.fromkeys(error_messages))))
            return None,list(dict.fromkeys(error_messages))
        return params,None


    def clear_entries(self):
        # (Original clear_entries method - updated netlist example)
        self._clear_all_entry_error_styles()
        self.r_entry.delete(0,"end"); self.r_entry.insert(0,"10"); self.l_entry.delete(0,"end"); self.l_entry.insert(0,"0.01"); self.c_entry.delete(0,"end"); self.c_entry.insert(0,"0.00001")
        self.include_r_var.set(True); self.include_l_var.set(True); self.include_c_var.set(True); self._on_include_component_change()
        self.v_mag_entry.delete(0,"end"); self.v_mag_entry.insert(0,"10"); self.v_phase_entry.delete(0,"end"); self.v_phase_entry.insert(0,"0")
        self.freq_details_entry.delete(0,"end"); self.freq_details_entry.insert(0,"60"); self.fp_desired_entry.delete(0,tk.END) # Default freq 60
        self.angle_unit.set("degrees"); self.circuit_topology_var.set("Série"); self.decimal_places_var.set("3"); self.scientific_notation_var.set(False)
        self.netlist_textbox.delete("1.0",tk.END);
        self.netlist_textbox.insert("1.0",
            "# Exemplo Netlist para Análise Nodal:\n"
            "# VS1 1 0 AC 10 0  # Fonte: Nome, Nó+, Nó-, Tipo, Vmag, Vfase_graus\n"
            "# IS1 2 0 AC 1 0 # Fonte Corrente: Nome, Nó_Saída(->), Nó_Entrada(<-), Tipo, Imag, Ifase_graus\n"
            "# R1 1 2 100       # Resistor: Nome, Nó1, Nó2, Valor_Ohms\n"
            "# L1 2 0 0.05      # Indutor: Nome, Nó1, Nó2, Valor_Henries\n"
            "# C1 1 2 1e-4      # Capacitor: Nome, Nó1, Nó2, Valor_Farads\n"
            "# FREQ 60          # Frequência de análise em Hz\n"
            "# --- Fontes Controladas (Exemplos) ---\n"
            "# E_exemplo 3 0 1 2 2.0      # VCVS: E<nome> <nó+> <nó-> <nó_ctrl+> <nó_ctrl-> <ganho_V>\n"
            "# G_exemplo 4 0 1 2 0.1      # VCCS: G<nome> <nó_saída> <nó_entrada> <nó_ctrl+> <nó_ctrl-> <transcond_Gm>\n"
            "# VS_mon 5 0 AC 1 0          # Fonte VS para monitorar corrente para H e F (exemplo)\n" # Note: VS_mon must be unique if multiple H/F sources use different monitor points.
            "# H_exemplo 6 0 VS_mon 50    # CCVS: H<nome> <nó+> <nó-> <nome_VS_monitor> <ganho_Rm>\n"
            "# F_exemplo 7 0 VS_mon 100   # CCCS: F<nome> <nó_saída> <nó_entrada> <nome_VS_monitor> <ganho_beta>\n\n"
            "# --- Elementos Trifásicos (Exemplos) ---\n"
            "# VSY FonteY 1 2 3 N_Y AC 127 0 ABC   # Fonte Y: Nome, nA, nB, nC, nN, AC, Vmag_fase, Vfas_faseA, Seq\n"
            "# LOADY CargaY 1 2 3 N_Y 10 0.01 0    # Carga Y: Nome, nA, nB, nC, nN, R_f, L_f, C_f\n"
        )
        self.results_text.configure(state="normal"); self.results_text.delete("1.0","end"); self.results_text.configure(state="disabled")
        self._clear_main_plot(initial_message="Diagrama Fasorial: Insira netlist e analise.")
        self._clear_static_circuit_diagram(initial_message="Diagrama do Circuito: Entradas limpas.")
        self._on_parameter_change(); self.analysis_performed_successfully=False


    def _grab_toplevel_safely(self, toplevel_window):
        # (Original _grab_toplevel_safely method - kept as is)
        if toplevel_window and toplevel_window.winfo_exists():
            try: toplevel_window.grab_set()
            except tk.TclError: pass

    def show_about_dialog_ctk(self):
        # (Original show_about_dialog_ctk method - updated version number/features)
        if self.about_dialog_window and self.about_dialog_window.winfo_exists(): self.about_dialog_window.lift(); self.about_dialog_window.focus_set(); return
        self.about_dialog_window=ctk.CTkToplevel(self.master); self.about_dialog_window.title("Sobre Analisador de Circuito CA"); self.about_dialog_window.geometry("500x680") # Slightly taller
        self.about_dialog_window.transient(self.master); self.about_dialog_window.after(50,self._grab_toplevel_safely,self.about_dialog_window)
        scroll_frame=ctk.CTkScrollableFrame(self.about_dialog_window); scroll_frame.pack(expand=True,fill="both") # Removed fg_color for default
        content_frame=ctk.CTkFrame(scroll_frame); content_frame.pack(expand=True,fill="x",padx=15,pady=15)
        ctk.CTkLabel(content_frame,text="Analisador de Circuito CA",font=ctk.CTkFont(size=18,weight="bold")).pack(pady=(0,10))
        info_text=("**Versão:** 3.3.0 (Parse Trifásico Inicial)\n\nFerramenta para análise de circuitos CA em frequência única.\n\n"
                   "**Funcionalidades Atuais:**\n- Análise Nodal de circuitos RLC com fontes de tensão CA independentes.\n"
                   "- Entrada via Netlist simplificada.\n"
                   "- Suporte a fontes de corrente CA independentes (IS).\n"
                   "- Parser para fontes trifásicas (VSY, VSD) e cargas (LOADY, LOADD) equilibradas,\n"
                   "  decompondo-as em equivalentes monofásicos para análise.\n"
                   "- Reconhecimento de fontes controladas (VCVS, VCCS, CCVS, CCCS) na netlist.\n"
                   "- Cálculo de tensões nodais, correntes e tensões em componentes.\n"
                   "- Cálculo de potência (P,Q,S) e Fator de Potência para a fonte principal.\n"
                   "- Correção de Fator de Potência (baseado nos resultados da fonte principal).\n"
                   "- Diagrama Fasorial (Tensões Nodais, Corrente da Fonte Principal).\n"
                   "- Diagrama de Circuito (Placeholder para netlist).\n"
                   "- Salvar/Carregar configurações (incluindo netlist).\n\n"
                   "**Roadmap:**\n- Suporte a supernós (fontes de tensão flutuantes).\n"
                   "- Estampagem MNA completa para fontes controladas (VCVS, VCCS, CCVS, CCCS).\n"
                   "- Análise de sistemas trifásicos desequilibrados (longo prazo).\n"
                   "- Melhorias no desenho do diagrama de circuito a partir da netlist.\n"
                   "- Análise de varredura de frequência.\n"
                   "- Editor Visual (Longo prazo).")
        ctk.CTkLabel(content_frame,text=info_text,justify="left",wraplength=420).pack(pady=10,padx=5,anchor="w")
        ctk.CTkButton(content_frame,text="Fechar",command=self.about_dialog_window.destroy,width=100).pack(pady=(15,5))
        self.about_dialog_window.after(10,self._center_toplevel_after_draw,self.about_dialog_window); self.about_dialog_window.focus_set()

    def _center_toplevel_after_draw(self, toplevel_window):
        # (Original _center_toplevel_after_draw method - kept as is)
        toplevel_window.update_idletasks()
        mw,mh,mx,my=self.master.winfo_width(),self.master.winfo_height(),self.master.winfo_x(),self.master.winfo_y()
        pw,ph=toplevel_window.winfo_width(),toplevel_window.winfo_height()
        if pw<=1 or ph<=1:
            try: s=str(toplevel_window.geometry()).split('+')[0]; pw,ph=map(int,s.split('x'))
            except: pw,ph=500,680 # Match about dialog size
        toplevel_window.geometry(f"{pw}x{ph}+{(mx+(mw-pw)//2)}+{(my+(mh-ph)//2)}")


    def _perform_nodal_analysis(self, parsed_components_list, frequency):
        analysis_results = {
            'nodal_voltages_phasors': {}, 'component_currents_phasors': {}, 'component_voltages_phasors': {},
            'v_source_phasor': None, 'i_source_total_phasor': None, 'z_equivalent_total_phasor': None,
            'p_total_avg_W': None, 'q_total_VAR': None, 's_total_apparent_VA': None, 'fp_total': None,
            'freq': frequency, 'topology': "Nodal Analysis", 'error_messages': []
        }
        omega = 2 * math.pi * frequency
        if omega == 0 and any(c['type'] in ['L', 'C'] for c in parsed_components_list):
            analysis_results['error_messages'].append("Frequency is zero. AC analysis with L or C is ill-defined. Consider DC analysis or non-zero frequency.")
            # For L and C, impedance is 0 or inf.
            # If only R, it's DC, but this is an AC analyzer.
            if not any(c['type'] in ['L', 'C'] for c in parsed_components_list): # Only R and VS
                 pass # Could proceed as DC if omega handled carefully for R-only circuits
            else:
                 return analysis_results


        all_nodes = set(['0'])
        for comp in parsed_components_list: all_nodes.update(comp['nodes'])

        numeric_nodes = [int(n) for n in all_nodes if n != '0' and n.isdigit()]
        
        # Check for floating VS for the initial error check condition
        has_floating_vs = any(c['type'].upper() == 'VS' and 
                              c['nodes'][0] != '0' and c['nodes'][1] != '0' 
                              for c in parsed_components_list)

        if not numeric_nodes and not has_floating_vs:
            if parsed_components_list: 
                 analysis_results['error_messages'].append("Nenhum nó numérico válido (ex: 1, 2, ...) encontrado para a construção da matriz, e nenhuma fonte de tensão flutuante para definir equações adicionais.")
            else: # No components at all
                 analysis_results['error_messages'].append("No components found to analyze.")
            return analysis_results

        num_actual_nodes = max(numeric_nodes) if numeric_nodes else 0

        # --- Stage 1: Identify all sources requiring auxiliary current variables & MNA sizing ---
        aux_current_vars_info = [] # List of dicts: {'name': str, 'comp_ref': dict, 'mna_idx': int, 'type': str}
                                   # type can be 'IndepFV', 'VCVS', 'CCVS_self', 'MonitoredGroundedVS'
        
        # Collect Independent Floating VS
        for comp in parsed_components_list:
            if comp['type'] == 'VS':
                n1_str, n2_str = comp['nodes']
                if n1_str != '0' and n2_str != '0':
                    if not (n1_str.isdigit() and int(n1_str) > 0 and n2_str.isdigit() and int(n2_str) > 0):
                        analysis_results['error_messages'].append(f"Fonte de tensão flutuante {comp['name']} ({n1_str}-{n2_str}) tem nós não numéricos ou não positivos.")
                        continue # Skip adding this problematic FV
                    if not any(aux_info['name'] == comp['name'] for aux_info in aux_current_vars_info):
                        aux_current_vars_info.append({'name': comp['name'], 'comp_ref': comp, 'type': 'IndepFV'})
        
        # Collect VCVS
        for comp in parsed_components_list:
            if comp['type'] == 'VCVS':
                if not any(aux_info['name'] == comp['name'] for aux_info in aux_current_vars_info):
                    aux_current_vars_info.append({'name': comp['name'], 'comp_ref': comp, 'type': 'VCVS'})

        # Collect CCVS (for their own current I_H)
        for comp in parsed_components_list:
            if comp['type'] == 'CCVS':
                if not any(aux_info['name'] == comp['name'] for aux_info in aux_current_vars_info):
                    aux_current_vars_info.append({'name': comp['name'], 'comp_ref': comp, 'type': 'CCVS_self'})

        # Identify Grounded VS used as control current monitors (for CCVS and future CCCS)
        controlling_vs_names_for_H_or_F = set()
        for comp in parsed_components_list:
            if comp['type'] in ['CCVS', 'CCCS'] and comp.get('control_source_name'):
                controlling_vs_names_for_H_or_F.add(comp['control_source_name'])

        for vs_name_ctrl in controlling_vs_names_for_H_or_F:
            found_vs_comp = next((c for c in parsed_components_list if c['name'] == vs_name_ctrl and c['type'] == 'VS'), None)
            if found_vs_comp:
                n1_vs, n2_vs = found_vs_comp['nodes']
                is_grounded = '0' in found_vs_comp['nodes']
                is_floating = n1_vs != '0' and n2_vs != '0' # Check if it was already added as IndepFV

                if is_grounded and not is_floating:
                    if not any(aux_info['name'] == vs_name_ctrl for aux_info in aux_current_vars_info):
                        aux_current_vars_info.append({'name': vs_name_ctrl, 'comp_ref': found_vs_comp, 'type': 'MonitoredGroundedVS'})
            # Error for not found VS control source is handled later during CCVS/CCCS stamping if map lookup fails

        # --- Stage 2: Assign MNA indices to auxiliary current variables and create map ---
        source_name_to_current_var_idx_map = {}
        current_mna_aux_idx_offset = 0
        for aux_var in aux_current_vars_info:
            assigned_idx = num_actual_nodes + current_mna_aux_idx_offset
            aux_var['mna_idx'] = assigned_idx
            source_name_to_current_var_idx_map[aux_var['name']] = assigned_idx
            current_mna_aux_idx_offset += 1
        
        num_total_aux_vars = len(aux_current_vars_info)
        mna_size = num_actual_nodes + num_total_aux_vars
        
        # For debug string and potentially other logic if needed
        num_independent_floating_vs = sum(1 for aux in aux_current_vars_info if aux['type'] == 'IndepFV')
        num_vcvs = sum(1 for aux in aux_current_vars_info if aux['type'] == 'VCVS')
        num_vccs = sum(1 for comp in parsed_components_list if comp['type'] == 'VCCS')
        num_ccvs_self = sum(1 for aux in aux_current_vars_info if aux['type'] == 'CCVS_self') # CCVS introduces its own current
        num_cccs = sum(1 for comp in parsed_components_list if comp['type'] == 'CCCS') # CCCS uses an existing current
        num_monitored_grounded_vs = sum(1 for aux in aux_current_vars_info if aux['type'] == 'MonitoredGroundedVS')

        
        if mna_size == 0:
            if parsed_components_list:
                analysis_results['error_messages'].append("Circuito mal definido ou vazio: Tamanho da matriz MNA seria zero, mas componentes existem (ex: componentes conectados apenas ao terra ou definições de nó inválidas).")
            else: # No components
                 analysis_results['error_messages'].append("Nenhum componente encontrado para analisar.")
            return analysis_results

        if analysis_results['error_messages'] and any("tem nós não numéricos ou não positivos" in e for e in analysis_results['error_messages']):
            return analysis_results # Critical error from FV node validation

        # --- Initialize M_matrix and Z_vector ---
        M_matrix = np.zeros((mna_size, mna_size), dtype=complex)
        Z_vector = np.zeros(mna_size, dtype=complex)
        
        defined_voltage_nodes = {} # node_idx (0-based) -> voltage_phasor
        primary_source_info = None
        for comp in parsed_components_list:
            if comp['type'].upper() == 'VS':
                v_mag, v_phase_deg = comp['v_mag'], comp['v_phase_deg']
                v_phasor = cmath.rect(v_mag, math.radians(v_phase_deg))
                if primary_source_info is None:
                    primary_source_info = {'name': comp['name'], 'nodes': comp['nodes'], 'phasor': v_phasor}
                    analysis_results['v_source_phasor'] = v_phasor

                n1_str, n2_str = comp['nodes']
                node_k_idx, fixed_node_val = -1, None
                if n1_str != '0' and n2_str == '0': node_k_idx, fixed_node_val = int(n1_str) - 1, v_phasor
                elif n2_str != '0' and n1_str == '0': node_k_idx, fixed_node_val = int(n2_str) - 1, -v_phasor
                
                if fixed_node_val is not None: # This is a grounded source
                    if not (0 <= node_k_idx < num_actual_nodes):
                        analysis_results['error_messages'].append(f"Índice de nó {node_k_idx+1} (da fonte VS {comp['name']}) está fora dos limites para equações KCL (nó máx: {num_actual_nodes}).")
                        continue 

                    if node_k_idx in defined_voltage_nodes:
                        if not cmath.isclose(defined_voltage_nodes[node_k_idx], fixed_node_val):
                            analysis_results['error_messages'].append(f"Nó {node_k_idx+1} tem definições de tensão conflitantes de múltiplas fontes aterradas (ex: {comp['name']}).")
                    else: 
                        defined_voltage_nodes[node_k_idx] = fixed_node_val
                        # Estampar esta tensão conhecida no sistema MNA (parte KCL)
                        M_matrix[node_k_idx, :] = 0.0  # Zera a linha KCL para este nó
                        M_matrix[node_k_idx, node_k_idx] = 1.0
                        Z_vector[node_k_idx] = fixed_node_val
                # Fontes flutuantes (n1_str != '0' and n2_str != '0') são tratadas por num_floating_vs e serão estampadas depois.

        if analysis_results['error_messages'] and "conflicting voltage" in "".join(analysis_results['error_messages']): return analysis_results # Critical error
        if analysis_results['error_messages'] and "fora dos limites para equações KCL" in "".join(analysis_results['error_messages']): return analysis_results

        # Estampagem de Componentes Passivos (R, L, C)
        for comp in parsed_components_list:
            comp_type, value = comp['type'].upper(), comp['value']
            n1_str, n2_str = comp['nodes']
            
            # Ignorar fontes de tensão e corrente nesta seção de estampagem passiva
            if comp_type == 'VS' or comp_type == 'IS':
                continue
            
            y_comp = 0j
            if comp_type == 'R':
                y_comp = 1.0 / value if value > 1e-12 else 1.0 / 1e-12 # Avoid div by zero, approx short
                if value <= 1e-12 : analysis_results['error_messages'].append(f"Warning: R='{comp['name']}' near zero, approximated as high conductance.")
            elif comp_type == 'L':
                if omega == 0: y_comp = 1.0/1e-12 # Short at DC
                elif value <= 1e-12 : y_comp = 1.0/1e-12 # L effectively zero, approx short.
                else: y_comp = 1.0 / (1j * omega * value)
            elif comp_type == 'C':
                if omega == 0: y_comp = 1j * omega * 1e-12 # Open at DC (very small Y)
                elif value <= 1e-15 : y_comp = 1j * omega * 1e-15 # C effectively zero, approx open.
                else: y_comp = 1j * omega * value
            else: # Tipos desconhecidos ou não passivos (já filtrados acima, mas para robustez)
                continue

            # Obter índices dos nós (0-based para num_actual_nodes)
            # Node indices are only valid if they are numeric and within the range [0, num_actual_nodes-1]
            n1_idx = -1
            if n1_str != '0' and n1_str.isdigit():
                temp_idx = int(n1_str) - 1
                if 0 <= temp_idx < num_actual_nodes:
                    n1_idx = temp_idx
            
            n2_idx = -1
            if n2_str != '0' and n2_str.isdigit():
                temp_idx = int(n2_str) - 1
                if 0 <= temp_idx < num_actual_nodes:
                    n2_idx = temp_idx

            # Validação adicional de índice para garantir que estão dentro dos limites de num_actual_nodes
            # para nós não-referência. Se um nó string não for '0' mas não mapear para um nX_idx válido, é um erro.
            if n1_str != '0' and n1_idx == -1 :
                analysis_results['error_messages'].append(f"Nó {n1_str} do componente {comp['name']} fora dos limites válidos ({num_actual_nodes} nós) para estampagem passiva.")
                continue 
            if n2_str != '0' and n2_idx == -1 :
                analysis_results['error_messages'].append(f"Nó {n2_str} do componente {comp['name']} fora dos limites válidos ({num_actual_nodes} nós) para estampagem passiva.")
                continue

            # Estampagem na M_matrix e Z_vector
            # Node 1 related stamping
            if n1_idx != -1: # Nó 1 não é referência
                if n1_idx not in defined_voltage_nodes: # Nó 1 tem tensão desconhecida
                    M_matrix[n1_idx, n1_idx] += y_comp
                    if n2_idx != -1 and n2_idx in defined_voltage_nodes: # Conectado a nó 2 com tensão definida
                        Z_vector[n1_idx] += y_comp * defined_voltage_nodes[n2_idx]
                # Se n1_idx está em defined_voltage_nodes, sua linha KCL já foi substituída por V_n1 = V_fixa.
                # A corrente devido a este componente em um nó adjacente com tensão definida é tratada abaixo.
            
            # Node 2 related stamping
            if n2_idx != -1: # Nó 2 não é referência
                if n2_idx not in defined_voltage_nodes: # Nó 2 tem tensão desconhecida
                    M_matrix[n2_idx, n2_idx] += y_comp
                    if n1_idx != -1 and n1_idx in defined_voltage_nodes: # Conectado a nó 1 com tensão definida
                        Z_vector[n2_idx] += y_comp * defined_voltage_nodes[n1_idx]
                # Se n2_idx está em defined_voltage_nodes, sua linha KCL já foi substituída por V_n2 = V_fixa.

            # Off-diagonal elements
            if n1_idx != -1 and n2_idx != -1: # Ambos não são referência
                if n1_idx not in defined_voltage_nodes and n2_idx not in defined_voltage_nodes: # E nenhum deles tem tensão definida
                    M_matrix[n1_idx, n2_idx] -= y_comp
                    M_matrix[n2_idx, n1_idx] -= y_comp
        
        if analysis_results['error_messages'] and any("fora dos limites válidos" in e for e in analysis_results['error_messages']):
            return analysis_results # Retorna se houver erros de índice

        # Estampagem de Fontes de Corrente Independentes (IS)
        for comp in parsed_components_list:
            if comp['type'].upper() == 'IS':
                i_mag, i_phase_deg = comp['i_mag'], comp['i_phase_deg']
                i_phasor = cmath.rect(i_mag, math.radians(i_phase_deg))
                node_out_str, node_in_str = comp['nodes']
                
                if node_out_str != '0':
                    node_out_idx = int(node_out_str) - 1 # Assume parser validated node_out_str is digit
                    if 0 <= node_out_idx < num_actual_nodes and node_out_idx not in defined_voltage_nodes:
                        Z_vector[node_out_idx] += i_phasor
                
                if node_in_str != '0':
                    node_in_idx = int(node_in_str) - 1 # Assume parser validated node_in_str is digit
                    if 0 <= node_in_idx < num_actual_nodes and node_in_idx not in defined_voltage_nodes:
                        Z_vector[node_in_idx] -= i_phasor

        # --- Stamping for sources in aux_current_vars_info ---
        # This loop handles IndepFV, VCVS, and MonitoredGroundedVS KCL contributions
        # CCVS_self contributions are handled in their specific loop later.
        for aux_var_info in aux_current_vars_info:
            comp_ref = aux_var_info['comp_ref']
            current_var_idx = aux_var_info['mna_idx'] # This is the MNA index for this source's current
            
            if aux_var_info['type'] == 'IndepFV':
                vs_comp = comp_ref
                n_pos_str, n_neg_str = vs_comp['nodes']
                v_phasor = cmath.rect(vs_comp['v_mag'], math.radians(vs_comp['v_phase_deg']))

                # Converter e validar nós da fonte flutuante
                valid_fv_nodes = True
                n_pos_node_idx = -1
                if n_pos_str.isdigit() and int(n_pos_str) > 0:
                    n_pos_node_idx = int(n_pos_str) - 1
                    if not (0 <= n_pos_node_idx < num_actual_nodes):
                        analysis_results['error_messages'].append(f"Nó positivo '{n_pos_str}' da FV '{vs_comp['name']}' ({n_pos_node_idx+1}) fora dos limites dos nós KCL ({num_actual_nodes} nós).")
                        valid_fv_nodes = False
                else:
                    analysis_results['error_messages'].append(f"Nó positivo '{n_pos_str}' da FV '{vs_comp['name']}' inválido (não é um inteiro positivo).")
                    valid_fv_nodes = False

                n_neg_node_idx = -1
                if n_neg_str.isdigit() and int(n_neg_str) > 0:
                    n_neg_node_idx = int(n_neg_str) - 1
                    if not (0 <= n_neg_node_idx < num_actual_nodes):
                        analysis_results['error_messages'].append(f"Nó negativo '{n_neg_str}' da FV '{vs_comp['name']}' ({n_neg_node_idx+1}) fora dos limites dos nós KCL ({num_actual_nodes} nós).")
                        valid_fv_nodes = False
                else:
                    analysis_results['error_messages'].append(f"Nó negativo '{n_neg_str}' da FV '{vs_comp['name']}' inválido (não é um inteiro positivo).")
                    valid_fv_nodes = False
                
                if not valid_fv_nodes:
                    continue # Pula para a próxima FV se os nós são inválidos

                if n_pos_node_idx == n_neg_node_idx:
                    analysis_results['error_messages'].append(f"Fonte flutuante '{vs_comp['name']}' conecta o mesmo nó '{n_pos_str}' a si mesmo. Isso é um curto-circuito e não é permitido para FV.")
                    continue

                # Equação de Restrição de Tensão: V_pos - V_neg = V_source
                # Esta equação vai na linha 'current_var_idx'
                M_matrix[current_var_idx, n_pos_node_idx] = 1.0
                M_matrix[current_var_idx, n_neg_node_idx] = -1.0
                Z_vector[current_var_idx] = v_phasor

                # Estampar a corrente da fonte flutuante (I_vs_comp) nas equações KCL dos nós
                # A variável para I_vs_comp está na coluna 'current_var_idx'
                # Corrente I_fv flui de n_pos para n_neg DENTRO da fonte.
                # Portanto, para o circuito externo, I_fv SAI de n_pos e ENTRA em n_neg.
                if n_pos_node_idx not in defined_voltage_nodes: # Se KCL do nó n_pos existe
                    M_matrix[n_pos_node_idx, current_var_idx] = 1.0 # Termo +I_fv
                
                if n_neg_node_idx not in defined_voltage_nodes: # Se KCL do nó n_neg existe
                    M_matrix[n_neg_node_idx, current_var_idx] = -1.0 # Termo -I_fv
        
            elif aux_var_info['type'] == 'VCVS':
                comp = comp_ref
                # current_var_idx is already set for this VCVS's current
                n_plus_str, n_minus_str = comp['nodes']
                ctrl_n_plus_str, ctrl_n_minus_str = comp['control_nodes']
                gain = comp['gain']
                comp_name = comp['name']

                valid_nodes = True
                n_p_idx, n_m_idx, c_p_idx, c_m_idx = -1, -1, -1, -1 # Initialize to -1 (ground/invalid)
                try:
                    n_p_idx = int(n_plus_str) - 1 if n_plus_str != '0' else -1
                    n_m_idx = int(n_minus_str) - 1 if n_minus_str != '0' else -1
                    c_p_idx = int(ctrl_n_plus_str) - 1 if ctrl_n_plus_str != '0' else -1
                    c_m_idx = int(ctrl_n_minus_str) - 1 if ctrl_n_minus_str != '0' else -1

                    nodes_to_validate_map = {
                        "Nó + (saída)": (n_plus_str, n_p_idx), "Nó - (saída)": (n_minus_str, n_m_idx),
                        "Nó controle +": (ctrl_n_plus_str, c_p_idx), "Nó controle -": (ctrl_n_minus_str, c_m_idx)
                    }
                    for desc, (node_str, node_idx) in nodes_to_validate_map.items():
                        if node_str != '0': # Only validate non-ground nodes against num_actual_nodes
                            if not (0 <= node_idx < num_actual_nodes):
                                analysis_results['error_messages'].append(
                                    f"VCVS '{comp_name}': {desc} '{node_str}' (índice {node_idx+1}) está fora dos limites. "
                                    f"Nós KCL válidos: 1 a {num_actual_nodes}."
                                )
                                valid_nodes = False
                    
                    if n_p_idx == -1 and n_m_idx == -1: # Both output nodes are ground
                        analysis_results['error_messages'].append(f"VCVS '{comp_name}' não pode ter ambos os nós de saída ('{n_plus_str}', '{n_minus_str}') conectados ao terra.")
                        valid_nodes = False

                except ValueError:
                    analysis_results['error_messages'].append(f"VCVS '{comp_name}' contém nó(s) não numérico(s) inválido(s). Nós devem ser '0' ou inteiros positivos.")
                    valid_nodes = False
                
                if not valid_nodes:
                    continue

                # Stamp Voltage Constraint Equation: V(n+) - V(n-) - gain*(V(c+)-V(c-)) = 0
                # This goes into row: current_var_idx
                if n_p_idx != -1: M_matrix[current_var_idx, n_p_idx] = 1.0
                if n_m_idx != -1: M_matrix[current_var_idx, n_m_idx] = -1.0
                
                if c_p_idx != -1: M_matrix[current_var_idx, c_p_idx] -= gain
                if c_m_idx != -1: M_matrix[current_var_idx, c_m_idx] += gain
                # Z_vector[current_var_idx] is already 0.0 by initialization

                # Stamp Current Contributions (I_E) to KCL equations
                # Current I_E flows from n_p_idx to n_m_idx through the VCVS.
                # So, I_E leaves node n_p_idx (if not ground/fixed) and enters node n_m_idx (if not ground/fixed).
                
                # Contribution to KCL at n_p_idx: +I_E
                if n_p_idx != -1 and n_p_idx not in defined_voltage_nodes:
                    M_matrix[n_p_idx, current_var_idx] = 1.0
                
                # Contribution to KCL at n_m_idx: -I_E
                if n_m_idx != -1 and n_m_idx not in defined_voltage_nodes:
                    M_matrix[n_m_idx, current_var_idx] = -1.0

            elif aux_var_info['type'] == 'MonitoredGroundedVS':
                # Voltage for this VS is already handled by defined_voltage_nodes.
                # We only need to stamp its current into KCL equations.
                # current_var_idx is the MNA column for this VS's current.
                vs_comp = comp_ref
                n1_str, n2_str = vs_comp['nodes']
                
                # Determine which node is not ground and its index
                non_ground_node_str = n1_str if n1_str != '0' else n2_str
                non_ground_node_idx = int(non_ground_node_str) - 1 # Assumes valid numeric node from parser

                if 0 <= non_ground_node_idx < num_actual_nodes:
                    if non_ground_node_idx not in defined_voltage_nodes: # Should not happen if it's a defined_voltage_node, but check
                        # Current direction: Standard MNA assumes current variable for VS flows from + to -
                        # If VS_mon is N1 0 (N1 is +), current I_VS_mon leaves N1. KCL: +I_VS_mon
                        # If VS_mon is 0 N1 (N1 is -), current I_VS_mon enters N1. KCL: -I_VS_mon
                        if n1_str == non_ground_node_str: # N1 is non-ground, so N1 is positive terminal
                            M_matrix[non_ground_node_idx, current_var_idx] = 1.0
                        else: # N2 is non-ground, so N1 is ground, N2 is negative terminal
                            M_matrix[non_ground_node_idx, current_var_idx] = -1.0
                else:
                    analysis_results['error_messages'].append(f"Nó '{non_ground_node_str}' da fonte VS monitorada '{vs_comp['name']}' inválido para estampagem de corrente KCL.")


        # Check for critical errors from IndepFV or VCVS stamping before proceeding
        if analysis_results['error_messages'] and any( True for e_msg in analysis_results['error_messages'] if
            ("fora dos limites" in e_msg or "inválido" in e_msg or "curto-circuito" in e_msg or "terra" in e_msg) and
            ("FV" in e_msg or "VCVS" in e_msg or "fonte VS monitorada" in e_msg)
        ):
            return analysis_results # Critical error in VCVS definition

        # Estampagem de Fontes de Corrente Controladas por Tensão (VCCS - 'G' elements)
        for comp in parsed_components_list:
            if comp['type'] == 'VCCS':
                n_out_str, n_in_str = comp['nodes']
                ctrl_n_plus_str, ctrl_n_minus_str = comp['control_nodes']
                gm = comp['gain']
                comp_name = comp['name']

                valid_nodes = True
                n_out_idx, n_in_idx, c_p_idx, c_m_idx = -1, -1, -1, -1
                try:
                    n_out_idx = int(n_out_str) - 1 if n_out_str != '0' else -1
                    n_in_idx = int(n_in_str) - 1 if n_in_str != '0' else -1
                    c_p_idx = int(ctrl_n_plus_str) - 1 if ctrl_n_plus_str != '0' else -1
                    c_m_idx = int(ctrl_n_minus_str) - 1 if ctrl_n_minus_str != '0' else -1

                    nodes_to_validate_map = {
                        "Nó saída (->)": (n_out_str, n_out_idx), "Nó entrada (<-)": (n_in_str, n_in_idx),
                        "Nó controle +": (ctrl_n_plus_str, c_p_idx), "Nó controle -": (ctrl_n_minus_str, c_m_idx)
                    }
                    for desc, (node_str, node_idx) in nodes_to_validate_map.items():
                        if node_str != '0':
                            if not (0 <= node_idx < num_actual_nodes):
                                analysis_results['error_messages'].append(
                                    f"VCCS '{comp_name}': {desc} '{node_str}' (índice {node_idx+1}) está fora dos limites. "
                                    f"Nós KCL válidos: 1 a {num_actual_nodes}."
                                )
                                valid_nodes = False
                except ValueError:
                    analysis_results['error_messages'].append(f"VCCS '{comp_name}' contém nó(s) não numérico(s) inválido(s). Nós devem ser '0' ou inteiros positivos.")
                    valid_nodes = False
                
                if not valid_nodes:
                    continue

                # Estampagem para o nó de SAÍDA (n_out_idx), corrente I_G = gm * (V_cp - V_cm) é injetada
                if n_out_idx != -1 and n_out_idx not in defined_voltage_nodes:
                    # Contribuição de V(ctrl_n_plus)
                    if c_p_idx != -1: # Controle não é terra
                        if c_p_idx not in defined_voltage_nodes: # Tensão de controle é uma variável
                            M_matrix[n_out_idx, c_p_idx] += gm
                        else: # Tensão de controle é fixa
                            Z_vector[n_out_idx] += gm * defined_voltage_nodes[c_p_idx]
                    # Contribuição de V(ctrl_n_minus)
                    if c_m_idx != -1: # Controle não é terra
                        if c_m_idx not in defined_voltage_nodes: # Tensão de controle é uma variável
                            M_matrix[n_out_idx, c_m_idx] -= gm
                        else: # Tensão de controle é fixa
                            Z_vector[n_out_idx] -= gm * defined_voltage_nodes[c_m_idx]

                # Estampagem para o nó de ENTRADA (n_in_idx), corrente I_G é drenada
                if n_in_idx != -1 and n_in_idx not in defined_voltage_nodes:
                    # Contribuição de V(ctrl_n_plus)
                    if c_p_idx != -1: # Controle não é terra
                        if c_p_idx not in defined_voltage_nodes: # Tensão de controle é uma variável
                            M_matrix[n_in_idx, c_p_idx] -= gm
                        else: # Tensão de controle é fixa
                            Z_vector[n_in_idx] -= gm * defined_voltage_nodes[c_p_idx]
                    # Contribuição de V(ctrl_n_minus)
                    if c_m_idx != -1: # Controle não é terra
                        if c_m_idx not in defined_voltage_nodes: # Tensão de controle é uma variável
                            M_matrix[n_in_idx, c_m_idx] += gm
                        else: # Tensão de controle é fixa
                            Z_vector[n_in_idx] += gm * defined_voltage_nodes[c_m_idx]
        
        if analysis_results['error_messages'] and any("VCCS" in e and ("fora dos limites" in e or "inválido" in e) for e in analysis_results['error_messages']):
            return analysis_results

        # Estampagem de Fontes de Tensão Controladas por Corrente (CCVS - 'H' elements)
        for comp in parsed_components_list:
            if comp['type'] == 'CCVS':
                comp_name = comp['name']
                n_plus_str, n_minus_str = comp['nodes']
                ctrl_src_name = comp['control_source_name'] # Ex: "VS_monitor"
                rm = comp['gain']

                valid_nodes_ccvs = True
                n_p_idx, n_m_idx = -1, -1
                try:
                    n_p_idx = int(n_plus_str) - 1 if n_plus_str != '0' else -1
                    n_m_idx = int(n_minus_str) - 1 if n_minus_str != '0' else -1

                    if n_plus_str != '0' and not (0 <= n_p_idx < num_actual_nodes):
                        analysis_results['error_messages'].append(f"CCVS '{comp_name}': Nó + (saída) '{n_plus_str}' fora dos limites.")
                        valid_nodes_ccvs = False
                    if n_minus_str != '0' and not (0 <= n_m_idx < num_actual_nodes):
                        analysis_results['error_messages'].append(f"CCVS '{comp_name}': Nó - (saída) '{n_minus_str}' fora dos limites.")
                        valid_nodes_ccvs = False
                    if n_p_idx == -1 and n_m_idx == -1:
                        analysis_results['error_messages'].append(f"CCVS '{comp_name}' não pode ser conectada entre ground e ground.")
                        valid_nodes_ccvs = False
                except ValueError:
                    analysis_results['error_messages'].append(f"Nó não numérico para CCVS '{comp_name}'.")
                    valid_nodes_ccvs = False
                
                if not valid_nodes_ccvs:
                    continue

                # Obter índice da variável de corrente de controle I_control
                idx_I_control_source = source_name_to_current_var_idx_map.get(ctrl_src_name)
                if idx_I_control_source is None:
                    analysis_results['error_messages'].append(f"Fonte de controle de corrente '{ctrl_src_name}' para CCVS '{comp_name}' não encontrada ou não possui uma variável de corrente associada na MNA.")
                    continue

                # Obter índice da variável de corrente para esta CCVS (I_H)
                current_var_idx_H = source_name_to_current_var_idx_map.get(comp_name)
                if current_var_idx_H is None: # Should have been added as 'CCVS_self'
                    analysis_results['error_messages'].append(f"Erro interno: CCVS '{comp_name}' não tem índice de corrente auxiliar atribuído.")
                    continue
            
                # Estampar Equação de Restrição de Tensão: V(n+) - V(n-) - rm * I_control = 0
                # This goes into row: current_var_idx_H
                if n_p_idx != -1: M_matrix[current_var_idx_H, n_p_idx] = 1.0
                if n_m_idx != -1: M_matrix[current_var_idx_H, n_m_idx] = -1.0
                
                M_matrix[current_var_idx_H, idx_I_control_source] -= rm
                # Z_vector[current_var_idx_H] permanece 0

                # Estampar Corrente da CCVS (I_H) nas KCLs
                # Current I_H (column current_var_idx_H) flows from n_p_idx to n_m_idx
                if n_p_idx != -1 and n_p_idx not in defined_voltage_nodes:
                    M_matrix[n_p_idx, current_var_idx_H] = 1.0
                if n_m_idx != -1 and n_m_idx not in defined_voltage_nodes:
                    M_matrix[n_m_idx, current_var_idx_H] = -1.0
        
        if analysis_results['error_messages'] and any("CCVS" in e and ("inválido" in e or "fora dos limites" in e or "não encontrada" in e or "não tem índice" in e) for e in analysis_results['error_messages']):
            return analysis_results

        # Estampagem de Fontes de Corrente Controladas por Corrente (CCCS - 'F' elements)
        for comp in parsed_components_list:
            if comp['type'] == 'CCCS':
                comp_name = comp['name']
                n_out_str, n_in_str = comp['nodes']
                ctrl_src_name = comp['control_source_name']
                beta = comp['gain']

                valid_nodes_cccs = True
                n_out_idx, n_in_idx = -1, -1
                try:
                    n_out_idx = int(n_out_str) - 1 if n_out_str != '0' else -1
                    n_in_idx = int(n_in_str) - 1 if n_in_str != '0' else -1

                    if n_out_str != '0' and not (0 <= n_out_idx < num_actual_nodes):
                        analysis_results['error_messages'].append(f"CCCS '{comp_name}': Nó saída (->) '{n_out_str}' fora dos limites.")
                        valid_nodes_cccs = False
                    if n_in_str != '0' and not (0 <= n_in_idx < num_actual_nodes):
                        analysis_results['error_messages'].append(f"CCCS '{comp_name}': Nó entrada (<-) '{n_in_str}' fora dos limites.")
                        valid_nodes_cccs = False
                    # A CCCS with both output nodes to ground is unusual but might be valid if it affects other parts via control.
                    # However, if both are ground, it has no KCL equations to stamp into.
                    if n_out_idx == -1 and n_in_idx == -1:
                         analysis_results['error_messages'].append(f"CCCS '{comp_name}' tem ambos os nós de saída/entrada ('{n_out_str}', '{n_in_str}') conectados ao terra. Não terá efeito nas KCLs.")
                         # Not necessarily an error to stop analysis, but a warning.

                except ValueError:
                    analysis_results['error_messages'].append(f"Nó não numérico para CCCS '{comp_name}'.")
                    valid_nodes_cccs = False
                
                if not valid_nodes_cccs:
                    continue

                # Obter índice da variável de corrente de controle I_control
                idx_I_control_source = source_name_to_current_var_idx_map.get(ctrl_src_name)
                if idx_I_control_source is None:
                    analysis_results['error_messages'].append(f"Fonte de controle de corrente '{ctrl_src_name}' para CCCS '{comp_name}' não encontrada ou não possui uma variável de corrente associada na MNA.")
                    continue

                # Estampar contribuições da CCCS nas KCLs
                # Corrente I_F = beta * I_ctrl é INJETADA em n_out_idx. KCL: Sum(YV) - beta*I_ctrl = I_indep
                if n_out_idx != -1 and n_out_idx not in defined_voltage_nodes:
                    M_matrix[n_out_idx, idx_I_control_source] -= beta
                
                # Corrente I_F = beta * I_ctrl é DRENADA de n_in_idx. KCL: Sum(YV) + beta*I_ctrl = I_indep
                if n_in_idx != -1 and n_in_idx not in defined_voltage_nodes:
                    M_matrix[n_in_idx, idx_I_control_source] += beta

        if analysis_results['error_messages'] and any("CCCS" in e and ("inválido" in e or "fora dos limites" in e or "não encontrada" in e) for e in analysis_results['error_messages']):
            return analysis_results

        # Não tente resolver a matriz M_matrix ainda.
        # Para debug (descomente se necessário):
        # analysis_results['debug_M_matrix_p2'] = [[str(val) for val in row] for row in M_matrix.tolist()]
        # analysis_results['debug_Z_vector_p2'] = [str(val) for val in Z_vector.tolist()]
        # if any(c['type'].upper() == 'VS' and c['nodes'][0]!='0' and c['nodes'][1]!='0' for c in parsed_components_list):
        #    analysis_results['error_messages'].append("Supernode analysis (parte 2) processada. Implementação incompleta intencionalmente.")

        # Para debug da parte 3 (descomente se necessário):
        # analysis_results['debug_M_matrix_p3'] = [[str(val) for val in row] for row in M_matrix.tolist()]
        # analysis_results['debug_Z_vector_p3'] = [str(val) for val in Z_vector.tolist()]
        # if num_floating_vs > 0: analysis_results['error_messages'].append("Supernode analysis (parte 3) processada. Implementação incompleta intencionalmente.")
        # --- The following section (solving and post-processing) is commented out or cleared ---
        # --- as the MNA matrix is not yet fully formed for solving. ---
        
        # Resolver o sistema MNA
        X_solution_vector = None
        if M_matrix.shape[0] == 0: # Nenhuma equação para resolver
            if not analysis_results['error_messages']:
                analysis_results['error_messages'].append("Matriz MNA vazia. Nada para resolver.")
            return analysis_results
        
        try:
            X_solution_vector = np.linalg.solve(M_matrix, Z_vector)
        except np.linalg.LinAlgError:
            analysis_results['error_messages'].append("Matriz MNA singular: O circuito pode estar mal definido (ex: seções flutuantes isoladas, nós não referenciados por FVs ou componentes, ou dependências lineares).")
            return analysis_results
        except Exception as e: # Outros erros inesperados na solução
            analysis_results['error_messages'].append(f"Erro inesperado ao resolver sistema MNA: {e}")
            return analysis_results

        # Extrair Tensões Nodais
        analysis_results['nodal_voltages_phasors']['0'] = 0j
        for i in range(num_actual_nodes):
            analysis_results['nodal_voltages_phasors'][str(i + 1)] = X_solution_vector[i]
        # Reafirmar tensões de nós definidos (deveriam coincidir com a solução)
        for node_idx_fixed, v_fixed in defined_voltage_nodes.items():
            # This is more of an assertion; the MNA construction should ensure this.
            # If X_solution_vector[node_idx_fixed] is very different, it indicates an MNA setup error.
            analysis_results['nodal_voltages_phasors'][str(node_idx_fixed + 1)] = v_fixed

        # Extrair Correntes das fontes em aux_current_vars_info
        for aux_var in aux_current_vars_info:
            source_name = aux_var['name']
            mna_idx_for_current = aux_var['mna_idx']
            analysis_results['component_currents_phasors'][source_name] = X_solution_vector[mna_idx_for_current]
            # Voltage for IndepFV is its definition, already stored if needed or can be recalculated
            if aux_var['type'] == 'IndepFV':
                 vs_comp_ref = aux_var['comp_ref']
                 analysis_results['component_voltages_phasors'][source_name] = cmath.rect(vs_comp_ref['v_mag'], math.radians(vs_comp_ref['v_phase_deg']))


        # Calcular Tensões e Correntes nos Componentes Passivos, IS e Fontes Aterradas
        for comp_item in parsed_components_list:
            name = comp_item['name']
            type_comp = comp_item['type'].upper()
            nodes_tuple = comp_item['nodes']
            value = comp_item.get('value') # Not all components have 'value' (e.g. IS uses i_mag)

            # Skip sources whose V/I are already handled via aux_current_vars_info for V and I
            if name in source_name_to_current_var_idx_map: # If it has an MNA current variable
                continue

            v1 = analysis_results['nodal_voltages_phasors'].get(nodes_tuple[0], 0j)
            v2 = analysis_results['nodal_voltages_phasors'].get(nodes_tuple[1], 0j)
            v_drop = v1 - v2 # Voltage drop V(node1) - V(node2)

            if type_comp == 'VS': # Grounded Voltage Source (since FVs are skipped)
                analysis_results['component_voltages_phasors'][name] = v_drop # Should be consistent with its definition
                # Current for grounded VS (if not primary) is not directly solved. Will be calculated for primary.
            elif type_comp == 'IS':
                analysis_results['component_voltages_phasors'][name] = v_drop
                analysis_results['component_currents_phasors'][name] = cmath.rect(comp_item['i_mag'], math.radians(comp_item['i_phase_deg']))
            elif type_comp == 'VCVS': # Voltage for VCVS is V(n+) - V(n-)
                # Current for VCVS was already extracted from X_solution_vector
                analysis_results['component_voltages_phasors'][name] = v_drop
            elif type_comp == 'CCVS': # Voltage for CCVS is V(n+) - V(n-)
                # Current for CCVS (I_H) was already extracted
                analysis_results['component_voltages_phasors'][name] = v_drop

            elif type_comp == 'CCCS':
                # Voltage across CCCS output terminals
                analysis_results['component_voltages_phasors'][name] = v_drop
                # Current for CCCS: I_F = beta * I_control
                beta_gain = comp_item['gain']
                ctrl_src_name_cccs = comp_item['control_source_name']
                idx_i_ctrl_cccs = source_name_to_current_var_idx_map.get(ctrl_src_name_cccs)
                
                if idx_i_ctrl_cccs is not None:
                    i_control_val = X_solution_vector[idx_i_ctrl_cccs]
                    i_cccs = beta_gain * i_control_val
                    analysis_results['component_currents_phasors'][name] = i_cccs

            elif type_comp == 'VCCS':
                # Voltage across VCCS output terminals
                analysis_results['component_voltages_phasors'][name] = v_drop
                # Current for VCCS: I_G = gm * (V(ctrl_p) - V(ctrl_m))
                gm_gain = comp_item['gain']
                ctrl_nodes_vccs = comp_item['control_nodes']
                
                v_cp_val = analysis_results['nodal_voltages_phasors'].get(ctrl_nodes_vccs[0], 0j)
                v_cm_val = analysis_results['nodal_voltages_phasors'].get(ctrl_nodes_vccs[1], 0j)
                
                i_vccs = gm_gain * (v_cp_val - v_cm_val)
                analysis_results['component_currents_phasors'][name] = i_vccs



            elif type_comp in ['R', 'L', 'C']:
                analysis_results['component_voltages_phasors'][name] = v_drop
                i_comp = 0j
                if type_comp == 'R':
                    i_comp = v_drop / value if value > 1e-12 else v_drop / 1e-12 
                elif type_comp == 'L':
                    if omega == 0: # DC case, inductor is a short
                        # If v_drop is non-zero across a short, current is theoretically infinite.
                        # We use a very small impedance.
                        i_comp = v_drop / 1e-12 if abs(v_drop) > 1e-9 else 0j 
                    elif value <= 1e-12: # Inductance effectively zero
                        i_comp = v_drop / 1e-12 if abs(v_drop) > 1e-9 else 0j
                    else:
                        i_comp = v_drop / (1j * omega * value)
                elif type_comp == 'C':
                    if omega == 0: # DC case, capacitor is open
                        i_comp = 0j
                    elif value <= 1e-15: # Capacitance effectively zero
                        i_comp = 0j
                    else:
                        i_comp = v_drop * (1j * omega * value)
                analysis_results['component_currents_phasors'][name] = i_comp

        # Recalcular Corrente da Fonte Principal (i_source_total_phasor)
        # primary_source_info was set when VS components were first processed.
        # analysis_results['v_source_phasor'] was also set then.
        if primary_source_info:
            ps_name = primary_source_info['name']
            ps_nodes = primary_source_info['nodes']
            
            # Check if primary source current was directly solved (i.e., it's in aux_current_vars_info)
            if ps_name in source_name_to_current_var_idx_map:
                analysis_results['i_source_total_phasor'] = analysis_results['component_currents_phasors'].get(ps_name)
            else: # Primary source is grounded
                i_source_calc = 0j
                # Determine the non-ground node of the primary grounded source
                # And the direction of current relative to its definition
                node_k_str = ""
                # Polarity_factor: 1 if current calculated is already "out of positive terminal"
                #                 -1 if current calculated is "into positive terminal"
                polarity_factor = 1 
                if ps_nodes[0] != '0' and ps_nodes[1] == '0': # e.g. VS1 1 0 (node 1 is positive)
                    node_k_str = ps_nodes[0]
                    polarity_factor = 1 
                elif ps_nodes[1] != '0' and ps_nodes[0] == '0': # e.g. VS1 0 1 (node 1 is negative, current out of ground)
                    node_k_str = ps_nodes[1]
                    polarity_factor = -1 # Current leaving node 1 is current entering source's physical positive terminal (gnd)

                if node_k_str:
                    for c_item in parsed_components_list:
                        if c_item['name'] == ps_name: continue # Skip the source itself
                        if node_k_str in c_item['nodes']:
                            branch_current = analysis_results['component_currents_phasors'].get(c_item['name'], 0j)
                            if c_item['nodes'][0] == node_k_str: # Current leaves node_k_str via this branch
                                i_source_calc += branch_current
                            elif c_item['nodes'][1] == node_k_str: # Current enters node_k_str via this branch
                                i_source_calc -= branch_current
                    analysis_results['i_source_total_phasor'] = i_source_calc * polarity_factor
                    analysis_results['component_currents_phasors'][ps_name] = analysis_results['i_source_total_phasor']

        # Clear results that depend on solving the system
        # analysis_results['nodal_voltages_phasors'] = {'0': 0j} # Now populated above
        # analysis_results['component_currents_phasors'] = {} # Now populated above
        # analysis_results['component_voltages_phasors'] = {} # Now populated above
        # analysis_results['i_source_total_phasor'] = None # Now populated above
        analysis_results['z_equivalent_total_phasor'] = None
        analysis_results['p_total_avg_W'] = None
        analysis_results['q_total_VAR'] = None
        analysis_results['s_total_apparent_VA'] = None
        analysis_results['fp_total'] = None

        # Final calculations for overall circuit parameters
        # analysis_results['v_source_phasor'] should already be set from primary_source_info
        if analysis_results.get('v_source_phasor') is not None and \
           analysis_results.get('i_source_total_phasor') is not None:
            v_s, i_s_total = analysis_results['v_source_phasor'], analysis_results['i_source_total_phasor']
            if v_s is not None and i_s_total is not None:
                analysis_results['z_equivalent_total_phasor'] = (v_s / i_s_total) if abs(i_s_total) > 1e-12 else complex(float('inf'), float('inf'))
                s_cplx = v_s * i_s_total.conjugate()
                analysis_results['p_total_avg_W'], analysis_results['q_total_VAR'] = s_cplx.real, s_cplx.imag
                analysis_results['s_total_apparent_VA'] = abs(s_cplx)
                s_abs = analysis_results['s_total_apparent_VA']
                analysis_results['fp_total'] = (s_cplx.real / s_abs) if s_abs > 1e-9 else (1.0 if abs(s_cplx.real) < 1e-9 else 0.0)
                analysis_results['fp_total'] = max(-1.0, min(1.0, analysis_results['fp_total']))

        # For compatibility with PF correction and results display
        if 'p_total_avg_W' in analysis_results : analysis_results['p_total'] = analysis_results['p_total_avg_W']
        if 'q_total_VAR' in analysis_results : analysis_results['q_total'] = analysis_results['q_total_VAR']
        if 's_total_apparent_VA' in analysis_results : analysis_results['s_total_apparent'] = analysis_results['s_total_apparent_VA']

        # Placeholder for debug info as requested
        if num_total_aux_vars > 0 or num_vccs > 0 or num_cccs > 0:
            analysis_results['debug_info'] = (f"Config MNA: Tam={mna_size}, Nós KCL={num_actual_nodes}, "
                                              f"TotAuxVars={num_total_aux_vars} (IndepFV={num_independent_floating_vs}, VCVS={num_vcvs}, CCVS_self={num_ccvs_self}, MonitVS={num_monitored_grounded_vs}), "
                                              f"VCCS={num_vccs}, CCCS={num_cccs}")
            # analysis_results['error_messages'].append("Análise de Supernó (parte 2) processada. Implementação incompleta intencionalmente.")


        return analysis_results


    def analyze_circuit(self):
        self.results_text.configure(state="normal"); self.results_text.delete("1.0","end"); self._clear_all_entry_error_styles(); self.analysis_performed_successfully=False
        self.analysis_results = {}
        output_text=""
        self.three_phase_source_details_map = {} # Reset for current analysis

        netlist_content = self.netlist_textbox.get("1.0", tk.END).strip()

        if not netlist_content:
            # --- Code path for manual RLC equivalent (OLD STYLE) ---
            # This path can be kept if desired, or removed if nodal is the only way.
            # For now, let's indicate it's not the primary path.
            output_text += "Netlist is empty. Nodal analysis requires a netlist.\n"
            output_text += "To use manual RLC equivalent mode (if still supported separately), ensure netlist is empty and fill manual fields.\n"
            # Example: Call old _perform_core_analysis if you want to retain it
            # params, errors = self._validate_all_parameters(silent=False)
            # if params and not errors:
            #   self.analysis_results = self._perform_core_analysis_RLC_Equivalent(params) # A renamed old function
            #   analysis_details_text = self._generate_analysis_details_text(self.analysis_results) # Old text generator
            #   output_text += analysis_details_text
            #   self._update_static_circuit_diagram(self.analysis_results) # Old diagram
            #   self._update_phasor_diagram(self.analysis_results) # Old phasor
            # else: output_text += "Errors in manual parameters."
            self.results_text.insert("1.0",output_text); self.results_text.configure(state="disabled")
            self._clear_main_plot(error_message="Netlist empty for Nodal Analysis.")
            self._clear_static_circuit_diagram(error_message="Netlist empty.")
            return
        # --- End manual RLC path ---

        self.progress_bar_frame.pack(pady=(5,0),padx=10,fill="x",before=self.note_label); self.progress_bar.pack(pady=5,padx=0,fill="x"); self.progress_bar.start(); self.master.update_idletasks()

        parsed_components, frequency, parse_errors = self._parse_netlist_for_nodal_analysis(netlist_content)

        if parse_errors:
            output_text += "Erro(s) ao processar netlist:\n" + "\n".join(parse_errors)
            messagebox.showerror("Erro no Netlist", "\n".join(parse_errors))
        elif not parsed_components :
             output_text += "Netlist processado, mas nenhum componente válido encontrado para análise."
        elif frequency is None or frequency <= 0:
            output_text += "Frequência de análise válida não encontrada ou não é positiva."
            if frequency is not None: output_text += f" (Valor: {frequency})"

        if output_text: # If any pre-analysis errors occurred
            self.results_text.insert("1.0",output_text)
            self.progress_bar.stop();self.progress_bar.pack_forget();self.progress_bar_frame.pack_forget();
            self.results_text.configure(state="disabled")
            self._clear_main_plot(error_message="Erro de entrada ou Netlist.")
            self._clear_static_circuit_diagram(error_message="Erro de entrada ou Netlist.")
            return

        try:
            self.analysis_results = self._perform_nodal_analysis(parsed_components, frequency)

            # Calculate and add three-phase summary if applicable
            self.current_p_real = self.analysis_results.get('p_total_avg_W')
            self.current_q_reactive = self.analysis_results.get('q_total_VAR')
            self.current_s_apparent = self.analysis_results.get('s_total_apparent_VA')
            self.current_fp_actual = self.analysis_results.get('fp_total')
            vs_phasor_for_pf = self.analysis_results.get('v_source_phasor')
            self.current_v_load_mag= abs(vs_phasor_for_pf) if vs_phasor_for_pf else 0
            self.current_freq = frequency

            if any(comp.get('three_phase_parent') for comp in parsed_components):
                self.analysis_results['three_phase_summary'] = self._calculate_three_phase_results(self.analysis_results, parsed_components)

            if self.analysis_results.get('error_messages'):
                output_text += "Análise Nodal encontrou problemas:\n" + "\n".join(self.analysis_results['error_messages']) + "\n\n"

            output_text += self._generate_nodal_analysis_details_text(self.analysis_results, parsed_components)
            self.analysis_performed_successfully = not bool(self.analysis_results.get('error_messages')) and \
                                               bool(self.analysis_results.get('nodal_voltages_phasors'))


            self._update_static_circuit_diagram_from_netlist(parsed_components, frequency, self.analysis_results)
            self._update_phasor_diagram_from_nodal(self.analysis_results) # Pass parsed_components via self
            self._plot_time_domain_waveforms() # Plot waveforms
            self._update_waveform_selection_ui() # Update selection UI after analysis

        except Exception as e:
            self.results_text.delete("1.0","end"); error_msg=f"Erro inesperado na análise: {str(e)}";
            messagebox.showerror("Erro Inesperado",error_msg); self.results_text.insert("1.0",error_msg)
            self._clear_main_plot(error_message="Erro na análise.")
            self._clear_static_circuit_diagram(error_message="Erro na análise.")
            import traceback; traceback.print_exc()
            self._clear_waveforms_plot(error_message="Erro durante a análise.")
            self._update_waveform_selection_ui() # Update UI even on error (shows "Execute análise...")
            self.analysis_performed_successfully = False
            self.parsed_components_for_plotting = [] # Clear on error
        finally:
            self.progress_bar.stop();self.progress_bar.pack_forget();self.progress_bar_frame.pack_forget();
            self.results_text.configure(state="normal") # Ensure it's normal before inserting
            self.results_text.delete("1.0", "end") # Clear previous content before inserting new
            self.results_text.insert("1.0", output_text if output_text.strip() else "Análise concluída. Verifique os resultados.")
            self.results_text.configure(state="disabled")

        if self.analysis_performed_successfully:
            self.parsed_components_for_plotting = parsed_components # Store for plotter

    def _generate_nodal_analysis_details_text(self, nodal_results, parsed_components):
        if not nodal_results: return "A análise nodal não produziu resultados."
        output = ""; freq = nodal_results.get('freq', 'N/A')
        output += f"--- Resultados da Análise Nodal (f = {self._format_value(freq, 'Hz')}) ---\n"

        if nodal_results.get('error_messages'):
            output += "**Problemas na Análise:**\n" + "\n".join(f"  - {e}" for e in nodal_results['error_messages']) + "\n\n"

        output += "Tensões Nodais (referenciadas ao nó '0'):\n"
        v_nodes = nodal_results.get('nodal_voltages_phasors', {})
        # Sort nodes: '0', then '1', '2', ...
        sorted_node_keys = sorted(v_nodes.keys(), key=lambda x: int(x) if x.isdigit() and x != '0' else (-1 if x == '0' else float('inf')))

        for node_num_str in sorted_node_keys:
            v_phasor = v_nodes[node_num_str]
            output += f"  V_nó[{node_num_str}]: {self.format_phasor(v_phasor, 'V')}\n"
        output += "\n"

        output += "Detalhes dos Componentes:\n"
        comp_voltages = nodal_results.get('component_voltages_phasors', {})
        comp_currents = nodal_results.get('component_currents_phasors', {})

        for comp_spec in parsed_components: # Iterate parsed_components to maintain order
            name = comp_spec['name']; comp_type = comp_spec['type']; val_str = ""
            if comp_type == 'R': val_str = f"{self._format_value(comp_spec['value'], 'Ω')}"
            elif comp_type == 'L': val_str = f"{self._format_value(comp_spec['value'], 'H')}"
            elif comp_type == 'C': val_str = f"{self._format_value(comp_spec['value'], 'F')}"
            elif comp_type == 'VS': val_str = f"{self.format_phasor(cmath.rect(comp_spec['v_mag'], math.radians(comp_spec['v_phase_deg'])), 'V')} (Def.)"
            elif comp_type == 'IS':
                i_mag_is, i_phase_deg_is = comp_spec.get('i_mag'), comp_spec.get('i_phase_deg')
                if i_mag_is is not None and i_phase_deg_is is not None:
                    val_str = f"{self.format_phasor(cmath.rect(i_mag_is, math.radians(i_phase_deg_is)), 'A')} (Def.)"
                else:
                    val_str = "Def. Erro"
            elif comp_type == 'VCVS':
                val_str = f"Ganho: {comp_spec['gain']}" # Control nodes also relevant but might make line too long
            elif comp_type == 'CCVS':
                val_str = f"Rm: {comp_spec['gain']} Ω, CtrlSrc: {comp_spec['control_source_name']}"
            elif comp_type == 'CCCS':
                val_str = f"Beta: {comp_spec['gain']}, CtrlSrc: {comp_spec['control_source_name']}"
            elif comp_type == 'VCCS':
                val_str = f"Gm: {comp_spec['gain']} S, CtrlNós: {comp_spec.get('control_nodes',['N/A','N/A'])[0]}-{comp_spec.get('control_nodes',['N/A','N/A'])[1]}"
            # Default value for CCCS if properties are missing (should not happen with proper init)
            # elif comp_type == 'CCCS': val_str = f"Beta: {comp_spec.get('gain', 'N/A')}, Ctrl: {comp_spec.get('control_source_name', 'N/A')}"
            else: # Should not happen if all types handled
                    val_str = "Def. Erro"

            node_info_str = f"Nós:{comp_spec['nodes'][0]}-{comp_spec['nodes'][1]}" if comp_spec.get('nodes') else "Nós: N/A"
            output += f"- {name} ({comp_type}, {node_info_str}, {val_str}):\n"
            v_drop = comp_voltages.get(name)
            i_flow = comp_currents.get(name)
            if v_drop is not None: output += f"    V_queda: {self.format_phasor(v_drop, 'V')}\n"
            if i_flow is not None: output += f"    I_comp: {self.format_phasor(i_flow, 'A')}\n"
            if v_drop is not None and i_flow is not None and comp_type not in ['VS', 'VCVS', 'VCCS', 'CCVS', 'CCCS']: # Power for controlled sources is more complex
                s_comp = v_drop * i_flow.conjugate() # For IS, v_drop is voltage across it, i_flow is its current
                output += f"    P_comp: {self._format_value(s_comp.real, 'W')}, Q_comp: {self._format_value(s_comp.imag, 'VAR')}\n"
        output += "\n"

        if nodal_results.get('v_source_phasor') is not None:
            output += "Resumo da Fonte Principal (assumido primeiro VS na netlist ou VS ligado ao terra):\n"
            output += f"  V_fonte: {self.format_phasor(nodal_results['v_source_phasor'], 'V')}\n"
            if nodal_results.get('i_source_total_phasor') is not None:
                output += f"  I_total_fonte: {self.format_phasor(nodal_results['i_source_total_phasor'], 'A')}\n"
            if nodal_results.get('z_equivalent_total_phasor') is not None:
                output += f"  Z_eq_vista_pela_fonte: {self.format_phasor(nodal_results['z_equivalent_total_phasor'], 'Ω')}\n"

            p_tot, q_tot = nodal_results.get('p_total_avg_W'), nodal_results.get('q_total_VAR')
            s_tot, fp_tot = nodal_results.get('s_total_apparent_VA'), nodal_results.get('fp_total')

            if p_tot is not None: output += f"  P_total: {self._format_value(p_tot, 'W')}\n"
            if q_tot is not None: output += f"  Q_total: {self._format_value(q_tot, 'VAR')}\n"
            if s_tot is not None: output += f"  S_total: {self._format_value(s_tot, 'VA')}\n"
            if fp_tot is not None:
                fp_type_str = ""
                if abs(s_tot if s_tot is not None else 0) < 1e-9 : fp_type_str = " (N/A - sem potência)"
                elif abs(q_tot if q_tot is not None else 0) < 1e-9 : fp_type_str = " (unitário)"
                else: fp_type_str = " (indutivo/atrasado)" if (q_tot if q_tot is not None else 0) > 0 else " (capacitivo/adiantado)"
                output += f"  FP_total: {self._format_value(fp_tot)}{fp_type_str}\n"
        
        # --- Three-Phase Summary Section ---
        three_phase_summary_results = nodal_results.get('three_phase_summary')
        if three_phase_summary_results:
            output += "\n--- Resumos Trifásicos (@ f = " + self._format_value(freq, 'Hz') + ") ---\n"
            for parent_name, summary in three_phase_summary_results.items():
                output += f"Elemento Original: {parent_name} (Tipo: {summary.get('type', 'N/A')})\n"
                if summary.get('errors'):
                    output += "  Erros no cálculo trifásico:\n" + "\n".join(f"    - {e}" for e in summary['errors']) + "\n"

                if 'Vph_avg_mag' in summary: output += f"  Tensão de Fase Média (Vφ): {self._format_value(summary['Vph_avg_mag'], 'V')}\n"
                if 'Vln_avg_mag' in summary: output += f"  Tensão de Linha Média (VL-L): {self._format_value(summary['Vln_avg_mag'], 'V')}\n"
                if 'Il_avg_mag' in summary:  output += f"  Corrente de Linha Média (IL): {self._format_value(summary['Il_avg_mag'], 'A')}\n"
                if 'Iph_avg_mag' in summary and 'Il_avg_mag' not in summary : # For Delta loads, show phase current if line current wasn't easily derived
                     output += f"  Corrente de Fase Média (Iφ): {self._format_value(summary['Iph_avg_mag'], 'A')}\n"
                if 'Zph_avg_phasor' in summary: output += f"  Impedância por Fase Média (Zφ): {self.format_phasor(summary['Zph_avg_phasor'], 'Ω')}\n"
                
                output += f"  Potência Ativa Total (P₃φ): {self._format_value(summary.get('P3ph', 0.0), 'W')}\n"
                output += f"  Potência Reativa Total (Q₃φ): {self._format_value(summary.get('Q3ph', 0.0), 'VAR')}\n"
                output += f"  Potência Aparente Total (S₃φ): {self._format_value(summary.get('S3ph_mag', 0.0), 'VA')}\n"
                
                fp3ph_val = summary.get('PF3ph', 1.0)
                q3ph_val = summary.get('Q3ph', 0.0)
                fp3ph_type = " (unitário)" if abs(q3ph_val) < 1e-9 else (" (indutivo/atrasado)" if q3ph_val > 0 else " (capacitivo/adiantado)")
                output += f"  Fator de Potência Trifásico (FP₃φ): {self._format_value(fp3ph_val)}{fp3ph_type}\n"
                output += "\n"
        return output


    def _calculate_and_display_pf_correction(self):
        # (Original _calculate_and_display_pf_correction - needs to use self.current_... variables)
        self._clear_all_entry_error_styles(); self._set_entry_error_style('fp_desired',is_error=False)
        if not self.analysis_performed_successfully: messagebox.showerror("Correção FP","Execute uma análise de circuito bem-sucedida primeiro."); return
        fp_desired_str=self.fp_desired_entry.get()
        if not fp_desired_str: messagebox.showerror("Entrada Inválida","Insira o Fator de Potência Desejado."); self._set_entry_error_style('fp_desired',True); return
        try:
            fp_desired=float(fp_desired_str)
            if not (0.01<=fp_desired<=1.0): messagebox.showerror("Entrada Inválida","FP Desejado deve estar entre 0.01 e 1.0."); self._set_entry_error_style('fp_desired',True); return
        except ValueError: messagebox.showerror("Entrada Inválida","FP Desejado deve ser um número."); self._set_entry_error_style('fp_desired',True); return

        # Use stored values from the last analysis
        P_atual = self.current_p_real
        Q_atual = self.current_q_reactive
        FP_atual = self.current_fp_actual
        V_carga = self.current_v_load_mag # Voltage magnitude at the point of correction
        freq = self.current_freq

        if any(v is None for v in [P_atual,Q_atual,FP_atual,V_carga,freq]): messagebox.showerror("Correção FP","Dados da análise anterior incompletos ou não disponíveis para correção."); return
        if abs(V_carga)<1e-6 or abs(freq)<1e-6: messagebox.showerror("Cálculo Impossível","Tensão da carga ou frequência próxima de zero."); return

        if Q_atual > 1e-9: # Carga Indutiva, Q > 0
            if fp_desired <= FP_atual + 1e-4 and fp_desired < 0.99999 : # Only correct if it's an improvement for inductive
                messagebox.showinfo("Correção FP",f"FP desejado ({fp_desired:.3f}) não é uma melhoria significativa sobre o FP atual ({FP_atual:.3f}) para carga indutiva, ou é menor.\nNenhuma correção com capacitor será calculada.")
                return
        elif Q_atual < -1e-9: # Carga Capacitiva, Q < 0
            messagebox.showinfo("Correção FP",f"Circuito já é capacitivo (Q={self._format_value(Q_atual,'VAR')}).\nCorreção com capacitor adicional não é aplicável para melhorar o FP em direção a 1 neste caso.")
            return
        else: # FP ~ 1 (Q ~ 0)
            messagebox.showinfo("Correção FP",f"Circuito já possui FP próximo de 1 (Q ≈ 0).\nNenhuma correção com capacitor é necessária para FP={fp_desired:.3f}.")
            return

        try: fp_desired_clamped=max(0.01,min(1.0,fp_desired)); phi_desejado_rad=math.acos(fp_desired_clamped)
        except ValueError: messagebox.showerror("Erro Cálculo","Valor inválido para acos(FP desejado)."); return

        # Q_desejada is positive if P_atual is positive and fp_desired is for lagging (inductive)
        # For correction towards unity (or leading up to unity for an inductive load), Q_desejada should be <= Q_atual
        # If original load is inductive (Q_atual > 0), Q_desejada will be P_atual * tan(acos(fp_desired))
        # We want the new Q to be Q_desejada. The capacitor provides Qc = Q_atual - Q_desejada.
        # This Qc is negative (capacitive). The capacitor value C = -Qc / (V^2 * omega)
        # Or, more simply, Qc_provided_by_cap = Q_atual - Q_target. Capacitor value is Qc_provided_by_cap / (omega * V^2)
        # This assumes fp_desired is for a lagging (or unity) power factor.
        # If fp_desired was to be leading, phi_desejado_rad would be negative, tan(phi) would be negative.

        Q_desejada_final = P_atual * math.tan(phi_desejado_rad) # This Q is for the load to have fp_desired (inductive if P>0, phi>0)
        
        # Qc_needed is the reactive power the capacitor must SUPPLY.
        # If Q_atual is positive (inductive), and Q_desejada_final is smaller positive (less inductive),
        # then capacitor must supply Q_atual - Q_desejada_final (which is positive).
        # A capacitor supplies "negative" VARs in the conventional sense (absorbs positive Q, or sources negative Q).
        # So, Q_for_capacitor_calc = Q_atual - Q_desejada_final. This is the amount of VARs to "cancel".
        Q_var_to_compensate = Q_atual - Q_desejada_final

        cap_val=0.0; S_nova=P_atual / fp_desired_clamped if abs(fp_desired_clamped)>1e-9 else math.sqrt(P_atual**2+Q_desejada_final**2)
        Q_nova_final_circuit = Q_desejada_final # This is the target Q for the whole circuit after correction

        results_txt = ""
        if Q_var_to_compensate > 1e-9: # If we need to compensate positive (inductive) VARs
            omega_calc=2*math.pi*freq
            try:
                # Capacitor supplies this Q_var_to_compensate. Q_cap_supplied = V^2 * omega * C
                cap_val = Q_var_to_compensate / (V_carga**2 * omega_calc)
            except ZeroDivisionError: messagebox.showerror("Erro Cálculo","Divisão por zero ao calcular capacitor (V_carga ou omega é zero)."); return

            results_txt=f"\n\n--- Resultados da Correção de Fator de Potência ---\n  FP Atual: {self._format_value(FP_atual)} (P={self._format_value(P_atual,'W')}, Q={self._format_value(Q_atual,'VAR')})\n"
            results_txt+=f"  FP Desejado (lagging/unity): {self._format_value(fp_desired)}\n  Capacitor (paralelo): {self._format_value(cap_val,'F')}\n"
            results_txt+=f"    (Equiv. a {self._format_value(cap_val*1e3,'mF')} ou {self._format_value(cap_val*1e6,'µF')} ou {self._format_value(cap_val*1e9,'nF')})\n"
            results_txt+=f"  Qc Fornecida pelo Capacitor: {self._format_value(-Q_var_to_compensate,'VAR')} (capacitivos)\n" # Capacitor supplies negative Q
            results_txt+=f"  Q_nova Estimada (carga+capacitor): {self._format_value(Q_nova_final_circuit,'VAR')}\n"
            results_txt+=f"  S_nova Estimada (carga+capacitor): {self._format_value(S_nova,'VA')}\n"
        else:
            results_txt=f"\n\n--- Correção de Fator de Potência ---\n  FP Atual: {self._format_value(FP_atual)}\n  FP Desejado: {self._format_value(fp_desired)}\n"
            results_txt+=f"  Nenhuma correção com capacitor é necessária ou o FP desejado não representa uma melhoria por este método para uma carga já pouco indutiva/capacitiva.\n  (VARs a compensar pelo capacitor: {self._format_value(Q_var_to_compensate,'VAR')})\n"

        self.results_text.configure(state="normal"); self.results_text.insert(tk.END,results_txt); self.results_text.configure(state="disabled")


    def _clear_main_plot(self, initial_message=None, error_message=None):
        # (Original _clear_main_plot method - kept as is)
        if self.ax_main_plot:
            self.ax_main_plot.set_visible(True) 
            # Surgical clear
            for artist in list(self.ax_main_plot.lines + self.ax_main_plot.patches + self.ax_main_plot.texts):
                artist.remove()
            if self.ax_main_plot.get_legend():
                self.ax_main_plot.get_legend().remove()
            # self.ax_main_plot.clear() # Replaced by surgical clear


            if self.ax_main_plot_twin and self.ax_main_plot_twin.figure:
                try:
                    self.fig_main_plot.delaxes(self.ax_main_plot_twin) # Attempt to remove twin axis
                except (AttributeError, ValueError, KeyError):
                    try: # Fallback: clear and hide if removal fails
                        self.ax_main_plot_twin.clear()
                        self.ax_main_plot_twin.set_visible(False)
                    except: pass # Ignore errors in fallback
                self.ax_main_plot_twin = None

            # Set placeholder background colors for clarity during debugging/idle
            self.ax_main_plot.set_facecolor(self._get_ctk_bg_color()) # Match CTk theme if possible
            self.fig_main_plot.patch.set_facecolor(self._get_ctk_bg_color())


            title = "Diagrama Fasorial"; message = initial_message or "Aguardando análise...";
            text_fill_color = self._get_ctk_text_color()
            if error_message:
                message = error_message; title = "Erro no Gráfico"; text_fill_color = 'red'

            self.ax_main_plot.text(0.5, 0.5, message, ha='center', va='center', fontsize=9, color=text_fill_color, wrap=True)
            self.ax_main_plot.set_title(title, fontsize=10, color=text_fill_color)

            self.ax_main_plot.set_xlabel("")
            self.ax_main_plot.set_ylabel("")
            self.ax_main_plot.set_xticks([])
            self.ax_main_plot.set_yticks([])
            self.ax_main_plot.grid(False)

            # try:
            #     self.fig_main_plot.tight_layout() # Not needed with constrained_layout
            # except Exception as e:
            #     print(f"[DEBUG] _clear_main_plot tight_layout error: {e}")
            
            if self.canvas_main_plot: # Redraw only if canvas exists
                 self.canvas_main_plot.draw_idle() # Use draw_idle for efficiency
            print(f"[DEBUG] _clear_main_plot executado. Mensagem: {message if message else 'Nenhuma'}")


    def _clear_static_circuit_diagram(self, initial_message=None, error_message=None):
        # (Original _clear_static_circuit_diagram method - kept as is)
        if not self.circuit_diagram_canvas:
            return
        self.circuit_diagram_canvas.delete("all")

        bg_color = self._get_ctk_bg_color()
        self.circuit_diagram_canvas.configure(bg=bg_color)
        text_color = self._get_ctk_text_color()

        canvas_width = self.circuit_diagram_canvas.winfo_width()
        canvas_height = self.circuit_diagram_canvas.winfo_height()
        if canvas_width <= 1: canvas_width = 300
        if canvas_height <= 1: canvas_height = 100

        message = initial_message or "Aguardando análise..."
        fill_color = "red" if error_message else text_color
        if error_message: message = error_message

        self.circuit_diagram_canvas.create_text(
            canvas_width / 2, canvas_height / 2,
            text=message, font=("Arial", 10), fill=fill_color, anchor="center", justify="center", width=canvas_width-20
        )
        print(f"[DEBUG] _clear_static_circuit_diagram executado. Mensagem: {message}")

    def _update_static_circuit_diagram_from_netlist(self, parsed_components, frequency, analysis_results):
        # Placeholder - drawing arbitrary netlists is complex. For now, lists components.
        if not self.circuit_diagram_canvas:
            print("[DEBUG] Canvas do diagrama de circuito não existe para netlist.")
            return
        self.circuit_diagram_canvas.delete("all")
        bg_color = self._get_ctk_bg_color()
        text_color = self._get_ctk_text_color()
        self.circuit_diagram_canvas.configure(bg=bg_color)

        # Ensure canvas dimensions are available
        self.circuit_diagram_canvas.update_idletasks()
        cw = self.circuit_diagram_canvas.winfo_width()
        ch = self.circuit_diagram_canvas.winfo_height()

        if cw <= 1: cw = 400  # Fallback width
        if ch <= 1: ch = max(200, len(parsed_components) * 15 + 40) # Dynamic fallback height

        if not parsed_components:
            self._clear_static_circuit_diagram(initial_message="Nenhum componente na netlist para desenhar.")
            return
        
        y_pos = 20
        self.circuit_diagram_canvas.create_text(10, y_pos, anchor="nw",
                                                text=f"Diagrama de Circuito (Baseado na Netlist - Simplificado)",
                                                fill=text_color, font=("Arial", 11, "bold"))
        y_pos += 25

        for comp in parsed_components:
            comp_details = f"{comp['name']} ({comp['type']}): Nós {comp['nodes'][0]}-{comp['nodes'][1]}"
            if comp['type'] == 'VS':
                val_str = f"AC {comp['v_mag']}V ∠{comp['v_phase_deg']}°"
            else:
                if comp['type'] == 'IS':
                    val_str = f"AC {comp['i_mag']}A ∠{comp['i_phase_deg']}°"
                else: # R, L, C
                    unit = "Ω" if comp['type'] == 'R' else ("H" if comp['type'] == 'L' else "F")
                val_str = f"{comp['value']}{unit}"
            comp_details += f", Valor: {val_str}"

            self.circuit_diagram_canvas.create_text(15, y_pos, text=comp_details, anchor="w", fill=text_color, font=("Arial", 9))
            y_pos += 18
            if y_pos > ch - 20: # Stop if overflowing (simple check)
                self.circuit_diagram_canvas.create_text(15, y_pos, text="...", anchor="w", fill=text_color)
                break
        
        # Add ground symbol (conceptual)
        if '0' in [node for comp_item in parsed_components for node in comp_item['nodes']]:
            gnd_x, gnd_y_base = cw - 30, ch - 20
            if gnd_y_base > 30 : # Only draw if space
                self.circuit_diagram_canvas.create_line(gnd_x, gnd_y_base - 10, gnd_x, gnd_y_base, fill=text_color, width=1.5) # Vertical line
                self.circuit_diagram_canvas.create_line(gnd_x - 10, gnd_y_base, gnd_x + 10, gnd_y_base, fill=text_color, width=1.5) # Longest horizontal
                self.circuit_diagram_canvas.create_line(gnd_x - 6, gnd_y_base + 3, gnd_x + 6, gnd_y_base + 3, fill=text_color, width=1.5) # Medium
                self.circuit_diagram_canvas.create_line(gnd_x - 3, gnd_y_base + 6, gnd_x + 3, gnd_y_base + 6, fill=text_color, width=1.5) # Shortest
                self.circuit_diagram_canvas.create_text(gnd_x, gnd_y_base - 15, text="0", fill=text_color, font=("Arial", 8))


        print("[DEBUG] _update_static_circuit_diagram_from_netlist (placeholder) executado.")

    def _update_phasor_diagram_from_nodal(self, nodal_results):
        if not self.ax_main_plot or not nodal_results or not self.analysis_performed_successfully :
            self._clear_main_plot(error_message="Dados insuficientes ou erro na análise nodal para fasores.")
            return
        # Use self.parsed_components_for_plotting which should be set by analyze_circuit
        # if not self.parsed_components_for_plotting:
        #     self._clear_main_plot(error_message="Lista de componentes parseados não disponível para detalhar fasores.")
        #     return

        print("\n[DEBUG] Entrando em _update_phasor_diagram_from_nodal")
        # Surgical clear before plotting new data
        for artist in list(self.ax_main_plot.lines + self.ax_main_plot.patches + self.ax_main_plot.texts):
            artist.remove()
        if self.ax_main_plot.get_legend():
            self.ax_main_plot.get_legend().remove()
        # self.ax_main_plot.clear() # Replaced


        self.ax_main_plot.set_facecolor('white')
        self.fig_main_plot.patch.set_facecolor('white')

        if self.ax_main_plot_twin and self.ax_main_plot_twin.figure:
            self.ax_main_plot_twin.set_visible(False)

        phasors_to_plot = {}
        v_nodes = nodal_results.get('nodal_voltages_phasors', {})
        # Sort nodes for consistent legend order: '0', then '1', '2', ...
        sorted_node_keys = sorted(v_nodes.keys(), key=lambda x: int(x) if x.isdigit() and x != '0' else (-1 if x == '0' else float('inf')))

        for node_str in sorted_node_keys:
            v_phasor = v_nodes[node_str]
            if node_str == '0' and abs(v_phasor) < 1e-9 : continue # Skip V_gnd if zero
            phasors_to_plot[f"$V_{{{node_str}}}$ (Nó)"] = v_phasor

        i_src_total = nodal_results.get('i_source_total_phasor')
        if i_src_total is not None:
            phasors_to_plot["$I_S$ (Fonte Prim.)"] = i_src_total

        # Plot currents from independent current sources
        for comp_name, comp_current_phasor in nodal_results.get('component_currents_phasors', {}).items():
            if comp_name.upper().startswith("IS"): # Check if it's an IS component
                phasors_to_plot[f"$I_{{{comp_name}}}$"] = comp_current_phasor
        
        # Plot currents through R, L, C components (if self.parsed_components_for_plotting is available)
        component_currents = nodal_results.get('component_currents_phasors', {})
        if hasattr(self, 'parsed_components_for_plotting') and self.parsed_components_for_plotting:
            for comp_spec in self.parsed_components_for_plotting:
                comp_type = comp_spec['type'].upper()
                if comp_type in ['R', 'L', 'C']:
                    comp_name = comp_spec['name']
                    i_phasor = component_currents.get(comp_name)
                    if i_phasor is not None:
                        phasors_to_plot[f"$I_{{{comp_name}}}$ ({comp_type})"] = i_phasor

        # --- Three-Phase Source Phasor Plotting ---
        first_three_phase_source_parent_name = None
        first_three_phase_source_type = None
        if hasattr(self, 'parsed_components_for_plotting') and self.parsed_components_for_plotting:
            for comp_spec in self.parsed_components_for_plotting:
                if comp_spec.get('three_phase_parent') and comp_spec.get('three_phase_type') in ['VSY', 'VSD']:
                    first_three_phase_source_parent_name = comp_spec['three_phase_parent']
                    first_three_phase_source_type = comp_spec['three_phase_type']
                    break

        if first_three_phase_source_parent_name:
            print(f"[DEBUG] Plotting three-phase source: {first_three_phase_source_parent_name} ({first_three_phase_source_type})")
            if first_three_phase_source_type == 'VSY':
                phase_labels_map_v = {'A': 'AN', 'B': 'BN', 'C': 'CN'}
                current_phase_labels_i = ['A', 'B', 'C']

                for original_phase_char in ['A', 'B', 'C']:
                    decomposed_comp_name = f"{first_three_phase_source_parent_name}_{original_phase_char}"

                    v_phase_phasor = nodal_results.get('component_voltages_phasors', {}).get(decomposed_comp_name)
                    if v_phase_phasor is not None:
                        label_suffix_v = phase_labels_map_v.get(original_phase_char, original_phase_char + "N_ERR")
                        phasors_to_plot[f"$V_{{{label_suffix_v}}}$ ({first_three_phase_source_parent_name})"] = v_phase_phasor

                    i_line_phasor = nodal_results.get('component_currents_phasors', {}).get(decomposed_comp_name)
                    if i_line_phasor is not None:
                        label_suffix_i = current_phase_labels_i[ord(original_phase_char) - ord('A')]
                        phasors_to_plot[f"$I_{{{label_suffix_i}}}$ ({first_three_phase_source_parent_name})"] = i_line_phasor

            elif first_three_phase_source_type == 'VSD':
                phase_pair_labels_v = {'AB': 'AB', 'BC': 'BC', 'CA': 'CA'} # For V_LL
                # For I_delta (currents in the delta windings)
                delta_current_labels_i = {'AB': 'AB', 'BC': 'BC', 'CA': 'CA'}
                # For I_line (currents leaving the A,B,C terminals of the VSD)
                line_current_labels_i = ['A', 'B', 'C']
                
                currents_in_delta = {} # Store I_AB, I_BC, I_CA for line current calculation

                for phase_pair_char in ['AB', 'BC', 'CA']: # Order matters for I_line calc
                    decomposed_comp_name = f"{first_three_phase_source_parent_name}_{phase_pair_char}"

                    v_line_phasor = nodal_results.get('component_voltages_phasors', {}).get(decomposed_comp_name)
                    if v_line_phasor is not None:
                        phasors_to_plot[f"$V_{{{phase_pair_char}}}$ ({first_three_phase_source_parent_name})"] = v_line_phasor

                    i_delta_phasor = nodal_results.get('component_currents_phasors', {}).get(decomposed_comp_name)
                    if i_delta_phasor is not None:
                        currents_in_delta[phase_pair_char] = i_delta_phasor
                        phasors_to_plot[rf"$I_{{\Delta,{delta_current_labels_i[phase_pair_char]}}}$ ({first_three_phase_source_parent_name})"] = i_delta_phasor
                
                # Calculate and add line currents for VSD
                if 'AB' in currents_in_delta and 'CA' in currents_in_delta: phasors_to_plot[f"$I_{{L,{line_current_labels_i[0]}}}$ ({first_three_phase_source_parent_name})"] = currents_in_delta['AB'] - currents_in_delta['CA']
                if 'BC' in currents_in_delta and 'AB' in currents_in_delta: phasors_to_plot[f"$I_{{L,{line_current_labels_i[1]}}}$ ({first_three_phase_source_parent_name})"] = currents_in_delta['BC'] - currents_in_delta['AB']
                if 'CA' in currents_in_delta and 'BC' in currents_in_delta: phasors_to_plot[f"$I_{{L,{line_current_labels_i[2]}}}$ ({first_three_phase_source_parent_name})"] = currents_in_delta['CA'] - currents_in_delta['BC']


            # --- NEW: Calculate and add Line-to-Line voltages for the identified three-phase source ---
            if hasattr(self, 'three_phase_source_details_map') and \
               first_three_phase_source_parent_name in self.three_phase_source_details_map:
                
                original_nodes_info = self.three_phase_source_details_map[first_three_phase_source_parent_name]
                node_label_A = original_nodes_info.get('nA')
                node_label_B = original_nodes_info.get('nB')
                node_label_C = original_nodes_info.get('nC')

                all_nodal_voltages_phasors = nodal_results.get('nodal_voltages_phasors', {})
                V_A_phasor = all_nodal_voltages_phasors.get(node_label_A)
                V_B_phasor = all_nodal_voltages_phasors.get(node_label_B)
                V_C_phasor = all_nodal_voltages_phasors.get(node_label_C)

                if V_A_phasor is not None and V_B_phasor is not None:
                    phasors_to_plot[f"$V_{{AB}}$ ({first_three_phase_source_parent_name})"] = V_A_phasor - V_B_phasor
                if V_B_phasor is not None and V_C_phasor is not None:
                    phasors_to_plot[f"$V_{{BC}}$ ({first_three_phase_source_parent_name})"] = V_B_phasor - V_C_phasor
                if V_C_phasor is not None and V_A_phasor is not None:
                    phasors_to_plot[f"$V_{{CA}}$ ({first_three_phase_source_parent_name})"] = V_C_phasor - V_A_phasor

        base_colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkcyan', 'magenta', 'saddlebrown', 'olive', 'darkslateblue']
        max_val = 0; plotted_arrows = []; plotted_labels = []

        for i, (label, phasor) in enumerate(phasors_to_plot.items()):
            if phasor is not None and abs(phasor) > 1e-9: # Only plot significant phasors
                x, y = phasor.real, phasor.imag; mag_ph = abs(phasor)

                if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(mag_ph)):
                    print(f"[DEBUG] Pulando fasor {label} devido a valores não finitos: x={x}, y={y}, mag={mag_ph}")
                    continue

                hw = max(0.01, 0.04 * mag_ph); hl = max(0.02, 0.08 * mag_ph)

                color = base_colors[i % len(base_colors)]
                
                # Determine linestyle and linewidth based on phasor type
                if "$I_S$" in label or label.startswith("$I_{IS") or label.startswith(f"$I_{{L,") or (first_three_phase_source_parent_name and f"$I_{{" in label and first_three_phase_source_parent_name in label and not rf"$I_{{\Delta" in label): # Source line currents
                    linestyle = '--'
                    linewidth = 2.0
                elif " (R)" in label or " (L)" in label or " (C)" in label: # Passive component currents
                    linestyle = ':'
                    linewidth = 1.2 # Slightly thinner dotted line
                else: # Default (likely nodal voltages)
                    linestyle = '-' 
                    linewidth = 1.5
                
                try:
                    arrow = self.ax_main_plot.arrow(0, 0, x, y, head_width=hw, head_length=hl,
                                                fc=color, ec=color, linestyle=linestyle, linewidth=linewidth,
                                                length_includes_head=True, zorder=i + 5)
                    plotted_arrows.append(arrow)
                    plotted_labels.append(f"{label}: {self.format_phasor(phasor)}")
                    max_val = max(max_val, abs(x), abs(y), mag_ph)
                except Exception as e_arrow:
                    print(f"[DEBUG] Erro ao desenhar seta para {label}: {e_arrow}")

        if not plotted_arrows:
            self._clear_main_plot(initial_message="Nenhum fasor significativo para exibir da análise nodal.")
            return

        limit = max(1,max_val) * 1.2 # Ensure limit is at least 1.2 if max_val is small but non-zero
        self.ax_main_plot.set_xlim(-limit, limit); self.ax_main_plot.set_ylim(-limit, limit)
        self.ax_main_plot.set_xlabel("Componente Real"); self.ax_main_plot.set_ylabel("Componente Imaginário")
        self.ax_main_plot.set_title("Diagrama Fasorial (Análise Nodal)")
        self.ax_main_plot.axhline(0, color='black', lw=0.5); self.ax_main_plot.axvline(0, color='black', lw=0.5)
        self.ax_main_plot.grid(True, linestyle=':', alpha=0.7); self.ax_main_plot.set_aspect('equal', adjustable='box')

        if plotted_arrows and plotted_labels:
            self.ax_main_plot.legend(plotted_arrows, plotted_labels, loc='best', fontsize='x-small')
        # try:
        #     self.fig_main_plot.tight_layout() # Not needed with constrained_layout
        # except Exception as e: print(f"[DEBUG] _update_phasor_diagram_from_nodal tight_layout error: {e}")
        self.canvas_main_plot.draw_idle()
        print("[DEBUG] Diagrama fasorial nodal desenhado.")


    def format_phasor(self, complex_val, unit=""):
        # (Original format_phasor method - kept as is)
        if not isinstance(complex_val, complex) or cmath.isinf(complex_val) or cmath.isnan(complex_val): return self._format_value(complex_val, unit)
        mag=abs(complex_val); phase_rad=cmath.phase(complex_val)
        if mag<1e-12: phase_rad=0.0 # Avoid phase issues for near-zero magnitudes
        mag_fmt=self._format_value(mag)
        phase_disp=math.degrees(phase_rad) if self.angle_unit.get()=="degrees" else phase_rad
        angle_sym="°" if self.angle_unit.get()=="degrees" else " rad"
        # Normalize displayed angle for degrees to +/-180 if desired, or 0-360
        if self.angle_unit.get()=="degrees":
             phase_disp = (phase_disp + 180) % 360 - 180 # Normalize to -180 to 180

        if abs(phase_disp)<1e-9: phase_disp=0.0 # Clean up near-zero phase display
        phase_fmt=self._format_value(phase_disp)
        return f"{mag_fmt} {unit} ∠ {phase_fmt}{angle_sym}"

if __name__ == '__main__':
    root = ctk.CTk()
    app = ACCircuitAnalyzerApp(root)
    root.mainloop()