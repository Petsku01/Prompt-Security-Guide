# Overnight Rebuild Instructions

## For Kuu (heartbeat processing)

When you receive a heartbeat, check this project's queue:

```bash
cat ~/.openclaw/workspace/prompt-security-guide/overnight-rebuild/queue.json
```

### Processing Logic

1. **Find next pending phase** where all `depends_on` phases are "complete"

2. **For that phase:**
   - If `web_searches` exists: run them first with `web_search` tool
   - Spawn sub-agent with `sessions_spawn`:
     - `agent: gemini` → use `agentId: "gemini"`
     - `agent: codex` → use `agentId: "codex"` with `runtime: "acp"`
     - `agent: main` → use default (Opus)
   - Include Senior Engineer prompt in task
   - Set appropriate timeout

3. **When sub-agent completes:**
   - Save output to `output_file`
   - Update phase status to "complete" in queue.json
   - Check for next phase

4. **When all phases complete:**
   - Generate FINAL_REPORT.md
   - Notify Petsku

### Senior Engineer Prompt (include in all tasks)

```
You are a senior software engineer. Key behaviors:
1. SURFACE ASSUMPTIONS before coding
2. STOP ON CONFUSION - don't guess
3. PUSH BACK on bad ideas
4. SIMPLICITY over cleverness
5. SURGICAL SCOPE - touch only what's asked

After changes provide: CHANGES MADE, POTENTIAL CONCERNS
```

### Status Updates

Update `queue.json` status field:
- `"pending"` - Not started
- `"running"` - In progress
- `"complete"` - Done
- `"failed"` - Error occurred

### File Locations

```
overnight-rebuild/
├── queue.json          # Task queue (update this)
├── STATUS.md           # Human-readable status
├── research/           # Phase 1 output
├── design/             # Phase 2 output
├── src/                # Phase 3 output
├── review/             # Phase 4 output
├── iterate/            # Phase 5 output
└── FINAL_REPORT.md     # Generated on completion
```

## Important Notes

- Don't rush - quality over speed
- If a phase fails, log error and continue to next possible phase
- Each web_search should be done before spawning the agent
- Compile web search results into the agent's task context
