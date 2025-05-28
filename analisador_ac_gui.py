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
        master_window.title("Analisador de Circuito CA (CustomTkinter) - Frequência Única")
        master_window.geometry("1100x800") 

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.angle_unit = tk.StringVar(value="degrees")
        self.circuit_topology_var = tk.StringVar(value="Série")
        self.decimal_places_var = tk.StringVar(value="3")
        self.scientific_notation_var = tk.BooleanVar(value=False)

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

        main_app_frame = ctk.CTkFrame(master_window, fg_color="transparent")
        main_app_frame.pack(expand=True, fill="both", padx=5, pady=5)

        title_label = ctk.CTkLabel(main_app_frame, text="Analisador de Circuito CA (Frequência Única)",
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

        netlist_main_label = ctk.CTkLabel(left_panel_scroll_frame, text="Entrada via Netlist", font=ctk.CTkFont(size=16, weight="bold"))
        netlist_main_label.pack(pady=(15,5), anchor="w", padx=10)
        netlist_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        netlist_frame.pack(pady=(0,10), padx=10, fill="x")
        self.netlist_textbox = ctk.CTkTextbox(netlist_frame, height=150, wrap="word", font=ctk.CTkFont(family="monospace", size=11))
        self.netlist_textbox.pack(expand=True, fill="x", padx=5, pady=5)
        self.netlist_textbox.insert("1.0",
            "# Exemplo Netlist RLC Série (para teste inicial):\n"
            "# VS 1 0 AC 220 0\n"
            "# R1 1 2 10\n# L1 2 0 0.02122\n" 
            "# TOPOLOGIA SERIE\n# FREQ_DETALHES 60\n"
        )
        process_netlist_button = ctk.CTkButton(netlist_frame, text="Processar Netlist e Aplicar", command=self._parse_and_apply_netlist)
        process_netlist_button.pack(pady=5, padx=5)

        topology_main_label = ctk.CTkLabel(left_panel_scroll_frame, text="Config. Circuito (Manual / Equivalente Netlist)",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        topology_main_label.pack(pady=(10,5), anchor="w", padx=10)
        topology_frame = ctk.CTkFrame(left_panel_scroll_frame, corner_radius=10)
        topology_frame.pack(pady=(0,10), padx=10, fill="x")
        ctk.CTkLabel(topology_frame, text="Topologia Principal (R_eq, L_eq, C_eq):").pack(side="left", padx=(10,10), pady=10)
        self.topology_selector = ctk.CTkSegmentedButton(
            topology_frame, values=["Série", "Paralelo"],
            variable=self.circuit_topology_var, command=self._on_parameter_change)
        self.topology_selector.pack(side="left", expand=True, fill="x", padx=10, pady=10)

        input_section_label = ctk.CTkLabel(left_panel_scroll_frame, text="Parâmetros (Manual / Equivalente Netlist)",
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

        ctk.CTkLabel(input_frame, text="Frequência de Análise (Hz):").grid(row=5, column=0, columnspan=2, padx=10, pady=8, sticky="w")
        self.freq_details_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 60"); self.freq_details_entry.insert(0, "60")
        self.freq_details_entry.grid(row=5, column=2, padx=(0,10), pady=8, sticky="ew")
        self.freq_details_entry.bind("<FocusOut>", self._on_parameter_change); self.freq_details_entry.bind("<Return>", self._on_parameter_change)
        self.entry_widgets['freq_details'] = self.freq_details_entry

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
        analyze_button = ctk.CTkButton(action_buttons_frame, text="Analisar Circuito", command=self.analyze_circuit)
        analyze_button.pack(side="left", padx=5, expand=True)
        clear_button = ctk.CTkButton(action_buttons_frame, text="Limpar Entradas e Netlist", command=self.clear_entries)
        clear_button.pack(side="left", padx=5, expand=True)
        about_button = ctk.CTkButton(action_buttons_frame, text="Sobre", command=self.show_about_dialog_ctk)
        about_button.pack(side="left", padx=5, expand=True)
        
        self.progress_bar_frame = ctk.CTkFrame(left_panel_scroll_frame, fg_color="transparent")
        self.progress_bar = ctk.CTkProgressBar(self.progress_bar_frame, orientation="horizontal", mode="indeterminate")
        self.note_label = ctk.CTkLabel(left_panel_scroll_frame, text="Nota: Analisa RLC Série/Paralelo (ou equivalentes Netlist) em frequência única.", font=ctk.CTkFont(size=12), text_color="gray50")
        self.note_label.pack(pady=(10,10), side="bottom")

        right_panel_frame = ctk.CTkFrame(panels_frame, corner_radius=10)
        right_panel_frame.grid(row=0, column=1, sticky="nsew", padx=(10,0), pady=0)
        # Configura o right_panel_frame para expandir o TabView
        right_panel_frame.grid_rowconfigure(0, weight=1)
        right_panel_frame.grid_columnconfigure(0, weight=1)

        # Criar TabView
        tab_view = ctk.CTkTabview(right_panel_frame, corner_radius=8)
        tab_view.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        tab_results = tab_view.add("Resultados")
        tab_circuit = tab_view.add("Circuito")
        tab_phasors = tab_view.add("Fasores")

        # Configurar grid das abas para expansão do conteúdo
        tab_results.grid_columnconfigure(0, weight=1)
        tab_results.grid_rowconfigure(0, weight=1)

        tab_circuit.grid_columnconfigure(0, weight=1)
        tab_circuit.grid_rowconfigure(0, weight=1)

        tab_phasors.grid_columnconfigure(0, weight=1)
        tab_phasors.grid_rowconfigure(0, weight=1) # Para o canvas do plot
        # A rowconfigure para a toolbar dentro do plot_container_frame é mantida como está

        # Aba "Resultados"
        self.results_text = ctk.CTkTextbox(tab_results, corner_radius=6, wrap="word", font=ctk.CTkFont(family="monospace", size=11))
        self.results_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.results_text.configure(state="disabled")

        # Aba "Circuito" - Frame e Canvas para o Diagrama Estático
        self.circuit_diagram_frame = ctk.CTkFrame(tab_circuit, corner_radius=6)
        self.circuit_diagram_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.circuit_diagram_frame.grid_columnconfigure(0, weight=1)
        self.circuit_diagram_frame.grid_rowconfigure(0, weight=1)
        
        self.circuit_diagram_canvas = tk.Canvas(self.circuit_diagram_frame, bg=self._get_ctk_bg_color(), highlightthickness=0)
        self.circuit_diagram_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Aba "Fasores" - Container para o diagrama fasorial (Matplotlib)
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

        self._clear_main_plot(initial_message="Diagrama Fasorial: Selecione parâmetros e analise.")
        self._clear_static_circuit_diagram(initial_message="Diagrama do Circuito: Aguardando análise.")

        self.master.after(10, self._on_include_component_change)
        self._on_include_component_change()

    def _get_ctk_bg_color(self):
        """Retorna a cor de fundo apropriada para o tema CTk."""
        # Tenta obter a cor de fundo do CTkFrame, senão usa um padrão.
        try:
            bg_color_tuple = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
            current_mode = ctk.get_appearance_mode()
            if isinstance(bg_color_tuple, (list, tuple)) and len(bg_color_tuple) == 2:
                return bg_color_tuple[0] if current_mode == "Light" else bg_color_tuple[1]
            return bg_color_tuple # Se for uma string única
        except Exception:
            return "white" if ctk.get_appearance_mode() == "Light" else "#2B2B2B" # Fallback mais comum para CTk
            
    def _get_ctk_text_color(self):
        """Retorna a cor de texto apropriada para o tema CTk."""
        try:
            text_color_tuple = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
            current_mode = ctk.get_appearance_mode()
            if isinstance(text_color_tuple, (list, tuple)) and len(text_color_tuple) == 2:
                return text_color_tuple[0] if current_mode == "Light" else text_color_tuple[1]
            return text_color_tuple # Se for uma string única
        except Exception:
            return "black" if ctk.get_appearance_mode() == "Light" else "white" # Fallback

            
    def _recreate_canvas(self):
        """Helper para recriar o canvas e a toolbar. (TESTE DRÁSTICO)"""
        print("[DEBUG RECREATE_CANVAS] Tentando recriar FigureCanvasTkAgg e Toolbar...")
        
        # Destruir widgets antigos se existirem
        if hasattr(self, 'canvas_main_plot') and self.canvas_main_plot and hasattr(self.canvas_main_plot, 'get_tk_widget'):
            tk_widget = self.canvas_main_plot.get_tk_widget()
            if tk_widget: # Verifica se o widget ainda existe antes de chamar destroy
                tk_widget.destroy()
                print("[DEBUG RECREATE_CANVAS] Widget do canvas antigo destruído.")
        self.canvas_main_plot = None 

        if hasattr(self, 'toolbar_main_plot') and self.toolbar_main_plot:
            self.toolbar_main_plot.destroy()
            print("[DEBUG RECREATE_CANVAS] Toolbar antiga destruída.")
        self.toolbar_main_plot = None

        if not self.fig_main_plot or not self.ax_main_plot: # Garante que a figura e o eixo base existam
            print("[DEBUG RECREATE_CANVAS] Recriando fig_main_plot e ax_main_plot pois não existiam ou foram invalidados.")
            self.fig_main_plot = Figure(figsize=(5, 4), dpi=100)
            self.ax_main_plot = self.fig_main_plot.add_subplot(111)

        self.canvas_main_plot = FigureCanvasTkAgg(self.fig_main_plot, master=self.plot_container_frame)
        canvas_widget = self.canvas_main_plot.get_tk_widget()
        canvas_widget.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.toolbar_main_plot = NavigationToolbar2Tk(self.canvas_main_plot, self.plot_container_frame, pack_toolbar=False)
        self.toolbar_main_plot.update()
        self.toolbar_main_plot.grid(row=1, column=0, sticky="ew", padx=2, pady=(0,2))
        print("[DEBUG RECREATE_CANVAS] Novo canvas e toolbar criados e posicionados.")

    def _calculate_equivalent_series(self, values):
        if not values: return 0.0
        return sum(values)

    def _calculate_equivalent_parallel(self, values):
        if not values: return 0.0
        sum_inverses = 0.0
        for v in values:
            if v > 1e-12: sum_inverses += 1.0 / v
            else: return 0.0
        if sum_inverses > 1e-12: return 1.0 / sum_inverses
        else: return float('inf')

    def _calculate_capacitors_parallel(self, values):
        if not values: return 0.0
        return sum(values)

    def _calculate_capacitors_series(self, values):
        if not values: return 0.0
        sum_inverses_c = 0.0
        for v in values:
            if v > 1e-12: sum_inverses_c += 1.0 / v
            else: return 0.0
        if sum_inverses_c > 1e-12: return 1.0 / sum_inverses_c
        else: return float('inf')

    def _parse_and_apply_netlist(self):
        netlist_content = self.netlist_textbox.get("1.0", tk.END).strip()
        if not netlist_content: messagebox.showinfo("Netlist", "A área de netlist está vazia."); return
        parsed_components={'R':[],'L':[],'C':[]}; v_mag,v_phase=None,None; freq_details_from_netlist=None; topology_from_netlist=None; error_log=[]
        vs_pattern=re.compile(r"VS\s+\w+\s+\w+\s+AC\s+([\d\.]+)\s*([\d\.]*)",re.IGNORECASE); comp_pattern=re.compile(r"([RCL])([A-Z0-9_]*)\s+(\w+)\s+(\w+)\s+([\d\.eE\-+]+)",re.IGNORECASE)
        topo_pattern=re.compile(r"TOPOLOGIA\s+(SERIE|PARALELO)",re.IGNORECASE); freq_det_pattern=re.compile(r"FREQ_DETALHES\s+([\d\.]+)",re.IGNORECASE); source_defined=False
        for l_num,line in enumerate(netlist_content.splitlines(),1):
            line=line.strip().upper(); L=f"L{l_num}: "
            if not line or line.startswith("#") or line.startswith("*"): continue
            m_vs=vs_pattern.match(line); m_comp=comp_pattern.match(line); m_topo=topo_pattern.match(line); m_freq=freq_det_pattern.match(line)
            if m_vs:
                if source_defined: error_log.append(L+"Múltiplas VS."); continue
                try: v_mag=float(m_vs.group(1)); v_phase=float(m_vs.group(2)) if m_vs.group(2) else 0.0; source_defined=True
                except ValueError: error_log.append(L+"Valor VS inválido."); continue
            elif m_comp:
                try: val=float(m_comp.group(5));parsed_components[m_comp.group(1)].append(val)
                except ValueError: error_log.append(L+f"Valor {m_comp.group(1)} inválido."); continue
                if val<0: error_log.append(L+f"Valor {m_comp.group(1)}<0."); continue
            elif m_topo:
                if topology_from_netlist: error_log.append(L+"Múltiplas TOPOLOGIA."); continue
                topology_from_netlist=m_topo.group(1).capitalize()
            elif m_freq:
                if freq_details_from_netlist: error_log.append(L+"Múltiplas FREQ_DETALHES."); continue
                try: freq_val=float(m_freq.group(1)); freq_details_from_netlist=freq_val
                except ValueError: error_log.append(L+"Valor FREQ_DETALHES inválido."); continue
                if freq_val<=0: error_log.append(L+"FREQ_DETALHES<=0."); freq_details_from_netlist=None; continue
            else: error_log.append(L+f"Sintaxe: {line}")
        if not source_defined and not any(parsed_components.values()): error_log.append("Nenhuma fonte ou componente.")
        if error_log: messagebox.showerror("Erro Netlist","\n".join(error_log)); return
        r_eq,l_eq,c_eq=0.0,0.0,0.0; eff_topo=topology_from_netlist or self.circuit_topology_var.get()
        if parsed_components['R']: r_eq=self._calculate_equivalent_series(parsed_components['R']) if eff_topo=="Série" else self._calculate_equivalent_parallel(parsed_components['R'])
        if parsed_components['L']: l_eq=self._calculate_equivalent_series(parsed_components['L']) if eff_topo=="Série" else self._calculate_equivalent_parallel(parsed_components['L'])
        if parsed_components['C']: c_eq=self._calculate_capacitors_series(parsed_components['C']) if eff_topo=="Série" else self._calculate_capacitors_parallel(parsed_components['C'])
        if v_mag is not None: self.v_mag_entry.delete(0,tk.END); self.v_mag_entry.insert(0,str(v_mag))
        if v_phase is not None: self.v_phase_entry.delete(0,tk.END); self.v_phase_entry.insert(0,str(v_phase))
        self.include_r_var.set(bool(parsed_components['R'])and r_eq!=float('inf')); self.r_entry.delete(0,tk.END); self.r_entry.insert(0,self._format_value_for_entry(r_eq if r_eq!=float('inf')else 0.0))
        self.include_l_var.set(bool(parsed_components['L'])and l_eq!=float('inf')); self.l_entry.delete(0,tk.END); self.l_entry.insert(0,self._format_value_for_entry(l_eq if l_eq!=float('inf')else 0.0))
        self.include_c_var.set(bool(parsed_components['C'])and c_eq!=float('inf')); self.c_entry.delete(0,tk.END); self.c_entry.insert(0,self._format_value_for_entry(c_eq if c_eq!=float('inf')else 0.0))
        if topology_from_netlist: self.circuit_topology_var.set(topology_from_netlist)
        if freq_details_from_netlist: self.freq_details_entry.delete(0,tk.END); self.freq_details_entry.insert(0,str(freq_details_from_netlist))
        self._on_include_component_change(); self._on_parameter_change(); messagebox.showinfo("Netlist Processada","Netlist aplicada.")

    def _format_value_for_entry(self, value, precision=6):
        if value == float('inf'): return "inf"
        if abs(value) < 1e-9 and value != 0: return f"{value:.{precision}e}"
        if abs(value) > 1e7: return f"{value:.{precision}e}"
        formatted_val = f"{value:.{precision}g}" 
        if 'e' not in formatted_val and '.' in formatted_val and len(formatted_val.split('.')[1]) > precision + 2 and value !=0:
            return f"{value:.{precision}e}" if abs(value) < 1e-4 else f"{value:.{precision}f}".rstrip('0').rstrip('.')
        return formatted_val

    def _on_parameter_change(self, event=None, from_combobox_value=None):
        self.analysis_performed_successfully = False

    def _on_formatting_change(self, event_or_choice=None):
        if self.results_text.get("1.0", "end-1c").strip() and self.analysis_performed_successfully:
             self.analyze_circuit() 

    def _on_include_component_change(self, event=None):
        self.r_entry.configure(state="normal" if self.include_r_var.get() else "disabled")
        self.l_entry.configure(state="normal" if self.include_l_var.get() else "disabled")
        self.c_entry.configure(state="normal" if self.include_c_var.get() else "disabled")
        self.analysis_performed_successfully = False

    def _format_value(self, value, unit=""):
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
                self.freq_details_entry.delete(0,tk.END); self.freq_details_entry.insert(0,ld.get('freq_details',"159"))
                self.angle_unit.set(ld.get('angle_unit',"degrees")); self.circuit_topology_var.set(ld.get('topology',"Série"))
                self.decimal_places_var.set(ld.get('decimal_places',"3")); self.scientific_notation_var.set(ld.get('scientific_notation',False))
                self.netlist_textbox.delete("1.0", tk.END); self.netlist_textbox.insert("1.0", ld.get('netlist_content', "# Insira netlist"))
                self.fp_desired_entry.delete(0, tk.END); self.fp_desired_entry.insert(0, ld.get('fp_desired', ""))
                messagebox.showinfo("Carregar","Configuração carregada!")
                self._on_parameter_change(); self.analysis_performed_successfully = False
                self._clear_main_plot(initial_message="Diagrama Fasorial: Configuração carregada, analise novamente.")
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
            current_border_color = widget.cget("border_color")
            if isinstance(current_border_color, (list, tuple)) and len(current_border_color) == 2: widget.configure(border_color=[tc,tc])
            elif isinstance(current_border_color, str): widget.configure(border_color=tc)

    def _clear_all_entry_error_styles(self):
        for wk in self.entry_widgets: self._set_entry_error_style(wk,is_error=False)

    def _validate_all_parameters(self, silent=True):
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
            if not silent: messagebox.showerror("Erro Entrada","\n".join(list(dict.fromkeys(error_messages))))
            return None,list(dict.fromkeys(error_messages))
        return params,None

    def clear_entries(self):
        self._clear_all_entry_error_styles()
        self.r_entry.delete(0,"end"); self.r_entry.insert(0,"10"); self.l_entry.delete(0,"end"); self.l_entry.insert(0,"0.01"); self.c_entry.delete(0,"end"); self.c_entry.insert(0,"0.00001")
        self.include_r_var.set(True); self.include_l_var.set(True); self.include_c_var.set(True); self._on_include_component_change()
        self.v_mag_entry.delete(0,"end"); self.v_mag_entry.insert(0,"10"); self.v_phase_entry.delete(0,"end"); self.v_phase_entry.insert(0,"0")
        self.freq_details_entry.delete(0,"end"); self.freq_details_entry.insert(0,"159"); self.fp_desired_entry.delete(0,tk.END)
        self.angle_unit.set("degrees"); self.circuit_topology_var.set("Série"); self.decimal_places_var.set("3"); self.scientific_notation_var.set(False) 
        self.netlist_textbox.delete("1.0",tk.END); self.netlist_textbox.insert("1.0","# Exemplo Netlist RLC Série:\n# VS 1 0 AC 10 0\n# R1 1 2 10\n# L1 2 3 0.01\n# C1 3 0 1e-5\n# TOPOLOGIA SERIE\n# FREQ_DETALHES 159\n")
        self.results_text.configure(state="normal"); self.results_text.delete("1.0","end"); self.results_text.configure(state="disabled")
        self._clear_main_plot(initial_message="Diagrama Fasorial: Selecione parâmetros e analise.")
        self._clear_static_circuit_diagram(initial_message="Diagrama do Circuito: Entradas limpas.")
        self._on_parameter_change(); self.analysis_performed_successfully=False

    def _grab_toplevel_safely(self, toplevel_window):
        if toplevel_window and toplevel_window.winfo_exists():
            try: toplevel_window.grab_set()
            except tk.TclError: pass 

    def show_about_dialog_ctk(self):
        if self.about_dialog_window and self.about_dialog_window.winfo_exists(): self.about_dialog_window.lift(); self.about_dialog_window.focus_set(); return
        self.about_dialog_window=ctk.CTkToplevel(self.master); self.about_dialog_window.title("Sobre Analisador de Circuito CA"); self.about_dialog_window.geometry("500x640")
        self.about_dialog_window.transient(self.master); self.about_dialog_window.after(50,self._grab_toplevel_safely,self.about_dialog_window)
        scroll_frame=ctk.CTkScrollableFrame(self.about_dialog_window,fg_color="transparent"); scroll_frame.pack(expand=True,fill="both")
        content_frame=ctk.CTkFrame(scroll_frame); content_frame.pack(expand=True,fill="x",padx=15,pady=15)
        ctk.CTkLabel(content_frame,text="Analisador de Circuito CA",font=ctk.CTkFont(size=18,weight="bold")).pack(pady=(0,15))
        info_text=("**Versão:** 2.5.0 (Foco Diagrama Fasorial)\n\nFerramenta para análise de circuitos RLC CA em frequência única.\n\n"
                   "**Funcionalidades:**\n- Análise RLC Série/Paralelo (eq.) em freq. única.\n- Entrada via Netlist e manual.\n"
                   "- Cálculo de RLC equivalentes.\n- Análise detalhada (Z, I, V, Potências P,Q,S, FP).\n- Cálculo de f0, Q, BW teóricos.\n"
                   "- Correção de Fator de Potência.\n- Diagrama Fasorial (V, I Total, I Ramos em Paralelo).\n- Salvar/Carregar configurações.\n\n"
                   "**Nota:** A visualização de formas de onda foi temporariamente removida.\n\n"
                   "**Roadmap:** Editor Visual, Análise Nodal, Trifásico.")
        ctk.CTkLabel(content_frame,text=info_text,justify="left",wraplength=420).pack(pady=10,padx=5,anchor="w")
        ctk.CTkButton(content_frame,text="Fechar",command=self.about_dialog_window.destroy,width=100).pack(pady=(15,5))
        self.about_dialog_window.after(10,self._center_toplevel_after_draw,self.about_dialog_window); self.about_dialog_window.focus_set()

    def _center_toplevel_after_draw(self, toplevel_window):
        toplevel_window.update_idletasks()
        mw,mh,mx,my=self.master.winfo_width(),self.master.winfo_height(),self.master.winfo_x(),self.master.winfo_y()
        pw,ph=toplevel_window.winfo_width(),toplevel_window.winfo_height()
        if pw<=1 or ph<=1:
            try: s=str(toplevel_window.geometry()).split('+')[0]; pw,ph=map(int,s.split('x'))
            except: pw,ph=500,640
        toplevel_window.geometry(f"{pw}x{ph}+{(mx+(mw-pw)//2)}+{(my+(mh-ph)//2)}")

    def _perform_core_analysis(self, circuit_params):
        results = {}
        r_val = circuit_params.get('r_val',0.0); l_val = circuit_params.get('l_val',0.0); c_val = circuit_params.get('c_val',0.0)
        v_mag=circuit_params.get('v_mag',0);v_phase_deg=circuit_params.get('v_phase_deg',0)
        topology=circuit_params.get('topology',"Série");freq=circuit_params.get('freq_details')

        results['v_source_phasor']=cmath.rect(v_mag,math.radians(v_phase_deg))
        results['r_val'] = r_val; results['l_val'] = l_val; results['c_val'] = c_val
        results['topology'] = topology; results['freq'] = freq

        z_r_val = complex(r_val, 0)
        z_l_val = complex(0, 2 * math.pi * freq * l_val) if l_val > 1e-12 and freq > 1e-12 else complex(0,0)
        z_c_val = complex(0, -1 / (2 * math.pi * freq * c_val)) if c_val > 1e-12 and freq > 1e-12 else complex(0, -float('inf'))
        
        results['z_r_phasor'] = z_r_val; results['z_l_phasor'] = z_l_val; results['z_c_phasor'] = z_c_val
        it = 0j 
        if topology=="Série":
            results['z_total_phasor'] = z_r_val + z_l_val + z_c_val
            if abs(results['z_total_phasor']) < 1e-12: it = results['v_source_phasor'] / (1e-12 + 0j) if abs(results['v_source_phasor']) > 1e-12 else 0j
            elif cmath.isinf(results['z_total_phasor']): it = 0j
            else: it = results['v_source_phasor'] / results['z_total_phasor']
            results['i_total_phasor'] = it
            results['v_r_phasor'] = it * z_r_val; results['v_l_phasor'] = it * z_l_val
            results['v_c_phasor'] = it * z_c_val if not cmath.isinf(z_c_val.imag) else results['v_source_phasor'] - results['v_r_phasor'] - results['v_l_phasor']
            results['i_r_phasor'] = it if r_val > 1e-12 else 0j; results['i_l_phasor'] = it if l_val > 1e-12 else 0j
            results['i_c_phasor'] = it if c_val > 1e-12 and not cmath.isinf(z_c_val.imag) else 0j
        elif topology=="Paralelo":
            yr = 1/z_r_val if r_val > 1e-12 else (complex(float('inf'),0) if r_val == 0 else 0j)
            yl = 1/z_l_val if l_val > 1e-12 and abs(z_l_val.imag) > 1e-12 else 0j
            yc = 0j
            if c_val > 1e-12: yc = 1/z_c_val if not cmath.isinf(z_c_val.imag) and abs(z_c_val.imag) > 1e-12 else (complex(float('inf'),0) if abs(z_c_val.imag)<1e-12 else 0j)
            y_total = yr + yl + yc
            results['z_total_phasor'] = 1/y_total if abs(y_total) > 1e-12 and not cmath.isinf(y_total) else (0j if cmath.isinf(y_total) else complex(float('inf'),0))
            results['i_total_phasor'] = results['v_source_phasor'] * y_total
            results['v_r_phasor'] = results['v_source_phasor'] if r_val > 1e-12 or (r_val == 0 and topology == "Paralelo") else 0j
            results['v_l_phasor'] = results['v_source_phasor'] if l_val > 1e-12 else 0j
            results['v_c_phasor'] = results['v_source_phasor'] if c_val > 1e-12 else 0j
            results['i_r_phasor'] = results['v_source_phasor'] * yr if r_val > 1e-12 or (r_val == 0 and topology == "Paralelo") else 0j
            results['i_l_phasor'] = results['v_source_phasor'] * yl if l_val > 1e-12 else 0j
            results['i_c_phasor'] = results['v_source_phasor'] * yc if c_val > 1e-12 else 0j
        
        s_complex = results['v_source_phasor'] * results['i_total_phasor'].conjugate()
        results['p_total'] = s_complex.real; results['q_total'] = s_complex.imag; results['s_total_apparent'] = abs(s_complex)
        results['fp_total'] = results['p_total'] / results['s_total_apparent'] if results['s_total_apparent'] > 1e-9 else (1.0 if abs(results['p_total'])<1e-9 and abs(results['q_total'])<1e-9 else 0.0)
        results['fp_total'] = max(-1.0, min(1.0, results['fp_total']))
        results['p_r_comp'] = (abs(results.get('i_r_phasor',0j))**2)*r_val if topology=="Série" and r_val>1e-12 else (abs(results.get('v_r_phasor',0j))**2/r_val if topology=="Paralelo" and r_val>1e-12 else 0.0)
        if r_val==0 and topology=="Paralelo" and yr!=0j and abs(yr.real if yr else 0)==float('inf'): results['p_r_comp'] = (results['v_source_phasor']*results.get('i_r_phasor',0j).conjugate()).real
        xl_val=z_l_val.imag; results['q_l_comp']=(abs(results.get('i_l_phasor',0j))**2)*xl_val if topology=="Série" and l_val>1e-12 and abs(xl_val)>1e-12 else (abs(results.get('v_l_phasor',0j))**2/xl_val if topology=="Paralelo" and l_val>1e-12 and abs(xl_val)>1e-12 else 0.0)
        xc_val=z_c_val.imag; results['q_c_comp']=(abs(results.get('i_c_phasor',0j))**2)*xc_val if topology=="Série" and c_val>1e-12 and not math.isinf(xc_val) and abs(xc_val)>1e-12 else (abs(results.get('v_c_phasor',0j))**2/xc_val if topology=="Paralelo" and c_val>1e-12 and not math.isinf(xc_val) and abs(xc_val)>1e-12 else 0.0)
        return results

    def analyze_circuit(self):
        self.results_text.configure(state="normal"); self.results_text.delete("1.0","end"); self._clear_all_entry_error_styles(); self.analysis_performed_successfully=False
        self.analysis_results = {} 
        params,errors=self._validate_all_parameters(silent=False)
        if not params: 
            self.results_text.insert("1.0","Erro de entrada:\n"+"\n".join(errors or ["Valores inválidos."])); 
            self.results_text.configure(state="disabled"); 
            self._clear_main_plot(error_message="Parâmetros inválidos.")
            return

        self.progress_bar_frame.pack(pady=(5,0),padx=10,fill="x",before=self.note_label); self.progress_bar.pack(pady=5,padx=0,fill="x"); self.progress_bar.start(); self.master.update_idletasks()
        output_text=""
        try:
            if params.get('freq_details') and params['freq_details'] > 0:
                self.analysis_results = self._perform_core_analysis(params)
                self.current_p_real=self.analysis_results.get('p_total'); self.current_q_reactive=self.analysis_results.get('q_total')
                self.current_s_apparent=self.analysis_results.get('s_total_apparent'); self.current_fp_actual=self.analysis_results.get('fp_total')
                self.current_v_load_mag=abs(self.analysis_results.get('v_source_phasor',0j))
                self.current_freq=params['freq_details']

                f0_res=None; r,l,c=params.get('r_val',0.0),params.get('l_val',0.0),params.get('c_val',0.0)
                if l>1e-12 and c>1e-12:
                    try: f0_res=1/(2*math.pi*math.sqrt(l*c))
                    except: pass 
                q_s, bw_s, f0_s = "N/A", "N/A", "N/A"
                if f0_res:
                    f0_s=self._format_value(f0_res,"Hz"); w0=2*math.pi*f0_res; q_v=None
                    if params['topology']=="Série": q_v=(w0*l)/r if r>1e-12 else float('inf')
                    elif params['topology']=="Paralelo": q_v=r/(w0*l) if r>1e-12 and l>1e-12 and w0>1e-9 else (w0*c*r if r>1e-12 and c>1e-12 and w0>1e-9 else (0.0 if r==0 else None))
                    if q_v is not None:
                        if q_v==float('inf'): q_s,bw_s="Infinito",self._format_value(0.0,"Hz")
                        elif q_v>1e-9: q_s=self._format_value(q_v); bw_s=self._format_value(f0_res/q_v,"Hz") if f0_res else "N/A"
                        else: q_s=self._format_value(q_v)+" (Baixo)"; bw_s="Muito Larga" if f0_res else "N/A"
                output_text+=f"--- Resumo Circuito Equivalente ({params['topology']}) ---\n"
                output_text+=f"  R_eq={self._format_value(r,'Ω')}, L_eq={self._format_value(l,'H')}, C_eq={self._format_value(c,'F')}\n"
                output_text+=f"  Ativos: R={'S' if self.include_r_var.get()and r>1e-12 else 'N'}, L={'S' if self.include_l_var.get()and l>1e-12 else 'N'}, C={'S' if self.include_c_var.get()and c>1e-12 else 'N'}\n"
                output_text+=f"  f0 Teórica: {f0_s}\n  Q Teórico: {q_s}\n  BW Teórica: {bw_s}\n-------------------------------------------\n\n"
                
                analysis_details_text = self._generate_analysis_details_text(self.analysis_results)
                output_text += analysis_details_text
                self.analysis_performed_successfully=True

                self._update_static_circuit_diagram(self.analysis_results)
                self._update_phasor_diagram(self.analysis_results) # Chama diretamente o diagrama fasorial
            else: 
                output_text+="Nenhuma frequência de análise válida foi fornecida.\n"
                self._clear_main_plot(error_message="Frequência inválida.")
                self._clear_static_circuit_diagram(error_message="Frequência inválida.")
            self.results_text.insert("1.0",output_text)
        except Exception as e:
            self.results_text.delete("1.0","end"); error_msg=f"Erro inesperado na análise: {str(e)}"; 
            messagebox.showerror("Erro Inesperado",error_msg); self.results_text.insert("1.0",error_msg)
            self._clear_main_plot(error_message="Erro na análise.")
            self._clear_static_circuit_diagram(error_message="Erro na análise.")
            import traceback; traceback.print_exc()
        finally: 
            self.progress_bar.stop();self.progress_bar.pack_forget();self.progress_bar_frame.pack_forget(); 
            self.results_text.configure(state="disabled")

    def _generate_analysis_details_text(self, results):
        if not results: return "Nenhum resultado para exibir."
        output = ""; topo=results.get('topology','N/A'); freq=results.get('freq','N/A')
        output+=f"--- Análise Detalhada para Frequência: {self._format_value(freq,'Hz')} ({topo}) ---\n"
        output+=f"  Fonte: {self.format_phasor(results.get('v_source_phasor',0j),'V')}\n  Z_total: {self.format_phasor(results.get('z_total_phasor',0j),'Ω')}\n  I_total Fonte: {self.format_phasor(results.get('i_total_phasor',0j),'A')}\n"
        output+="  ---------------------------\n  Tensões nos Componentes Equivalentes:\n"
        output+=f"    V_R_eq: {self.format_phasor(results.get('v_r_phasor',0j),'V') if results.get('r_val',0)>1e-12 or (topo=='Paralelo'and results.get('r_val',0)==0) else 'N/A'}\n"
        output+=f"    V_L_eq: {self.format_phasor(results.get('v_l_phasor',0j),'V') if results.get('l_val',0)>1e-12 else 'N/A'}\n"
        output+=f"    V_C_eq: {self.format_phasor(results.get('v_c_phasor',0j),'V') if results.get('c_val',0)>1e-12 else 'N/A'}\n"
        output+="  ---------------------------\n  Correntes nos Componentes Equivalentes:\n"
        output+=f"    I_R_eq: {self.format_phasor(results.get('i_r_phasor',0j),'A') if results.get('r_val',0)>1e-12 or (topo=='Paralelo'and results.get('r_val',0)==0) else 'N/A'}\n"
        output+=f"    I_L_eq: {self.format_phasor(results.get('i_l_phasor',0j),'A') if results.get('l_val',0)>1e-12 else 'N/A'}\n"
        output+=f"    I_C_eq: {self.format_phasor(results.get('i_c_phasor',0j),'A') if results.get('c_val',0)>1e-12 else 'N/A'}\n"
        fp_val=results.get('fp_total',0.0); q_total_val=results.get('q_total',0.0); s_total_val=results.get('s_total_apparent',0.0)
        fp_type=" (unitário)" if abs(q_total_val)<1e-9 else (" (atrasado - indutivo)" if q_total_val>0 else " (adiantado - capacitivo)")
        if abs(s_total_val)<1e-9: fp_type=" (N/A - sem potência)"
        output+="  ---------------------------\n  Análise de Potência (Total da Fonte):\n"
        output+=f"    |S|: {self._format_value(s_total_val,'VA')}\n    P: {self._format_value(results.get('p_total',0.0),'W')}\n    Q: {self._format_value(q_total_val,'VAR')}\n    FP: {self._format_value(fp_val)}{fp_type}\n"
        output+="  ---------------------------\n  Potências nos Componentes Equivalentes:\n"
        output+=f"    P_R_eq: {self._format_value(results.get('p_r_comp',0.0),'W') if results.get('r_val',0)>1e-12 or (topo=='Paralelo'and results.get('r_val',0)==0) else 'N/A'}\n"
        output+=f"    Q_L_eq: {self._format_value(results.get('q_l_comp',0.0),'VAR') if results.get('l_val',0)>1e-12 else 'N/A'}\n"
        output+=f"    Q_C_eq: {self._format_value(results.get('q_c_comp',0.0),'VAR') if results.get('c_val',0)>1e-12 else 'N/A'}\n"
        pr_comp,p_total_val,r_val=results.get('p_r_comp',0.0),results.get('p_total',0.0),results.get('r_val',0.0)
        if r_val>1e-12 and not any(map(math.isinf,(pr_comp,p_total_val))) and not any(map(math.isnan,(pr_comp,p_total_val))):
            if abs(p_total_val)>1e-6 or abs(pr_comp)>1e-6: output+=f"    (Verif. P_R_eq ≈ P_total: {'Sim' if math.isclose(pr_comp,p_total_val,rel_tol=1e-2,abs_tol=1e-3) else 'Não'})\n"
        ql_comp,qc_comp,q_sum_comp_valid,q_sum_comp=results.get('q_l_comp',0.0),results.get('q_c_comp',0.0),True,0
        if results.get('l_val',0)>1e-12:
            if math.isinf(ql_comp) or math.isnan(ql_comp): q_sum_comp_valid=False
            else: q_sum_comp+=ql_comp
        if results.get('c_val',0)>1e-12:
            if math.isinf(qc_comp) or math.isnan(qc_comp): q_sum_comp_valid=False
            else: q_sum_comp+=qc_comp
        if q_sum_comp_valid and not (math.isinf(q_total_val) or math.isnan(q_total_val)):
            if abs(q_total_val)>1e-6 or abs(q_sum_comp)>1e-6:
                abs_tol_q=max(1e-3,abs(ql_comp)*1e-2 if results.get('l_val',0)>1e-12 and not math.isinf(ql_comp) else 0, abs(qc_comp)*1e-2 if results.get('c_val',0)>1e-12 and not math.isinf(qc_comp) else 0)
                output+=f"    (Verif. Q_L_eq+Q_C_eq ≈ Q_total: {'Sim' if math.isclose(q_sum_comp,q_total_val,rel_tol=1e-2,abs_tol=abs_tol_q) else 'Não'})\n"
        return output

    def _calculate_and_display_pf_correction(self):
        self._clear_all_entry_error_styles(); self._set_entry_error_style('fp_desired',is_error=False)
        if not self.analysis_performed_successfully: messagebox.showerror("Correção FP","Execute uma análise de circuito bem-sucedida primeiro."); return
        fp_desired_str=self.fp_desired_entry.get()
        if not fp_desired_str: messagebox.showerror("Entrada Inválida","Insira o Fator de Potência Desejado."); self._set_entry_error_style('fp_desired',True); return
        try:
            fp_desired=float(fp_desired_str)
            if not (0.01<=fp_desired<=1.0): messagebox.showerror("Entrada Inválida","FP Desejado deve estar entre 0.01 e 1.0."); self._set_entry_error_style('fp_desired',True); return
        except ValueError: messagebox.showerror("Entrada Inválida","FP Desejado deve ser um número."); self._set_entry_error_style('fp_desired',True); return
        
        P_atual = self.analysis_results.get('p_total')
        Q_atual = self.analysis_results.get('q_total')
        FP_atual = self.analysis_results.get('fp_total')
        v_source_phasor_for_pf = self.analysis_results.get('v_source_phasor')
        V_carga = abs(v_source_phasor_for_pf) if v_source_phasor_for_pf else 0
        freq = self.analysis_results.get('freq')

        if any(v is None for v in [P_atual,Q_atual,FP_atual,V_carga,freq]): messagebox.showerror("Correção FP","Dados da análise anterior incompletos."); return
        if abs(V_carga)<1e-6 or abs(freq)<1e-6: messagebox.showerror("Cálculo Impossível","Tensão da carga ou frequência próxima de zero."); return
        
        if Q_atual > 1e-9: 
            if fp_desired <= FP_atual + 1e-4 and fp_desired < 0.99999: 
                messagebox.showinfo("Correção FP",f"FP desejado ({fp_desired:.3f}) não é melhoria significativa sobre o FP atual ({FP_atual:.3f}) para carga indutiva, ou é menor.\nNenhuma correção com capacitor será calculada.")
                return
        elif Q_atual < -1e-9: 
            messagebox.showinfo("Correção FP",f"Circuito já é capacitivo (Q={self._format_value(Q_atual,'VAR')}).\nCorreção com capacitor adicional não é aplicável para melhorar o FP em direção a 1.")
            return
        else: 
            messagebox.showinfo("Correção FP",f"Circuito já possui FP próximo de 1 (Q ≈ 0).\nNenhuma correção com capacitor é necessária para FP={fp_desired:.3f}.")
            return
        
        try: fp_desired_clamped=max(0.01,min(1.0,fp_desired)); phi_desejado_rad=math.acos(fp_desired_clamped)
        except ValueError: messagebox.showerror("Erro Cálculo","Valor inválido para acos(FP desejado)."); return
        
        Q_desejada=P_atual*math.tan(phi_desejado_rad); Q_capacitor_necessaria=Q_atual-Q_desejada
        cap_val=0.0; S_nova=self.analysis_results.get('s_total_apparent',0.0); Q_nova_final=Q_atual

        if Q_capacitor_necessaria > 1e-9: 
            omega=2*math.pi*freq
            try: cap_val=Q_capacitor_necessaria/(V_carga**2*omega)
            except ZeroDivisionError: messagebox.showerror("Erro Cálculo","Divisão por zero ao calcular capacitor."); return
            Q_nova_final=Q_desejada; S_nova=P_atual/fp_desired_clamped if abs(fp_desired_clamped)>1e-9 else math.sqrt(P_atual**2+Q_nova_final**2)
            results_txt=f"\n\n--- Resultados da Correção de Fator de Potência ---\n  FP Atual: {self._format_value(FP_atual)} (P={self._format_value(P_atual,'W')}, Q={self._format_value(Q_atual,'VAR')})\n"
            results_txt+=f"  FP Desejado: {self._format_value(fp_desired)}\n  Capacitor (paralelo): {self._format_value(cap_val,'F')}\n"
            results_txt+=f"    (Equiv. a {self._format_value(cap_val*1e3,'mF')} ou {self._format_value(cap_val*1e6,'µF')} ou {self._format_value(cap_val*1e9,'nF')})\n"
            results_txt+=f"  Qc Fornecida: {self._format_value(Q_capacitor_necessaria,'VAR')} (capacitivos)\n  Q_nova Estimada (carga+capacitor): {self._format_value(Q_nova_final,'VAR')}\n  S_nova Estimada (carga+capacitor): {self._format_value(S_nova,'VA')}\n"
        else:
            results_txt=f"\n\n--- Correção de Fator de Potência ---\n  FP Atual: {self._format_value(FP_atual)}\n  FP Desejado: {self._format_value(fp_desired)}\n"
            results_txt+=f"  Nenhuma correção com capacitor é necessária ou o FP desejado não representa uma melhoria por este método.\n  (Q a compensar pelo capacitor: {self._format_value(Q_capacitor_necessaria,'VAR')})\n"
        self.results_text.configure(state="normal"); self.results_text.insert(tk.END,results_txt); self.results_text.configure(state="disabled")

    def _clear_main_plot(self, initial_message=None, error_message=None):
        if self.ax_main_plot:
            self.ax_main_plot.set_visible(True) # Garantir que o eixo principal esteja visível
            self.ax_main_plot.clear()
            
            if self.ax_main_plot_twin and self.ax_main_plot_twin.figure: 
                try:
                    self.fig_main_plot.delaxes(self.ax_main_plot_twin)
                except (AttributeError, ValueError, KeyError): 
                    # Se delaxes falhar, tente limpar e esconder
                    try:
                        self.ax_main_plot_twin.clear()
                        self.ax_main_plot_twin.set_visible(False)
                    except: pass # Ignorar erros na limpeza secundária
                self.ax_main_plot_twin = None 

            # DEBUG: Cor de fundo para o placeholder
            self.ax_main_plot.set_facecolor('lightgrey') 
            self.fig_main_plot.patch.set_facecolor('lightyellow')

            title = "Diagrama Fasorial"; message = initial_message or "Aguardando análise..."; color = 'gray'
            if error_message: message = error_message; title = "Erro no Gráfico"; color = 'red'
            
            self.ax_main_plot.text(0.5, 0.5, message, ha='center', va='center', fontsize=9, color=color, wrap=True)
            self.ax_main_plot.set_title(title, fontsize=10)
            
            self.ax_main_plot.set_xlabel("")
            self.ax_main_plot.set_ylabel("")
            self.ax_main_plot.set_xticks([])
            self.ax_main_plot.set_yticks([])
            self.ax_main_plot.grid(False) 

            try: 
                self.fig_main_plot.tight_layout() 
            except Exception as e:
                print(f"[DEBUG] _clear_main_plot tight_layout error: {e}")

            # self.canvas_main_plot.draw() # REMOVIDO: Deixar a função de plotagem principal chamar draw()
            print(f"[DEBUG] _clear_main_plot executado (sem draw). Mensagem: {message if message else 'Nenhuma'}")


    def _clear_static_circuit_diagram(self, initial_message=None, error_message=None):
        if not self.circuit_diagram_canvas:
            return
        self.circuit_diagram_canvas.delete("all")
        
        # Tenta obter a cor de fundo do CTkFrame para o canvas
        bg_color = self._get_ctk_bg_color()
        self.circuit_diagram_canvas.configure(bg=bg_color)

        # Tenta obter a cor do texto do CTkLabel
        text_color = self._get_ctk_text_color()
        
        canvas_width = self.circuit_diagram_canvas.winfo_width()
        canvas_height = self.circuit_diagram_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1: # Canvas pode não ter sido desenhado ainda
            canvas_width = 300 # Estimativa
            canvas_height = 100 # Estimativa

        message = initial_message or "Aguardando análise..."
        fill_color = "red" if error_message else text_color
        if error_message: message = error_message

        self.circuit_diagram_canvas.create_text(
            canvas_width / 2, canvas_height / 2,
            text=message, font=("Arial", 10), fill=fill_color, anchor="center"
        )
        print(f"[DEBUG] _clear_static_circuit_diagram executado. Mensagem: {message}")

    def _update_static_circuit_diagram(self, analysis_data):
        if not self.circuit_diagram_canvas:
            print("[DEBUG] Canvas do diagrama de circuito não existe.")
            if hasattr(self, '_clear_static_circuit_diagram'):
                 self._clear_static_circuit_diagram(error_message="Canvas não inicializado.")
            return
        if not analysis_data:
            self._clear_static_circuit_diagram(error_message="Dados de análise ausentes.")
            return

        self.circuit_diagram_canvas.delete("all")
        bg_color = self._get_ctk_bg_color()
        line_color = self._get_ctk_text_color()
        self.circuit_diagram_canvas.configure(bg=bg_color)

        topology = analysis_data.get('topology', "Série")
        r_val_data = analysis_data.get('r_val', 0)
        l_val_data = analysis_data.get('l_val', 0)
        c_val_data = analysis_data.get('c_val', 0)

        r_active = self.include_r_var.get() and r_val_data > 1e-9
        l_active = self.include_l_var.get() and l_val_data > 1e-9
        c_active = self.include_c_var.get() and c_val_data > 1e-9

        active_components = []
        if r_active: active_components.append('R')
        if l_active: active_components.append('L')
        if c_active: active_components.append('C')

        if not active_components and not analysis_data.get('v_source_phasor'):
            self._clear_static_circuit_diagram(initial_message="Nenhum componente ativo para desenhar.")
            return

        canvas = self.circuit_diagram_canvas
        # Ensure canvas dimensions are available
        canvas.update_idletasks() 
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        
        if cw <= 1: cw = 400  # Fallback width
        if ch <= 1: ch = 150  # Fallback height

        padding = 20
        comp_width, comp_height = 40, 40  # Base width for R, L; height reference
        plate_gap_c = 5 # Actual width of capacitor symbol
        source_radius = 15
        y_center = ch / 2
        x_start_source = padding + source_radius # Center of the source symbol

        # Desenhar Fonte AC
        canvas.create_oval(x_start_source - source_radius, y_center - source_radius,
                           x_start_source + source_radius, y_center + source_radius, outline=line_color, width=2)
        # Simple sine wave inside source
        canvas.create_line(x_start_source - source_radius * 0.6, y_center,
                           x_start_source - source_radius * 0.2, y_center - source_radius * 0.5,
                           x_start_source + source_radius * 0.2, y_center + source_radius * 0.5,
                           x_start_source + source_radius * 0.6, y_center,
                           fill=line_color, width=1.5, smooth=True)
        canvas.create_text(x_start_source, y_center + source_radius + 12, text="Vs", fill=line_color, font=("Arial", 9))

        current_x = x_start_source + source_radius # Point where wire leaves the source

        if topology == "Série":
            # Initial wire from source
            canvas.create_line(current_x, y_center, current_x + padding / 2, y_center, fill=line_color, width=1.5)
            current_x += padding / 2

            for comp_type in active_components:
                # Fio antes do componente
                canvas.create_line(current_x, y_center, current_x + padding / 2, y_center, fill=line_color, width=1.5)
                current_x += padding / 2
                
                comp_draw_start_x = current_x

                if comp_type == 'R':
                    canvas.create_rectangle(comp_draw_start_x, y_center - comp_height / 3, comp_draw_start_x + comp_width, y_center + comp_height / 3, outline=line_color, width=2)
                    r_val_str = self._format_value(r_val_data, "Ω")
                    canvas.create_text(comp_draw_start_x + comp_width / 2, y_center + comp_height / 3 + 12, text=f"R\n{r_val_str}", fill=line_color, font=("Arial", 8), justify=tk.CENTER)
                    current_x += comp_width
                elif comp_type == 'L': # Bobina simples (3 arcos)
                    arc_r = comp_height / 4
                    canvas.create_arc(comp_draw_start_x, y_center - arc_r, comp_draw_start_x + comp_width / 3, y_center + arc_r, start=90, extent=180, style=tk.ARC, outline=line_color, width=2)
                    canvas.create_arc(comp_draw_start_x + comp_width / 3, y_center - arc_r, comp_draw_start_x + 2 * comp_width / 3, y_center + arc_r, start=90, extent=180, style=tk.ARC, outline=line_color, width=2)
                    canvas.create_arc(comp_draw_start_x + 2 * comp_width / 3, y_center - arc_r, comp_draw_start_x + comp_width, y_center + arc_r, start=90, extent=180, style=tk.ARC, outline=line_color, width=2)
                    l_val_str = self._format_value(l_val_data, "H")
                    canvas.create_text(comp_draw_start_x + comp_width / 2, y_center + arc_r + 12, text=f"L\n{l_val_str}", fill=line_color, font=("Arial", 8), justify=tk.CENTER)
                    current_x += comp_width
                elif comp_type == 'C':
                    canvas.create_line(comp_draw_start_x, y_center - comp_height / 2, comp_draw_start_x, y_center + comp_height / 2, fill=line_color, width=2)
                    canvas.create_line(comp_draw_start_x + plate_gap_c, y_center - comp_height / 2, comp_draw_start_x + plate_gap_c, y_center + comp_height / 2, fill=line_color, width=2)
                    c_val_str = self._format_value(c_val_data, "F")
                    canvas.create_text(comp_draw_start_x + plate_gap_c / 2, y_center + comp_height / 2 + 12, text=f"C\n{c_val_str}", fill=line_color, font=("Arial", 8), justify=tk.CENTER)
                    current_x += plate_gap_c
                
                # Fio depois do componente
                canvas.create_line(current_x, y_center, current_x + padding / 2, y_center, fill=line_color, width=1.5)
                current_x += padding / 2
            
            # Return wire to the source
            if active_components: # Only draw return if there were components
                return_wire_y_top = padding
                canvas.create_line(current_x, y_center, current_x, return_wire_y_top, fill=line_color, width=1.5)  # Up
                canvas.create_line(current_x, return_wire_y_top, padding, return_wire_y_top, fill=line_color, width=1.5)  # Left
                canvas.create_line(padding, return_wire_y_top, padding, y_center, fill=line_color, width=1.5)  # Down to source start
            else: # Direct connection back if no components (e.g. source only)
                 canvas.create_line(current_x, y_center, current_x, y_center - (ch/2 - padding), fill=line_color, width=1.5) 
                 canvas.create_line(current_x, y_center - (ch/2 - padding), padding, y_center - (ch/2 - padding), fill=line_color, width=1.5) 
                 canvas.create_line(padding, y_center - (ch/2 - padding), padding, y_center, fill=line_color, width=1.5)


        elif topology == "Paralelo":
            num_branches = len(active_components)
            branch_spacing = (ch - 2 * padding) / (num_branches + 1) if num_branches > 0 else ch / 2

            x_input_bar = current_x + padding # X-coordinate of the input vertical bar
            x_output_bar = x_input_bar + comp_width + padding # X for output bar (comp_width is a general space for components)

            # Wire from source to input bar
            canvas.create_line(current_x, y_center, x_input_bar, y_center, fill=line_color, width=1.5)

            if num_branches > 0:
                # Input and Output vertical bars
                canvas.create_line(x_input_bar, padding, x_input_bar, ch - padding, fill=line_color, width=1.5)
                canvas.create_line(x_output_bar, padding, x_output_bar, ch - padding, fill=line_color, width=1.5)

                for i, comp_type in enumerate(active_components):
                    y_branch = padding + (i + 1) * branch_spacing
                    
                    # Start of component symbol on the branch
                    x_comp_symbol_start = x_input_bar + padding / 2 

                    # Wire from input bar to component
                    canvas.create_line(x_input_bar, y_branch, x_comp_symbol_start, y_branch, fill=line_color, width=1.5)
                    
                    actual_width_drawn = 0
                    if comp_type == 'R':
                        canvas.create_rectangle(x_comp_symbol_start, y_branch - comp_height / 4, x_comp_symbol_start + comp_width, y_branch + comp_height / 4, outline=line_color, width=2)
                        r_val_str = self._format_value(r_val_data, "Ω")
                        canvas.create_text(x_comp_symbol_start + comp_width / 2, y_branch + comp_height / 4 + 12, text=f"R\n{r_val_str}", fill=line_color, font=("Arial", 8), justify=tk.CENTER)
                        actual_width_drawn = comp_width
                    elif comp_type == 'L':
                        arc_r_p = comp_height / 5 
                        canvas.create_arc(x_comp_symbol_start, y_branch - arc_r_p, x_comp_symbol_start + comp_width / 3, y_branch + arc_r_p, start=90, extent=180, style=tk.ARC, outline=line_color, width=2)
                        canvas.create_arc(x_comp_symbol_start + comp_width / 3, y_branch - arc_r_p, x_comp_symbol_start + 2 * comp_width / 3, y_branch + arc_r_p, start=90, extent=180, style=tk.ARC, outline=line_color, width=2)
                        canvas.create_arc(x_comp_symbol_start + 2 * comp_width / 3, y_branch - arc_r_p, x_comp_symbol_start + comp_width, y_branch + arc_r_p, start=90, extent=180, style=tk.ARC, outline=line_color, width=2)
                        l_val_str = self._format_value(l_val_data, "H")
                        canvas.create_text(x_comp_symbol_start + comp_width / 2, y_branch + arc_r_p + 12, text=f"L\n{l_val_str}", fill=line_color, font=("Arial", 8), justify=tk.CENTER)
                        actual_width_drawn = comp_width
                    elif comp_type == 'C':
                        canvas.create_line(x_comp_symbol_start, y_branch - comp_height / 3, x_comp_symbol_start, y_branch + comp_height / 3, fill=line_color, width=2)
                        canvas.create_line(x_comp_symbol_start + plate_gap_c, y_branch - comp_height / 3, x_comp_symbol_start + plate_gap_c, y_branch + comp_height / 3, fill=line_color, width=2)
                        c_val_str = self._format_value(c_val_data, "F")
                        canvas.create_text(x_comp_symbol_start + plate_gap_c / 2, y_branch + comp_height / 3 + 12, text=f"C\n{c_val_str}", fill=line_color, font=("Arial", 8), justify=tk.CENTER)
                        actual_width_drawn = plate_gap_c
                    
                    # Wire from component to output bar
                    canvas.create_line(x_comp_symbol_start + actual_width_drawn, y_branch, x_output_bar, y_branch, fill=line_color, width=1.5)

                # Wire from output bar back to source
                x_return_path_start = x_output_bar + padding / 2
                canvas.create_line(x_output_bar, y_center, x_return_path_start, y_center, fill=line_color, width=1.5) # Right from output bar
                return_wire_y_top = padding
                canvas.create_line(x_return_path_start, y_center, x_return_path_start, return_wire_y_top, fill=line_color, width=1.5) # Up
                canvas.create_line(x_return_path_start, return_wire_y_top, padding, return_wire_y_top, fill=line_color, width=1.5) # Left
                canvas.create_line(padding, return_wire_y_top, padding, y_center, fill=line_color, width=1.5) # Down to source start
            else: # No components, direct connection for parallel
                canvas.create_line(x_input_bar, y_center, x_input_bar, y_center - (ch/2 - padding), fill=line_color, width=1.5) 
                canvas.create_line(x_input_bar, y_center - (ch/2 - padding), padding, y_center - (ch/2 - padding), fill=line_color, width=1.5) 
                canvas.create_line(padding, y_center - (ch/2 - padding), padding, y_center, fill=line_color, width=1.5)

        print("[DEBUG] _update_static_circuit_diagram executado (com valores).")

    def _update_phasor_diagram(self, analysis_data):
        if not self.ax_main_plot or not analysis_data or not self.analysis_performed_successfully:
            self._clear_main_plot(error_message="Dados insuficientes para fasores.")
            return
        
        print("\n[DEBUG] Entrando em _update_phasor_diagram")
        self.ax_main_plot.clear()
        self.ax_main_plot.set_facecolor('white') # Resetar cor de fundo
        self.fig_main_plot.patch.set_facecolor('white') # Resetar cor de fundo da figura

        if self.ax_main_plot_twin and self.ax_main_plot_twin.figure:
            self.ax_main_plot_twin.set_visible(False)

        current_topology = analysis_data.get('topology')

        phasors_to_plot = {
            # Tensões nos componentes equivalentes
            "$V_R$": analysis_data.get('v_r_phasor') if self.include_r_var.get() and analysis_data.get('r_val',0)>1e-12 else None,
            "$V_L$": analysis_data.get('v_l_phasor') if self.include_l_var.get() and analysis_data.get('l_val',0)>1e-12 else None,
            "$V_C$": analysis_data.get('v_c_phasor') if self.include_c_var.get() and analysis_data.get('c_val',0)>1e-12 else None,
            # Tensão da Fonte
            "$V_S$ (Fonte)": analysis_data.get('v_source_phasor'),
            # Corrente Total
            "$I_T$ (Total)": analysis_data.get('i_total_phasor'),
        }

        # Adicionar correntes de ramo para topologia Paralelo
        if current_topology == "Paralelo":
            if self.include_r_var.get() and analysis_data.get('r_val',0) > 1e-12:
                phasors_to_plot["$I_R$"] = analysis_data.get('i_r_phasor') # Legenda simplificada
            if self.include_l_var.get() and analysis_data.get('l_val',0) > 1e-12:
                phasors_to_plot["$I_L$"] = analysis_data.get('i_l_phasor') # Legenda simplificada
            if self.include_c_var.get() and analysis_data.get('c_val',0) > 1e-12:
                phasors_to_plot["$I_C$"] = analysis_data.get('i_c_phasor') # Legenda simplificada

        # Definir cores e estilos
        # Usaremos um esquema de cores base e modificaremos o estilo para correntes de ramo
        base_colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkcyan', 'magenta', 'saddlebrown', 'olive', 'darkslateblue']
        max_val=0; plotted_arrows=[]; plotted_labels=[]

        for i,(label,phasor) in enumerate(phasors_to_plot.items()):
            if phasor is not None and abs(phasor)>1e-9:
                x,y=phasor.real,phasor.imag; mag_ph=abs(phasor)
                hw=0.04*mag_ph if mag_ph>1e-9 else 0.01; hl=0.08*mag_ph if mag_ph>1e-9 else 0.02 # Ajustado para setas um pouco menores
                if hw == 0: hw = 0.01
                if hl == 0: hl = 0.02

                color = base_colors[i % len(base_colors)]
                linestyle = '-' # Padrão
                linewidth = 1.5

                # Distinguir correntes de ramo (I_R, I_L, I_C) - não I_T
                if label in ["$I_R$", "$I_L$", "$I_C$"]:
                    linestyle = '--' # Tracejado para correntes de ramo
                    linewidth = 1.2
                    # Para garantir cores diferentes para I_R, I_L, I_C mesmo se V_R, V_L, V_C não forem plotados,
                    # podemos ajustar o índice de cor ou ter um conjunto de cores separado para correntes.
                    # Por simplicidade, o esquema atual de cores sequenciais é mantido.
                # Para I_T, podemos dar um destaque
                if label == "$I_T$ (Total)":
                    linewidth = 2.0

                arrow=self.ax_main_plot.arrow(0,0,x,y,head_width=hw,head_length=hl,
                                              fc=color, ec=color, 
                                              linestyle=linestyle, linewidth=linewidth,
                                              length_includes_head=True,zorder=i+5)
                plotted_arrows.append(arrow); plotted_labels.append(f"{label}: {self.format_phasor(phasor)}"); max_val=max(max_val,abs(x),abs(y),mag_ph)
        
        if not plotted_arrows: # Se nenhum fasor foi plotado
            print("[DEBUG] Nenhum fasor significativo para plotar.")
            self._clear_main_plot(initial_message="Nenhum fasor significativo para exibir.")
            return

        if max_val==0:max_val=1 
        limit=max_val*1.2; self.ax_main_plot.set_xlim(-limit,limit); self.ax_main_plot.set_ylim(-limit,limit)
        self.ax_main_plot.set_xlabel("Componente Real"); self.ax_main_plot.set_ylabel("Componente Imaginário"); self.ax_main_plot.set_title("Diagrama Fasorial")
        self.ax_main_plot.axhline(0,color='black',lw=0.5); self.ax_main_plot.axvline(0,color='black',lw=0.5); self.ax_main_plot.grid(True,ls=':',alpha=0.7); self.ax_main_plot.set_aspect('equal',adjustable='box')
        self.ax_main_plot.legend(plotted_arrows,plotted_labels,loc='best',fontsize='x-small')
        try: self.fig_main_plot.tight_layout()
        except RuntimeError: # Pode acontecer se o layout estiver muito restrito
            print(f"[DEBUG] _update_phasor_diagram tight_layout error (RuntimeError).")
        except Exception as e: print(f"[DEBUG] _update_phasor_diagram tight_layout error: {e}")
        self.canvas_main_plot.draw()
        print("[DEBUG] Diagrama fasorial desenhado.")

    def format_phasor(self, complex_val, unit=""):
        if not isinstance(complex_val, complex) or cmath.isinf(complex_val) or cmath.isnan(complex_val): return self._format_value(complex_val, unit)
        mag=abs(complex_val); phase_rad=cmath.phase(complex_val)
        if mag<1e-12: phase_rad=0.0
        mag_fmt=self._format_value(mag)
        phase_disp=math.degrees(phase_rad) if self.angle_unit.get()=="degrees" else phase_rad
        angle_sym="°" if self.angle_unit.get()=="degrees" else " rad"
        if abs(phase_disp)<1e-9: phase_disp=0.0
        phase_fmt=self._format_value(phase_disp)
        return f"{mag_fmt} {unit} ∠ {phase_fmt}{angle_sym}"

if __name__ == '__main__':
    root = ctk.CTk()
    app = ACCircuitAnalyzerApp(root)
    root.mainloop()