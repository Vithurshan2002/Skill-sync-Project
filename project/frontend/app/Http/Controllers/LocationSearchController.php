<?php

namespace App\Http\Controllers;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;

class LocationSearchController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        $request->validate(['query' => ['required', 'string', 'min:3', 'max:200']]);
        $query = preg_replace('/\s+/u', ' ', trim($request->string('query')->toString()));
        if (mb_strlen($query) < 3) {
            return response()->json(['message' => 'Enter at least three characters.'], 422);
        }
        $url = config('services.geocoding.search_url');
        if (! is_string($url) || ! str_starts_with($url, 'https://')) {
            return $this->unavailable();
        }
        $cache = Cache::store(config('services.geocoding.cache_store', 'file'));
        $key = 'geocoding:result:'.hash('sha256', $url.'|lk|en,ta,si|'.mb_strtolower($query));
        if (($cached = $cache->get($key)) !== null) {
            return response()->json(['data' => $cached])->header('Cache-Control', 'private, no-store');
        }
        // Shared across all users; public Nominatim permits at most one request per second.
        $lock = $cache->lock('geocoding:provider-lock', 20);
        if (! $lock->get()) {
            return $this->busy();
        }
        try {
            if ($cache->get('geocoding:next-request', 0) > microtime(true)) {
                return $this->busy();
            }
            $cache->put('geocoding:next-request', microtime(true) + 1.1, 3);
            try {
                $response = Http::acceptJson()
                    ->withUserAgent('SkillSync/1.0 (service marketplace address search; '.config('app.url').')')
                    ->connectTimeout(3)->timeout(8)->withoutRedirecting()
                    ->get($url, ['q' => $query, 'format' => 'jsonv2', 'countrycodes' => 'lk',
                        'limit' => 5, 'accept-language' => 'en,ta,si']);
            } catch (ConnectionException) {
                return $this->unavailable();
            } finally {
                $cache->put('geocoding:next-request', microtime(true) + 1.1, 3);
            }
            if ($response->status() === 429) {
                $cache->put('geocoding:next-request', microtime(true) + 60, 61);

                return $this->busy(60);
            }
            $rows = $response->json();
            if (! $response->successful() || ! is_array($rows) || ! array_is_list($rows)) {
                return $this->unavailable();
            }
            $results = [];
            foreach (array_slice($rows, 0, 5) as $row) {
                if (! is_array($row) || ! is_string($row['display_name'] ?? null)
                    || ! is_numeric($row['lat'] ?? null) || ! is_numeric($row['lon'] ?? null)) {
                    continue;
                }
                $latitude = (float) $row['lat'];
                $longitude = (float) $row['lon'];
                if (! is_finite($latitude) || ! is_finite($longitude) || abs($latitude) > 90 || abs($longitude) > 180) {
                    continue;
                }
                $results[] = ['label' => mb_substr(strip_tags($row['display_name']), 0, 400),
                    'latitude' => $latitude, 'longitude' => $longitude];
            }
            $cache->put($key, $results, now()->addHours(12));

            return response()->json(['data' => $results])->header('Cache-Control', 'private, no-store');
        } finally {
            $lock->release();
        }
    }

    private function unavailable(): JsonResponse
    {
        return response()->json(['message' => 'Address search is temporarily unavailable. Select a point on the map or use current location.'], 503);
    }

    private function busy(int $seconds = 2): JsonResponse
    {
        return response()->json(['message' => 'Address search is busy. Please wait a moment and search again.'], 429)
            ->header('Retry-After', (string) $seconds);
    }
}
