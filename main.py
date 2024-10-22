from lib.Drag.DragSetup import DragSetup
from lib.Motor.Motor import Motor
from lib.Recovery import Parachute
from lib.rk4 import rk4_step
import pandas as pd
from math import pi
import matplotlib.pyplot as plt


# Self-Explanatory
def inches_to_meters(inches):
    return (inches * 2.54) / 100


class Rocket:
    def __init__(self, drag_setup: DragSetup, motor: Motor, dry_mass, time=0, dt=.1,
                 initial_height_msl=0.0):
        self.drag_setup = drag_setup  # drag setup class
        self.motor = motor  # motor class
        self.dry_mass = dry_mass  # dry mass in kg
        self.initial_height_asl = initial_height_msl  # Initial Height in m ASL
        self.height_agl = 0  # height above ground level
        self.height_msl = initial_height_msl  # height above ground level
        self.velocity = 0
        self.gravity = self.drag_setup.atmosphere.g
        self.time = time
        self.dt = dt
        self.data_list = []
        self.dataframe = pd.DataFrame(
            columns=['Time', 'Height AGL', 'Height MSL', "Velocity",
                     'Acceleration',
                     'Mass', 'Thrust', 'Drag', 'Air Density', 'Air Pressure',
                     'Air_Temperature', 'Speed of Sound', 'Drag Coefficient', 'Mach',
                     'Cross-sectional Area'])
        self.dataframe: pd.DataFrame

    def mass(self, time):
        return self.dry_mass + self.motor.mass(time)

    def acceleration(self, height_asl, velocity, time):
        drag = self.drag_setup.calculate_drag_force(velocity, height_asl, self.time)
        thrust = self.motor.thrust(time)
        weight = -self.gravity * self.mass(time)
        if self.height_msl < self.initial_height_asl:
            normal_force = -weight
        else:
            normal_force = 0
        force = drag + thrust + weight + normal_force
        return force / self.mass(time)

    # Update self using the rk4 function
    def rkt_rk4_step(self):
        self.height_msl, self.velocity = rk4_step(self.height_msl, self.velocity, self.acceleration, self.dt, self.time)

    def update_agl(self):
        self.height_agl = self.height_msl - self.initial_height_asl

    def mach(self):
        return abs(self.velocity / self.drag_setup.atmosphere.speed_of_sound(self.height_msl))

    def output(self):
        return [self.time, self.height_agl, self.height_msl, self.velocity,
                self.acceleration(self.height_msl, self.velocity, self.time),
                self.mass(self.time), self.motor.thrust(self.time),
                self.drag_setup.calculate_drag_force(self.velocity, self.height_msl, self.time),
                self.drag_setup.atmosphere.density(self.height_msl),
                self.drag_setup.atmosphere.pressure(self.height_msl),
                self.drag_setup.atmosphere.temperature(self.height_msl),
                self.drag_setup.atmosphere.speed_of_sound(self.height_msl),
                self.drag_setup.drag_coef,
                self.mach(),
                self.drag_setup.cross_area]

    def dataframe_update(self):
        data = self.output()
        new_data = pd.DataFrame([data], columns=self.dataframe.columns)
        self.dataframe = pd.concat([self.dataframe, new_data], ignore_index=True)

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

    cross_area_reefed = pi * (.5 / 2) ** 2  # area in m^2
    drag_coef_reefed = 2
    inflation__time_reefed = 5  # time in seconds
    reefed_parachute = Parachute(cross_area_reefed, drag_coef_reefed, inflation__time_reefed)

    cross_area_main = pi * (3 / 2) ** 2  # area in m^2
    drag_coef_main = 2
    inflation_time_main = 5  # time in seconds
    deployment_altitude = 600  # meters
    main_parachute = Parachute(cross_area_main, drag_coef_main, inflation_time_main,
                               deployment_altitude=deployment_altitude)
    main_parachute.start_surface_area = cross_area_reefed

    # Initializes with 8" body tube
    drag_setup = DragSetup(fin_thickness, fin_height, drag_coef, reefed_parachute, main_parachute)
    drag_setup.atmosphere.p_0 = 97866.6421  # historical pressure for june
    drag_setup.atmosphere.h_0 = 1219.2  # Mean height of WSMR ASL in m
    drag_setup.atmosphere.temp_0 = 27 + 273.15  # Mean temp of june (mean of high hand low)

    wet_mass_motor = 210  # Kilograms
    burn_time = 18  # Seconds
    mean_thrust = 10000  # Newtons
    motor = Motor(wet_mass_motor, burn_time, mean_thrust)

    dry_mass_rocket = 1 / 2 * wet_mass_motor  # Kilograms
    initial_height_msl = drag_setup.atmosphere.h_0
    return Rocket(drag_setup, motor, dry_mass_rocket, initial_height_msl=initial_height_msl)


if __name__ == '__main__':
    # print("Height", ",", "Velocity", ",", "Acceleration", ",", "Time", ",", "Mass", ",","Drag Force")
    # %% Generate rocket
    rocket = initialize()

    while rocket.height_agl >= 0:
        # adding data to a list for csv file

        # Update height + velocity using the rk4
        rocket.rkt_rk4_step()
        # Convert asl to agl
        rocket.update_agl()

        rocket.dataframe_update()

        # output the values with space between them
        # Done: setup csv file export using pandas (ask ChatGPT about it)
        # numpy is good for making the arrays
        # TODO: decide between MatPlotLib and Sheets/Excel for presentation of data

        # print(rocket.height_agl, ",", rocket.velocity, ",",
        #      rocket.acceleration(rocket.height_agl, rocket.velocity, current_time), ",",
        #      current_time, ",", rocket.mass(current_time), ",",
        #      rocket.drag_setup.calculate_drag_force(rocket.velocity, rocket.height_agl))

        rocket.time += rocket.dt
    # %%
    dataframe = rocket.dataframe
    time = dataframe['Time']
    Height_AGL = dataframe['Height AGL']
    Velocity = dataframe['Velocity']
    Drag = dataframe['Drag']
    plt.plot(time, Height_AGL)
    plt.plot(time, Velocity)
    plt.show()
    # %%
    print(rocket.dataframe)
    rocket.dataframe.to_csv("Simulation_data.csv")
