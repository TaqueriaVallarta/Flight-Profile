import numpy as np
from scipy.integrate import solve_ivp
import sympy as sp
import matplotlib.pyplot as plt
import math
# Critical properties of nitrous oxide (constants)
tCrit = 309.57  # Critical temperature in Kelvin
pCrit = 72.51   # Critical pressure in bar
rhoCrit = 452.0 # Critical density in kg/m^3

# Define symbols for constants
P_tank = sp.Symbol('P_tank')  # Pressure in bar
m_total = sp.Symbol('m_total')  # Total mass in kg
V_tank = sp.Symbol('V_tank')  # Volume in m^3
T = sp.Symbol('T')  # Temperature in Kelvin

# Define symbols for other parameters
K_inj = sp.Symbol('K_inj')
K_fit = sp.Symbol('K_fit')
rho = sp.Symbol('rho')  # Density constant for injector calculations
A_tank = sp.Symbol('A_tank')
A_manifold = sp.Symbol('A_manifold')
A_injector = sp.Symbol('A_injector')
A_fit = sp.Symbol('A_fit')
N_inj = sp.Symbol('N_inj')
N_fit = sp.Symbol('N_fit')
m_dot_fit = sp.Function('m_dot_fit')(sp.Symbol('t'))
m_dot_injector = sp.Function('m_dot_injector')(sp.Symbol('t'))
m_dot_total = sp.Function('m_dot_total')(sp.Symbol('t'))
m_liquid = sp.Function('m_liquid')(sp.Symbol('t'))
m_vapour = sp.Function('m_vapour')(sp.Symbol('t'))

# Initial conditions (numeric values)
P_tank_val = 800 * 0.0689476  # Convert from psi to bar
m_total_val = 64  # kg
V_tank_val = 95.562497 / 1000  # Convert from liters to m^3
T_val = 300  # Kelvin

# Set constants based on previous method
K_inj_val = sp.sqrt(1 / 0.63)
K_fit_val = sp.sqrt(1 / 0.7)
A_tank_val = math.pi * ((4 - 0.25) * 0.0254) ** 2  # m^2
A_manifold_val = math.pi * (0.69 / 2 * 0.0254) ** 2  # m^2
N_inj_val = 16
N_fit_val = 4
A_injector_val = math.pi * (0.1 / 2 * 0.0254) ** 2  # m^2
A_fit_val = math.pi * (0.19 / 2 * 0.0254) ** 2  # m^2

# Define functions for thermodynamic parameters
# Nitrous oxide vapor pressure, Bar
def nox_vp(temp):
    p = [1.0, 1.5, 2.5, 5.0]
    b = [-6.71893, 1.35966, -1.3779, -4.051]
    Tr = temp / tCrit
    rab = 1 - Tr

    if isinstance(temp, sp.Basic):
        p = sp.Matrix(p)
        b = sp.Matrix(b)
        shona = sum(b[i] * rab ** p[i] for i in range(len(p)))
        return pCrit * sp.exp(shona / Tr)
    else:
        # Numeric calculation
        shona = sum(b[i] * rab**p[i] for i in range(len(p)))
        return pCrit * math.exp(shona / Tr)

# Nitrous oxide saturated liquid density, kg/m^3
def nox_Lrho(temp):
    Tr = temp / tCrit
    rab = 1 - Tr
    if isinstance(temp, sp.Basic):
        b = sp.Matrix([1.72328, -0.8395, 0.5106, -0.10412])
        shona = sum(b[index] * rab**((index + 1) / 3) for index in range(len(b)))
        return rhoCrit * sp.exp(shona)
    else:
        # Numeric calculation
        b = [1.72328, -0.8395, 0.5106, -0.10412]
        shona = sum(b[index] * rab**((index + 1) / 3) for index in range(len(b)))
        return rhoCrit * math.exp(shona)

# Nitrous oxide saturated vapor density, kg/m^3
def nox_Vrho(temp):
    Tr = temp / tCrit
    rab = 1 / Tr - 1
    b = [-1.009, -6.2879, 7.50332, -7.90463, 0.629427]
    if isinstance(temp, sp.Basic):
        b = sp.Matrix(b)
        shona = sum(b[index] * rab**((index + 1) / 3) for index in range(len(b)))
        return rhoCrit * sp.exp(shona)
    else:
        # Numeric calculation
        shona = sum(b[index] * rab**((index + 1) / 3) for index in range(len(b)))
        return rhoCrit * math.exp(shona)

# Nitrous liquid enthalpy of vaporization, J/kg
def nox_enthV(T_Kelvin):
    bL = [-200.0, 116.043, -917.225, 794.779, -589.587]
    bV = [-200.0, 440.055, -459.701, 434.081, -485.338]
    Tr = T_Kelvin / tCrit
    rab = 1.0 - Tr
    if isinstance(T_Kelvin, sp.Basic):
        bL = sp.Matrix(bL)
        bV = sp.Matrix(bV)

    shonaL = bL[0]
    shonaV = bV[0]
    for dd in range(1, 5):
        shonaL += bL[dd] * rab ** (dd / 3.0)  # Saturated liquid enthalpy
        shonaV += bV[dd] * rab ** (dd / 3.0)  # Saturated vapor enthalpy

    return (shonaV - shonaL) * 1000.0  # Enthalpy change in J/kg

