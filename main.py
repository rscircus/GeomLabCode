import tkinter as tk
import tkinter.ttk as ttk

# Main Window
class GeomLabApp(tk.Tk):
    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)

        # Configure self
        self.geometry('800x600')
        self.title('Symbolic Maps')

        # Menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Symbolic Maps', command=lambda: self.show_frame(SymbolicMapsPage))
        file_menu.add_command(label='Painting Program', command=lambda: self.show_frame(PaintingProgramPage))
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
        for page in (SymbolicMapsPage, PaintingProgramPage, AboutPage):
            frame = page(container, self)
            frame.grid(row=0, column=0, sticky="nswe")
            self.frames[page] = frame

        # Display
        self.show_frame(PaintingProgramPage)


    def show_frame(self, container):
        '''Show a specific frame in the window.'''

        frame = self.frames[container]
        frame.tkraise()


class SymbolicMapsPage(tk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()


    def create_widgets(self):
        # Combobox (to select algo, input data, cost function)
        self.algorithm = ttk.Combobox(self)
        self.algorithm['values'] = ("MinMxSumK", "Painter", "Random")
        self.algorithm.current(1)
        self.algorithm.pack(side="top")

        self.about = tk.Button(self, text="About", command=lambda: self.controller.show_frame(AboutPage))
        self.about.pack(side="bottom")

class PaintingProgramPage(tk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller

        self.old_x = None
        self.old_y = None

        self.create_widgets()

    def create_widgets(self):
        self.canvas = tk.Canvas(self, bg='white')
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind('<B1-Motion>', self.paint)
        self.canvas.bind('<ButtonRelease-1>', self.reset)

        self.painter = tk.Button(self, text="Go to Symbolic Maps Page", command=lambda: self.controller.show_frame(SymbolicMapsPage))
        self.painter.pack(side="bottom")

    def paint(self, event):
        if self.old_x and self.old_y:
            self.canvas.create_line(self.old_x, self.old_y, event.x, event.y,
                               width=2, fill='black',
                               capstyle=tk.ROUND, smooth=tk.TRUE, splinesteps=36)
        self.old_x = event.x
        self.old_y = event.y

    def reset(self, event):
        self.old_x, self.old_y = None, None


class AboutPage(tk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        self.painter = tk.Button(self, text="Go to Symbolic Maps Page", command=lambda: self.controller.show_frame(SymbolicMapsPage))
        self.painter.pack(side="bottom")

        self.label = tk.Label(self, text="Some info about the algos, complexity, us, maybe link to paper...")
        self.label.pack(side="top")

def quit():
    print('Hi')


# Create application
app = GeomLabApp()

# Run application
app.mainloop()
