import DragSetup
from DragSetup import DragSetup
from Motor import Motor
from rk4 import rk4_step
import pandas as pd


# Self-Explanatory
def inches_to_meters(inches):
    return (inches * 2.54) / 100


class Rocket:
    def __init__(self, drag_setup: DragSetup, motor: Motor, dry_mass, initial_height_asl=0):
        self.drag_setup = drag_setup  # drag setup class
        self.motor = motor  # motor class
        self.dry_mass = dry_mass  # dry mass in kg
        self.initial_height_asl = initial_height_asl  # Initial Height in m ASL
        self.height_agl = 0  # height above ground level
        self.height_asl = initial_height_asl  # height above ground level
        self.velocity = 0
        self.gravity = self.drag_setup.atmosphere.g

    def mass(self, time):
        return self.dry_mass + self.motor.mass(time)

    def acceleration(self, height, velocity, time):
        drag = self.drag_setup.calculate_drag_force(velocity, height)
        thrust = self.motor.thrust(time)
        weight = -self.gravity * self.mass(time)
        force = drag + thrust + weight
        return force / self.mass(time)

    # Update self using the rk4 function
    def rkt_rk4_step(self, time, dt):
        self.height_asl, self.velocity = rk4_step(self.height_asl, self.velocity, self.acceleration, dt, time)

    def update_agl(self):
        self.height_agl = self.height_asl - self.initial_height_asl


# initializes all the values
def initialize():
    # todo: make initialize values somewhat realistic
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
    print("Height", ",", "Velocity", ",",
          "Acceleration", ",",
          "Time", ",", "Mass", ",",
          "Drag Force")
    rocket = initialize()
    current_time = 0
    time_step = .1
    simulation_data = []
    while rocket.height_agl >= 0:
        # Update height + velocity using the rk4
        rocket.rkt_rk4_step(current_time, time_step)
        # Convert asl to agl
        rocket.update_agl()
        print(rocket.height_agl, current_time)
        # output the values with space between them
        # TODO: setup csv file export using pandas (ask ChatGPT about it)
        # numpy is good for making the arrays
        # TODO: decide between MatPlotLib and Sheets/Excel for presentation of data

        # adding data to a list for csv file
        simulation_data.append([current_time, rocket.height_agl, rocket.height_asl, rocket.velocity,
                                rocket.acceleration(rocket.height_agl, rocket.velocity, current_time),
                                rocket.mass(current_time), rocket.motor.thrust(current_time),
                                rocket.drag_setup.calculate_drag_force(rocket.velocity, rocket.height_agl),
                                rocket.drag_setup.atmosphere.density(rocket.height_agl),
                                rocket.drag_setup.atmosphere.pressure(rocket.height_agl),
                                rocket.drag_setup.atmosphere.temperature(rocket.height_agl),
                                rocket.drag_setup.atmosphere.speed_of_sound(rocket.height_agl),
                                rocket.drag_setup.drag_coef])

        # print(rocket.height_agl, ",", rocket.velocity, ",",
        #      rocket.acceleration(rocket.height_agl, rocket.velocity, current_time), ",",
        #      current_time, ",", rocket.mass(current_time), ",",
        #      rocket.drag_setup.calculate_drag_force(rocket.velocity, rocket.height_agl))

        current_time += time_step

    Simulation_dataframe = pd.DataFrame(simulation_data,
                                        columns=['Time Stamp', 'Height_agl', 'Height_asl', "Velocity", 'Acceleration',
                                                 'Mass', 'Thrust', 'Drag', 'Air_Density', 'Air_pressure',
                                                 'Air_Temperature', 'Speed_of_sound', 'Drag_Coefficient'])
    Simulation_dataframe.to_csv("Simulation_data.csv")
