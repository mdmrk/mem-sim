from tkinter import ttk
from tkinter import *
from copy import deepcopy
import threading as t
import random
import time
import enum
import math
import sys
import re


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
    InvalidMemoryAmount = 3
    WrongDataType = 4


class AppException(Exception):
    def __init__(self, AppExceptionTypes, text=""):
        super().__init__()
        if AppExceptionTypes == AppExceptionTypes.WrongProcessInputFormat:
            print("err -> '" + str(text) + "' tiene mal formato. Debería ser <process> <arrival> <req_mem> <duration>")
        elif AppExceptionTypes == AppExceptionTypes.TooFewProcesses:
            print("err -> Hay muy pocos procesos, se necesitan al menos 3")
        elif AppExceptionTypes == AppExceptionTypes.InvalidMemoryAmount:
            print(f"err -> La memoria requerida debe contenerse en (100, {Simulation.TOTAL_MEM}]")
        elif AppExceptionTypes == AppExceptionTypes.WrongDataType:
            print(f"err -> Se ha introducido un valor erróneo")


class MemorySpace():
    #
    # Espacio de memoria ocupada
    #
    def __init__(self, beg, end):
        self._beg = beg
        self._end = end

    def get_beg(self):
        return self._beg

    def get_end(self):
        return self._end

    def get_size(self):
        return self._end - self._beg + 1


class Process():
    #
    # Representación de un proceso
    #
    def __init__(self, name, arrival, req_mem, duration):
        self._name = name
        self._arrival = arrival
        self._req_mem = req_mem
        self._duration = duration
        self._leaves = None
        self._malloc = None  # Memoria
        self._rect = None
        self._info = None

    def malloc(self, mem_space):
        self._malloc = mem_space

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

    def set_info(self, info):
        self._info = info

    def get_info(self):
        return self._info

    def get_req_mem(self):
        return self._req_mem

    def get_malloc(self):
        return self._malloc

    def get_name(self):
        return self._name


