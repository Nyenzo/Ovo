import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

def download_model():
    """Download the model and tokenizer locally"""
    model_name = "microsoft/DialoGPT-medium"
    local_path = "llm-model"
    
    print(f"Downloading {model_name} to {local_path}...")
    
    try:
        # Download tokenizer
        print("Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.save_pretrained(local_path)
        
        # Download model
        print("Downloading model (this may take a while)...")
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model.save_pretrained(local_path)
        
        print(f"✅ Model downloaded successfully to {local_path}/")
        print(f"📁 Files created:")
        
        # List the downloaded files
        for root, dirs, files in os.walk(local_path):
            for file in files:
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                print(f"   {file_path} ({size:,} bytes)")
                
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False
    
    return True

if __name__ == "__main__":
    download_model() 