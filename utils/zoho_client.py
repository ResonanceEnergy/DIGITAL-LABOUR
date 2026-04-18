"""Zoho One Integration Client — CRM, Projects, Analytics, Contracts.

Connects BIT RAGE LABOUR SYSTEMS to the Zoho ecosystem for:
  - CRM: Contacts, Leads, Deals, Pipeline management
  - Mail: Already wired via SMTP/IMAP (inbox_reader, cold_email_spray)
  - Projects: Task/mandate tracking (complements Paperclip)
  - Analytics: KPI dashboards for C-Suite (Axiom, Vectis, Ledgr)

Auth: Zoho OAuth2 Self-Client flow (generate refresh token once, auto-refreshes)
Datacenter: zohocloud.ca (Canadian)

Usage:
    from utils.zoho_client import zoho

    # Create a lead from freelance platform
    lead = await zoho.create_lead({
        "First_Name": "John", "Last_Name": "Doe",
        "Company": "Acme Corp", "Email": "john@acme.com",
        "Lead_Source": "Upwork", "Description": "Needs SEO content"
    })

    # Create a deal from won bid
    deal = await zoho.create_deal({
        "Deal_Name": "Acme SEO Package",
        "Stage": "Won", "Amount": 500,
        "Pipeline": "Freelance", "Contact_Name": lead["id"]
    })

    # Push contact from cold email prospect
    contact = await zoho.upsert_contact({
        "Email": "jane@startup.io",
        "First_Name": "Jane", "Last_Name": "Smith",
        "Lead_Source": "Cold Email"
    })

Setup:
    1. Go to https://api-console.zohocloud.ca/
    2. Create a Self Client
    3. Generate refresh token with scopes:
       ZohoCRM.modules.ALL, ZohoCRM.settings.ALL, ZohoProjects.portals.ALL
    4. Add to .env: ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger("brl.zoho_client")

# ── Configuration ───────────────────────────────────────────────

ZOHO_DATACENTER = os.getenv("ZOHO_DATACENTER", "ca")  # ca = Canada
ZOHO_ACCOUNTS_URL = f"https://accounts.zohocloud.{ZOHO_DATACENTER}"
ZOHO_CRM_URL = f"https://www.zohoapis.{ZOHO_DATACENTER}/crm/v6"
ZOHO_PROJECTS_URL = f"https://projectsapi.zoho.{ZOHO_DATACENTER}/restapi"

ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN", "")

# Token cache
_token_cache: dict[str, Any] = {"access_token": "", "expires_at": 0}


# ── BRL Pipeline Stages → Zoho CRM Stages ──────────────────────

PIPELINE_STAGES = {
    "freelance": [
        "Hunt", "Bid Submitted", "Interview", "Won",
        "In Delivery", "Delivered", "Payment Received", "Closed Lost"
    ],
    "direct_sales": [
        "Lead In", "Qualified", "Proposal Sent", "Negotiation",
        "Won", "In Delivery", "Delivered", "Payment Received", "Closed Lost"
    ],
    "cold_outreach": [
        "Prospected", "Email Sent", "Replied", "Meeting Booked",
        "Proposal Sent", "Won", "Closed Lost"
    ],
}

# Map BRL lead sources to Zoho Lead_Source values
LEAD_SOURCE_MAP = {
    "fiverr": "Fiverr",
    "upwork": "Upwork",
    "freelancer": "Freelancer.com",
    "pph": "PeoplePerHour",
    "guru": "Guru",
    "cold_email": "Cold Email",
    "website": "Website",
    "api": "API / RapidAPI",
    "referral": "Referral",
    "linkedin": "LinkedIn",
    "x_twitter": "X / Twitter",
    "lead_magnet": "Lead Magnet",
    "stripe": "Stripe Direct",
    "chatbot": "White-Label Bot",
}


class ZohoClient:
    """Async Zoho API client for BIT RAGE LABOUR SYSTEMS."""

    def __init__(self):
        self._http: Optional[httpx.AsyncClient] = None

    @property
    def configured(self) -> bool:
        return bool(ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET and ZOHO_REFRESH_TOKEN)

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    # ── OAuth2 Token Management ─────────────────────────────────

    async def _get_access_token(self) -> str:
        """Get valid access token, refreshing if expired."""
        if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 60:
            return _token_cache["access_token"]

        if not self.configured:
            raise RuntimeError("Zoho OAuth not configured. Set ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN")

        client = await self._client()
        resp = await client.post(
            f"{ZOHO_ACCOUNTS_URL}/oauth/v2/token",
            params={
                "grant_type": "refresh_token",
                "client_id": ZOHO_CLIENT_ID,
                "client_secret": ZOHO_CLIENT_SECRET,
                "refresh_token": ZOHO_REFRESH_TOKEN,
            },
        )
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"Zoho token refresh failed: {data}")

        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
        logger.info("Zoho access token refreshed (expires in %ds)", data.get("expires_in", 3600))
        return _token_cache["access_token"]

    async def _headers(self) -> dict:
        token = await self._get_access_token()
        return {"Authorization": f"Zoho-oauthtoken {token}"}

    # ── CRM: Generic CRUD ───────────────────────────────────────

    async def _crm_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated CRM API request."""
        client = await self._client()
        headers = await self._headers()
        url = f"{ZOHO_CRM_URL}/{endpoint}"

        if method == "GET":
            resp = await client.get(url, headers=headers, params=data)
        elif method == "POST":
            resp = await client.post(url, headers=headers, json={"data": [data]} if data else None)
        elif method == "PUT":
            resp = await client.put(url, headers=headers, json={"data": [data]} if data else None)
        elif method == "DELETE":
            resp = await client.delete(url, headers=headers, params=data)
        else:
            raise ValueError(f"Unknown method: {method}")

        if resp.status_code >= 400:
            logger.error("Zoho CRM %s %s → %d: %s", method, endpoint, resp.status_code, resp.text[:200])
            return {"error": resp.text, "status": resp.status_code}

        return resp.json() if resp.text else {}

    # ── CRM: Leads ──────────────────────────────────────────────

    async def create_lead(self, lead_data: dict) -> dict:
        """Create a lead in Zoho CRM.

        Args:
            lead_data: Dict with Zoho CRM Lead fields.
                Required: Last_Name, Company
                Recommended: Email, Phone, Lead_Source, Description
        """
        # Map BRL source to Zoho source
        source = lead_data.get("Lead_Source", "").lower()
        if source in LEAD_SOURCE_MAP:
            lead_data["Lead_Source"] = LEAD_SOURCE_MAP[source]

        result = await self._crm_request("POST", "Leads", lead_data)
        logger.info("Zoho lead created: %s", lead_data.get("Last_Name", ""))
        return result

    async def search_leads(self, criteria: str) -> dict:
        """Search leads. criteria: '(Email:equals:john@example.com)'"""
        return await self._crm_request("GET", "Leads/search", {"criteria": criteria})

    # ── CRM: Contacts ───────────────────────────────────────────

    async def create_contact(self, contact_data: dict) -> dict:
        """Create a contact in Zoho CRM."""
        result = await self._crm_request("POST", "Contacts", contact_data)
        logger.info("Zoho contact created: %s %s", contact_data.get("First_Name", ""), contact_data.get("Last_Name", ""))
        return result

    async def upsert_contact(self, contact_data: dict) -> dict:
        """Create or update contact by email (dedup-safe)."""
        return await self._crm_request("POST", "Contacts/upsert", contact_data)

    async def search_contacts(self, criteria: str) -> dict:
        return await self._crm_request("GET", "Contacts/search", {"criteria": criteria})

    # ── CRM: Deals ──────────────────────────────────────────────

    async def create_deal(self, deal_data: dict) -> dict:
        """Create a deal in Zoho CRM.

        Args:
            deal_data: Dict with Zoho CRM Deal fields.
                Required: Deal_Name, Stage
                Recommended: Amount, Pipeline, Contact_Name, Closing_Date
        """
        result = await self._crm_request("POST", "Deals", deal_data)
        logger.info("Zoho deal created: %s ($%s)", deal_data.get("Deal_Name", ""), deal_data.get("Amount", 0))
        return result

    async def update_deal_stage(self, deal_id: str, stage: str, notes: str = "") -> dict:
        """Move deal to a new pipeline stage."""
        data = {"Stage": stage}
        if notes:
            data["Description"] = notes
        result = await self._crm_request("PUT", f"Deals/{deal_id}", data)
        logger.info("Zoho deal %s → stage: %s", deal_id, stage)
        return result

    async def search_deals(self, criteria: str) -> dict:
        return await self._crm_request("GET", "Deals/search", {"criteria": criteria})

    async def get_deals_by_stage(self, stage: str) -> dict:
        return await self.search_deals(f"(Stage:equals:{stage})")

    # ── CRM: Notes ──────────────────────────────────────────────

    async def add_note(self, module: str, record_id: str, title: str, content: str) -> dict:
        """Add a note to any CRM record (Lead, Contact, Deal)."""
        client = await self._client()
        headers = await self._headers()
        resp = await client.post(
            f"{ZOHO_CRM_URL}/{module}/{record_id}/Notes",
            headers=headers,
            json={"data": [{"Note_Title": title, "Note_Content": content}]},
        )
        return resp.json() if resp.text else {}

    # ── CRM: Activities / Tasks ─────────────────────────────────

    async def create_task(self, task_data: dict) -> dict:
        """Create a CRM task (follow-up, callback, etc.)."""
        return await self._crm_request("POST", "Tasks", task_data)

    # ── BRL-Specific Helpers ────────────────────────────────────

    async def sync_freelance_job(
        self, platform: str, job_data: dict, stage: str = "Hunt"
    ) -> dict:
        """Sync a freelance job/bid to Zoho CRM as a Deal.

        Called by OpenClaw during freelance lifecycle.
        Maps: hunt→Hunt, bid→Bid Submitted, win→Won, deliver→In Delivery, collect→Payment Received
        """
        deal = {
            "Deal_Name": f"[{platform.upper()}] {job_data.get('title', 'Untitled')[:80]}",
            "Stage": stage,
            "Pipeline": "Freelance",
            "Amount": job_data.get("budget", 0),
            "Description": json.dumps({
                "platform": platform,
                "job_id": job_data.get("id", ""),
                "url": job_data.get("url", ""),
                "skills": job_data.get("skills", []),
                "client": job_data.get("client_name", ""),
            }, indent=2),
            "Lead_Source": LEAD_SOURCE_MAP.get(platform, platform),
        }

        # Try to link to existing contact
        client_name = job_data.get("client_name", "")
        if client_name:
            deal["Contact_Name"] = client_name

        return await self.create_deal(deal)

    async def sync_cold_email_prospect(self, prospect: dict) -> dict:
        """Sync a cold email prospect to Zoho CRM as a Lead.

        Called by cold_email_spray and prospect_engine.
        """
        return await self.create_lead({
            "First_Name": prospect.get("first_name", ""),
            "Last_Name": prospect.get("last_name", prospect.get("name", "Unknown")),
            "Company": prospect.get("company", ""),
            "Email": prospect.get("email", ""),
            "Phone": prospect.get("phone", ""),
            "Lead_Source": "Cold Email",
            "Description": f"ICP Score: {prospect.get('score', 0)}/100\n"
                           f"Industry: {prospect.get('industry', '')}\n"
                           f"Source: {prospect.get('source', 'prospect_engine')}",
        })

    async def sync_inbound_lead(self, source: str, lead_data: dict) -> dict:
        """Sync an inbound lead (website, API, lead magnet, Stripe).

        Called by api/intake.py, api/lead_magnet.py, billing/tracker.py.
        """
        return await self.create_lead({
            "First_Name": lead_data.get("first_name", ""),
            "Last_Name": lead_data.get("last_name", lead_data.get("name", "Inbound")),
            "Company": lead_data.get("company", ""),
            "Email": lead_data.get("email", ""),
            "Lead_Source": LEAD_SOURCE_MAP.get(source, source),
            "Description": json.dumps(lead_data, indent=2, default=str),
        })

    async def sync_stripe_payment(self, charge: dict) -> dict:
        """When Stripe payment received, create/update deal as Won + Payment Received.

        Called by automation/revenue_daemon.py.
        """
        return await self.create_deal({
            "Deal_Name": f"[STRIPE] {charge.get('description', 'Payment')[:80]}",
            "Stage": "Payment Received",
            "Pipeline": "Direct Sales",
            "Amount": charge.get("amount", 0) / 100,  # Stripe amounts are in cents
            "Lead_Source": "Stripe Direct",
            "Description": f"Stripe charge: {charge.get('id', '')}\n"
                           f"Customer: {charge.get('customer', '')}\n"
                           f"Email: {charge.get('receipt_email', '')}",
        })

    async def get_pipeline_summary(self) -> dict:
        """Get pipeline summary for C-Suite KPI reporting.

        Returns deal counts and amounts by stage for each pipeline.
        Called by c_suite/vectis.py and c_suite/ledgr.py.
        """
        summary = {}
        for pipeline_name, stages in PIPELINE_STAGES.items():
            pipeline_data = {"total_deals": 0, "total_value": 0, "stages": {}}
            for stage in stages:
                try:
                    result = await self.get_deals_by_stage(stage)
                    deals = result.get("data", [])
                    stage_value = sum(d.get("Amount", 0) or 0 for d in deals)
                    pipeline_data["stages"][stage] = {
                        "count": len(deals),
                        "value": stage_value,
                    }
                    pipeline_data["total_deals"] += len(deals)
                    pipeline_data["total_value"] += stage_value
                except Exception:
                    pipeline_data["stages"][stage] = {"count": 0, "value": 0}
            summary[pipeline_name] = pipeline_data
        return summary

    # ── Lifecycle ───────────────────────────────────────────────

    async def close(self):
        if self._http:
            await self._http.aclose()
            self._http = None


