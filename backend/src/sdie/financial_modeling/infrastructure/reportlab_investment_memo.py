"""ReportLab renderer for an executive investment-committee memo."""
from __future__ import annotations

import io
from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import Decimal
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from sdie.financial_modeling.application.planning import OperatingForecastAnalysisResult
from sdie.financial_modeling.domain.capital_allocation import CapitalAllocationResult

_INK = colors.HexColor("#0D1117")
_LEDGER = colors.HexColor("#1E6B62")
_MUTED = colors.HexColor("#5A6472")
_LIGHT = colors.HexColor("#F2F5F3")
_TABLE_CELL_STYLE = ParagraphStyle(
    "MemoTableCell",
    fontName="Helvetica",
    fontSize=7.5,
    leading=9,
    textColor=_INK,
)


class ReportLabInvestmentMemoRenderer:
    def render(
        self,
        *,
        portfolio_name: str,
        business_context: str,
        allocation: CapitalAllocationResult,
        forecast: OperatingForecastAnalysisResult,
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=0.65 * inch,
            bottomMargin=0.65 * inch,
            leftMargin=0.7 * inch,
            rightMargin=0.7 * inch,
            title=portfolio_name,
            author="Strategic Decision Intelligence Engine",
        )
        styles = self._styles()
        selected_names = [
            metric.opportunity.name
            for metric in allocation.opportunity_metrics
            if metric.opportunity.investment_id in set(allocation.selected_investment_ids)
        ]
        story: list[object] = [
            Paragraph("STRATEGIC DECISION INTELLIGENCE ENGINE", styles["Eyebrow"]),
            Paragraph("Executive Investment Decision Memo", styles["Eyebrow2"]),
            Spacer(1, 8),
            Paragraph(escape(_clean(portfolio_name)), styles["Title"]),
            Paragraph(
                f"Prepared {datetime.now(ZoneInfo('America/New_York')).strftime('%B %d, %Y')} | "
                f"Currency: {allocation.capital_budget.currency}",
                styles["Meta"],
            ),
            Spacer(1, 18),
            Paragraph("1. Investment decision", styles["Section"]),
            Paragraph(
                "Approve " + escape(_clean(", ".join(selected_names))) + ".",
                styles["Recommendation"],
            ),
            Paragraph(
                f"This exact 0-1 capital-budget solution deploys "
                f"{_money(allocation.capital_used.amount)} of "
                f"{_money(allocation.capital_budget.amount)} available capital and produces "
                f"a modeled portfolio NPV of {_money(allocation.portfolio_npv.amount)}.",
                styles["Body"],
            ),
            Spacer(1, 10),
            Paragraph("2. Business context", styles["Section"]),
            Paragraph(escape(_clean(business_context)), styles["Body"]),
            Spacer(1, 10),
            Paragraph("3. Capital requirements", styles["Section"]),
            self._capital_summary(allocation),
            Spacer(1, 12),
            Paragraph("4. Financial projections", styles["Section"]),
            Paragraph(
                f"Five-year operating forecast for "
                f"{escape(_clean(forecast.base_case.assumptions.project_name))}.",
                styles["Body"],
            ),
            self._forecast_table(forecast),
            PageBreak(),
            Paragraph("5. NPV, IRR, and payback findings", styles["Section"]),
            self._investment_table(allocation),
            Spacer(1, 12),
            Paragraph("6. Scenario comparison", styles["Section"]),
            self._scenario_table(forecast),
            Paragraph(
                f"Probability-weighted expected NPV: "
                f"{_money(forecast.scenarios.probability_weighted_npv.amount)}.",
                styles["Body"],
            ),
            Spacer(1, 12),
            Paragraph("7. Sensitivity results", styles["Section"]),
            self._sensitivity_table(forecast),
            Paragraph(
                "Revenue-growth break-even: "
                + (
                    f"{forecast.sensitivity.break_even_revenue_growth_percent}% per year."
                    if forecast.sensitivity.break_even_revenue_growth_percent is not None
                    else "not reached within the tested -90% to +200% annual growth range."
                ),
                styles["Body"],
            ),
            PageBreak(),
            Paragraph("8. Assumptions", styles["Section"]),
            Paragraph(
                "All case values are analyst-supplied hypothetical forecasts. Free cash flow is "
                "EBIT x (1 - tax rate) + depreciation and amortization - capital expenditures - "
                "change in working capital. Taxes are floored at zero because net operating loss "
                "carryforwards are not modeled. No terminal value is included; valuation therefore "
                "covers only the explicit five-year horizon.",
                styles["Body"],
            ),
            Paragraph(
                "Sensitivity shocks are analyst-assumed one-way stresses: +/-2 percentage points for "
                "revenue growth, discount rate, and capex; +/-3 points for gross margin.",
                styles["Body"],
            ),
            Spacer(1, 12),
            Paragraph("9. Risks and constraints", styles["Section"]),
            *self._risk_paragraphs(allocation, styles),
            Spacer(1, 12),
            Paragraph("10. Recommended capital allocation", styles["Section"]),
            self._allocation_table(allocation),
            Paragraph(
                escape(_clean(allocation.optimization_method))
                + " The defined baseline is shown only as a comparison policy; it is not the "
                "value-maximizing objective.",
                styles["Body"],
            ),
            Spacer(1, 18),
            Paragraph(
                "Traceability: every amount in this memo is recomputed from the submitted forecast, "
                "cash-flow, risk, dependency, exclusivity, and capital-budget inputs.",
                styles["Footer"],
            ),
        ]
        doc.build(story, onFirstPage=self._page_footer, onLaterPages=self._page_footer)
        return buffer.getvalue()

    @staticmethod
    def _capital_summary(allocation: CapitalAllocationResult) -> Table:
        rows = [
            ["Capital budget", "Capital used", "Utilization", "Portfolio NPV"],
            [
                _money(allocation.capital_budget.amount),
                _money(allocation.capital_used.amount),
                f"{allocation.capital_utilization_percent}%",
                _money(allocation.portfolio_npv.amount),
            ],
        ]
        return _table(rows, [1.55 * inch] * 4)

    @staticmethod
    def _forecast_table(forecast: OperatingForecastAnalysisResult) -> Table:
        rows: list[list[str]] = [
            ["Year", "Revenue", "EBITDA", "EBIT", "Capex", "Change NWC", "FCF"]
        ]
        for year in forecast.base_case.years:
            rows.append(
                [
                    str(year.year),
                    _money(year.revenue.amount),
                    _money(year.ebitda.amount),
                    _money(year.ebit.amount),
                    _money(year.capital_expenditures.amount),
                    _money(year.change_in_working_capital.amount),
                    _money(year.free_cash_flow.amount),
                ]
            )
        return _table(
            rows,
            [
                0.42 * inch,
                0.92 * inch,
                0.88 * inch,
                0.82 * inch,
                0.82 * inch,
                0.82 * inch,
                0.88 * inch,
            ],
        )

    @staticmethod
    def _investment_table(allocation: CapitalAllocationResult) -> Table:
        rows: list[list[object]] = [
            ["Investment", "Capital", "NPV", "IRR", "Payback", "Downside NPV"]
        ]
        for metric in allocation.opportunity_metrics:
            rows.append(
                [
                    _table_cell(metric.opportunity.name),
                    _money(metric.opportunity.initial_capital.amount),
                    _money(metric.npv.amount),
                    _percent(metric.irr.as_percent()) if metric.irr else "n/m",
                    f"{metric.payback_period:.2f} yrs" if metric.payback_period is not None else "Beyond horizon",
                    _money(metric.downside_npv.amount),
                ]
            )
        return _table(
            rows,
            [1.75 * inch, 0.95 * inch, 0.95 * inch, 0.65 * inch, 1.0 * inch, 1.05 * inch],
        )

    @staticmethod
    def _scenario_table(forecast: OperatingForecastAnalysisResult) -> Table:
        rows: list[list[str]] = [["Scenario", "Probability", "NPV", "IRR"]]
        for scenario in forecast.scenarios.scenarios:
            rows.append(
                [
                    scenario.name,
                    _percent(scenario.probability.as_percent()),
                    _money(scenario.forecast.npv.amount),
                    _percent(scenario.forecast.irr.as_percent()) if scenario.forecast.irr else "n/m",
                ]
            )
        return _table(rows, [1.7 * inch, 1.3 * inch, 1.5 * inch, 1.2 * inch])

    @staticmethod
    def _sensitivity_table(forecast: OperatingForecastAnalysisResult) -> Table:
        rows: list[list[str]] = [["Driver", "Low NPV", "Base NPV", "High NPV"]]
        drivers: dict[str, dict[str, Decimal]] = {}
        for point in forecast.sensitivity.points:
            drivers.setdefault(point.driver, {})[point.case] = point.npv.amount
        for driver, cases in drivers.items():
            rows.append(
                [
                    driver.replace("_", " ").title(),
                    _money(cases["low"]),
                    _money(cases["base"]),
                    _money(cases["high"]),
                ]
            )
        return _table(rows, [1.75 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch])

    @staticmethod
    def _risk_paragraphs(
        allocation: CapitalAllocationResult, styles: dict[str, ParagraphStyle]
    ) -> Iterable[Paragraph]:
        for metric in allocation.opportunity_metrics:
            constraints: list[str] = []
            if metric.opportunity.dependencies:
                constraints.append("depends on " + ", ".join(metric.opportunity.dependencies))
            if metric.opportunity.mutually_exclusive_group:
                constraints.append(
                    "mutually exclusive group: " + metric.opportunity.mutually_exclusive_group
                )
            suffix = f" Constraints: {'; '.join(constraints)}." if constraints else ""
            yield Paragraph(
                f"<b>{escape(_clean(metric.opportunity.name))}</b> - "
                f"{escape(_clean(metric.opportunity.risk_assumption))} "
                f"Modeled downside exposure: {_money(metric.downside_exposure.amount)}.{escape(suffix)}",
                styles["Body"],
            )

    @staticmethod
    def _allocation_table(allocation: CapitalAllocationResult) -> Table:
        selected = set(allocation.selected_investment_ids)
        rows: list[list[object]] = [["Decision", "Investment", "Capital", "NPV", "Priority"]]
        for metric in allocation.opportunity_metrics:
            rows.append(
                [
                    "Fund" if metric.opportunity.investment_id in selected else "Defer",
                    _table_cell(metric.opportunity.name),
                    _money(metric.opportunity.initial_capital.amount),
                    _money(metric.npv.amount),
                    f"{metric.opportunity.strategic_priority}/5",
                ]
            )
        rows.extend(
            [
                [
                    "",
                    "Optimized portfolio",
                    _money(allocation.capital_used.amount),
                    _money(allocation.portfolio_npv.amount),
                    "",
                ],
                ["", "Defined baseline", "", _money(allocation.baseline_npv.amount), ""],
                ["", "Incremental NPV", "", _money(allocation.incremental_npv_vs_baseline.amount), ""],
            ]
        )
        return _table(rows, [0.65 * inch, 2.45 * inch, 1.0 * inch, 1.0 * inch, 0.75 * inch])

    @staticmethod
    def _styles() -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "Eyebrow": ParagraphStyle(
                "MemoEyebrow", parent=base["Normal"], textColor=_LEDGER, fontSize=9,
                fontName="Helvetica-Bold", spaceAfter=2,
            ),
            "Eyebrow2": ParagraphStyle(
                "MemoEyebrow2", parent=base["Normal"], textColor=_MUTED, fontSize=9,
            ),
            "Title": ParagraphStyle(
                "MemoTitle", parent=base["Title"], textColor=_INK, fontSize=23, leading=27,
            ),
            "Meta": ParagraphStyle("MemoMeta", parent=base["Normal"], textColor=_MUTED, fontSize=8),
            "Section": ParagraphStyle(
                "MemoSection", parent=base["Normal"], textColor=_LEDGER, fontSize=12,
                fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=6,
            ),
            "Recommendation": ParagraphStyle(
                "MemoRecommendation", parent=base["Normal"], textColor=_INK, fontSize=15,
                fontName="Helvetica-Bold", leading=19, spaceAfter=6,
            ),
            "Body": ParagraphStyle(
                "MemoBody", parent=base["Normal"], textColor=_INK, fontSize=9.5,
                leading=13.5, spaceAfter=5,
            ),
            "Footer": ParagraphStyle(
                "MemoFooter", parent=base["Normal"], textColor=_MUTED, fontSize=7.5, leading=10,
            ),
        }

    @staticmethod
    def _page_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(_MUTED)
        canvas.drawString(0.7 * inch, 0.35 * inch, "SDIE | Executive Investment Decision Memo")
        canvas.drawRightString(7.8 * inch, 0.35 * inch, f"Page {doc.page}")
        canvas.restoreState()


def _table(rows: Sequence[Sequence[object]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D0CC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _money(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def _percent(value: Decimal) -> str:
    return f"{value:.1f}%"


def _table_cell(value: str) -> Paragraph:
    return Paragraph(escape(_clean(value)), _TABLE_CELL_STYLE)


def _clean(value: str) -> str:
    return (
        value.replace("—", "-")
        .replace("–", "-")
        .replace("−", "-")
        .replace("×", "x")
        .replace("Δ", "Change ")
    )
