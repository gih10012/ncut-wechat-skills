# Account ownership and purpose

- 操作的账号均为**本人持有的合法账号**。
- 用途：个人自动化 / 内容归档（非他人账号、非批量、非反作弊）。
- 工作目标：优化 skills，服务本人的合法个人工作流。

# Project intent

Build skills that can independently discover and add capabilities in a fresh context, following the EaseCation web-api model. Existing examples are starting points, not a whitelist of tasks the agent can perform. Read the relevant SKILL.md first; do not ask the user to supply endpoints when they can be discovered from registered services, a service directory, an available client, or existing source evidence.

Current priority: verify direct reuse and independent discovery with real tasks. The longer roadmap is in README.md; do not execute it automatically during an ordinary request. UI use is limited to necessary authentication and observing interfaces, not routine business execution.

# Structure and execution

- Installed skills are symlinks to `skills/`; edit repository files. The two skills share the Python HTTP/knowledge core, not credentials.
- Normal hits execute the existing command/request. On a miss, discover only the relevant service, verify behavior, and add one capability plus a workflow only when needed. Do not create a new crawler project, background daemon, generic DSL, or a container merely to cover a new endpoint.
- Native message access must be verified against the user's own client/session. Public articles or business-Web cookies do not prove native message access. Preserve existing phone/Linux logins and avoid seizing the desktop.
- For writes, resolve current targets, body, prerequisites and success/readback behavior from current evidence. Keep one-time code/ticket/captcha values private. Readonly POSTs and local drafts must not be reported as remote writes. Non-idempotent failures require readback before retry.
- New-capability exploration has a 15-minute active-work limit per business objective, excluding time waiting for the user's authentication. Changing routes does not reset it. At the limit, stop that branch and report evidence, the remaining gap, and next options; never substitute an easier example as successful acceptance. Ask only for missing choices/authentication that cannot be obtained locally.

# Publishing and validation

The user explicitly requested this public GitHub repository and timely commits/pushes. Commit coherent verified increments and push them; do not request that authorization again. Never publish account state, message content, student data, captures, personal results, or secrets. Runtime state belongs outside the repository.

Run tests relevant to the change. A milestone requires corresponding real runtime evidence; offline tests only prove their covered behaviors. Before claiming fresh-context usability, exercise the documented commands without relying on old conversation artifacts or private source paths.
