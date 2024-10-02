from types import NoneType

from lib.Drag.DragSetup import DragSetup
from lib.Motor.Motor import Motor
from lib.rk4 import rk4_step
from pandas import DataFrame
import json

class Rocket:
    def __init__(self, drag_setup: DragSetup, dry_mass, time=0,
                 dt=.1, initial_height_msl=0.0):
        self.burn_time = 27
        self.drag_setup = drag_setup  # drag setup class
        self.motor = Motor(dry_mass, self.burn_time, 200)  # motor class
        self.dry_mass = dry_mass  # dry mass in kg
        self.initial_height_asl = initial_height_msl  # Initial Height in m ASL
        self.height_agl = 0  # height above ground level
        self.height_msl = initial_height_msl  # height above ground level
        self.velocity = 0
        self.gravity = self.drag_setup.atmosphere.g
        self.time = time
        self.dt = dt
        self.data_list = []
        self.dataframe = DataFrame(
            columns=['Time', 'Height AGL', 'Height MSL', 'Velocity',
                     'Acceleration',
                     'Mass', 'Thrust', 'Drag', 'Air Density', 'Air Pressure',
                     'Air_Temperature', 'Speed of Sound', 'Drag Coefficient', 'Mach',
                     'Cross-sectional Area', 'Flight State', 'Weight', 'Total Force'])
        self.dataframe: DataFrame
        self.values = {
            "temp_0": self.drag_setup.atmosphere.temp_0,
            "p_0": self.drag_setup.atmosphere.p_0,
            "h_0": self.drag_setup.atmosphere.h_0,
            "body_diameter": self.drag_setup.body_diameter,
            "fin_thickness": self.drag_setup.fin_thickness,
            "fin_height": self.drag_setup.fin_height,
            "drag_coef": self.drag_setup.drag_coef,
            "cross_area_reefed": self.drag_setup.reefed_parachute.surface_area,
            "drag_coef_reefed": self.drag_setup.reefed_parachute.drag_coefficient,
            "inflation_time_reefed": self.drag_setup.reefed_parachute.inflation_time,
            "cross_area_main": self.drag_setup.main_parachute.surface_area,
            "drag_coef_main": self.drag_setup.main_parachute.drag_coefficient,
            "inflation_time_main": self.drag_setup.main_parachute.inflation_time,
            "deployment_altitude": self.drag_setup.main_parachute.deployment_altitude,
            "dry_mass": self.dry_mass,
            "Isp": self.motor.Isp,
            "burn_time": self.motor.burn_time,
            "outer_grain_radius": self.motor.outer_grain_radius,
            "final_thickness": self.motor.final_thickness,
            "volumetric_loading": self.motor.VF
        }

    def set_vals_to_vars(self):
        # Synchronize dictionary to ensure up-to-date values
        self.values["temp_0"] = self.drag_setup.atmosphere.temp_0
        self.values["p_0"] = self.drag_setup.atmosphere.p_0
        self.values["h_0"] = self.drag_setup.atmosphere.h_0
        self.values["body_diameter"] = self.drag_setup.body_diameter
        self.values["fin_thickness"] = self.drag_setup.fin_thickness
        self.values["fin_height"] = self.drag_setup.fin_height
        self.values["drag_coef"] = self.drag_setup.drag_coef
        self.values["cross_area_reefed"] = self.drag_setup.reefed_parachute.surface_area
        self.values["drag_coef_reefed"] = self.drag_setup.reefed_parachute.drag_coefficient
        self.values["inflation_time_reefed"] = self.drag_setup.reefed_parachute.inflation_time
        self.values["cross_area_main"] = self.drag_setup.main_parachute.surface_area
        self.values["drag_coef_main"] = self.drag_setup.main_parachute.drag_coefficient
        self.values["inflation_time_main"] = self.drag_setup.main_parachute.inflation_time
        self.values["deployment_altitude"] = self.drag_setup.main_parachute.deployment_altitude
        self.values["dry_mass"] = self.dry_mass
        self.values["Isp"] = self.motor.Isp
        self.values["burn_time"] = self.motor.burn_time
        self.values["outer_grain_radius"] = self.motor.outer_grain_radius
        self.values["final_thickness"] = self.motor.final_thickness
        self.values["volumetric_loading"] = self.motor.VF
        self.motor.dry_mass_rkt = self.dry_mass
        self.motor.update_self()
        self.drag_setup.main_parachute.start_surface_area = self.drag_setup.reefed_parachute.surface_area
        return self.values

    def set_vars_to_new(self, new_values: dict):
        # Update the values in both directions
        self.drag_setup.atmosphere.temp_0 = new_values.get("temp_0", self.drag_setup.atmosphere.temp_0)
        self.drag_setup.atmosphere.p_0 = new_values.get("p_0", self.drag_setup.atmosphere.p_0)
        self.drag_setup.atmosphere.h_0 = new_values.get("h_0", self.drag_setup.atmosphere.h_0)
        self.drag_setup.body_diameter = new_values.get("body_diameter", self.drag_setup.body_diameter)
        self.drag_setup.fin_thickness = new_values.get("fin_thickness", self.drag_setup.fin_thickness)
        self.drag_setup.fin_height = new_values.get("fin_height", self.drag_setup.fin_height)
        self.drag_setup.drag_coef = new_values.get("drag_coef", self.drag_setup.drag_coef)
        self.drag_setup.reefed_parachute.surface_area = new_values.get("cross_area_reefed",
                                                                       self.drag_setup.reefed_parachute.surface_area)
        self.drag_setup.reefed_parachute.drag_coefficient = new_values.get("drag_coef_reefed",
                                                                           self.drag_setup.reefed_parachute.drag_coefficient)
        self.drag_setup.reefed_parachute.inflation_time = new_values.get("inflation_time_reefed",
                                                                         self.drag_setup.reefed_parachute.inflation_time)
        self.drag_setup.main_parachute.surface_area = new_values.get("cross_area_main",
                                                                     self.drag_setup.main_parachute.surface_area)
        self.drag_setup.main_parachute.drag_coefficient = new_values.get("drag_coef_main",
                                                                         self.drag_setup.main_parachute.drag_coefficient)
        self.drag_setup.main_parachute.inflation_time = new_values.get("inflation_time_main",
                                                                       self.drag_setup.main_parachute.inflation_time)
        self.drag_setup.atmosphere.deployment_altitude = new_values.get("deployment_altitude",
                                                                        self.drag_setup.main_parachute.deployment_altitude)
        self.dry_mass = new_values.get("dry_mass", self.dry_mass)
        self.motor.Isp = new_values.get("Isp", self.motor.Isp)
        self.burn_time = new_values.get("burn_time", self.burn_time)
        self.motor.burn_time = self.burn_time
        self.motor.outer_grain_radius = new_values.get("outer_grain_radius", self.motor.outer_grain_radius)
        self.motor.final_thickness = new_values.get("final_thickness", self.motor.final_thickness)
        self.motor.VF = new_values.get("volumetric_loading", self.motor.VF)
        self.motor.dry_mass_rkt = self.dry_mass
        self.motor.update_self()
        self.drag_setup.main_parachute.start_surface_area = self.drag_setup.reefed_parachute.surface_area
        # Reflect changes in the internal dictionary
        self.values = new_values

    

    def mass(self, time):
        return self.motor.mass(time)

    def acceleration(self, height_asl, velocity, time):
        drag, self.dt = self.drag_setup.calculate_drag_force(velocity, height_asl, self.time)
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
                self.drag_setup.calculate_drag_force(self.velocity, self.height_msl, self.time)[0],
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
        return self.dataframe


    def sim_to_apogee(self):
        while self.velocity >= 0:
            self.rkt_rk4_step()
            self.update_agl()

            self.time += self.dt
        return self

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

    def get_values_from_files(self):
        with open('values.json', 'rb') as fp:
            values = json.load(fp)
        self.set_vars_to_new(values)
