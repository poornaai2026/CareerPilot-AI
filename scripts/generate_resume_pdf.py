"""
Generates a PDF of Poorna Chandra Rao J's resume using reportlab.
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_pdf():
    out_dir = Path("resumes")
    out_dir.mkdir(exist_ok=True)
    pdf_path = out_dir / "Poorna_Chandra_Rao_Resume.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f2444'),
        fontName='Helvetica-Bold',
        alignment=1,
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0056b3'),
        fontName='Helvetica-Bold',
        alignment=1,
        spaceAfter=3
    )

    contact_style = ParagraphStyle(
        'Contact',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#333333'),
        fontName='Helvetica',
        alignment=1,
        spaceAfter=8
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0f2444'),
        fontName='Helvetica-Bold',
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#222222'),
        fontName='Helvetica',
        spaceAfter=3
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#222222'),
        fontName='Helvetica',
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    story = []

    # Header
    story.append(Paragraph("POORNA CHANDRA RAO J", title_style))
    story.append(Paragraph("Senior Quality & Gen AI Quality Engineer | Agentic AI & Test Automation", subtitle_style))
    story.append(Paragraph(
        "Hyderabad, India • +91-8143675811 • poorna.ai.2026@gmail.com • Portfolio: qe-2-ai.vercel.app • GitHub: github.com/poornaai2026/QE2AI",
        contact_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0f2444'), spaceAfter=6))

    # Summary
    story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
    summary_text = (
        "<b>Senior Quality Engineer & QA Lead with 12+ years of enterprise IT experience</b>, combining 10+ years in core automation architecture "
        "(Java, Selenium, Appium, REST Assured) with 2+ years pioneering AI Quality Engineering and GenAI application testing. Proven track record "
        "architecting agentic workflows and automated evaluation pipelines using <b>Python, FastAPI, LangGraph, RAG architectures, and Ragas</b>. "
        "Creator of the open-source <b>QE2AI platform</b> and 10 production AI mini-projects. Adept at establishing quantitative LLM quality gates, "
        "building intelligent test generation systems, and modernizing CI/CD pipelines to ensure reliability across enterprise-scale systems."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 4))

    # Skills
    story.append(Paragraph("CORE COMPETENCIES & TECHNICAL SKILLS", section_heading))
    skills = [
        "<b>GenAI & Agentic AI:</b> LangGraph, LangChain, MCP (Model Context Protocol), FastMCP, AI Agents, Agentic AI, RAG Systems, LLM Applications, Prompt Engineering, LLM Evaluation, Ragas, Guardrails, Vector Search, Vector Databases, asyncio",
        "<b>GenAI Engineering:</b> Python 3.11, FastAPI, Pydantic V2, RAG Pipelines, LLM Integration, Test Case Generation, AI Quality Gates, AI Validation, Embeddings, Retrieval Pipelines, Redis Semantic Cache, LangSmith",
        "<b>Test Automation:</b> Playwright, Selenium WebDriver, Appium, Karate, REST Assured, TestNG, Cucumber (BDD), pytest, pytest-bdd, Postman, Newman, Self-Healing Locators",
        "<b>Cloud, DevOps & CI/CD:</b> Docker, Kubernetes (K8s), GCP, GitHub Actions, Jenkins, Bitbucket Pipelines, CI/CD Optimization, Linux/Bash",
        "<b>Languages & Web:</b> Python, FastAPI, Core Java, JavaScript, HTML5, CSS, JSON, REST, SCAPI, OCAPI Architecture",
        "<b>Databases & Tools:</b> MySQL, MongoDB, PostgreSQL, ChromaDB, FAISS, Pinecone Vector DB, Redis, JIRA, Confluence, BrowserStack"
    ]
    for sk in skills:
        story.append(Paragraph(f"• {sk}", bullet_style))
    story.append(Spacer(1, 4))

    # Open Source
    story.append(Paragraph("FEATURED OPEN-SOURCE PLATFORM: QE2AI (qe-2-ai.vercel.app)", section_heading))
    os_bullets = [
        "<b>Automated LLM Evaluation Gate (Project 07):</b> Built CI/CD quality gate with Ragas & DeepEval scoring Faithfulness (>=0.88) & Context Precision (>=0.85).",
        "<b>Model Context Protocol (MCP) Server (Project 06):</b> Developed FastMCP server exposing test runner tools and CI/CD logs directly to LLMs.",
        "<b>Stateful LangGraph AI Test Agent (Project 05):</b> Autonomous requirement-to-test generation agent with automated retry & self-healing.",
        "<b>FastAPI Microservices & Semantic Caching:</b> Async endpoints with Pydantic V2 and Redis semantic caching (90% latency reduction)."
    ]
    for b in os_bullets:
        story.append(Paragraph(f"• {b}", bullet_style))
    story.append(Spacer(1, 4))

    # Experience
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_heading))
    story.append(Paragraph("<b>Publicis Sapient</b> | Sr. Quality Engineer L2 / QA Lead <i>(Hyderabad, India | Feb 2023 – Present)</i>", body_style))
    story.append(Paragraph("<b>PrecisionRX – Client: UHG / Optum</b> | <i>GenAI QE Engineer</i>", body_style))
    exp_bullets = [
        "Defined end-to-end QE strategy & automation architecture, leading framework modernization from AccelQ to a Python-based Playwright solution.",
        "Designed and developed a Python-based RAG application retrieving requirements from Jira/Confluence to generate traceable, AI-powered test cases.",
        "Engineered FastAPI backend services to orchestrate RAG workflows, LLM interactions, and automated test-case generation.",
        "Implemented AI validation quality gates for hallucination detection, requirement coverage, and generated test-case correctness prior to execution.",
        "Integrated Ragas-based LLM evaluation to benchmark AI-generated test assets for faithfulness, answer relevance, and context precision.",
        "Architected and containerized Playwright test suites using Docker, integrating them into GitHub Actions CI/CD to achieve 80%+ regression coverage."
    ]
    for b in exp_bullets:
        story.append(Paragraph(f"• {b}", bullet_style))

    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Endeavor Group (Dan Murphy's) & Marriott</b> | <i>Lead Automation Engineer</i>", body_style))
    story.append(Paragraph("• Architected modular API automation framework for Salesforce Commerce Cloud (SCAPI), validating checkout & payment gateway integrations.", bullet_style))
    story.append(Paragraph("• Led migration of legacy Tosca automation framework to Python-Playwright architecture leveraging Cursor, Playwright MCP, and autonomous QE agents.", bullet_style))

    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Optimum Solutions (Client: DBS Bank)</b> | <i>Sr. Automation Engineer (Jun 2020 – Jan 2023)</i>", body_style))
    story.append(Paragraph("• Automated web CRM insurance platforms and mobile banking workflows using Selenium, Appium, Karate, Core Java, and TestNG.", bullet_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("EDUCATION & HONORS", section_heading))
    story.append(Paragraph("• <b>B.Tech in Electronics & Instrumentation</b> | Bapatla Engineering College, Acharya Nagarjuna University", bullet_style))
    story.append(Paragraph("• <b>Awards:</b> Best Employee Award & QE R&R Recognition (2023) @ Publicis Sapient | Inner Source Contributor Award", bullet_style))
    story.append(Paragraph("• <b>All India GATE Rank Holder</b> | Top Ranker: SSC & Intermediate State Merit", bullet_style))

    doc.build(story)
    print(f"Generated PDF at: {pdf_path.resolve()}")

if __name__ == "__main__":
    generate_pdf()

