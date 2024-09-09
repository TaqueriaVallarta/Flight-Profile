from math import pi, exp, sqrt


def base_cross_area(body_diameter, fin_thickness, fin_height):
    return (pi * (body_diameter / 2) ** 2) + 3 * fin_height * fin_thickness


# Drag Force, takes in what you would expect
def drag_force(cross_area, air_density, drag_coef, velocity):
    return cross_area * air_density * drag_coef * (velocity ** 2)


# Self-Explanatory
def inches_to_meters(inches):
    return (inches * 2.54) / 100


# Takes in the input/initial values and has methods to calculate other stuff
class Atmosphere:
    def __init__(self, temp_0, p_0, h_0):
        self.temp_0 = temp_0  # Initial temperature in Kelvin
        self.p_0 = p_0  # Initial pressure in Pascals
        self.h_0 = h_0  # Initial altitude in meters
        self.M = 0.0289652  # Molar Mass of Dry Air, kg/mol
        self.R = 8.3144626  # Universal Gas Constant J/K*mol
        self.g = 9.81  # Gravitational acceleration, m/s^2
        self.L = 0.0065  # Temperature lapse rate, K/m
        self.T0 = 288.15  # Standard temperature, K
        self.U = 11000  # Tropopause height, m
        self.H_tp = 6500  # measured in meters (got from wikipedia)
        self.gamma = 1.4  # measured for air at 0° C, TODO: find any differing values

    def temperature(self, h):
        """Calculate the temperature at a given altitude h."""
        if h >= self.U:
            return self.temp_0 - self.L * (self.U - self.h_0)
        else:
            return self.temp_0 - self.L * (h - self.h_0)

    def pressure(self, h):
        """Calculate the pressure at a given altitude h."""
        temp = self.temperature(h)
        if h >= self.U:
            return (self.p_0 * (1 - (temp / self.temp_0)) ** ((self.g * self.M) / (self.L * self.R))
                    * exp(-(h - self.U) / self.H_tp))
        else:
            return self.p_0 * (1 - (temp / self.temp_0)) ** ((self.g * self.M) / (self.L * self.R))

    def density(self, h):
        """Calculate the air density at a given altitude h."""
        temp = self.temperature(h)
        pressure = self.pressure(h)
        return pressure / ((self.R / self.M) * temp)

    def speed_of_sound(self, h):
        return sqrt(1.4 * self.R * self.temperature(h) / self.M)


class DragSetup:
    def __init__(self, atmosphere, body_diameter, fin_thickness, fin_height, drag_coef):
        self.atmosphere = atmosphere  # Instance of Atmosphere class
        self.body_diameter = body_diameter  # Diameter of the rocket body in meters
        self.fin_thickness = fin_thickness  # Thickness of the fins in meters
        self.fin_height = fin_height  # Height of the fins in meters
        self.drag_coef = drag_coef  # Drag coefficient
        self.cross_area = base_cross_area(body_diameter, fin_thickness, fin_height)  # Cross-sectional area

    def calculate_drag_force(self, velocity, altitude):
        """Calculate the drag force at a given velocity and altitude."""
        air_density = self.atmosphere.density(altitude)
        return drag_force(self.cross_area, air_density, self.drag_coef, velocity)


# in future maybe make this a class, with every all ready to go for simulation
def main():
    pressure_0 = 101125
    temperature_0 = 288.15
    height_0 = 0
    atmo = Atmosphere(temperature_0, pressure_0, height_0)

    diameter = inches_to_meters(8)
    fin_thickness = inches_to_meters(.5)
    fin_height = inches_to_meters(12)

    drag_setup = DragSetup(atmo, diameter, fin_thickness, fin_height, drag_coef=0.5)



