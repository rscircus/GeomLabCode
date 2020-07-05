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
        file_menu.add_command(label='Quit')
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
        for page in (SymbolicMapsPage, AboutPage):
            frame = page(container, self)
            frame.grid(row=0, column=0, sticky="nswe")
            self.frames[page] = frame

        # Display
        self.show_frame(SymbolicMapsPage)


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
        # TODO: Later orientation/gridding
        #self.algorithm.grid(column=0, row=0)

        self.about = tk.Button(self, text="About", command=lambda: self.controller.show_frame(AboutPage))
        self.about.pack(side="bottom")

class PaintingProgramPage(tk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        self.painter = tk.Button(self, text="Back to Symbolic Maps Page", command=lambda: self.controller.show_frame(SymbolicMapsPage))
        self.painter.pack(side="bottom")


class AboutPage(tk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        self.painter = tk.Button(self, text="Back to Symbolic Maps Page", command=lambda: self.controller.show_frame(SymbolicMapsPage))
        self.painter.pack(side="bottom")

def quit():
    print('Hi')


# Create application
app = GeomLabApp()

# Run application
app.mainloop()
