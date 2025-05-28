import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import cmath
import math
import numpy as np
import json
import re

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

        # --- Current analysis values for PF correction ---
        self.current_p_real = None
        self.current_q_reactive = None
        self.current_s_apparent = None
        self.current_fp_actual = None
        self.current_v_load_mag = None
        self.current_freq = None
        # ---

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

        tab_results.grid_columnconfigure(0, weight=1)
        tab_results.grid_rowconfigure(0, weight=1)
        tab_circuit.grid_columnconfigure(0, weight=1)
        tab_circuit.grid_rowconfigure(0, weight=1)
        tab_phasors.grid_columnconfigure(0, weight=1)
        tab_phasors.grid_rowconfigure(0, weight=1)

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

        self.fig_main_plot = Figure(figsize=(5, 4), dpi=100)
        self.ax_main_plot = self.fig_main_plot.add_subplot(111)
        self.canvas_main_plot = FigureCanvasTkAgg(self.fig_main_plot, master=self.plot_container_frame)
        canvas_widget = self.canvas_main_plot.get_tk_widget()
        canvas_widget.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.toolbar_main_plot = NavigationToolbar2Tk(self.canvas_main_plot, self.plot_container_frame, pack_toolbar=False)
        self.toolbar_main_plot.update()
        self.toolbar_main_plot.grid(row=1, column=0, sticky="ew", padx=2, pady=(0,2))

        self._clear_main_plot(initial_message="Diagrama Fasorial: Insira netlist e analise.")
        self._clear_static_circuit_diagram(initial_message="Diagrama do Circuito: Aguardando análise via netlist.")

        self.master.after(10, self._on_include_component_change)
        self._on_include_component_change()

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

        vs_source_defined_count = 0 # For auto-naming VS
        is_source_defined_count = 0 # For auto-naming IS
        e_source_count = 0 # For VCVS
        g_source_count = 0 # For VCCS
        h_source_count = 0 # For CCVS
        f_source_count = 0 # For CCCS

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
                        'value': v_mag # 'value' for consistency, might represent magnitude
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
                        'type': comp_type_char, 'name': name, 'nodes': (node1, node2), 'value': value
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
                        'value': i_mag # 'value' for consistency, represents magnitude
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
                        'gain': gain, 'value': gain
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
                        'gain': gain, 'value': gain
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
                        'gain': gain, 'value': gain
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
                        'gain': gain, 'value': gain
                    })
                except ValueError:
                    error_log.append(L_PREFIX + f"Invalid numeric value for gain (current gain) of CCCS {name}.")
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
            "# VS_mon 5 0 AC 1 0          # Fonte VS para monitorar corrente para H e F (exemplo)\n"
            "# H_exemplo 6 0 VS_mon 50    # CCVS: H<nome> <nó+> <nó-> <nome_VS_monitor> <ganho_Rm>\n"
            "# F_exemplo 7 0 VS_mon 100   # CCCS: F<nome> <nó_saída> <nó_entrada> <nome_VS_monitor> <ganho_beta>\n"
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
        scroll_frame=ctk.CTkScrollableFrame(self.about_dialog_window,fg_color="transparent"); scroll_frame.pack(expand=True,fill="both")
        content_frame=ctk.CTkFrame(scroll_frame); content_frame.pack(expand=True,fill="x",padx=15,pady=15)
        ctk.CTkLabel(content_frame,text="Analisador de Circuito CA",font=ctk.CTkFont(size=18,weight="bold")).pack(pady=(0,10))
        info_text=("**Versão:** 3.2.0 (Parse Fontes Controladas)\n\nFerramenta para análise de circuitos CA em frequência única.\n\n"
                   "**Funcionalidades Atuais:**\n- Análise Nodal de circuitos RLC com fontes de tensão CA independentes.\n"
                   "- Entrada via Netlist simplificada.\n"
                   "- Suporte a fontes de corrente CA independentes (IS).\n"
                   "- Reconhecimento de fontes controladas (VCVS, VCCS, CCVS, CCCS) na netlist.\n"
                   "- Cálculo de tensões nodais, correntes e tensões em componentes.\n"
                   "- Cálculo de potência (P,Q,S) e Fator de Potência para a fonte principal.\n"
                   "- Correção de Fator de Potência (baseado nos resultados da fonte principal).\n"
                   "- Diagrama Fasorial (Tensões Nodais, Corrente da Fonte Principal).\n"
                   "- Diagrama de Circuito (Placeholder para netlist).\n"
                   "- Salvar/Carregar configurações (incluindo netlist).\n\n"
                   "**Roadmap:**\n- Suporte a supernós (fontes de tensão flutuantes).\n"
                   "- Estampagem MNA completa para fontes controladas (VCVS, VCCS, CCVS, CCCS).\n"
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

            self.current_p_real = self.analysis_results.get('p_total_avg_W')
            self.current_q_reactive = self.analysis_results.get('q_total_VAR')
            self.current_s_apparent = self.analysis_results.get('s_total_apparent_VA')
            self.current_fp_actual = self.analysis_results.get('fp_total')
            vs_phasor_for_pf = self.analysis_results.get('v_source_phasor')
            self.current_v_load_mag= abs(vs_phasor_for_pf) if vs_phasor_for_pf else 0
            self.current_freq = frequency

            if self.analysis_results.get('error_messages'):
                output_text += "Análise Nodal encontrou problemas:\n" + "\n".join(self.analysis_results['error_messages']) + "\n\n"

            output_text += self._generate_nodal_analysis_details_text(self.analysis_results, parsed_components)
            self.analysis_performed_successfully = not bool(self.analysis_results.get('error_messages')) and \
                                               bool(self.analysis_results.get('nodal_voltages_phasors'))


            self._update_static_circuit_diagram_from_netlist(parsed_components, frequency, self.analysis_results)
            self._update_phasor_diagram_from_nodal(self.analysis_results, parsed_components)

        except Exception as e:
            self.results_text.delete("1.0","end"); error_msg=f"Erro inesperado na análise: {str(e)}";
            messagebox.showerror("Erro Inesperado",error_msg); self.results_text.insert("1.0",error_msg)
            self._clear_main_plot(error_message="Erro na análise.")
            self._clear_static_circuit_diagram(error_message="Erro na análise.")
            import traceback; traceback.print_exc()
            self.analysis_performed_successfully = False
        finally:
            self.progress_bar.stop();self.progress_bar.pack_forget();self.progress_bar_frame.pack_forget();
            self.results_text.configure(state="normal") # Ensure it's normal before inserting
            self.results_text.delete("1.0", "end") # Clear previous content before inserting new
            self.results_text.insert("1.0", output_text if output_text.strip() else "Análise concluída. Verifique os resultados.")
            self.results_text.configure(state="disabled")


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
            self.ax_main_plot.set_visible(True) # Ensure main axis is visible
            self.ax_main_plot.clear()

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

            try:
                self.fig_main_plot.tight_layout()
            except Exception as e:
                print(f"[DEBUG] _clear_main_plot tight_layout error: {e}")
            
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

    def _update_phasor_diagram_from_nodal(self, nodal_results, parsed_components_list):
        if not self.ax_main_plot or not nodal_results or not self.analysis_performed_successfully :
            self._clear_main_plot(error_message="Dados insuficientes ou erro na análise nodal para fasores.")
            return
        if not parsed_components_list: # Need parsed components to identify RLC types
            self._clear_main_plot(error_message="Lista de componentes não disponível para detalhar fasores de corrente RLC.")
            return

        print("\n[DEBUG] Entrando em _update_phasor_diagram_from_nodal")
        self.ax_main_plot.clear()
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
        
        # Plot currents through R, L, C components
        component_currents = nodal_results.get('component_currents_phasors', {})
        for comp_spec in parsed_components_list:
            comp_type = comp_spec['type'].upper()
            if comp_type in ['R', 'L', 'C']:
                comp_name = comp_spec['name']
                i_phasor = component_currents.get(comp_name)
                if i_phasor is not None:
                    phasors_to_plot[f"$I_{{{comp_name}}}$ ({comp_type})"] = i_phasor


        base_colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkcyan', 'magenta', 'saddlebrown', 'olive', 'darkslateblue']
        max_val = 0; plotted_arrows = []; plotted_labels = []

        for i, (label, phasor) in enumerate(phasors_to_plot.items()):
            if phasor is not None and abs(phasor) > 1e-9: # Only plot significant phasors
                x, y = phasor.real, phasor.imag; mag_ph = abs(phasor)
                hw = max(0.01, 0.04 * mag_ph); hl = max(0.02, 0.08 * mag_ph)

                color = base_colors[i % len(base_colors)]
                
                # Determine linestyle and linewidth based on phasor type
                if "$I_S$" in label or label.startswith("$I_{IS"): # Source currents (VS primary, IS)
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
        try: self.fig_main_plot.tight_layout()
        except Exception as e: print(f"[DEBUG] _update_phasor_diagram_from_nodal tight_layout error: {e}")
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