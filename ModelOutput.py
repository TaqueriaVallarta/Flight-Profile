import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib

# Load the trained model
model = joblib.load('apogee_predictor_model.pkl')

# Load the scaler (if saved)
scaler = joblib.load('scaler.pkl')

# Define the range of burn times to test
burn_times = np.arange(10, 31, 1)  # Burn times from 10 to 30 seconds

# Create a DataFrame with constant values for other variables
# Assume these are some reasonable fixed values for other features
constant_features = {
    "fin_thickness": 0.01,  # Example value in meters
    "fin_height": 0.1,  # Example value in meters
    "drag_coef": 0.5,
    "wet_mass_motor": 200,  # Example value in kilograms
    "dry_mass": 100,  # Example value in kilograms
    "temp_0": 300,  # Example value in Kelvin
    "p_0": 101325,  # Example value in Pascals
    "impulse": 100000
}

# Create a DataFrame for predictions
predictions_df = pd.DataFrame({
    "burn_time_motor": burn_times,
    **constant_features
})

# Scale the input features
X_new_scaled = scaler.transform(predictions_df)

# Make predictions
predictions_df["predicted_apogee"] = model.predict(X_new_scaled)

# Plot the results
plt.figure(figsize=(10, 6))
plt.plot(predictions_df["burn_time_motor"], predictions_df["predicted_apogee"], marker='o')
plt.title('Effect of Burn Time on Apogee')
plt.xlabel('Burn Time (seconds)')
plt.ylabel('Predicted Apogee (meters)')
plt.grid(True)
plt.show()
