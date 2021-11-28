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

    def get_y0(self):
        return self._y0

    def get_y1(self):
        return self._y1


class Process():
    def __init__(self, name, arrival, req_mem, duration):
        self._name = name
        self._arrival = arrival
        self._req_mem = req_mem
        self._duration = duration
        self._leaves = None
        self._malloc = None
        self._rect = None

    def malloc(self, ms):
        self._malloc = ms

    def get_arrival(self):
        return self._arrival

    def get_leaves(self):
        return self._leaves

    def set_leaves(self, instant):
        self._leaves = instant + self._duration

    def set_rect(self, rect):
        self._rect = rect

    def get_rect(self):
        return self._rect

    def get_req_mem(self):
        return self._req_mem

    def get_malloc(self):
        return self._malloc

    def get_name(self):
        return self._name


class Simulation():
    def __init__(self, processes, algo_opt, step_sec, mem_view):
        self.TOTAL_MEM = 2000
        self.instant = 1
        self.idle_processes = processes
        self.runn_processes = []
        self.algo_opt = algo_opt
        self.step_sec = 1/step_sec
        self.paused = False
        self.stopped = False
        self.run_instantly = False
        self.step_info = ""
        self.mem_view = mem_view

    def get_instant(self):
        return self.instant

    def step(self):
        while self.paused:
            time.sleep(.2)
        self.step_info = f"{self.instant}t -"
        for runn_ps in self.runn_processes:
            if self.instant >= runn_ps.get_leaves():
                self.free_mem_runn_ps(runn_ps)
        for idle_ps in self.idle_processes:
            if idle_ps.get_arrival() <= self.instant:
                mem_pos = 0

                if self.algo_opt == Algorithm.MEJ_HUECO.value:
                    free_mem = []  # [[0, 123], [165, 254]...]

                    for runn_ps in self.runn_processes:
                        if mem_pos < runn_ps.get_malloc().get_y0():
                            free_mem.append([mem_pos, runn_ps.get_malloc().get_y0() - 1])
                        mem_pos = runn_ps.get_malloc().get_y1() + 1
                    if mem_pos + idle_ps.get_req_mem() < self.TOTAL_MEM and idle_ps.get_malloc() == None:
                        free_mem.append([mem_pos, mem_pos + idle_ps.get_req_mem()])
                    if len(free_mem) > 0:
                        best_mem_space = min(free_mem, key=lambda mem: mem[0])

                        if best_mem_space[1] - best_mem_space[0] >= idle_ps.get_req_mem():
                            self.idle_to_runn(idle_ps, best_mem_space[0], best_mem_space[1])
                elif self.algo_opt == Algorithm.SIG_HUECO.value:
                    for runn_ps in self.runn_processes:
                        if mem_pos + idle_ps.get_req_mem() < runn_ps.get_malloc().get_y0():
                            self.idle_to_runn(idle_ps, mem_pos, mem_pos + idle_ps.get_req_mem())
                            break
                        mem_pos = runn_ps.get_malloc().get_y1() + 1
                    if mem_pos + idle_ps.get_req_mem() < self.TOTAL_MEM and idle_ps.get_malloc() == None:
                        self.idle_to_runn(idle_ps, mem_pos, mem_pos + idle_ps.get_req_mem())
            self.runn_processes.sort(key=lambda x: x.get_malloc().get_y0())
        self.instant += 1
        if not self.run_instantly:
            time.sleep(self.step_sec)

    def get_step_info(self):
        return self.step_info

    def idle_to_runn(self, idle_ps, y0, y1):
        idle_ps.malloc(MemorySpace(y0, y1))
        idle_ps.set_leaves(self.instant)
        idle_ps.set_rect(self.draw_rect(y0, y1))
        self.runn_processes.append(idle_ps)
        self.idle_processes.remove(idle_ps)
        self.step_info += f"> Puesto en marcha (Proceso {idle_ps.get_name()}) - Reservados {idle_ps.get_req_mem()} ({idle_ps.get_malloc().get_y0()}, {idle_ps.get_malloc().get_y1()})" + "\n"

    def free_mem_runn_ps(self, runn_ps):
        self.step_info += f"> Me voy (Proceso {runn_ps.get_name()}) - Quedan libres {runn_ps.get_req_mem()} ({runn_ps.get_malloc().get_y0()}, {runn_ps.get_malloc().get_y1()})" + "\n"
        self.mem_view.delete(runn_ps.get_rect())
        self.runn_processes.remove(runn_ps)

    def set_paused(self, paused):
        self.paused = paused

    def is_paused(self):
        return self.paused

    def set_stopped(self, stopped):
        self.stopped = stopped

    def is_stopped(self):
        return self.stopped

    def set_run_instantly(self):
        self.run_instantly = True

    def is_ended(self):
        return self.stopped or len(self.idle_processes) + len(self.runn_processes) == 0

    def draw_rect(self, y0, y1):
        return self.mem_view.create_rectangle(
            0, self.mem_view.winfo_screenmmheight() / self.TOTAL_MEM * y0, self.mem_view.winfo_screenwidth(), (self.mem_view.winfo_screenmmheight() / self.TOTAL_MEM) * y1, fill=self.get_rand_color())

    def get_rand_color(self):
        def r(): return random.randint(10, 220)
        return '#%02X%02X%02X' % (r(), r(), r())


