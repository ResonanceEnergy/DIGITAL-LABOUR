#!/usr/bin/env python3
"""
OPTIMUS Discord Bot — Task Optimization Engine
===============================================
Agent O · NCC Digital-Labour
Role     : Task Optimization Engine
Mandate  : Maximize task completion rate (target: 95% completion within SLA)
Channel  : #optimus  (🤖 CORE AGENTS category)
# App ID   : 1477878028716605661
# Pub Key  : df076bcc7085e97f99f5f56305f5753066ddee943781d1026a628c56ddc99025

Env vars (create .env.optimus or export in shell):
  OPTIMUS_DISCORD_BOT_TOKEN  — Bot token from Discord Developer Portal
  DISCORD_GUILD_ID           — NCC server (guild) ID
  OPTIMUS_CHANNEL_NAME       — channel to post in  (default: optimus)
  DAILY_BRIEFS_CHANNEL_NAME  — secondary channel   (default: daily-briefs)
  NCL_HOME                   — Path to NCL data root (default: ~/NCL)
  NCL_RELAY_PORT             — Relay server port     (default: 8787)
  DL_REPO          — Path to Digital-Labour repo (default: ~/repos/Digital-Labour)

Commands (prefix !optimus <cmd> OR !o <cmd>):
  status   — task queue + efficiency score
  health   — full system health via watchdog
  tasks    — pending / active / completed task breakdown
  missions — mission-runner status
  brief    — trigger daily brief
  cycle    — run one autonomous-scheduler cycle
  sla      — SLA compliance report
  logs [N] — last N event-log lines (default 20)
  help     — this list

Scheduled tasks:
  Every 10 min — SLA watchdog: alert if completion rate drops below 90%
  06:00 UTC    — daily performance brief to #optimus + #daily-briefs
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands, tasks

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [OPTIMUS] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("optimus.bot")

# ── Config ─────────────────────────────────────────────────────────────────────
TOKEN: str = os.environ.get("OPTIMUS_DISCORD_BOT_TOKEN", "")
GUILD_ID: int | None = None
_raw_guild = os.environ.get("DISCORD_GUILD_ID", "")
if _raw_guild and _raw_guild.strip().isdigit():
    GUILD_ID = int(_raw_guild.strip())
OPTIMUS_CH: str = os.environ.get("OPTIMUS_CHANNEL_NAME", "optimus")
BRIEFS_CH: str = os.environ.get("DAILY_BRIEFS_CHANNEL_NAME", "daily-briefs")

REPO_ROOT = Path(os.environ.get("DL_REPO",
                 Path.home() / "repos" / "Digital-Labour"))
RUNTIME = REPO_ROOT / "runtime"

# ── Colours ────────────────────────────────────────────────────────────────────
COLOR_OK = 0x2ECC71  # green
COLOR_WARN = 0xF39C12  # amber
COLOR_CRIT = 0xE74C3C  # red
COLOR_INFO = 0x3498DB  # blue
COLOR_OPTIMUS = 0xF1C40F  # gold — OPTIMUS brand

SLA_TARGET = 95.0  # % completion target
SLA_ALERT = 90.0  # alert threshold

VERSION = "1.0.0"

# ── Bot setup ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
# requires Privileged Intent enabled in Dev Portal — see below
intents.message_content = True

bot = commands.Bot(
    command_prefix=["!optimus ", "!o "],
    intents=intents,
    help_command=None,
    case_insensitive=True,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _find_channel(name: str) -> discord.TextChannel | None:
    for guild in bot.guilds:
        for ch in guild.text_channels:
            if ch.name.lower() == name.lower():
                return ch
    return None


def _run_watchdog() -> dict:
    """Run watchdog.run_checks() — import first, subprocess fallback."""
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from runtime.watchdog import run_checks  # type: ignore[import]

        return run_checks()
    except Exception as exc:
        log.warning("watchdog import failed, using subprocess: %s", exc)
    try:
        r = subprocess.run(
            [sys.executable, str(RUNTIME / "watchdog.py"), "--json"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO_ROOT),
        )
        return json.loads(r.stdout)
    except Exception as exc2:
        return {"error": str(exc2)}


def _overall_level(checks: dict) -> str:
    if "error" in checks:
        return "unknown"
    levels = [
        v.get("level", "ok" if v.get("ok", True) else "critical")
        for v in checks.values()
        if isinstance(v, dict)
    ]
    if "critical" in levels:
        return "critical"
    if "warn" in levels:
        return "warn"
    return "ok"


def _health_embed(
        checks: dict, title: str="⚡ OPTIMUS — Health Report") ->discord.Embed:
    level = _overall_level(checks)
    color = {"ok": COLOR_OK, "warn": COLOR_WARN,
        "critical": COLOR_CRIT}.get(level, COLOR_INFO)
    icon = {"ok": "🟢", "warn": "🟡", "critical": "🔴"}.get(level, "⚪")

    embed = discord.Embed(
        title=f"{icon} {title}",
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"OPTIMUS v{VERSION} · Task Optimization Engine")

    if "error" in checks:
        embed.description = f"```\nWatchdog error: {checks['error']}\n```"
        return embed

    for name, data in checks.items():
        if not isinstance(data, dict):
            continue
        ok = data.get("ok", True)
        lvl = data.get("level", "ok" if ok else "critical")
        bullet = {"ok": "✅", "warn": "⚠️", "critical": "❌"}.get(lvl, "ℹ️")
        parts = []
        for key in (
            "status", "latency_ms", "pct_used", "free_gb", "count", "error"):
            val = data.get(key)
            if val is not None:
                if key == "latency_ms":
                    parts.append(f"{val} ms")
                elif key == "pct_used":
                    parts.append(f"{val}% used")
                elif key == "free_gb":
                    parts.append(f"{val} GB free")
                elif key == "count":
                    parts.append(f"{val} events")
                else:
                    parts.append(str(val))
        value = " · ".join(parts) or (lvl.upper() if not ok else "OK")
        embed.add_field(
            name=f"{bullet}  {name.replace('_', ' ').title()} ", value=value,
            inline=True)

    return embed


def _task_status() -> dict:
    """
    Pull task stats from autonomous_scheduler or mission_runner.
    Returns a dict with pending / active / completed / efficiency.
    """
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        # Try to read backlog or state files for real numbers
        state_candidates = [
            REPO_ROOT / "state" / "tasks.json",
            REPO_ROOT / "state" / "flywheel" / "task_state.json",
            REPO_ROOT / "repo_depot" / "state.json",
        ]
        for p in state_candidates:
            if p.exists():
                data = json.loads(p.read_text())
                return data
    except Exception:
        pass
    # Fallback: run scheduler with --status flag
    try:
        sched = REPO_ROOT / "repo_depot" / "autonomous_scheduler.py"
        r = subprocess.run(
            [sys.executable, str(sched), "--status"],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(REPO_ROOT),
        )
        out = r.stdout.strip() or r.stderr.strip()
        return {"raw": out[:1600]} if out else {"raw": "No status output."}
    except Exception as exc:
        return {"error": str(exc)}


def _sla_report() -> dict:
    """Build an SLA compliance snapshot."""
    tasks = _task_status()
    # If we got structured data, compute compliance
    if "completed" in tasks and "pending" in tasks:
        total = tasks.get("completed", 0) + \
                          tasks.get("pending", 0) + tasks.get("active", 0)
        rate = round(tasks["completed"] / total * 100, 1) if total else 0.0
        return {
            "completion_rate": rate,
            "sla_target": SLA_TARGET,
            "compliant": rate >= SLA_TARGET,
            "pending": tasks.get("pending", 0),
            "active": tasks.get("active", 0),
            "completed": tasks.get("completed", 0),
            "total": total,
        }
    return {"raw": tasks.get("raw", tasks.get("error", "Unable to compute SLA."))}


def _missions_text() -> str:
    try:
        r = subprocess.run(
            [sys.executable, str(RUNTIME / "mission_runner.py"), "--status"],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(REPO_ROOT),
        )
        out = r.stdout.strip() or r.stderr.strip()
        return out[:1800] if out else "No mission output."
    except Exception as exc:
        return f"Error running mission_runner: {exc}"


def _run_scheduler_cycle() -> str:
    sched = REPO_ROOT / "repo_depot" / "autonomous_scheduler.py"
    if not sched.exists():
        return f"Scheduler not found at {sched}"
    try:
        r = subprocess.run(
            [sys.executable, str(sched), "--once"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
        out = (r.stdout + r.stderr).strip()
        return out[:1800] if out else "Cycle complete (no output)."
    except Exception as exc:
        return f"Scheduler error: {exc}"


def _daily_brief_text() -> str:
    try:
        r = subprocess.run(
            [sys.executable, str(
                RUNTIME / "mission_runner.py"), "--daily-brief"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
        out = (r.stdout + r.stderr).strip()
        return out[:1900] if out else "Daily brief complete (no output)."
    except Exception as exc:
        return f"Daily brief error: {exc}"


def _tail_event_log(n: int = 20) -> str:
    ncl_home = Path(os.environ.get("NCL_HOME", Path.home() / "NCL"))
    for p in [
        ncl_home / "events.ndjson",
        ncl_home / "logs" / "events.ndjson",
        REPO_ROOT / "runtime" / "events.ndjson",
    ]:
        if p.exists():
            try:
                lines = p.read_text().splitlines()[-n:]
                if lines:
                    return "\n".join(lines)
            except OSError:
                pass
    return "Event log not found or empty."


# ──────────────────────────────────────────────────────────────────────────────
# Lifecycle
# ──────────────────────────────────────────────────────────────────────────────


@bot.event
async def on_ready():
    log.info("OPTIMUS bot online as %s (ID %s)", bot.user, bot.user.id)
    ch = _find_channel(OPTIMUS_CH)
    if ch:
        embed = discord.Embed(
            title="⚡ OPTIMUS — Online",
            description=(
                "**Task Optimization Engine** initialized.\n"
                f"Mandate: 95% task completion within SLA\n"
                f"Priority escalation: GASKET → OPTIMUS → AZ → CEO\n\n"
                f"Repo: `{REPO_ROOT}`"
            ),
            color=COLOR_OPTIMUS,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="Commands",
            value="`!o status` `!o health` `!o tasks` `!o missions` `!o brief` `!o cycle` `!o sla` `!o logs` `!o help`",
            inline=False,
        )
        embed.set_footer(
            text=f"OPTIMUS v{VERSION} · App ID 1477878028716605661")
        await ch.send(embed=embed)
    else:
        log.warning("Could not find #%s channel", OPTIMUS_CH)

    sla_monitor_loop.start()
    daily_brief_loop.start()
    log.info("Background tasks started.")


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────


@bot.command(name="status", aliases=["s"])
async def cmd_status(ctx: commands.Context):
    """Quick task + health overview."""
    async with ctx.typing():
        checks = await asyncio.get_event_loop().run_in_executor(None, _run_watchdog)
        embed = _health_embed(checks, title="⚡ OPTIMUS — Status")
    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="health", aliases=["h"])
async def cmd_health(ctx: commands.Context):
    """Detailed health report + raw JSON."""
    async with ctx.typing():
        checks = await asyncio.get_event_loop().run_in_executor(None, _run_watchdog)
        embed = _health_embed(checks, title="⚡ OPTIMUS — Health Detail")
        raw = json.dumps(checks, indent=2, default=str)[:900]
    await ctx.reply(embed=embed, mention_author=False)
    await ctx.send(f"```json\n{raw}\n```")


@bot.command(name="tasks", aliases=["t"])
async def cmd_tasks(ctx: commands.Context):
    """Task queue breakdown — pending / active / completed."""
    async with ctx.typing():
        data = await asyncio.get_event_loop().run_in_executor(None, _task_status)

    embed = discord.Embed(
        title="📊 OPTIMUS — Task Queue",
        color=COLOR_OPTIMUS,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"OPTIMUS v{VERSION}")

    if "raw" in data:
        embed.description = f"```\n{data['raw']}\n```"
    elif "error" in data:
        embed.description = f"❌ `{data['error']}`"
        embed.color = COLOR_CRIT
    else:
        total = data.get("total", 1) or 1
        rate = round(data.get("completed", 0) / total * 100, 1)
        color = (
            COLOR_OK if rate >= SLA_TARGET else (
                COLOR_WARN if rate >= SLA_ALERT else COLOR_CRIT)
        )
        embed.color = color
        embed.add_field(name="✅ Completed", value=str(
            data.get("completed", "?")), inline=True)
        embed.add_field(name="🔄 Active", value=str(
            data.get("active", "?")), inline=True)
        embed.add_field(name="⏳ Pending", value=str(
            data.get("pending", "?")), inline=True)
        embed.add_field(name="📈 Completion Rate",
                        value=f"{rate}%", inline=True)
        embed.add_field(name="🎯 SLA Target",
                        value=f"{SLA_TARGET}%", inline=True)

    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="sla")
async def cmd_sla(ctx: commands.Context):
    """SLA compliance report."""
    async with ctx.typing():
        report = await asyncio.get_event_loop().run_in_executor(None, _sla_report)

    embed = discord.Embed(
        title="🎯 OPTIMUS — SLA Report",
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(
        text=f"OPTIMUS v{VERSION} · Target: {SLA_TARGET}% within SLA")

    if "raw" in report:
        embed.description = f"```\n{report['raw']}\n```"
        embed.color = COLOR_INFO
    else:
        rate = report.get("completion_rate", 0)
        compliant = report.get("compliant", False)
        embed.color = COLOR_OK if compliant else (
            COLOR_WARN if rate >= SLA_ALERT else COLOR_CRIT)
        status_icon = "✅" if compliant else (
            "⚠️" if rate >= SLA_ALERT else "🚨")
        embed.add_field(name=f"{status_icon} Completion Rate",
                        value=f"**{rate}%**", inline=True)
        embed.add_field(name="🎯 SLA Target",
                        value=f"{SLA_TARGET}%", inline=True)
        embed.add_field(
            name="📊 Status", value="COMPLIANT"
            if compliant else "BELOW TARGET", inline=True)
        embed.add_field(name="✅ Completed", value=str(
            report.get("completed", "?")), inline=True)
        embed.add_field(name="🔄 Active", value=str(
            report.get("active", "?")), inline=True)
        embed.add_field(name="⏳ Pending", value=str(
            report.get("pending", "?")), inline=True)

    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="missions", aliases=["m"])
async def cmd_missions(ctx: commands.Context):
    """Mission-runner status."""
    async with ctx.typing():
        output = await asyncio.get_event_loop().run_in_executor(None, _missions_text)
    embed = discord.Embed(
        title="📋 OPTIMUS — Mission Status",
        description=f"```\n{output}\n```",
        color=COLOR_INFO,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"OPTIMUS v{VERSION}")
    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="brief", aliases=["b"])
async def cmd_brief(ctx: commands.Context):
    """Generate and post today's daily brief."""
    async with ctx.typing():
        output = await asyncio.get_event_loop().run_in_executor(None, _daily_brief_text)
    embed = discord.Embed(
        title="📰 OPTIMUS — Daily Brief",
        description=f"```\n{output}\n```",
        color=COLOR_INFO,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"OPTIMUS v{VERSION}")
    await ctx.reply(embed=embed, mention_author=False)
    if ctx.channel.name.lower() != BRIEFS_CH.lower():
        briefs_ch = _find_channel(BRIEFS_CH)
        if briefs_ch:
            await briefs_ch.send(embed=embed)


