# Provider And Storage Interfaces

## Ports

- `ILLMService` and `IEmbeddingService` define complete, streaming, chat, tool,
  and embedding operations plus availability metadata.
- `IFileRepository` defines bounded file read/write/list/delete behavior.
- `IVectorStoreRepository` defines point upsert, batch upsert, search, lookup,
  deletion, and collection lifecycle.
- `IQualityChecker` and `ICodeAnalyzer` define structured quality and code
  analysis results.

`LocalFileRepository` is the built-in local implementation. Atomic helpers
construct and filter quality issues/reports without choosing persistence.

## Optional Implementations

`OpenAILLMService` and `OpenAIEmbeddingService` require the `openai` extra and
an explicit key or `OPENAI_API_KEY`. `QdrantVectorStore` requires the `qdrant`
extra and a caller-selected URL/key. Constructors expose `is_available()` so an
application can fail before starting work.

Importing provider modules does not send traffic. Calling generation,
embedding, vector, or collection methods can contact external services, incur
cost, and transmit caller data. Applications must enforce consent, retention,
redaction, timeouts, and network policy around those calls.

## Implementing A Provider

Implement every abstract method, preserve async streaming semantics, return the
documented response models, and surface provider errors rather than returning a
successful empty value. Register implementations through `ServiceContainer`
when dependency injection is useful.

See [Python API](reference/python-api.md) for every method signature and
[Configuration](CONFIGURATION.md) for credential handling.
