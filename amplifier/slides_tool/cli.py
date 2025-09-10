"""
Click CLI interface for the slides tool.

This module provides the command-line interface for generating,
revising, and exporting presentations.
"""

import asyncio
import logging
import sys
from pathlib import Path

import click

from .exporter import BatchExporter
from .exporter import PresentationExporter
from .generator import SlideGenerator
from .generator import markdown_to_html
from .models import ExportRequest
from .models import GenerationRequest
from .state_manager import QuickSave
from .state_manager import StateManager
from .utils import ensure_output_dir
from .utils import format_duration

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """Amplifier Slides Tool - Generate presentations from natural language."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    ctx.ensure_object(dict)


@cli.command()
@click.option("--prompt", "-p", required=True, help="Generation prompt")
@click.option("--context", "-c", help="Additional context (inline)")
@click.option("--context-file", "-f", type=click.Path(exists=True), help="Context from file")
@click.option("--num-slides", "-n", type=int, help="Number of slides to generate")
@click.option(
    "--style",
    "-s",
    type=click.Choice(["professional", "academic", "creative", "minimal"]),
    default="professional",
    help="Presentation style",
)
@click.option("--output-dir", "-o", type=click.Path(), default="slides_output", help="Output directory")
@click.option(
    "--theme",
    "-t",
    type=click.Choice(["black", "white", "league", "beige", "sky", "night", "serif", "simple", "solarized"]),
    default="black",
    help="Reveal.js theme",
)
@click.option("--include-images", is_flag=True, help="Include image placeholders")
@click.option(
    "--export",
    "-e",
    multiple=True,
    type=click.Choice(["html", "png", "gif"]),
    default=(),
    help="Export formats (default: html)",
)
@click.pass_context
def generate(ctx, prompt, context, context_file, num_slides, style, output_dir, theme, include_images, export):
    """Generate a new presentation from a prompt."""
    import time

    start_time = time.time()

    # Create output directory
    output_path = ensure_output_dir(Path(output_dir))

    # Set up state manager
    state_manager = StateManager(output_path)

    # Create generation request
    request = GenerationRequest(
        prompt=prompt,
        context=context,
        context_file=context_file,
        num_slides=num_slides,
        style=style,
        include_images=include_images,
    )

    click.echo(f"🎯 Generating presentation: {prompt[:50]}...")

    # Default to HTML if no formats specified
    if not export:
        export = ("html",)

    async def _generate():
        generator = SlideGenerator()

        # Use quick save for crash recovery
        with QuickSave(state_manager, "generation") as saver:
            saver.update(prompt=prompt, status="starting")

            try:
                # Generate presentation
                presentation, markdown = await generator.generate(request)
                presentation.theme = theme

                saver.update(status="generated", slide_count=len(presentation.slides))

                # Generate HTML
                html = markdown_to_html(markdown, theme)

                # Save everything
                save_path = state_manager.save_presentation(presentation, markdown, html)

                saver.update(status="saved", path=str(save_path))

                # Export to requested formats
                if export:
                    click.echo(f"📦 Exporting to {', '.join(export)}...")
                    try:
                        exporter = PresentationExporter()
                        batch_exporter = BatchExporter(exporter)

                        html_file = save_path / "presentation.html"

                        # Convert tuple to list manually to avoid the strange Click/list() bug
                        export_list = []
                        for fmt in export:
                            export_list.append(fmt)

                        # Now call export_all with our manually created list
                        await batch_exporter.export_all(html_file, export_list, save_path)
                    except Exception as export_error:
                        click.echo(f"❌ Export error: {export_error}", err=True)
                        import traceback

                        traceback.print_exc()
                        raise

                    saver.update(status="exported", formats=list(export))

                return save_path, presentation

            except TimeoutError:
                click.echo("⏱️  Generation timed out. Try a simpler prompt.", err=True)
                saver.update(status="timeout")
                sys.exit(1)
            except Exception as e:
                click.echo(f"❌ Generation failed: {e}", err=True)
                saver.update(status="error", error=str(e))
                sys.exit(1)

    # Run async generation
    save_path, presentation = asyncio.run(_generate())

    duration = time.time() - start_time

    # Report results
    click.echo(f"✅ Generated {len(presentation.slides)} slides in {format_duration(duration)}")
    click.echo(f"📁 Saved to: {save_path}")

    # Show file paths
    click.echo("\nGenerated files:")
    click.echo(f"  📝 Markdown: {save_path}/presentation.md")
    click.echo(f"  🌐 HTML: {save_path}/presentation.html")

    for format_type in export:
        if format_type != "html":
            click.echo(f"  📦 {format_type.upper()}: {save_path}/presentation.{format_type}")


@cli.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Presentation file to revise")
@click.option("--feedback", "-b", required=True, help="Revision feedback")
@click.option("--preserve-structure", is_flag=True, default=True, help="Keep the same slide structure")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory (defaults to same as input)")
@click.option(
    "--export",
    "-e",
    multiple=True,
    type=click.Choice(["html", "png", "gif"]),
    default=(),
    help="Export formats (default: html)",
)
@click.pass_context
def revise(ctx, file, feedback, preserve_structure, output_dir, export):
    """Revise an existing presentation based on feedback."""
    import time

    start_time = time.time()

    input_path = Path(file)

    # Determine output directory
    if output_dir:
        output_path = ensure_output_dir(Path(output_dir))
    else:
        output_path = input_path.parent

    # Set up state manager
    state_manager = StateManager(output_path)

    click.echo(f"🔄 Revising presentation: {input_path.name}")
    click.echo(f"💭 Feedback: {feedback[:100]}...")

    async def _revise():
        generator = SlideGenerator()

        with QuickSave(state_manager, "revision") as saver:
            saver.update(input_file=str(input_path), feedback=feedback)

            try:
                # Load current presentation
                if input_path.suffix == ".md":
                    current_markdown = input_path.read_text()
                elif input_path.suffix == ".html":
                    # Extract markdown from HTML if possible
                    click.echo("⚠️  HTML input - attempting to extract content", err=True)
                    current_markdown = input_path.read_text()
                else:
                    click.echo(f"❌ Unsupported file type: {input_path.suffix}", err=True)
                    sys.exit(1)

                saver.update(status="loaded")

                # Revise presentation
                presentation, markdown = await generator.revise(current_markdown, feedback, preserve_structure)

                saver.update(status="revised", version=presentation.version)

                # Generate HTML
                html = markdown_to_html(markdown, presentation.theme)

                # Save everything
                save_path = state_manager.save_presentation(presentation, markdown, html)

                saver.update(status="saved", path=str(save_path))

                # Export to requested formats
                if export:
                    click.echo(f"📦 Exporting to {', '.join(export)}...")
                    exporter = PresentationExporter()
                    batch_exporter = BatchExporter(exporter)

                    html_file = save_path / "presentation.html"

                    # Convert tuple to list manually to avoid the strange Click/list() bug
                    export_list = []
                    for fmt in export:
                        export_list.append(fmt)

                    await batch_exporter.export_all(html_file, export_list, save_path)

                    saver.update(status="exported")

                return save_path, presentation

            except Exception as e:
                click.echo(f"❌ Revision failed: {e}", err=True)
                saver.update(status="error", error=str(e))
                sys.exit(1)

    # Run async revision
    save_path, presentation = asyncio.run(_revise())

    duration = time.time() - start_time

    # Report results
    click.echo(f"✅ Revised to version {presentation.version} in {format_duration(duration)}")
    click.echo(f"📁 Saved to: {save_path}")


@cli.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Presentation file to export")
@click.option("--format", "-t", required=True, type=click.Choice(["html", "png", "gif"]), help="Export format")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--include-fragments", is_flag=True, help="Include fragment animations (for PNG/GIF)")
@click.option("--delay", "-d", type=int, default=200, help="Frame delay for GIF (in 1/100 seconds)")
@click.pass_context
def export(ctx, file, format, output, include_fragments, delay):
    """Export a presentation to various formats."""
    input_path = Path(file)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = input_path.parent / f"{input_path.stem}.{format}"

    click.echo(f"📦 Exporting to {format.upper()}: {input_path.name}")

    async def _export():
        exporter = PresentationExporter()

        request = ExportRequest(
            presentation_file=str(input_path),
            format=format,
            output_path=str(output_path),
            options={"include_fragments": include_fragments, "delay": delay},
        )

        result = await exporter.export(request)

        if not result.success:
            click.echo(f"❌ Export failed: {result.error}", err=True)
            sys.exit(1)

        return result

    # Run async export
    result = asyncio.run(_export())

    # Report results
    click.echo(f"✅ Exported in {format_duration(result.export_time)}")
    click.echo(f"📄 Output: {result.output_path}")


@cli.command()
@click.option("--dir", "-d", type=click.Path(exists=True), default="slides_output", help="Presentations directory")
@click.pass_context
def list(ctx, dir):
    """List all saved presentations and versions."""
    presentations_dir = Path(dir)

    if not presentations_dir.exists():
        click.echo("No presentations found.")
        return

    # List all presentation directories
    presentation_dirs = [d for d in presentations_dir.iterdir() if d.is_dir()]

    if not presentation_dirs:
        click.echo("No presentations found.")
        return

    click.echo("📚 Saved Presentations:\n")

    for pres_dir in sorted(presentation_dirs, key=lambda d: d.stat().st_mtime, reverse=True):
        state_manager = StateManager(pres_dir)

        # Check for current presentation
        current_file = pres_dir / "current" / "presentation.json"
        if current_file.exists():
            try:
                presentation, _, _ = state_manager.load_presentation()
                click.echo(f"📁 {pres_dir.name}")
                click.echo(f"   Title: {presentation.title}")
                click.echo(f"   Slides: {len(presentation.slides)}")
                click.echo(f"   Version: {presentation.version}")
                click.echo(f"   Theme: {presentation.theme}")

                # List versions
                versions = state_manager.list_versions()
                if versions:
                    click.echo(f"   Versions: {len(versions)}")

                click.echo()
            except Exception as e:
                click.echo(f"📁 {pres_dir.name} (error reading: {e})")


@cli.command()
@click.pass_context
def check(ctx):
    """Check if all required dependencies are installed."""
    click.echo("🔍 Checking dependencies...\n")

    # Check Claude CLI
    generator = SlideGenerator()
    if generator.sdk_available:
        click.echo("✅ Claude CLI: Installed")
    else:
        click.echo("❌ Claude CLI: Not found (install with: npm install -g @anthropic-ai/claude-code)")

    # Check export tools
    exporter = PresentationExporter()

    if exporter.playwright_available:
        click.echo("✅ Playwright: Installed")
    else:
        click.echo("⚠️  Playwright: Not found (install with: pip install playwright)")

    if exporter.puppeteer_available:
        click.echo("✅ Puppeteer: Installed")
    else:
        click.echo("⚠️  Puppeteer: Not found (optional)")

    if exporter.imagemagick_available:
        click.echo("✅ ImageMagick: Installed")
    else:
        click.echo("⚠️  ImageMagick: Not found (needed for GIF export)")

    click.echo("\n📝 Note: The tool works with fallback options even if some dependencies are missing.")


# Review and improvement commands
@cli.group()
@click.pass_context
def review(ctx):
    """Review and improve presentations using AI analysis."""
    pass


@review.command(name="analyze")
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Presentation file to analyze")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["visual", "content", "comprehensive"]),
    default="comprehensive",
    help="Type of review to perform",
)
@click.option("--strict", is_flag=True, help="Use strict evaluation criteria")
@click.option("--output", "-o", type=click.Path(), help="Save review results to JSON file")
@click.pass_context
def review_analyze(ctx, file, type, strict, output):
    """Analyze a presentation and identify issues."""
    from pathlib import Path

    from .review import ReviewRequest
    from .review import SlideReviewAnalyzer

    presentation_path = Path(file)
    click.echo(f"🔍 Analyzing presentation: {presentation_path.name}")
    click.echo(f"   Review type: {type}")

    async def _analyze():
        analyzer = SlideReviewAnalyzer()

        request = ReviewRequest(
            presentation_file=str(presentation_path),
            review_type=type,
            focus_areas=None,
            strict_mode=strict,
        )

        result = await analyzer.analyze(request)
        return result

    # Run analysis
    result = asyncio.run(_analyze())

    # Display results
    click.echo(f"\n📊 Overall Score: {result.overall_score:.1f}/10")

    if result.strengths:
        click.echo("\n✅ Strengths:")
        for strength in result.strengths:
            click.echo(f"   • {strength}")

    if result.issues:
        click.echo(f"\n⚠️  Issues Found ({len(result.issues)}):")
        for issue in result.issues:
            severity_icon = "🔴" if issue.severity == "critical" else "🟡" if issue.severity == "major" else "🟢"
            click.echo(f"   {severity_icon} Slide {issue.slide_index + 1}: {issue.description}")
            if issue.suggestion:
                click.echo(f"      💡 {issue.suggestion}")

    if result.general_feedback:
        click.echo(f"\n💬 General Feedback: {result.general_feedback}")

    click.echo(f"\n🎯 Needs Revision: {'Yes' if result.needs_revision else 'No'}")

    # Save to file if requested
    if output:
        import json

        output_path = Path(output)
        with open(output_path, "w") as f:
            json.dump(
                {
                    "overall_score": result.overall_score,
                    "needs_revision": result.needs_revision,
                    "strengths": result.strengths,
                    "issues": [
                        {
                            "slide_index": issue.slide_index,
                            "type": issue.issue_type,
                            "severity": issue.severity,
                            "description": issue.description,
                            "suggestion": issue.suggestion,
                        }
                        for issue in result.issues
                    ],
                    "general_feedback": result.general_feedback,
                },
                f,
                indent=2,
            )
        click.echo(f"\n💾 Review saved to: {output_path}")


@review.command(name="auto-improve")
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Presentation file to improve")
@click.option("--max-iterations", "-i", type=int, default=3, help="Maximum improvement iterations")
@click.option("--target-score", "-s", type=float, default=8.0, help="Target quality score (0-10)")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory for iterations")
@click.option(
    "--export",
    "-e",
    multiple=True,
    type=click.Choice(["html", "png", "gif"]),
    default=["html", "png"],
    help="Export formats for each iteration",
)
@click.pass_context
def review_auto_improve(ctx, file, max_iterations, target_score, output_dir, export):
    """Automatically improve a presentation through iterative review and revision."""
    import time
    from pathlib import Path

    from .exporter import PresentationExporter
    from .generator import SlideGenerator
    from .review import AutoImproveRequest
    from .review import RevisionOrchestrator
    from .review import SlideReviewAnalyzer

    start_time = time.time()
    presentation_path = Path(file)

    click.echo(f"🚀 Auto-improving presentation: {presentation_path.name}")
    click.echo(f"   Max iterations: {max_iterations}")
    click.echo(f"   Target score: {target_score}/10")

    async def _improve():
        generator = SlideGenerator()
        exporter = PresentationExporter()
        analyzer = SlideReviewAnalyzer()

        orchestrator = RevisionOrchestrator(generator, exporter, analyzer)

        request = AutoImproveRequest(
            presentation_file=str(presentation_path),
            max_iterations=max_iterations,
            target_score=target_score,
            review_type="comprehensive",
            output_dir=output_dir,
            export_formats=list(export),
        )

        result = await orchestrator.auto_improve(request)
        return result

    # Run improvement
    result = asyncio.run(_improve())

    # Display results
    click.echo(f"\n{'✅' if result.success else '❌'} Auto-improvement {'completed' if result.success else 'failed'}")

    if result.iterations:
        click.echo("\n📈 Improvement Progress:")
        for iteration in result.iterations:
            score_change = f"+{iteration.improvement_delta:.1f}" if iteration.improvement_delta else ""
            click.echo(
                f"   Iteration {iteration.iteration}: Score {iteration.review_result.overall_score:.1f} {score_change}"
            )
            if iteration.revision_applied:
                click.echo(f"      ✏️  Revision applied ({len(iteration.review_result.issues)} issues addressed)")

    if result.final_score:
        click.echo(f"\n🏆 Final Score: {result.final_score:.1f}/10")

    if result.stopped_reason:
        reasons = {
            "target_reached": "✅ Target score reached!",
            "max_iterations": "🔄 Maximum iterations reached",
            "no_improvement": "📊 No further improvement possible",
            "error": f"❌ Error: {result.error}",
        }
        click.echo(f"\n{reasons.get(result.stopped_reason, result.stopped_reason)}")

    if result.final_presentation_file:
        click.echo(f"\n📁 Final presentation: {result.final_presentation_file}")

    duration = time.time() - start_time
    click.echo(f"\n⏱️  Total time: {format_duration(duration)}")


# Full pipeline command (top-level, not in review group)
@cli.command(name="full-pipeline")
@click.option("--prompt", "-p", required=True, help="Generation prompt")
@click.option("--context", "-c", help="Additional context")
@click.option("--max-iterations", "-i", type=int, default=3, help="Maximum improvement iterations")
@click.option("--target-score", "-s", type=float, default=8.0, help="Target quality score")
@click.option("--output-dir", "-o", type=click.Path(), default="slides_output", help="Output directory")
@click.option(
    "--theme",
    "-t",
    type=click.Choice(["black", "white", "league", "beige", "sky", "night", "serif", "simple", "solarized"]),
    default="black",
    help="Reveal.js theme",
)
@click.pass_context
def full_pipeline(ctx, prompt, context, max_iterations, target_score, output_dir, theme):
    """Generate and auto-improve a presentation in one command."""
    import time
    from pathlib import Path

    from .exporter import PresentationExporter
    from .generator import SlideGenerator
    from .generator import markdown_to_html
    from .models import GenerationRequest
    from .review import AutoImproveRequest
    from .review import RevisionOrchestrator
    from .review import SlideReviewAnalyzer
    from .state_manager import StateManager
    from .utils import ensure_output_dir

    start_time = time.time()
    output_path = ensure_output_dir(Path(output_dir))

    click.echo("🎯 Full Pipeline: Generate & Auto-Improve")
    click.echo(f"   Prompt: {prompt[:50]}...")

    async def _full_pipeline():
        # Phase 1: Generate
        click.echo("\n📝 Phase 1: Generating initial presentation...")
        generator = SlideGenerator()

        gen_request = GenerationRequest(
            prompt=prompt,
            context=context,
            context_file=None,
            num_slides=None,
            style="professional",
            include_images=False,
        )

        presentation, markdown = await generator.generate(gen_request)
        presentation.theme = theme

        # Save initial version
        state_manager = StateManager(output_path)
        html = markdown_to_html(markdown, theme)
        save_path = state_manager.save_presentation(presentation, markdown, html)

        # Export initial version to PNG for review
        click.echo("📦 Exporting to PNG for review...")
        exporter = PresentationExporter()
        from .exporter import BatchExporter

        batch_exporter = BatchExporter(exporter)
        html_file = save_path / "presentation.html"
        await batch_exporter.export_all(html_file, ["png"], save_path)

        png_file = save_path / "presentation.png"

        click.echo("✅ Initial generation complete (Score: TBD)")

        # Phase 2: Auto-improve
        click.echo(f"\n🔄 Phase 2: Auto-improving (up to {max_iterations} iterations)...")
        analyzer = SlideReviewAnalyzer()
        orchestrator = RevisionOrchestrator(generator, exporter, analyzer)

        improve_request = AutoImproveRequest(
            presentation_file=str(png_file),
            max_iterations=max_iterations,
            target_score=target_score,
            review_type="comprehensive",
            output_dir=str(save_path),
            export_formats=["html", "png"],
        )

        result = await orchestrator.auto_improve(improve_request)

        return save_path, result

    # Run full pipeline
    save_path, result = asyncio.run(_full_pipeline())

    # Display final results
    click.echo("\n" + "=" * 50)
    click.echo("📊 FINAL RESULTS")
    click.echo("=" * 50)

    if result.final_score:
        click.echo(f"🏆 Final Score: {result.final_score:.1f}/10")

    if result.iterations:
        improvements = [it for it in result.iterations if it.revision_applied]
        click.echo(f"✏️  Revisions Applied: {len(improvements)}")

    click.echo(f"📁 Output Directory: {save_path}")

    duration = time.time() - start_time
    click.echo(f"⏱️  Total Time: {format_duration(duration)}")

    click.echo("\n✅ Full pipeline complete!")


if __name__ == "__main__":
    cli()