@bot.command(name="cycle", aliases=["c"])
async def cmd_cycle(ctx: commands.Context):
    """Trigger one autonomous-scheduler cycle."""
    await ctx.send("🔄 OPTIMUS firing scheduler cycle…")
    async with ctx.typing():
        output = await asyncio.get_event_loop().run_in_executor(None, _run_scheduler_cycle)
    embed = discord.Embed(
        title="🔄 OPTIMUS — Scheduler Cycle",
        description=f"```\n{output}\n```",
        color=COLOR_OK,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"OPTIMUS v{VERSION}")
    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="logs", aliases=["l"])
async def cmd_logs(ctx: commands.Context, n: int = 20):
    """Last N event log lines (default 20)."""
    n = max(1, min(n, 100))
    async with ctx.typing():
        output = await asyncio.get_event_loop().run_in_executor(None, lambda: _tail_event_log(n))
    if len(output) > 1800:
        output = "…(truncated)\n" + output[-1800:]
    embed = discord.Embed(
        title=f"📜 OPTIMUS — Last {n} Event Log Lines",
        description=f"```\n{output}\n```",
        color=COLOR_INFO,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"OPTIMUS v{VERSION}")
    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="help", aliases=["?"])
async def cmd_help(ctx: commands.Context):
    """Command reference."""
    embed = discord.Embed(
        title="🛠 OPTIMUS — Command Reference",
        description="Prefix: `!optimus` or `!o`\nExample: `!o status`",
        color=COLOR_OPTIMUS,
        timestamp=datetime.now(timezone.utc),
    )
    for name, desc in [
        ("status / s", "Colour-coded health overview"),
        ("health / h", "Detailed health report + raw JSON"),
        ("tasks / t", "Task queue: pending / active / completed"),
        ("sla", "SLA compliance report vs 95% target"),
        ("missions / m", "Mission-runner status"),
        ("brief / b", "Generate + post daily brief"),
        ("cycle / c", "Trigger one autonomous-scheduler cycle"),
        ("logs [N] / l [N]", "Last N event log lines (default 20, max 100)"),
        ("help / ?", "This reference"),
    ]:
        embed.add_field(name=f"`{name}`", value=desc, inline=False)
    embed.set_footer(
        text=f"OPTIMUS v{VERSION} · Task Optimization Engine · 95% SLA")
    await ctx.reply(embed=embed, mention_author=False)


