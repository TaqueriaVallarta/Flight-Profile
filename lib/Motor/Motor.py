from math import sqrt, pi
import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
import logging

class Motor:
    def __init__(self, dry_mass_rkt, burn_time, Isp, vf=.875, OF=6.5):
        self.g0 = 9.81  # Gravity (m/s^2)
        self.Isp = Isp  # Specific Impulse
        self.Veq = self.g0 * self.Isp  # Equivalent Velocity
        self.rho_ox = 772.5  # Density of Nitrous (kg/m^3)
        self.rho_f = 940  # Density of HTPB (kg/m^3)
        self.dry_mass_rkt = dry_mass_rkt  # Dry Mass of Rocket in kg
        self.VF = vf  # Volumetric Loading Factor typical values in sutton (.8-.95)
        self.burn_time = burn_time
        self.OF = OF  # Oxidizer to Fuel ratio
        self.outer_grain_radius = (7.25 / 2) * (2.54 / 100)  # Outer grain radius (m)
        self.final_thickness = .25*2.54/100 # Final grain thickness (m)
        self.final_grain_radius = self.outer_grain_radius - self.final_thickness  # Final Grain Radius after burn (m)
        self.n = 0.346  # Coefficient for regression r\beg
        self.a0 = .417 / (10 ** (self.n + 3))

        # Calculate parameters that depend on acceleration
        self.acceleration, self.latex_equation, self.equation = self.solve_for_acceleration()

        # Values based on the calculated acceleration
        self.total_impulse = (self.acceleration * self.burn_time * self.dry_mass_rkt * self.Veq) / \
                             (self.Veq - self.acceleration * self.burn_time)
        self.mass_prop = self.total_impulse / self.Veq  # Propellant Total Mass (kg)
        self.mass_fuel = self.mass_prop / (1 + self.OF)  # Fuel Mass (kg)
        self.mass_ox = (self.mass_prop * self.OF) / (1 + self.OF)  # Oxidizer Mass (kg)
        self.mean_thrust = self.total_impulse / self.burn_time  # Mean Thrust (N)
        self.V_fuel = self.mass_fuel / self.rho_f  # Required Volume of Fuel (m^3)
        self.initial_grain_radius = sqrt(self.mass_fuel / (self.rho_f * pi * self.VF))  # Initial Grain Radius (m)
        self.grain_length = self.V_fuel / (
                pi * (self.final_grain_radius ** 2 - self.initial_grain_radius ** 2))  # Length of fuel grain (m)
        self.mass_extra_htpb = self.rho_f * self.grain_length * pi * (
                self.outer_grain_radius ** 2 - self.final_grain_radius ** 2)  # Leftover mass of HTPB
        self.wet_mass = self.mass_prop + self.dry_mass_rkt  # Wet mass of rocket (kg)

        # Injector Values initializing
        self.delta_p = 85 * 6894.776  # Change in pressure across injector (Pa)
        self.N = 16  # Number of Injectors
        self.A0 = (self.mass_fuel * self.OF) / (
                self.burn_time * sqrt(2 * self.delta_p * self.rho_ox))  # Equivalent Injector Area (m^2)
        self.K = 1.8  # Head Loss Coefficient
        self.inj_radius = sqrt(self.A0 * sqrt(self.K) / (pi * self.N))  # Injector Radius (m)
        self.mass_flow_ox = self.mass_ox / self.burn_time

        # Minimums and Maximums
        self.min_accel = 4.5 * self.g0
        self.min_length = (self.min_accel * self.burn_time * self.dry_mass_rkt * self.VF) / (
                pi * self.rho_f * self.final_grain_radius ** 2 * self.VF * (1 + self.OF) * (
                self.Veq - self.min_accel * self.burn_time) - self.min_accel * self.burn_time * self.dry_mass_rkt)
        self.max_length = 1.25  # Max length (1.25 meters)
        self.length = np.array([self.min_length, self.max_length])
        self.accel = (self.rho_f * self.length * pi * self.final_grain_radius ** 2 * (
                1 + self.OF) * self.Veq * self.VF) / \
                     (self.burn_time * ((
                                                self.VF + 1) * self.dry_mass_rkt + self.rho_f * self.length * pi * self.final_grain_radius ** 2 * (
                                                1 + self.OF) * self.VF))

        # Inert Mass Fraction
        self.f_inert = self.dry_mass_rkt / self.wet_mass

    def solve_for_acceleration(self):
        # Define the symbols
        V_F, r_f, rho_f, OF, V_eq, t_B, x, m_dry0, a0, n = sp.symbols('V_F r_f rho_f OF V_eq t_B x m_dry0 a0 n')

        # Define the left-hand side of the equation
        lhs = r_f ** (2 * n + 1)

        # Define the right-hand side of the equation
        rhs = (x / (V_eq - x * t_B)) ** n * (
                a0 * t_B * (2 * n + 1) * (m_dry0 * OF / (pi * (1 + OF))) ** n +
                (t_B * m_dry0 / ((rho_f * pi * V_F) * (1 + OF))) ** ((2 * n + 1) / 2) *
                (x / (V_eq - x * t_B)) ** (1 / 2)
        )

        # Full symbolic equation
        equation = sp.simplify(sp.Eq(lhs, rhs))

        # Display the equation
        sp.init_printing()  # This will enable pretty printing
        # Substitute values into the equation
        substituted_eq = equation.subs({
            V_F: self.VF,
            r_f: self.final_grain_radius,
            rho_f: self.rho_f,
            OF: self.OF,
            V_eq: self.Veq,
            t_B: self.burn_time,
            m_dry0: self.dry_mass_rkt,
            a0: self.a0,
            n: self.n
        })
        # Solve for x (the variable on the left-hand side)
        solution = sp.nsolve(substituted_eq, 5 * self.g0)
        return float(solution), sp.latex(substituted_eq), equation

    # This function is so that everything can just be resolvedd after updating the values ratehr than reinitializing the class
    def update_self(self):
        # Calculate parameters that depend on acceleration
        self.final_grain_radius = self.outer_grain_radius - self.final_thickness
        self.acceleration, self.latex_equation, self.equation = self.solve_for_acceleration()

        # Values based on the calculated acceleration
        self.total_impulse = (self.acceleration * self.burn_time * self.dry_mass_rkt * self.Veq) / \
                             (self.Veq - self.acceleration * self.burn_time)
        self.mass_prop = self.total_impulse / self.Veq  # Propellant Total Mass (kg)
        self.mass_fuel = self.mass_prop / (1 + self.OF)  # Fuel Mass (kg)
        self.mass_ox = (self.mass_prop * self.OF) / (1 + self.OF)  # Oxidizer Mass (kg)
        self.mean_thrust = self.total_impulse / self.burn_time  # Mean Thrust (N)
        self.V_fuel = self.mass_fuel / self.rho_f  # Required Volume of Fuel (m^3)
        self.initial_grain_radius = sqrt(self.mass_fuel / (self.rho_f * pi * self.VF))  # Initial Grain Radius (m)
        self.grain_length = self.V_fuel / (
                pi * (self.final_grain_radius ** 2 - self.initial_grain_radius ** 2))  # Length of fuel grain (m)
        self.mass_extra_htpb = self.rho_f * self.grain_length * pi * (
                self.outer_grain_radius ** 2 - self.final_grain_radius ** 2)  # Leftover mass of HTPB
        self.wet_mass = self.mass_prop + self.dry_mass_rkt  # Wet mass of rocket (kg)

        # Injector Values initializing
        self.delta_p = 85 * 6894.776  # Change in pressure across injector (Pa)
        self.N = 16  # Number of Injectors
        self.A0 = (self.mass_fuel * self.OF) / (
                self.burn_time * sqrt(2 * self.delta_p * self.rho_ox))  # Equivalent Injector Area (m^2)
        self.K = 1.8  # Head Loss Coefficient
        self.inj_radius = sqrt(self.A0 * sqrt(self.K) / (pi * self.N))  # Injector Radius (m)
        self.mass_flow_ox = self.mass_ox / self.burn_time

        # Minimums and Maximums
        self.min_accel = 4.5 * self.g0
        self.min_length = (self.min_accel * self.burn_time * self.dry_mass_rkt * self.VF) / (
                pi * self.rho_f * self.final_grain_radius ** 2 * self.VF * (1 + self.OF) * (
                self.Veq - self.min_accel * self.burn_time) - self.min_accel * self.burn_time * self.dry_mass_rkt)
        self.max_length = 1.25  # Max length (1.25 meters)
        self.length = np.array([self.min_length, self.max_length])
        self.accel = (self.rho_f * self.length * pi * self.final_grain_radius ** 2 * (
                1 + self.OF) * self.Veq * self.VF) / \
                     (self.burn_time * ((
                                                self.VF + 1) * self.dry_mass_rkt + self.rho_f * self.length * pi * self.final_grain_radius ** 2 * (
                                                1 + self.OF) * self.VF))

        # Inert Mass Fraction
        self.f_inert = self.dry_mass_rkt / self.wet_mass


    def initial_output(self):
        # Check if acceleration is within limits (considering self.accel is an array)
        accel_status = "within limits" if (
                self.min_accel <= self.acceleration <= np.max(self.accel)) else "out of limits"

        # Check if grain length is within outer boundaries
        grain_length_status = "within boundaries" if self.min_length <= self.grain_length <= self.max_length else "out of boundaries"

        # Conversion factors
        meter_to_feet = 3.28084  # 1 meter = 3.28084 feet
        kg_to_lb = 2.20462  # 1 kg = 2.20462 pounds

        # Convert lengths to feet and masses to pounds
        inj_diameter_inch = self.inj_radius * 2 * 39.37  # Injector diameter in inches
        initial_grain_radius_inch = self.initial_grain_radius * 39.37  # Initial grain radius in inches
        grain_length_feet = self.grain_length * meter_to_feet  # Grain length in feet
        fuel_mass_lb = self.mass_fuel * kg_to_lb  # Fuel mass in pounds
        ox_mass_lb = self.mass_ox * kg_to_lb  # Oxidizer mass in pounds
        extra_htpb_mass_lb = self.mass_extra_htpb * kg_to_lb  # Extra HTPB mass in pounds
        usable_mass_lb = (self.dry_mass_rkt - self.mass_extra_htpb) * kg_to_lb  # Usable mass in pounds

        # Print the output
        if accel_status == "within limits":
            logging.info(f"Acceleration is {accel_status} and is {self.acceleration:.2f} m/s^2 or {self.acceleration/self.g0:.2f} Gs")
        else:
            logging.warning(f"Acceleration is {accel_status} and is {self.acceleration:.2f} m/s^2 or {self.acceleration/self.g0:.2f} Gs")
        logging.info(f"Acceleration limits are {self.min_accel:.2f} m/s^2 to {np.max(self.accel):.2f} m/s^2")
        logging.info(f"Grain length is {grain_length_status} and is {self.grain_length:.2f} m or {grain_length_feet:.2f} ft")
        logging.info(f"Minimum Grain Length: {self.min_length:.2f} m")
        logging.info(f"Mean thrust: {self.mean_thrust:.2f} N")
        logging.info(f"Total impulse: {self.total_impulse:.2f} Ns")
        logging.info(f"Equivalent Injector Area: {self.A0*100*2:.2f} cm^2")
        logging.info(f"Initial grain radius: {initial_grain_radius_inch:.2f} inches")
        logging.info(f"Final grain radius: {self.final_grain_radius*100/2.54:.2f} inches")
        logging.info(f"Fuel mass: {self.mass_fuel:.2f} kg ({fuel_mass_lb:.2f} lbs)")
        logging.info(f"Oxidizer mass: {self.mass_ox:.2f} kg ({ox_mass_lb:.2f} lbs)")
        logging.info(f"Extra HTPB mass: {self.mass_extra_htpb:.2f} kg ({extra_htpb_mass_lb:.2f} lbs)")
        logging.info(
            f"Usable mass (rocket dry mass - extra HTPB): {self.dry_mass_rkt - self.mass_extra_htpb:.2f} kg ({usable_mass_lb:.2f} lbs)")
        logging.info(f"Equivalent injector area: {self.A0:.6f} m^2")
        logging.info(f"Inert Mass Fraction: {self.f_inert * 100:.1f}%")
        logging.info(f"Total Wet Mass: {self.wet_mass:.2f} kg")
        # Example usage

    def mass_fuel_time(self, time):
        # Calculate the first term inside the parentheses
        term_1 = (self.a0 * (2 * self.n + 1) * (
                    self.mass_flow_ox / pi) ** self.n * time) + self.initial_grain_radius ** (2 * self.n + 1)

        # Raise the term to the power of 2 / (2n + 1)
        term_1_powered = term_1 ** (2 / (2 * self.n + 1))

        # Subtract R_i^2 (initial grain radius squared)
        result = term_1_powered - self.initial_grain_radius ** 2

        # Multiply the result by pi, rho_f, and L_grain
        mass_fuel = pi * self.rho_f * self.grain_length * result

        return mass_fuel

    def mass_ox_time(self, time):
        return self.mass_flow_ox * time

    def mass(self, time):
        if time <= self.burn_time:
            return self.wet_mass - self.mass_fuel_time(time) - self.mass_ox_time(time)
        else:
            return self.wet_mass - self.mass_fuel_time(self.burn_time) - self.mass_ox_time(self.burn_time)

    def mass_flow_fuel(self, time):
        return 2 * pi * self.rho_f * self.grain_length * self.a0 * (self.mass_flow_ox / pi) ** self.n * (
                    self.a0 * (2 * self.n - 1) * (
                        self.mass_flow_ox / pi) ** self.n * time + self.initial_grain_radius ** (2 * self.n + 1)) ** (
                    (1 - 2 * self.n) / (1 + 2 * self.n))

    def mass_flow(self, time):
        return self.mass_flow_ox + self.mass_flow_fuel(time)

    def thrust(self, time):
        if time <= self.burn_time:
            return self.mass_flow(time) * self.Veq
        else:
            return 0

