from tkinter import ttk
from tkinter import *
import threading as t
import datetime
import random
import time
import enum


class State(enum.Enum):
    RUNNING = 1
    IDLE = 2
    PAUSED = 3


class Algorithm(enum.Enum):
    SIG_HUECO = 1
    MEJ_HUECO = 2


class AppExceptionTypes(enum.Enum):
    WrongProcessInputFormat = 1
    TooFewProcesses = 2


class AppException(Exception):
    def __init__(self, AppExceptionTypes, text=""):
        super().__init__()
        if AppExceptionTypes == AppExceptionTypes.WrongProcessInputFormat:
            print("ERROR: " + str(text) + " tiene mal formato. Debería ser <process> <arrival> <req_mem> <duration>")
        elif AppExceptionTypes == AppExceptionTypes.TooFewProcesses:
            print("ERROR: hay muy pocos procesos, se necesitan almenos 3")


class MemorySpace():
    def __init__(self, y0, y1):
        self._y0 = y0
        self._y1 = y1

    def get_y0():
        return self._y0

    def get_y1():
        return self._y1


class MemoryViewer(Canvas):
    def __init__(self):
        super().__init__(bg="white", relief=SUNKEN, bd=2)


class MemoryViewerInfo(Canvas):
    def __init__(self):
        super().__init__(bg="white", relief=SUNKEN, bd=2, width=100)


class Simulation():
    def __init__(self):
        self.instant = 1
        self.malloc = []
        self.ps_data = None
        self.algo_opt = None
        self.step_sec = None
        self.paused = False
        self.stopped = False
        self.run_instantly = False

    def run_sim(self, ps_data, algo_opt, step_sec):
        self.ps_data = ps_data
        self.algo_opt = algo_opt
        self.step_sec = 1/step_sec

    def get_instant(self):
        return self.instant

    def step(self):
        if self.paused:
            return
        self.instant += 1
        if not self.run_instantly:
            time.sleep(self.step_sec)

    def set_paused(self, paused):
        self.paused = paused

    def is_paused(self):
        return self.paused

    def set_stopped(self, stopped):
        self.stopped = stopped

    def is_stopped(self):
        return self.stopped

    def run_instantly(self):
        self.run_instantly = True


