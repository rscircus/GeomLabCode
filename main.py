import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import tkinter as tk
import tkinter.ttk as ttk

# Philipp's deps:
import numpy as np
import cv2
import math

import symbolicstacking as st

# Expand TK's oval:
def _create_circle(self, x, y, r, **kwargs):
    return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
tk.Canvas.create_circle = _create_circle

# Expand TK's oval to support our pies:
def _create_circle_arc(self, x, y, r, **kwargs):
    if "start" in kwargs and "end" in kwargs:
        kwargs["extent"] = kwargs["end"] - kwargs["start"]
        del kwargs["end"]
    return self.create_arc(x-r, y-r, x+r, y+r, **kwargs)
tk.Canvas.create_circle_arc = _create_circle_arc

# Main Window
class GeomLabApp(tk.Tk):
    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)

        # Configure self
        self.geometry('1800x868')
        self.title('Symbolic Maps')

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Symbolic Maps', command=lambda: self.show_frame(SymbolicMapsPage))
        file_menu.add_command(label='Painting Program', command=lambda: self.show_frame(PaintingProgramPage))
        file_menu.add_command(label='Matplotlib', command=lambda: self.show_frame(MatplotlibPage))
        file_menu.add_command(label='About', command=lambda: self.show_frame(AboutPage))
        file_menu.add_command(label='Quit', command=lambda: self.destroy())
        menubar.add_cascade(label='File', menu=file_menu)
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

        # Display
        self.show_frame(SymbolicMapsPage)


    def show_frame(self, container):
        '''Show a specific frame in the window.'''

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
        self.circles=[]
        self.pies=[]
        self.piePieces=[]

        # Code
        self.prepare_data()

        # Execute symbolic algo
        self.change_algorithm()

    def change_algorithm(self):
        '''Update Canvas upon algo change.'''

        algo = self.algorithm.current()

        if algo == 0: #MinMaxSumK
            self.circles = st.maxMinMinKStacking(self.circles, "absolute")
        elif algo == 1: #Painters
            self.circles = st.painterAlgorithm(self.circles)
        elif algo == 2: #Random
            pass
        else:
            print("You shouldn't see me.")

        # Draw
        self.draw_circles()

    def draw_circles(self):

        for c in self.circles:
            # x, y ,r
            self.canvas.create_circle(c[0], c[1] ,c[2] ,fill='#bbb', outline='#000')

    def data_algo_change(self, event):
        self.canvas.delete("all")
        self.prepare_data()
        self.change_algorithm()
        self.draw_circles()

    def create_widgets(self):
        # Top widgets

        self.frame = tk.Frame(self, self.parent)
        self.frame.grid(column=0, row=0, sticky='w')

        # Add canvas
        self.canvas = tk.Canvas(self, bg='white', width=1800, height=900)
        self.canvas.grid(column=0,row=1,sticky='nsew')

        # Combobox (to select algo, input data, cost function)
        self.datalabel = tk.Label(self.frame, text ="Chose input data: ")
        self.datalabel.grid(column=0, row=0)

        self.data = ttk.Combobox(self.frame)
        self.data['values'] = ("test", "May", "June")
        self.data.current(1)
        self.data.grid(column=1, row=0)
        self.data.bind("<<ComboboxSelected>>", self.data_algo_change)

        self.datalabel = tk.Label(self.frame, text ="Chose algorithm :")
        self.datalabel.grid(column=0, row=1)

        self.algorithm = ttk.Combobox(self.frame)
        self.algorithm['values'] = ("MinMxSumK", "Painter", "Random")
        self.algorithm.current(1)
        self.algorithm.grid(column=1, row=1)
        self.algorithm.bind("<<ComboboxSelected>>", self.data_algo_change)

        # Add about button
        self.about = tk.Button(self, text="About", command=lambda: self.controller.show_frame(AboutPage))
        self.about.grid(column=2, row=0)


    def prepare_data(self):
        def latLongToPoint(lat,long,h,w):
            '''Return (x,y) for lat, long inside a box.'''
            lat=-lat+90
            long=long+180 #längengerade oben unten
            y=lat/180
            x=long/360
            x=int(x*w)
            y=int(y*h)
            return x,y
                
        def calculatePointOnCircle(c,angle):
            '''Return pos in interval (0,1) on circumference of circle.'''
            cosangle=np.cos(angle)
            sinangle=np.sin(angle)
            return cosangle*c[2]+c[0], sinangle*c[2]+c[1] 

        #structure: loc,loc,lat,long,conf,dead,recovered
        # TODO: Give this reasonable names
        maps = {}
        self.circles = []
        self.piePieces = []
        self.pies = []
        maps[0] = np.load("data/testData.npy", allow_pickle=True)
        maps[1] = np.load("data/testDataEndeMai.npy", allow_pickle=True)
        maps[2] = np.load("data/testDataJuni.npy", allow_pickle=True)
        myworldmap = maps[self.data.current()]
        worldmap = cv2.imread('assets/test4.png')
        h=len(worldmap)
        w=len(worldmap[0])
        print(h)
        print(w)
        myData=[]
        
        for case in myworldmap:
            tmp=[]
            for slot in case:
                tmp.append(slot)
            myData.append(tmp)

        for case in list(myData):
            if(case[4]<5000):
                myData.remove(case)
            
        maximum=1
        for case in myData:
            if(case[4]<1):
                tmp=1
            else:
                tmp=case[4]
            if(tmp>maximum):
                maximumsecond=maximum
                maximum=tmp
                maximum2=np.log(4+case[4]*100/maximumsecond)

        for case in myData:
            lat=case[2]
            long=case[3]
            x,y=latLongToPoint(lat, long, h, w)
            case[4]=case[4]+5
            case[5]=case[5]+5
            case[6]=case[6]+5
                
            if(case[4]<case[6]):
                continue

            if(case[4]==0):
                conf=1
            else:
                conf=np.log(4+case[4]*100/maximumsecond)
                
            if(case[5]==0 or math.isnan(case[5])):
                dead=1
            else:
                dead=(case[5])
                
            if(case[6]==0 or math.isnan(case[6])):
                rec=1
            else:
                rec=(case[6])
                
            conf=125*conf/maximum2
            dead=np.sqrt(conf*conf*(dead/case[4]))
            rec=np.sqrt(conf*conf*(rec/case[4])+dead*dead)
            r=conf
            rprime2=dead
            rprime1=rec
            rprime0=1
            self.circles.append([int(x),int(y),int(r),int(rprime1),int(rprime2)])
            self.pies.append([int(x),int(y),int(r)])

            a0=rprime0*rprime0
            a1=rprime1*rprime1
            a2=rprime2*rprime2
            a=r*r  
            p1=(case[5]/case[4]) *2*np.pi
            p2=(((case[6]/case[4]))*2*np.pi )+p1
            self.piePieces.append([p1,p2])    

            # TODO: Have a look at the data in the console
            #print(self.circles)

