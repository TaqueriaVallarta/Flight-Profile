import DragSetup
from DragSetup import Atmosphere, DragSetup
from Motor import Motor

pressure_0 = 101125
temperature_0 = 288.15
height_0 = 0
atmo = Atmosphere(temperature_0, pressure_0, height_0)

# Self-Explanatory
def inches_to_meters(inches):
    return (inches * 2.54) / 100


def initialize():

    fin_thickness = inches_to_meters(.5)
    fin_height = inches_to_meters(12)
    drag_coef = .5

    # Initializes with 8" body tube
    drag_setup = DragSetup(fin_thickness, fin_height, drag_coef)

    motor = Motor(

