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


class Rocket:
    def __init__(self, drag_setup, motor, dry_mass, initial_height_asl=0):
        self.drag_setup = drag_setup  # drag setup class
        self.motor = motor  # motor class
        self.dry_mass = dry_mass  # dry mass in kg
        self.initial_height_asl = initial_height_asl  # Initial Height in m ASL
        self.height_agl = 0  # height above ground level
        self.height_asl = initial_height_asl  # height above ground level
        self.velocity = 0
        self.acceleration = 0
        self.gravity = self.drag_setup.gravity


def initialize():
    fin_thickness = inches_to_meters(.5)
    fin_height = inches_to_meters(12)
    drag_coef = .5

    # Initializes with 8" body tube
    drag_setup = DragSetup(fin_thickness, fin_height, drag_coef)

    wet_mass = 20  # Kilograms
    burn_time = 20  # Seconds
    mean_thrust = 4000  # Newtons
    motor = Motor(wet_mass, burn_time, mean_thrust)

    dry_mass = 80  # Kilograms
    return Rocket(drag_setup, motor, dry_mass)

if __name__ == '__main__':
    rocket = initialize()
    time = 0
    time_step = .1
    while rocket.height_agl >=0:
        r
