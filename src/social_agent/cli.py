"""
Command-line interface for social-agent.
"""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from . import __version__

console = Console()


def run_async(coro):
    """Helper to run async code from sync CLI."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@click.group()
@click.version_option(version=__version__, prog_name="social-agent")
def main():
    """Social Agent - AI-powered social media operations framework."""
    pass


@main.command()
@click.option(
    "--provider", default=None, help="LLM provider (openai/claude/dashscope/zhipu/ollama)"
)
@click.option("--model", default=None, help="LLM model name")
def status(provider, model):
    """Show current agent status."""
    from .config import Settings
    from .agent import SocialAgent

    settings = Settings.load()
    if provider:
        settings.llm.provider = provider
    if model:
        settings.llm.model = model

    agent = SocialAgent(settings)
    run_async(agent.initialize())

    info = agent.get_status()

    console.print(
        Panel(
            f"[green]social-agent v{__version__}[/green]\n"
            f"LLM: {info['llm_provider']} / {info['llm_model']}\n"
            f"Platforms: {', '.join(info['platforms']) or 'None configured'}\n"
            f"Plugins: {len(info['loaded_plugins'])} loaded",
            title="Status",
        )
    )

    # Show loaded plugins
    if info["loaded_plugins"]:
        table = Table(title="Loaded Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Description")
        table.add_column("Status")

        for plugin in info["loaded_plugins"]:
            status = "[green]Loaded[/green]" if plugin["loaded"] else "[dim]Available[/dim]"
            table.add_row(
                plugin["name"],
                plugin["type"],
                plugin["description"][:50],
                status,
            )

        console.print(table)

    run_async(agent.shutdown())


@main.command()
@click.option("--platform", "-p", default=None, help="Platform name (default: all)")
@click.option("--limit", "-n", default=10, help="Number of trending topics")
def trending(platform, limit):
    """Fetch trending topics from platforms."""
    from .config import Settings
    from .agent import SocialAgent

    settings = Settings.load()
    agent = SocialAgent(settings)
    run_async(agent.initialize())

    topics = run_async(agent.get_trending(platform=platform, limit=limit))

    if not topics:
        console.print(
            "[yellow]No trending topics found. Make sure platform plugins are configured.[/yellow]"
        )
        run_async(agent.shutdown())
        return

    table = Table(title="Trending Topics")
    table.add_column("#", style="dim", width=4)
    table.add_column("Platform", style="cyan")
    table.add_column("Topic", style="white")
    table.add_column("Score", style="yellow", justify="right")

    for i, topic in enumerate(topics, 1):
        table.add_row(
            str(i),
            topic.platform,
            topic.title[:60],
            str(topic.hot_score),
        )

    console.print(table)
    run_async(agent.shutdown())


@main.command()
@click.option("--topic", "-t", required=True, help="Content topic")
@click.option("--platform", "-p", multiple=True, help="Target platform(s)")
@click.option("--style", "-s", default="professional", help="Content style")
@click.option("--keywords", "-k", multiple=True, help="Keywords to include")
def generate(topic, platform, style, keywords):
    """Generate content for social media platforms."""
    from .config import Settings
    from .agent import SocialAgent

    settings = Settings.load()
    agent = SocialAgent(settings)
    run_async(agent.initialize())

    platforms = list(platform) if platform else list(settings.platforms.keys())
    if not platforms:
        console.print("[red]No platforms specified. Use --platform or configure in .env[/red]")
        return

    with console.status("[bold green]Generating content..."):
        contents = run_async(
            agent.create_content(
                topic=topic,
                platforms=platforms,
                style=style,
                keywords=list(keywords),
            )
        )

    for content in contents:
        panel_content = (
            f"[cyan]Platform:[/cyan] {content.platform}\n"
            f"[cyan]Title:[/cyan] {content.title or '(none)'}\n"
            f"[cyan]Summary:[/cyan] {content.summary or '(none)'}\n\n"
            f"{content.text}\n"
        )
        if content.hashtags:
            panel_content += f"\n[cyan]Tags:[/cyan] {' '.join(f'#{t}' for t in content.hashtags)}"

        console.print(
            Panel(panel_content, title=f"Content for {content.platform}", border_style="green")
        )

    run_async(agent.shutdown())


@main.command()
@click.option("--keyword", "-k", required=True, help="Search keyword")
@click.option("--platform", "-p", default=None, help="Platform name")
@click.option("--limit", "-n", default=10, help="Max results")
def search(keyword, platform, limit):
    """Search for content across platforms."""
    from .config import Settings
    from .agent import SocialAgent

    settings = Settings.load()
    agent = SocialAgent(settings)
    run_async(agent.initialize())

    results = run_async(agent.search(keyword=keyword, platform=platform, limit=limit))

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        run_async(agent.shutdown())
        return

    table = Table(title=f"Search: {keyword}")
    table.add_column("Platform", style="cyan")
    table.add_column("Title")
    table.add_column("Author", style="dim")
    table.add_column("Stats", style="yellow", justify="right")

    for item in results:
        table.add_row(
            item.get("_platform", "?"),
            str(item.get("title", item.get("text", "")))[:50],
            str(item.get("author", item.get("user", "")))[:20],
            str(item.get("stats", item.get("likes", ""))),
        )

    console.print(table)
    run_async(agent.shutdown())


@main.command()
@click.option("--topic", "-t", required=True, help="Content topic")
@click.option("--platform", "-p", multiple=True, help="Target platform(s)")
@click.option("--dry-run", is_flag=True, help="Generate only, don't publish")
def publish(topic, platform, dry_run):
    """Generate and publish content to platforms."""
    from .config import Settings
    from .agent import SocialAgent

    settings = Settings.load()
    agent = SocialAgent(settings)
    run_async(agent.initialize())

    platforms = list(platform) if platform else list(settings.platforms.keys())
    if not platforms:
        console.print("[red]No platforms specified.[/red]")
        return

    if dry_run:
        with console.status("[bold green]Generating content (dry run)..."):
            contents = run_async(agent.create_content(topic=topic, platforms=platforms))
        for c in contents:
            console.print(
                Panel(
                    f"[cyan]{c.platform}[/cyan]\n{c.text}", title="Preview", border_style="yellow"
                )
            )
    else:
        with console.status("[bold green]Generating and publishing..."):
            results = run_async(agent.create_and_publish(topic=topic, platforms=platforms))

        for r in results:
            if r.success:
                console.print(f"  [green]OK[/green] {r.platform}: {r.url or r.post_id}")
            else:
                console.print(f"  [red]FAIL[/red] {r.platform}: {r.error}")

    run_async(agent.shutdown())


@main.command()
def plugins():
    """List available and loaded plugins."""
    from .config import Settings
    from .agent import SocialAgent

    settings = Settings.load()
    agent = SocialAgent(settings)
    run_async(agent.initialize())

    plugin_list = agent.plugin_manager.list_plugins()

    if not plugin_list:
        console.print("[yellow]No plugins found. Install platform plugins to get started.[/yellow]")
        console.print("\nAvailable plugin packages:")
        console.print("  pip install social-agent[weibo]      # Weibo support")
        console.print("  pip install social-agent[xiaohongshu] # Xiaohongshu support")
        console.print("  pip install social-agent[douyin]     # Douyin support")
        console.print("  pip install social-agent[bilibili]   # Bilibili support")
        console.print("  pip install social-agent[all]        # All platforms")
    else:
        table = Table(title="Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Description")
        table.add_column("Status")

        for p in plugin_list:
            status = "[green]Loaded[/green]" if p["loaded"] else "[dim]Available[/dim]"
            table.add_row(p["name"], p["type"], p["description"][:50], status)

        console.print(table)

    run_async(agent.shutdown())


if __name__ == "__main__":
    main()