# ──────────────────────────────────────────────────────────────────────────────
# Background tasks
# ──────────────────────────────────────────────────────────────────────────────


@tasks.loop(minutes=10)
async def sla_monitor_loop():
    """Every 10 min: alert #optimus if SLA completion rate drops below 90%."""
    await bot.wait_until_ready()
    ch = _find_channel(OPTIMUS_CH)
    if not ch:
        return

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, _sla_report)

    if "completion_rate" in report:
        rate = report["completion_rate"]
        if rate < SLA_ALERT:
            level = "critical" if rate < 80 else "warn"
            color = COLOR_CRIT if level == "critical" else COLOR_WARN
            icon = "🚨" if level == "critical" else "⚠️"
            embed = discord.Embed(
                title=f"{icon} OPTIMUS — SLA ALERT",
                description=f"Completion rate **{rate}%** is below the {SLA_ALERT}% alert threshold (target: {SLA_TARGET}%).",
                color=color,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field( name="✅ Completed", value=str(
                report.get("completed", "?")), inline=True )
            embed.add_field(name="⏳ Pending", value=str(
                report.get("pending", "?")), inline=True)
            embed.set_footer(
                text=f"OPTIMUS v{VERSION} · Escalation: GASKET → OPTIMUS → AZ → CEO")
            await ch.send(embed=embed)
            log.warning("SLA alert posted: %.1f%%", rate)


@tasks.loop(hours=24)
async def daily_brief_loop():
    """06:00 UTC — post daily performance brief."""
    await bot.wait_until_ready()
    now = datetime.now(timezone.utc)
    next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now >= next_run:
        from datetime import timedelta

        next_run += timedelta(days=1)
    await asyncio.sleep((next_run - now).total_seconds())

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _daily_brief_text)
    embed = discord.Embed(
        title="📰 OPTIMUS — Daily Performance Brief",
        description=f"```\n{output[:1800]}\n```",
        color=COLOR_INFO,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"OPTIMUS v{VERSION} · Automated daily brief")

    for ch_name in [OPTIMUS_CH, BRIEFS_CH]:
        ch = _find_channel(ch_name)
        if ch:
            await ch.send(embed=embed)
            log.info("Daily brief posted to #%s", ch_name)


