import tkinter as tk
import tkinter.ttk as ttk

# Draw on canvas
lastx, lasty = 0, 0

def xy(event):
    global lastx, lasty
    lastx, lasty = event.x, event.y

def addLine(event):
    global lastx, lasty
    canvas.create_line((lastx, lasty, event.x, event.y))
    lastx, lasty = event.x, event.y

# Main Frame
class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        # Canvas
        self.canvas = tk.Canvas()
        self.canvas.pack(side='top', fill='both', expand='yes')
        self.canvas.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.canvas.bind("<Button-1>", xy)
        self.canvas.bind("<B1-Motion>", addLine)

        self.master = master
        #self.pack()
        self.create_widgets()


    def create_widgets(self):

        # Hi there button
        self.hi_there = tk.Button(self)
        self.hi_there["text"] = "Hello World\n(click me)"
        self.hi_there["command"] = self.say_hi
        self.hi_there.pack(side="top")

        # Combobox (to select algo, input data, cost function)
        self.algorithm = ttk.Combobox(self)
        self.algorithm['values'] = ("MinMxSumK", "Painter", "Random")
        self.algorithm.current(1)
        self.algorithm.pack(side="top")
        # TODO: Later orientation/gridding
        #self.algorithm.grid(column=0, row=0)


        # Quit Button
        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=self.master.destroy)
        self.quit.pack(side="bottom")

    def say_hi(self):
        print("hi there, everyone!")



# Define window props
window = tk.Tk()
window.geometry('800x600')
window.title('Symbolic Maps')
window.columnconfigure(0, weight=1)
window.rowconfigure(0, weight=1)

# Menu
menu = tk.Menu(window)
menu_item = tk.Menu(menu)
menu_item.add_command(label='Quit')
menu.add_cascade(label='File', menu=menu_item)
window.config(menu=menu)

# Create application
app = Application(master=window)

# TODO: Ugly
canvas = app.canvas #Canvas(root)

# Run application
app.mainloop()
