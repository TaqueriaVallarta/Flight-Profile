from lib.Drag import DragSetup
from lib.Drag.DragSetup import DragSetup
from lib.Motor.Motor import Motor
from lib.rk4 import rk4_step
import pandas as pd


# Self-Explanatory
def inches_to_meters(inches):
    return (inches * 2.54) / 100


class Rocket:
    def __init__(self, drag_setup: DragSetup, motor: Motor, dry_mass, time=0, dt=.1,
                 initial_height_asl=0.0):
        self.drag_setup = drag_setup  # drag setup class
        self.motor = motor  # motor class
        self.dry_mass = dry_mass  # dry mass in kg
        self.initial_height_asl = initial_height_asl  # Initial Height in m ASL
        self.height_agl = 0  # height above ground level
        self.height_asl = initial_height_asl  # height above ground level
        self.velocity = 0
        self.gravity = self.drag_setup.atmosphere.g
        self.time = time
        self.dt = dt

    def mass(self, time):
        return self.dry_mass + self.motor.mass(time)

    def acceleration(self, height_asl, velocity, time):
        drag = self.drag_setup.calculate_drag_force(velocity, height_asl)
        thrust = self.motor.thrust(time)
        weight = -self.gravity * self.mass(time)
        if self.height_asl < self.initial_height_asl:
            normal_force = -weight
        else:
            normal_force = 0
        force = drag + thrust + weight + normal_force
        return force / self.mass(time)

    # Update self using the rk4 function
    def rkt_rk4_step(self):
        self.height_asl, self.velocity = rk4_step(self.height_asl, self.velocity, self.acceleration, self.dt, self.time)

    def update_agl(self):
        self.height_agl = self.height_asl - self.initial_height_asl

    def mach(self):
        return abs(self.velocity / self.drag_setup.atmosphere.speed_of_sound(self.height_asl))

    def outputs(self):
        return [self.time, self.height_agl, self.height_asl, self.velocity,
                self.acceleration(rocket.height_agl, self.velocity, self.time),
                self.mass(self.time), self.motor.thrust(self.time),
                self.drag_setup.calculate_drag_force(self.velocity, self.height_agl),
                self.drag_setup.atmosphere.density(self.height_agl),
                self.drag_setup.atmosphere.pressure(self.height_agl),
                self.drag_setup.atmosphere.temperature(self.height_agl),
                self.drag_setup.atmosphere.speed_of_sound(self.height_asl),
                self.drag_setup.drag_coef,
                self.mach()]

    def sim_to_apogee(self):
        while self.velocity >= 0:
            self.rkt_rk4_step()
            self.update_agl()

            self.time += self.dt


# initializes all the values
def initialize():
    # todo: make initialize values somewhat realistic
    fin_thickness = inches_to_meters(.5)
    fin_height = inches_to_meters(12)
    drag_coef = .5

    # Initializes with 8" body tube
    drag_setup = DragSetup(fin_thickness, fin_height, drag_coef)
    drag_setup.atmosphere.p_0 = 97866.6421  # historical pressure for june
    drag_setup.atmosphere.h_0 = 1219.2  # Mean height of WSMR ASL in m
    drag_setup.atmosphere.temp_0 = 27 + 273.15  # Mean temp of june (mean of high hand low)

    wet_mass_motor = 210  # Kilograms
    burn_time = 18  # Seconds
    mean_thrust = 10000  # Newtons
    motor = Motor(wet_mass_motor, burn_time, mean_thrust)

    dry_mass_rocket = 1 / 2 * wet_mass_motor  # Kilograms
    initial_height_asl = drag_setup.atmosphere.h_0
    return Rocket(drag_setup, motor, dry_mass_rocket, initial_height_asl=initial_height_asl)


if __name__ == '__main__':
    # print("Height", ",", "Velocity", ",", "Acceleration", ",", "Time", ",", "Mass", ",","Drag Force")
    rocket = initialize()

    simulation_data = [rocket.outputs()]

    while rocket.height_agl >= 0:
        # adding data to a list for csv file

        # Update height + velocity using the rk4
        rocket.rkt_rk4_step()
        # Convert asl to agl
        rocket.update_agl()

        simulation_data.append(rocket.outputs())

        # print(rocket.height_agl, rocket.time)
        # output the values with space between them
        # Done: setup csv file export using pandas (ask ChatGPT about it)
        # numpy is good for making the arrays
        # TODO: decide between MatPlotLib and Sheets/Excel for presentation of data

        # print(rocket.height_agl, ",", rocket.velocity, ",",
        #      rocket.acceleration(rocket.height_agl, rocket.velocity, current_time), ",",
        #      current_time, ",", rocket.mass(current_time), ",",
        #      rocket.drag_setup.calculate_drag_force(rocket.velocity, rocket.height_agl))

        rocket.time += rocket.dt

    Simulation_dataframe = pd.DataFrame(simulation_data,
                                        columns=['Time Stamp', 'Height_agl', 'Height_asl', "Velocity", 'Acceleration',
                                                 'Mass', 'Thrust', 'Drag', 'Air_Density', 'Air_pressure',
                                                 'Air_Temperature', 'Speed_of_sound', 'Drag_Coefficient', 'Mach'])
    Simulation_dataframe.to_csv("Simulation_data.csv")
