import asyncio
import time
import aiohttp

# Dummy API endpoints (JSONPlaceholder) - simulating multiple "LLM calls"
URLS = [
    "https://jsonplaceholder.typicode.com/posts/1",
    "https://jsonplaceholder.typicode.com/posts/2",
    "https://jsonplaceholder.typicode.com/posts/3",
]


async def fetch_data(session: aiohttp.ClientSession, url: str) -> dict:
    """Simulates a single async LLM/API call."""
    print(f"Sending request to {url} ...")
    async with session.get(url) as response:
        data = await response.json()
        print(f"Done with {url}")
        return data


async def main():
    async with aiohttp.ClientSession() as session:
        # Create a task for each URL -> all requests start concurrently
        tasks = [asyncio.create_task(fetch_data(session, url)) for url in URLS]

        # Wait for all of them to complete, collecting results in order
        results = await asyncio.gather(*tasks)

    return results


if __name__ == "__main__":
    t1 = time.perf_counter()
    results = asyncio.run(main())
    t2 = time.perf_counter()

    print("\n--- Results ---")
    for r in results:
        print(f"Title: {r['title']}")

    print(f"\nFinished in {t2 - t1:.2f} seconds")