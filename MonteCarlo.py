from main import initialize, Rocket
import numpy as np
import matplotlib.pyplot as plt

# Number of simulations
num_simulations = 5000

rocket1 = initialize()


def plusminus_x_percent(number, x):
    return number - number * x * .01, number + number * x * .01


# Define parameter variations (mean, standard deviation for normal distribution)
drag_coef_min, drag_coef_max = plusminus_x_percent(rocket1.drag_setup.drag_coef, 20)
wet_mass_min, wet_mass_max = plusminus_x_percent(rocket1.motor.wet_mass, 20)
burn_time_min, burn_time_max = plusminus_x_percent(rocket1.motor.burn_time, 20)
thrust_min, thrust_max = plusminus_x_percent(rocket1.motor.mean_thrust, 20)
p_0_min, p_0_max = plusminus_x_percent(rocket1.drag_setup.atmosphere.p_0, 2)
temp_0_min, temp_0_max = plusminus_x_percent(rocket1.drag_setup.atmosphere.temp_0, 2)

# Results storage
apogees = []
rockets = []

rocket: Rocket
for _ in range(num_simulations):
    rockets.append(initialize())

for rocket in rockets:
    # Randomly sample input parameters
    rocket.drag_setup.drag_coef = np.random.uniform(drag_coef_min, drag_coef_max)
    rocket.motor.wet_mass = np.random.uniform(wet_mass_min, wet_mass_max)
    rocket.motor.burn_time = np.random.uniform(burn_time_min, burn_time_max)
    rocket.motor.mean_thrust = np.random.uniform(thrust_min, thrust_max)
    rocket.drag_setup.atmosphere.p_0 = np.random.uniform(p_0_min, p_0_max)
    rocket.drag_setup.atmosphere.temp_0 = np.random.uniform(temp_0_min, temp_0_max)
    rocket.dry_mass = rocket.motor.wet_mass / 2

    # Recreate classes with random parameters

    # Simulate until apogee
    rocket.sim_to_apogee()

    # Record results
    apogees.append(rocket.height_agl / 0.3048)
    print(len(apogees))

# Analyze and plot results
plt.figure(figsize=(12, 6))

# Histogram of apogees
plt.hist(apogees, bins=30, color='skyblue', edgecolor='black')
plt.xlabel('Apogee (ft)')
plt.ylabel('Frequency')
plt.title('Monte Carlo Simulation: Apogee Distribution')

plt.tight_layout()
plt.show()
