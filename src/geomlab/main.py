import matplotlib
import random
import logging
import datetime

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont

# Philipp's deps:
import numpy as np
import cv2
import math

# Import covid loader and most recent covid data
from . import covidloader as cl
from . import symbolicstacking as st

# Basic settings
logging.basicConfig(filename="log.txt", level=logging.DEBUG)

# Expand TK's oval:
def _create_circle(self, x, y, r, **kwargs):
    return self.create_oval(x - r, y - r, x + r, y + r, **kwargs)


tk.Canvas.create_circle = _create_circle

# Expand TK's oval to support our pies:
def _create_circle_arc(self, x, y, r, **kwargs):
    if "start" in kwargs and "end" in kwargs:
        kwargs["extent"] = kwargs["end"] - kwargs["start"]
        del kwargs["end"]
    return self.create_arc(x - r, y - r, x + r, y + r, **kwargs)


tk.Canvas.create_circle_arc = _create_circle_arc


def on_combo_configure(event):
    """Adjust width of combobox based on values."""
    combo = event.widget
    style = ttk.Style()

    long = max(combo.cget("values"), key=len)

    font = tkfont.nametofont(str(combo.cget("font")))
    width = max(0, font.measure(long.strip() + "0") - combo.winfo_width())

    style.configure("TCombobox", postoffset=(0, 0, width, 0))


# Main Window
class GeomLabApp(tk.Tk):
    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)

        # Configure self
        self.geometry("1800x868")
        self.title("Symbolic Maps")

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Symbolic Maps", command=lambda: self.show_frame(SymbolicMapsPage)
        )
        file_menu.add_command(
            label="Painting Program",
            command=lambda: self.show_frame(PaintingProgramPage),
        )
        file_menu.add_command(
            label="Matplotlib", command=lambda: self.show_frame(MatplotlibPage)
        )
        file_menu.add_command(label="About", command=lambda: self.show_frame(AboutPage))
        file_menu.add_command(label="Quit", command=lambda: self.destroy())
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

        # Configure content
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Create "pages"
        self.frames = {}

        # Create
        for page in (SymbolicMapsPage, PaintingProgramPage, MatplotlibPage, AboutPage):
            frame = page(container, self)
            frame.grid(row=0, column=0, sticky="nswe")
            self.frames[page] = frame

        # Add a second SymbolicMapsPage
        scnd_container = tk.Frame(self)
        scnd_container.pack(side="top", fill="both", expand=True)
        scnd_frame = SymbolicMapsPage(scnd_container, self)
        scnd_frame.grid(row=0, column=1, sticky="nswe")

        # Display
        self.show_frame(SymbolicMapsPage)

    def show_frame(self, container):
        """Show a specific frame in the window."""

        frame = self.frames[container]
        frame.tkraise()


