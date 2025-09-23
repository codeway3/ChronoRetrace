from fastapi import APIRouter, Depends
import pandas as pd
import json
import datetime
from app.analytics.services.technical_analysis_service import TechnicalAnalysisService
from app.analytics.schemas.technical_analysis import (
    TechnicalIndicatorsRequest,
    TechnicalIndicatorsResponse,
)
from app.data.managers import data_manager as data_fetcher

router = APIRouter()


@router.post("/technical-indicators", response_model=TechnicalIndicatorsResponse)
def get_technical_indicators(
    request: TechnicalIndicatorsRequest,
    service: TechnicalAnalysisService = Depends(TechnicalAnalysisService),
):
    """
    Calculate specified technical indicators for the given stock symbol and period.
    """
    # Fetch historical data
    market_type = "A_share" if "." in request.symbol else "US_stock"
    start_date = datetime.datetime.strptime(request.start_date, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(request.end_date, "%Y-%m-%d").date()
    df = data_fetcher.fetch_stock_data(
        request.symbol,
        request.interval,
        market_type,
        start_date=start_date,
        end_date=end_date,
    )

    # Ensure column names are lowercase
    df.columns = df.columns.str.lower()

    # Calculate indicators
    df_with_indicators = service.calculate_indicators(df, request.indicators)

    # Convert to list of dicts
    data_list = df_with_indicators.to_dict(orient="records")

    return TechnicalIndicatorsResponse(symbol=request.symbol, data=data_list)
