import json
from typing import Any, Dict, List, Tuple

import jsonschema
from jsonschema import ValidationError


class SchemaProcessor:
    def validate_against_schema(
        self, data: Dict[str, Any], schema: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Return (ok, errors). Errors is empty when ok is True."""
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, []
        except ValidationError as e:
            return False, [str(e)]

    def merge_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge chunk outputs into a single object.

        Dicts merge recursively. Arrays concatenate. For scalar conflicts, the
        first non-null value wins — chunk order reflects input order, so earlier
        mentions are treated as authoritative.
        """
        if not chunk_results:
            return {}
        merged: Dict[str, Any] = {}
        for result in chunk_results:
            if isinstance(result, dict):
                merged = self._deep_merge(merged, result)
        return merged

    def _deep_merge(self, a: Any, b: Any) -> Any:
        if isinstance(a, dict) and isinstance(b, dict):
            out = dict(a)
            for k, v in b.items():
                out[k] = self._deep_merge(a[k], v) if k in a else v
            return out
        if isinstance(a, list) and isinstance(b, list):
            return a + b
        if a is None or a == "":
            return b
        return a

    def create_schema_prompt(self, schema: Dict[str, Any]) -> str:
        schema_str = json.dumps(schema, indent=2)
        return f"""You convert unstructured text into structured JSON.

The output MUST strictly follow the provided JSON schema. Do not add extra fields or modify the structure.

Target Schema:
{schema_str}

Instructions:
1. Read the input text carefully.
2. Extract values that map to the schema fields.
3. Return a single JSON object that matches the schema exactly — no prose, no markdown.
4. If a required field is not present in the text, leave it null rather than inventing a value.
"""

    def extract_schema_fields(self, schema: Dict[str, Any]) -> List[str]:
        fields: List[str] = []

        def walk(obj, path=""):
            if not isinstance(obj, dict):
                return
            if "properties" in obj:
                for name, sub in obj["properties"].items():
                    current = f"{path}.{name}" if path else name
                    fields.append(current)
                    walk(sub, current)
            if "items" in obj:
                walk(obj["items"], path)

        walk(schema)
        return fields

    def analyze_schema_complexity(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        fields = self.extract_schema_fields(schema)
        max_depth = max((f.count(".") for f in fields), default=0)
        total_fields = len(fields)

        field_types: Dict[str, int] = {}

        def analyze_types(obj):
            if not isinstance(obj, dict):
                return
            if "type" in obj:
                # JSON Schema permits `type` to be a list (e.g. ["string", "null"]).
                types = obj["type"] if isinstance(obj["type"], list) else [obj["type"]]
                for t in types:
                    field_types[t] = field_types.get(t, 0) + 1
            if "properties" in obj:
                for sub in obj["properties"].values():
                    analyze_types(sub)
            if "items" in obj:
                analyze_types(obj["items"])

        analyze_types(schema)

        return {
            "total_fields": total_fields,
            "max_depth": max_depth,
            "field_types": field_types,
            "complexity_score": total_fields * (max_depth + 1),
        }

    def optimize_chunk_size(self, schema_complexity: Dict[str, Any]) -> int:
        complexity_score = schema_complexity.get("complexity_score", 0)
        total_fields = schema_complexity.get("total_fields", 0)
        if complexity_score > 1000:
            return 2000
        if total_fields > 100:
            return 2500
        return 3000
