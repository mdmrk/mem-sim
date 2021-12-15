from tkinter import *
from tkinter import ttk
from enum import Enum
from copy import deepcopy
from threading import Thread
import random
import time
import math
import re


class SimState(Enum):
    RUNNING = 1
    IDLE = 2
    PAUSED = 3
    STOPPED = 4


class PrcsState(Enum):
    WAITING = 1
    RUNNING = 2
    ENDED = 3


class Algorithm(Enum):
    SIG_HUECO = 1
    MEJ_HUECO = 2


class AppExceptionTypes(Enum):
    WRONG_PROCESS_INPUT_FORMAT = 1
    TOO_FEW_PROCESSES = 2
    INVALID_REQUIRED_MEMORY_AMOUNT = 3
    WRONG_DATA_TYPE = 4
    SIMULATION_ERROR = 5


class AppException(Exception):
    def __init__(self, exc_type: AppExceptionTypes, text=""):
        super().__init__()
        if exc_type == exc_type.WRONG_PROCESS_INPUT_FORMAT:
            print("err -> '" + str(text) + "' tiene mal formato. Debería ser <process> <arrival> <req_mem> <duration>")
        elif exc_type == exc_type.TOO_FEW_PROCESSES:
            print("err -> Hay muy pocos procesos")
        elif exc_type == exc_type.INVALID_REQUIRED_MEMORY_AMOUNT:
            print(f"err -> La memoria requerida debe contenerse en (100, {Simulation.TOTAL_MEM}]")
        elif exc_type == exc_type.WRONG_DATA_TYPE:
            print(f"err -> Se ha introducido un valor erróneo")
        elif exc_type == exc_type.SIMULATION_ERROR:
            print(f"err -> Error en la simulación")


class Process():
    #
    # Representación de un proceso
    #
    def __init__(self, name: str, arrival: int, req_mem: int, duration: int):
        self._name = name
        self._arrival = arrival
        self._req_mem = req_mem
        self._duration = duration
        self._leaves = None
        self._prcs_state = PrcsState.WAITING

    def set_prcs_state(self, prcs_state: PrcsState):
        self._prcs_state = prcs_state

    def get_arrival(self):
        return self._arrival

    def get_leaves(self):
        return self._leaves

    def set_leaves(self, inst: int):
        self._leaves = inst + self._duration

    def get_req_mem(self):
        return self._req_mem

    def is_waiting(self):
        return self._prcs_state == PrcsState.WAITING

    def is_running(self):
        return self._prcs_state == PrcsState.RUNNING

    def is_ended(self):
        return self._prcs_state == PrcsState.ENDED

    def get_name(self):
        return self._name


class Partition():
    #
    # Espacio en memoria
    #
    def __init__(self, beg: int, size: int):
        self._beg = beg
        self._size = size
        self._prcs = None  # Una partición puede estar ocupada por un proceso

    def get_beg(self):
        return self._beg

    def get_end(self):
        return self._beg + self._size - 1

    def get_size(self):
        return self._size

    def reduce(self, amt: int):
        self._size -= amt
        self._beg += amt

    def expand(self, amt: int):
        self._size += amt

    def set_prcs(self, prcs: Process):
        self._prcs = prcs

    def get_prcs(self):
        return self._prcs

    def is_assigned(self):
        return True if self._prcs else False


class MemoryCanvasObj():
    def __init__(self, part: Partition, shape, text):
        self._part = part
        self._shape = shape
        self._text = text

    def get_part(self):
        return self._part

    def get_shape(self):
        return self._shape

    def get_text(self):
        return self._text


