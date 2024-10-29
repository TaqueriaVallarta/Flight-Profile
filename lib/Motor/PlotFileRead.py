import pandas as pd

def load_plt_to_dataframe(file_path):
    """
    Reads a .plt file and returns a DataFrame using every 3rd line as rows.

    Parameters:
        file_path (str): The path to the .plt file.

    Returns:
        pd.DataFrame: A DataFrame with columns ['OF', 'temp', 'gamma', 'mass'].
    """
    # Read the file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Filter out header lines and take every 3rd line
    data_lines = [line for i, line in enumerate(lines) if i > 0 and not line.startswith('#') and (i - 1) % 3 == 0]

    # Split each line into columns and create a DataFrame
    data = [line.split() for line in data_lines]
    df = pd.DataFrame(data, columns=['OF', 'temp', 'gamma', 'mass'])

    # Convert strings to numeric values
    df = df.apply(pd.to_numeric)

    return df

# Example usage:
# df = load_plt_to_dataframe("path/to/your/file.plt")
# print(df)
