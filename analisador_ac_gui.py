# <Cole o código completo da aplicação Tkinter aqui>
# Exemplo:
import tkinter as tk
from tkinter import ttk, messagebox
import cmath # Para números complexos
import math

class ACCircuitAnalyzerApp:
    def __init__(self, master):
        self.master = master
        master.title("Analisador de Circuito CA Série RLC")
        master.geometry("600x700") # Ajustado para melhor visualização

        # Estilo
        self.style = ttk.Style()
        self.style.theme_use('clam') # Um tema moderno

        # Frame principal
        main_frame = ttk.Frame(master, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Título dentro da janela
        title_label = ttk.Label(main_frame, text="Análise de Circuito CA Série RLC", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # --- Seção de Entradas ---
        input_frame = ttk.LabelFrame(main_frame, text="Parâmetros do Circuito e da Fonte", padding="15")
        input_frame.pack(fill=tk.X, pady=10)

        # Layout de grade para entradas
        input_frame.columnconfigure(1, weight=1) # Coluna dos campos de entrada expansível

        # Componentes
        ttk.Label(input_frame, text="Resistor (R) [Ω]:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.r_entry = ttk.Entry(input_frame, width=15)
        self.r_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.r_entry.insert(0, "100") # Valor padrão

        ttk.Label(input_frame, text="Indutor (L) [H]:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.l_entry = ttk.Entry(input_frame, width=15)
        self.l_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.l_entry.insert(0, "0.1") # Valor padrão

        ttk.Label(input_frame, text="Capacitor (C) [F]:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.c_entry = ttk.Entry(input_frame, width=15)
        self.c_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        self.c_entry.insert(0, "0.00001") # Valor padrão (10uF)

        # Fonte de Tensão CA
        ttk.Label(input_frame, text="Tensão da Fonte (Vmag) [V]:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.v_mag_entry = ttk.Entry(input_frame, width=15)
        self.v_mag_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        self.v_mag_entry.insert(0, "10") # Valor padrão

        ttk.Label(input_frame, text="Fase da Fonte (θv) [°]:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.v_phase_entry = ttk.Entry(input_frame, width=15)
        self.v_phase_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)
        self.v_phase_entry.insert(0, "0") # Valor padrão

        ttk.Label(input_frame, text="Frequência (f) [Hz]:").grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        self.freq_entry = ttk.Entry(input_frame, width=15)
        self.freq_entry.grid(row=5, column=1, padx=5, pady=5, sticky=tk.EW)
        self.freq_entry.insert(0, "60") # Valor padrão

        # Botão de Análise
        analyze_button = ttk.Button(main_frame, text="Analisar Circuito", command=self.analyze_circuit)
        analyze_button.pack(pady=20, ipadx=10, ipady=5)

        # --- Seção de Saídas ---
        output_frame = ttk.LabelFrame(main_frame, text="Resultados da Análise", padding="15")
        output_frame.pack(expand=True, fill=tk.BOTH, pady=10)

        self.results_text = tk.Text(output_frame, height=15, width=60, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1)
        self.results_text.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.results_text.config(state=tk.DISABLED) # Apenas leitura

        # Nota sobre a limitação
        note_label = ttk.Label(main_frame, text="Nota: Esta ferramenta analisa um circuito RLC série fixo.\nUm construtor gráfico de circuitos não está implementado.", justify=tk.CENTER)
        note_label.pack(pady=(10,0))


    def analyze_circuit(self):
        """
        Realiza a análise do circuito CA série RLC com base nos valores de entrada.
        """
        try:
            # Obter valores dos campos de entrada
            r_val = float(self.r_entry.get())
            l_val = float(self.l_entry.get())
            c_val = float(self.c_entry.get())
            v_mag = float(self.v_mag_entry.get())
            v_phase_deg = float(self.v_phase_entry.get())
            freq = float(self.freq_entry.get())

            # Validar entradas
            if r_val < 0 or l_val < 0 or c_val < 0 or v_mag < 0 or freq <= 0:
                messagebox.showerror("Erro de Entrada", "Valores de R, L, C e Vmag devem ser >= 0. Frequência deve ser > 0.")
                return

            # Converter fase da tensão para radianos
            v_phase_rad = math.radians(v_phase_deg)
            v_source_phasor = cmath.rect(v_mag, v_phase_rad) # Fasor da tensão da fonte

            # Calcular impedâncias
            # Impedância do Resistor
            z_r = complex(r_val, 0)

            # Impedância do Indutor
            # XL = 2 * pi * f * L
            z_l = complex(0, 2 * cmath.pi * freq * l_val) if l_val > 0 else complex(0,0)

            # Impedância do Capacitor
            # XC = 1 / (2 * pi * f * C)
            if c_val > 0:
                z_c = complex(0, -1 / (2 * cmath.pi * freq * c_val))
            else: # Capacitor com valor zero (ou negativo, já filtrado) é tratado como circuito aberto
                z_c = complex(float('inf'), 0) # Impedância infinita

            # Impedância Total
            z_total = z_r + z_l + z_c

            output = f"--- Parâmetros de Entrada ---\n"
            output += f"R: {r_val} Ω\n"
            output += f"L: {l_val} H\n"
            output += f"C: {c_val} F\n"
            output += f"Fonte: {v_mag:.2f} V ∠ {v_phase_deg:.2f}°\n"
            output += f"Frequência: {freq} Hz\n\n"
            output += "--- Resultados ---\n"

            if abs(z_total) == float('inf'):
                # Se a impedância total for infinita (ex: capacitor de 0F em série)
                i_total_phasor = complex(0, 0)
                output += "Impedância Total (Z_total): Infinita (Circuito Aberto)\n"
                output += f"Corrente Total (I_total): {self.format_phasor(i_total_phasor, 'A')}\n"
                v_r_phasor = complex(0,0)
                v_l_phasor = complex(0,0)
                v_c_phasor = v_source_phasor
                output += f"Tensão no Resistor (V_R): {self.format_phasor(v_r_phasor, 'V')}\n"
                output += f"Tensão no Indutor (V_L): {self.format_phasor(v_l_phasor, 'V')}\n"
                output += f"Tensão no Capacitor (V_C): {self.format_phasor(v_c_phasor, 'V')}\n"

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

                v_sum_phasor = v_r_phasor + v_l_phasor + v_c_phasor
                output += "---------------------------\n"
                output += f"Soma das Tensões (V_R+V_L+V_C): {self.format_phasor(v_sum_phasor, 'V')}\n"
                output += f"(Deveria ser igual à Tensão da Fonte: {self.format_phasor(v_source_phasor, 'V')})\n"

            self.results_text.config(state=tk.NORMAL)
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, output)
            self.results_text.config(state=tk.DISABLED)

        except ValueError:
            messagebox.showerror("Erro de Entrada", "Por favor, insira valores numéricos válidos.")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {str(e)}")

    def format_phasor(self, complex_val, unit=""):
        if abs(complex_val) == float('inf'):
            return f"Infinito {unit}"

        mag = abs(complex_val)
        phase_rad = cmath.phase(complex_val)
        phase_deg = math.degrees(phase_rad)
        return f"{mag:.3f} {unit} ∠ {phase_deg:.2f}°"


if __name__ == '__main__':
    root = tk.Tk()
    app = ACCircuitAnalyzerApp(root)
    root.mainloop()