# Module-level singleton
zoho = ZohoClient()


# ── Sync Wrappers (for non-async callers) ──────────────────────

def _run_async(coro):
    """Run an async coroutine from sync code safely."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an event loop (e.g., FastAPI) — schedule as task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result(timeout=30)
    else:
        return asyncio.run(coro)


def sync_freelance_job(platform: str, job_data: dict, stage: str = "Hunt") -> dict:
    """Sync wrapper: push freelance job/bid to Zoho CRM as a Deal."""
    if not zoho.configured:
        logger.debug("Zoho not configured — skipping sync_freelance_job")
        return {}
    try:
        return _run_async(zoho.sync_freelance_job(platform, job_data, stage))
    except Exception as e:
        logger.warning("Zoho sync_freelance_job failed: %s", e)
        return {"error": str(e)}


def sync_cold_email_prospect(prospect: dict) -> dict:
    """Sync wrapper: push cold email prospect to Zoho CRM as a Lead."""
    if not zoho.configured:
        return {}
    try:
        return _run_async(zoho.sync_cold_email_prospect(prospect))
    except Exception as e:
        logger.warning("Zoho sync_cold_email_prospect failed: %s", e)
        return {"error": str(e)}


def sync_inbound_lead(source: str, lead_data: dict) -> dict:
    """Sync wrapper: push inbound lead to Zoho CRM."""
    if not zoho.configured:
        return {}
    try:
        return _run_async(zoho.sync_inbound_lead(source, lead_data))
    except Exception as e:
        logger.warning("Zoho sync_inbound_lead failed: %s", e)
        return {"error": str(e)}


def sync_stripe_payment(charge: dict) -> dict:
    """Sync wrapper: push Stripe payment to Zoho CRM as a Won Deal."""
    if not zoho.configured:
        return {}
    try:
        return _run_async(zoho.sync_stripe_payment(charge))
    except Exception as e:
        logger.warning("Zoho sync_stripe_payment failed: %s", e)
        return {"error": str(e)}
