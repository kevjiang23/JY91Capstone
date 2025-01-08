import re

# Prompt the user to paste the data into the terminal
print("Paste the data below, and then press Enter followed by Ctrl+D (or Ctrl+Z on Windows):")
data = []
try:
    while True:
        line = input()
        data.append(line)
except EOFError:
    pass
data = "\n".join(data)

# Use regex to extract the X values from the Angle field
angle_x_values = re.findall(r"Angle: \((-?\d+\.\d+),", data)

# Convert the extracted values to float
x_values = list(map(float, angle_x_values))

# Calculate the average
average_x = sum(x_values) / len(x_values) if x_values else 0

print(f"The average value of the first Angle measure (X) is: {average_x:.6f}")