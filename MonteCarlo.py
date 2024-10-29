import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import fsolve
from joblib import Parallel, delayed
from functools import lru_cache
import csv
from main import initialize  # Import the initialize function from main.py


# Use lru_cache to memoize the eq function
def eq(variables):
    rocket = initialize(40).get_values_from_files()
    burn_time, dry_mass = variables
    rocket.set_vars_to_new({'dry_mass': dry_mass, 'burn_time': burn_time})
    apogee, accel = rocket.sim_to_apogee()
    print(apogee, accel, burn_time, dry_mass)
    eq1 = apogee - 15240
    eq2 = 1000 * (accel - 5 * 9.81)
    return eq1, eq2


# Helper function to solve eq1 = 0 for a given burn_time
def solve_eq1_for_burn_time(burn_time, dry_mass_guess):
    root = fsolve(lambda dry_mass: eq((burn_time, dry_mass))[0], dry_mass_guess)
    return root[0]


# Helper function to solve eq2 = 0 for a given burn_time
def solve_eq2_for_burn_time(burn_time, dry_mass_guess):
    root = fsolve(lambda dry_mass: eq((burn_time, dry_mass))[1], dry_mass_guess)
    return root[0]


# Define a range of burn_time values to solve for
burn_time_vals = np.linspace(10, 40, 40)  # Burn time values
dry_mass_guess = 120  # Initial guess for dry mass, adjust if needed

# Output file
output_file = 'dry_mass_solutions.csv'

# Create the CSV file and write the header
with open(output_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Burn Time', 'Dry Mass for eq1', 'Dry Mass for eq2'])  # Write header


    # Function to compute dry_mass solutions and write to CSV
    def compute_and_save_solutions(burn_time):
        dm_eq1 = solve_eq1_for_burn_time(burn_time, dry_mass_guess)
        dm_eq2 = solve_eq2_for_burn_time(burn_time, dry_mass_guess)

        # Write to CSV
        with open(output_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([burn_time, dm_eq1, dm_eq2])  # Write the current results

        return dm_eq1, dm_eq2


    # Run computations in parallel for all burn_time values
    # Serial execution of computations for all burn_time values
    results = []
    for bt in burn_time_vals:
        result = compute_and_save_solutions(bt)
        print(result)
        results.append(result)

    # results = Parallel(n_jobs=-1)(delayed(compute_and_save_solutions)(bt) for bt in burn_time_vals)

# Unzip results into separate arrays
dry_mass_for_eq1, dry_mass_for_eq2 = zip(*results)

# Convert results to numpy arrays
dry_mass_for_eq1 = np.array(dry_mass_for_eq1)
dry_mass_for_eq2 = np.array(dry_mass_for_eq2)

# Plot the results
plt.plot(burn_time_vals, dry_mass_for_eq1, label='eq1 = 0 (Apogee constraint)', color='red')
plt.plot(burn_time_vals, dry_mass_for_eq2, label='eq2 = 0 (Acceleration constraint)', color='blue')

plt.xlabel('Burn Time')
plt.ylabel('Dry Mass')
plt.title('Implicit Functions for eq1 = 0 and eq2 = 0 (Optimized)')
plt.legend()
plt.grid(True)
plt.show()
