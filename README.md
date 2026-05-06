# text-to-json-schema

CLI that converts unstructured text into a JSON object matching a target [JSON Schema](https://json-schema.org/), using Azure OpenAI. Built as a take-home for Metaforms.ai.

## quickstart

```bash
pip install -r requirements.txt
cp config.template.ini config.ini   # fill in your azure openai creds
python main.py --input samples/input_large.txt \
               --schema samples/schemas/product_schema.json \
               --output result.json --verbose
```

## how it works

1. Load the input text and the target schema.
2. Inspect the schema (depth, field count) and pick a chunk size — denser schemas get smaller chunks so the model has more headroom per call.
3. Token-chunk the input with `tiktoken` (`cl100k_base`).
4. For each chunk, send a system prompt that embeds the schema and ask the model for a JSON object. JSON mode is enabled on the API call.
5. Validate each chunk's output against the schema with `jsonschema`. Drop failed chunks into a `*_failed_chunks.json` sidecar so you can inspect them.
6. Deep-merge the surviving chunks into one object: dicts merge recursively, arrays concatenate, and on scalar conflicts the first non-null value wins.

## design choices

- **schema embedded in the prompt, not derived from the text.** A fuzzy free-form extraction would have been simpler but the assignment is specifically about hitting a target shape — pinning the schema in the system prompt keeps the model honest.
- **chunk-then-merge instead of streaming a single huge call.** Lets the tool handle inputs that don't fit the model context window. The trade-off is that the merge step has to actually be correct (early versions kept only the first chunk — fixed).
- **first non-null wins on scalar conflicts.** The input is read top-to-bottom; the first mention of a value is usually the canonical one. Last-wins would let later, parenthetical mentions overwrite the headline value.
- **per-chunk validation, not just final.** Failing fast on a single bad chunk keeps a corrupted extraction out of the merged output, and the failed-chunk sidecar makes prompt regressions debuggable.

## what this is not

- not a benchmarked accuracy claim — there's no eval harness here, just structural validation. The schema-conformance pass rate depends entirely on the schema and input.
- not parallel — chunks are processed sequentially with a 1s sleep to stay under rate limits.
- not a streaming API — one shot per chunk.

## tests

```bash
pytest
```

LLM calls are mocked; the suite runs without azure credentials.

## stack

python · azure openai (gpt-4o family) · tiktoken · jsonschema · backoff · pytest
