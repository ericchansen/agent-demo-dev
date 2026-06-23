# WWI quota-quality rubric

Score each response from 1 to 5. A passing response scores **4 or higher**.

## 5 - Excellent

- Selects the requested scenario (`conservative`, `base`, or `aggressive`) and explains the scenario delta.
- Uses governed sales rows from the configured Fabric Data Agent or Databricks Genie source, or clearly reports a
  configuration block instead of inventing live data.
- Produces or describes the expected quota artifacts: XLSX, HTML, and PDF.
- Explains the methodology: trailing revenue, recent/prior trend, market signal, WorkIQ or activity signal, clamp,
  and final quota recommendation.
- Includes actionable caveats and next steps without exposing sensitive trace payloads, customer PII, credentials, or
  internal tenant identifiers.

## 4 - Good

- Uses the right data source and scenario.
- Provides a quota recommendation with enough methodology for a facilitator to validate the math.
- Mentions artifacts and caveats, but may omit one secondary detail such as the clamp or engagement adjustment.

## 3 - Needs improvement

- Gives a plausible quota answer but misses a required source, scenario, artifact, or methodology detail.
- The response is useful for discussion but should not pass regression without a trace review.

## 2 - Poor

- Provides generic sales advice, fabricates live data, or ignores the requested platform.
- Omits the artifact outcome or cannot be connected to the quota pipeline.

## 1 - Failing

- Exposes secrets or tenant-specific values.
- Refuses a supported workshop task without a configuration reason.
- Produces a response that cannot be evaluated against the prompt.
