"""Run the documented synthetic case through SDIE's public HTTP contracts."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sdie.financial_modeling.application.planning import (
    AnalyzeOperatingForecastUseCase,
    OptimizeCapitalAllocationUseCase,
)
from sdie.financial_modeling.infrastructure.reportlab_investment_memo import (
    ReportLabInvestmentMemoRenderer,
)
from sdie.financial_modeling.interface.router import (
    _allocation_command,
    _allocation_response,
    _forecast_command,
    _forecast_response,
)
from sdie.financial_modeling.interface.schemas import (
    AnalyzeOperatingForecastRequest,
    CapitalAllocationRequest,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        type=Path,
        default=Path(__file__).parents[2] / "case-studies" / "software-product-capital-allocation.json",
    )
    parser.add_argument("--pdf", type=Path, help="Optional path for the generated executive memo")
    args = parser.parse_args()

    print(f"Loading {args.case}", flush=True)
    payload = json.loads(args.case.read_text(encoding="utf-8"))
    allocation_request = CapitalAllocationRequest.model_validate(payload["allocation"])
    forecast_request = AnalyzeOperatingForecastRequest.model_validate(payload["forecast_analysis"])
    print("Optimizing capital allocation", flush=True)
    allocation = asyncio.run(
        OptimizeCapitalAllocationUseCase().execute(_allocation_command(allocation_request))
    )
    print("Analyzing five-year forecast", flush=True)
    forecast = asyncio.run(
        AnalyzeOperatingForecastUseCase().execute(_forecast_command(forecast_request))
    )
    result = {
        "allocation": _allocation_response(allocation_request, allocation).model_dump(mode="json"),
        "forecast": _forecast_response(forecast).model_dump(mode="json"),
    }
    print(json.dumps(result, indent=2))

    if args.pdf:
        memo = ReportLabInvestmentMemoRenderer().render(
            portfolio_name=allocation_request.portfolio_name,
            business_context=allocation_request.business_context,
            allocation=allocation,
            forecast=forecast,
        )
        args.pdf.parent.mkdir(parents=True, exist_ok=True)
        args.pdf.write_bytes(memo)
        print(f"Wrote {args.pdf}")


if __name__ == "__main__":
    main()
