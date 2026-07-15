"""Check stock table and run screening."""
import asyncio
import sys
import os
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.getcwd())


async def check_stocks():
    from data.database import async_session_factory, Stock
    from sqlalchemy import select
    async with async_session_factory() as s:
        r = await s.execute(select(Stock))
        stocks = r.scalars().all()
        print(f"Stock count: {len(stocks)}")
        for st in stocks:
            print(f"  {st.symbol} ({st.market})")


async def run_scan():
    from data.downloader import DataDownloader
    d = DataDownloader()
    results = await d.screen_all("US")
    print(f"\nScan results: {len(results)} stocks")
    for r in results[:10]:
        rs_val = r.get('rs_rating', 0) or 0
        pat = r.get('pattern')
        if pat is None:
            pat_type = "-"
        elif isinstance(pat, dict):
            pat_type = pat.get('type', '-')
        else:
            pat_type = str(pat)
        print(f"  {r['code']:8s} signal={str(r['signal']):6s} score={r['score']:.1f} "
              f"stage2={r['stage2']} rs={rs_val} pattern={pat_type}")
    # Print full first result for debugging
    if results:
        import json
        print(f"\n--- First result full ---")
        r = results[0]
        for k, v in r.items():
            print(f"  {k}: {json.dumps(str(v)) if not isinstance(v, (int, float, bool)) else v}")


if __name__ == "__main__":
    print("=== Checking Stock table ===")
    asyncio.run(check_stocks())
    print("\n=== Running scan ===")
    asyncio.run(run_scan())
