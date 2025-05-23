import customtkinter as ctk # Importa customtkinter como ctk
import tkinter as tk # Ainda precisamos para tk.StringVar e messagebox
from tkinter import messagebox # Mantemos o messagebox padrão por enquanto
import cmath
import math

class ACCircuitAnalyzerApp:
    def __init__(self, master_window):
        self.master = master_window
        master_window.title("Analisador de Circuito CA Série RLC (CustomTkinter)")
        master_window.geometry("650x750") 

        ctk.set_appearance_mode("System") 
        ctk.set_default_color_theme("blue")  

        self.angle_unit = tk.StringVar(value="degrees") 

        self.sweep_enabled_var = tk.BooleanVar(value=False) # Para o CTkSwitch
        self.plot_variable_options = ["|Z_total|", "|I_total|", "|V_R|", "|V_L|", "|V_C|", 
                                    "Fase(Z_total) (°)", "Fase(I_total) (°)", 
                                    "Fase(V_R) (°)", "Fase(V_L) (°)", "Fase(V_C) (°)"]
        self.plot_variable_selected = tk.StringVar(value=self.plot_variable_options[0])

        main_frame = ctk.CTkFrame(master_window, corner_radius=10)
        main_frame.pack(expand=True, fill="both", padx=15, pady=15)

        title_label = ctk.CTkLabel(main_frame, text="Análise de Circuito CA Série RLC",
                                   font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(10, 25))

        input_section_label = ctk.CTkLabel(main_frame, text="Parâmetros do Circuito e da Fonte",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        input_section_label.pack(pady=(0,5), anchor="w", padx=10)

        input_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        input_frame.pack(fill="x", padx=10, pady=(0,10))
        input_frame.grid_columnconfigure(1, weight=1)

        entry_width = 200 
        
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

        ctk.CTkLabel(input_frame, text="Tensão Fonte (Vmag) [V]:").grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.v_mag_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 10")
        self.v_mag_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")
        self.v_mag_entry.insert(0, "10")

        ctk.CTkLabel(input_frame, text="Fase Fonte (θv) [°]:").grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.v_phase_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 0")
        self.v_phase_entry.grid(row=4, column=1, padx=10, pady=8, sticky="ew")
        self.v_phase_entry.insert(0, "0")

        ctk.CTkLabel(input_frame, text="Frequência (f) [Hz]:").grid(row=5, column=0, padx=10, pady=8, sticky="w")
        self.freq_entry = ctk.CTkEntry(input_frame, width=entry_width, placeholder_text="Ex: 60")
        self.freq_entry.grid(row=5, column=1, padx=10, pady=8, sticky="ew")
        self.freq_entry.insert(0, "60")

        output_options_label = ctk.CTkLabel(main_frame, text="Opções de Saída",
                                            font=ctk.CTkFont(size=16, weight="bold"))
        output_options_label.pack(pady=(10,5), anchor="w", padx=10)
        
        output_options_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        output_options_frame.pack(fill="x", padx=10, pady=(0,10))

        ctk.CTkLabel(output_options_frame, text="Unidade do Ângulo:").pack(side="left", padx=(10,5), pady=10)
        
        degrees_radio = ctk.CTkRadioButton(output_options_frame, text="Graus (°)", variable=self.angle_unit, value="degrees")
        degrees_radio.pack(side="left", padx=5, pady=10)
        
        radians_radio = ctk.CTkRadioButton(output_options_frame, text="Radianos (rad)", variable=self.angle_unit, value="radians")
        radians_radio.pack(side="left", padx=5, pady=10)

        

        action_buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent") 
        action_buttons_frame.pack(pady=20)

        analyze_button = ctk.CTkButton(action_buttons_frame, text="Analisar Circuito", command=self.analyze_circuit, font=ctk.CTkFont(size=14, weight="bold"))
        analyze_button.pack(side="left", padx=10)

        clear_button = ctk.CTkButton(action_buttons_frame, text="Limpar Entradas", command=self.clear_entries, fg_color="gray50", hover_color="gray30")
        clear_button.pack(side="left", padx=10)

        about_button = ctk.CTkButton(action_buttons_frame, text="Sobre", command=self.show_about_dialog_ctk, width=80)
        about_button.pack(side="left", padx=10)

        results_section_label = ctk.CTkLabel(main_frame, text="Resultados da Análise",
                                             font=ctk.CTkFont(size=16, weight="bold"))
        results_section_label.pack(pady=(10,5), anchor="w", padx=10)

        self.results_text = ctk.CTkTextbox(main_frame, height=200, corner_radius=10, wrap="word", font=ctk.CTkFont(family="monospace", size=13))
        self.results_text.pack(expand=True, fill="both", padx=10, pady=(0,10))
        self.results_text.configure(state="disabled") 

        note_label = ctk.CTkLabel(main_frame, text="Nota: Esta ferramenta analisa um circuito RLC série fixo.\nUm construtor gráfico de circuitos não está implementado.",
                                  font=ctk.CTkFont(size=12), text_color="gray50")
        note_label.pack(pady=(10,10))

    def clear_entries(self):
        self.r_entry.delete(0, "end")
        self.r_entry.insert(0, "100")
        self.l_entry.delete(0, "end")
        self.l_entry.insert(0, "0.1")
        self.c_entry.delete(0, "end")
        self.c_entry.insert(0, "0.00001")
        self.v_mag_entry.delete(0, "end")
        self.v_mag_entry.insert(0, "10")
        self.v_phase_entry.delete(0, "end")
        self.v_phase_entry.insert(0, "0")
        self.freq_entry.delete(0, "end")
        self.freq_entry.insert(0, "60")

        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.configure(state="disabled")
    
    def show_about_dialog_ctk(self):
        if hasattr(self, "about_window") and self.about_window.winfo_exists():
            self.about_window.lift() 
            self.about_window.focus_set() 
            return

        self.about_window = ctk.CTkToplevel(self.master)
        self.about_window.title("Sobre Analisador de Circuito CA")
        self.about_window.geometry("450x300") # Aumentei um pouco a altura para o botão
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
        
        info_text = ("Versão: 1.1.2 (CustomTkinter)\n\n" # Atualizei a versão
                     "Desenvolvido como exemplo de aplicação.\n\n"
                     "Funcionalidades:\n"
                     "- Análise de circuito RLC série em CA.\n"
                     "- Cálculo de impedâncias, correntes, tensões e potências.") 
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
        
        if popup_width == 1 and popup_height == 1: # Janela pode não ter dimensões reais ainda
            # Estimativa baseada na geometria definida, menos decorações
            try:
                geom_parts = self.about_window.geometry().split('+')[0].split('x')
                popup_width = int(geom_parts[0])
                popup_height = int(geom_parts[1])
            except: # Fallback se a geometria não puder ser parseada
                 popup_width = 450 
                 popup_height = 300


        center_x = master_x + (master_width - popup_width) // 2
        center_y = master_y + (master_height - popup_height) // 2
        
        self.about_window.geometry(f"{popup_width}x{popup_height}+{center_x}+{center_y}")
        self.about_window.focus_set() 


    def analyze_circuit(self):
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
            if freq <= 0: error_messages.append("Frequência (f) deve ser maior que zero.")

            if error_messages:
                messagebox.showerror("Erro de Entrada", "\n".join(error_messages))
                return
            
            v_phase_rad = math.radians(v_phase_deg)
            v_source_phasor = cmath.rect(v_mag, v_phase_rad)
            z_r = complex(r_val, 0)
            z_l = complex(0, 2 * cmath.pi * freq * l_val) if l_val > 0 else complex(0,0)
            z_c = complex(0, -1 / (2 * cmath.pi * freq * c_val)) if c_val > 0 else complex(float('inf'), 0)
            z_total = z_r + z_l + z_c
            
            output = f"--- Parâmetros de Entrada ---\n"
            output += f"R: {r_val} Ω\nL: {l_val} H\nC: {c_val} F\n"
            output += f"Fonte: {v_mag:.2f} V ∠ {v_phase_deg:.2f}°\nFrequência: {freq} Hz\n\n"
            output += "--- Resultados ---\n"

            i_total_phasor = complex(0,0)

            if abs(z_total) == float('inf'):
                output += "Impedância Total (Z_total): Infinita (Circuito Aberto)\n"
                output += f"Corrente Total (I_total): {self.format_phasor(i_total_phasor, 'A')}\n"
                v_r_phasor, v_l_phasor = complex(0,0), complex(0,0)
                v_c_phasor = v_source_phasor
                output += f"Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                output += f"Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                output += f"Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                
                output += "---------------------------\n"
                output += "Análise de Potência (Total):\n"
                output += "  Potência Aparente (|S|): 0.000 VA\n"
                output += "  Potência Ativa (P): 0.000 W\n"
                output += "  Potência Reativa (Q): 0.000 VAR\n"
                output += "  Fator de Potência (FP): N/A (circuito aberto)\n"

                output += "---------------------------\n"
                output += "Verificação LKT:\n"
                output += f"  Soma Fasorial (V_R+V_L+V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                output += f"  (Deveria ser igual à Tensão da Fonte: {self.format_phasor(v_source_phasor, 'V')})\n"
                
            else: 
                i_total_phasor = v_source_phasor / z_total 
                v_r_phasor = i_total_phasor * z_r
                v_l_phasor = i_total_phasor * z_l
                v_c_phasor = i_total_phasor * z_c

                output += f"Impedância Total (Z_total): {self.format_phasor(z_total, 'Ω')}\n"
                output += f"Corrente Total (I_total): {self.format_phasor(i_total_phasor, 'A')}\n"
                output += "---------------------------\n"
                output += f"Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                output += f"Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                output += f"Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"
                
                output += "---------------------------\n" 
                output += "Análise de Potência (Total):\n"
                s_complex = v_source_phasor * i_total_phasor.conjugate()
                p_real = s_complex.real
                q_reactive = s_complex.imag
                s_apparent_mag = abs(s_complex)
                power_factor = 0.0 
                if s_apparent_mag != 0:
                    power_factor = p_real / s_apparent_mag
                fp_type = "(N/A)" 
                epsilon = 1e-9 
                if abs(s_apparent_mag) < epsilon:
                     fp_type = "(N/A - sem potência)"
                elif abs(q_reactive) < epsilon: 
                    fp_type = "(unitário)"
                elif q_reactive > 0: 
                    fp_type = "(atrasado - indutivo)"
                else: 
                    fp_type = "(adiantado - capacitivo)"
                output += f"  Potência Aparente (|S|): {s_apparent_mag:.3f} VA\n"
                output += f"  Potência Ativa (P): {p_real:.3f} W\n"
                output += f"  Potência Reativa (Q): {q_reactive:.3f} VAR\n"
                output += f"  Fator de Potência (FP): {power_factor:.3f} {fp_type}\n"

                v_sum_phasor = v_r_phasor + v_l_phasor + v_c_phasor
                output += "---------------------------\n"
                output += "Verificação LKT:\n"
                output += f"  Soma Fasorial (V_R+V_L+V_C): {self.format_phasor(v_sum_phasor, 'V')}\n"
                output += f"  (Deveria ser igual à Tensão da Fonte: {self.format_phasor(v_source_phasor, 'V')})\n"
            
            self.results_text.configure(state="normal")
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", output)
            self.results_text.configure(state="disabled")

        except ValueError:
            messagebox.showerror("Erro de Entrada", "Por favor, insira valores numéricos válidos.")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {str(e)}")

    def format_phasor(self, complex_val, unit=""):
        if abs(complex_val) == float('inf'):
            return f"Infinito {unit}"
        mag = abs(complex_val)
        phase_rad = cmath.phase(complex_val)
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