"""
Schema Processor Module

Parses and formats database schemas (CREATE TABLE statements) for LLM consumption.
"""

import re
from typing import Dict, List, Optional


class TableInfo:
    """Represents a parsed database table."""
    
    def __init__(self, name: str):
        self.name = name
        self.columns: List[Dict] = []
        self.primary_key: Optional[str] = None
        self.foreign_keys: List[Dict] = []
    
    def add_column(self, name: str, data_type: str, constraints: str = ""):
        self.columns.append({
            "name": name,
            "type": data_type,
            "constraints": constraints
        })
    
    def add_foreign_key(self, column: str, ref_table: str, ref_column: str):
        self.foreign_keys.append({
            "column": column,
            "references_table": ref_table,
            "references_column": ref_column
        })
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "columns": self.columns,
            "primary_key": self.primary_key,
            "foreign_keys": self.foreign_keys
        }


def parse_schema(schema_text: str) -> List[TableInfo]:
    """
    Parse CREATE TABLE statements into structured table information.
    
    Args:
        schema_text: Raw SQL schema with CREATE TABLE statements
        
    Returns:
        List of TableInfo objects
    """
    tables = []
    
    # Find all CREATE TABLE statements
    create_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?\s*\((.*?)\)(?:\s*;)?'
    matches = re.findall(create_pattern, schema_text, re.IGNORECASE | re.DOTALL)
    
    for table_name, columns_text in matches:
        table = TableInfo(table_name)
        
        # Split by comma, but be careful with nested parentheses
        parts = split_column_definitions(columns_text)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check for PRIMARY KEY constraint
            pk_match = re.match(r'PRIMARY\s+KEY\s*\(([^)]+)\)', part, re.IGNORECASE)
            if pk_match:
                table.primary_key = pk_match.group(1).strip().strip('`"\'')
                continue
            
            # Check for FOREIGN KEY constraint
            fk_match = re.match(
                r'FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"\']?(\w+)[`"\']?\s*\(([^)]+)\)',
                part, re.IGNORECASE
            )
            if fk_match:
                table.add_foreign_key(
                    fk_match.group(1).strip().strip('`"\''),
                    fk_match.group(2).strip(),
                    fk_match.group(3).strip().strip('`"\'')
                )
                continue
            
            # Parse column definition
            col_match = re.match(r'[`"\']?(\w+)[`"\']?\s+(\w+(?:\([^)]+\))?)\s*(.*)', part, re.IGNORECASE)
            if col_match:
                col_name = col_match.group(1)
                col_type = col_match.group(2)
                constraints = col_match.group(3).strip()
                
                # Check for inline PRIMARY KEY
                if 'PRIMARY KEY' in constraints.upper():
                    table.primary_key = col_name
                
                table.add_column(col_name, col_type, constraints)
        
        tables.append(table)
    
    return tables


def split_column_definitions(text: str) -> List[str]:
    """Split column definitions handling nested parentheses."""
    parts = []
    current = ""
    depth = 0
    
    for char in text:
        if char == '(':
            depth += 1
            current += char
        elif char == ')':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    
    if current.strip():
        parts.append(current.strip())
    
    return parts


def format_schema_for_prompt(schema_text: str) -> str:
    """
    Format schema into a clear, structured format for the LLM prompt.
    
    Args:
        schema_text: Raw SQL schema
        
    Returns:
        Formatted schema string
    """
    tables = parse_schema(schema_text)
    
    if not tables:
        # If parsing failed, return the raw schema
        return f"Raw Schema:\n{schema_text}"
    
    output = []
    output.append("DATABASE SCHEMA:")
    output.append("=" * 50)
    
    for table in tables:
        output.append(f"\nTable: {table.name}")
        output.append("-" * 30)
        
        # Columns
        output.append("Columns:")
        for col in table.columns:
            pk_marker = " [PK]" if col["name"] == table.primary_key else ""
            output.append(f"  - {col['name']}: {col['type']}{pk_marker}")
        
        # Foreign Keys
        if table.foreign_keys:
            output.append("Foreign Keys:")
            for fk in table.foreign_keys:
                output.append(
                    f"  - {fk['column']} -> {fk['references_table']}.{fk['references_column']}"
                )
    
    output.append("\n" + "=" * 50)
    
    # Also include relationships summary
    relationships = extract_relationships(tables)
    if relationships:
        output.append("\nRELATIONSHIPS:")
        for rel in relationships:
            output.append(f"  {rel}")
    
    return "\n".join(output)


def extract_relationships(tables: List[TableInfo]) -> List[str]:
    """
    Extract and describe relationships between tables.
    
    Args:
        tables: List of parsed TableInfo objects
        
    Returns:
        List of relationship descriptions
    """
    relationships = []
    
    for table in tables:
        for fk in table.foreign_keys:
            relationships.append(
                f"{table.name}.{fk['column']} references {fk['references_table']}.{fk['references_column']}"
            )
    
    return relationships