class Simulation():
    #
    # Simula la gestión de memoria
    #
    TOTAL_MEM = 2000

    def __init__(self, processes, algo_opt, step_sec, mem_view, mem_view_info):
        self._instant = 1
        self._idle_processes = processes
        self._mem_view_info = mem_view_info
        self._mem_view = mem_view
        self._runn_processes = []
        self._algo_opt = algo_opt
        self._step_sec = 1/step_sec
        self._paused = False
        self._stopped = False
        self._step_info = ""

    def get_instant(self):
        return self._instant

    def step(self):
        #
        # Calcula una iteración en la simulación
        #
        self._step_info = f"{self._instant} -"
        for runn_ps in self._runn_processes:
            if self._instant >= runn_ps.get_leaves():
                self.free_mem_runn_ps(runn_ps)
        for idle_ps in self._idle_processes:
            if idle_ps.get_arrival() <= self._instant:
                mem_pos = 0

                if self._algo_opt == Algorithm.MEJ_HUECO.value:
                    # Algo. Mejor hueco
                    free_mem = [] # [[0, 123], [165, 254]...]

                    for runn_ps in self._runn_processes:
                        if mem_pos < runn_ps.get_malloc().get_beg() and runn_ps.get_malloc().get_beg() - mem_pos >= idle_ps.get_req_mem():
                            free_mem.append([mem_pos, runn_ps.get_malloc().get_beg() - 1])
                        mem_pos = runn_ps.get_malloc().get_end() + 1
                    if mem_pos + idle_ps.get_req_mem() - 1 < self.TOTAL_MEM and idle_ps.get_malloc() is None:
                        free_mem.append([mem_pos, mem_pos + idle_ps.get_req_mem() - 1])
                    if len(free_mem) > 0:
                        best_mem_space = min(free_mem, key=lambda mem: mem[1] - mem[0])
                        self.idle_to_runn(idle_ps, best_mem_space[0], best_mem_space[0] + idle_ps.get_req_mem() - 1)
                elif self._algo_opt == Algorithm.SIG_HUECO.value:
                    # Algo. Siguiente hueco
                    for runn_ps in self._runn_processes:
                        if mem_pos + idle_ps.get_req_mem() < runn_ps.get_malloc().get_beg():
                            self.idle_to_runn(idle_ps, mem_pos, mem_pos + idle_ps.get_req_mem() - 1)
                            break
                        mem_pos = runn_ps.get_malloc().get_end() + 1
                    if mem_pos + idle_ps.get_req_mem() - 1 < self.TOTAL_MEM and idle_ps.get_malloc() is None:
                        self.idle_to_runn(idle_ps, mem_pos, mem_pos + idle_ps.get_req_mem() - 1)
            self._runn_processes.sort(key=lambda x: x.get_malloc().get_beg())

    def get_step_info(self):
        return self._step_info

    def get_step_export(self):
        #
        # Devolver una cadena con los bloques ocupados y libres de memoria en este instante
        #
        mem_pos = 0
        line = ""

        line += f"{self._instant} "
        for runn_ps in self._runn_processes:
            if mem_pos < runn_ps.get_malloc().get_beg():
                line += f"[{mem_pos} hueco {runn_ps.get_malloc().get_beg() - 1}] "
            line += f"[{runn_ps.get_malloc().get_beg()} {runn_ps.get_name()} {runn_ps.get_malloc().get_size()}] "
            mem_pos = runn_ps.get_malloc().get_end() + 1
        if mem_pos < self.TOTAL_MEM:
            line += f"[{mem_pos} hueco {self.TOTAL_MEM - mem_pos}]"
        return line + "\n"

    def idle_to_runn(self, idle_ps, beg, end):
        #
        # Asignar memoria a un proceso y ponerlo en el array de los que se están ejecutando
        #
        color = self.get_rand_color()

        idle_ps.malloc(MemorySpace(beg, end))
        idle_ps.set_leaves(self._instant)
        idle_ps.set_rect(self.draw_rect(beg, end, color))
        idle_ps.set_info(self.draw_info(f"{idle_ps.get_name()} ({idle_ps.get_malloc().get_beg()}, {idle_ps.get_malloc().get_end()})", beg, end, color))
        self._runn_processes.append(idle_ps)
        self._idle_processes.remove(idle_ps)
        self._step_info += f" [!] Ocupa memoria (Proceso {idle_ps.get_name()}) -> {idle_ps.get_req_mem()} ({idle_ps.get_malloc().get_beg()}, {idle_ps.get_malloc().get_end()})" + "\n"

    def free_mem_runn_ps(self, runn_ps):
        #
        # Libera la memoria de un proceso
        #
        self._step_info += f" [!] Libera memoria (Proceso {runn_ps.get_name()}) -> {runn_ps.get_req_mem()} ({runn_ps.get_malloc().get_beg()}, {runn_ps.get_malloc().get_end()})" + "\n"
        self._mem_view.delete(runn_ps.get_rect())
        self._mem_view_info.delete(runn_ps.get_info())
        self._runn_processes.remove(runn_ps)

    def set_paused(self, paused):
        self._paused = paused

    def is_paused(self):
        return self._paused

    def set_stopped(self, stopped):
        self._stopped = stopped

    def is_stopped(self):
        return self._stopped

    def get_step_sec(self):
        return self._step_sec

    def inc_instant(self):
        self._instant += 1

    def is_ended(self):
        return self._stopped or len(self._idle_processes) + len(self._runn_processes) == 0

    def draw_rect(self, beg, end, color):
        #
        # Renderiza un rectángulo simulando un espacio en memoria
        #
        return self._mem_view.create_rectangle(0, self._mem_view.winfo_height() - (self._mem_view.winfo_height() / self.TOTAL_MEM * beg), self._mem_view.winfo_width(), self._mem_view.winfo_height() - (self._mem_view.winfo_height() / self.TOTAL_MEM) * end, fill=color, width=0)

    def draw_info(self, text, beg, end, color):
        #
        # Indica mediante texto el proceso e intervalo de memoria por cada espacio reservado
        #
        return self._mem_view_info.create_text(115, self._mem_view.winfo_height() - (self._mem_view_info.winfo_height() / self.TOTAL_MEM) * ((end + beg) / 2), text=text, fill=color, anchor=E)

    def get_rand_color(self):
        #
        # Devuelve un color aleatorio en formato hex
        #
        def r(): return random.randint(10, 220)
        return '#%02X%02X%02X' % (r(), r(), r())


