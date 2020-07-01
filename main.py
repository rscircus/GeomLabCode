# Implementation of the GeomLab
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

class SymbolicMaps(Widget):
    pass

class GeomLabApp(App):
    def build(self):
        return SymbolicMaps()

if __name__ == '__main__':
    GeomLabApp().run()
