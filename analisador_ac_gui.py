import customtkinter as ctk # Importa customtkinter como ctk
import tkinter as tk # Ainda precisamos para tk.StringVar e messagebox
from tkinter import messagebox # Mantemos o messagebox padrão por enquanto
import cmath
import math
import numpy as np # Importa numpy

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ACCircuitAnalyzerApp:
    def __init__(self, master_window):
        self.master = master_window
        master_window.title("Analisador de Circuito CA Série RLC (CustomTkinter)")
        master_window.geometry("800x1000") # Aumentado para o gráfico

        ctk.set_appearance_mode("System")  # Pode ser "System", "Light", "Dark"
        ctk.set_default_color_theme("blue")  # Temas: "blue", "green", "dark-blue"

        self.angle_unit = tk.StringVar(value="degrees") # tk.StringVar ainda é usado

        self.sweep_enabled_var = tk.BooleanVar(value=False) # Para o CTkSwitch
        self.plot_variable_options = ["|Z_total|", "|I_total|", "|V_R|", "|V_L|", "|V_C|",
                                      "Fase(Z_total) (°)", "Fase(I_total) (°)",
                                      "Fase(V_R) (°)", "Fase(V_L) (°)", "Fase(V_C) (°)"]
        self.plot_variable_selected = tk.StringVar(value=self.plot_variable_options[0])


        # Frame principal
        main_frame = ctk.CTkFrame(master_window, corner_radius=10)
        main_frame.pack(expand=True, fill="both", padx=15, pady=15)

        # Título dentro da janela
        title_label = ctk.CTkLabel(main_frame, text="Análise de Circuito CA Série RLC",
                                   font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(10, 20)) # Reduzi um pouco o pady inferior

        # --- Seção de Entradas ---
        input_section_label = ctk.CTkLabel(main_frame, text="Parâmetros do Circuito e da Fonte",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        input_section_label.pack(pady=(0,5), anchor="w", padx=10)

        input_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        input_frame.pack(fill="x", padx=10, pady=(0,10))
        input_frame.grid_columnconfigure(1, weight=1)

        # Componentes
        entry_width = 200 # Largura padrão para entradas CTk
        
        ctk.CTkLabel(input_frame, text="Resistor (R) [Ω]:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.r_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 100")
        self.r_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.r_entry.insert(0, "100")

        ctk.CTkLabel(input_frame, text="Indutor (L) [H]:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.l_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0.1")
        self.l_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.l_entry.insert(0, "0.1")

        ctk.CTkLabel(input_frame, text="Capacitor (C) [F]:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.c_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0.00001")
        self.c_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        self.c_entry.insert(0, "0.00001")

        # Fonte de Tensão CA
        ctk.CTkLabel(input_frame, text="Tensão Fonte (Vmag) [V]:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.v_mag_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 10")
        self.v_mag_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")
        self.v_mag_entry.insert(0, "10")

        ctk.CTkLabel(input_frame, text="Fase Fonte (θv) [°]:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.v_phase_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0")
        self.v_phase_entry.grid(row=4, column=1, padx=10, pady=8, sticky="ew")
        self.v_phase_entry.insert(0, "0")

        ctk.CTkLabel(input_frame, text="Frequência Única (f) [Hz]:").grid(row=5, column=0, padx=10, pady=8, sticky="w") # Label alterada
        self.freq_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 60")
        self.freq_entry.grid(row=5, column=1, padx=10, pady=8, sticky="ew")
        self.freq_entry.insert(0, "60")

        # --- Seção de Opções de Saída ---
        output_options_label = ctk.CTkLabel(main_frame, text="Opções de Saída",
                                            font=ctk.CTkFont(size=16, weight="bold"))
        output_options_label.pack(pady=(10,5), anchor="w", padx=10)
        
        output_options_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        output_options_frame.pack(fill="x", padx=10, pady=(0,10))

        ctk.CTkLabel(output_options_frame, text="Unidade do Ângulo (Saída):").pack(side="left", padx=(10,5), pady=10) # Label alterada
        
        degrees_radio = ctk.CTkRadioButton(output_options_frame, text="Graus (°)", variable=self.angle_unit, value="degrees")
        degrees_radio.pack(side="left", padx=5, pady=10)
        
        radians_radio = ctk.CTkRadioButton(output_options_frame, text="Radianos (rad)", variable=self.angle_unit, value="radians")
        radians_radio.pack(side="left", padx=5, pady=10)

        # --- Seção de Varredura de Frequência ---
        sweep_section_label = ctk.CTkLabel(main_frame, text="Configurações da Varredura de Frequência",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        sweep_section_label.pack(pady=(15,5), anchor="w", padx=10)

        sweep_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        sweep_frame.pack(fill="x", padx=10, pady=(0,10))
        sweep_frame.grid_columnconfigure(1, weight=1) 
        sweep_frame.grid_columnconfigure(3, weight=1) 

        self.sweep_switch = ctk.CTkSwitch(sweep_frame, text="Habilitar Varredura", variable=self.sweep_enabled_var,
                                          command=self.toggle_sweep_entries_state)
        self.sweep_switch.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(sweep_frame, text="Frequência Inicial (Hz):").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.freq_start_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1")
        self.freq_start_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.freq_start_entry.insert(0, "1")

        ctk.CTkLabel(sweep_frame, text="Frequência Final (Hz):").grid(row=1, column=2, padx=10, pady=8, sticky="w")
        self.freq_end_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 1000")
        self.freq_end_entry.grid(row=1, column=3, padx=10, pady=8, sticky="ew")
        self.freq_end_entry.insert(0, "1000")

        ctk.CTkLabel(sweep_frame, text="Número de Pontos:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.num_points_entry = ctk.CTkEntry(sweep_frame, placeholder_text="Ex: 200")
        self.num_points_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
        self.num_points_entry.insert(0, "200")
        
        ctk.CTkLabel(sweep_frame, text="Plotar Grandeza:").grid(row=2, column=2, padx=10, pady=8, sticky="w")
        self.plot_variable_combobox = ctk.CTkComboBox(sweep_frame, values=self.plot_variable_options,
                                                      variable=self.plot_variable_selected, state="readonly")
        self.plot_variable_combobox.grid(row=2, column=3, padx=10, pady=8, sticky="ew")


        # Frame para os botões de ação
        action_buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent") 
        action_buttons_frame.pack(pady=15) # Reduzi o pady

        analyze_button = ctk.CTkButton(action_buttons_frame, text="Analisar Circuito", command=self.analyze_circuit, font=ctk.CTkFont(size=14, weight="bold"))
        analyze_button.pack(side="left", padx=10)

        clear_button = ctk.CTkButton(action_buttons_frame, text="Limpar Entradas", command=self.clear_entries, fg_color="gray50", hover_color="gray30")
        clear_button.pack(side="left", padx=10)

        about_button = ctk.CTkButton(action_buttons_frame, text="Sobre", command=self.show_about_dialog_ctk, width=80)
        about_button.pack(side="left", padx=10)

        # --- Frame para o Gráfico Matplotlib ---
        plot_frame_label = ctk.CTkLabel(main_frame, text="Gráfico da Varredura",
                                        font=ctk.CTkFont(size=16, weight="bold"))
        plot_frame_label.pack(pady=(10,5), anchor="w", padx=10)
        
        self.plot_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        # Definindo uma altura mínima para o frame do gráfico e permitindo que expanda
        self.plot_frame.pack(fill="both", expand=True, padx=10, pady=(0,10), ipady=100) # ipady para altura mínima
        
        self.fig = Figure(figsize=(5, 3.5), dpi=100) 
        self.ax = self.fig.add_subplot(111)
        # clear_plot é chamado no final do __init__ através de toggle_sweep_entries_state
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        # self.canvas.draw() # Será desenhado pelo clear_plot

        # --- Seção de Saídas em Texto ---
        results_section_label_text = ctk.CTkLabel(main_frame, text="Resultados da Análise (Texto)",
                                             font=ctk.CTkFont(size=16, weight="bold"))
        results_section_label_text.pack(pady=(10,5), anchor="w", padx=10)

        self.results_text = ctk.CTkTextbox(main_frame, height=150, corner_radius=10, wrap="word", 
                                           font=ctk.CTkFont(family="monospace", size=13))
        self.results_text.pack(fill="x", padx=10, pady=(0,10)) # fill="x" para não expandir verticalmente mais que o necessário
        self.results_text.configure(state="disabled")

        note_label = ctk.CTkLabel(main_frame, text="Nota: Esta ferramenta analisa um circuito RLC série fixo.",
                                  font=ctk.CTkFont(size=12), text_color="gray50")
        note_label.pack(pady=(10,10), side="bottom") # side="bottom" para fixar na parte inferior

        self.toggle_sweep_entries_state() # Define o estado inicial dos campos de varredura e limpa o plot

    def toggle_sweep_entries_state(self):
        """
        Habilita ou desabilita os campos de entrada da varredura de frequência
        com base no estado do CTkSwitch.
        """
        if self.sweep_enabled_var.get():
            sweep_state = "normal"
            single_freq_state = "disabled"
            self.results_text.configure(state="normal")
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", "Modo de varredura habilitado. Configure e clique em Analisar.")
            self.results_text.configure(state="disabled")

        else:
            sweep_state = "disabled"
            single_freq_state = "normal"
            self.results_text.configure(state="normal")
            self.results_text.delete("1.0", "end") # Limpa o texto ao desabilitar varredura
            self.results_text.configure(state="disabled")
        
        self.freq_entry.configure(state=single_freq_state)
        self.freq_start_entry.configure(state=sweep_state)
        self.freq_end_entry.configure(state=sweep_state)
        self.num_points_entry.configure(state=sweep_state)
        self.plot_variable_combobox.configure(state=sweep_state)
        self.clear_plot() # Limpa o gráfico ao alternar o modo

    def clear_plot(self):
        if hasattr(self, 'ax'): # Verifica se o eixo do gráfico já existe
            self.ax.clear()
            self.ax.set_title("Aguardando Análise")
            self.ax.set_xlabel("Frequência (Hz)")
            self.ax.set_ylabel("Grandeza")
            self.ax.grid(True, which="both", linestyle="--", linewidth=0.5)
            if hasattr(self, 'fig'): self.fig.tight_layout() # Evita sobreposição de labels
            if hasattr(self, 'canvas'): self.canvas.draw()
            
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

        # self.sweep_enabled_var.set(False) # Opcional: desabilitar varredura ao limpar
        # self.toggle_sweep_entries_state() # Atualiza o estado dos campos se desabilitar

        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.configure(state="disabled")
        self.clear_plot()
    
    def show_about_dialog_ctk(self):
        if hasattr(self, "about_window") and self.about_window.winfo_exists():
            self.about_window.lift() 
            self.about_window.focus_set() 
            return

        self.about_window = ctk.CTkToplevel(self.master)
        self.about_window.title("Sobre Analisador de Circuito CA")
        self.about_window.geometry("450x300") 
        self.about_window.transient(self.master) 
        
        self.about_window.update_idletasks() 

        try: 
            self.about_window.grab_set() 
        except tk.TclError as e: 
            print(f"Aviso: Falha ao executar grab_set imediatamente: {e}. Tentando com atraso.")
            self.about_window.after(100, self.about_window.grab_set)

        about_frame = ctk.CTkFrame(self.about_window, corner_radius=10)
        about_frame.pack(expand=True, fill="both", padx=15, pady=15)

        ctk.CTkLabel(about_frame, text="Analisador de Circuito CA Série RLC", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,10))
        
        info_text = ("Versão: 1.2.0 (CustomTkinter)\n\n" # Atualizei a versão
                     "Desenvolvido como exemplo de aplicação.\n\n"
                     "Funcionalidades:\n"
                     "- Análise de circuito RLC série em CA (freq. única e varredura).\n"
                     "- Cálculo de impedâncias, correntes, tensões e potências.\n"
                     "- Plotagem de grandezas vs. frequência.") 
        ctk.CTkLabel(about_frame, text=info_text, justify="left", wraplength=380).pack(pady=10)

        close_button = ctk.CTkButton(about_frame, text="Fechar", command=self.about_window.destroy, width=100)
        close_button.pack(pady=20)
        
        # Centralizar
        self.master.update_idletasks()
        master_x = self.master.winfo_x()
        master_y = self.master.winfo_y()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()

        self.about_window.update_idletasks()
        popup_width = self.about_window.winfo_width()
        popup_height = self.about_window.winfo_height()
        
        if popup_width <= 1 or popup_height <= 1: # Fallback se as dimensões não estiverem prontas
            try:
                geom_parts = self.about_window.geometry().split('+')[0].split('x')
                popup_width, popup_height = int(geom_parts[0]), int(geom_parts[1])
            except: # Fallback se a geometria não puder ser parseada
                 popup_width = 450 
                 popup_height = 300

        center_x = master_x + (master_width - popup_width) // 2
        center_y = master_y + (master_height - popup_height) // 2
        
        self.about_window.geometry(f"{popup_width}x{popup_height}+{center_x}+{center_y}")
        self.about_window.focus_set() 

    def analyze_circuit(self):
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end") 

        if self.sweep_enabled_var.get():
            self.perform_frequency_sweep()
        else:
            self.perform_single_frequency_analysis()
        
        self.results_text.configure(state="disabled")

    def perform_single_frequency_analysis(self):
        output = ""
        try:
            r_val = float(self.r_entry.get())
            l_val = float(self.l_entry.get())
            c_val = float(self.c_entry.get())
            v_mag = float(self.v_mag_entry.get())
            v_phase_deg = float(self.v_phase_entry.get())
            freq = float(self.freq_entry.get())

            error_messages = []
            if r_val < 0: error_messages.append("Resistor (R) não pode ser negativo.")
            if l_val < 0: error_messages.append("Indutor (L) não pode ser negativo.")
            if c_val < 0: error_messages.append("Capacitor (C) não pode ser negativo.")
            if v_mag < 0: error_messages.append("Tensão da Fonte (Vmag) não pode ser negativa.")
            if freq <= 0: error_messages.append("Frequência Única (f) deve ser maior que zero.")
            if error_messages:
                messagebox.showerror("Erro de Entrada (Freq. Única)", "\n".join(error_messages))
                self.results_text.insert("1.0", "Erro na entrada para análise de frequência única.")
                return

            v_phase_rad = math.radians(v_phase_deg)
            v_source_phasor = cmath.rect(v_mag, v_phase_rad)
            z_r = complex(r_val, 0)
            z_l = complex(0, 2 * cmath.pi * freq * l_val) if l_val > 0 else complex(0,0)
            z_c = complex(0, -1 / (2 * cmath.pi * freq * c_val)) if c_val > 0 else complex(float('inf'), 0)
            z_total = z_r + z_l + z_c
            
            output = f"--- Análise em Frequência Única: {freq:.2f} Hz ---\n"
            output += f"R: {r_val} Ω, L: {l_val} H, C: {c_val} F\n"
            output += f"Fonte: {v_mag:.2f} V ∠ {v_phase_deg:.2f}°\n\n"
            output += "--- Resultados ---\n"
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
            self.clear_plot()
        except ValueError:
            messagebox.showerror("Erro de Entrada", "Valores numéricos inválidos (Freq. Única).")
            self.results_text.insert("1.0", "Erro na entrada para análise de frequência única.")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Erro (Freq. Única): {str(e)}")
            self.results_text.insert("1.0", f"Erro inesperado: {str(e)}")
            import traceback # Para debug
            traceback.print_exc() # Para debug

    def perform_frequency_sweep(self):
        output_summary = "--- Varredura de Frequência ---\n"
        try:
            freq_start = float(self.freq_start_entry.get())
            freq_end = float(self.freq_end_entry.get())
            num_points = int(self.num_points_entry.get())
            plot_choice = self.plot_variable_selected.get()
            
            # Parâmetros do circuito
            r_val = float(self.r_entry.get()); l_val = float(self.l_entry.get()); c_val = float(self.c_entry.get())
            v_mag = float(self.v_mag_entry.get()); v_phase_deg = float(self.v_phase_entry.get())
            v_phase_rad = math.radians(v_phase_deg)
            v_source_phasor_fixed = cmath.rect(v_mag, v_phase_rad)

            error_messages_sweep = []
            if r_val < 0: error_messages_sweep.append("Resistor (R) não pode ser negativo.")
            if l_val < 0: error_messages_sweep.append("Indutor (L) não pode ser negativo.")
            if c_val < 0: error_messages_sweep.append("Capacitor (C) não pode ser negativo.")
            if v_mag < 0: error_messages_sweep.append("Tensão da Fonte (Vmag) não pode ser negativa.")
            if freq_start <= 0: error_messages_sweep.append("Frequência Inicial deve ser > 0.")
            if freq_end <= freq_start: error_messages_sweep.append("Frequência Final deve ser > Frequência Inicial.")
            if num_points < 2: error_messages_sweep.append("Número de Pontos deve ser >= 2.")
            if error_messages_sweep:
                messagebox.showerror("Erro na Configuração da Varredura", "\n".join(error_messages_sweep))
                self.results_text.insert("1.0", "Erro na configuração da varredura.")
                return

            frequencies = np.linspace(freq_start, freq_end, num_points)
            plot_data_y = []
            output_summary += f"Varrendo de {freq_start:.2f} Hz a {freq_end:.2f} Hz ({num_points} pontos).\n"
            output_summary += f"Plotando: {plot_choice}\n\n"

            for freq_current in frequencies:
                z_r_sweep = complex(r_val, 0)
                z_l_sweep = complex(0, 2 * cmath.pi * freq_current * l_val) if l_val > 0 else complex(0,0)
                # Evitar divisão por zero se freq_current for zero (embora já validado > 0)
                # ou se c_val for zero (já tratado para ser infinito)
                if c_val > 0 and freq_current > 0 :
                     z_c_sweep = complex(0, -1 / (2 * cmath.pi * freq_current * c_val))
                else: # c_val = 0 ou freq_current = 0 (para o capacitor)
                     z_c_sweep = complex(float('inf'), 0)

                z_total_sweep = z_r_sweep + z_l_sweep + z_c_sweep
                current_value_to_plot = 0.0 

                i_total_sweep = v_source_phasor_fixed / z_total_sweep if abs(z_total_sweep) != float('inf') else complex(0,0)
                
                # Dicionário para mapear a escolha do ComboBox para a função lambda que calcula o valor
                val_map = {
                    "|Z_total|": lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: abs(zt),
                    "|I_total|": lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: abs(i),
                    "|V_R|":     lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: abs(i * zr),
                    "|V_L|":     lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: abs(i * zl),
                    "|V_C|":     lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: abs(vs) if abs(zc) == float('inf') else abs(i * zc),
                    "Fase(Z_total) (°)": lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: math.degrees(cmath.phase(zt)) if abs(zt) != float('inf') else 0.0,
                    "Fase(I_total) (°)": lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: math.degrees(cmath.phase(i)) if abs(i) > 1e-12 else 0.0,
                    "Fase(V_R) (°)":     lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: math.degrees(cmath.phase(i * zr)) if abs(i * zr) > 1e-12 else 0.0,
                    "Fase(V_L) (°)":     lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: math.degrees(cmath.phase(i * zl)) if abs(i * zl) > 1e-12 else 0.0,
                    "Fase(V_C) (°)":     lambda f, i, vr, vl, vc, zr, zl, zc, zt, vs: math.degrees(cmath.phase(vs if abs(zc) == float('inf') else i * zc)) \
                                                                                      if abs(vs if abs(zc) == float('inf') else i * zc) > 1e-12 else 0.0
                }
                if plot_choice in val_map:
                    # Passando os valores relevantes para a função lambda
                    current_value_to_plot = val_map[plot_choice](freq_current, i_total_sweep, 
                                                                 i_total_sweep * z_r_sweep, 
                                                                 i_total_sweep * z_l_sweep, 
                                                                 v_source_phasor_fixed if abs(z_c_sweep) == float('inf') else i_total_sweep * z_c_sweep,
                                                                 z_r_sweep, z_l_sweep, z_c_sweep, z_total_sweep, v_source_phasor_fixed)
                plot_data_y.append(current_value_to_plot)
            
            self.plot_sweep_results(frequencies, plot_data_y, plot_choice)
            output_summary += "Varredura concluída. Veja o gráfico.\n"
            self.results_text.insert("1.0", output_summary)

        except ValueError:
            messagebox.showerror("Erro na Varredura", "Valores numéricos inválidos para varredura.")
            self.results_text.insert("1.0","Erro na configuração da varredura (valores inválidos).")
        except Exception as e:
            messagebox.showerror("Erro Inesperado na Varredura", f"Ocorreu um erro: {str(e)}")
            self.results_text.insert("1.0", f"Erro inesperado na varredura: {str(e)}")
            import traceback
            traceback.print_exc()

    def plot_sweep_results(self, frequencies, plot_data_y, y_label_choice):
        self.ax.clear()
        self.ax.plot(frequencies, plot_data_y, marker='.', linestyle='-', markersize=3) # Marcadores menores
        self.ax.set_title(f"{y_label_choice} vs Frequência")
        self.ax.set_xlabel("Frequência (Hz)")
        self.ax.set_ylabel(y_label_choice)
        self.ax.grid(True, which="both", linestyle="--", linewidth=0.5)
        
        if len(frequencies) > 1 and frequencies[-1] / frequencies[0] > 50: 
             self.ax.set_xscale('log')
        else:
             self.ax.set_xscale('linear')
        
        is_magnitude_plot = "|" in y_label_choice
        is_phase_plot = "Fase" in y_label_choice

        if is_magnitude_plot and len(plot_data_y) > 1:
            # Filtrar zeros e infinitos para min_val para evitar erros com log scale
            positive_values = [d for d in plot_data_y if d > 1e-9 and d != float('inf')]
            if positive_values:
                min_val = min(positive_values) 
                max_val = max(d for d in plot_data_y if d != float('inf')) # Max desconsiderando inf
                if min_val > 0 and max_val / min_val > 1000: 
                    self.ax.set_yscale('log')
                else:
                    self.ax.set_yscale('linear')
            else: # Todos os valores são zero ou negativos
                self.ax.set_yscale('linear')
        elif not is_phase_plot : # Se não for magnitude nem fase, mas algo que pode variar muito
             self.ax.set_yscale('linear') # Default para outros casos, ou lógica específica

        self.fig.tight_layout()
        self.canvas.draw()

    def format_phasor(self, complex_val, unit=""):
        if abs(complex_val) == float('inf'):
            return f"Infinito {unit}"
        mag = abs(complex_val)
        phase_rad = cmath.phase(complex_val)
        
        # Evitar fase de um número complexo muito próximo de zero (ex: 0+0j)
        if mag < 1e-12: # Tolerância para considerar como zero
            phase_rad = 0.0

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