class AppManager(Tk):
    def __init__(self):
        super().__init__()
        self.wm_title("Gestor Memoria")

        ## Control vars ##
        # Constants #
        self.MAX_LOG_LENGTH = 10
        self.INPUT_FILENAME = "processes.txt"

        # Control #
        self.processes = []
        self.app_state = State.IDLE
        self.algo_opt = IntVar()
        self.simulation = None
        self.sim_handl_thread = None
        self.ckbtn_instant_sim_value = BooleanVar()

        ## Widgets (UI) ##
        # Layout #
        self.frm_main = Frame(self)
        self.frm_inputs = Frame(self)
        self.fmr_processes_list = Frame(self)

        # Buttons, options and selectors #
        self.algo_sel_1 = Radiobutton(
            self.frm_inputs, text="Siguiente hueco", var=self.algo_opt, value=Algorithm.SIG_HUECO.value)
        self.algo_sel_2 = Radiobutton(
            self.frm_inputs, text="Mejor hueco", var=self.algo_opt, value=Algorithm.MEJ_HUECO.value)
        self.btn_quit = Button(self.frm_inputs, text="Salir", command=self.destroy)
        self.btn_read_ps_list = Button(
            self.fmr_processes_list, text="Leer listado procesos", command=self.read_ps_from_fl)
        self.btn_start = Button(self.frm_inputs, text="Iniciar", command=self.run_sim)
        self.btn_pause = Button(self.frm_inputs, text="Pausar", command=self.pause)
        self.btn_stop = Button(self.frm_inputs, text="Detener", command=self.stop)
        self.btn_clr_log = Button(self.frm_inputs, text="Limpiar", command=self.clr_log)
        self.btn_clr_processes_list = Button(self.fmr_processes_list, text="Vaciar", command=self.clr_processes_list)
        self.btn_rand_processes_list = Button(self.fmr_processes_list, text="Aleatorio", command=self.gen_rand_ps)
        self.sli_iter_sec = Scale(self.frm_inputs, label="Instantes/seg", from_=1, to=10, orient=HORIZONTAL)
        self.ckbtn_instant_sim = Checkbutton(self.frm_inputs, text="Simulación rápida", variable=self.ckbtn_instant_sim_value, onvalue=True, offvalue=False)

        # Data displays #
        self.mem_view = Canvas(bg="white", relief=SUNKEN, bd=2)
        self.mem_view_info = Canvas(bg="white", relief=SUNKEN, bd=2, width=100)
        self.log = Text(self, relief=SUNKEN, bd=2, state=DISABLED)
        self.processes_list = ttk.Treeview(self, columns=(
            "process", "arrival", "req_mem", "duration"))

        self.initUI()

    def initUI(self):
        self.algo_sel_1.select()
        ttk.Style(self).configure("Treeview", rowheight=15)

        # Table #
        self.processes_list.column("#0", width=0, stretch=NO)
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
        self.fmr_processes_list.grid(row=3, column=2, sticky=NSEW)
        self.mem_view_info.grid(row=0, column=1, sticky=NS, rowspan=2)
        self.mem_view.grid(row=0, column=2, sticky=NSEW, rowspan=2)
        self.log.grid(row=1, column=0, sticky=NSEW)
        self.processes_list.grid(row=2, column=2, sticky=NSEW)

        # Inputs grid #
        self.frm_inputs.columnconfigure(0, weight=3)
        self.frm_inputs.columnconfigure(1, weight=1)
        self.frm_inputs.columnconfigure(2, weight=2)
        self.algo_sel_1.grid(row=0, column=1, sticky=W)
        self.algo_sel_2.grid(row=1, column=1, sticky=W)
        self.btn_start.grid(row=0, column=0, sticky=NSEW)
        self.btn_pause.grid(row=1, column=0, sticky=NSEW)
        self.btn_stop.grid(row=2, column=0, sticky=NSEW)
        self.btn_quit.grid(row=3, column=0, sticky=NSEW)
        self.btn_clr_log.grid(row=0, column=3, sticky=NE)
        self.sli_iter_sec.grid(row=2, column=1, sticky=W, rowspan=3)
        self.ckbtn_instant_sim.grid(row=2, column=2, sticky=W, rowspan=3, columnspan=1)

        # Processes list grid #
        self.fmr_processes_list.columnconfigure(1, weight=3)
        self.fmr_processes_list.columnconfigure(2, weight=3)
        self.fmr_processes_list.columnconfigure(0, weight=1)
        self.btn_read_ps_list.grid(row=0, column=2, sticky=NSEW)
        self.btn_clr_processes_list.grid(row=0, column=0, sticky=NSEW)
        self.btn_rand_processes_list.grid(row=0, column=1, sticky=NSEW)

    def read_ps_from_fl(self):
        fl = open(self.INPUT_FILENAME, "r")

        self.clr_processes_list()
        while True:
            ln = fl.readline()
            if not ln:
                break
            try:
                self.add_ps_to_list(ln.strip())
            except:
                exit(1)
        fl.close()
        if len(self.processes) < 3:
            raise AppException(AppExceptionTypes.TooFewProcesses)
        self.update_gui()
        self.print("Los procesos se han cargado correctamente", "success")

    def add_ps_to_list(self, ps):
        ps_values = ps.split()

        if len(ps_values) != 4:
            raise AppException(AppExceptionTypes.WrongProcessInputFormat, ps_values)

        self.processes.append(Process(
            ps_values[0],
            int(ps_values[1]),
            int(ps_values[2]),
            int(ps_values[3])))

        self.processes_list.insert(
            parent="", index="end", text="", values=ps_values)

    def gen_rand_ps(self):
        amount = 50

        self.clr_processes_list()
        for i in range(0, amount):
            self.add_ps_to_list(f"p{str(i)} {random.randint(1, amount * 2)} {random.randint(100, 1999)} {random.randint(1, amount)}")
        self.update_gui()

    def clr_log(self):
        self.log.config(state=NORMAL)
        self.log.delete("1.0", END)
        self.log.config(state=DISABLED)

    def clr_processes_list(self):
        if len(self.processes_list.get_children()) == 0:
            return
        self.processes_list.delete(*self.processes_list.get_children())
        self.btn_start.config(state=DISABLED)
        self.print("Todos los procesos eliminados")
        self.processes = []

    def print(self, text, tags=None, endl=True):
        self.log.config(state=NORMAL)
        self.log.insert(END, "[" + datetime.datetime.now().strftime('%H:%M:%S') + "]~ " + str(text) + "\n" if endl else "", tags)
        self.log.yview_moveto(1)
        self.log.config(state=DISABLED)

    def run_sim(self):
        self.sim_handl_thread = t.Thread(target=self.handle_sim, daemon=True)
        self.sim_handl_thread.start()

    def is_checked_ckb_instant_sim(self, ckb):
        self.print(f"Simulación instantánea activada") if ckb.get() else self.print(f"Simulación instantánea desactivada")

    def handle_sim(self):
        self.print(f"{len(self.processes)} procesos cargados")
        self.print("Algoritmo a usar: " + ("Mejor hueco" if self.algo_opt.get() == Algorithm.MEJ_HUECO.value else "Siguiente hueco"))
        self.print("Lanzando simulación...")
        self.simulation = Simulation(self.processes.copy(), self.algo_opt.get(), self.sli_iter_sec.get(), self.mem_view)

        self.app_state = State.RUNNING
        if self.ckbtn_instant_sim_value.get():
            self.simulation.set_run_instantly()

        while not self.simulation.is_ended():
            self.update_gui()
            self.simulation.step()
            self.print(self.simulation.get_step_info())

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

    def update_gui(self):
        if self.app_state == State.RUNNING:
            self.btn_start.config(state=DISABLED)
            self.btn_stop.config(state=NORMAL)
            self.btn_pause.config(state=NORMAL)
            self.btn_read_ps_list.config(state=DISABLED)
            self.algo_sel_1.config(state=DISABLED)
            self.algo_sel_2.config(state=DISABLED)
            self.sli_iter_sec.config(state=DISABLED)
            self.ckbtn_instant_sim.config(state=DISABLED)
        elif self.app_state == State.IDLE:
            self.btn_stop.config(state=DISABLED)
            self.btn_pause.config(state=DISABLED)
            self.btn_read_ps_list.config(state=NORMAL)
            self.algo_sel_1.config(state=NORMAL)
            self.algo_sel_2.config(state=NORMAL)
            self.sli_iter_sec.config(state=NORMAL)
            self.ckbtn_instant_sim.config(state=NORMAL)
            self.btn_start.config(state=NORMAL) if len(self.processes) else self.btn_start.config(state=DISABLED)
        elif self.app_state == State.PAUSED:
            self.btn_start.config(state=DISABLED)
            self.btn_stop.config(state=NORMAL)
            self.btn_pause.config(state=NORMAL)
            self.btn_read_ps_list.config(state=DISABLED)
            self.algo_sel_1.config(state=DISABLED)
            self.algo_sel_2.config(state=DISABLED)
            self.sli_iter_sec.config(state=NORMAL)
            self.ckbtn_instant_sim.config(state=DISABLED)


def main():
    app = AppManager()
    app.mainloop()


if __name__ == "__main__":
    main()