class PaintingProgramPage(tk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller

        self.old_x = None
        self.old_y = None

        self.create_widgets()

        # Single circle
        self.canvas.create_circle(150, 40 ,20 ,fill='#bbb', outline='')

        # Arcs
        self.canvas.create_circle(100, 120, 50, fill="blue", outline="#DDD", width=4)
        self.canvas.create_circle_arc(100, 120, 48, fill="green", outline="", start=45, end=140)
        self.canvas.create_circle_arc(100, 120, 48, fill="green", outline="", start=275, end=305)
        self.canvas.create_circle_arc(100, 120, 45, style="arc", outline="white", width=6, start=270-25, end=270+25)

    def create_widgets(self):
        self.canvas = tk.Canvas(self, bg='white')
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind('<B1-Motion>', self.paint)
        self.canvas.bind('<ButtonRelease-1>', self.reset)

        self.symbolic_button = tk.Button(self, text="Go to Symbolic Maps Page", command=lambda: self.controller.show_frame(SymbolicMapsPage))
        self.symbolic_button.pack(side="bottom")

    def paint(self, event):
        if self.old_x and self.old_y:
            self.canvas.create_line(self.old_x, self.old_y, event.x, event.y,
                               width=2, fill='black',
                               capstyle=tk.ROUND, smooth=tk.TRUE, splinesteps=36)
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

        self.fig = Figure(figsize=(5,5), dpi=100)
        self.subfig = self.fig.add_subplot(111)
        self.subfig.plot([1,2,3,4,5,6],[1,3,2,5,3,6])

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

class AboutPage(tk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        self.label = tk.Label(self, text="Some info about the algos, complexity, us, maybe link to paper...")
        self.label.pack(side="top")

        self.symbolic_button = tk.Button(self, text="Go to Symbolic Maps Page", command=lambda: self.controller.show_frame(SymbolicMapsPage))
        self.symbolic_button.pack(side="bottom")

# Create application
app = GeomLabApp()

# Run application
app.mainloop()
