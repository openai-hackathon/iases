# OpenAI API: GPT-5.6 and GPT-6 Model Names and Reasoning Effort

Verified on: 2026-09-12. Based on official OpenAI API documentation.

Use the model IDs below in the API's `model` field. Set reasoning effort through a separate parameter.

| Model | API model ID | Supported reasoning effort | Default effort | Official source |
| --- | --- | --- | --- | --- |
| GPT-5.6 Sol | `gpt-5.6-sol` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | `medium` | [Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol) |
| Alias for GPT-5.6 Sol | `gpt-5.6` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | `medium` | [Sol alias and effort](https://developers.openai.com/api/docs/models/gpt-5.6-sol) |
| GPT-5.6 Terra | `gpt-5.6-terra` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | `medium` | [Terra model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra) |
| GPT-5.6 Luna | `gpt-5.6-luna` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | `medium` | [Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna) |
| GPT-6 Astra | `gpt-6-astra` | `low`, `medium`, `high`, `xhigh`, `max` | Not explicitly stated in the official documentation reviewed; set it explicitly | [Astra model page](https://developers.openai.com/api/docs/models/gpt-6-astra) |

For GPT-6, use the documented full ID, `gpt-6-astra`. This review found no official confirmation that `gpt-6` is a supported alias. The published effort lists for the four general-purpose models above include neither `minimal` nor `ultra`; do not assume those values are supported. [Official model catalog](https://developers.openai.com/api/docs/models)

GPT-6 Astra does not support `none`; sending it returns HTTP 400. Its lowest supported effort is `low`. [Reasoning effort documentation](https://developers.openai.com/api/docs/guides/reasoning#reasoning-effort)

**API parameters**

The Responses API uses `reasoning.effort`. Chat Completions uses the top-level `reasoning_effort` field. Tool calling with GPT-6 Astra requires the Responses API. [GPT-6 Astra API configuration](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra)

Responses API: `POST https://api.openai.com/v1/responses`. Example request body:

```json
{
  "model": "gpt-6-astra",
  "reasoning": {
    "effort": "high"
  },
  "input": "Analyze the time complexity of this code: for i in range(n): print(i)"
}
```

Chat Completions: `POST https://api.openai.com/v1/chat/completions`. Example request body:

```json
{
  "model": "gpt-5.6-sol",
  "reasoning_effort": "medium",
  "messages": [
    {
      "role": "user",
      "content": "Analyze the time complexity of this code: for i in range(n): print(i)"
    }
  ]
}
```

You can replace the model and effort in these examples with a supported combination from the table, such as `gpt-5.6-luna` with `max`, or `gpt-6-astra` with `xhigh`. [Official model catalog](https://developers.openai.com/api/docs/models)

**Pro mode and reasoning effort**

GPT-5.6 Sol, Terra, and Luna support `reasoning.mode` values of `standard` (the default) and `pro` in the Responses API. Mode and effort are independent: Pro mode works with the selected model's supported efforts. If effort is omitted, GPT-5.6 defaults to `medium` in both modes. [GPT-5.6 Pro guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6), [Reasoning mode documentation](https://developers.openai.com/api/docs/guides/reasoning#reasoning-mode)

The official GPT-6 Astra guide also lists Pro mode as supported. Enable it by keeping the model ID and setting `reasoning.mode`; there is no need to append `-pro` to the model name. [GPT-6 Astra capabilities](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra)

Example Responses API request using Pro mode:

```json
{
  "model": "gpt-5.6-sol",
  "reasoning": {
    "mode": "pro",
    "effort": "high"
  },
  "input": "Review this database migration plan and identify steps that could fail and how to fix them."
}
```

Pro mode performs more model work, typically increasing latency and token usage. It is a separate setting from `effort: "max"`. [Reasoning mode documentation](https://developers.openai.com/api/docs/guides/reasoning#reasoning-mode)

The cybersecurity-specific `gpt-5.6-cyber` model requires separate approval and provisioning. Its model page did not list a complete set of supported efforts when reviewed, so the general-purpose GPT-5.6 settings have not been assumed to apply to it. [GPT-5.6 Cyber model page](https://developers.openai.com/api/docs/models/gpt-5.6-cyber)

This was a documentation review. No paid API calls were made, and model access for an individual account was not verified.