# Frames
class SymbolicMapsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()

        # Display objects
        self.pie_sets = {}
        self.pie_piece_sets = {}
        self.data_sets = {}
        self.circles = []
        self.pies = []
        self.piePieces = []
        self.circlesToDraw = []  # for nested disks different structure
        self.numberOfFeatures = 0  # numberOffeatures eg, rec,dead,rest equal 3
        self.angles = []

        # Code
        self.initialize_data()
        self.prepare_data()
        self.timer_running = False
        self.counter = 123456
        self.timer_start_timestamp = datetime.datetime.now()

        # Execute symbolic algo
        self.apply_algorithm()

    # TODO: Shift into own object
    # TODO: Timer is defunct - probably needs an own thread for display updates
    # TODO: Using wallclock timestamps for now
    def timer_update_label(self):
        def count():
            if self.timer_running:
                if self.counter == 123456:
                    timestr = "Starting..."
                else:
                    timestamp = datetime.date.fromtimestamp(self.counter)
                    timestr = timestamp.strftime("%H:%M:%S")
                self.timerlabel["text"] = timestr

                self.timerlabel.after(1000, count)
                self.counter += 1

        # timer is running
        count()

    def timer_start(self):
        self.timer_running_label["bg"] = "red"
        self.timer_running_label["text"] = "Timer running"
        self.timer_running_label.update_idletasks()
        self.timer_start_timestamp = datetime.datetime.now()
        # self.timer_update_label()

    def timer_stop(self):
        self.timer_running_label["bg"] = "green"
        self.timer_running_label["text"] = "Timer not running"
        self.timer_running_label.update_idletasks()
        self.timerlabel["text"] = (
            "Runtime (wall): "
            + str(
                int(
                    (
                        datetime.datetime.now() - self.timer_start_timestamp
                    ).total_seconds()
                    * 1000
                )
            )
            + " milliseconds"
        )

        # self.timer_running = False
        # self.counter = 123456

    def apply_algorithm(self):
        """Update Canvas upon algo change."""

        # Set current dataset
        print("Current data set:")
        print(self.data.current())

        self.circles = self.data_sets[self.data.current()]
        self.piePieces = self.pie_piece_sets[self.data.current()]
        self.pies = self.pie_sets[self.data.current()]
        self.angles = [0] * len(self.pies)

        algo = self.algorithm.current()
        # "Painter", #0
        # "Random", #1
        # "Pie stacking", #2
        # "hawaiian stacking", #3
        # "maxMinMinK Stacking (absolute)", #4
        # "maxMinMinK Stacking (relative)", #5
        # "maxMinSumK Stacking (absolute)", #6
        # "maxMinSumK Stacking (relative)", #7
        # "maxMinSumK Stacking (weighted)", #8

        # Timer start
        self.timer_start()

        # TODO: Assuming objective values are positive
        objective_value = -1

        if algo == 0:
            self.circles = st.algorithmNestedDisksPainter(self.circles)
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
        elif algo == 1:
            random.shuffle(self.circles)
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
        elif algo == 2:
            self.pies, self.piePieces, self.angles = st.algorithmPieChartsStacking(
                self.pies, self.piePieces
            )
        elif algo == 3:
            self.circlesToDraw = st.algorithmHawaiianStacking(self.circles)
            self.numberOfFeatures = len(self.circles[0]) - 2

        elif algo == 4:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinMin(
                self.circles, "absolute"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
        elif algo == 5:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinMin(
                self.circles, "relative"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
        elif algo == 6:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinSum(
                self.circles, "relative"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
        elif algo == 7:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinSum(
                self.circles, "relative"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
        elif algo == 8:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinSum(
                self.circles, "weighted"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
        else:
            logging.critical("You shouldn't see me.")

        # Timer end
        self.timer_stop()

        # Objective update
        if objective_value != -1:
            self.objective_running_label["text"] = "Objective"
            self.objectivelabel["text"] = str(objective_value)
            self.objective_running_label["bg"] = "green"
        else:
            self.objective_running_label["bg"] = "red"
            self.objective_running_label["text"] = "No objective"
            self.objectivelabel["text"] = "N/A"

        # Draw
        self.draw_subcircle_stacking()
        if algo == 2:
            self.draw_pie_stacking()

    def draw_circles(self):

        for c in self.circles:
            # x, y ,r
            self.canvas.create_circle(c[0], c[1], c[2], fill="#bbb", outline="#000")

    def from_rgb(self, rgb):
        """translates an rgb tuple of int to a tkinter friendly color code"""
        return "#%02x%02x%02x" % rgb

    def draw_subcircle_stacking_3Features(self):
        counter = 1
        for c in self.circlesToDraw:
            y = c[0]
            x = c[1]
            r = c[2]
            if counter == 1:
                color = "#FF9994"
            if counter == 2:
                color = "#94FF99"
            if counter == 3:
                color = "#A0A0A0"
            counter = counter + 1
            if counter == 4:
                counter = 1
            self.canvas.create_circle(x, y, r, fill=color, outline="#000")

    def draw_subcircle_stacking_arbitraryFeatures(self):
        counter = 0
        counterMax = self.numberOfFeatures - 1
        for c in self.circlesToDraw:
            y = c[0]
            x = c[1]
            r = c[2]
            colorValue = int(200 - counter * (150 / counterMax))
            colorRGB = (colorValue, colorValue, colorValue)
            colorHEX = self.from_rgb(colorRGB)
            self.canvas.create_circle(x, y, r, fill=colorHEX, outline="#000")
            if counter == counterMax:
                counter = 0
            else:
                counter = counter + 1

    def draw_subcircle_stacking(self):
        counterMax = self.numberOfFeatures
        if counterMax == 3:
            self.draw_subcircle_stacking_3Features()
        else:
            self.draw_subcircle_stacking_arbitraryFeatures()

    def draw_pie_stacking_3Features(self):
        for i in range(0, len(self.pies)):
            angle = self.angles[i]
            y = self.pies[i][0]
            x = self.pies[i][1]
            r = self.pies[i][2]
            angle = self.angles[i]
            s = angle * 180 / np.pi
            e = (angle + self.piePieces[i][0]) * 180 / np.pi
            ext = e - s
            if ext < 0:
                ext = ext + 360
            self.canvas.create_arc(
                x - r,
                y - r,
                x + r,
                y + r,
                fill="#A0A0A0",
                outline="black",
                start=s - 90,
                extent=ext,
            )
            s = e
            e = (angle + self.piePieces[i][1]) * 180 / np.pi
            ext = e - s
            if ext < 0:
                ext = ext + 360
            self.canvas.create_arc(
                x - r,
                y - r,
                x + r,
                y + r,
                fill="#94FF99",
                outline="black",
                start=s - 90,
                extent=ext,
            )
            s = e
            e = angle * 180 / np.pi
            e = e + 360
            ext = e - s
            self.canvas.create_arc(
                x - r,
                y - r,
                x + r,
                y + r,
                fill="#FF9994",
                outline="black",
                start=s - 90,
                extent=ext,
            )

    def draw_pies_stacking_arbitraryFeatures(self):
        for i in range(0, len(self.pies)):
            # geometry of the circle
            angle = self.angles[i]
            y = self.pies[i][0]
            x = self.pies[i][1]
            r = self.pies[i][2]
            angle = self.angles[i]

            # initial Piece (does depend on somthing which is not in piePieces)
            s = angle * 180 / np.pi
            e = (angle + self.piePieces[i][0]) * 180 / np.pi
            ext = e - s
            if ext < 0:
                ext = ext + 360
            colorValue = int(200 - 0 * (150 / len(self.piePieces)))
            colorHEX = self.from_rgb((colorValue, colorValue, colorValue))
            self.canvas.create_arc(
                x - r,
                y - r,
                x + r,
                y + r,
                fill=colorHEX,
                outline="black",
                start=s - 90,
                extent=ext,
            )

            # middle Pieces
            for j in range(1, len(self.piePieces[i])):
                s = (angle + self.piePieces[i][j - 1]) * 180 / np.pi
                e = (angle + self.piePieces[i][j]) * 180 / np.pi
                ext = e - s
                if ext < 0:
                    ext = ext + 360
                colorValue = int(200 - j * (150 / (len(self.piePieces[i]))))
                colorHEX = self.from_rgb((colorValue, colorValue, colorValue))
                self.canvas.create_arc(
                    x - r,
                    y - r,
                    x + r,
                    y + r,
                    fill=colorHEX,
                    outline="black",
                    start=s - 90,
                    extent=ext,
                )

            # last Piece (does depend on somthing which is not in piePieces)
            s = (angle + self.piePieces[i][len(self.piePieces[i]) - 1]) * 180 / np.pi
            e = (angle * 180 / np.pi) + 360
            ext = e - s
            if ext < 0:
                ext = ext + 360
            colorValue = int(50)
            colorHEX = self.from_rgb((colorValue, colorValue, colorValue))
            self.canvas.create_arc(
                x - r,
                y - r,
                x + r,
                y + r,
                fill=colorHEX,
                outline="black",
                start=s - 90,
                extent=ext,
            )

    def draw_pie_stacking(self):
        if len(self.piePieces[0]) == 2:
            self.draw_pie_stacking_3Features()
        else:
            self.draw_pies_stacking_arbitraryFeatures()

    def data_algo_change(self, event):
        print("Change algorithm.")
        self.canvas.delete("all")
        self.apply_algorithm()
        # self.draw_circles()

    def create_widgets(self):
        # Top widgets
        self.frame = tk.Frame(self, self.parent)
        self.frame.grid(column=0, row=0, sticky="w")

        # Add algo timer
        self.timerlabel = tk.Label(self.frame, text="Timer...", fg="red")
        self.timerlabel.grid(column=2, row=1, sticky=tk.W + tk.E)

        self.timer_running_label = tk.Label(
            self.frame, text="Timer not running", bg="red", fg="white"
        )
        self.timer_running_label.grid(column=2, row=0, sticky=tk.W + tk.E)

        # Add objective value display
        self.objectivelabel = tk.Label(self.frame, text="Objective...", fg="red")
        self.objectivelabel.grid(column=3, row=1, sticky=tk.W + tk.E)

        self.objective_running_label = tk.Label(
            self.frame, text="No objective", bg="red", fg="white"
        )
        self.objective_running_label.grid(column=3, row=0, sticky=tk.W + tk.E)

        # Add canvas
        self.canvas = tk.Canvas(self, bg="white", width=1800, height=900)
        self.canvas.grid(column=0, row=1, sticky="nsew")

        # Combobox (to select algo, input data, cost function)
        self.datalabel = tk.Label(self.frame, text="Choose input data: ")
        self.datalabel.grid(column=0, row=0)

        self.data = ttk.Combobox(self.frame, width=50)
        self.data["values"] = ("test", "May", "June", "Random")
        self.data.current(1)
        self.data.grid(column=1, row=0)
        self.data.bind("<<ComboboxSelected>>", self.data_algo_change)
        self.data.bind("<<Configure>>", on_combo_configure)

        self.datalabel = tk.Label(self.frame, text="Choose algorithm :")
        self.datalabel.grid(column=0, row=1)

        self.algorithm = ttk.Combobox(self.frame, width=50)
        self.algorithm["values"] = (
            "Painter",  # 0
            "Random",  # 1
            "Pie stacking",  # 2
            "hawaiian stacking",  # 3
            "maxMinMinK Stacking (absolute)",  # 4
            "maxMinMinK Stacking (relative)",  # 5
            "maxMinSumK Stacking (absolute)",  # 6
            "maxMinSumK Stacking (relative)",  # 7
            "maxMinSumK Stacking (weighted)",  # 8
        )
        self.algorithm.current(0)
        self.algorithm.grid(column=1, row=1)
        self.algorithm.bind("<<ComboboxSelected>>", self.data_algo_change)
        self.algorithm.bind("<<Configure>>", on_combo_configure)

    # TODO: split this into {initialize, flush}

    def initialize_data(self):
        self._maps = {}
        self.circles = []
        self.pie_piece_sets = {}
        self.pies = []
        self._maps[0] = np.load("data/testData.npy", allow_pickle=True)
        self._maps[1] = np.load("data/testDataEndeMai.npy", allow_pickle=True)
        self._maps[2] = np.load("data/testDataJuni.npy", allow_pickle=True)

        self._worldmap = cv2.imread(
            "assets/test4.png"
        )  # Todo paint worldmap in background
        self._screen_height = len(self._worldmap)
        self._screen_width = len(self._worldmap[0])

        logging.info(self._screen_height)
        logging.info(self._screen_width)

    # This can be reworked but is held compatible to Philipp's
    # code due to early development state.
    def prepare_data(self):
        def latLongToPoint(lat, long, h, w):
            """Return (x,y) for lat, long inside a box."""
            lat = -lat + 90
            long = long + 180  # längengerade oben unten
            y = lat / 180
            x = long / 360
            x = int(x * w)
            y = int(y * h)
            return x, y

        def calculatePointOnCircle(c, angle):
            """Return pos in interval (0,1) on circumference of circle."""
            cosangle = np.cos(angle)
            sinangle = np.sin(angle)
            return cosangle * c[2] + c[0], sinangle * c[2] + c[1]

        # structure: loc,loc,lat,long,conf,dead,recovered

        # Prepare npy or create circles
        # TODO: Talk to Philip about this
        for i in range(3):

            # flush previous set of circles
            circles = []
            pies = []
            piePieces = []
            my_data = []
            maximum_second = -1
            maximum = -1
            maximum_2 = -1

            my_worldmap = self._maps[i]

            for case in my_worldmap:
                tmp = []
                for slot in case:
                    tmp.append(slot)
                my_data.append(tmp)

            for case in list(my_data):
                if case[4] < 5000:
                    my_data.remove(case)

            for case in my_data:
                if case[4] < 1:
                    tmp = 1
                else:
                    tmp = case[4]
                if tmp > maximum:
                    maximum_second = maximum
                    maximum = tmp
                    maximum_2 = np.log(4 + case[4] * 100 / maximum_second)

            for case in my_data:
                lat = case[2]
                long = case[3]
                x, y = latLongToPoint(
                    lat, long, self._screen_height, self._screen_width
                )
                case[4] = case[4] + 5
                case[5] = case[5] + 5
                case[6] = case[6] + 5

                if case[4] < case[6]:
                    continue

                if case[4] == 0:
                    conf = 1
                else:
                    conf = np.log(4 + case[4] * 100 / maximum_second)

                if case[5] == 0 or math.isnan(case[5]):
                    dead = 1
                else:
                    dead = case[5]

                if case[6] == 0 or math.isnan(case[6]):
                    rec = 1
                else:
                    rec = case[6]

                conf = 125 * conf / maximum_2
                dead = np.sqrt(conf * conf * (dead / case[4]))
                rec = np.sqrt(conf * conf * (rec / case[4]) + dead * dead)
                r = conf
                rprime2 = dead
                rprime1 = rec
                rprime0 = 1

                # appending circles with pie radii
                circles.append(
                    [int(y), int(x), int(r), int(rprime1), int(rprime2)]
                )  # its important that its y,x i'm sorry :(
                pies.append(
                    [int(y), int(x), int(r)]
                )  # its important that its y,x i'm sorry :(

                # appending pie pieces
                a0 = rprime0 * rprime0
                a1 = rprime1 * rprime1
                a2 = rprime2 * rprime2
                a = r * r
                p1 = (case[5] / case[4]) * 2 * np.pi
                p2 = (((case[6] / case[4])) * 2 * np.pi) + p1
                piePieces.append([p1, p2])

                # TODO: Think about datastructure for pies and piePieces = probably a class
                self.data_sets[i] = circles
                self.pie_piece_sets[i] = piePieces
                self.pie_sets[i] = pies

            # Generate random set
            circles = []
            MAX_RADIUS = 100
            for _ in range(100):
                x = random.randint(0, self._screen_width - MAX_RADIUS)
                y = random.randint(0, self._screen_height - MAX_RADIUS)
                r = random.randint(1, MAX_RADIUS)
                circles.append([y, x, r])  # its important that its y,x i'm sorry :(

            self.data_sets[3] = circles
            logging.debug(self.circles)


class PaintingProgramPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller

        self.old_x = None
        self.old_y = None

        self.create_widgets()

        # Single circle
        self.canvas.create_circle(150, 40, 20, fill="#bbb", outline="")

        # Arcs
        self.canvas.create_circle(100, 120, 50, fill="blue", outline="#DDD", width=4)
        self.canvas.create_circle_arc(
            100, 120, 48, fill="green", outline="", start=45, end=140
        )
        self.canvas.create_circle_arc(
            100, 120, 48, fill="green", outline="", start=275, end=305
        )
        self.canvas.create_circle_arc(
            100,
            120,
            45,
            style="arc",
            outline="white",
            width=6,
            start=270 - 25,
            end=270 + 25,
        )

    def create_widgets(self):
        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", self.reset)

        self.symbolic_button = tk.Button(
            self,
            text="Go to Symbolic Maps Page",
            command=lambda: self.controller.show_frame(SymbolicMapsPage),
        )
        self.symbolic_button.pack(side="bottom")

    def paint(self, event):
        if self.old_x and self.old_y:
            self.canvas.create_line(
                self.old_x,
                self.old_y,
                event.x,
                event.y,
                width=2,
                fill="black",
                capstyle=tk.ROUND,
                smooth=tk.TRUE,
                splinesteps=36,
            )
        self.old_x = event.x
        self.old_y = event.y

    def reset(self, event):
        self.old_x, self.old_y = None, None


class MatplotlibPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        self.label = tk.Label(self, text="Matplotlib... plotting a simple data series")
        self.label.pack(side="top")

        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.subfig = self.fig.add_subplot(111)
        self.subfig.plot([1, 2, 3, 4, 5, 6], [1, 3, 2, 5, 3, 6])

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        # self.canvas._tkcanvas.pack(side="top", fill="both", expand=True)


class AboutPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        self.label = tk.Label(
            self,
            text="Some info about the algos, complexity, us, maybe link to paper...",
        )
        self.label.pack(side="top")

        self.symbolic_button = tk.Button(
            self,
            text="Go to Symbolic Maps Page",
            command=lambda: self.controller.show_frame(SymbolicMapsPage),
        )
        self.symbolic_button.pack(side="bottom")


def main():
    """The main function of the geomlab."""
    # Create application
    app = GeomLabApp()

    # Run application
    app.mainloop()


# TODO: Convert solution drawings for pies and movable circles
