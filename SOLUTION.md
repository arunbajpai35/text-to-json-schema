# Text-to-JSON Schema Conversion System

## Architecture Overview

This system converts unstructured plain text into structured JSON format that strictly adheres to a desired schema. The solution uses Azure OpenAI's GPT-4o model with a chunking strategy to handle large inputs.

### Core Components

1. **Azure OpenAI Client** (`utils/azure_llm.py`)
   - Handles API communication with retry logic
   - Configurable timeout and token limits
   - Backoff strategy for rate limiting

2. **Text Chunker** (`utils/chunker.py`)
   - Splits large text into manageable chunks
   - Uses tiktoken for accurate token counting
   - Preserves semantic boundaries

3. **Schema-Driven Processor** (`main.py`)
   - Takes both text input and target schema
   - Validates output against schema
   - Merges results from multiple chunks

## Key Design Decisions

### 1. Schema-First Approach
**Decision**: Require target schema as input rather than inferring structure
**Rationale**: 
- Ensures output consistency and predictability
- Allows for complex nested structures (7+ levels)
- Supports validation against business requirements
- Enables handling of 100k+ field schemas

### 2. Chunking Strategy
**Decision**: Process large texts in chunks of 3000 tokens
**Rationale**:
- Balances context window usage with processing efficiency
- Allows handling of 50k+ token inputs
- Preserves semantic coherence within chunks
- Enables parallel processing potential

### 3. Azure OpenAI Integration
**Decision**: Use Azure OpenAI GPT-4o instead of open-source models
**Rationale**:
- Superior performance on structured output tasks
- Better handling of complex nested schemas
- Reliable JSON generation capabilities
- Cost not a constraint per assignment requirements

## Trade-offs Analysis

### 1. Chunk Size vs. Context Preservation
**Trade-off**: Larger chunks preserve more context but use more tokens
**Current Choice**: 3000 tokens per chunk
**Future Optimization**: Dynamic chunk sizing based on schema complexity

### 2. Schema Validation vs. Processing Speed
**Trade-off**: Strict validation adds latency but ensures quality
**Current Choice**: Post-processing validation
**Future Optimization**: Streaming validation with early termination

### 3. Retry Logic vs. Resource Usage
**Trade-off**: Aggressive retries increase reliability but cost
**Current Choice**: 3 retries with exponential backoff
**Future Optimization**: Circuit breaker pattern for repeated failures

## Performance Characteristics

### Input Handling
- **Small inputs** (< 3000 tokens): Single API call
- **Medium inputs** (3k-50k tokens): Multiple chunks, sequential processing
- **Large inputs** (50k+ tokens): Chunked processing with merge strategy

### Schema Complexity Support
- **Flat schemas**: Direct field mapping
- **Nested schemas** (2-3 levels): Object structure preservation
- **Deep nested schemas** (7+ levels): Recursive processing
- **Array schemas**: List comprehension and validation

### Error Handling
- **JSON parsing errors**: Retry with modified prompt
- **Schema validation errors**: Partial result preservation
- **API failures**: Exponential backoff with circuit breaker

## Deployment Options

### CLI Interface (Current)
```bash
python main.py --input text.txt --schema schema.json --output result.json
```

### Web Interface (Future Enhancement)
- Flask/FastAPI backend
- File upload for text and schema
- Real-time processing status
- Download results in JSON format

## Scalability Considerations

### Current Limitations
- Sequential chunk processing
- Single-threaded execution
- Memory constraints for very large schemas

### Future Optimizations
- Parallel chunk processing
- Streaming response handling
- Distributed processing for 100k+ field schemas
- Caching for repeated schema patterns

## Cost Analysis

### API Usage
- **Small inputs**: ~$0.01-0.05 per request
- **Medium inputs**: ~$0.05-0.20 per request  
- **Large inputs**: ~$0.20-1.00 per request

### Optimization Opportunities
- Schema caching for repeated patterns
- Batch processing for multiple inputs
- Token optimization through prompt engineering

## Security Considerations

### Data Handling
- No persistent storage of input data
- Secure API key management via config files
- Input sanitization for malicious content

### API Security
- Rate limiting to prevent abuse
- Request timeout protection
- Error message sanitization

## Testing Strategy

### Unit Tests
- Schema validation functions
- Chunking algorithm accuracy
- JSON parsing robustness

### Integration Tests
- End-to-end processing pipeline
- Large input handling (50k+ tokens)
- Complex schema validation (7+ nested levels)

### Performance Tests
- Token counting accuracy
- Processing time benchmarks
- Memory usage optimization

## Future Enhancements

### 1. Advanced Schema Support
- JSON Schema validation
- Custom validation rules
- Schema versioning

### 2. Performance Optimizations
- Parallel processing
- Streaming responses
- Intelligent chunking

### 3. User Experience
- Web interface
- Real-time progress tracking
- Result preview and editing

### 4. Enterprise Features
- Multi-tenant support
- Audit logging
- Advanced error reporting
