import json
from pathlib import Path
from typing import List
from .models import ScrapedData


class DataWriter:
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def write(self, data: List[ScrapedData], filename: str, format: str = "json") -> str:
        filepath = self.output_dir / filename
        json_data = [item.model_dump() for item in data]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        return str(filepath)