@daily_brief_loop.before_loop
async def before_daily_brief():
    await bot.wait_until_ready()


# ──────────────────────────────────────────────────────────────────────────────
# Error handler
# ──────────────────────────────────────────────────────────────────────────────


@bot.event
async def on_command_error(
    ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❓ Unknown command. Try `!o help` for the full list.", delete_after=10)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing argument: `{error.param.name}`. See `!o help`.")
    else:
        log.error("Command error in %s: %s", ctx.command, error)
        await ctx.send(f"❌ Error: `{error}`")


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────


def main():
    if not TOKEN:
        log.critical(
            "OPTIMUS_DISCORD_BOT_TOKEN is not set.\n"
            "  App ID (already registered): 1477878028716605661\n"
            "  1. Go to https://discord.com/developers/applications/1477878028716605661\n"
            "  2. Open Bot tab → Reset Token → copy it\n"
            "  3. Export OPTIMUS_DISCORD_BOT_TOKEN=<token>\n"
            "  4. Invite with: Send Messages, Embed Links, Read Message History, "
            "Use Application Commands")
        sys.exit(1)

    log.info("Starting OPTIMUS Discord bot (v%s)…", VERSION)
    log.info("Repo root : %s", REPO_ROOT)
    log.info("Channel   : #%s", OPTIMUS_CH)
    log.info("App ID    : 1477878028716605661")

    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
