# save as: inspect_models.py
import json
import h5py
import os
import glob

def inspect_threshold_files():
    """Check what's in threshold files"""
    threshold_files = glob.glob("lstm_model/*_threshold.json")
    
    print(f"Found {len(threshold_files)} threshold files:")
    
    for i, file_path in enumerate(threshold_files[:5]):  # Check first 5
        print(f"\n--- {file_path} ---")
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            print(f"Content: {data}")
            if 'hyperparameters' in data:
                print("✅ Has hyperparameters")
            else:
                print("❌ Missing hyperparameters")
        except Exception as e:
            print(f"Error reading: {e}")

def inspect_weight_file_structure():
    """Check HDF5 weight file structure"""
    weight_files = glob.glob("lstm_model/*_lstm_model.weights.h5")
    
    print(f"\nFound {len(weight_files)} weight files:")
    
    for i, file_path in enumerate(weight_files[:3]):  # Check first 3
        print(f"\n--- {file_path} ---")
        try:
            with h5py.File(file_path, 'r') as f:
                print("HDF5 structure:")
                
                def print_structure(group, indent=0):
                    for key in group.keys():
                        item = group[key]
                        spaces = "  " * indent
                        if isinstance(item, h5py.Group):
                            print(f"{spaces}{key}/ (Group)")
                            if indent < 3:  # Limit depth
                                print_structure(item, indent + 1)
                        elif isinstance(item, h5py.Dataset):
                            print(f"{spaces}{key} (Dataset) - Shape: {item.shape}")
                
                print_structure(f)
                
        except Exception as e:
            print(f"Error reading HDF5: {e}")

if __name__ == "__main__":
    print("🔍 Inspecting model files...")
    inspect_threshold_files()
    inspect_weight_file_structure()
