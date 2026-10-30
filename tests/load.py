"""Bounded HTTP benchmark; not a production capacity certification."""
import argparse
import concurrent.futures
import http.client
import json
import time

parser = argparse.ArgumentParser()
parser.add_argument('--requests', type=int, default=30000)
parser.add_argument('--concurrency', type=int, default=100)
args = parser.parse_args()
if args.requests < 1 or args.concurrency < 1:
    parser.error('requests and concurrency must be positive')
connection = http.client.HTTPConnection('nginx', timeout=30)
connection.request('GET', '/catalog.json', headers={'Host': 'localhost'})
response = connection.getresponse()
assert response.status == 200
etag = response.getheader('ETag')
apps = len(json.loads(response.read())['apps'])
connection.close()


def worker(count):
    connection = http.client.HTTPConnection('nginx', timeout=30)
    latencies = []
    try:
        for _ in range(count):
            started = time.perf_counter()
            connection.request('GET', '/catalog.json', headers={'Host': 'localhost', 'If-None-Match': etag})
            response = connection.getresponse()
            response.read()
            if response.status != 304:
                raise RuntimeError(f'Unexpected HTTP {response.status}')
            latencies.append(time.perf_counter() - started)
    finally:
        connection.close()
    return latencies


started = time.perf_counter()
counts = [args.requests // args.concurrency + (index < args.requests % args.concurrency) for index in range(args.concurrency)]
with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
    timings = sorted(value for result in executor.map(worker, counts) for value in result)
elapsed = time.perf_counter() - started
assert len(timings) == args.requests
print(json.dumps({'requests': len(timings), 'concurrency': args.concurrency, 'apps': apps,
                  'seconds': round(elapsed, 3), 'requests_per_second': round(len(timings) / elapsed, 1),
                  'p95_ms': round(timings[min(len(timings)-1, int(len(timings) * .95))] * 1000, 2),
                  'p99_ms': round(timings[min(len(timings)-1, int(len(timings) * .99))] * 1000, 2)}))
