import re
from datetime import datetime

def calculate_average_difference():
    print("Paste the terminal output below. When done, press Enter and then Ctrl+D (or Ctrl+Z on Windows):")
    try:
        # Read pasted input
        input_data = ""
        while True:
            line = input()
            input_data += line + "\n"
    except EOFError:
        pass

    # Extract timestamps using regex
    timestamps = re.findall(r"Timestamp: (\d{2}:\d{2}:\d{2}\.\d+)", input_data)

    if not timestamps:
        print("No timestamps found in the input. Please check the format.")
        return

    # Convert timestamps to datetime objects
    datetime_objects = [datetime.strptime(ts, "%H:%M:%S.%f") for ts in timestamps]

    # Calculate differences in milliseconds
    differences = [(datetime_objects[i + 1] - datetime_objects[i]).total_seconds() * 1000 for i in range(len(datetime_objects) - 1)]

    # Calculate the average difference
    average_difference = sum(differences) / len(differences)

    print(f"Average difference between closest timestamps: {average_difference:.2f} ms")

if __name__ == "__main__":
    calculate_average_difference()