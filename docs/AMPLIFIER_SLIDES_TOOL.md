# AMPLIFIER SLIDES TOOL

A **hybrid AI + code tool** that generates professional presentations AND uses AI to analyze and improve its own visual output!

---

## **SYSTEM CAPABILITIES:**

### **High-Quality Generation:**

- **Claude SDK integration** - Creates professional, technical content
- **Reveal.js styling** - Professional dark theme with large typography
- **Real statistics** - Industry data (73% delays, 45% budget overruns, etc.)
- **Architecture diagrams** - Mermaid charts and ASCII flow diagrams
- **Professional layouts** - Proper spacing, navigation, branding

### **AI Review System:**

- **Real image analysis** - Claude Read tool analyzes actual PNG exports
- **Truncation detection** - Identifies content cut off at slide edges
- **Specific feedback** - Actionable suggestions for improvement
- **Visual validation** - Reviews what users actually see, not HTML source

### **Multiple Export Formats:**

- **PNG frames** - High-resolution images for video editing
- **Animated GIFs** - Complete presentations for documentation
- **Self-contained HTML** - Shareable reveal.js presentations

---

## **USE CASES:**

### **Demo Video Production**

- **High-resolution PNG frames** ready for 1080p video editing
- **Professional quality** representing technical expertise
- **AI-validated quality** with truncation detection
- **Content-rich presentations** with real industry data

### **Documentation Enhancement**

- **Animated GIFs** for README embedding
- **Professional technical illustrations**
- **AI-optimized layouts** ensuring content visibility
- **Multiple slide formats** for different documentation needs

---

## **FEATURES:**

1. **Generates professional slides** from natural language
2. **Exports to multiple formats** for video and documentation
3. **Uses AI to review its own visual output**
4. **Detects content truncation automatically**
5. **Generates specific improvement feedback**
6. **Creates iterative improvement loops**

**The tool demonstrates true AI-powered quality control with a complete feedback loop:**

- AI generates content → Visual export → AI analyzes results → Improvement suggestions → Iteration

The system validates its own output quality through actual visual inspection, not just code review.

---

## **READY FOR EXPERIMENTAL USE:**

**Commands that work:**

```bash
# Generate professional presentations
make slides-generate PROMPT="detailed requirements" OUTPUT_DIR="output"

# Export for video production
uv run python -m amplifier.slides_tool.cli export --file presentation.html --format png

# Export for documentation
uv run python -m amplifier.slides_tool.cli export --file presentation.html --format gif

# AI review and improvement (using Claude Read tool)
uv run python -m amplifier.slides_tool.cli review analyze --presentation presentation.html
```
