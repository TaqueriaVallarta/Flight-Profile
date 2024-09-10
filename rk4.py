# rk4 program, takes in the values and acceleration as a function
def rk4_step(height, velocity, acceleration, dt, t):
    """
    Perform a single step of the RK4 method.

    Args:
    height: float - Initial position.
    velocity: float - Initial velocity.
    acceleration: function - Function to compute acceleration a(height, velocity, t).
    dt: float - Time step size.
    t: float - Current time.

    Returns:
    tuple - (new position, new velocity)
    """
    # k1 values for position and velocity
    k1x = velocity
    k1v = acceleration(height, velocity, t)

    # k2 values for position and velocity
    k2x = velocity + 0.5 * dt * k1v
    k2v = acceleration(height + 0.5 * dt * k1x, velocity + 0.5 * dt * k1v, t + 0.5 * dt)

    # k3 values for position and velocity
    k3x = velocity + 0.5 * dt * k2v
    k3v = acceleration(height + 0.5 * dt * k2x, velocity + 0.5 * dt * k2v, t + 0.5 * dt)

    # k4 values for position and velocity
    k4x = velocity + dt * k3v
    k4v = acceleration(height + dt * k3x, velocity + dt * k3v, t + dt)

    # Compute new position and velocity
    new_x = height + (dt / 6) * (k1x + 2 * k2x + 2 * k3x + k4x)
    new_v = velocity + (dt / 6) * (k1v + 2 * k2v + 2 * k3v + k4v)

    return new_x, new_v