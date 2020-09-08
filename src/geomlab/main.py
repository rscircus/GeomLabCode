import matplotlib
import random
import logging
import datetime
import numpy as np
import math

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont

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
        self.square_sets = {}
        self.circles = []
        self.pies = []
        self.piePieces = []
        self.squares = []
        self.circlesToDraw = []  # for nested disks different structure
        self.numberOfFeatures = 0  # numberOffeatures eg, rec,dead,rest equal 3
        self.angles = []

        # geomDataGeneration (should be adapted by the user)
        self.maximalSize = 50
        self.scalingFactor = 200
        self.lowerBoundCases = 5000

        self.timer_running = False
        self.counter = 123456
        self.timer_start_timestamp = datetime.datetime.now()

        # Prepare inputs
        self.initialize_data()
        self.prepare_data()

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
        self.squares = self.square_sets[self.data.current()]

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
            self.objective_list.insert(tk.END, st.utilitysNestedDisks(self.circles))

        elif algo == 1:
            random.shuffle(self.circles)
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
            self.objective_list.insert(tk.END, st.utilitysNestedDisks(self.circles))

        elif algo == 2:
            self.pies, self.piePieces, self.angles = st.algorithmPieChartsStacking(
                self.pies, self.piePieces
            )
            self.objective_list.insert(tk.END, st.utilitysPieCharts(self.circles.self.piePieces, self.angles))

        elif algo == 3:
            self.circlesToDraw = st.algorithmHawaiianStacking(self.circles)
            self.numberOfFeatures = len(self.circles[0]) - 2
            self.objective_list.insert(tk.END, st.utilitysHawaiian(self.circles, -1)) # TODO: number of nestings? like 2?

        elif algo == 4:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinMin(
                self.circles, "absolute"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
            self.objective_list.insert(tk.END, st.utilitysNestedDisks(self.circles))

        elif algo == 5:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinMin(
                self.circles, "relative"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
            self.objective_list.insert(tk.END, st.utilitysNestedDisks(self.circles))

        elif algo == 6:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinSum(
                self.circles, "relative"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
            self.objective_list.insert(tk.END, st.utilitysNestedDisks(self.circles))

        elif algo == 7:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinSum(
                self.circles, "relative"
            )
            self.circlesToDraw, self.numberOfFeatures = st.formatChangeNestedDisks(
                self.circles
            )
            self.objective_list.insert(tk.END, st.utilitysNestedDisks(self.circles))

        elif algo == 8:
            self.squares, m1, m2, m3 = st.algorithmSquaresStacking(self.squares)
            # TODO square utility is missing


        else:
            logging.critical("You shouldn't see me.")

        # Timer end
        self.timer_stop()

        # Objective update
        # TODO: Leaving that as this has to adapt after the objective_list intro
        #if objective_value != -1:
        self.objective_running_label["text"] = "Objective"
        self.objectivelabel["text"] = str(objective_value)
        self.objective_running_label["bg"] = "green"
#        else:
#            self.objective_running_label["bg"] = "red"
#            self.objective_running_label["text"] = "Objective"
#            self.objectivelabel["text"] = "N/A"

        # Utilities
        #self.objective_list.insert(tk.END, "sth")


        # Draw

        if not algo in [2, 8]:
            self.draw_subcircle_stacking()
        if algo == 2:
            self.draw_pie_stacking()

        if algo == 8:
            self.drawSquareSolution()

    def draw_circles(self):

        for c in self.circles:
            # x, y ,r
            self.canvas.create_circle(c[0], c[1], c[2], fill="#bbb", outline="#000")

    def from_rgb(self, rgb):
        """translates an rgb tuple of int to a tkinter friendly color code"""
        return "#%02x%02x%02x" % rgb

    def drawSquareSolution(self):
        for i in range(0, len(self.squares)):
            self.drawSquare(self.squares[i])

    def drawSquare(self, square):

        color1PIL = "#FF9994"
        color2PIL = "#94FF99"
        color3PIL = "#A0A0A0"

        tmp = [0, 0]
        tmp[1] = square[4][0] + (square[3][0] - square[0][0])
        tmp[0] = square[4][1] + (square[3][1] - square[0][1])
        square1_vertices = (
            (square[0][1], square[0][0]),
            (square[4][1], square[4][0]),
            (tmp[0], tmp[1]),
            (square[3][1], square[3][0]),
        )

        tmp2 = [0, 0]
        tmp2[1] = square[4][0] + (square[5][0] - square[1][0])
        tmp2[0] = square[4][1] + (square[5][1] - square[1][1])
        square2_vertices = (
            (square[4][1], square[4][0]),
            (square[1][1], square[1][0]),
            (square[5][1], square[5][0]),
            (tmp2[0], tmp2[1]),
        )

        square3_vertices = (
            (tmp2[0], tmp2[1]),
            (square[5][1], square[5][0]),
            (square[2][1], square[2][0]),
            (tmp[0], tmp[1]),
        )

        color1 = ""
        color2 = ""
        color3 = ""
        if square[4][2] == "dead":
            color1 = color3PIL
        else:
            if square[4][2] == "rec":
                color1 = color2PIL
            else:
                color1 = color1PIL

        if square[5][2] == "dead":
            color2 = color3PIL
        else:
            if square[5][2] == "rec":
                color2 = color2PIL
            else:
                color2 = color1PIL
        if square[7] == "dead":
            color3 = color3PIL
        else:
            if square[7] == "rec":
                color3 = color2PIL
            else:
                color3 = color1PIL

        self.canvas.create_polygon(
            square1_vertices, outline="#000", fill=color1, width=2
        )
        self.canvas.create_polygon(
            square2_vertices, outline="#000", fill=color2, width=2
        )
        self.canvas.create_polygon(
            square3_vertices, outline="#000", fill=color3, width=2
        )

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
        self.canvas.create_image(0, 0, image=self.world_image, anchor="nw")
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

        # Add cost/objective value display
        self.objectivelabel = tk.Label(self.frame, text="Objective...", fg="red")
        self.objectivelabel.grid(column=3, row=1, sticky=tk.W + tk.E)

        self.objective_running_label = tk.Label(
            self.frame, text="No objective", bg="red", fg="white"
        )
        self.objective_running_label.grid(column=3, row=0, sticky=tk.W + tk.E)

        # Simply display all objectives there are
        self.objective_list = tk.Listbox(self.frame)
        self.olist_scrollbar = tk.Scrollbar(self.frame)

        self.objective_list.config(yscrollcommand = self.olist_scrollbar.set, relief=tk.SUNKEN, border=2, height=3, width=200)
        self.olist_scrollbar.config(command = self.objective_list.yview)
        self.olist_scrollbar.grid(row=0, column=5, sticky='ns', rowspan=3)
        self.objective_list.grid(row=0, column=4, sticky='w', rowspan=3)

        self.objective_list.insert(tk.END, "minSum relPerc absPerc minRelNonZero minAbsNonZero coveredCircles")

        # Add canvas
        self.canvas = tk.Canvas(self, bg="white", width=1800, height=900)
        self.canvas.grid(column=0, row=1, sticky="nsew")

        # Input data
        self.datalabel = tk.Label(self.frame, text="Choose input data: ")
        self.datalabel.grid(column=0, row=0)

        self.data = ttk.Combobox(self.frame, width=50)

        # Append all available covid data
        self.data["values"] = tuple(cl.dates_list)
        self.data.current(193) # 193 is a good dataset
        print(self.data.current())
        self.data.grid(column=1, row=0)
        self.data.bind("<<ComboboxSelected>>", self.data_algo_change)
        self.data.bind("<<Configure>>", on_combo_configure)

        # Algorithm
        self.algolabel = tk.Label(self.frame, text="Choose algorithm :")
        self.algolabel.grid(column=0, row=1)

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
            "Squares",  # 8
        )
        self.algorithm.current(0)
        self.algorithm.grid(column=1, row=1)
        self.algorithm.bind("<<ComboboxSelected>>", self.data_algo_change)
        self.algorithm.bind("<<Configure>>", on_combo_configure)

        # Symbolic Maps selector
        self.symbolic_mapslabel = tk.Label(self.frame, text="Choose symbolic maps: ")
        self.symbolic_mapslabel.grid(column=0, row=2)
        self.symbolic_maps = ttk.Combobox(self.frame, width=50)
        self.symbolic_maps["values"] = (
            "Plain circles",  # 0
            "Concentric circles",  # 1
            "Pies",  # 2
            "Squares)",  # 3
        )
        self.symbolic_maps.current(1) # Concentric circles as default
        self.symbolic_maps.grid(column=1, row=2)
        self.symbolic_maps.bind("<<ComboboxSelected>>", self.data_algo_change)
        self.symbolic_maps.bind("<<Configure>>", on_combo_configure)

    # TODO: split this into {initialize, flush}

    def initialize_data(self):
        self._maps = {}
        self.circles = []
        self.pie_piece_sets = {}
        self.pies = []

        # Geometry by background
        self.world_image = tk.PhotoImage(file=r"assets/test4.png")
        self.canvas.create_image(0, 0, image=self.world_image, anchor="nw")

        self.screen_height = self.world_image.height()
        self.screen_width = self.world_image.width()

        logging.info(self.screen_height)
        logging.info(self.screen_width)


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

        def changeStructureFromPanda(df):
            myData = []

            for lat, lon, conf, dead in zip(
                df["latitude"], df["longitude"], df["confirmed_cases"], df["deaths"]
            ):
                tmp = [0, 0, lat, lon, conf + 1, dead + 1, 1 + (conf - dead) / 2]
                myData.append(tmp)

            return myData

        def createOneSquare(size, case, heightOfImage, widthOfImage):
            square = []
            x, y = latLongToPoint(case[2], case[3], heightOfImage, widthOfImage)

            # corners and center of the square
            center = [y, x]
            x1 = [y + size, x - size]
            x2 = [y + size, x + size]
            x3 = [y - size, x + size]

            # special points and their represented "type"
            x4 = [y - size, x - size]
            x5 = [0, 0, " "]
            x6 = [0, 0, " "]
            last = [" "]

            # data
            allCases = case[4]
            dead = case[5]
            rec = case[6]
            rest = case[4] - dead - rec

            # checks which small square corresponds to which  "type"
            if dead >= rec and dead >= rest:
                perc = dead / allCases
                x5[0] = x1[0] + (x2[0] - x1[0]) * perc
                x5[1] = x1[1] + (x2[1] - x1[1]) * perc
                x5[2] = "dead"
                if rec > rest:
                    perc = rec / (rec + rest)
                    x6[0] = x2[0] + (x3[0] - x2[0]) * perc
                    x6[1] = x2[1] + (x3[1] - x2[1]) * perc
                    x6[2] = "rec"
                    last = "rest"
                else:
                    perc = rest / (rec + rest)
                    x6[0] = x2[0] + (x3[0] - x2[0]) * perc
                    x6[1] = x2[1] + (x3[1] - x2[1]) * perc
                    x6[2] = "rest"
                    last = "rec"

                square.append(x1)
                square.append(x2)
                square.append(x3)
                square.append(x4)
                square.append(x5)
                square.append(x6)
                square.append(center)
                square.append(last)
                return square

            if rec >= dead and rec >= rest:
                perc = rec / allCases
                x5[0] = x1[0] + (x2[0] - x1[0]) * perc
                x5[1] = x1[1] + (x2[1] - x1[1]) * perc
                x5[2] = "rec"
                if rest > dead:
                    perc = rest / (rest + dead)
                    x6[0] = x2[0] + (x3[0] - x2[0]) * perc
                    x6[1] = x2[1] + (x3[1] - x2[1]) * perc
                    x6[2] = "rest"
                    last = "dead"
                else:
                    perc = dead / (rest + dead)
                    x6[0] = x2[0] + (x3[0] - x2[0]) * perc
                    x6[1] = x2[1] + (x3[1] - x2[1]) * perc
                    x6[2] = "dead"
                    last = "rest"
                square.append(x1)
                square.append(x2)
                square.append(x3)
                square.append(x4)
                square.append(x5)
                square.append(x6)
                square.append(center)
                square.append(last)
                return square

            if rest >= dead and rest >= rec:
                perc = rest / allCases
                x5[0] = x1[0] + (x2[0] - x1[0]) * perc
                x5[1] = x1[1] + (x2[1] - x1[1]) * perc
                x5[2] = "rest"
                if rec > dead:
                    perc = rec / (rec + dead)
                    x6[0] = x2[0] + (x3[0] - x2[0]) * perc
                    x6[1] = x2[1] + (x3[1] - x2[1]) * perc
                    x6[2] = "rec"
                    last = "dead"
                else:
                    perc = dead / (rec + dead)
                    x6[0] = x2[0] + (x3[0] - x2[0]) * perc
                    x6[1] = x2[1] + (x3[1] - x2[1]) * perc
                    x6[2] = "dead"
                    last = "rec"

                square.append(x1)
                square.append(x2)
                square.append(x3)
                square.append(x4)
                square.append(x5)
                square.append(x6)
                square.append(center)
                square.append(last)
                return square

        def generateGeomData(myData, index):
            # calculate secondminimum and prepare scaling of the circles

            for case in list(my_data):
                if case[4] < self.lowerBoundCases:
                    my_data.remove(case)

            maximum = 1
            maximumsecond = 1
            for case in myData:
                if case[4] < 1:
                    tmp = 1
                else:
                    tmp = case[4]
                if tmp > maximum:
                    maximumsecond = maximum
                    maximum = tmp
            multiplicativeconstant = self.maximalSize / np.log(1 + self.scalingFactor)

            circles = []
            pies = []
            piePieces = []
            squares = []

            # generating circles,pies and squares
            for case in myData:
                lat = case[2]
                long = case[3]
                x, y = latLongToPoint(
                    lat, long, self.screen_height, self.screen_width
                )

                # making sure data makes sense
                if case[4] < case[6]:
                    continue
                if case[4] == 0:
                    conf = 1
                else:
                    conf = case[4]
                if case[5] == 0 or math.isnan(case[5]):
                    dead = 1
                else:
                    dead = case[5]
                if case[6] == 0 or math.isnan(case[6]):
                    rec = 1
                else:
                    rec = case[6]

                # nestedCircles
                confAdjusted = multiplicativeconstant * np.log(
                    1 + self.scalingFactor * conf / maximumsecond
                )
                deadAdjusted = multiplicativeconstant * np.log(
                    1 + self.scalingFactor * dead / maximumsecond
                )
                recAdjusted = multiplicativeconstant * np.log(
                    1 + self.scalingFactor * (rec + dead) / maximumsecond
                )

                r = confAdjusted
                rprime2 = deadAdjusted
                rprime1 = recAdjusted

                circles.append([int(y), int(x), int(r), int(rprime1), int(rprime2)])

                # pies
                pies.append([int(y), int(x), int(r)])
                p1 = (case[5] / case[4]) * 2 * np.pi
                p2 = (((case[6] / case[4])) * 2 * np.pi) + p1
                piePieces.append([p1, p2])

                # squares
                tmpSquare = createOneSquare(
                    r, case, self.screen_height, self.screen_width
                )
                squares.append(tmpSquare)

            # TODO: Catch errors on data acquisition level?
            if len(circles) == 0:
                print(f"Data quality issues: Circles array is empty for dataset no. {index} ...")
                return

            self.data_sets[index] = circles
            self.pie_piece_sets[index] = piePieces
            self.pie_sets[index] = pies
            self.square_sets[index] = squares

        # structure: loc,loc,lat,long,conf,dead,recovered

        # Prepare npy or create circles
        for i in range(3):

            # flush previous set of circles
            my_data = []

            cur_data_set_idx = len(self.data_sets)

            # append downloaded datasets
            for _, df in cl.cases_by_date.items():

                # generate geomData
                my_data = changeStructureFromPanda(df)
                generateGeomData(my_data, cur_data_set_idx)
                cur_data_set_idx = len(self.data_sets)

            len(self.pie_piece_sets)

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

        # Example for rectangle
        # args: (x1, y1, x2, y2, **kwargs)
        self.canvas.create_rectangle(350, 200, 400, 250, fill="red")

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
