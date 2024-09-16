from types import NoneType

from lib.Drag.DragSetup import DragSetup
from lib.Motor.Motor import Motor
from lib.rk4 import rk4_step
import pandas as pd


class Rocket:
    def __init__(self, drag_setup: DragSetup, motor: Motor, dry_mass, time=0, dt=.1,
                 initial_height_msl=0.0,):
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
                     'Cross-sectional Area', 'Flight State', 'Weight', 'Total Force'])
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
                self.drag_setup.cross_area,
                self.flight_state(),
                -self.mass(self.time) * self.gravity,
                self.acceleration(self.height_msl, self.velocity, self.time) * self.mass(self.time)]

    def flight_state(self):
        if self.time <= self.motor.burn_time:
            return "Motor Burning"
        elif (self.acceleration(self.height_msl, self.velocity, self.time) < 0) and (self.velocity > 0):
            return "Coasting"
        elif self.drag_setup.main_parachute.DeployStatus:
            return "Main Unreefed"
        elif self.drag_setup.reefed_parachute.DeployStatus:
            return "Main Reefed"
        return ""

    def events(self):
        states = self.dataframe['Flight State']
        events = [""] * states.size
        for i, state in enumerate(states):
            if i - 1 < 0:
                continue
            if state != states[i - 1]:
                if state == "Coasting":
                    events[i] = "Motor Burnout"
                elif state == "Main Reefed":
                    events[i] = "Apogee and Reef Deploy"
                elif state == "Main Unreefed":
                    events[i] = "Main Unreefing"
        return events

    def datalist_update(self):
        data = self.output()
        self.data_list.append(data)

    def dataframe_update(self):
        columns = self.dataframe.columns
        for i, column in enumerate(columns):
            series = []
            for j in range(len(self.data_list)):
                series.append(self.data_list[j][i])
            self.dataframe[column] = series
        self.dataframe['Events'] = self.events()
        self.dataframe = self.dataframe.astype({'Time': float, 'Thrust': float, 'Flight State': str, 'Events': str})

    def sim_to_apogee(self):
        while self.velocity >= 0:
            self.rkt_rk4_step()
            self.update_agl()

            self.time += self.dt

    def copy_dataframe(self):
        self.dataframe.to_clipboard(index=False)

    def simulate_to_ground(self):
        while self.height_agl >= 0:
            # adding data to a list for csv file

            # Update height + velocity using the rk4
            self.rkt_rk4_step()
            # Convert asl to agl
            self.update_agl()

            self.datalist_update()

            # output the values with space between them
            # Done: setup csv file export using pandas (ask ChatGPT about it)
            # numpy is good for making the arrays
            # TODO: decide between MatPlotLib and Sheets/Excel for presentation of data

            # print(rocket.height_agl, ",", rocket.velocity, ",",
            #      rocket.acceleration(rocket.height_agl, rocket.velocity, current_time), ",",
            #      current_time, ",", rocket.mass(current_time), ",",
            #      rocket.drag_setup.calculate_drag_force(rocket.velocity, rocket.height_agl))

            self.time += self.dt
        self.dataframe_update()
