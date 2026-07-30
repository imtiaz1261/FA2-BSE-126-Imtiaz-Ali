"""
Sample knowledge base for the RAG chatbot being evaluated.

In a real deployment this module would be replaced by your actual document
store / ingestion pipeline. It exists here so the evaluation pipeline is
fully self-contained and runnable end-to-end without any external chatbot —
swap `get_documents()` for your own retrieval source and everything downstream
(vector store, retriever, evaluator, reports) keeps working unchanged.

Domain: fictional cloud storage company "Nimbus Cloud", used consistently
across the 20-question evaluation dataset.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str


def get_documents() -> list[Document]:
    return [
        Document(
            "doc_overview",
            "Nimbus Cloud is a cloud storage and compute platform founded in 2019. "
            "It provides object storage, managed databases, and serverless compute "
            "for individuals and businesses.",
        ),
        Document(
            "doc_founders",
            "Nimbus Cloud was founded by Maria Chen and Raj Patel in San Francisco, "
            "California in 2019.",
        ),
        Document(
            "doc_pricing",
            "Nimbus Cloud offers three pricing tiers: Free ($0/month), Pro ($20/month), "
            "and Enterprise (custom pricing, contact sales).",
        ),
        Document(
            "doc_storage_limits",
            "Storage limits by tier: the Free tier includes 5GB of storage, the Pro tier "
            "includes 500GB of storage, and the Enterprise tier includes unlimited storage.",
        ),
        Document(
            "doc_encryption",
            "All data on Nimbus Cloud is encrypted using AES-256 encryption at rest and "
            "TLS 1.3 encryption in transit.",
        ),
        Document(
            "doc_compliance",
            "Nimbus Cloud holds SOC 2 Type II certification and ISO 27001 certification, "
            "and is fully GDPR compliant for customers in the European Union.",
        ),
        Document(
            "doc_uptime_sla",
            "The uptime SLA is 99.9% for the Pro plan and 99.99% for the Enterprise plan. "
            "The Free tier has no formal uptime SLA.",
        ),
        Document(
            "doc_regions",
            "Nimbus Cloud is available in four regions: US-East, US-West, EU-Central, "
            "and AP-Southeast.",
        ),
        Document(
            "doc_api_limits",
            "API rate limits are 100 requests per minute on the Free tier, 1000 requests "
            "per minute on the Pro tier, and custom limits on the Enterprise tier.",
        ),
        Document(
            "doc_backups",
            "Nimbus Cloud performs daily backup snapshots. Backups are retained for "
            "30 days on the Pro plan and 90 days on the Enterprise plan. The Free tier "
            "does not include automated backups.",
        ),
        Document(
            "doc_support",
            "Customer support varies by tier: Free tier users have access to a community "
            "forum only, Pro tier users get email support with a 24-hour response time, "
            "and Enterprise tier customers get a dedicated account manager with a "
            "1-hour response time.",
        ),
        Document(
            "doc_integrations",
            "Nimbus Cloud integrates with Slack, GitHub, Zapier, and Salesforce.",
        ),
        Document(
            "doc_competitor",
            "Compared to its competitor CloudPeak, Nimbus Cloud offers lower data egress "
            "fees but supports fewer geographic regions than CloudPeak.",
        ),
        Document(
            "doc_data_deletion",
            "When a customer deletes data, it is purged from primary storage within 30 days. "
            "Copies of deleted data in backup snapshots are purged within 90 days.",
        ),
        Document(
            "doc_free_tier_limits",
            "The Free tier does not include single sign-on (SSO), does not include "
            "dedicated support, and is capped at 5GB of storage.",
        ),
    ]
