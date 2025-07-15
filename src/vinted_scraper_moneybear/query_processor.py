import os
import json
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Tuple
from pathlib import Path

def load_data(file_path: str) -> Tuple[List[str], List[str]]:
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data['inputs'], data['outputs']

def save_data(file_path: str, inputs: List[str], outputs: List[str]):
    with open(file_path, 'w') as f:
        json.dump({'inputs': inputs, 'outputs': outputs}, f, indent=2)

class ProductDataset(Dataset):
    def __init__(self, inputs: List[str], outputs: List[str], tokenizer):
        assert len(inputs) == len(outputs), "Inputs and outputs must have same length"
        self.inputs = inputs
        self.outputs = outputs
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.inputs)

    def __getitem__(self, idx):
        input_encoding = self.tokenizer(
            self.inputs[idx],
            padding='max_length',
            max_length=64,
            truncation=True,
            return_tensors="pt"
        )
        
        output_encoding = self.tokenizer(
            self.outputs[idx],
            padding='max_length',
            max_length=64,
            truncation=True,
            return_tensors="pt"
        )

        return {
            'input_ids': input_encoding['input_ids'].squeeze(),
            'attention_mask': input_encoding['attention_mask'].squeeze(),
            'labels': output_encoding['input_ids'].squeeze()
        }

def train_model(model, train_dataloader, num_epochs: int, device: str, save_path: str):
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    model.train()
    
    for epoch in range(num_epochs):
        total_loss = 0
        for batch in train_dataloader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            
            loss = outputs.loss
            total_loss += loss.item()
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
        avg_loss = total_loss / len(train_dataloader)
        print(f"Epoch {epoch + 1}/{num_epochs}, Average Loss: {avg_loss:.4f}")
    
    model.save_pretrained(save_path)
    print(f"Model saved to {save_path}")

def generate_output(text: str, model_path: str, device: str = None):
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    tokenizer = T5Tokenizer.from_pretrained('t5-base', legacy=False)
    model = T5ForConditionalGeneration.from_pretrained(model_path).to(device)
    
    model.eval()
    with torch.no_grad():
        input_encoding = tokenizer(
            text,
            padding='max_length',
            max_length=64,
            truncation=True,
            return_tensors="pt"
        ).to(device)
        
        generated_ids = model.generate(
            input_ids=input_encoding['input_ids'],
            attention_mask=input_encoding['attention_mask'],
            max_new_tokens=50,
        )
        
        return tokenizer.decode(generated_ids[0], skip_special_tokens=True)

def parse_output(output: str) -> Dict:
    try:
        item, attributes = output.split(' | ')
        attributes_dict = {}
        for attr in attributes.split(', '):
            key, value = attr.split('=')
            attributes_dict[key] = value
        return {item: attributes_dict}
    except ValueError:
        return {"error": "Invalid output format"}

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'{device=}')
    
    model_path = "trained_t5_model"
    data_path = "training_data.json"
    
    if not Path(model_path).exists():
        if Path(data_path).exists():
            inputs, outputs = load_data(data_path)
        else:
            raise ValueError('Data file not found')
        
        tokenizer = T5Tokenizer.from_pretrained('t5-base', legacy=False)
        model = T5ForConditionalGeneration.from_pretrained('t5-base').to(device)
        
        dataset = ProductDataset(inputs, outputs, tokenizer)
        train_dataloader = DataLoader(dataset, batch_size=8, shuffle=True)
        train_model(model, train_dataloader, num_epochs=30, device=device, save_path=model_path)
    
    test_input = "Puma shoes black"
    generated = generate_output(test_input, model_path, device)
    print(f"Input: {test_input}")
    print(f"Generated output: {generated}")
    print(f"Parsed output: {parse_output(generated)}")

if __name__ == "__main__":
    main()