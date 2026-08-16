"""
generate_documents.py
-----------------------
Generates 55 sample .txt knowledge-base documents into data/documents/
for the Jarvis-Lite AI Knowledge Assistant demo. Replace these with
your own real documents for production use — the loader accepts any
.txt/.md files (see document_loader.py for the optional frontmatter
format).
"""
from pathlib import Path

DOCS = [
    ("AI & Machine Learning", "What is Retrieval-Augmented Generation (RAG)",
     "RAG combines a language model with an external knowledge source. Instead of relying only on what the model memorized during training, the system retrieves relevant documents from a vector database and feeds them into the prompt, so answers can be grounded in up-to-date, specific information."),
    ("AI & Machine Learning", "How Vector Embeddings Work",
     "An embedding model converts text into a list of numbers (a vector) that captures its meaning. Texts with similar meaning end up close together in this vector space, which is what makes semantic search possible even when the exact words differ."),
    ("AI & Machine Learning", "Difference Between Semantic Search and Keyword Search",
     "Keyword search matches literal words and phrases, so it misses synonyms and paraphrases. Semantic search compares meaning using embeddings, so a query like 'reset my access' can still match a document about 'forgot password' even without shared words."),
    ("AI & Machine Learning", "What is a Vector Database",
     "A vector database stores embeddings alongside metadata and is optimized for fast nearest-neighbor search across millions of vectors. Popular options include ChromaDB, Pinecone, Weaviate, and Milvus, each with different trade-offs around hosting and scale."),
    ("AI & Machine Learning", "Choosing an Embedding Model",
     "Smaller embedding models like all-MiniLM-L6-v2 are fast and cheap but slightly less accurate, while larger models capture nuance better at higher compute cost. The right choice depends on your latency budget, dataset size, and accuracy requirements."),
    ("AI & Machine Learning", "What is Chunking in RAG Pipelines",
     "Chunking splits long documents into smaller passages before embedding them, so retrieval returns focused, relevant snippets instead of entire files. Overlapping chunks help preserve context that would otherwise be cut at a boundary."),
    ("AI & Machine Learning", "Prompt Engineering Basics",
     "Prompt engineering is the practice of crafting inputs to a language model to get more reliable, accurate outputs. Techniques include giving clear instructions, providing examples, and specifying the desired output format."),
    ("AI & Machine Learning", "What is Fine-Tuning",
     "Fine-tuning adjusts a pretrained model's weights using a smaller, task-specific dataset, letting it specialize in a domain like legal text or customer support without training a model from scratch."),
    ("AI & Machine Learning", "Hallucination in Language Models",
     "Hallucination happens when a language model generates confident-sounding text that is factually incorrect or unsupported by any source. Retrieval-augmented generation reduces this by grounding answers in retrieved documents."),
    ("AI & Machine Learning", "Cosine Similarity Explained",
     "Cosine similarity measures the angle between two vectors rather than their magnitude, producing a score between -1 and 1 (or 0 and 1 for normalized embeddings). It's the standard metric for comparing embeddings in semantic search."),
    ("Product Documentation", "What is Jarvis-Lite",
     "Jarvis-Lite is an AI knowledge assistant that lets teams ask natural-language questions and get answers grounded in their own internal documents, using semantic search over a vector database instead of manual keyword lookup."),
    ("Product Documentation", "Jarvis-Lite Supported File Types",
     "Jarvis-Lite can index plain text and Markdown files out of the box, with PDF and Word document support available through the optional document-conversion module."),
    ("Product Documentation", "How Jarvis-Lite Ranks Answers",
     "Every indexed passage gets a relevance score between 0 and 1 based on cosine similarity to your query's embedding. Jarvis-Lite returns the top-5 highest scoring passages by default, along with their source document and score."),
    ("Product Documentation", "Configuring Jarvis-Lite's Top-K Results",
     "The number of results Jarvis-Lite returns is controlled by the TOP_K environment variable, defaulting to 5. Increasing it surfaces more candidate passages at the cost of a longer context for the downstream language model."),
    ("Product Documentation", "Switching Jarvis-Lite's Vector Database",
     "Jarvis-Lite ships with ChromaDB as the default, persistent, local vector store. Setting VECTOR_DB_PROVIDER=pinecone switches to a managed Pinecone index for teams that need cloud-hosted, multi-region search."),
    ("Product Documentation", "Re-indexing Documents in Jarvis-Lite",
     "When source documents change, Jarvis-Lite needs to be re-indexed to pick up the updates. Calling reset_index() clears the existing collection before a fresh index_documents() run to avoid stale duplicate entries."),
    ("Product Documentation", "Jarvis-Lite Metadata Fields",
     "Each indexed chunk in Jarvis-Lite carries metadata including doc_id, filename, source path, title, category, and chunk_index, all of which are returned alongside search results for traceability."),
    ("Product Documentation", "Jarvis-Lite Offline Mode",
     "For environments without internet access, Jarvis-Lite can run with a local TF-IDF based embedding provider and an in-memory vector store, trading some semantic accuracy for zero external dependencies."),
    ("IT & Security", "How to Reset Your Password",
     "To reset a forgotten password, go to the login page and select 'Forgot password', enter your registered email, and follow the reset link sent to your inbox. Links expire after 30 minutes for security."),
    ("IT & Security", "Setting Up Two-Factor Authentication",
     "Two-factor authentication adds a second verification step beyond your password, usually a code from an authenticator app. Enable it from Account Settings under the Security tab to significantly reduce the risk of unauthorized access."),
    ("IT & Security", "Company VPN Access Policy",
     "Employees connecting from outside the office network must use the company VPN to access internal systems. VPN credentials are separate from your email login and are issued by the IT helpdesk on your first day."),
    ("IT & Security", "Reporting a Phishing Email",
     "If you receive a suspicious email asking for credentials or urgent payment, do not click any links. Forward it to security@company.com and delete it; never reply to or forward it to colleagues directly."),
    ("IT & Security", "Data Classification Levels",
     "Company data is classified as Public, Internal, Confidential, or Restricted. Confidential and Restricted data must be encrypted at rest and never shared outside approved, access-controlled systems."),
    ("IT & Security", "Requesting Software Installation",
     "New software requests go through the IT service portal, where they're reviewed for licensing and security compliance before approval. Most standard business tools are approved within one business day."),
    ("IT & Security", "Laptop Encryption Requirements",
     "All company-issued laptops must have full-disk encryption enabled (BitLocker on Windows, FileVault on Mac) before they're allowed to connect to internal systems, protecting data if a device is lost or stolen."),
    ("IT & Security", "Guest Wi-Fi Access",
     "Visitors can connect to the Guest Wi-Fi network using a temporary code issued at reception, valid for the day. The guest network is isolated from internal systems and cannot access company file shares."),
    ("HR & Onboarding", "First Week Onboarding Checklist",
     "New hires should complete IT account setup, benefits enrollment, and mandatory compliance training within their first week. Your manager and HR buddy will walk you through each step during onboarding meetings."),
    ("HR & Onboarding", "How to Request Time Off",
     "Time-off requests are submitted through the HR portal at least two weeks in advance for planned leave. Your manager receives an automatic approval request and you'll see the status update in the portal."),
    ("HR & Onboarding", "Company Holiday Calendar",
     "The company observes the standard national holidays each year plus two floating holidays employees can use at their discretion, all listed on the shared HR calendar available to every employee."),
    ("HR & Onboarding", "Remote Work Policy",
     "Employees may work remotely up to three days per week with manager approval, provided they remain reachable during core hours of 10am-4pm local time and attend required in-person meetings."),
    ("HR & Onboarding", "Expense Reimbursement Process",
     "Business expenses are submitted through the finance portal with an itemized receipt attached. Approved reimbursements are processed within the next two payroll cycles."),
    ("HR & Onboarding", "Performance Review Cycle",
     "Formal performance reviews happen twice a year, in June and December, combining self-assessment, manager feedback, and peer input to inform growth plans and compensation discussions."),
    ("HR & Onboarding", "Parental Leave Policy",
     "Eligible employees receive twelve weeks of paid parental leave following the birth or adoption of a child, which can be taken continuously or split within the first year."),
    ("HR & Onboarding", "Employee Referral Program",
     "Employees who refer a candidate that's hired and completes 90 days receive a referral bonus. Submit referrals through the careers portal before the candidate applies to be eligible."),
    ("Productivity & Tools", "Best Practices for Writing Documentation",
     "Good internal documentation states the purpose up front, uses short paragraphs and headers, and is updated whenever the underlying process changes so it doesn't go stale and mislead readers."),
    ("Productivity & Tools", "Effective Meeting Notes",
     "Useful meeting notes capture decisions made, owners for each action item, and deadlines, rather than a full transcript. Share them within 24 hours while context is still fresh for attendees."),
    ("Productivity & Tools", "Managing Email Overload",
     "Batching email checks to two or three set times a day, unsubscribing from low-value lists, and using filters for recurring notifications can meaningfully cut down on inbox interruptions."),
    ("Productivity & Tools", "Time Blocking for Deep Work",
     "Time blocking reserves dedicated calendar slots for focused work on a single task, reducing context-switching. Many people find 90-minute blocks, followed by a short break, work well for sustained concentration."),
    ("Productivity & Tools", "Choosing a Project Management Tool",
     "The right project management tool depends on team size and workflow complexity — simple kanban boards suit small teams, while larger organizations often need dependency tracking and resource planning features."),
    ("Productivity & Tools", "Writing Clear Slack Messages",
     "Clear async messages state the ask and the deadline in the first line, avoid vague phrases like 'quick question', and use threads to keep related discussion together instead of scattering it across the channel."),
    ("Cloud & Infrastructure", "What is a Vector Database Index",
     "An index in a vector database is the data structure (often HNSW or IVF) used to speed up approximate nearest-neighbor search, trading a small amount of accuracy for dramatically faster query times at scale."),
    ("Cloud & Infrastructure", "On-Premise vs Managed Vector Databases",
     "Self-hosted vector databases like a local ChromaDB instance give full control over data residency at the cost of managing infrastructure yourself, while managed options like Pinecone handle scaling and uptime for a subscription fee."),
    ("Cloud & Infrastructure", "What is an API Rate Limit",
     "A rate limit caps how many requests a client can make to an API within a given time window, protecting the service from overload. Exceeding it typically returns an HTTP 429 error until the window resets."),
    ("Cloud & Infrastructure", "Environment Variables Best Practices",
     "Secrets and environment-specific settings like API keys and database URLs should live in environment variables or a secrets manager, never hardcoded in source code or committed to version control."),
    ("Cloud & Infrastructure", "What is Persistent Storage",
     "Persistent storage retains data across process restarts and redeployments, unlike in-memory storage which is wiped when a process stops. Vector databases used in production need persistent storage to avoid re-indexing from scratch."),
    ("Cloud & Infrastructure", "Basics of Container Deployment",
     "Packaging an application into a container bundles its code and dependencies into a single portable unit that runs consistently across development, staging, and production environments."),
    ("Cloud & Infrastructure", "What is Logging and Why It Matters",
     "Structured application logs record what a system did and when, making it possible to diagnose failures after the fact. Logging at appropriate levels (INFO, WARNING, ERROR) avoids both silence and noise."),
    ("Customer Support", "How to Escalate a Support Ticket",
     "If a ticket hasn't been addressed within the SLA window, reply to the ticket requesting escalation or contact the support lead directly with the ticket number for a priority review."),
    ("Customer Support", "Understanding Service Level Agreements",
     "An SLA defines the guaranteed response and resolution times a support team commits to, usually tiered by issue severity, with critical issues receiving the fastest guaranteed response."),
    ("Customer Support", "Common Login Issues and Fixes",
     "Most login problems are resolved by clearing browser cookies, confirming caps lock is off, or requesting a password reset. Persistent issues after these steps should be escalated to IT support."),
    ("Customer Support", "How Refunds Are Processed",
     "Approved refunds are issued to the original payment method and typically appear within 5-10 business days, depending on the customer's bank or card issuer processing times."),
    ("General Knowledge", "What is Cloud Computing",
     "Cloud computing delivers computing resources like servers, storage, and databases over the internet on demand, letting organizations scale capacity up or down without owning physical hardware."),
    ("General Knowledge", "What is an API",
     "An API (Application Programming Interface) is a defined way for different software systems to communicate, letting one program request data or actions from another without needing to know its internal implementation."),
    ("General Knowledge", "Difference Between SQL and NoSQL Databases",
     "SQL databases store data in structured tables with fixed schemas and strong consistency guarantees, while NoSQL databases offer flexible schemas and are often chosen for scale, speed, or unstructured data."),
]

OUT_DIR = Path(__file__).parent / "documents"


def slugify(title: str) -> str:
    return (
        title.lower()
        .replace("'", "")
        .replace(",", "")
        .replace("?", "")
        .replace("/", "-")
        .replace(" ", "-")
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i, (category, title, body) in enumerate(DOCS, start=1):
        filename = f"doc_{i:03d}_{slugify(title)}.txt"
        content = f"Title: {title}\nCategory: {category}\n---\n{body}\n"
        (OUT_DIR / filename).write_text(content, encoding="utf-8")
    print(f"Wrote {len(DOCS)} documents to {OUT_DIR}")


if __name__ == "__main__":
    main()
