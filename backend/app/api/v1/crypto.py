from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from app.services.crypto_fetcher import get_crypto_ohlcv, get_top_cryptos

router = APIRouter()


@router.get("/top", response_model=List[Dict[str, Any]])
async def read_top_cryptos():
    """
    Retrieve the top 100 cryptocurrencies by market capitalization.
    """
    cryptos = get_top_cryptos()  # Use the default limit (100) from the service
    if not cryptos:
        raise HTTPException(
            status_code=404, detail="Could not fetch top cryptocurrencies."
        )
    return cryptos


@router.get("/{symbol}/history", response_model=List[Dict[str, Any]])
async def read_crypto_history(
    symbol: str, interval: str = Query("daily", enum=["daily", "weekly", "monthly"])
):
    """
    Retrieve the OHLCV data for a given cryptocurrency symbol.
    """
    history = get_crypto_ohlcv(symbol.upper(), interval=interval)
    if not history:
        raise HTTPException(
            status_code=404, detail=f"Could not fetch {interval} data for {symbol}."
        )
    return history