class AppManager(Tk):
    def __init__(self):
        super().__init__()

        ## Control vars ##
        # Constants #
        self.TOTAL_MEM = 2000
        self.MAX_LOG_LENGTH = 10
        self.INPUT_FILENAME = "processes.txt"

        # Control #
        self.ps_data = []
        self.app_state = State.IDLE
        self.algo_opt = Algorithm.SIG_HUECO
        self.simulation = None
        self.sim_handl_thread = None
        self.ckbtn_instant_sim_value = StringVar()

        ## Widgets (UI) ##
        # Layout #
        self.frm_main = Frame(self)
        self.frm_inputs = Frame(self)

        # Buttons, options and selectors #
        self.algo_sel_1 = Radiobutton(
            self.frm_inputs, text="Siguiente hueco", var=self.algo_opt, value=Algorithm.SIG_HUECO)
        self.algo_sel_2 = Radiobutton(
            self.frm_inputs, text="Mejor hueco", var=self.algo_opt, value=Algorithm.MEJ_HUECO)
        self.btn_quit = Button(self.frm_inputs, text="Salir", command=self.destroy)
        self.btn_gen_ps_list = Button(
            self.frm_inputs, text="Leer listado procesos", command=self.read_ps_from_fl)
        self.btn_start = Button(self.frm_inputs, text="Iniciar", command=self.run_sim)
        self.btn_pause = Button(self.frm_inputs, text="Pausar", command=self.pause)
        self.btn_stop = Button(self.frm_inputs, text="Detener", command=self.stop)
        self.sli_iter_sec = Scale(self.frm_inputs, label="Instantes/segundo", from_=1, to=10, orient=HORIZONTAL)
        self.ckbtn_instant_sim = Checkbutton(self.frm_inputs, text="Simulación instantánea", variable=self.ckbtn_instant_sim_value)

        # Data displays #
        self.mem_view = MemoryViewer()
        self.mem_view_info = MemoryViewerInfo()
        self.log = Text(self, relief=SUNKEN, bd=2, state=DISABLED)
        self.processes_list = ttk.Treeview(self, columns=(
            "process", "arrival", "req_mem", "duration"))

        self.initUI()

    def initUI(self):
        self.wm_title("Gestor Memoria")
        self.algo_sel_1.select()
        ttk.Style(self).configure("Treeview", rowheight=15)

        # Table #
        self.processes_list.column("#0", width=0,  stretch=NO)
        self.processes_list.column(
            "process", anchor=CENTER, stretch=YES, width=90)
        self.processes_list.column(
            "arrival", anchor=CENTER, stretch=YES, width=90)
        self.processes_list.column(
            "req_mem", anchor=CENTER, stretch=YES, width=100)
        self.processes_list.column(
            "duration", anchor=CENTER, stretch=YES, width=90)
        self.processes_list.heading("#0", text="", anchor=CENTER)
        self.processes_list.heading("process", anchor=CENTER, text="Proceso")
        self.processes_list.heading("arrival", anchor=CENTER, text="Llegada")
        self.processes_list.heading(
            "req_mem", anchor=CENTER, text="Memoria req.")
        self.processes_list.heading("duration", anchor=CENTER, text="Duración")

        self.btn_start.config(state=DISABLED)
        self.btn_pause.config(state=DISABLED)
        self.btn_stop.config(state=DISABLED)

        self.log.tag_configure("warning", foreground="red")
        self.log.tag_configure("success", foreground="green")

        ## Layout ##
        # Main grid #
        self.frm_main.grid()
        self.columnconfigure(0, weight=1)
        self.frm_inputs.grid(row=2, column=0, sticky=NSEW)
        self.mem_view_info.grid(row=0, column=1, sticky=NS, rowspan=2)
        self.mem_view.grid(row=0, column=2, sticky=NSEW, rowspan=2)
        self.log.grid(row=1, column=0, sticky=NSEW)
        self.processes_list.grid(row=0, column=0, sticky=NSEW)

        # Inputs grid #
        self.frm_inputs.columnconfigure(1, weight=1)
        self.frm_inputs.columnconfigure(2, weight=2)
        self.algo_sel_1.grid(row=0, column=1, sticky=W)
        self.algo_sel_2.grid(row=1, column=1, sticky=W)
        self.btn_gen_ps_list.grid(row=0, column=0, sticky=NSEW)
        self.btn_start.grid(row=1, column=0, sticky=NSEW)
        self.btn_pause.grid(row=2, column=0, sticky=NSEW)
        self.btn_stop.grid(row=3, column=0, sticky=NSEW)
        self.btn_quit.grid(row=4, column=0, sticky=NSEW)
        self.sli_iter_sec.grid(row=2, column=1, sticky=W, rowspan=3)
        self.ckbtn_instant_sim.grid(row=2, column=2, sticky=W, rowspan=3)

    def read_ps_from_fl(self):
        fl = open(self.INPUT_FILENAME, "r")

        self.processes_list.delete(*self.processes_list.get_children())
        self.ps_data = []
        while True:
            ln = fl.readline()
            if not ln:
                break
            try:
                self.add_ps_to_list(ln.strip())
            except:
                exit(1)
        fl.close()
        if len(self.ps_data) < 3:
            raise AppException(AppExceptionTypes.TooFewProcesses)
        if len(self.ps_data):
            self.btn_start.config(state=NORMAL)
        else:
            self.btn_start.config(state=DISABLED)

    def add_ps_to_list(self, ps):
        ps_values = ps.split()

        if len(ps_values) != 4:
            raise AppException(AppExceptionTypes.WrongProcessInputFormat, ps_values)

        self.ps_data.append({
            "process": ps_values[0],
            "arrival": int(ps_values[1]),
            "req_mem": ps_values[2],
            "duration": int(ps_values[3]),
            "leaves": int(ps_values[1]) + int(ps_values[3])
        })
        self.processes_list.insert(
            parent="", index="end", text="", values=ps_values)

    def draw_rect(self, y0, y1):
        self.mem_view.create_rectangle(
            0, y0, self.mem_view.winfo_screenwidth(), y1, fill=self.get_rand_color())

    def get_rand_color(self):
        def r(): return random.randint(10, 220)
        return '#%02X%02X%02X' % (r(), r(), r())

    def print(self, text, tags=None, endl=True):
        self.log.config(state=NORMAL)
        self.log.insert(END, "[" + datetime.datetime.now().strftime('%H:%M:%S') + "]~ " + str(text) + "\n" if endl else "", tags)
        self.log.config(state=DISABLED)

    def run_sim(self):
        self.sim_handl_thread = t.Thread(target=self.handle_sim, daemon=True)
        self.sim_handl_thread.start()

    def handle_sim(self):
        def sort_arrival(k): return k["arrival"]
        last_ps_to_leave = max(ps["leaves"] for ps in self.ps_data)
        self.simulation = Simulation()

        self.print(f"{len(self.ps_data)} procesos cargados")
        self.print("Ordenando procesos por tiempo de llegada")
        self.ps_data.sort(key=sort_arrival)
        self.print("Lanzando simulación...")

        self.app_state = State.RUNNING
        self.simulation.run_sim(self.ps_data, self.algo_opt, self.sli_iter_sec.get())
        if self.ckbtn_instant_sim_value.get():
            self.simulation.run_instantly()

        while self.simulation.get_instant() < last_ps_to_leave and not self.simulation.is_stopped():
            self.update_gui()
            self.simulation.step()

        self.print("La simulación se ha detenido", "warning") if self.simulation.is_stopped() else self.print("La simulación se ha completado exitosamente", "success")
        self.app_state = State.IDLE
        self.simulation = None
        self.update_gui()

    def pause(self):
        if self.simulation.is_paused():
            self.state = State.RUNNING
            self.update_gui()
            self.simulation.set_paused(False)
            self.btn_pause.config(text="Pausar")
        else:
            self.state = State.PAUSED
            self.update_gui()
            self.simulation.set_paused(True)
            self.btn_pause.config(text="Reanudar")

    def stop(self):
        self.simulation.set_stopped(True)
        self.print("Deteniendo simulación...")
        self.update_gui()

    def update_gui(self):
        if self.app_state == State.RUNNING:
            self.btn_start.config(state=DISABLED)
            self.btn_stop.config(state=NORMAL)
            self.btn_pause.config(state=NORMAL)
            self.btn_gen_ps_list.config(state=DISABLED)
            self.algo_sel_1.config(state=DISABLED)
            self.algo_sel_2.config(state=DISABLED)
            self.sli_iter_sec.config(state=DISABLED)
            self.ckbtn_instant_sim.config(state=DISABLED)
        elif self.app_state == State.IDLE:
            self.btn_start.config(state=NORMAL)
            self.btn_stop.config(state=DISABLED)
            self.btn_pause.config(state=DISABLED)
            self.btn_gen_ps_list.config(state=NORMAL)
            self.algo_sel_1.config(state=NORMAL)
            self.algo_sel_2.config(state=NORMAL)
            self.sli_iter_sec.config(state=NORMAL)
            self.ckbtn_instant_sim.config(state=NORMAL)
        elif self.app_state == State.PAUSED:
            self.btn_start.config(state=DISABLED)
            self.btn_stop.config(state=NORMAL)
            self.btn_pause.config(state=NORMAL)
            self.btn_gen_ps_list.config(state=DISABLED)
            self.algo_sel_1.config(state=DISABLED)
            self.algo_sel_2.config(state=DISABLED)
            self.sli_iter_sec.config(state=NORMAL)
            self.ckbtn_instant_sim.config(state=DISABLED)


def main():
    app = AppManager()
    app.mainloop()


if __name__ == "__main__":
    main()