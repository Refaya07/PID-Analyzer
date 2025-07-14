import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import pandas as pd
import numpy as np
import importlib.resources
from sklearn.ensemble import RandomForestRegressor

DATA_FOLDER = "data"
COUNTER_FILE = "log_counter.txt"

def get_next_file_index():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("1")
        return 1
    with open(COUNTER_FILE, "r") as f:
        current = int(f.read().strip())
    with open(COUNTER_FILE, "w") as f:
        f.write(str(current + 1))
    return current

def apply_style():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background="#f8f9fa")
    style.configure("TLabel", background="#f8f9fa", font=("Segoe UI", 11))
    style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
    style.configure("TEntry", padding=5)
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    style.configure("Treeview", font=("Segoe UI", 10), rowheight=25)

class Sidebar(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#e9ecef", width=180)
        self.controller = controller
        self.pack_propagate(0)

        tk.Label(self, text="MENU", bg="#e9ecef", font=("Segoe UI", 14, "bold")).pack(pady=(20, 10))
        ttk.Button(self, text="Start", command=lambda: controller.show_frame("StartPage"), width=20).pack(pady=5)
        ttk.Button(self, text="Analisis", command=lambda: controller.show_frame("AnalysisPage"), width=20).pack(pady=5)
    

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        container = ttk.Frame(self)
        container.place(relx=0.5, rely=0.4, anchor="center")

        tk.Label(container, text="Mode Pengujian", font=("Segoe UI", 18, "bold"), bg="#f8f9fa").grid(row=0, column=0, columnspan=2, pady=10)
        ttk.Label(container, text="Pilih Mode:").grid(row=1, column=0, sticky="e")
        self.mode_var = tk.StringVar()
        self.mode_dropdown = ttk.Combobox(container, textvariable=self.mode_var, state="readonly")
        self.mode_dropdown['values'] = ["Air Temp", "Baby", "Humidity"]
        self.mode_dropdown.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        ttk.Label(container, text="Setpoint:").grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.setpoint_entry = ttk.Entry(container)
        self.setpoint_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

        ttk.Label(container, text="Waktu Pembacaan (detik):").grid(row=3, column=0, sticky="e", padx=10, pady=5)
        self.interval_entry = ttk.Entry(container)
        self.interval_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=5)

        ttk.Button(container, text="Upload Log File", command=self.upload_log_file).grid(row=4, column=0, columnspan=2, pady=15)
        ttk.Button(container, text="Lanjut ke Analisis", command=lambda: controller.show_frame("AnalysisPage")).grid(row=5, column=0, columnspan=2, pady=10)

    def upload_log_file(self):
        mode = self.mode_var.get()
        setpoint = self.setpoint_entry.get()
        interval = self.interval_entry.get()
        if not mode or not setpoint or not interval:
            messagebox.showwarning("Input Kurang", "Harap isi semua kolom sebelum melanjutkan.")
            return

        file_path = filedialog.askopenfilename(title="Pilih File Log", filetypes=[("Log files", "*.log")])
        if not file_path:
            return

        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
        except Exception as e:
            messagebox.showerror("Gagal Membaca File", str(e))
            return

        pattern = {
            "Air Temp": r"\[Air Mode\] \{heater: (\d+), fan: \d+, input: ([\d.]+), error: ([\-\d.]+)\}",
            "Baby":     r"\[Baby Mode\] \{heater: (\d+), fan: \d+, input: ([\d.]+), error: ([\-\d.]+)\}",
            "Humidity": r"\[Humidity Mode\] \{heater: (\d+), fan: \d+, input: ([\d.]+), error: ([\-\d.]+)\}",
        }.get(mode)

        data_rows = []
        for line in lines:
            match = re.search(pattern, line)
            if match:
                heater = int(match.group(1))
                input_val = float(match.group(2))
                error = float(match.group(3))
                data_rows.append({"setpoint": float(setpoint), "heater": heater, "input": input_val, "error": error})

        if not data_rows:
            messagebox.showwarning("Data Kosong", f"Tidak ditemukan data yang sesuai mode {mode}.")
            return

        os.makedirs(DATA_FOLDER, exist_ok=True)
        index = get_next_file_index()
        output_filename = f"Data_monitor{index}.xlsx"
        pd.DataFrame(data_rows).to_excel(os.path.join(DATA_FOLDER, output_filename), index=False)
        messagebox.showinfo("Berhasil", f"Data berhasil disimpan ke: {output_filename}")

class AnalysisPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.file_path = None

        container = ttk.Frame(self)
        container.place(relx=0.5, rely=0.4, anchor="center")
        tk.Label(container, text="Analisis Data", font=("Segoe UI", 16, "bold"), bg="#f8f9fa").grid(row=0, column=0, columnspan=2, pady=10)
        ttk.Button(container, text="Upload Excel", command=self.upload_excel).grid(row=1, column=0, columnspan=2, pady=5)
        self.kp_entry = self.make_entry(container, "Kp", 2)
        self.ki_entry = self.make_entry(container, "Ki", 3)
        self.kd_entry = self.make_entry(container, "Kd", 4)
        ttk.Button(container, text="Lanjut ke Rekap", command=self.proses_analisis).grid(row=5, column=0, columnspan=2, pady=20)

    def make_entry(self, parent, label, row):
        ttk.Label(parent, text=label + ":").grid(row=row, column=0, sticky="e", padx=10, pady=5)
        entry = ttk.Entry(parent)
        entry.grid(row=row, column=1, padx=10, sticky="ew")
        return entry

    def upload_excel(self):
        path = filedialog.askopenfilename(title="Pilih File Excel", filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.file_path = path
            messagebox.showinfo("Upload", f"Berhasil upload: {path}")

    def proses_analisis(self):
        if not self.file_path:
            messagebox.showerror("Error", "Silakan upload file Excel terlebih dahulu.")
            return
        try:
            df = pd.read_excel(self.file_path)
            kp, ki, kd = float(self.kp_entry.get()), float(self.ki_entry.get()), float(self.kd_entry.get())
        except Exception as e:
            messagebox.showerror("Input Error", str(e))
            return

        setpoint = df['setpoint'].iloc[0]
        input_values = df['input'].values
        time_step = 5
        rise_start = rise_end = None
        for i, val in enumerate(input_values):
            if rise_start is None and val >= 0.1 * setpoint:
                rise_start = i
            if rise_start is not None and val >= 0.9 * setpoint:
                rise_end = i
                break
        rise_time = (rise_end - rise_start) * time_step if rise_start is not None and rise_end is not None else 0
        tolerance = 0.05 * setpoint
        settling_time = 0
        for i in range(len(input_values) - 1, -1, -1):
            if abs(input_values[i] - setpoint) > tolerance:
                settling_time = (i + 1) * time_step
                break
        peak = np.max(input_values)
        overshoot = ((peak - setpoint) / setpoint) * 100 if peak > setpoint else 0
        steady_state_error = np.mean(np.abs(input_values[-int(len(input_values) * 0.1):] - setpoint))
        self.controller.analysis_result = {
            "setpoint": setpoint, "kp": kp, "ki": ki, "kd": kd,
            "rise_time": rise_time, "settling_time": settling_time,
            "overshoot": overshoot, "steady_state_error": steady_state_error
        }
        messagebox.showinfo("Berhasil", "Analisis selesai. Lanjut ke Rekap.")
        self.controller.show_frame("SummaryPage")

class SummaryPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.data_rows = []

        container = ttk.Frame(self)
        container.pack(pady=20, fill="both", expand=True)
        tk.Label(container, text="Rekap Hasil Analisis", font=("Segoe UI", 16, "bold"), bg="#f8f9fa").pack(pady=10)
        tree_frame = ttk.Frame(container)
        tree_frame.pack(fill="both", expand=True, padx=20)

        columns = ("setpoint", "kp", "ki", "kd", "rise_time", "settling_time", "overshoot", "steady_state_error")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").capitalize())
            self.tree.column(col, width=120, anchor="center")
        h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scroll.set)
        self.tree.pack(side="top", fill="x")
        h_scroll.pack(side="bottom", fill="x")

        button_frame = ttk.Frame(container)
        button_frame.pack(pady=10)
        # Hasil tuning ditampilkan di layar
        self.result_frame = ttk.Frame(container)
        self.result_frame.pack(pady=10)

        self.kp_label = ttk.Label(self.result_frame, text="Kp: -", font=("Segoe UI", 12, "bold"), foreground="#333")
        self.ki_label = ttk.Label(self.result_frame, text="Ki: -", font=("Segoe UI", 12, "bold"), foreground="#333")
        self.kd_label = ttk.Label(self.result_frame, text="Kd: -", font=("Segoe UI", 12, "bold"), foreground="#333")

        self.kp_label.grid(row=0, column=0, padx=20)
        self.ki_label.grid(row=0, column=1, padx=20)
        self.kd_label.grid(row=0, column=2, padx=20)

        ttk.Button(button_frame, text="Tambah Data", command=self.go_to_start).grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="Hapus Data", command=self.delete_selected_row).grid(row=0, column=1, padx=10)
        ttk.Button(button_frame, text="Tuning", command=self.run_tuning).grid(row=0, column=2, padx=10)

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        new_data = self.controller.analysis_result
        self.add_row(new_data)

    def add_row(self, row_dict):
        row = (
            row_dict["setpoint"], row_dict["kp"], row_dict["ki"], row_dict["kd"],
            row_dict["rise_time"], row_dict["settling_time"],
            row_dict["overshoot"], row_dict["steady_state_error"]
        )
        self.data_rows.append(row)
        self.tree.insert("", "end", values=row)

    def delete_selected_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Pilih Baris", "Silakan pilih baris yang ingin dihapus.")
            return
        for item in selected:
            idx = self.tree.index(item)
            self.tree.delete(item)
            self.data_rows.pop(idx)

    def go_to_start(self):
        self.controller.show_frame("StartPage")

    def run_tuning(self):
        if len(self.data_rows) < 3:
            messagebox.showwarning("Data Kurang", "Minimal butuh 3 data untuk training.")
            return
        try:
            df = pd.DataFrame(self.data_rows, columns=[
                "setpoint", "kp", "ki", "kd", "rise_time", "settling_time", "overshoot", "steady_state_error"
            ])
            X = df[["rise_time", "settling_time", "overshoot", "steady_state_error"]]
            model_kp = RandomForestRegressor().fit(X, df["kp"])
            model_ki = RandomForestRegressor().fit(X, df["ki"])
            model_kd = RandomForestRegressor().fit(X, df["kd"])
            mean_feat = X.mean().values.reshape(1, -1)
            pred_kp = model_kp.predict(mean_feat)[0]
            pred_ki = model_ki.predict(mean_feat)[0]
            pred_kd = model_kd.predict(mean_feat)[0]
            with open("hasil_tunning.txt", "w") as f:
                f.write(f"Kp: {pred_kp:.3f}\nKi: {pred_ki:.3f}\nKd: {pred_kd:.3f}\n")
                        # Tampilkan ke layar GUI
            self.kp_label.config(text=f"Kp: {pred_kp:.3f}")
            self.ki_label.config(text=f"Ki: {pred_ki:.3f}")
            self.kd_label.config(text=f"Kd: {pred_kd:.3f}")

            messagebox.showinfo("Berhasil", "Hasil tuning disimpan ke 'hasil_tunning.txt'")
        except Exception as e:
            messagebox.showerror("Tuning Error", str(e))

class MultiPageGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Integrated PID Analyzer")
        self.geometry("960x600")
        self.configure(bg="#f8f9fa")
        apply_style()

        self.analysis_result = {}
        self.sidebar = Sidebar(self, self)
        self.sidebar.pack(side="left", fill="y")

        self.container = tk.Frame(self, bg="#f8f9fa")
        self.container.pack(side="right", fill="both", expand=True)

        self.frames = {}
        for Page in (StartPage, AnalysisPage, SummaryPage):
            page_name = Page.__name__
            frame = Page(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("StartPage")

    def show_frame(self, page_name):
        self.frames[page_name].tkraise()

if __name__ == "__main__":
    app = MultiPageGUI()
    app.mainloop()
