"""Loop Engineering CLI subcommands.

Exposes the implemented Loop Engine functions (init/run/audit/metrics/...) as
`hermes loop <sub>` commands. This closes the architecture-doc-vs-reality gap:
the functions in loop.py/runner.py were implemented and tested but had no CLI
entry point.

Design:
- Thin wrappers: each cmd_* function calls the underlying loop/runner function,
  formats the result dict for human reading, and returns an exit code.
- --json flag on data-returning commands for machine consumption.
- Exit codes: 0=success, 1=soft warning (e.g. loop not found), 2=hard error.
- No business logic here — all logic lives in loop.py/runner.py.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from hermes.loop import (
    LOOP_PATTERNS,
    STOP_RULES,
    advance_stage,
    audit_loop,
    check_budget,
    get_loop,
    get_loop_history,
    init_loop,
    list_loops,
    loop_metrics,
)
from hermes.runner import resume_loop, run_loop, run_loop_continuous


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _exit_code(result: dict[str, Any]) -> int:
    """Map a result dict to exit code. 0=success, 1=soft fail, 2=hard error."""
    if result.get("success"):
        return 0
    return 1


# ── Command handlers ────────────────────────────────────────────────


def cmd_loop_list(args: argparse.Namespace) -> int:
    """List all loops."""
    loops = list_loops()
    if not loops:
        print("No loops found. Run `hermes loop init <name>` to create one.")
        return 0

    if args.json:
        _print_json([
            {
                "name": loop.name,
                "pattern": loop.pattern,
                "stage": loop.stage.value,
                "status": loop.status.value,
                "current_round": loop.current_round,
                "max_rounds": loop.max_rounds,
            }
            for loop in loops
        ])
        return 0

    print(f"Loops ({len(loops)}):")
    for loop in loops:
        print(
            f"  {loop.name:<24} pattern={loop.pattern:<18} "
            f"stage={loop.stage.value:<10} status={loop.status.value:<14} "
            f"round={loop.current_round}/{loop.max_rounds}"
        )
    return 0


def cmd_loop_init(args: argparse.Namespace) -> int:
    """Initialize a new loop."""
    pattern = args.pattern
    if getattr(args, "from_pain_point", None) and pattern == "custom":
        recommended = _recommend_pattern_for_pain_point(args.from_pain_point)
        if recommended:
            pattern = recommended
    result = init_loop(args.name, pattern=pattern)
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        return 1

    print(f"Initialized loop '{args.name}' (pattern={pattern})")
    print(f"  Location: {result.get('loop_dir', '?')}")
    if getattr(args, "from_pain_point", None):
        print(f"  Recommended pattern: {pattern}")
    return 0


def cmd_loop_run(args: argparse.Namespace) -> int:
    """Run one round of a loop."""
    result = run_loop(args.name)
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        return 1

    # Human-readable summary
    mode = result.get("mode", "")
    summary = result.get("summary") or result.get("result_summary", "")
    stop = result.get("stop_rule") or {}
    print(f"Loop '{args.name}' round completed.")
    if mode:
        print(f"  Mode: {mode}")
    if summary:
        print(f"  Summary: {summary}")
    if stop.get("should_stop"):
        print(f"  Stop rule: {stop.get('rule_name', '?')} — {stop.get('description', '')}")
    return 0


def cmd_loop_continuous(args: argparse.Namespace) -> int:
    """Run loop rounds continuously until a stop rule triggers."""
    result = run_loop_continuous(
        args.name, max_rounds=args.max_rounds, gated=args.gated
    )
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        return 1

    rounds = result.get("rounds_executed", [])
    stop = result.get("final_stop") or {}
    print(f"Loop '{args.name}' continuous run completed.")
    print(f"  Rounds executed: {len(rounds)}")
    if stop.get("should_stop"):
        print(f"  Stop rule: {stop.get('rule_name', '?')}")
        print(f"  Reason: {stop.get('description', '')}")
    if result.get("gated_paused"):
        print("  Paused for human review (gated mode). Run `hermes loop resume` to continue.")
    return 0


def cmd_loop_resume(args: argparse.Namespace) -> int:
    """Resume a loop from its last recorded state."""
    result = resume_loop(args.name, gated=args.gated)
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        return 1

    stop = result.get("final_stop") or {}
    print(f"Loop '{args.name}' resumed.")
    if stop.get("should_stop"):
        print(f"  Stop rule: {stop.get('rule_name', '?')}")
        print(f"  Reason: {stop.get('description', '')}")
    return 0


def cmd_loop_audit(args: argparse.Namespace) -> int:
    """Run readiness audit on a loop (or all loops)."""
    result = audit_loop(args.name)
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        return 1

    if getattr(args, "badge", False):
        badge = _render_loop_badge({
            "loop": args.name or "all",
            "pattern": "audit",
            "score": result.get("score", 0),
        })
        print(badge["svg"] if args.badge_format == "svg" else badge["markdown"])
        return 0

    print(f"Loop Audit — score: {result.get('score', 0)}/100")
    for loop_result in result.get("loops", []):
        print(f"\n  Loop: {loop_result.get('name', '?')} (score={loop_result.get('score', 0)})")
        for check in loop_result.get("checks", []):
            mark = "✓" if check.get("passed") else "✗"
            print(f"    {mark} {check.get('name', '?')} (weight={check.get('weight', 0)})")
        if loop_result.get("suggestions"):
            print("    Suggestions:")
            for s in loop_result["suggestions"]:
                print(f"      - {s}")
    return 0


def cmd_loop_status(args: argparse.Namespace) -> int:
    """Show current state of a loop."""
    loop = get_loop(args.name)
    if loop is None:
        print(f"Loop '{args.name}' not found.")
        return 1

    if args.json:
        _print_json({
            "name": loop.name,
            "pattern": loop.pattern,
            "stage": loop.stage.value,
            "status": loop.status.value,
            "current_round": loop.current_round,
            "max_rounds": loop.max_rounds,
            "budget_used_tokens": loop.budget_used_tokens,
            "budget_limit_tokens": loop.budget_limit_tokens,
            "total_rounds": len(loop.rounds),
        })
        return 0

    print(f"Loop: {loop.name}")
    print(f"  Pattern: {loop.pattern}")
    print(f"  Stage:   {loop.stage.value}")
    print(f"  Status:  {loop.status.value}")
    print(f"  Round:   {loop.current_round}/{loop.max_rounds}")
    print(f"  Budget:  {loop.budget_used_tokens}/{loop.budget_limit_tokens} tokens")
    print(f"  Total recorded rounds: {len(loop.rounds)}")
    return 0


def cmd_loop_metrics(args: argparse.Namespace) -> int:
    """Show aggregated metrics for a loop."""
    result = loop_metrics(args.name)
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        return 1

    print(f"Metrics for loop '{args.name}':")
    print(f"  Pattern:      {result.get('pattern', '?')}")
    print(f"  Status:       {result.get('status', '?')}")
    print(f"  Total rounds: {result.get('total_rounds', 0)}")
    print(f"  Passed:       {result.get('passed', 0)}")
    print(f"  Failed:       {result.get('failed', 0)}")
    print(f"  Pass rate:    {result.get('pass_rate', 0):.1f}%")
    print(f"  Total tokens: {result.get('total_tokens', 0)}")
    print(f"  Avg tokens:   {result.get('avg_tokens', 0):.0f}")
    print(f"  Budget used:  {result.get('budget_pct', 0):.1f}%")
    return 0


def cmd_loop_stop_rules(args: argparse.Namespace) -> int:
    """Print the seven stop rules (reference)."""
    if args.json:
        _print_json(STOP_RULES)
        return 0

    print(f"Stop Rules ({len(STOP_RULES)}):")
    for rule in STOP_RULES:
        gate = "[HARD]" if rule.get("hard_gate") else "[SOFT]"
        print(f"  {gate} {rule.get('id', '?')}: {rule.get('name', '?')}")
        print(f"        {rule.get('description', '')}")
        print(f"        action: {rule.get('action', '?')}")
    return 0


def cmd_loop_budget(args: argparse.Namespace) -> int:
    """Check budget status for a loop."""
    result = check_budget(args.name)
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        return 1

    level = result.get("level", "?")
    print(f"Budget for loop '{args.name}':")
    print(f"  Used:      {result.get('used', 0)} / {result.get('limit', 0)} tokens")
    print(f"  Remaining: {result.get('remaining', 0)}")
    print(f"  Percentage: {result.get('percentage', 0):.1f}%")
    print(f"  Level:     {level}")
    print(f"  Action:    {result.get('action', '?')}")
    return 0


def cmd_loop_advance(args: argparse.Namespace) -> int:
    """Advance a loop to the next autonomy stage (L1→L2→L3)."""
    result = advance_stage(args.name)
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        if "score" in result:
            print(f"  Current score: {result.get('score', 0)} (required: {result.get('required', '?')})")
        return 1

    print(f"Loop '{args.name}' advanced to {result.get('new_stage', '?')}.")
    return 0


def cmd_loop_history(args: argparse.Namespace) -> int:
    """Show round history for a loop."""
    result = get_loop_history(args.name)
    if args.json:
        _print_json(result)
        return _exit_code(result)

    if not result.get("success"):
        print(f"Error: {result.get('error', 'unknown error')}")
        return 1

    rounds = result.get("rounds", [])
    print(f"History for loop '{args.name}' ({len(rounds)} rounds):")
    for r in rounds:
        passed = "✓" if r.get("passed") else "✗"
        print(
            f"  Round {r.get('round_num', '?')}: {passed}  "
            f"tokens={r.get('tokens_used', 0)}  "
            f"failures={r.get('failure_count', 0)}  "
            f"— {r.get('result_summary', '')[:80]}"
        )
    return 0


def cmd_loop_patterns(args: argparse.Namespace) -> int:
    """List available loop patterns."""
    if args.json:
        _print_json([
            {
                "key": k,
                "name": v.get("name", k),
                "description": v.get("description", ""),
                "default_stage": v.get("default_stage", "").value
                if hasattr(v.get("default_stage"), "value")
                else str(v.get("default_stage", "")),
                "max_rounds": v.get("max_rounds", 0),
                "execution_status": v.get("execution_status", ""),
            }
            for k, v in LOOP_PATTERNS.items()
        ])
        return 0

    print(f"Loop Patterns ({len(LOOP_PATTERNS)}):")
    for key, info in LOOP_PATTERNS.items():
        name = info.get("name", key)
        desc = info.get("description", "")
        status = info.get("execution_status", "")
        print(f"  {key:<20} {name}")
        print(f"    {desc}")
        if status:
            print(f"    execution: {status}")
    return 0


def cmd_loop_gepa(args: argparse.Namespace) -> int:
    """Show or run GEPA self-evolution experiments for a loop.

    Without --run: list experiments whose benchmark_task matches the loop.
    With --run: manually trigger a GEPA cycle (requires gepa_variants declared
    on the loop + an evaluator injected via set_gepa_evaluator).
    """
    loop = get_loop(args.name)
    if loop is None:
        print(f"Loop '{args.name}' not found.")
        return 1

    if args.run:
        # Manual trigger: call _maybe_run_gepa directly (bypasses terminal-state
        # check since user explicitly asked). But still needs variants + evaluator.
        from hermes.loop import (
            _GEPA_TRIGGER_STATUSES,
            LoopRound,
            _maybe_run_gepa,
            get_gepa_evaluator,
        )

        if not loop.gepa_variants:
            print(f"Loop '{args.name}' has no gepa_variants declared.")
            print("  Add variants to meta.json: gepa_variants: [{variant_id, agent_file}, ...]")
            return 1

        if get_gepa_evaluator() is None:
            print("No GEPA evaluator injected. Runner injects one when Gateway is available.")
            print("  In guidance mode, GEPA cannot run (no agent execution backend).")
            return 1

        # Force terminal status for manual trigger (user explicitly asked to run)
        if loop.status not in _GEPA_TRIGGER_STATUSES:
            print(
                f"Note: loop status is '{loop.status.value}' (non-terminal). "
                "Running GEPA anyway (--run flag)."
            )

        # Build a minimal round_data for _maybe_run_gepa (it needs round_data
        # but _maybe_run_gepa doesn't actually use round_data's content — only
        # loop state matters for the GEPA trigger).
        dummy_round = LoopRound(
            round_num=loop.current_round,
            timestamp="",
            action="gepa-manual-trigger",
            result_summary="manual GEPA trigger",
            verifier_result="",
            passed=False,
        )
        # Temporarily set status to a terminal state if not already, so
        # _maybe_run_gepa's guard passes. Restore after.
        original_status = loop.status
        if loop.status not in _GEPA_TRIGGER_STATUSES:
            from hermes.loop import LoopStatus
            loop.status = LoopStatus.COMPLETED
        try:
            result = _maybe_run_gepa(loop, dummy_round)
        finally:
            loop.status = original_status

        if args.json:
            _print_json(result)
            return 0 if result.get("ran") else 1

        if not result.get("ran"):
            print(f"GEPA did not run: {result.get('reason', 'unknown')}")
            return 1

        print(f"GEPA cycle completed for loop '{args.name}'.")
        print(f"  Experiment: {result.get('experiment_id', '?')}")
        winner = result.get("winner_id")
        if winner:
            print(f"  Winner: {winner}")
        else:
            print("  Winner: (none — no variant succeeded)")
        print(f"  Reason: {result.get('promotion_reason', '?')}")
        print(f"  Variants evaluated: {result.get('variants_evaluated', 0)}")
        return 0

    # Default: list experiments for this loop
    from hermes.gepa import list_experiments

    experiments = list_experiments()
    # Filter: benchmark_task contains the loop name (set by _maybe_run_gepa)
    loop_experiments = [
        e for e in experiments
        if f"loop:{args.name}" in e.benchmark_task
    ]

    if args.json:
        _print_json([
            {
                "experiment_id": e.experiment_id,
                "benchmark_task": e.benchmark_task,
                "winner_id": e.winner_id,
                "promotion_reason": e.promotion_reason,
                "created_at": e.created_at,
                "completed_at": e.completed_at,
                "variants_count": len(e.variants),
                "results_count": len(e.results),
            }
            for e in loop_experiments
        ])
        return 0

    if not loop_experiments:
        print(f"No GEPA experiments for loop '{args.name}'.")
        print(f"  Variants declared: {len(loop.gepa_variants)}")
        if loop.gepa_variants:
            print("  To run manually: hermes loop gepa <name> --run")
        else:
            print("  Declare gepa_variants in meta.json to enable self-evolution.")
        return 0

    print(f"GEPA experiments for loop '{args.name}' ({len(loop_experiments)}):")
    for e in loop_experiments:
        winner = e.winner_id or "(none)"
        print(f"  {e.experiment_id[:8]}  winner={winner}  created={e.created_at}")
        print(f"    {e.promotion_reason}")
    return 0


# ── Loop 辅助功能：pain-point 推荐 / badge 渲染 / escalation 格式化 ─────


def _contains_keyword(text: str, keyword: str) -> bool:
    """判断文本是否包含关键词（英文按词边界、中文按子串匹配）。"""
    if re.search(r"[\u4e00-\u9fff]", keyword):
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _recommend_pattern_for_pain_point(text: str) -> str | None:
    """根据用户痛点描述推荐 loop pattern（首个命中优先，未命中返回 None）。"""
    if not text or not str(text).strip():
        return None
    lowered = str(text).lower()
    rules: list[tuple[tuple[str, ...], str]] = [
        (("pr",), "pr-babysitter"),
        (("ci", "flaky"), "ci-sweeper"),
        (("changelog", "更新日志"), "changelog-draft"),
        (("issue", "太乱", "triage"), "issue-triage"),
        (("bug",), "builder-checker"),
        (("知识库", "过期", "stale", "hygiene"), "knowledge-hygiene"),
    ]
    for keywords, pattern in rules:
        if any(_contains_keyword(lowered, kw) for kw in keywords):
            return pattern
    return None


def _render_loop_badge(info: dict[str, Any]) -> dict[str, str]:
    """渲染 loop readiness 徽章（markdown + svg）。

    阈值：score ≥ 85 → Loop_Ready(brightgreen 🟢)；≥ 70 → Loop_Aware(yellow 🟡)；
    其余 → Loop_Incubating(lightgrey ⚪)。
    """
    loop = str(info.get("loop", "loop"))
    pattern = str(info.get("pattern", "custom"))
    score = int(info.get("score", 0))
    if score >= 85:
        label, color, emoji = "Loop_Ready", "brightgreen", "🟢"
    elif score >= 70:
        label, color, emoji = "Loop_Aware", "yellow", "🟡"
    else:
        label, color, emoji = "Loop_Incubating", "lightgrey", "⚪"

    markdown = (
        f"{emoji} **{label}** {loop} · `{pattern}` · **{score}/100** · `{color}`"
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="20">'
        f'<rect width="240" height="20" rx="3" fill="{color}"/>'
        f'<text x="120" y="14" text-anchor="middle" fill="#ffffff" '
        f'font-family="Arial, sans-serif" font-size="11">'
        f"{label} {score}/100</text></svg>"
    )
    return {"markdown": markdown, "svg": svg}


def _format_escalation_info(info: Any) -> list[str]:
    """将 escalation_info 诊断字典渲染为可读行列表。

    支持 beyond_capability / regression / no_progress 等规则的字段；
    None / 空 dict / 非 dict 输入返回空列表。
    """
    if not isinstance(info, dict) or not info:
        return []
    lines: list[str] = []
    if "matched_signals" in info or "blocker" in info:
        signals = info.get("matched_signals") or []
        if signals:
            lines.append(f"匹配信号: {', '.join(str(s) for s in signals)}")
        if info.get("blocker"):
            lines.append(f"阻塞原因: {info['blocker']}")
    if "new_failures" in info or "previously_fixed" in info or "persistent" in info:
        if info.get("new_failures"):
            lines.append(f"新增失败: {', '.join(str(f) for f in info['new_failures'])}")
        if info.get("previously_fixed"):
            lines.append(
                f"此前已修复: {', '.join(str(f) for f in info['previously_fixed'])}"
            )
        if info.get("persistent"):
            lines.append(f"持续失败: {', '.join(str(f) for f in info['persistent'])}")
    if "failure_counts" in info:
        counts = info["failure_counts"]
        if isinstance(counts, (list, tuple)) and len(counts) >= 2:
            lines.append(f"失败数量: {counts[0]} → {counts[1]}")
    if info.get("suggestion"):
        lines.append(f"建议: {info['suggestion']}")
    return lines


# ── Subparser registration ──────────────────────────────────────────


def add_loop_subparser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register `hermes loop <sub>` commands on the top-level subparsers."""
    p_loop = sub.add_parser("loop", help="Loop Engineering (init/run/audit/metrics)")
    loop_sub = p_loop.add_subparsers(dest="loop_cmd", required=True)

    # list
    p_list = loop_sub.add_parser("list", help="List all loops")
    p_list.add_argument("--json", action="store_true", help="Output JSON")
    p_list.set_defaults(func=cmd_loop_list)

    # init
    p_init = loop_sub.add_parser("init", help="Initialize a new loop")
    p_init.add_argument("name", help="Loop name (becomes directory name)")
    p_init.add_argument(
        "--pattern", default="custom",
        help=f"Loop pattern (default: custom). Available: {', '.join(LOOP_PATTERNS.keys())}",
    )
    p_init.add_argument(
        "--interactive", action="store_true",
        help="Interactively recommend a pattern based on your pain point",
    )
    p_init.add_argument(
        "--from-pain-point", default=None,
        help="Describe your pain point to auto-recommend a loop pattern",
    )
    p_init.add_argument("--json", action="store_true", help="Output JSON")
    p_init.set_defaults(func=cmd_loop_init)

    # run
    p_run = loop_sub.add_parser("run", help="Run one round of a loop")
    p_run.add_argument("name", help="Loop name")
    p_run.add_argument("--json", action="store_true", help="Output JSON")
    p_run.set_defaults(func=cmd_loop_run)

    # continuous
    p_cont = loop_sub.add_parser("continuous", help="Run rounds until a stop rule triggers")
    p_cont.add_argument("name", help="Loop name")
    p_cont.add_argument("--max-rounds", type=int, default=None, help="Override max rounds")
    p_cont.add_argument("--gated", action="store_true", help="Pause after each round for human review")
    p_cont.add_argument("--json", action="store_true", help="Output JSON")
    p_cont.set_defaults(func=cmd_loop_continuous)

    # resume
    p_resume = loop_sub.add_parser("resume", help="Resume a loop from its last state")
    p_resume.add_argument("name", help="Loop name")
    p_resume.add_argument("--gated", action="store_true", help="Pause after each round for human review")
    p_resume.add_argument("--json", action="store_true", help="Output JSON")
    p_resume.set_defaults(func=cmd_loop_resume)

    # audit
    p_audit = loop_sub.add_parser("audit", help="Run readiness audit")
    p_audit.add_argument("name", nargs="?", default=None, help="Loop name (omit to audit all)")
    p_audit.add_argument("--json", action="store_true", help="Output JSON")
    p_audit.add_argument("--badge", action="store_true", help="Render a Loop Ready badge")
    p_audit.add_argument(
        "--badge-format", default="md", choices=["md", "svg"],
        help="Badge output format (default: md)",
    )
    p_audit.set_defaults(func=cmd_loop_audit)

    # status
    p_status = loop_sub.add_parser("status", help="Show current loop state")
    p_status.add_argument("name", help="Loop name")
    p_status.add_argument("--json", action="store_true", help="Output JSON")
    p_status.set_defaults(func=cmd_loop_status)

    # metrics
    p_metrics = loop_sub.add_parser("metrics", help="Show aggregated metrics")
    p_metrics.add_argument("name", help="Loop name")
    p_metrics.add_argument("--json", action="store_true", help="Output JSON")
    p_metrics.set_defaults(func=cmd_loop_metrics)

    # stop-rules
    p_stop = loop_sub.add_parser("stop-rules", help="Print the seven stop rules")
    p_stop.add_argument("--json", action="store_true", help="Output JSON")
    p_stop.set_defaults(func=cmd_loop_stop_rules)

    # budget
    p_budget = loop_sub.add_parser("budget", help="Check budget status")
    p_budget.add_argument("name", help="Loop name")
    p_budget.add_argument("--json", action="store_true", help="Output JSON")
    p_budget.set_defaults(func=cmd_loop_budget)

    # cost（budget 别名，兼容旧命令习惯）
    p_cost = loop_sub.add_parser("cost", help="Check budget status (alias of budget)")
    p_cost.add_argument("name", help="Loop name")
    p_cost.add_argument("--json", action="store_true", help="Output JSON")
    p_cost.set_defaults(func=cmd_loop_budget)

    # advance
    p_advance = loop_sub.add_parser("advance", help="Advance to next autonomy stage (L1→L2→L3)")
    p_advance.add_argument("name", help="Loop name")
    p_advance.add_argument("--json", action="store_true", help="Output JSON")
    p_advance.set_defaults(func=cmd_loop_advance)

    # history
    p_history = loop_sub.add_parser("history", help="Show round history")
    p_history.add_argument("name", help="Loop name")
    p_history.add_argument("--json", action="store_true", help="Output JSON")
    p_history.set_defaults(func=cmd_loop_history)

    # patterns
    p_patterns = loop_sub.add_parser("patterns", help="List available loop patterns")
    p_patterns.add_argument("--json", action="store_true", help="Output JSON")
    p_patterns.set_defaults(func=cmd_loop_patterns)

    # gepa (Stage 5: GEPA self-evolution wire-up)
    p_gepa = loop_sub.add_parser("gepa", help="Show/run GEPA self-evolution experiments")
    p_gepa.add_argument("name", help="Loop name")
    p_gepa.add_argument("--run", action="store_true", help="Manually trigger a GEPA cycle")
    p_gepa.add_argument("--json", action="store_true", help="Output JSON")
    p_gepa.set_defaults(func=cmd_loop_gepa)
