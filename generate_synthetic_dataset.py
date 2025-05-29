# --- File: generate_synthetic_dataset.py ---


import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def generate_synthetic_data(num_samples, start_time, node_id="node_1", anomaly_ratio=0.05, include_labels=True):
    """
    Generates synthetic time-series data for network monitoring.

    Args:
        num_samples (int): Number of data points to generate.
        start_time (datetime): The starting timestamp for the data.
        node_id (str): Identifier for the network node.
        anomaly_ratio (float): Approximate percentage of samples to be anomalous.
        include_labels (bool): Whether to include an 'is_anomaly' column.

    Returns:
        pandas.DataFrame: A DataFrame containing the synthetic data.
    """

    # Define all features as per your model
    all_features = [
        'Throughput', 'Latency', 'Packet_Loss', 'Signal_Strength',
        'Temperature', 'Power_Quality', 'Weather_Condition',
        'Hour', 'Day', 'Week',
        'CPU_Utilization', 'Memory_Usage', 'Buffer_Occupancy', 'Error_Counters',
        'Link_Status', 'Neighbor_Count', 'Traffic_Distribution', 'Service_Priority'
    ]

    data = []
    timestamps = [start_time + timedelta(minutes=i) for i in range(num_samples)]
    
    # Base values for normal operation for *non-time-based/categorical* features
    base_values = {
        'Throughput': 1000, 'Latency': 20, 'Packet_Loss': 0.1, 'Signal_Strength': -50,
        'Temperature': 25, 'Power_Quality': 230,
        'CPU_Utilization': 30, 'Memory_Usage': 40, 'Buffer_Occupancy': 10, 'Error_Counters': 0,
        'Link_Status': 1, # 1: Active, 0: Inactive
        'Neighbor_Count': 5, 'Traffic_Distribution': 0.5, 'Service_Priority': 0 # 0: Normal, 1: Critical
    }

    # Standard deviations for normal fluctuations for *non-time-based/categorical* features
    std_devs = {
        'Throughput': 50, 'Latency': 5, 'Packet_Loss': 0.05, 'Signal_Strength': 5,
        'Temperature': 2, 'Power_Quality': 5,
        'CPU_Utilization': 5, 'Memory_Usage': 5, 'Buffer_Occupancy': 2, 'Error_Counters': 0.5,
        'Link_Status': 0.1,
        'Neighbor_Count': 0.5, 'Traffic_Distribution': 0.05, 'Service_Priority': 0.1
    }

    # Introduce anomalies
    anomaly_indices = np.random.choice(num_samples, int(num_samples * anomaly_ratio), replace=False)
    anomaly_indices.sort() # Keep them in time order

    for i in range(num_samples):
        current_timestamp = timestamps[i]
        row = {'timestamp': current_timestamp, 'node_id': node_id}
        is_anomaly = False

        for feature in all_features:
            val = None # Initialize val

            # Handle time-based features separately
            if feature == 'Hour':
                val = current_timestamp.hour
            elif feature == 'Day':
                val = current_timestamp.day
            elif feature == 'Week':
                val = current_timestamp.isocalendar()[1]
            elif feature == 'Weather_Condition':
                # Simple weather cycle: more clear during day, more varied at night
                hour_of_day = current_timestamp.hour
                if 6 <= hour_of_day < 18: # Daytime
                    val = np.random.choice([0, 0, 0, 1, 2], p=[0.7, 0.1, 0.1, 0.05, 0.05]) # 0:Clear, 1:Rain, 2:Wind
                else: # Nighttime
                    val = np.random.choice([0, 1, 2], p=[0.6, 0.2, 0.2])
                val = int(round(np.clip(val, 0, 2))) # Ensure it's 0, 1, or 2
            elif feature == 'Link_Status':
                # Link Status is binary, mostly active
                val = np.random.choice([0,1], p=[0.01, 0.99])
            elif feature == 'Service_Priority':
                # Service Priority is binary, mostly normal
                val = np.random.choice([0,1], p=[0.9, 0.1])
            else:
                # For other numerical features, apply base values and fluctuations
                val = base_values[feature] + np.random.normal(0, std_devs[feature])
            
            # Introduce anomalies
            if i in anomaly_indices:
                is_anomaly = True
                if feature == 'Throughput':
                    val = max(100, val * np.random.uniform(0.1, 0.5)) # Significant drop
                elif feature == 'Latency':
                    val = val * np.random.uniform(3, 8) # Significant spike
                elif feature == 'Packet_Loss':
                    val = min(10.0, val * np.random.uniform(10, 50)) # Significant increase
                elif feature == 'CPU_Utilization' or feature == 'Memory_Usage' or feature == 'Buffer_Occupancy':
                    val = min(100, val * np.random.uniform(1.8, 3.0)) # Significant spike
                elif feature == 'Error_Counters':
                    val = val + np.random.uniform(10, 100) # Sudden increase
                elif feature == 'Link_Status':
                    val = 0 # Force link inactive during anomaly
                elif feature == 'Service_Priority':
                    val = 1 # Force critical priority during anomaly

            row[feature] = round(max(0.0, val), 2) if isinstance(val, (float, np.float64)) else int(val) # Ensure non-negative, round floats, keep ints as ints

        if include_labels:
            row['is_anomaly'] = 1 if is_anomaly else 0 # 1 for anomaly, 0 for normal
        data.append(row)

    df = pd.DataFrame(data)
    
    # Ensure discrete values are integers and within reasonable bounds after generation
    # (Especially after anomaly injection, make sure they don't exceed max/min for % or counts)
    df['Weather_Condition'] = df['Weather_Condition'].astype(int)
    df['Hour'] = df['Hour'].astype(int)
    df['Day'] = df['Day'].astype(int)
    df['Week'] = df['Week'].astype(int)
    df['Link_Status'] = df['Link_Status'].astype(int)
    df['Service_Priority'] = df['Service_Priority'].astype(int)
    df['CPU_Utilization'] = df['CPU_Utilization'].clip(0, 100)
    df['Memory_Usage'] = df['Memory_Usage'].clip(0, 100)
    df['Packet_Loss'] = df['Packet_Loss'].clip(0, 100)


    return df

