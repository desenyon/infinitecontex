# Mental Model

Think of Infinite Context as a context compiler:

- Input: repo structure, code behavior hints, git/workflow signals, decision memory.
- Transform: rank, summarize, and compress into layered packets.
- Output: deterministic restore artifacts that minimize tokens while preserving intent.

Layers:

- Layer A: Structural context.
- Layer B: Behavioral context.
- Layer C: Intent context.
- Layer D: Working-set context.

The restore phase is not replaying logs. It validates assumptions and identifies stale/missing/changed state relative to the current repo.
