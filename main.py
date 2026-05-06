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
        default=None,
        help="Maximum tokens per chunk. Defaults to a schema-complexity heuristic.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return parser.parse_args()


def _completion_with_repair(client, system_prompt, chunk):
    """Ask the model for JSON; on a parse failure, re-prompt once with the error."""
    raw = client.get_completion(system_prompt, chunk)
    try:
        return json.loads(raw), raw
    except json.JSONDecodeError as e:
        repair_prompt = (
            f"{system_prompt}\n\nThe previous response failed to parse as JSON: "
            f"{e}. Return only a valid JSON object."
        )
        raw = client.get_completion(repair_prompt, chunk)
        return json.loads(raw), raw


def process_with_schema(
    text: str,
    schema: dict,
    client: AzureOpenAIClient,
    processor: SchemaProcessor,
    chunk_size: int | None = None,
    verbose: bool = False,
):
    complexity = processor.analyze_schema_complexity(schema)
    effective_chunk_size = (
        chunk_size if chunk_size is not None
        else processor.optimize_chunk_size(complexity)
    )

    log.info(
        "schema: fields=%d depth=%d complexity=%d chunk_size=%d",
        complexity["total_fields"],
        complexity["max_depth"],
        complexity["complexity_score"],
        effective_chunk_size,
    )

    system_prompt = processor.create_schema_prompt(schema)
    chunks = chunk_text(text, max_tokens=effective_chunk_size)
    if not chunks:
        raise ValueError("no text chunks generated from input")

    log.info("processing %d chunk(s)", len(chunks))

    chunk_results = []
    failed_chunks = []

    for idx, chunk in enumerate(chunks):
        log.debug("chunk %d/%d", idx + 1, len(chunks))
        raw = ""
        try:
            parsed, raw = _completion_with_repair(client, system_prompt, chunk)
            chunk_results.append(parsed)
            sleep(1)
        except json.JSONDecodeError as e:
            log.warning("chunk %d invalid json after repair: %s", idx + 1, e)
            failed_chunks.append({
                "chunk_index": idx,
                "raw_output": raw,
                "error": f"JSON decode error: {e}",
            })
        except Exception as e:
            log.warning("chunk %d failed: %s", idx + 1, e)
            failed_chunks.append({
                "chunk_index": idx,
                "raw_output": raw,
                "error": str(e),
            })

    final_result = processor.merge_chunk_results(chunk_results, schema)
    if not processor.validate_against_schema(final_result, schema):
        log.warning(
            "merged output does not match schema: %s",
            "; ".join(processor.get_validation_errors()),
        )
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
