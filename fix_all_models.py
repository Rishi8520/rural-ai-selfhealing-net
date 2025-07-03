# save as: fix_all_models.py
import json
import h5py
import os
import glob

def extract_hyperparams_from_hdf5(weight_file_path):
    """Extract hyperparameters from HDF5 weight file using correct structure"""
    try:
        with h5py.File(weight_file_path, 'r') as f:
            # ✅ CORRECT LOCATION: optimizer/vars/ contains the actual LSTM weights
            if 'optimizer' not in f or 'vars' not in f['optimizer']:
                print(f"❌ No optimizer/vars found in {weight_file_path}")
                return None
            
            optimizer_vars = f['optimizer']['vars']
            
            # Find LSTM kernel (input_features=18, hidden*4)
            lstm_kernel_shape = None
            for var_key in optimizer_vars.keys():
                if isinstance(optimizer_vars[var_key], h5py.Dataset):
                    shape = optimizer_vars[var_key].shape
                    # Look for shape (18, hidden_size*4)
                    if len(shape) == 2 and shape[0] == 18 and shape[1] % 4 == 0:
                        hidden_size = shape[1] // 4
                        if hidden_size >= 16:  # Reasonable hidden size
                            lstm_kernel_shape = shape
                            break
            
            if lstm_kernel_shape is None:
                print(f"❌ No valid LSTM kernel found in {weight_file_path}")
                return None
            
            # Calculate hyperparameters
            hidden_size = lstm_kernel_shape[1] // 4
            
            # ✅ COUNT LSTM LAYERS from layers structure
            num_layers = 0
            if 'layers' in f:
                layers_group = f['layers']
                for key in layers_group.keys():
                    if 'lstm' in key.lower():
                        num_layers += 1
            
            if num_layers == 0:
                num_layers = 2  # Default fallback
            
            hyperparams = {
                'hidden_size': hidden_size,
                'num_layers': num_layers,
                'dropout_rate': 0.2,  # Default (can't be extracted from weights)
                'input_features_count': 18,
                'sequence_length': 1
            }
            
            print(f"✅ Extracted: hidden_size={hidden_size}, num_layers={num_layers}")
            return hyperparams
            
    except Exception as e:
        print(f"❌ Error processing {weight_file_path}: {e}")
        return None

def fix_all_threshold_files():
    """Fix all threshold files with extracted hyperparameters"""
    weight_files = glob.glob("lstm_model/*_lstm_model.weights.h5")
    fixed_count = 0
    
    print(f"🔧 Processing {len(weight_files)} weight files...")
    
    for weight_file in weight_files:
        # Extract node ID
        node_id = os.path.basename(weight_file).replace('_lstm_model.weights.h5', '')
        threshold_file = f"lstm_model/{node_id}_threshold.json"
        
        if not os.path.exists(threshold_file):
            print(f"❌ Threshold file missing for {node_id}")
            continue
        
        # Extract hyperparameters from weight file
        hyperparams = extract_hyperparams_from_hdf5(weight_file)
        if not hyperparams:
            print(f"❌ Could not extract hyperparams for {node_id}")
            continue
        
        # Load existing threshold
        try:
            with open(threshold_file, 'r') as f:
                existing_data = json.load(f)
            
            threshold_value = existing_data.get('dynamic_anomaly_threshold', 0.1)
            
            # Create updated data with hyperparameters
            updated_data = {
                'dynamic_anomaly_threshold': threshold_value,
                'hyperparameters': hyperparams
            }
            
            # Save updated file
            with open(threshold_file, 'w') as f:
                json.dump(updated_data, f, indent=2)
            
            print(f"✅ Fixed {node_id}: hidden_size={hyperparams['hidden_size']}, layers={hyperparams['num_layers']}")
            fixed_count += 1
            
        except Exception as e:
            print(f"❌ Error fixing {threshold_file}: {e}")
    
    print(f"\n🎯 Fixed {fixed_count}/{len(weight_files)} threshold files")
    return fixed_count

if __name__ == "__main__":
    print("🔧 Fixing all threshold files with correct hyperparameters...")
    fixed_count = fix_all_threshold_files()
    if fixed_count > 0:
        print("✅ Done! Try loading models again.")
    else:
        print("❌ No files were fixed. Check the error messages above.")