class MemoryCanvas():
    def __init__(self):
        self._mem_canvas_shapes = Canvas(bg="white", relief=SUNKEN, bd=2)
        self._mem_canvas_text = Canvas(bg="white", relief=SUNKEN, bd=2, width=120)
        self._objects = []

    def get_rand_color(self):
        #
        # Devuelve un color aleatorio en formato hex
        #
        def r(): return random.randint(10, 220)
        return '#%02X%02X%02X' % (r(), r(), r())

    def get_mem_canvas_shapes(self):
        return self._mem_canvas_shapes

    def get_mem_canvas_text(self):
        return self._mem_canvas_text

    def add_obj(self, part: Partition):
        color = self.get_rand_color()

        shape = self._mem_canvas_shapes.create_rectangle(0, self._mem_canvas_shapes.winfo_height() - (self._mem_canvas_shapes.winfo_height() / Simulation.TOTAL_MEM * part.get_beg()),
                                                         self._mem_canvas_shapes.winfo_width(), self._mem_canvas_shapes.winfo_height() - (self._mem_canvas_shapes.winfo_height() / Simulation.TOTAL_MEM) * part.get_end(), fill=color, width=0)
        text = self._mem_canvas_text.create_text(115, self._mem_canvas_shapes.winfo_height() - (self._mem_canvas_text.winfo_height() / Simulation.TOTAL_MEM) *
                                                 ((part.get_end() + part.get_beg()) / 2), text=f"{part.get_prcs().get_name()} ({part.get_beg()}, {part.get_end()})", fill=color, anchor=E)
        self._objects.append(MemoryCanvasObj(part, shape, text))

    def rmv_obj(self, part: Partition):
        obj: MemoryCanvasObj

        for obj in self._objects:
            if obj.get_part() == part:
                self._mem_canvas_shapes.delete(obj.get_shape())
                self._mem_canvas_text.delete(obj.get_text())
                self._objects.remove(obj)
                break

    def clr(self):
        self._mem_canvas_shapes.delete("all")
        self._mem_canvas_text.delete("all")
        self._objects = []


