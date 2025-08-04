import json
import jsonschema
from typing import Dict, Any, List, Optional
from jsonschema import ValidationError

class SchemaProcessor:
    def __init__(self):
        self.validation_errors = []
    
    def validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate that the output data matches the target schema
        """
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True
        except ValidationError as e:
            self.validation_errors.append(str(e))
            return False
    
    def merge_chunk_results(self, chunk_results: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge results from multiple chunks into a single valid output
        """
        if not chunk_results:
            return {}
        
        # Simple merge strategy - take the first valid result
        for result in chunk_results:
            if self.validate_against_schema(result, schema):
                return result
        
        # If no valid results, return empty dict
        return {}
    
    def create_schema_prompt(self, schema: Dict[str, Any]) -> str:
        """
        Create a prompt that includes the target schema
        """
        schema_str = json.dumps(schema, indent=2)
        return f"""
You are a smart AI agent that converts unstructured text into structured JSON format.

IMPORTANT: The output MUST strictly follow the provided JSON schema. Do not add extra fields or modify the structure.

Target Schema:
{schema_str}

Instructions:
1. Read and understand the input text
2. Extract relevant information
3. Structure the data EXACTLY according to the target schema
4. Ensure all required fields are present
5. Validate that the output matches the schema structure

Input:
{{input_text}}

Output:
Return ONLY a valid JSON object that matches the target schema exactly. No explanations or additional text.
"""
    
    def extract_schema_fields(self, schema: Dict[str, Any]) -> List[str]:
        """
        Extract all field names from a JSON schema for analysis
        """
        fields = []
        
        def extract_fields(obj, path=""):
            if isinstance(obj, dict):
                if "properties" in obj:
                    for field_name, field_schema in obj["properties"].items():
                        current_path = f"{path}.{field_name}" if path else field_name
                        fields.append(current_path)
                        extract_fields(field_schema, current_path)
                elif "items" in obj:
                    extract_fields(obj["items"], path)
                elif "type" in obj and obj["type"] == "object":
                    # Handle nested objects
                    if "properties" in obj:
                        for field_name, field_schema in obj["properties"].items():
                            current_path = f"{path}.{field_name}" if path else field_name
                            fields.append(current_path)
                            extract_fields(field_schema, current_path)
        
        extract_fields(schema)
        return fields
    
    def analyze_schema_complexity(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze schema complexity for processing optimization
        """
        fields = self.extract_schema_fields(schema)
        
        # Count nested levels
        max_depth = 0
        for field in fields:
            depth = field.count('.')
            max_depth = max(max_depth, depth)
        
        # Count total fields
        total_fields = len(fields)
        
        # Analyze field types
        field_types = {}
        def analyze_types(obj):
            if isinstance(obj, dict):
                if "type" in obj:
                    field_type = obj["type"]
                    field_types[field_type] = field_types.get(field_type, 0) + 1
                if "properties" in obj:
                    for field_schema in obj["properties"].values():
                        analyze_types(field_schema)
                if "items" in obj:
                    analyze_types(obj["items"])
        
        analyze_types(schema)
        
        return {
            "total_fields": total_fields,
            "max_depth": max_depth,
            "field_types": field_types,
            "complexity_score": total_fields * (max_depth + 1)
        }
    
    def optimize_chunk_size(self, schema_complexity: Dict[str, Any]) -> int:
        """
        Optimize chunk size based on schema complexity
        """
        complexity_score = schema_complexity.get("complexity_score", 0)
        total_fields = schema_complexity.get("total_fields", 0)
        
        # Adjust chunk size based on complexity
        if complexity_score > 1000:  # Very complex schema
            return 2000  # Smaller chunks for complex schemas
        elif total_fields > 100:  # Many fields
            return 2500  # Medium chunks
        else:
            return 3000  # Standard chunk size
    
    def get_validation_errors(self) -> List[str]:
        """
        Get list of validation errors
        """
        return self.validation_errors.copy()
    
    def clear_validation_errors(self):
        """
        Clear validation error history
        """
        self.validation_errors.clear() 