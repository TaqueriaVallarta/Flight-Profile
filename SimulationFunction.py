import random
import pandas as pd
from main import initialize
from lib.RocketClass import Rocket
from lib.Drag.DragSetup import DragSetup, Atmosphere
from lib.Motor.Motor import Motor


def generate_random_value(base_value, deviation=0.2):
    """Generate a random value within a uniform distribution around base_value."""
    return base_value * (1 + random.uniform(-deviation, deviation))


def simulate_rockets(num_simulations, deviation=0.2, pressure_deviation=0.02, temperature_deviation=0.1):
    # Initialize base rocket
    base_rocket = initialize()
    base_rocket.get_values_from_files()

    # Get base values
    base_values = base_rocket.set_vals_to_vars()

    results = []

    for _ in range(num_simulations):
        # Create new instance of DragSetup and Motor with random values
        new_atmosphere = Atmosphere(
            temp_0=generate_random_value(base_values["temp_0"], temperature_deviation),
            p_0=generate_random_value(base_values["p_0"], pressure_deviation),
            h_0=base_values["h_0"]
        )
        new_drag_setup = DragSetup(
            fin_thickness=generate_random_value(base_values["fin_thickness"], deviation),
            fin_height=generate_random_value(base_values["fin_height"], deviation),
            drag_coef=generate_random_value(base_values["drag_coef"], deviation),
            reefed_parachute=base_rocket.drag_setup.reefed_parachute,  # Keep original
            main_parachute=base_rocket.drag_setup.main_parachute  # Keep original
        )

        new_motor = Motor(
            wet_mass=generate_random_value(base_values["wet_mass_motor"], deviation),
            burn_time=generate_random_value(base_values["burn_time_motor"], deviation),
            impulse=generate_random_value(base_values["impulse"], deviation)  # Assuming impulse replaces mean_thrust
        )

        dry_mass_rocket = generate_random_value(base_values["dry_mass"], deviation)
        initial_height_msl = base_rocket.initial_height_msl

        new_rocket = Rocket(new_drag_setup, new_motor, dry_mass_rocket, initial_height_msl=initial_height_msl)

        # Record the inputs
        result = {
            "fin_thickness": new_drag_setup.fin_thickness,
            "fin_height": new_drag_setup.fin_height,
            "drag_coef": new_drag_setup.drag_coef,
            "wet_mass_motor": new_motor.wet_mass,
            "burn_time_motor": new_motor.burn_time,
            "impulse": new_motor.impulse,
            "dry_mass": dry_mass_rocket,
            "temp_0": new_atmosphere.temp_0,
            "p_0": new_atmosphere.p_0
        }

        # Simulate to apogee
        new_rocket.sim_to_apogee()

        # Record the results
        result["apogee"] = new_rocket.height_agl
        results.append(result)

    # Convert results to DataFrame
    df = pd.DataFrame(results)

    # Save results to CSV file
    df.to_csv('rocket_simulation_results.csv', index=False)

    print(f"Simulation complete. Results saved to 'rocket_simulation_results.csv'.")


# Run the simulation with desired number of rockets and deviation
simulate_rockets(num_simulations=1000, deviation=0.2)
