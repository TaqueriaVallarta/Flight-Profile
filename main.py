# %%
from lib.Drag.DragSetup import DragSetup
from lib.Motor.Motor import Motor
from lib.Recovery import Parachute
from lib.RocketClass import Rocket
from math import pi
import matplotlib.pyplot as plt


# Self-Explanatory
def inches_to_meters(inches):
    return (inches * 2.54) / 100


# initializes all the values for rocket
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
    # %% Generate rocket
    rocket = initialize()

    # %% Simulate rocket to ground hit
    rocket.simulate_to_ground()

    # %% Export the data
    rocket.copy_dataframe()
    rocket.dataframe.to_csv("Simulation_data.csv", index=False)
