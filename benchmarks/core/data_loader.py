"""
Spider Data Loader

Loads and manages Spider benchmark dataset.
"""

import json
from pathlib import Path
from typing import List, Dict
import random


class SpiderDataLoader:
    """Loads and manages Spider benchmark data."""
    
    def __init__(self, spider_dir: str):
        self.spider_dir = Path(spider_dir)
        self.dev_data = []
        self.tables = {}
        self.db_schemas = {}
        
    def load(self) -> bool:
        """Load Spider dev set and table definitions."""
        dev_path = self.spider_dir / "dev.json"
        tables_path = self.spider_dir / "tables.json"
        
        if not dev_path.exists():
            print(f"Error: Spider dev.json not found at {dev_path}")
            print("Please download Spider from: https://yale-lily.github.io/spider")
            return False
        
        if not tables_path.exists():
            print(f"Error: Spider tables.json not found at {tables_path}")
            return False
        
        # Load dev set
        with open(dev_path, 'r', encoding='utf-8') as f:
            self.dev_data = json.load(f)
        
        # Load table definitions
        with open(tables_path, 'r', encoding='utf-8') as f:
            tables_list = json.load(f)
            self.tables = {t['db_id']: t for t in tables_list}
        
        # Build schema strings for each database
        for db_id, table_info in self.tables.items():
            self.db_schemas[db_id] = self._build_schema_string(table_info)
        
        print(f"Loaded {len(self.dev_data)} examples from Spider dev set")
        print(f"Loaded {len(self.tables)} database schemas")
        return True
    
    def _build_schema_string(self, table_info: Dict) -> str:
        """Convert Spider table info to CREATE TABLE statements."""
        schema_parts = []
        
        table_names = table_info['table_names_original']
        column_names = table_info['column_names_original']
        column_types = table_info['column_types']
        primary_keys = table_info.get('primary_keys', [])
        
        # Group columns by table
        columns_by_table = {}
        for idx, (table_idx, col_name) in enumerate(column_names):
            if table_idx == -1:  # Special * column
                continue
            if table_idx not in columns_by_table:
                columns_by_table[table_idx] = []
            columns_by_table[table_idx].append({
                'name': col_name,
                'type': column_types[idx] if idx < len(column_types) else 'TEXT',
                'idx': idx
            })
        
        # Build CREATE TABLE for each table
        for table_idx, table_name in enumerate(table_names):
            cols = columns_by_table.get(table_idx, [])
            if not cols:
                continue
                
            col_defs = []
            for col in cols:
                col_type = col['type'].upper()
                pk = " PRIMARY KEY" if col['idx'] in primary_keys else ""
                col_defs.append(f"    {col['name']} {col_type}{pk}")
            
            create_stmt = f"CREATE TABLE {table_name} (\n"
            create_stmt += ",\n".join(col_defs)
            create_stmt += "\n);"
            schema_parts.append(create_stmt)
        
        return "\n\n".join(schema_parts)
    
    def get_samples(self, n: int = 100, shuffle: bool = True, seed: int = 42) -> List[Dict]:
        """Get n samples from the dev set."""
        if shuffle:
            random.seed(seed)
            samples = random.sample(self.dev_data, min(n, len(self.dev_data)))
        else:
            samples = self.dev_data[:n]
        
        return samples
    
    def get_schema(self, db_id: str) -> str:
        """Get schema string for a database."""
        return self.db_schemas.get(db_id, "")
    
    def get_table_info(self, db_id: str) -> Dict:
        """Get raw table info for a database."""
        return self.tables.get(db_id, {})
