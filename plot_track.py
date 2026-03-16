import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the data
df = pd.read_csv('telemetry_log.csv')

# Drop completely empty/invalid rows or where position is static initially
df = df.dropna(subset=['position_x', 'position_z'])

# Filter out paused or loading states
# Assuming speed > 0 indicates driving
df = df[df['speed_mps'] > 1.0]

# GT7 coordinates use X and Z for the horizontal plane (track map)
x = df['position_x']
z = df['position_z']

# To color the line based on throttle/brake:
# We can create a simple condition:
# Green = mostly throttle
# Red = mostly brake
# Blue = coasting

throttle = df['throttle'] / 255.0  # normalize 0 to 1
brake = df['brake'] / 255.0        # normalize 0 to 1

colors = []
for t, b in zip(throttle, brake):
    if b > 0.1:
        colors.append('red') # Braking
    elif t > 0.1:
        colors.append('green') # Throttle
    else:
        colors.append('blue') # Coasting

fig, ax = plt.subplots(figsize=(12, 10))

# Scatter plot for color mapped points
scatter = ax.scatter(x, z, c=colors, s=10, alpha=0.6)

# Aesthetics
ax.set_facecolor('#111111')
fig.patch.set_facecolor('#111111')
ax.set_title(f"Track Map & Inputs - {df['car_name'].iloc[0]}", color='white', fontsize=16)
ax.set_xlabel('Position X', color='white')
ax.set_ylabel('Position Z', color='white')
ax.tick_params(colors='white')

# Ensure aspect ratio is equal so the track isn't squished
ax.set_aspect('equal', 'box')

# Custom legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='Throttle', markerfacecolor='green', markersize=10),
    Line2D([0], [0], marker='o', color='w', label='Braking', markerfacecolor='red', markersize=10),
    Line2D([0], [0], marker='o', color='w', label='Coasting', markerfacecolor='blue', markersize=10)
]
ax.legend(handles=legend_elements, loc='upper right', facecolor='#222222', edgecolor='white', labelcolor='white')

plt.tight_layout()
plt.savefig('track_map.png', dpi=300, facecolor=fig.get_facecolor())
print("Saved track map to track_map.png")
