# Project intent

Build skills that can independently discover and add capabilities in a fresh context, following the EaseCation web-api model. Existing examples are starting points, not a whitelist of tasks the agent can perform. Read the relevant SKILL.md first; do not ask the user to supply endpoints when they can be discovered from registered services, a service directory, an available client, or existing source evidence.

Priorities: v0 real HTTP POST writes with readback and prerequisite examples; v1 native WeChat/WeCom message receive/send and public articles; v2 observed WeChat deep links; v3 school-Web alternatives for WeCom services, then per-service OAuth where necessary. Keep incomplete milestones explicit.

# Structure and execution

- Installed skills are symlinks to `skills/`; edit repository files. The two skills share the Python HTTP/knowledge core, not credentials.
- Normal hits execute the existing command/request. On a miss, discover only the relevant service, verify behavior, and add one capability plus a workflow only when needed. Do not create a new crawler project, background daemon, generic DSL, or a container merely to cover a new endpoint.
- Native message access must be verified against the user's own client/session. Public articles or business-Web cookies do not prove native message access. Preserve existing phone/Linux logins and avoid seizing the desktop.
- For writes, resolve current targets, body, prerequisites and success/readback behavior from current evidence. Keep one-time code/ticket/captcha values private. Readonly POSTs and local drafts must not be reported as remote writes. Non-idempotent failures require readback before retry.
- Use bounded exploration as a checkpoint, not a reason to abandon an authorized new capability. Change approaches when evidence warrants it. Ask only for missing choices/authentication that cannot be obtained locally.

# Publishing and validation

The user explicitly requested this public GitHub repository and timely commits/pushes. Commit coherent verified increments and push them; do not request that authorization again. Never publish account state, message content, student data, captures, personal results, or secrets. Runtime state belongs outside the repository.

Run tests relevant to the change. A milestone requires corresponding real runtime evidence; offline tests only prove their covered behaviors. Before claiming fresh-context usability, exercise the documented commands without relying on old conversation artifacts or private source paths.
