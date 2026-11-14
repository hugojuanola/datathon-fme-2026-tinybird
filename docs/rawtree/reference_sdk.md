# TypeScript SDK (/docs/reference/sdk)



TypeScript SDK [#typescript-sdk]

Use these TypeScript packages with the service API:

* [`@rawtree/sdk`](https://www.npmjs.com/package/@rawtree/sdk) for query, insert, and table metadata.
* [`@rawtree/otel`](https://www.npmjs.com/package/@rawtree/otel) for OpenTelemetry setup, RawTree trace export, and optional [AI SDK](https://ai-sdk.dev/) integration.

The SDK source is public at [`rawtreedb/rawtree-sdk-typescript`](https://github.com/rawtreedb/rawtree-sdk-typescript).

Install [#install]

```bash
npm install @rawtree/sdk
```

For OpenTelemetry helpers:

```bash
npm install @rawtree/otel
```

API client [#api-client]

```ts
import { RawTree } from "@rawtree/sdk";

const rawtree = new RawTree({
  apiKey: process.env.RAWTREE_API_KEY!,
});

await rawtree.insert("events", [
  { event: "signup", user_id: "u_123" },
]);

const result = await rawtree.query<{ event: string; count: number }>(
  "SELECT event, count() AS count FROM events GROUP BY event",
);

const tables = await rawtree.tables.list();
const schema = await rawtree.tables.describe("events");
```

The SDK sends the API key as `Authorization: Bearer <apiKey>`. See the [API reference](/docs/reference/api) for the underlying HTTP surface.

OpenTelemetry and AI integration [#opentelemetry-and-ai-integration]

Use `@rawtree/otel` when you want a TypeScript app to export OpenTelemetry traces to RawTree, including [AI SDK](https://ai-sdk.dev/) telemetry. For AI SDK telemetry, also install `ai`, `@ai-sdk/otel`, and the provider you use, such as `@ai-sdk/openai`:

```ts
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { registerOTel, aiSdkIntegration } from "@rawtree/otel";

const rawtree = registerOTel({
  apiKey: process.env.RAWTREE_API_KEY!,
  database: "observability",
  table: "ai_traces",
  serviceName: "checkout-agent",
  environment: "production",
  integrations: [aiSdkIntegration()],
  onExportError: (error) => {
    console.warn("RawTree trace export failed", error);
  },
});

try {
  const result = await generateText({
    model: openai("gpt-4o"),
    prompt: "Summarize the latest checkout incident.",
    telemetry: {
      functionId: "checkout-incident-summary",
    },
  });

  console.log(result.text);
} finally {
  await rawtree.shutdown();
}
```

`registerOTel` options:

| Option          | Description                                                    |
| --------------- | -------------------------------------------------------------- |
| `apiKey`        | Service API key. Required.                                     |
| `database`      | Database to write spans to. Defaults to your default database. |
| `table`         | Table to write spans to. Defaults to `traces`.                 |
| `serviceName`   | Stored as the OpenTelemetry resource attribute `service.name`. |
| `environment`   | Deployment environment, such as `production`.                  |
| `integrations`  | Tool integrations to enable, such as `aiSdkIntegration()`.     |
| `onExportError` | Called with the `Error` for every failed export.               |

The exporter sends traces only. It posts OTLP JSON to the [insert API](/docs/reference/api) with the `otlp-traces` transform, so the table gets one row per span.

The AI SDK integration records prompts and outputs by default, in the `gen_ai.input.messages` and `gen_ai.output.messages` span attributes. To keep timing, model, and token usage without that content, turn recording off per call or agent:

```ts
telemetry: {
  recordInputs: false,
  recordOutputs: false,
},
```

Failed exports don't throw into your app. By default, a failed export is logged once with `console.error`, and repeats of the same message are not logged again. Pass `onExportError` to handle failures yourself. It replaces the default logging. `shutdown()` flushes pending spans and doesn't reject when an export fails.

For native OTLP endpoints, Collector setup, destination tables, and smoke tests, see the [OpenTelemetry guide](/docs/integrations/opentelemetry).
