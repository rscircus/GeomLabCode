import matplotlib
import random
import logging
import time
import datetime
import numpy as np
import math
import copy
import csv

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
    """Private function to create circle from TK's create_oval function."""
    return self.create_oval(x - r, y - r, x + r, y + r, **kwargs)


tk.Canvas.create_circle = _create_circle

# Expand TK's oval to support our pies:
def _create_circle_arc(self, x, y, r, **kwargs):
    """Private function to create circle arc from TK's create_arc function."""
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


# Config object


class Config:
    """This object contains the configuration of the project."""

    def __init__(self):

        # geomDataGeneration (should be adapted by the user)
        # default values
        self.maximalSize = 40
        self.scalingFactor = 500
        self.lowerBoundCases = 10000


# Main Window
class GeomLabApp(tk.Tk):
    """Extends tk.Tk to GeomLabApp with all necessary frames. Manages the window."""
    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)

        # Configure self
        self.geometry("1810x2000")
        self.title("Symbolic Maps")

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Symbolic Maps", command=lambda: self.show_frame(SymbolMapsPage)
        )
        file_menu.add_command(
            label="Settings Page",
            command=lambda: self.show_frame(SettingsPage),
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

        # Create config
        self.symbolic_config = Config()

        # Create "pages"
        self.frames = {}

        # Create
        for page in (
                SymbolMapsPage,
                SettingsPage,
                PaintingProgramPage,
                MatplotlibPage,
                AboutPage,
        ):
            frame = page(container, self)
            frame.grid(row=0, column=0, sticky="nswe")
            self.frames[page] = frame

        # Add a second frame of type SymbolicMapsPage
        scnd_container = tk.Frame(self)
        scnd_container.pack(side="top", fill="both", expand=True)
        scnd_frame = SymbolMapsPage(scnd_container, self)
        scnd_frame.grid(row=0, column=1, sticky="nswe")

        # Display page in first frame
        self.show_frame(SymbolMapsPage)

    def show_frame(self, container):
        """Show a specific frame in the window."""

        frame = self.frames[container]
        frame.tkraise()


# Frames
class SymbolMapsPage(tk.Frame):
    """Frmae for the visualization of the symbol maps using COVID-19 data."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.csv_filename = (
            "./" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_utilities.csv"
        )
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
        self.circles_for_drawing = []  # for nested disks different structure
        self.squares_for_drawing = []  
        self.numberOfFeatures = 0  # numberOffeatures eg, rec,dead,rest equal 3
        self.angles = []

        self.timer_running = False
        self.counter = 123456
        self.timer_start_timestamp = datetime.datetime.now()

        # Prepare inputs
        self.initialize_data()
        self.prepare_data()

        # Write explanation line into csv
        with open(self.csv_filename, mode="a") as utility_file:
            utility_writer = csv.writer(
                utility_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
            )
            utility_writer.writerow(
                [
                    "Timestamp",
                    "Unixtime (secs)",
                    "Algorithm",
                    "covered",
                    "minVis(r)/minDist",
                    "minVis(a)/minDistAvg",
                    "min1Gl/maxDistAvg",
                    "avgRel",
                    "abs%",
                ]
            )

        # Execute symbolic algo
        self.apply_algorithm()

    def flush_everything(self):
        self.pie_sets = {}
        self.pie_piece_sets = {}
        self.data_sets = {}
        self.square_sets = {}
        self.circles = []
        self.pies = []
        self.piePieces = []
        self.squares = []
        self.circles_for_drawing = []
        self.squares_for_drawing = []
        self.numberOfFeatures = 0
        self.angles = []

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
        self.circles = self.data_sets[self.data.current()]
        self.piePieces = self.pie_piece_sets[self.data.current()]
        self.pies = self.pie_sets[self.data.current()]
        self.angles = [0] * len(self.pies)
        self.squares = self.square_sets[self.data.current()]

        print("Current data set:")
        print(self.data.current())
        print(f"Number of circles: {len(self.circles)}")
        print(f"Number of pies: {len(self.pies)}")
        print(f"Number of squares: {len(self.squares)}")

        algo = self.algorithm.current()

        """
            "centered disks | random",  # 0
            "centered disks | LeftToRight",  # 1
            "centered disks | RightToLeft",  # 2
            "centered disks | Painter",  # 3
            "centered disks | MinMin-Stacking (abs)",  # 4
            "centered disks | MinMin-Stacking (rel)",  # 5
            "centered disks | MinSum-Stacking (abs)",  # 6
            "centered disks | MinSum-Stacking (rel)",  # 7
            "hawaiian disks | random",  # 8
            "hawaiian disks | LeftToRight",  # 9
            "hawaiian disks | RightToLeft",  # 10
            "hawaiian disks | Painter",  # 11
            "hawaiian disks | our Stacking",  # 12
            "pie charts | random",  # 13
            "pie charts | LeftToRight",  # 14
            "pie charts | RightToLeft",  # 15
            "pie charts | Painter",  # 16
            "pie charts | our Stacking",  # 17
            "squares | Painter+heuristic" #18
            "squares | Painter+random rotations" #19
            "squares | random Stacking+heuristic rotations" #20
            "squares | random Stacking+heuristic rotations" #21
            "squares | our Stacking" #22
        """

        # Timer start
        self.timer_start()

        # TODO: Assuming objective values are positive
        objective_value = -1

        self.objective_list.delete(1)

        if algo == 0:
            self.circles = st.algorithmNestedDisksRandom(self.circles)
            (
                self.circles_for_drawing,
                self.numberOfFeatures,
            ) = st.formatChangeNestedDisks(self.circles)
            self.objective_list.insert(1, st.utilitysNestedDisks(self.circles))

        elif algo == 1:
            self.circles = st.algorithmNestedDisksLeftToRight(self.circles)
            (
                self.circles_for_drawing,
                self.numberOfFeatures,
            ) = st.formatChangeNestedDisks(self.circles)
            self.objective_list.insert(1, st.utilitysNestedDisks(self.circles))

        elif algo == 2:
            self.circles = st.algorithmNestedDisksRightToLeft(self.circles)
            (
                self.circles_for_drawing,
                self.numberOfFeatures,
            ) = st.formatChangeNestedDisks(self.circles)
            self.objective_list.insert(1, st.utilitysNestedDisks(self.circles))

        elif algo == 3:
            self.circles = st.algorithmNestedDisksPainter(self.circles)
            (
                self.circles_for_drawing,
                self.numberOfFeatures,
            ) = st.formatChangeNestedDisks(self.circles)
            self.objective_list.insert(1, st.utilitysNestedDisks(self.circles))

        elif algo == 4:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinMin(
                self.circles, "absolute"
            )
            (
                self.circles_for_drawing,
                self.numberOfFeatures,
            ) = st.formatChangeNestedDisks(self.circles)
            self.objective_list.insert(1, st.utilitysNestedDisks(self.circles))

        elif algo == 5:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinMin(
                self.circles, "relative"
            )
            (
                self.circles_for_drawing,
                self.numberOfFeatures,
            ) = st.formatChangeNestedDisks(self.circles)
            self.objective_list.insert(1, st.utilitysNestedDisks(self.circles))

        elif algo == 6:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinSum(
                self.circles, "absolute"
            )
            (
                self.circles_for_drawing,
                self.numberOfFeatures,
            ) = st.formatChangeNestedDisks(self.circles)
            self.objective_list.insert(1, st.utilitysNestedDisks(self.circles))

        elif algo == 7:
            self.circles, objective_value = st.algorithmNestedDisksStackingMinSum(
                self.circles, "relative"
            )
            (
                self.circles_for_drawing,
                self.numberOfFeatures,
            ) = st.formatChangeNestedDisks(self.circles)
            self.objective_list.insert(1, st.utilitysNestedDisks(self.circles))

        elif algo == 8:
            self.circles_for_drawing = st.algorithmHawaiianRandom(self.circles)
            self.numberOfFeatures = len(self.circles[0]) - 2
            self.objective_list.insert(
                1, st.utilitysHawaiian(self.circles_for_drawing, 3)
            )

        elif algo == 9:
            self.circles_for_drawing = st.algorithmHawaiianLeftToRight(self.circles)
            self.numberOfFeatures = len(self.circles[0]) - 2
            self.objective_list.insert(
                1, st.utilitysHawaiian(self.circles_for_drawing, 3)
            )
        elif algo == 10:
            self.circles_for_drawing = st.algorithmHawaiianRightToLeft(self.circles)
            self.numberOfFeatures = len(self.circles[0]) - 2
            self.objective_list.insert(
                1, st.utilitysHawaiian(self.circles_for_drawing, 3)
            )

        elif algo == 11:
            self.circles_for_drawing = st.algorithmHawaiianPainter(self.circles)
            self.numberOfFeatures = len(self.circles[0]) - 2
            self.objective_list.insert(
                1, st.utilitysHawaiian(self.circles_for_drawing, 3)
            )

        elif algo == 12:
            self.circles_for_drawing = st.algorithmHawaiianStacking(self.circles)
            self.numberOfFeatures = len(self.circles[0]) - 2
            self.objective_list.insert(
                1, st.utilitysHawaiian(self.circles_for_drawing, 3)
            )

        elif algo == 13:
            self.pies, self.piePieces, self.angles = st.algorithmPieChartsRandom(
                self.pies, self.piePieces
            )
            self.objective_list.insert(
                1, st.utilitysPieCharts(self.pies, self.piePieces, self.angles)
            )

        elif algo == 14:
            self.pies, self.piePieces, self.angles = st.algorithmPieChartsPainterRandom(
                self.pies, self.piePieces
            )
            self.objective_list.insert(
                1, st.utilitysPieCharts(self.pies, self.piePieces, self.angles)
            )

        elif algo == 15:
            self.pies, self.piePieces, self.angles = st.algorithmPieChartsRightToLeft(
                self.pies, self.piePieces
            )
            self.objective_list.insert(
                1, st.utilitysPieCharts(self.pies, self.piePieces, self.angles)
            )

        elif algo == 16:
            self.pies, self.piePieces, self.angles = st.algorithmPieChartsPainter(
                self.pies, self.piePieces
            )
            self.objective_list.insert(
                1, st.utilitysPieCharts(self.pies, self.piePieces, self.angles)
            )

        elif algo == 17:
            self.pies, self.piePieces, self.angles = st.algorithmPieChartsStacking(
                self.pies, self.piePieces
            )
            self.objective_list.insert(
                1, st.utilitysPieCharts(self.pies, self.piePieces, self.angles)
            )

        elif algo == 18:
            self.squares_for_drawing = st.algorithmHeuristicPainterSquareStacking(
                copy.deepcopy(self.squares)
            )
            self.objective_list.insert(
                1, st.utilitysSquares(self.squares_for_drawing)
            )
            print("square utilitys: ", st.utilitysSquares(self.squares_for_drawing))

        elif algo == 19:
            self.squares_for_drawing = st.algorithmRandomPainterSquareStacking(
                copy.deepcopy(self.squares)
            )
            self.objective_list.insert(
                1, st.utilitysSquares(self.squares_for_drawing)
            )
            print("square utilitys: ", st.utilitysSquares(self.squares_for_drawing))

        elif algo == 20:
            self.squares_for_drawing = st.algorithmHeuristicRandomSquareStacking(
                copy.deepcopy(self.squares)
            )
            self.objective_list.insert(
                1, st.utilitysSquares(self.squares_for_drawing)
            )
            print("square utilitys: ", st.utilitysSquares(self.squares_for_drawing))

        elif algo == 21:
            self.squares_for_drawing = st.algorithmCompletelyRandomSquareStacking(
                copy.deepcopy(self.squares)
            )
            self.objective_list.insert(
                1, st.utilitysSquares(self.squares_for_drawing)
            )
            print("square utilitys: ", st.utilitysSquares(self.squares_for_drawing))

        elif algo == 22:
            self.squares_for_drawing, _, _, _ = st.algorithmSquaresStacking(
                copy.deepcopy(self.squares)
            )
            self.objective_list.insert(
                1, st.utilitysSquares(self.squares_for_drawing)
            )
            print("square utilitys: ", st.utilitysSquares(self.squares_for_drawing))
        else:
            logging.critical("Algorithm not present. You shouldn't see me.")

        # Write results in to csv
        #
        # As the results are written into the 2nd line of objective_list, they
        # are picked up there with an error check.
        if self.objective_list.size() == 2:
            print(f"Appending to {self.csv_filename}")
            with open(self.csv_filename, mode="a") as utility_file:
                utility_writer = csv.writer(
                    utility_file,
                    delimiter=",",
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL,
                )
                obj = self.objective_list.get(1, 1)
                obj_list = list(obj[0])
                full_data = [
                    datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
                    time.mktime(datetime.datetime.now().timetuple()),
                    self.algorithm.get(),
                ]
                full_data.extend(obj_list)
                utility_writer.writerow(full_data)
        else:
            logging.critical("Some utility function is still missing!")

        # Timer end
        self.timer_stop()

        # Objective update
        # TODO: Leaving that as this has to adapt after the objective_list intro
        if objective_value != -1:
            self.objective_running_label["text"] = "Num. objective"
            self.objectivelabel["text"] = str(objective_value)
            self.objective_running_label["bg"] = "green"
        else:
            self.objective_running_label["bg"] = "red"
            self.objective_running_label["text"] = "Objective"
            self.objectivelabel["text"] = "N/A"

        # Utilities
        # self.objective_list.insert(1, "sth")

        # Draw

        if algo in range(0, 13):
            self.draw_subcircle_stacking()
        if algo in range(13, 18):
            self.draw_pie_stacking()

        if algo in range(18, 23):
            self.drawSquareSolution()


    def draw_circles(self):
        for c in self.circles:
            # x, y ,r
            self.canvas.create_circle(c[0], c[1], c[2], fill="#bbb", outline="#000")

    def from_rgb(self, rgb):
        """translates an rgb tuple of int to a tkinter friendly color code."""
        return "#%02x%02x%02x" % rgb

    def drawSquareSolution(self):
        for i in range(0, len(self.squares_for_drawing)):
            self.drawSquare(self.squares_for_drawing[i])

    def drawSquare(self, square):

        color1PIL = "#FF9994"
        color2PIL = "#94FF99"
        color3PIL = "#A0A0A0"

        tmp = [0, 0]
        tmp[1] = square[4][0] + (square[3][0] - square[0][0])
        tmp[0] = square[4][1] + (square[3][1] - square[0][1])
        
        #tuple for all of the mosaic parts of the square
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

        #coloring the squares in the correct colors
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
        for c in self.circles_for_drawing:
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
        for c in self.circles_for_drawing:
            y = c[0]
            x = c[1]
            r = c[2]
            #colors are given by different greyvalues
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
            #first arc from imaginary zero line to the first line
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
            #inner piece
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
            #piece from the last line to the imaginary 0 line
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

            # last Piece (does depend on something which is not in piePieces)
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

        self.objective_list.config(
            yscrollcommand=self.olist_scrollbar.set,
            relief=tk.SUNKEN,
            border=2,
            height=3,
            width=115,
        )
        self.olist_scrollbar.config(command=self.objective_list.yview)
        self.olist_scrollbar.grid(row=0, column=5, sticky="ns", rowspan=3)
        self.objective_list.grid(row=0, column=4, sticky="w", rowspan=3)

        self.objective_list.insert(
            tk.END, "covered | minVis(r)/minDist | minVis(a)/minDistAvg | min1Gl/maxDistAvg | avgRel | abs%"
        )
        self.objective_list.insert(tk.END, "--- no run, yet ---")

        # Add canvas
        self.canvas = tk.Canvas(self, bg="white", width=1800, height=900)
        self.canvas.grid(column=0, row=1, sticky="nsew")

        # Input data
        self.datalabel = tk.Label(self.frame, text="Choose input data: ")
        self.datalabel.grid(column=0, row=0)

        self.data = ttk.Combobox(self.frame, width=50)

        # Append all available covid data
        for i in range(0,11):
            cl.dates_list[len(cl.dates_list)-i-1]="random {}".format(10-i)
        
        
        self.data["values"] = tuple(cl.dates_list)
        self.data.current(193)  # 193 is a good dataset
        print(self.data.current())
        self.data.grid(column=1, row=0)
        self.data.bind("<<ComboboxSelected>>", self.data_algo_change)
        self.data.bind("<<Configure>>", on_combo_configure)

        # Algorithm
        self.algolabel = tk.Label(self.frame, text="Choose algorithm :")
        self.algolabel.grid(column=0, row=1)

        self.algorithm = ttk.Combobox(self.frame, width=50)
        self.algorithm["values"] = (
            "centered disks | random",  # 0
            "centered disks | LeftToRight",  # 1
            "centered disks | RightToLeft",  # 2
            "centered disks | Painter",  # 3
            "centered disks | MinMin-Stacking (abs)",  # 4
            "centered disks | MinMin-Stacking (rel)",  # 5
            "centered disks | MinSum-Stacking (abs)",  # 6
            "centered disks | MinSum-Stacking (rel)",  # 7
            "hawaiian disks | random",  # 8
            "hawaiian disks | LeftToRight",  # 9
            "hawaiian disks | RightToLeft",  # 10
            "hawaiian disks | Painter",  # 11
            "hawaiian disks | our Stacking",  # 12
            "pie charts | random",  # 13
            "pie charts | PainterRandom",  # 14
            "pie charts | RightToLeft",  # 15
            "pie charts | Painter",  # 16
            "pie charts | our Stacking",  # 17
            "squares | Painter+heuristic",  # 18
            "squares | Painter+random rotations",  # 19
            "squares | random Stacking+heuristic rotations",  # 20
            "squares | random Stacking+random rotations",  # 21
            "squares | our Stacking",  # 22
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

        # Geometry by background
        self.world_image = tk.PhotoImage(file=r"assets/test4.png")
        self.canvas.create_image(0, 0, image=self.world_image, anchor="nw")

        self.screen_height = self.world_image.height()
        self.screen_width = self.world_image.width()

        logging.info(self.screen_height)
        logging.info(self.screen_width)

    #prepares the data for the proportional symbols
    def prepare_data(self):
        #calculates coordinates from latitiude and longitude
        def latLongToPoint(lat, long, h, w):
            """Return (x,y) for lat, long inside a box."""
            lat = -lat + 90
            long = long + 180  # längengerade oben unten
            y = lat / 180
            x = long / 360
            x = int(x * w)
            y = int(y * h)
            return x, y
        
        #changes the dataframe structure to a list
        def changeStructureFromPanda(df):
            myData = []

            for lat, lon, conf, dead, rec in zip(
                df["latitude"],
                df["longitude"],
                df["confirmed_cases"],
                df["deaths"],
                df["recovered"],
            ):
                if conf > 0 and dead > 0 and rec > 0:
                    tmp = [0, 0, lat, lon, conf + 1, dead + 1, 1 + rec]
                    myData.append(tmp)

            return myData
        
        
        #for a given data point generate a mosaic square
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
            
        #generates some random data which has some nice properties
        def generateRandomData(numberOfCircles,maxRadius):
            circles=[]
            pies=[]
            piePieces=[]
            squares=[]
            for i in range(0,numberOfCircles):
                randomRadius=np.random.randint(maxRadius/3, maxRadius)
                x=np.random.randint(0.1*self.screen_height,0.9*self.screen_height)
                y=np.random.randint(0.33* self.screen_width,0.66* self.screen_width)
                
                
                #appending everything
                tmp=[x,y,randomRadius,2*randomRadius/3,4*randomRadius/9]
                circles.append(tmp)
                pies.append([int(x), int(y), int(randomRadius)])
                piePieces.append([2, 4])
                tmpSquare = createOneSquare(
                    randomRadius, 
                    [0,0,np.random.randint(-45,45),np.random.randint(-45,45),randomRadius,randomRadius/4,2*randomRadius/4], 
                    self.screen_height, self.screen_width
                )
                squares.append(tmpSquare)
                
            print("generateRandomData:")
            print(f"Number of pies: {len(pies)}")
            print(f"Number of circles: {len(circles)}")
            return circles,pies,piePieces,squares             
              
        
                
        def generateGeomData(myData, index):

            # transport current values from config singleton
            maximalSize = self.controller.symbolic_config.maximalSize
            scalingFactor = self.controller.symbolic_config.scalingFactor
            lowerBoundCases = self.controller.symbolic_config.lowerBoundCases


            for case in list(my_data):
                if case[4] < lowerBoundCases:
                    my_data.remove(case)

            valueList = []
            for case in list(my_data):
                valueList.append(case[4])
            valueList = sorted(valueList, reverse=True)

            # sometimes use the 4th biggest confirmed value for scaling because of USA INDIA BRASIL
            if len(valueList) == 1:
                factor = valueList[0]
            if len(valueList) == 0:
                factor = 1
            if len(valueList) <= 50 and len(valueList) > 1:
                factor = valueList[1]
            if len(valueList) > 50:
                factor = valueList[3]

            multiplicativeconstant = maximalSize / np.log(1 + scalingFactor)

            circles = []
            pies = []
            piePieces = []
            squares = []

            # generating circles,pies and squares
            for case in myData:
                lat = case[2]
                long = case[3]
                x, y = latLongToPoint(lat, long, self.screen_height, self.screen_width)

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
                    1 + scalingFactor * conf / factor
                )

                deadAdjusted = multiplicativeconstant * np.log(
                    1 + scalingFactor / 2 * dead / factor
                )
                recAdjusted = multiplicativeconstant * np.log(
                    1 + scalingFactor / 2 * (rec + dead) / factor
                )

                r = confAdjusted
                rprime2 = deadAdjusted
                rprime1 = recAdjusted
                if rprime2 < 1 or rprime1 < 1 or r < 1:
                    r = r + 1
                    rprime2 = rprime2 + 1
                    rprime1 = rprime1 + 1

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


            if len(circles) == 0:
                print(
                    f"Data quality issues: Circles array is empty for dataset no. {index} ..."
                )
                return
    
    
            print("generateGeomData:")
            print(f"Number of pies: {len(pies)}")
            print(f"Number of circles: {len(circles)}")
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

            for k in range(0,11):
                #generate random data
                circles,pies,piePieces,squares   = generateRandomData(60, 50)
                self.data_sets[cur_data_set_idx]=     circles 
                self.pie_piece_sets[cur_data_set_idx] = piePieces
                self.pie_sets[cur_data_set_idx] = pies
                self.square_sets[cur_data_set_idx] = squares
                cur_data_set_idx=cur_data_set_idx+1
                
                


            
        


class PaintingProgramPage(tk.Frame):
    """A frame to demonstrate the custom TK functions."""
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
            command=lambda: self.controller.show_frame(SymbolMapsPage),
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
    """Test the matplotlib instance here in case it is needed."""
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


class SettingsPage(tk.Frame):
    """A frame to configure the whole project using a singleton."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):

        # Title
        self.title_label = tk.Label(
            self,
            text="Settings of the current algorithms",
        )
        self.title_label.grid(column=0, row=0, sticky=tk.W + tk.E)

        # Settings
        self.frame = tk.Frame(self)
        self.frame.grid(column=0, row=1, sticky=tk.W + tk.E)

        self.maximalSize_label = tk.Label(self.frame, text="Maximal size:")
        self.maximalSize_label.grid(column=0, row=1, sticky=tk.W)
        self.maximalSize_entry = tk.Entry(self.frame, show=None)
        self.maximalSize_entry.grid(column=1, row=1, sticky=tk.W)
        self.maximalSize_entry.delete(0, tk.END)
        self.maximalSize_entry.insert(
            0, str(self.controller.symbolic_config.maximalSize)
        )

        self.scalingFactor_label = tk.Label(self.frame, text="Scaling factor:")
        self.scalingFactor_label.grid(column=0, row=2, sticky=tk.W)
        self.scalingFactor_entry = tk.Entry(self.frame, show=None)
        self.scalingFactor_entry.grid(column=1, row=2, sticky=tk.W)
        self.scalingFactor_entry.delete(0, tk.END)
        self.scalingFactor_entry.insert(
            0, str(self.controller.symbolic_config.scalingFactor)
        )

        self.lowerBoundCases_label = tk.Label(self.frame, text="Lower bound cases:")
        self.lowerBoundCases_label.grid(column=0, row=3, sticky=tk.W)
        self.lowerBoundCases_entry = tk.Entry(self.frame, show=None)
        self.lowerBoundCases_entry.grid(column=1, row=3, sticky=tk.W)
        self.lowerBoundCases_entry.delete(0, tk.END)
        self.lowerBoundCases_entry.insert(
            0, str(self.controller.symbolic_config.lowerBoundCases)
        )

        self.separator = tk.Label(self.frame, text="")
        self.separator.grid(column=0, row=4, sticky=tk.W)

        self.symbolic_button = tk.Button(
            self,
            text="Save & show first Symbolic Maps page",
            command=lambda: self.save_and_to_symbolic_maps(),
        )
        self.symbolic_button.grid(column=0, row=2, sticky=tk.W + tk.E)

    def save_and_to_symbolic_maps(self):
        self.controller.symbolic_config.maximalSize = int(self.maximalSize_entry.get())
        self.controller.symbolic_config.scalingFactor = int(
            self.scalingFactor_entry.get()
        )
        self.controller.symbolic_config.lowerBoundCases = int(
            self.lowerBoundCases_entry.get()
        )

        self.controller.frames[SymbolMapsPage].flush_everything()
        self.controller.frames[SymbolMapsPage].initialize_data()
        self.controller.frames[SymbolMapsPage].prepare_data()

        self.controller.show_frame(SymbolMapsPage)

        self.controller.frames[SymbolMapsPage].data_algo_change(None)


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
            command=lambda: self.controller.show_frame(SymbolMapsPage),
        )
        self.symbolic_button.pack(side="bottom")


def main():
    """The main function of the geomlab."""
    # Create application
    app = GeomLabApp()

    # Run application
    app.mainloop()