class AppManager(Tk):
    #
    # Aplicación central. Maneja la interfaz de usuario y la simulación
    #
    def __init__(self):
        #
        # Constructor
        #
        super().__init__()
        self.wm_title("Gestor Memoria")

        ## Control vars ##
        # Constants #
        self.INPUT_FILENAME = "procesos.txt"
        self.MIN_PROCESSES_AMOUNT = 6

        # Control #
        self._processes = []
        self._app_state = State.IDLE
        self._algo_opt = IntVar()
        self.simulation = None
        self._sim_handl_thread = None
        self._ckbtn_instant_sim_value = BooleanVar()
        self._ckbtn_export_value = BooleanVar()

        ## Widgets (UI) ##
        # Layout #
        self.frm_main = Frame(self)
        self.frm_inputs = Frame(self)
        self.fmr_processes_list = Frame(self)

        # Buttons, textboxes, options and selectors #
        self.algo_sel_1 = Radiobutton(self.frm_inputs, text="Siguiente hueco", var=self._algo_opt, value=Algorithm.SIG_HUECO.value)
        self.algo_sel_2 = Radiobutton(self.frm_inputs, text="Mejor hueco", var=self._algo_opt, value=Algorithm.MEJ_HUECO.value)
        self.btn_quit = Button(self.frm_inputs, text="Salir", command=self.destroy)
        self.btn_start = Button(self.frm_inputs, text="Iniciar", command=self.run_sim)
        self.btn_pause = Button(self.frm_inputs, text="Pausar", command=self.pause)
        self.btn_stop = Button(self.frm_inputs, text="Detener", command=self.stop)
        self.btn_clr_log = Button(self.frm_inputs, text="Limpiar", command=self.clr_log)
        self.btn_clr_processes_list = Button(self.fmr_processes_list, text="Vaciar", command=self.clr_processes_list)
        self.btn_rand_processes_list = Button(self.fmr_processes_list, text="Aleatorio", command=self.gen_rand_ps)
        self.btn_read_processes_list = Button(self.fmr_processes_list, text="Importar procesos", command=self.read_ps_from_fl)
        self.sli_iter_sec = Scale(self.frm_inputs, label="Instantes/seg", from_=1, to=10, orient=HORIZONTAL)
        self.sli_processes_amount = Scale(self.fmr_processes_list, label="Núm. procesos", from_=self.MIN_PROCESSES_AMOUNT, to=500, sliderlength=10, orient=HORIZONTAL)
        self.ckbtn_instant_sim = Checkbutton(self.frm_inputs, text="Simulación rápida", variable=self._ckbtn_instant_sim_value, onvalue=True, offvalue=False)
        self.ckbtn_export = Checkbutton(self.frm_inputs, text="Exportar al acabar", variable=self._ckbtn_export_value, onvalue=True, offvalue=False)

        # Data displays #
        self.mem_view = Canvas(bg="white", relief=SUNKEN, bd=2)
        self.mem_view_info = Canvas(bg="white", relief=SUNKEN, bd=2, width=120)
        self.log = Text(self, relief=SUNKEN, bd=2, state=DISABLED)
        self.processes_list = ttk.Treeview(self, columns=("process", "arrival", "req_mem", "duration"))

        self.initUI()

    def initUI(self):
        #
        # Inicializa parámetros de la interfaz
        #
        self.algo_sel_1.select()
        ttk.Style(self).configure("Treeview", rowheight=15)

        # Table #
        self.processes_list.column("#0", width=0, stretch=NO)
        self.processes_list.column("process", anchor=CENTER, stretch=YES, width=90)
        self.processes_list.column("arrival", anchor=CENTER, stretch=YES, width=90)
        self.processes_list.column("req_mem", anchor=CENTER, stretch=YES, width=100)
        self.processes_list.column("duration", anchor=CENTER, stretch=YES, width=90)
        self.processes_list.heading("#0", text="", anchor=CENTER)
        self.processes_list.heading("process", anchor=CENTER, text="Proceso")
        self.processes_list.heading("arrival", anchor=CENTER, text="Llegada")
        self.processes_list.heading("req_mem", anchor=CENTER, text="Memoria req.")
        self.processes_list.heading("duration", anchor=CENTER, text="Duración")

        self.btn_start.config(state=DISABLED)
        self.btn_pause.config(state=DISABLED)
        self.btn_stop.config(state=DISABLED)

        self.log.tag_configure("warning", foreground="red")
        self.log.tag_configure("success", foreground="green")

        self.sli_processes_amount.set(50)

        ## Layout ##
        # Main grid #
        self.frm_main.grid()
        self.columnconfigure(0, weight=1)
        self.frm_inputs.grid(row=2, column=0, sticky=NSEW)
        self.fmr_processes_list.grid(row=3, column=2, sticky=NSEW)
        self.mem_view.grid(row=0, column=2, sticky=NSEW, rowspan=2)
        self.mem_view_info.grid(row=0, column=1, sticky=NS, rowspan=2)
        self.log.grid(row=1, column=0, sticky=NSEW)
        self.processes_list.grid(row=2, column=2, sticky=NSEW)

        # Inputs grid #
        self.frm_inputs.columnconfigure(0, minsize=120)
        self.frm_inputs.columnconfigure(3, weight=1)
        self.algo_sel_1.grid(row=0, column=1, sticky=W)
        self.algo_sel_2.grid(row=1, column=1, sticky=W)
        self.btn_start.grid(row=0, column=0, sticky=NSEW)
        self.btn_pause.grid(row=1, column=0, sticky=NSEW)
        self.btn_stop.grid(row=2, column=0, sticky=NSEW)
        self.btn_quit.grid(row=3, column=0, sticky=NSEW)
        self.btn_clr_log.grid(row=0, column=4, sticky=NE)
        self.sli_iter_sec.grid(row=2, column=1, sticky=W, rowspan=2)
        self.ckbtn_instant_sim.grid(row=2, column=2, sticky=W, columnspan=1)
        self.ckbtn_export.grid(row=3, column=2, sticky=W)

        # Processes list grid #
        self.fmr_processes_list.columnconfigure(1, weight=3)
        self.fmr_processes_list.columnconfigure(2, weight=3)
        self.fmr_processes_list.columnconfigure(0, weight=1)
        self.btn_read_processes_list.grid(row=0, column=2, sticky=NSEW)
        self.btn_clr_processes_list.grid(row=0, column=0, sticky=NSEW)
        self.btn_rand_processes_list.grid(row=0, column=1, sticky=NSEW)
        self.sli_processes_amount.grid(row=1, column=1, sticky=N)

    def read_ps_from_fl(self):
        #
        # Lee el archivo de texto para añadir los procesos
        #
        fl = open(self.INPUT_FILENAME, "r")

        self.clr_processes_list()
        while True:
            ln = fl.readline()
            if not ln:
                break
            if ln.startswith("#"):
                continue
            try:
                self.add_ps_to_list(ln.strip())
            except:
                self.clr_processes_list()
                return
        fl.close()
        self.update_ui()
        self.print("Los procesos se han cargado correctamente", "success")

    def add_ps_to_list(self, ps):
        #
        # Añade a la lista un proceso
        #
        ALL_NUM_RGX = r"^\d+$"
        ps_values = list(map(lambda value: int(value) if re.search(ALL_NUM_RGX, value) else value, ps.split()))

        if len(ps_values) != 4:
            raise AppException(AppExceptionTypes.WrongProcessInputFormat, ps_values)
        if ps_values[2] < 100 or ps_values[2] > Simulation.TOTAL_MEM:
            raise AppException(AppExceptionTypes.InvalidMemoryAmount, ps_values[2])
        if not re.search(ALL_NUM_RGX, str(ps_values[1])) or not re.search(ALL_NUM_RGX, str(ps_values[2])) or not re.search(ALL_NUM_RGX, str(ps_values[3])):
            raise AppException(AppExceptionTypes.WrongDataType)
        self._processes.append(Process(ps_values[0], ps_values[1], ps_values[2], ps_values[3]))
        self.processes_list.insert(parent="", index="end", text="", values=ps_values)

    def gen_rand_ps(self):
        #
        # Añade a la lista tantos procesos con datos aleatorios como indique el slider
        # Atajo: Ctrl+a
        #
        if self.btn_rand_processes_list["state"] == "disabled":
            return
        processes_amount = self.sli_processes_amount.get()

        self.clr_processes_list()
        for i in range(0, processes_amount):
            self.add_ps_to_list(f"p{str(i)} {random.randint(1, processes_amount * 3)} {random.randint(100, Simulation.TOTAL_MEM)} {random.randint(1, math.floor(processes_amount / 3))}")
        self.print(f"Se han cargado {processes_amount} procesos aleatoriamente", "success")
        self.update_ui()

    def clr_log(self):
        #
        # Limpia todo el texto del registro (log)
        #
        self.log.config(state=NORMAL)
        self.log.delete("1.0", END)
        self.log.config(state=DISABLED)

    def is_sim_ready_to_run(self):
        return len(self._processes) > 3 and self._app_state == State.IDLE

    def clr_processes_list(self):
        #
        # Elimina todos los procesos de la lista
        #
        if len(self.processes_list.get_children()) == 0 or self.btn_clr_processes_list["state"] == "disabled":
            return
        self.processes_list.delete(*self.processes_list.get_children())
        self.btn_start.config(state=DISABLED)
        self.print("Todos los procesos eliminados")
        self._processes = []

    def print(self, text, tags=None, endl=True):
        #
        # Imprime por el recuadro de texto (log)
        #
        self.log.config(state=NORMAL)
        self.log.insert(END, " " + str(text) + "\n" if endl else "", tags)
        self.log.yview_moveto(1)
        self.log.config(state=DISABLED)

    def run_sim(self):
        #
        # Guarda en variable el hilo que contiene la funcion de simulación y
        # la ejecuta
        # Atajo: Intro
        #
        self._sim_handl_thread = t.Thread(target=self.handle_sim, daemon=True)
        self._sim_handl_thread.start()

    def handle_sim(self):
        #
        # Se encarga de inicializar una nueva simulación, llamar
        # a realizar una nueva iteración y parar/pausar
        #
        self.print("Algoritmo a usar: " + ("Mejor hueco" if self._algo_opt.get() == Algorithm.MEJ_HUECO.value else "Siguiente hueco"))
        self.print("Lanzando simulación...")
        self.simulation = Simulation(deepcopy(self._processes), self._algo_opt.get(), self.sli_iter_sec.get(), self.mem_view, self.mem_view_info)
        export_txt = ""
        EXPORT_FILENAME = "particiones.txt"

        self._app_state = State.RUNNING

        while True:
            while self.simulation.is_paused() and not self.simulation.is_ended():
                time.sleep(.2)
            if self.simulation.is_ended():
                break
            self.update_ui()
            self.simulation.step()
            self.print(self.simulation.get_step_info())
            if not self._ckbtn_instant_sim_value.get():
                time.sleep(self.simulation.get_step_sec())
            if self._ckbtn_export_value.get():
                export_txt += self.simulation.get_step_export()
            self.simulation.inc_instant()

        if self.simulation.is_stopped():
            self.print("La simulación se ha detenido", "warning")
        else:
            self.print("La simulación se ha completado exitosamente", "success")
            if self._ckbtn_export_value.get():
                self.print(f"Exportando a {EXPORT_FILENAME}")
                with open(EXPORT_FILENAME, "w") as o_fl:
                    o_fl.write(str(export_txt))
        self._app_state = State.IDLE
        self.simulation = None
        self.update_ui()

    def pause(self):
        #
        # Pausa la simulación
        # Atajo: Barra espaciadora
        #
        if self.btn_pause["state"] == "disabled":
            return
        if self.simulation.is_paused():
            self._app_state = State.RUNNING
            self.simulation.set_paused(False)
        else:
            self._app_state = State.PAUSED
            self.simulation.set_paused(True)
        self.update_ui()

    def stop(self):
        #
        # Detiene la simulación
        # Atajo: Intro
        #
        self.simulation.set_stopped(True)
        self.print("Deteniendo simulación...")

    def update_ui(self):
        #
        # Actualizar elementos de la interfaz: ¿se debe poder interactuar con un elemento en este momento?, texto que muestra,...
        #
        if self._app_state == State.RUNNING:
            self.btn_start.config(state=DISABLED)
            self.btn_stop.config(state=NORMAL)
            self.btn_pause.config(state=NORMAL, text="Pausar")
            self.btn_read_processes_list.config(state=DISABLED)
            self.btn_clr_processes_list.config(state=DISABLED)
            self.btn_rand_processes_list.config(state=DISABLED)
            self.algo_sel_1.config(state=DISABLED)
            self.algo_sel_2.config(state=DISABLED)
            self.sli_iter_sec.config(state=DISABLED)
            self.ckbtn_instant_sim.config(state=DISABLED)
            self.ckbtn_export.config(state=DISABLED)
        elif self._app_state == State.IDLE:
            self.btn_stop.config(state=DISABLED)
            self.btn_pause.config(state=DISABLED, text="Pausar")
            self.btn_read_processes_list.config(state=NORMAL)
            self.btn_clr_processes_list.config(state=NORMAL)
            self.btn_rand_processes_list.config(state=NORMAL)
            self.btn_start.config(state=NORMAL) if len(self._processes) else self.btn_start.config(state=DISABLED)
            self.algo_sel_1.config(state=NORMAL)
            self.algo_sel_2.config(state=NORMAL)
            self.sli_iter_sec.config(state=NORMAL)
            self.ckbtn_instant_sim.config(state=NORMAL)
            self.ckbtn_export.config(state=NORMAL)
            self.mem_view.delete("all")
            self.mem_view_info.delete("all")
        elif self._app_state == State.PAUSED:
            self.btn_start.config(state=DISABLED)
            self.btn_stop.config(state=NORMAL)
            self.btn_pause.config(state=NORMAL, text="Reanudar")
            self.btn_read_processes_list.config(state=DISABLED)
            self.btn_clr_processes_list.config(state=DISABLED)
            self.btn_rand_processes_list.config(state=DISABLED)
            self.algo_sel_1.config(state=DISABLED)
            self.algo_sel_2.config(state=DISABLED)
            self.sli_iter_sec.config(state=NORMAL)
            self.ckbtn_instant_sim.config(state=DISABLED)
            self.ckbtn_export.config(state=DISABLED)


def set_hotkeys(app):
    #
    # Atajos de teclado
    #
    app.bind("<space>", lambda event: app.pause())  # Pausar simulación
    app.bind("<Control-q>", lambda event: app.destroy())  # Salir
    app.bind("<Control-a>", lambda event: app.gen_rand_ps())  # Llenar tabla con procesos aleatorios
    app.bind("<Control-l>", lambda event: app.clr_log())  # Limpiar el registro
    app.bind("<Control-L>", lambda event: app.clr_processes_list())  # Limpiar el listado de procesos (Ctrl+shift+l)
    app.bind("<Return>", lambda event: app.run_sim() if app.is_sim_ready_to_run() else app.stop() if app.simulation is not None else None)  # Iniciar / Detener simulación


def main():
    #
    # Programa principal
    #
    app = AppManager()
    set_hotkeys(app)
    app.mainloop()


if __name__ == "__main__":
    main()