# Nitrous saturated liquid isobaric heat capacity, J/kg K
def nox_CpL(T_Kelvin):
    b = [2.49973, 0.023454, -3.80136, 13.0945, -14.518]
    Tr = T_Kelvin / tCrit
    rab = 1.0 - Tr
    if isinstance(T_Kelvin, sp.Basic):
        b = sp.Matrix(b)
    shona = 1.0 + b[1] / rab

    for dd in range(1, 4):
        shona += b[dd + 1] * rab ** dd

    return b[0] * shona * 1000.0  # Convert from KJ to J

# Define time variable
t = sp.symbols('t')

# Define time-dependent functions for pressures and mass flow rates
P_manifold = sp.Function('P_manifold')(t)
P_injector = sp.Symbol('P_injector')
P_injector_val = 500*0.0689476

# Define thermodynamic parameters as functions of time
H_v = nox_enthV(T)  # Enthalpy of nitrous oxide as a function of temperature
C_liquid = nox_CpL(T)  # Specific heat capacity of liquid nitrous
rho_liquid = nox_Lrho(T)  # Density of liquid nitrous
rho_vapour = nox_Vrho(T)  # Density of vapor nitrous

# Define the equations
# 1. Continuity equation for mass flow rates
continuity_eq = sp.Eq(m_dot_total.diff(t), m_dot_fit + m_dot_injector)

# 2. Tank to manifold pressure balance
tank_manifold_eq = sp.Eq(
    P_tank + (1 / (2 * rho_liquid * A_tank_val)) * (m_dot_total**2).diff(t),
    P_manifold + (1 / (2 * rho_liquid * A_manifold_val)) * (m_dot_injector**2).diff(t)
)

# 3. Injector flow dynamics
injector_eq = sp.Eq(
    P_injector - P_manifold,
    (1 / (2 * rho_liquid)) * (K_inj_val / (N_inj_val * A_injector_val)**2 - 1 / A_manifold_val) * (m_dot_injector**2).diff(t)
)

# 4. Fitting flow dynamics
fitting_eq = sp.Eq(
    P_injector - P_tank,
    (1 / (2 * rho_liquid)) * (K_fit_val / (N_fit_val * A_fit_val)**2 - 1 / A_tank_val) * (m_dot_fit**2).diff(t)
)

# 5. Mass conservation equation
mass_eq = sp.Eq(m_total, m_liquid + m_vapour)

# 6. Volume constraint for phase equilibrium
volume_eq = sp.Eq(m_liquid / rho_liquid + m_vapour / rho_vapour, V_tank)

# 7. Temperature change equation from energy balance
DeltaQ = sp.Function('DeltaQ')(t)  # Heat removed from liquid nitrous
DeltaT = -DeltaQ / (m_liquid * C_liquid)
temp_eq = sp.Eq(T.diff(t), DeltaT)

# 8. Mass update due to vaporization
m_liquid_new = (V_tank - m_total / rho_vapour) / (1 / rho_liquid - 1 / rho_vapour)
m_v = m_liquid - m_liquid_new

# Optional: stopping condition
stop_condition = sp.Piecewise((0, m_v < 0), (m_v, m_v >= 0))

# Combine equations into a system
equations = [
    continuity_eq,
    tank_manifold_eq,
    injector_eq,
    fitting_eq,
    mass_eq,
    volume_eq,
    temp_eq
]

# Display the system of equations
for i, eq in enumerate(equations, 1):
    print(f"Equation {i}:")
    print(sp.latex(eq))

lhs = []
rhs = []

for eq in equations:
    lhs.append(eq.lhs)
    rhs.append(eq.rhs)


# Create a function to evaluate the equations numerically
def evaluate_system(t, y):
    # Create a dictionary to map variables to their values
    variables = {
        m_total: y[0],
        T: y[1],
        P_manifold: y[2],
        m_liquid: y[3],
        m_vapour: y[4]
    }

    # Substitute values into the left-hand side of each equation and evaluate
    residuals = []
    for l, r in zip(lhs, rhs):
        # For equations involving P_injector, substitute its constant value
        if P_injector in l.free_symbols or P_injector in r.free_symbols:
            residuals.append(sp.N(
                l.subs(variables).subs(P_injector, P_injector_val) - r.subs(variables).subs(P_injector,
                                                                                            P_injector_val)))
        else:
            residuals.append(sp.N(l.subs(variables) - r.subs(variables)))

    return [float(res) for res in residuals]

m_liquid_val = 64

# Define the initial conditions
initial_conditions = [
    m_total_val,  # Total mass
    T_val,  # Temperature
    P_tank_val,  # Initial manifold pressure
    m_total_val,  # Initial mass of liquid nitrous
    0  # Initial mass of vapour (may be zero at start)
]

# Set the time span for the integration
time_span = (0, 10)  # For example, from t=0 to t=10 seconds
time_eval = np.linspace(*time_span, 100)  # Time points to store results

# Solve the system using solve_ivp
solution = solve_ivp(evaluate_system, time_span, initial_conditions, t_eval=time_eval)

# Extract results
time = solution.t
results = solution.y

# Plotting the results
plt.figure(figsize=(12, 8))
plt.subplot(3, 1, 1)
plt.plot(time, results[2], label='P_manifold')
plt.ylabel('Pressure (bar)')
plt.axhline(y=P_injector_val, color='r', linestyle='--', label='P_injector (constant)')
plt.legend()

plt.subplot(3, 1, 2)
plt.plot(time, results[3], label='m_liquid')
plt.plot(time, results[4], label='m_vapour')
plt.ylabel('Mass (kg)')
plt.legend()

plt.subplot(3, 1, 3)
plt.plot(time, results[1], label='Temperature (K)')
plt.xlabel('Time (s)')
plt.ylabel('Temperature (K)')
plt.legend()

plt.tight_layout()
plt.show()
