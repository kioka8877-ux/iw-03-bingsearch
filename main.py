"""
IW-03 BingSearch — Bing Organic Search Results
Iron Warrior #3 — Alternative Google, marché Japon/US.
Attaque : Scale SERP ($59/10K reqs)
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
sys.path.insert(0, '/home/user/iron_warriors/shared')
from base import (
    create_app, fetch_html, SearchResult, SERPResponse,
    clean_text, get_timestamp, measure_latency
)
import time

app = create_app("IW-03 BingSearch", "Bing organic search results — alternative Google")

@app.get("/search", response_model=SERPResponse)
async def bing_search(
    q: str = Query(..., description="Search query"),
    num: int = Query(10, ge=1, le=50, description="Number of results"),
    cc: str = Query("us", description="Country code (us, fr, uk, jp...)"),
    setlang: str = Query("en", description="Language (en, fr, ja...)"),
):
    start = time.time()
    url = f"https://www.bing.com/search?q={quote_plus(q)}&count={num}&cc={cc}&setlang={setlang}"
    try:
        html = await fetch_html(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bing fetch failed: {e}")

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()

    # Bing organic results — li.b_algo
    for li in soup.find_all('li', class_='b_algo'):
        h2 = li.find('h2')
        link = h2.find('a', href=True) if h2 else None
        snippet_tag = li.find('p') or li.find('div', class_='b_caption')
        if h2 and link:
            href = link['href']
            if href in seen or not href.startswith('http'):
                continue
            seen.add(href)
            results.append(SearchResult(
                title=clean_text(h2.get_text()),
                url=href,
                snippet=clean_text(snippet_tag.get_text()) if snippet_tag else "",
                position=len(results) + 1,
            ))
            if len(results) >= num:
                break

    # Related searches
    related = []
    for rs in soup.find_all('a', class_='b_widgetExpand'):
        related.append(clean_text(rs.get_text()))
    if not related:
        for rs in soup.find_all('li', class_='b_ans'):
            for a in rs.find_all('a', href=True):
                if '/search?q=' in a['href']:
                    related.append(clean_text(a.get_text()))

    return SERPResponse(
        query=q, engine="bing",
        results=results, related_searches=related[:10],
        timestamp=get_timestamp(), latency_ms=measure_latency(start),
    )
