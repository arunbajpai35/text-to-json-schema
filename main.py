# main.py
import os
import json
import argparse
from time import sleep
from utils.config_loader import load_config
from utils.azure_llm import AzureOpenAIClient
from utils.chunker import chunk_text
from utils.schema_processor import SchemaProcessor

def read_file(filepath: str) -> str:
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filepath}")
    except Exception as e:
        raise Exception(f"Error reading file {filepath}: {e}")

def write_json(filepath: str, data: dict):
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        raise Exception(f"Error writing file {filepath}: {e}")

def validate_config(config):
    """Validate that required configuration is present"""
    if "azure" not in config:
        raise ValueError("Azure configuration section not found in config.ini")
    
    azure_config = config["azure"]
    required_fields = ["api_key", "api_base", "deployment_name", "api_version"]
    
    for field in required_fields:
        if not azure_config.get(field) or azure_config.get(field) == f"your-{field.replace('_', '-')}-here":
            raise ValueError(f"Please configure {field} in config.ini")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Convert text to JSON using schema')
    parser.add_argument('--input', '-i', required=True, help='Input text file path')
    parser.add_argument('--schema', '-s', required=True, help='Target JSON schema file path')
    parser.add_argument('--output', '-o', default='output.json', help='Output JSON file path')
    parser.add_argument('--chunk-size', '-c', type=int, default=3000, help='Maximum tokens per chunk')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    return parser.parse_args()

def process_with_schema(text: str, schema: dict, client: AzureOpenAIClient, 
                       processor: SchemaProcessor, chunk_size: int = 3000, verbose: bool = False):
    """
    Process text with schema-driven approach
    """
    # Analyze schema complexity
    complexity = processor.analyze_schema_complexity(schema)
    optimized_chunk_size = processor.optimize_chunk_size(complexity)
    
    if verbose:
        print(f"[📊] Schema Analysis:")
        print(f"  - Total fields: {complexity['total_fields']}")
        print(f"  - Max depth: {complexity['max_depth']}")
        print(f"  - Complexity score: {complexity['complexity_score']}")
        print(f"  - Optimized chunk size: {optimized_chunk_size} tokens")
    
    # Create schema-aware prompt
    system_prompt = processor.create_schema_prompt(schema)
    
    # Chunk the text
    chunks = chunk_text(text, max_tokens=optimized_chunk_size)
    
    if not chunks:
        raise ValueError("No text chunks generated from input")
    
    if verbose:
        print(f"[📝] Processing {len(chunks)} chunks...")
    
    chunk_results = []
    failed_chunks = []
    
    for idx, chunk in enumerate(chunks):
        if verbose:
            print(f"[⏳] Processing chunk {idx + 1}/{len(chunks)}...")
        
        try:
            result = client.get_completion(system_prompt, chunk)
            parsed = json.loads(result)
            
            # Validate against schema
            if processor.validate_against_schema(parsed, schema):
                chunk_results.append(parsed)
                if verbose:
                    print(f"[✅] Chunk {idx + 1} processed successfully")
            else:
                if verbose:
                    print(f"[⚠️] Chunk {idx + 1} failed schema validation")
                failed_chunks.append({
                    "chunk_index": idx,
                    "raw_output": result,
                    "error": "Schema validation failed",
                    "validation_errors": processor.get_validation_errors()
                })
            
            sleep(1)  # avoid rate limits
            
        except json.JSONDecodeError as e:
            if verbose:
                print(f"[❌] Chunk {idx + 1} failed to parse JSON: {e}")
            failed_chunks.append({
                "chunk_index": idx,
                "raw_output": result if 'result' in locals() else '',
                "error": f"JSON decode error: {e}"
            })
        except Exception as e:
            if verbose:
                print(f"[❌] Chunk {idx + 1} failed: {e}")
            failed_chunks.append({
                "chunk_index": idx,
                "raw_output": result if 'result' in locals() else '',
                "error": str(e)
            })
    
    # Merge results
    final_result = processor.merge_chunk_results(chunk_results, schema)
    
    return final_result, failed_chunks

def main():
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Load configuration
        config = load_config()
        validate_config(config)
        
        # Initialize components
        azure_config = config["azure"]
        client = AzureOpenAIClient(azure_config)
        processor = SchemaProcessor()
        
        # Read input files
        input_text = read_file(args.input)
        schema_json = read_file(args.schema)
        
        if not input_text.strip():
            raise ValueError("Input file is empty")
        
        # Parse schema
        try:
            schema = json.loads(schema_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON schema: {e}")
        
        if args.verbose:
            print(f"[📁] Input file: {args.input}")
            print(f"[📋] Schema file: {args.schema}")
            print(f"[💾] Output file: {args.output}")
            print(f"[📏] Chunk size: {args.chunk_size} tokens")
        
        # Process with schema
        result, failed_chunks = process_with_schema(
            input_text, schema, client, processor, 
            args.chunk_size, args.verbose
        )
        
        # Write results
        write_json(args.output, result)
        
        if failed_chunks:
            failed_chunks_path = args.output.replace('.json', '_failed_chunks.json')
            write_json(failed_chunks_path, failed_chunks)
            print(f"[⚠️] Some chunks failed. See details in {failed_chunks_path}")
        else:
            print("[✅] All chunks processed successfully.")
        
        if args.verbose:
            print(f"[📊] Final result written to: {args.output}")
            
    except KeyboardInterrupt:
        print("\n[⏹️] Process interrupted by user")
    except Exception as e:
        print(f"[❌] Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
