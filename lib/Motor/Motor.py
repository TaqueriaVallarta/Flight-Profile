import numpy as np
from numpy import sqrt, pi
from scipy import integrate, optimize
from scipy.optimize import least_squares, fsolve
from lib.Motor.PlotFileRead import load_plt_to_dataframe
from pint import UnitRegistry, Quantity
from matplotlib import pyplot as plt
from rocketcea.cea_obj import CEA_Obj
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

ureg = UnitRegistry()
from rocketcea.cea_obj import CEA_Obj


class Motor:

    def __init__(self, m_other, burn_time, tank_length = 3.35):
        # Constants (as placeholders)
        self.initial_OF = None
        self.OF_ideal = 6.5
        self.initial_grain_radius = None
        self.grain_length = None
        self.CEA = CEA_Obj(fuelName='HTPB',oxName='N2O')

        self.tank_length = tank_length * ureg.meters
        self.tank_thickness = (.25 * ureg.inches).to_base_units()
        self.tank_outer_radius = (4 * ureg.inches).to_base_units()
        self.tank_inner_radius = self.tank_outer_radius - self.tank_thickness

        self.rho_tank = 2700 * ureg.kg / ureg.meter**3 # T6-6061 kg/m^3

        self.rho_ox = 772.25 * ureg.kg / ureg.meter**3 # N2O kg/m^3
        self.rho_fuel = 940 * ureg.kg / ureg.meter**3 # HTPB kg/m^3
        self.ullage = 1.1 # fraction of total tank volume to usable tank volume

        self.burn_time = burn_time*ureg.seconds # seconds
        self.tank_volume = pi*self.tank_length*(self.tank_outer_radius**2-self.tank_inner_radius**2)
        self.tank_inner_volume = pi*self.tank_length*self.tank_inner_radius**2
        self.oxidizer_mass = self.rho_ox*self.tank_inner_volume / self.ullage
        self.ox_flow = self.oxidizer_mass / self.burn_time
        self.tank_mass = self.rho_tank*self.tank_volume
        self.chamber_pressure = (500 * ureg.lbf / ureg.inch**2).to_base_units()
        self.exit_pressure = 60000 * ureg.N / ureg.meter**2
        self.n = 0.364  # coefficient
        self.m = 0.293  # coefficient
        self.a = (.07577*10**(3*self.m-self.n-3)) * ureg.meter**(1-self.m+2*self.n) * ureg.seconds**(self.n-1) / ureg.kg**(self.n)

        self.outer_grain_radius = (7.25/2 * ureg.inches).to_base_units()
        self.final_grain_thickness = (.25*ureg.inches).to_base_units()
        self.final_grain_radius = self.outer_grain_radius - self.final_grain_thickness
        self.length_radius_solver()

        self.throat_area_calced = self.throat_area()

        self.area_ratio = self.eps()
        self.exit_area = self.area_ratio * self.throat_area_calced
        if type(m_other)!=Quantity:
            m_other *= ureg.kilograms
        self.other_mass = m_other # other mass
        self.extra_fuel_mass = self.grain_length*self.rho_fuel*pi*(self.outer_grain_radius**2-self.final_grain_radius**2)
        self.dry_mass = self.tank_mass + self.extra_fuel_mass + self.other_mass


    def update_self(self):
        if type(self.burn_time) != Quantity:
            self.burn_time = self.burn_time * ureg.seconds
        if type(self.other_mass) != Quantity:
            self.other_mass = self.other_mass * ureg.kilograms
        if type(self.exit_pressure) != Quantity:
            self.exit_pressure = self.exit_pressure * ureg.newtons / ureg.meter**2
        self.outer_grain_radius = (7.25/2 * ureg.inches).to_base_units()
        self.final_grain_thickness = (.25*ureg.inches).to_base_units()
        self.final_grain_radius = self.outer_grain_radius - self.final_grain_thickness
        self.ox_flow = self.oxidizer_mass / self.burn_time
        self.length_radius_solver()
        self.area_ratio = self.eps()
        self.throat_area_calced = self.throat_area()
        self.exit_area = self.area_ratio * self.throat_area_calced
        self.extra_fuel_mass = self.grain_length * self.rho_fuel * pi * (
                    self.outer_grain_radius ** 2 - self.final_grain_radius ** 2)
        self.dry_mass = self.tank_mass + self.extra_fuel_mass + self.other_mass

    def v_eq(self, time, ambient_pressure, fudge_factor):
        fac_CR = self.contraction_ratio(time)
        self.CEA.fac_CR = fac_CR
        Isp = self.CEA.estimate_Ambient_Isp(Pc=self.chamber_pressure.magnitude, MR=self.OF_t(time).magnitude, eps=self.area_ratio, Pamb=ambient_pressure)[0]
        return Isp * 9.81 * fudge_factor

    def eps(self):
        return self.CEA.get_eps_at_PcOvPe(Pc=self.chamber_pressure.to(ureg.psi).magnitude, MR=self.OF_ideal, PcOvPe=(self.chamber_pressure/self.exit_pressure).magnitude)


    def OF_t(self, time):
        return self.ox_flow / self.fuel_flow(time)

    def radius(self,time):
        if type(time) != Quantity:
            time = time * ureg.seconds
        term1 = self.a * (2 * self.n + 1) * self.grain_length ** self.m * (self.ox_flow / pi) ** self.n
        term1 = term1.magnitude
        time = time.magnitude
        initial_grain_radius = self.initial_grain_radius.magnitude
        radius = (term1*time + initial_grain_radius ** (2 * self.n + 1))**(1/(2*self.n + 1)) * ureg.meter
        return radius

    def mass(self, time):
        if time <= self.burn_time.magnitude:
            oxmass = self.oxidizer_mass-(self.ox_flow*time*ureg.seconds)
            fuelmass = self.fuel_mass(time)
            return (oxmass + fuelmass + self.dry_mass).magnitude
        return self.dry_mass.magnitude

    def mean_time(self, func):
        return integrate.quad(func, 0, self.burn_time.magnitude)[0] / self.burn_time.magnitude


    def fuel_mass(self, time):
        return self.rho_fuel*pi*self.grain_length*(self.final_grain_radius**2-self.radius(time)**2)

    def fuel_flow(self, time: Quantity):
        if type(time)!=Quantity:
            time *= ureg.seconds
        time.ito_base_units()
        term1 = (2 * pi * self.rho_fuel * self.grain_length ** (1 + self.m)).magnitude
        radius = (self.radius(time)).magnitude
        term2 = (self.a*(self.ox_flow/pi)**self.n*radius**((1-2*self.n)/(1+2*self.n))).magnitude
        return term1*term2 * ureg.kg / ureg.second

    def mass_flow(self, time):
        fuel_flow = self.fuel_flow(time)
        return fuel_flow+self.ox_flow


    def length_radius_solver(self):

        burn_time = self.burn_time.magnitude

        r_f = self.final_grain_radius
        def equations(variables):
            grain_length, initial_grain_radius= variables
            self.grain_length = grain_length * ureg.meter
            self.initial_grain_radius = initial_grain_radius * ureg.meter
            grain_length *= ureg.meters
            initial_grain_radius *= ureg.meters

            eq1 = 200*(self.radius(burn_time) - self.final_grain_radius).magnitude
            eq2 = self.OF_ideal - self.ox_flow.magnitude * self.mean_time(lambda time: self.fuel_flow(time).magnitude**-1)
            return [eq1, eq2]

        initial_guess = [.8, .05]
        bounds = [[.4,.01], [2, r_f.magnitude]]
        solution = least_squares(equations, initial_guess, bounds=bounds)


        self.grain_length, self.initial_grain_radius = solution['x']
        self.grain_length *= ureg.meters
        self.initial_grain_radius *= ureg.meters
        return solution['x']

    def exit_area_calc(self):
        gamma = lambda time: self.values(self.OF_t(time))[2]
        def mach(time):
            ratio = (self.exit_pressure/self.chamber_pressure).magnitude
            return sqrt(2/(gamma(time)-1)*(ratio**(-(gamma(time)-1)/gamma(time))-1))

        mach = self.mean_time(mach)
        gamma = self.mean_time(gamma)
        term1 = ((gamma+1)/2)**(-(gamma+1)/2/(gamma-1))
        term2 = (1+((gamma-1)/2)*mach**2)**((gamma+1)/2/(gamma-1))

        ratio = term1*term2 / mach
        return ratio * self.throat_area_calced

    def exit_mach(self, time: Quantity):
        area_ratio = self.exit_area / self.throat_area_calced
        gamma = self.values(self.OF_t(time))[2]

        # Precompute constant factor for efficiency
        constant_factor = ((gamma + 1) / 2) ** (-(gamma + 1) / (2 * (gamma - 1)))

        # Function to calculate area ratio for given Mach number
        def area_ratio2(M_e):
            return constant_factor * (1 + (gamma - 1) / 2 * M_e ** 2) ** ((gamma + 1) / (2 * (gamma - 1))) / M_e

        # Function, when it equals 0 M_e is solved
        def func(M_e):
            return (area_ratio - area_ratio2(M_e)).magnitude

        # Solve for exit Mach number, using an initial guess
        mach_exit = fsolve(func, np.array([3]))[0]

        return mach_exit

    def exit_vel(self, time):
        R = 8314 * ureg.joules / ureg.kmol / ureg.kelvin
        molar_mass, temp, gamma = self.values(self.OF_t(time))
        molar_mass *= ureg.kg / ureg.kmol
        temp *= ureg.kelvin
        v_e =  self.exit_mach(time)*sqrt(gamma*R*temp/molar_mass)
        return v_e.to_base_units()



    def throat_area(self):
        # Constants and time-independent values
        burn_time = self.burn_time.magnitude
        R_universal = 8314 * ureg.joules / (ureg.kelvin * ureg.kmol)
        chamber_pressure_inv = 1 / self.chamber_pressure
        # Define functions to compute required values at a given time
        def values_at_time(time):
            return self.values(self.OF_t(time))

        # Precompute reusable values
        def area(time):
            # Extract needed values
            values = values_at_time(time)
            molar_mass = values[0] * ureg.kg / ureg.kmol
            temp = values[1] * ureg.kelvin
            gamma = values[2]

            # Compute derived quantities
            R_specific = R_universal / molar_mass
            mdot = self.mass_flow(time * ureg.second)
            temp_sqrt = sqrt(temp)
            gamma_sqrt = sqrt(R_specific / gamma)

            # Compute constant part of the formula for the area ratio
            term1 = ((gamma + 1) / 2) ** ((gamma + 1) / (2 * (gamma - 1)))

            # Calculate area at the given time
            return mdot * temp_sqrt * chamber_pressure_inv * gamma_sqrt * term1

        # Minimize the negative area to find the maximum throat area
        result = optimize.minimize_scalar(lambda time: area(time), bounds=[0, burn_time], method='bounded')

        # Calculate max throat area at the optimal time
        max_throat_area = area(result['x']).to_base_units()

        return max_throat_area.to_base_units()

    def values(self, of_value):
        eps = self.eps()
        psi = self.chamber_pressure.to(ureg.lbf / ureg.inch ** 2).magnitude

        mass, gamma = self.CEA.get_Throat_MolWt_gamma(Pc=psi,
                                                      MR=of_value, eps=eps)
        temp = self.CEA.get_Temperatures(Pc=psi, MR=of_value, eps=eps)[2]
        return mass, temp, gamma

    def thrust(self, time, ambient_pressure, fudge_factor):
        if time*ureg.seconds > self.burn_time:
            return 0

        return self.v_eq(time, ambient_pressure, fudge_factor)*self.mass_flow(time).magnitude

        thrust_mass_flow = (self.mass_flow(time)*self.exit_vel(time, fudge_factor)).to_base_units()
        pressure_force = ((self.exit_pressure - (ambient_pressure * ureg.newton/ ureg.meter**2))*self.exit_area).to_base_units()
        return (thrust_mass_flow+pressure_force).magnitude

    def contraction_ratio(self, time):
        ratio = (pi*self.radius(time*ureg.seconds)**2/self.throat_area_calced).magnitude
        return ratio

    def initial_outputs(self):
        logging.info(f"Grain Length: {self.grain_length:.3f}")
        logging.info(f"Initial Radius (in): {self.initial_grain_radius.to(ureg.inches):.3f}")
        logging.info(f"Ox Flow: {self.ox_flow:.3f}")
        logging.info(f"Throat Area: {self.throat_area_calced.to(ureg.inches**2):.3f}")
        logging.info(f"Throat Radius: {(self.throat_area_calced.to(ureg.inches**2)/pi)**.5:.3f}")
        logging.info(f"Initial OF Ratio: {self.OF_t(0):.3f}")
        logging.info(f"Exit Area: {self.exit_area.to(ureg.inches**2):.3f}")
        logging.info(f"Exit Radius: {(self.exit_area.to(ureg.inches**2)/pi)**.5}:.3f")
        logging.info(f"Mean OF Ratio: {self.mean_time(self.OF_t):.3f}")
        logging.info(f"Mean Exit Velocity: {self.mean_time(lambda time: self.exit_vel(time).magnitude)}")
        logging.info(f"Mean Exit Mach: {self.mean_time(self.exit_mach)}")
        logging.info(f"Mean Contraction Ratio: {self.mean_time(self.contraction_ratio):.3f}")
        logging.info(f"Expansion Ratio: {self.exit_area/self.throat_area_calced:.2f}")
        logging.info(f"Mean Gamma: {self.mean_time(lambda time: self.values(self.OF_t(time))[2]):.3f}")
        logging.info(f"Mean Molar Mass: {self.mean_time(lambda time: self.values(self.OF_t(time))[0]):.2f}")
        logging.info(f"Mean Temperature: {self.mean_time(lambda time: self.values(self.OF_t(time))[1]):.1f}")
        logging.info(f"Dry Mass: {self.tank_mass+self.extra_fuel_mass+self.other_mass:.2f}")
        logging.info(f"Fuel Mass: {self.fuel_mass(0):.2f}")
        logging.info(f"Wet Mass: {self.oxidizer_mass+self.dry_mass+self.fuel_mass(self.burn_time):.2f}")
        logging.info(f"Inert Mass Fraction: {self.dry_mass/(self.oxidizer_mass+self.dry_mass+ self.fuel_mass(self.burn_time))}")

if __name__ == '__main__':
    motor = Motor(40, 22)
    motor.initial_outputs()