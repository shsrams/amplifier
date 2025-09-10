"""
Multi-format export engine for presentations.

This module handles exporting presentations to various formats
(HTML, PDF, PNG, GIF) using appropriate tools.
"""

import logging
import shutil
import subprocess
from pathlib import Path

from .models import ExportRequest
from .models import ExportResult
from .utils import format_duration
from .utils import write_text

logger = logging.getLogger(__name__)


class PresentationExporter:
    """Export presentations to various formats."""

    def __init__(self):
        """Initialize exporter and check for required tools."""
        self.playwright_available = self._check_playwright()
        self.puppeteer_available = self._check_puppeteer()
        self.imagemagick_available = self._check_imagemagick()

        if not self.playwright_available and not self.puppeteer_available:
            logger.warning("Neither Playwright nor Puppeteer found. PDF and image exports will be limited.")

    def _check_playwright(self) -> bool:
        """Check if Playwright is available."""
        try:
            import importlib.util

            return importlib.util.find_spec("playwright") is not None
        except ImportError:
            return False

    def _check_puppeteer(self) -> bool:
        """Check if Puppeteer is available."""
        try:
            result = subprocess.run(["which", "puppeteer"], capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_imagemagick(self) -> bool:
        """Check if ImageMagick is available for GIF creation."""
        try:
            result = subprocess.run(["which", "convert"], capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def export(self, request: ExportRequest) -> ExportResult:
        """
        Export presentation to requested format.

        Args:
            request: Export request with format and options

        Returns:
            ExportResult with status and output path
        """
        import time

        start_time = time.time()

        try:
            # Ensure input file exists
            input_path = Path(request.presentation_file)
            if not input_path.exists():
                return ExportResult(
                    success=False,
                    output_path=None,
                    format=request.format,
                    error=f"Input file not found: {input_path}",
                    export_time=time.time() - start_time,
                )

            # Determine output path
            if request.output_path:
                output_path = Path(request.output_path)
            else:
                output_path = input_path.parent / f"{input_path.stem}.{request.format}"

            # Export based on format
            if request.format == "html":
                await self._export_html(input_path, output_path, request.options)
            elif request.format == "pdf":
                return ExportResult(
                    success=False,
                    output_path=None,
                    format=request.format,
                    error="PDF export has been removed. Use PNG or GIF formats instead.",
                    export_time=time.time() - start_time,
                )
            elif request.format == "png":
                await self._export_png(input_path, output_path, request.options)
            elif request.format == "gif":
                await self._export_gif(input_path, output_path, request.options)
            else:
                return ExportResult(
                    success=False,
                    output_path=None,
                    format=request.format,
                    error=f"Unsupported format: {request.format}",
                    export_time=time.time() - start_time,
                )

            return ExportResult(
                success=True,
                output_path=str(output_path),
                format=request.format,
                error=None,
                export_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                success=False,
                output_path=None,
                format=request.format,
                error=str(e),
                export_time=time.time() - start_time,
            )

    async def _export_html(self, input_path: Path, output_path: Path, options: dict) -> None:
        """Export as self-contained HTML."""
        # If input is already HTML, just copy it (unless it's the same file)
        if input_path.suffix == ".html":
            if input_path.resolve() != output_path.resolve():
                shutil.copy2(input_path, output_path)
            # If same file, no need to copy
        else:
            # Convert markdown to HTML
            from .generator import markdown_to_html

            markdown_content = input_path.read_text()
            theme = options.get("theme", "black")
            html_content = markdown_to_html(markdown_content, theme)

            write_text(html_content, output_path)

    # PDF export methods removed - use PNG or GIF formats instead

    async def _export_png(self, input_path: Path, output_path: Path, options: dict) -> None:
        """Export slides as PNG images."""
        if not self.playwright_available:
            raise RuntimeError("PNG export requires Playwright. Install with: pip install playwright")

        from playwright.async_api import async_playwright

        # Ensure we have HTML
        if input_path.suffix != ".html":
            html_path = input_path.parent / f"{input_path.stem}_temp.html"
            await self._export_html(input_path, html_path, options)
            input_path = html_path
            cleanup_temp = True
        else:
            cleanup_temp = False

        # Create output directory for images
        if output_path.is_dir():
            output_dir = output_path
        else:
            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})

            # Load the presentation
            await page.goto(f"file://{input_path.absolute()}")

            # Wait for page and scripts to load
            await page.wait_for_timeout(3000)

            # Force initialization if needed (simpler approach)
            await page.evaluate("""() => {
                // If Reveal is already ready, do nothing
                if (window.Reveal && window.Reveal.isReady()) {
                    return;
                }

                // If Reveal exists but not initialized, initialize it
                if (window.Reveal && !window.Reveal.isReady()) {
                    window.Reveal.initialize({
                        hash: true,
                        plugins: window.RevealMarkdown ? [window.RevealMarkdown] : []
                    });
                }
            }""")

            # Wait for markdown processing and initialization
            await page.wait_for_timeout(2000)

            # Ensure Reveal is initialized and get slide information
            slide_info = await page.evaluate("""() => {
                // Check if Reveal exists
                if (!window.Reveal) {
                    console.error('Reveal.js not loaded');
                    return { error: 'Reveal not loaded' };
                }

                // Use Reveal's API to get slide information
                // This works after markdown processing
                const totalSlides = window.Reveal.getTotalSlides ? window.Reveal.getTotalSlides() : 0;

                // Get all slides using Reveal's method
                const slides = window.Reveal.getSlides ? window.Reveal.getSlides() : [];

                // Build indices for each slide
                const slideIndices = [];

                if (slides.length > 0) {
                    // Use Reveal's internal structure
                    for (let i = 0; i < slides.length; i++) {
                        // For simple linear progression, we'll use index-based navigation
                        slideIndices.push({ index: i });
                    }
                } else {
                    // Fallback to manual detection
                    const horizontalSlides = document.querySelectorAll('.reveal .slides > section');

                    for (let h = 0; h < horizontalSlides.length; h++) {
                        const hSlide = horizontalSlides[h];
                        const verticalSlides = hSlide.querySelectorAll('section');

                        if (verticalSlides.length > 0) {
                            for (let v = 0; v < verticalSlides.length; v++) {
                                slideIndices.push({ h: h, v: v });
                            }
                        } else {
                            slideIndices.push({ h: h, v: 0 });
                        }
                    }
                }

                return {
                    total: totalSlides || slideIndices.length,
                    indices: slideIndices
                };
            }""")

            if "error" in slide_info:
                logger.error("Reveal.js not properly initialized")
                raise RuntimeError("Reveal.js initialization failed")

            slide_count = slide_info["total"]
            slide_indices = slide_info["indices"]
            logger.info(f"Found {slide_count} slides to capture")

            # Capture each slide
            for i, indices in enumerate(slide_indices):
                # Navigate to slide based on index type
                if "index" in indices:
                    # Use simple index-based navigation
                    slide_index = indices["index"]
                    try:
                        # First, go to first slide
                        if i == 0:
                            await page.evaluate(
                                "() => { if (window.Reveal) { try { window.Reveal.slide(0, 0); } catch(e) { console.log('Slide navigation error:', e); } } }"
                            )
                        else:
                            # Navigate to specific slide index
                            await page.evaluate(
                                f"() => {{ if (window.Reveal) {{ try {{ window.Reveal.slide({slide_index}, 0); }} catch(e) {{ console.log('Slide navigation error:', e); }} }} }}"
                            )
                    except Exception:
                        # Fallback: use next() to navigate
                        logger.debug(f"Using next() navigation for slide {i + 1}")
                        await page.evaluate("() => { if (window.Reveal) { window.Reveal.slide(0, 0); } }")
                        for _ in range(slide_index):
                            await page.evaluate(
                                "() => { if (window.Reveal && window.Reveal.next) { window.Reveal.next(); } }"
                            )
                else:
                    # Use h,v coordinates
                    h = indices.get("h", 0)
                    v = indices.get("v", 0)
                    try:
                        await page.evaluate(
                            f"() => {{ if (window.Reveal && window.Reveal.slide) {{ window.Reveal.slide({h}, {v}); }} }}"
                        )
                    except Exception:
                        logger.warning(f"Could not navigate to slide {i + 1}")

                await page.wait_for_timeout(500)

                # Take screenshot
                screenshot_path = output_dir / f"slide_{i + 1:03d}.png"
                await page.screenshot(path=str(screenshot_path))
                logger.info(f"Captured slide {i + 1}/{slide_count}")

                # Capture fragments if requested
                if options.get("include_fragments", False):
                    fragment_count = await page.evaluate("() => Reveal.getSlide().querySelectorAll('.fragment').length")
                    for f in range(fragment_count):
                        await page.keyboard.press("ArrowRight")
                        await page.wait_for_timeout(300)
                        fragment_path = output_dir / f"slide_{i + 1:03d}_fragment_{f + 1}.png"
                        await page.screenshot(path=str(fragment_path))

            await browser.close()

        # Cleanup temp file if created
        if cleanup_temp:
            input_path.unlink()

        logger.info(f"Exported {slide_count} slides to {output_dir}")

    async def _export_gif(self, input_path: Path, output_path: Path, options: dict) -> None:
        """Export slides as animated GIF."""
        if not self.imagemagick_available:
            raise RuntimeError("GIF export requires ImageMagick. Install with: apt-get install imagemagick")

        # First export as PNG images
        temp_dir = input_path.parent / f"{input_path.stem}_png_temp"
        temp_dir.mkdir(exist_ok=True)

        png_options = options.copy()
        png_options["include_fragments"] = options.get("include_fragments", True)

        await self._export_png(input_path, temp_dir, png_options)

        # Get all PNG files
        png_files = sorted(temp_dir.glob("*.png"))

        if not png_files:
            raise RuntimeError("No PNG files generated for GIF creation")

        # Create GIF using ImageMagick
        delay = options.get("delay", 200)  # Default 2 seconds per slide

        cmd = [
            "convert",
            "-delay",
            str(delay),
            "-loop",
            "0",  # Infinite loop
        ]

        # Add all PNG files
        cmd.extend(str(f) for f in png_files)

        # Add output file
        cmd.append(str(output_path))

        # Run ImageMagick
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"ImageMagick failed: {result.stderr}")

        # Cleanup temp files
        for png_file in png_files:
            png_file.unlink()
        temp_dir.rmdir()

        logger.info(f"Created animated GIF with {len(png_files)} frames")


class BatchExporter:
    """Export multiple formats in one operation."""

    def __init__(self, exporter: PresentationExporter):
        """Initialize batch exporter."""
        self.exporter = exporter

    async def export_all(self, input_file: Path, formats: list[str], output_dir: Path) -> dict[str, ExportResult]:
        """
        Export to multiple formats.

        Args:
            input_file: Input presentation file
            formats: List of formats to export
            output_dir: Directory for output files

        Returns:
            Dictionary mapping format to result
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results = {}

        for format_type in formats:
            output_path = output_dir / f"{input_file.stem}.{format_type}"

            # Type cast to satisfy type checker - formats are validated by CLI
            request = ExportRequest(
                presentation_file=str(input_file),
                format=format_type,  # type: ignore[arg-type]
                output_path=str(output_path),
            )

            result = await self.exporter.export(request)
            results[format_type] = result

            if result.success:
                logger.info(f"Exported {format_type} in {format_duration(result.export_time)}: {result.output_path}")
            else:
                logger.error(f"Failed to export {format_type}: {result.error}")

        return results
