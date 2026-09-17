"""Portfolio ingestion tests for CSV, XLSX, and manual holdings."""

from datetime import date
from io import BytesIO

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from backend.services.portfolio_upload_service import (
    PortfolioUploadService,
    UploadedHolding,
)
from quant_engine.data.models import MarketBar
from tests.services.test_signal_evaluation_service import IntegrationProvider


def provider() -> IntegrationProvider:
    return IntegrationProvider(
        [
            MarketBar(
                ticker=ticker,
                timestamp=date(2026, 1, 2),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=1_000.0,
            )
            for ticker, price in (("AAA", 120.0), ("BBB", 80.0))
        ]
    )


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_parse_and_create_uploaded_portfolio(db_session: Session, extension: str) -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["aaa", "bbb"],
            "quantity": [2.0, 1.0],
            "average_price": [100.0, 90.0],
        }
    )
    if extension == "csv":
        content = frame.to_csv(index=False).encode()
    else:
        output = BytesIO()
        frame.to_excel(output, index=False)
        content = output.getvalue()
    service = PortfolioUploadService(db_session, provider())

    holdings = service.parse(content, f"holdings.{extension}")
    portfolio = service.create_portfolio(
        "Uploaded", "USD", holdings, date(2026, 1, 2), "test-user"
    )
    persisted = service.portfolios.repo.get_holdings(portfolio.id)

    assert [item.ticker for item in persisted] == ["AAA", "BBB"]
    assert portfolio.total_value == pytest.approx(320.0)
    assert sum(item.weight for item in persisted) == pytest.approx(1.0)


def test_manual_upload_validates_every_price_before_creating_portfolio(
    db_session: Session,
) -> None:
    service = PortfolioUploadService(db_session, provider())
    holdings = [
        UploadedHolding(ticker="AAA", quantity=1.0, average_price=100.0),
        UploadedHolding(ticker="MISSING", quantity=1.0, average_price=100.0),
    ]

    with pytest.raises(ValueError, match="MISSING"):
        service.create_portfolio(
            "Invalid", "USD", holdings, date(2026, 1, 2), "test-user"
        )

    assert service.portfolios.repo.list_portfolios() == []
