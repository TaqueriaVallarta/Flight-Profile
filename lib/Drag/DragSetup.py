from math import pi, exp, sqrt, copysign, pow
from lib.Recovery import Parachute
import pandas as pd
import numpy as np

# TODO: setup drag reduction due to exhaust plume
def base_cross_area(body_diameter, fin_thickness, fin_height):
    return (pi * (body_diameter / 2) ** 2) + 3 * fin_height * fin_thickness


# Drag Force, takes in what you would expect
def drag_force(cross_area, air_density, drag_coef, velocity):
    return .5 * cross_area * air_density * drag_coef * (velocity ** 2)



# Takes in the input/initial values and has methods to calculate other stuff
class Atmosphere:
    def __init__(self, temp_0, height_0):
        # Constants
        self.air_mol_weight = 28.9644    # Molecular weight of air [g/mol]
        self.density_sea_level = 1.225   # Density at sea level [kg/m³]
        self.pressure_sea_level = 101325 # Pressure at sea level [Pa]
        self.gamma = 1.4                 # Adiabatic index
        self.g = 9.81           # Gravitational acceleration [m/s²]
        self.R = 287.053                 # Specific gas constant for air [J/(kg·K)]
        self.gas_constant = 8.31432      # Universal gas constant [J/(mol·K)]
        self.h_0 = 1348
        self.t_0 = 300.1
        # Atmospheric layers and related data
        self.altitudes = [0, 11000, 20000, 32000, 47000, 51000, 71000, 84852]
        self.pressures_rel = [1, 0.22336, 0.05403, 0.00857, 0.00109, 0.00066, 0.000039, 0.0000037]
        self.temperatures = [288.15, 216.65, 216.65, 228.65, 270.65, 270.65, 214.65, 186.946]
        self.temp_grads = [-6.5, 0, 1, 2.8, 0, -2.8, -2, 0]  # Temperature gradient [K/km]
        self.gMR = self.g * self.air_mol_weight / self.gas_constant

        # Adjust base sea level temperature
        self.t_0 = self.t_0-self.temp_grads[0]*self.h_0/1000 # K

    def _calculate_base_values(self, height):
        # Ensure altitude is within valid range
        if height < -5000 or height > 86000:
            raise ValueError("Altitude must be between -5000 and 86000 meters.")

        # Determine the atmospheric layer
        i = 0
        while height > self.altitudes[i + 1]:
            i += 1
            if i > len(self.altitudes)-2:
                raise ValueError("Too High")


        base_temp = self.temperatures[i]
        temp_grad = self.temp_grads[i] / 1000  # Convert K/km to K/m
        pressure_rel_base = self.pressures_rel[i]
        delta_altitude = height - self.altitudes[i]

        # Calculate temperature at altitude

        temperature = base_temp + temp_grad * delta_altitude

        # Calculate relative pressure at altitude
        if abs(temp_grad) < 1e-10:  # No temperature gradient
            pressure_relative = pressure_rel_base * exp(-self.gMR * delta_altitude/1000 / base_temp)
        else:
            pressure_relative = pressure_rel_base * pow(base_temp / temperature, self.gMR / 1000 / temp_grad)

        # Adjust temperature for sea level input
        temperature += (self.t_0 - 288.15)

        return temperature, pressure_relative

    def temperature(self, height):
        """Returns the temperature at a given altitude in Kelvin."""
        temperature, _ = self._calculate_base_values(height)
        return temperature

    def pressure(self, height):
        """Returns the pressure at a given altitude in Pascals."""
        temperature, pressure_relative = self._calculate_base_values(height)
        return pressure_relative * self.pressure_sea_level

    def density(self, height):
        """Returns the density at a given altitude in kg/m³."""
        temperature, pressure_relative = self._calculate_base_values(height)
        return self.density_sea_level * pressure_relative * 288.15 / temperature

    def speed_of_sound(self, height):
        """Returns the speed of sound at a given altitude in m/s."""
        temperature, _ = self._calculate_base_values(height)
        return sqrt(self.gamma * self.R * temperature)


# Makes DragSetup so that the drag body is made. Drag Coef may end up being a function, we'll see
# Initializes Drag with US Standard Atmosphere and 8 inch body tube
class DragSetup:
    def __init__(self, fin_thickness, fin_height, drag_coef, reefed_parachute: Parachute, main_parachute: Parachute,
                 temp_0=288.15, height_0 = 0,
                 body_diameter=8 * .0252):
        self.atmosphere = Atmosphere(temp_0, height_0)  # Instance of Atmosphere class
        self.body_diameter = body_diameter  # Diameter of the rocket body in meters
        self.fin_thickness = fin_thickness  # Thickness of the fins in meters
        self.fin_height = fin_height  # Height of the fins in meters
        self.drag_coef = drag_coef  # Drag coefficient
        self.cross_area = base_cross_area(body_diameter, fin_thickness, fin_height)  # Cross-sectional area
        self.reefed_parachute = reefed_parachute
        self.main_parachute = main_parachute
        self.df = pd.read_csv("C:/Users/andre/OneDrive/Documents/GitHub/Flight-Profile/lib/Drag/DragCoefCurve.CSV")

    def coef(self, mach_number):
        power_off = np.interp(mach_number, self.df['Mach'], self.df['CD Power-Off'])
        power_on = np.interp(mach_number, self.df['Mach'], self.df['CD Power-On'])
        return power_on, power_off

    def calculate_drag_force(self, velocity, height, time, burn_time):
        """Calculate the drag force at a given velocity and altitude."""
        recommended_dt = .05
        mach = velocity/self.atmosphere.speed_of_sound(height)
        self.drag_coef = self.coef(mach)[1]
        if time <= burn_time:
            self.drag_coef = self.coef(mach)[0]

        if velocity < 0:
            if (height - self.atmosphere.h_0) <= self.main_parachute.deployment_altitude:
                if not self.main_parachute.DeployStatus:
                    self.main_parachute.DeployStatus = True
                    self.main_parachute.DeployTime = time
                self.cross_area, recommended_dt = self.main_parachute.cross_area(time)
                self.drag_coef = self.main_parachute.drag_coefficient
            else:
                if not self.reefed_parachute.DeployStatus:
                    self.reefed_parachute.DeployStatus = True
                    self.reefed_parachute.DeployTime = time
                self.cross_area, recommended_dt = self.reefed_parachute.cross_area(time)
                self.drag_coef = self.main_parachute.drag_coefficient

        air_density = self.atmosphere.density(height)
        return (drag_force(self.cross_area, air_density, self.drag_coef, velocity) * copysign(1, -velocity),
                recommended_dt)
