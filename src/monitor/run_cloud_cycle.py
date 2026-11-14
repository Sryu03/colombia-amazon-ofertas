"""Cloud-ready Zero-Token execution entrypoint for GitHub Actions & Vercel Cron."""

from __future__ import annotations

import json
import os
from pathlib import Path

from api.index import run_zero_token_pipeline
from src.publisher.vercel_deployer import deploy_to_vercel


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent.parent
    result = run_zero_token_pipeline()

    vercel_hook = os.getenv("VERCEL_DEPLOY_HOOK_URL")
    vercel_token = os.getenv("VERCEL_TOKEN")
    deploy_res = deploy_to_vercel(
        project_dir=str(project_root),
        token=vercel_token,
        deploy_hook_url=vercel_hook,
    )

    summary = {
        "status": result["status"],
        "zero_token_llm_tokens_used": result["zero_token_llm_tokens_used"],
        "trm_cop": result["trm_cop"],
        "monitored_count": result["monitored_count"],
        "approved_deals_count": result["approved_deals_count"],
        "telegram_delivery_status": result.get("telegram_delivery_status", {}),
        "vercel_status": deploy_res["status"],
        "public_web_url": deploy_res.get("url"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