class Simulation():
    #
    # Simula la gestión de memoria
    #
    TOTAL_MEM = 2000

    def __init__(self, processes: list = None, algo_opt: Algorithm = None, step_sec: int = 1, mem_canvas: MemoryCanvas = None):
        self._inst = 1
        self._memory = [Partition(0, self.TOTAL_MEM)]
        self._mem_canvas = mem_canvas
        self._processes = processes
        self._algo_opt = algo_opt
        self._step_intvl = 1/step_sec
        self._step_info = ""
        self._sim_state = SimState.IDLE

    def get_inst(self):
        return self._inst

    def set_sim_state(self, state: SimState):
        self._sim_state = state

    def step(self):
        #
        # Calcula una iteración en la simulación
        #
        self._step_info = f"{self._inst} -"
        prcs: Process
        part: Partition

        for idx, part in enumerate(self._memory):
            if part.is_assigned():
                if part.get_prcs().get_leaves() <= self._inst:
                    self.liberate(part, idx)
        for prcs in self._processes:
            if prcs.get_arrival() <= self._inst and prcs.is_waiting():
                self.assign(prcs)

    def assign(self, prcs: Process):
        part: Partition

        if self._algo_opt == Algorithm.SIG_HUECO.value:
            for idx, part in enumerate(self._memory):
                if part.get_size() >= prcs.get_req_mem() and not part.is_assigned():
                    new_part = Partition(part.get_beg(), prcs.get_req_mem())
                    prcs.set_prcs_state(PrcsState.RUNNING)
                    prcs.set_leaves(self._inst)
                    new_part.set_prcs(prcs)
                    part.reduce(prcs.get_req_mem())
                    self._memory.insert(idx, new_part)
                    self._mem_canvas.add_obj(new_part)
                    self._step_info += f"\n     [!] Entra {prcs.get_name()} · Ocupa => {new_part.get_size()} ({new_part.get_beg()}, {new_part.get_end()})"
                    break
        elif self._algo_opt == Algorithm.MEJ_HUECO.value:
            part = None

            for idx, p in enumerate(self._memory):
                if p.get_size() >= prcs.get_req_mem() and not p.is_assigned():
                    part = p if part is None else p if p.get_size() < part.get_size() else part
            if part:
                idx = self._memory.index(part)
                new_part = Partition(part.get_beg(), prcs.get_req_mem())
                prcs.set_prcs_state(PrcsState.RUNNING)
                prcs.set_leaves(self._inst)
                new_part.set_prcs(prcs)
                part.reduce(prcs.get_req_mem())
                self._memory.insert(idx, new_part)
                self._mem_canvas.add_obj(new_part)
                self._step_info += f"\n     [!] Entra {prcs.get_name()} · Ocupa => {new_part.get_size()} ({new_part.get_beg()}, {new_part.get_end()})"

    def liberate(self, part: Partition, idx: int()):
        part: Partition
        prev_part = self._memory[idx - 1] if idx - 1 >= 0 else None
        if prev_part:
            prev_part = prev_part if not prev_part.is_assigned() else None
        next_part = self._memory[idx + 1] if idx + 1 < len(self._memory) else None
        if next_part:
            next_part = next_part if not next_part.is_assigned() else None

        self._step_info += f"\n     [!] Sale {part.get_prcs().get_name()} · Libera => {part.get_size()} ({part.get_beg()}, {part.get_end()})"
        self._processes.remove(part.get_prcs())
        part.get_prcs().set_prcs_state(PrcsState.ENDED)
        self._mem_canvas.rmv_obj(part)
        part.set_prcs(None)

        if prev_part and next_part:
            prev_part.expand(part.get_size() + next_part.get_size())
            self._memory.remove(next_part)
            self._memory.remove(part)
        elif prev_part:
            prev_part.expand(part.get_size())
            self._memory.remove(part)
        elif next_part:
            part.expand(next_part.get_size())
            self._memory.remove(next_part)
        else:
            pass

    def get_inst_export(self):
        step = ""
        part: Partition

        for part in self._memory:
            step += f"{self._inst} [{part.get_prcs().get_name() if part.is_assigned() else 'VACÍO'} {part.get_beg()}, {part.get_size()}]{' ' if self._memory[len(self._memory) - 1] != part else ''}"
        return step

    def get_step_info(self):
        return self._step_info

    def is_paused(self):
        return self._sim_state == SimState.PAUSED

    def is_stopped(self):
        return self._sim_state == SimState.STOPPED

    def is_ended(self):
        return self._sim_state == SimState.STOPPED or not len(self._processes)

    def is_idle(self):
        return self._sim_state == SimState.IDLE

    def is_running(self):
        return self._sim_state == SimState.RUNNING

    def get_step_sec(self):
        return self._step_intvl

    def clr_mem_canvas(self):
        self._mem_canvas.clr()

    def inc_inst(self):
        self._inst += 1


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
        self.MIN_PROCESSES_AMOUNT = 3
        self.MIN_MEMORY_VALUE = 100

        # Control #
        self._processes = []
        self._algo_opt = IntVar()
        self._simulation = Simulation()
        self._ckbtn_instant_sim_value = BooleanVar()
        self._ckbtn_export_value = BooleanVar()

        ## Widgets (UI) ##
        # Layout #
        self._frm_main = Frame(self)
        self._frm_inputs = Frame(self)
        self._frm_prcs_list = Frame(self)

        # Buttons, textboxes, options and selectors #
        self._algo_sel_1 = Radiobutton(self._frm_inputs, text="Siguiente hueco", var=self._algo_opt, value=Algorithm.SIG_HUECO.value)
        self._algo_sel_2 = Radiobutton(self._frm_inputs, text="Mejor hueco", var=self._algo_opt, value=Algorithm.MEJ_HUECO.value)
        self._btn_quit = Button(self._frm_inputs, text="Salir", command=self.destroy)
        self._btn_start = Button(self._frm_inputs, text="Iniciar", command=self.run_sim)
        self._btn_pause = Button(self._frm_inputs, text="Pausar", command=self.pause_sim)
        self._btn_stop = Button(self._frm_inputs, text="Detener", command=self.stop_sim)
        self._btn_clr_log = Button(self._frm_inputs, text="Limpiar", command=self.clr_log)
        self._btn_clr_prcs_list = Button(self._frm_prcs_list, text="Vaciar", command=self.clr_prcs_list)
        self._btn_rand_prcs_list = Button(self._frm_prcs_list, text="Aleatorio", command=self.make_rand_prcs)
        self._btn_read_prcs_list = Button(self._frm_prcs_list, text="Importar procesos", command=self.read_prcs_from_fl)
        self._sli_iter_sec = Scale(self._frm_inputs, label="Instantes/seg", from_=1, to=10, orient=HORIZONTAL)
        self._sli_prcs_amount = Scale(self._frm_prcs_list, label="Núm. procesos", from_=self.MIN_PROCESSES_AMOUNT, to=500, sliderlength=10, orient=HORIZONTAL)
        self._ckbtn_instant_sim = Checkbutton(self._frm_inputs, text="Simulación rápida", variable=self._ckbtn_instant_sim_value, onvalue=True, offvalue=False)
        self._ckbtn_export = Checkbutton(self._frm_inputs, text="Exportar al acabar", variable=self._ckbtn_export_value, onvalue=True, offvalue=False)

        # Data displays #
        self._mem_canvas = MemoryCanvas()
        self._log = Text(self, relief=SUNKEN, bd=2, state=DISABLED)
        self._prcs_list = ttk.Treeview(self, columns=("process", "arrival", "req_mem", "duration"))

        self.init_ui()

    def init_ui(self):
        #
        # Inicializa parámetros de la interfaz
        #
        self._algo_sel_1.select()
        ttk.Style(self).configure("Treeview", rowheight=15)

        # Table #
        self._prcs_list.column("#0", width=0, stretch=NO)
        self._prcs_list.column("process", anchor=CENTER, stretch=YES, width=90)
        self._prcs_list.column("arrival", anchor=CENTER, stretch=YES, width=90)
        self._prcs_list.column("req_mem", anchor=CENTER, stretch=YES, width=100)
        self._prcs_list.column("duration", anchor=CENTER, stretch=YES, width=90)
        self._prcs_list.heading("#0", text="", anchor=CENTER)
        self._prcs_list.heading("process", anchor=CENTER, text="Proceso")
        self._prcs_list.heading("arrival", anchor=CENTER, text="Llegada")
        self._prcs_list.heading("req_mem", anchor=CENTER, text="Memoria req.")
        self._prcs_list.heading("duration", anchor=CENTER, text="Duración")

        self._btn_start.config(state=DISABLED)
        self._btn_pause.config(state=DISABLED)
        self._btn_stop.config(state=DISABLED)

        self._log.tag_configure("red", foreground="red")
        self._log.tag_configure("green", foreground="green")

        self._sli_prcs_amount.set(30)

        ## Layout ##
        # Main grid #
        self.columnconfigure(0, weight=1)
        self._frm_inputs.grid(row=2, column=0, sticky=NSEW)
        self._frm_prcs_list.grid(row=3, column=2, sticky=NSEW)
        self._mem_canvas.get_mem_canvas_shapes().grid(row=0, column=2, sticky=NSEW, rowspan=2)
        self._mem_canvas.get_mem_canvas_text().grid(row=0, column=1, sticky=NS, rowspan=2)
        self._log.grid(row=1, column=0, sticky=NSEW)
        self._prcs_list.grid(row=2, column=2, sticky=NSEW)

        # Inputs grid #
        self._frm_inputs.columnconfigure(0, minsize=120)
        self._frm_inputs.columnconfigure(3, weight=1)
        self._algo_sel_1.grid(row=0, column=1, sticky=W)
        self._algo_sel_2.grid(row=1, column=1, sticky=W)
        self._btn_start.grid(row=0, column=0, sticky=NSEW)
        self._btn_pause.grid(row=1, column=0, sticky=NSEW)
        self._btn_stop.grid(row=2, column=0, sticky=NSEW)
        self._btn_quit.grid(row=3, column=0, sticky=NSEW)
        self._btn_clr_log.grid(row=0, column=4, sticky=NE)
        self._sli_iter_sec.grid(row=2, column=1, sticky=W, rowspan=2)
        self._ckbtn_instant_sim.grid(row=2, column=2, sticky=W, columnspan=1)
        self._ckbtn_export.grid(row=3, column=2, sticky=W)

        # Processes list grid #
        self._frm_prcs_list.columnconfigure(1, weight=3)
        self._frm_prcs_list.columnconfigure(2, weight=3)
        self._frm_prcs_list.columnconfigure(0, weight=1)
        self._btn_read_prcs_list.grid(row=0, column=2, sticky=NSEW)
        self._btn_clr_prcs_list.grid(row=0, column=0, sticky=NSEW)
        self._btn_rand_prcs_list.grid(row=0, column=1, sticky=NSEW)
        self._sli_prcs_amount.grid(row=1, column=1, sticky=N)

    def read_prcs_from_fl(self):
        #
        # Lee el archivo de texto para añadir los procesos
        #
        prcs_fl = open(self.INPUT_FILENAME, "r")

        self.clr_prcs_list()
        while True:
            prcs = prcs_fl.readline()
            if not prcs:
                break
            if prcs.startswith("#"):
                continue
            try:
                self.add_prcs(prcs.strip())
            except:
                self.clr_prcs_list()
                return
        prcs_fl.close()
        self.update_ui()
        self.print("Los procesos se han cargado correctamente", "green")

    def add_prcs(self, prcs: str):
        #
        # Añade a la lista un proceso
        #
        ALL_NUM_RGX = r"^\d+$"
        prcs_values = list(map(lambda value: int(value) if re.search(ALL_NUM_RGX, value) else value, prcs.split()))

        if len(prcs_values) != 4:
            raise AppException(AppExceptionTypes.WRONG_PROCESS_INPUT_FORMAT, prcs_values)
        if not re.search(ALL_NUM_RGX, str(prcs_values[1])) or not re.search(ALL_NUM_RGX, str(prcs_values[2])) or not re.search(ALL_NUM_RGX, str(prcs_values[3])):
            raise AppException(AppExceptionTypes.WRONG_DATA_TYPE)
        if prcs_values[2] < self.MIN_MEMORY_VALUE or prcs_values[2] > Simulation.TOTAL_MEM:
            raise AppException(AppExceptionTypes.INVALID_REQUIRED_MEMORY_AMOUNT, prcs_values[2])
        self._processes.append(Process(prcs_values[0], prcs_values[1], prcs_values[2], prcs_values[3]))
        self._prcs_list.insert(parent="", index="end", text="", values=prcs_values)

    def make_rand_prcs(self):
        #
        # Añade a la lista tantos procesos con datos aleatorios como indique el slider
        # Atajo: Ctrl+a
        #
        if self._btn_rand_prcs_list["state"] == "disabled":
            return
        prcs_amt = self._sli_prcs_amount.get()

        self.clr_prcs_list()
        for i in range(prcs_amt):
            self.add_prcs(f"p{str(i)} {random.randint(1, prcs_amt * 3)} {random.randint(100, Simulation.TOTAL_MEM)} {random.randint(1, math.floor(math.sqrt(math.pow(prcs_amt, 1.05))))}")
        self.print(f"Se han creado {prcs_amt} procesos aleatoriamente", "green")
        self.update_ui()

    def clr_log(self):
        #
        # Limpia todo el texto del registro (log)
        #
        self._log.config(state=NORMAL)
        self._log.delete("1.0", END)
        self._log.config(state=DISABLED)

    def is_sim_ready_to_run(self):
        return len(self._processes) >= self.MIN_PROCESSES_AMOUNT and self._simulation.is_idle()

    def clr_prcs_list(self):
        #
        # Elimina todos los procesos de la lista
        #
        if len(self._prcs_list.get_children()) == 0 or self._btn_clr_prcs_list["state"] == "disabled":
            return
        self._prcs_list.delete(*self._prcs_list.get_children())
        self._processes = []
        self.update_ui()
        self.print("Todos los procesos eliminados")

    def print(self, text: str, tags: str = None):
        #
        # Imprime por el recuadro de texto (log)
        #
        self._log.config(state=NORMAL)
        self._log.insert(END, " " + str(text) + "\n", tags)
        self._log.yview_moveto(1)
        self._log.config(state=DISABLED)

    def run_sim(self):
        #
        # Hilo que ejecuta funcion de simulación
        # Atajo: Intro
        #
        sim_handl_thread = Thread(target=self.handle_sim, daemon=True)
        sim_handl_thread.start()

    def handle_sim(self):
        #
        # Se encarga de inicializar una nueva simulación, llamar
        # a realizar una nueva iteración y parar/pausar
        #
        self.print("Algoritmo a usar: " + ("Mejor hueco" if self._algo_opt.get() == Algorithm.MEJ_HUECO.value else "Siguiente hueco"))
        self.print("Lanzando simulación...")
        self._simulation = Simulation(deepcopy(self._processes), self._algo_opt.get(), self._sli_iter_sec.get(), self._mem_canvas)
        export_txt = ""
        EXPORT_FILENAME = "particiones.txt"
        self._simulation.set_sim_state(SimState.RUNNING)

        try:
            while True:
                while self._simulation.is_paused() and not self._simulation.is_ended():
                    time.sleep(.2)
                if self._simulation.is_ended():
                    break
                self._simulation.step()
                self.print(self._simulation.get_step_info())
                if self._ckbtn_export_value.get():
                    export_txt += self._simulation.get_inst_export() + "\n"
                self.update_ui()
                if not self._ckbtn_instant_sim_value.get():
                    time.sleep(self._simulation.get_step_sec())
                self._simulation.inc_inst()
        except:
            self.print("Error en la simulación", "red")
            self._simulation.set_sim_state(SimState.STOPPED)
            raise AppException(AppExceptionTypes.SIMULATION_ERROR)
        finally:
            if self._simulation.is_stopped():
                self.print("La simulación se ha detenido", "red")
            else:
                self.print("La simulación se ha completado exitosamente", "green")
                if self._ckbtn_export_value.get():
                    self.print(f"Exportando a {EXPORT_FILENAME}")
                    with open(EXPORT_FILENAME, "w") as o_fl:
                        o_fl.write(str(export_txt))
            self._simulation.clr_mem_canvas()
            self._simulation = Simulation()
            self.update_ui()

    def pause_sim(self):
        #
        # Pausa la simulación
        # Atajo: Barra espaciadora
        #
        if self._btn_pause["state"] == "disabled":
            return
        if self._simulation.is_paused():
            self._simulation.set_sim_state(SimState.RUNNING)
        else:
            self._simulation.set_sim_state(SimState.PAUSED)
        self.update_ui()

    def stop_sim(self):
        #
        # Detiene la simulación
        # Atajo: Intro
        #
        if self._simulation.is_idle():
            return
        self._simulation.set_sim_state(SimState.STOPPED)
        self.print("Deteniendo simulación...")

    def update_ui(self):
        #
        # Actualizar elementos de la interfaz: ¿se debe poder interactuar con un elemento en este momento?, texto que muestra,...
        #
        if self._simulation.is_running():
            self._btn_start.config(state=DISABLED)
            self._btn_stop.config(state=NORMAL)
            self._btn_pause.config(state=NORMAL, text="Pausar")
            self._btn_read_prcs_list.config(state=DISABLED)
            self._btn_clr_prcs_list.config(state=DISABLED)
            self._btn_rand_prcs_list.config(state=DISABLED)
            self._algo_sel_1.config(state=DISABLED)
            self._algo_sel_2.config(state=DISABLED)
            self._sli_iter_sec.config(state=DISABLED)
            self._ckbtn_instant_sim.config(state=DISABLED)
            self._ckbtn_export.config(state=DISABLED)
        elif self._simulation.is_idle():
            self._btn_stop.config(state=DISABLED)
            self._btn_pause.config(state=DISABLED, text="Pausar")
            self._btn_read_prcs_list.config(state=NORMAL)
            self._btn_clr_prcs_list.config(state=NORMAL)
            self._btn_rand_prcs_list.config(state=NORMAL)
            self._btn_start.config(state=NORMAL) if len(self._processes) else self._btn_start.config(state=DISABLED)
            self._algo_sel_1.config(state=NORMAL)
            self._algo_sel_2.config(state=NORMAL)
            self._sli_iter_sec.config(state=NORMAL)
            self._ckbtn_instant_sim.config(state=NORMAL)
            self._ckbtn_export.config(state=NORMAL)
        elif self._simulation.is_paused():
            self._btn_start.config(state=DISABLED)
            self._btn_stop.config(state=NORMAL)
            self._btn_pause.config(state=NORMAL, text="Reanudar")
            self._btn_read_prcs_list.config(state=DISABLED)
            self._btn_clr_prcs_list.config(state=DISABLED)
            self._btn_rand_prcs_list.config(state=DISABLED)
            self._algo_sel_1.config(state=DISABLED)
            self._algo_sel_2.config(state=DISABLED)
            self._sli_iter_sec.config(state=NORMAL)
            self._ckbtn_instant_sim.config(state=DISABLED)
            self._ckbtn_export.config(state=DISABLED)


def set_hotkeys(app: AppManager):
    #
    # Atajos de teclado
    #
    app.bind("<space>", lambda event: app.pause_sim())  # Pausar simulación
    app.bind("<Control-q>", lambda event: app.destroy())  # Salir
    app.bind("<Control-a>", lambda event: app.make_rand_prcs())  # Llenar tabla con procesos aleatorios
    app.bind("<Control-l>", lambda event: app.clr_log())  # Limpiar el registro
    app.bind("<Control-L>", lambda event: app.clr_prcs_list())  # Limpiar el listado de procesos (Ctrl+shift+l)
    app.bind("<Return>", lambda event: app.run_sim() if app.is_sim_ready_to_run() else app.stop_sim() if app._simulation is not None else None)  # Iniciar / Detener simulación


def main():
    #
    # Programa principal
    #
    app = AppManager()
    set_hotkeys(app)
    app.mainloop()


if __name__ == "__main__":
    main()
