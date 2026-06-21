import matplotlib.pyplot as plt
import numpy as np
from .earth import earth_sphere

def plot_conjunctions_3d(target_r, conjunctions_list, max_conjunctions=3):
    """
    Plot the target's 3D orbit, Earth, and highlight the positions
    of closest approaching objects at their TCA.
    """
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection="3d")

    # 1. Plot Target Orbit
    ax.plot(target_r[:, 0], target_r[:, 1], target_r[:, 2], color="cyan", lw=2, label="Tracked Satellite")

    # 2. Plot Earth
    xe, ye, ze = earth_sphere()
    ax.plot_surface(xe, ye, ze, color="blue", alpha=0.15)

    # 3. Highlight closest approaches
    # Limit to top N closest approaches
    closest = conjunctions_list[:max_conjunctions]
    
    # Use distinct colors for each close approach object
    colors = ["red", "orange", "magenta"]

    for idx, conj in enumerate(closest):
        color = colors[idx % len(colors)]
        
        # Position of target at TCA
        # tca_seconds / dt tells us the approximate index in target_r
        # Wait, a safer way is to find the closest step in times, or just look up by value
        # But we also saved the debris position in the json: sat_position_m
        # Let's extract the debris position at TCA and the target's position at TCA
        sat_pos = np.array(conj["sat_position_m"])
        # Target position at TCA is sat_position_m - relative_position_m
        rel_pos = np.array(conj["relative_position_m"])
        target_pos_tca = sat_pos - rel_pos
        
        # Plot Debris Position at TCA
        ax.scatter(sat_pos[0], sat_pos[1], sat_pos[2], color=color, s=50, marker="x", 
                   label=f"{conj['sat_name']} ({conj['sat_id']})")
        
        # Plot Target Position at TCA
        ax.scatter(target_pos_tca[0], target_pos_tca[1], target_pos_tca[2], color="cyan", s=40, marker="o")
        
        # Draw proximity line
        ax.plot(
            [target_pos_tca[0], sat_pos[0]],
            [target_pos_tca[1], sat_pos[1]],
            [target_pos_tca[2], sat_pos[2]],
            color=color, linestyle="--", lw=1.5
        )
        
        # Add text label for miss distance
        dist_km = conj["min_distance_m"] / 1000.0
        label_text = f" {conj['sat_name']}\n Miss: {dist_km:.2f} km"
        ax.text(sat_pos[0], sat_pos[1], sat_pos[2], label_text, color=color, fontsize=9)

    # Styling
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title("3D Conjunction & Proximity Map")
    
    # Set equal scaling to prevent distortion
    max_range = np.max(np.abs(target_r)) * 1.1
    ax.set_xlim(-max_range, max_range)
    ax.set_ylim(-max_range, max_range)
    ax.set_zlim(-max_range, max_range)
    
    ax.legend(loc="upper right")
    return fig
