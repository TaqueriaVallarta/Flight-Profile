from lib.Drag.DragSetup import DragSetup
from lib.Motor.Motor import Motor
from lib.Recovery import Parachute
from lib.RocketClass import Rocket
from math import pi
from lib.GoogleSheets import UpdateSpreadsheet
import time
import logging
import numpy as np
import matplotlib.pyplot as plt


# Self-Explanatory
def inches_to_meters(inches):
    return (inches * 2.54) / 100


# initializes all the values for rocket
def initialize(dry_mass_rocket):
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
    intial_surface_area_main = cross_area_reefed
    main_parachute = Parachute(cross_area_main, drag_coef_main, inflation_time_main,
                               deployment_altitude=deployment_altitude)
    main_parachute.start_surface_area = cross_area_reefed

    # Initializes with 8" body tube
    drag_setup = DragSetup(fin_thickness, fin_height, drag_coef, reefed_parachute, main_parachute)
    drag_setup.atmosphere.p_0 = 97866.6421  # historical pressure for june
    drag_setup.atmosphere.h_0 = 1219.2  # Mean height of WSMR ASL in m
    drag_setup.atmosphere.temp_0 = 27 + 273.15  # Mean temp of june (mean of high hand low)

    initial_height_msl = drag_setup.atmosphere.h_0
    return Rocket(drag_setup, dry_mass_rocket, initial_height_msl=initial_height_msl)


def df_column_switch(df, column1, column2):
    i = list(df.columns)
    a, b = i.index(column1), i.index(column2)
    i[b], i[a] = i[a], i[b]
    df = df[i]
    return df


if __name__ == '__main__':
    # Log the start time of the process
    start_time = time.process_time()
    logging.info(f"Starting process at {start_time:.2f} seconds")

    # Initialize Rocket object
    rocket = initialize(40)

    # Initialize spreadsheet updater
    update_spreadsheet = UpdateSpreadsheet(rocket)
    update_spreadsheet.process_spreadsheet_update(start_time=start_time)
    update_spreadsheet.rocket.motor.initial_output()

    # Log the total elapsed process time
    end_time = time.process_time()
    elapsed_time = end_time - start_time
    logging.info(f"Process completed in {elapsed_time:.2f} seconds")


    logging.info(f"Apogee: {max(update_spreadsheet.rocket.dataframe['Height AGL']):.2f} m and {max(update_spreadsheet.rocket.dataframe['Height AGL'])*100/2.56/12:.2f} ft")

    exit()

    rockets = [initialize(i) for i in range(20,50,1)]
    for rocket in rockets:
        rocket.sim_to_apogee()

    mass_values = np.linspace(20, 60, 80)
    apogee_values = [initialize(m).sim_to_apogee().height_agl for m in mass_values]

    plt.plot(mass_values, apogee_values)
    plt.xlabel('Dry Mass (kg)')
    plt.ylabel('Apogee (m)')
    plt.title('Testing Different Dry Masses')

    # Set the axis to start at (0, 0)
    plt.xlim(np.min(mass_values), np.max(mass_values))
    plt.ylim(0, max(apogee_values) * 1.1)  # Adding some margin to the max thrust value

    plt.grid(True)
    plt.show()