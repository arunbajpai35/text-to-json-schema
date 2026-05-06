import json
import argparse
import logging
import os
import sys
from time import sleep

from utils.config_loader import load_config
from utils.azure_llm import AzureOpenAIClient
from utils.chunker import chunk_text
from utils.schema_processor import SchemaProcessor

log = logging.getLogger("text_to_json_schema")


def read_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_json(filepath: str, data: dict) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def validate_config(config) -> None:
    if "azure" not in config:
        raise ValueError("azure configuration section not found")
    azure_config = config["azure"]
    for field in ("api_key", "api_base", "deployment_name", "api_version"):
        value = azure_config.get(field)
        placeholder = f"your-{field.replace('_', '-')}-here"
        if not value or value == placeholder:
            raise ValueError(f"missing config value: {field}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Convert text to JSON using a schema")
    parser.add_argument("--input", "-i", required=True, help="Input text file")
    parser.add_argument("--schema", "-s", required=True, help="Target JSON schema file")
    parser.add_argument("--output", "-o", default="output.json", help="Output JSON file")
    parser.add_argument(
        "--chunk-size",
        "-c",
        type=int,
        default=3000,
        help="Maximum tokens per chunk (overridden by schema-complexity heuristic)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return parser.parse_args()


def process_with_schema(
    text: str,
    schema: dict,
    client: AzureOpenAIClient,
    processor: SchemaProcessor,
    chunk_size: int = 3000,
    verbose: bool = False,
):
    complexity = processor.analyze_schema_complexity(schema)
    optimized_chunk_size = processor.optimize_chunk_size(complexity)

    log.info(
        "schema: fields=%d depth=%d complexity=%d chunk_size=%d",
        complexity["total_fields"],
        complexity["max_depth"],
        complexity["complexity_score"],
        optimized_chunk_size,
    )

    system_prompt = processor.create_schema_prompt(schema)
    chunks = chunk_text(text, max_tokens=optimized_chunk_size)
    if not chunks:
        raise ValueError("no text chunks generated from input")

    log.info("processing %d chunk(s)", len(chunks))

    chunk_results = []
    failed_chunks = []

    for idx, chunk in enumerate(chunks):
        log.debug("chunk %d/%d", idx + 1, len(chunks))
        result = ""
        try:
            result = client.get_completion(system_prompt, chunk)
            parsed = json.loads(result)
            if processor.validate_against_schema(parsed, schema):
                chunk_results.append(parsed)
            else:
                log.warning("chunk %d failed schema validation", idx + 1)
                failed_chunks.append({
                    "chunk_index": idx,
                    "raw_output": result,
                    "error": "Schema validation failed",
                    "validation_errors": processor.get_validation_errors(),
                })
            sleep(1)
        except json.JSONDecodeError as e:
            log.warning("chunk %d invalid json: %s", idx + 1, e)
            failed_chunks.append({
                "chunk_index": idx,
                "raw_output": result,
                "error": f"JSON decode error: {e}",
            })
        except Exception as e:
            log.warning("chunk %d failed: %s", idx + 1, e)
            failed_chunks.append({
                "chunk_index": idx,
                "raw_output": result,
                "error": str(e),
            })

    final_result = processor.merge_chunk_results(chunk_results, schema)
    return final_result, failed_chunks


def _failed_chunks_path(output_path: str) -> str:
    base, ext = os.path.splitext(output_path)
    return f"{base}_failed_chunks{ext or '.json'}"


def main() -> int:
    args = parse_arguments()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        config = load_config()
        validate_config(config)

        client = AzureOpenAIClient(config["azure"])
        processor = SchemaProcessor()

        input_text = read_file(args.input)
        schema_json = read_file(args.schema)

        if not input_text.strip():
            raise ValueError("input file is empty")

        try:
            schema = json.loads(schema_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON schema: {e}")

        result, failed_chunks = process_with_schema(
            input_text, schema, client, processor, args.chunk_size, args.verbose
        )

        write_json(args.output, result)

        if failed_chunks:
            sidecar = _failed_chunks_path(args.output)
            write_json(sidecar, failed_chunks)
            log.warning("%d chunk(s) failed; details in %s", len(failed_chunks), sidecar)
        else:
            log.info("all chunks processed successfully")

        log.info("output written to %s", args.output)
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130
    except Exception as e:
        log.error("error: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