if __name__ == "__main__":
    output_dir = "synthetic_network_data"
    os.makedirs(output_dir, exist_ok=True)

    start_time = datetime(2025, 1, 1, 0, 0, 0) # Start of the year

    # --- Training Data (larger) ---
    print("Generating training data...")
    train_samples = 50000 # Increased training samples for better model learning
    train_df = generate_synthetic_data(train_samples, start_time, anomaly_ratio=0.03, include_labels=False)
    train_df.to_csv(os.path.join(output_dir, "training_data.csv"), index=False)
    print(f"Training data saved to {os.path.join(output_dir, 'training_data.csv')} with {len(train_df)} samples.")

    # --- Validation Data ---
    print("Generating validation data...")
    val_samples = 10000 # Increased validation samples
    val_start_time = start_time + timedelta(minutes=train_samples)
    val_df = generate_synthetic_data(val_samples, val_start_time, anomaly_ratio=0.05, include_labels=True)
    val_df.to_csv(os.path.join(output_dir, "validation_data.csv"), index=False)
    print(f"Validation data saved to {os.path.join(output_dir, 'validation_data.csv')} with {len(val_df)} samples.")

    # --- Test Data ---
    print("Generating test data...")
    test_samples = 20000 # Increased test samples
    test_start_time = val_start_time + timedelta(minutes=val_samples)
    test_df = generate_synthetic_data(test_samples, test_start_time, anomaly_ratio=0.10, include_labels=True)
    test_df.to_csv(os.path.join(output_dir, "test_data.csv"), index=False)
    print(f"Test data saved to {os.path.join(output_dir, 'test_data.csv')} with {len(test_df)} samples.")

    print("\nSynthetic dataset generation complete!")

# --- End of File: generate_synthetic_dataset.py ---