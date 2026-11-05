<?php

namespace Tests\Feature;

use App\Http\Middleware\BackendSession;
use App\Models\User;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class LocationSearchTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        $this->withoutMiddleware(BackendSession::class);
        config(['services.geocoding.cache_store' => 'array',
            'services.geocoding.search_url' => 'https://geocoder.test/search']);
        Http::preventStrayRequests();
    }

    private function signIn(int $id = 1): void
    {
        $user = new User;
        $user->id = $id;
        $this->actingAs($user);
    }

    public function test_search_requires_login_and_valid_query(): void
    {
        $this->postJson('/locations/search', ['query' => 'Colombo'])->assertUnauthorized();
        $this->signIn();
        foreach (['ab', '   ', str_repeat('a', 201), ['Colombo']] as $query) {
            $this->postJson('/locations/search', ['query' => $query])->assertUnprocessable();
        }
        Http::assertNothingSent();
    }

    public function test_search_sanitizes_results_and_caches_across_users(): void
    {
        $this->signIn();
        Http::fake(['geocoder.test/*' => Http::response([
            ['display_name' => '<b>Colombo Fort</b>, Sri Lanka', 'lat' => '6.9344', 'lon' => '79.8428'],
            ['display_name' => 'Invalid point', 'lat' => '91', 'lon' => '80'],
            ['display_name' => ['invalid'], 'lat' => '7', 'lon' => '80'],
        ])]);
        $this->postJson('/locations/search', ['query' => '  Colombo   Fort  '])->assertOk()
            ->assertJsonCount(1, 'data')->assertJsonPath('data.0.latitude', 6.9344)
            ->assertJsonPath('data.0.label', 'Colombo Fort, Sri Lanka');
        Http::assertSent(fn (Request $request) => $request['q'] === 'Colombo Fort'
            && $request['countrycodes'] === 'lk' && $request['limit'] === 5
            && $request->hasHeader('User-Agent') && str_starts_with($request->header('User-Agent')[0], 'SkillSync/'));
        $this->signIn(2);
        $this->postJson('/locations/search', ['query' => 'colombo fort'])->assertOk()->assertJsonCount(1, 'data');
        Http::assertSentCount(1);
        $this->postJson('/locations/search', ['query' => 'Jaffna'])->assertTooManyRequests()->assertHeader('Retry-After', '2');
        Http::assertSentCount(1);
    }

    public function test_empty_results_are_cached_without_becoming_an_error(): void
    {
        $this->signIn();
        Http::fake(['geocoder.test/*' => Http::response([])]);
        $this->postJson('/locations/search', ['query' => 'Unknown landmark'])->assertOk()->assertExactJson(['data' => []]);
        $this->postJson('/locations/search', ['query' => 'Unknown landmark'])->assertOk();
        Http::assertSentCount(1);
    }

    public function test_global_lock_prevents_overlapping_provider_calls(): void
    {
        $this->signIn();
        $lock = Cache::store('array')->lock('geocoding:provider-lock', 20);
        $this->assertTrue($lock->get());
        try {
            $this->postJson('/locations/search', ['query' => 'Jaffna'])->assertTooManyRequests();
            Http::assertNothingSent();
        } finally {
            $lock->release();
        }
    }

    public function test_connection_failure_is_safe_and_releases_global_lock(): void
    {
        $this->signIn();
        Http::fake(['geocoder.test/*' => Http::failedConnection()]);
        $this->postJson('/locations/search', ['query' => 'Colombo'])->assertStatus(503)
            ->assertJsonPath('message', 'Address search is temporarily unavailable. Select a point on the map or use current location.');
        $lock = Cache::store('array')->lock('geocoding:provider-lock', 20);
        $this->assertTrue($lock->get());
        $lock->release();
        $this->postJson('/locations/search', ['query' => 'Jaffna'])->assertTooManyRequests();
    }

    public function test_provider_throttling_applies_shared_backoff(): void
    {
        $this->signIn();
        Http::fake(['geocoder.test/*' => Http::response([], 429)]);
        $this->postJson('/locations/search', ['query' => 'Colombo'])->assertTooManyRequests()->assertHeader('Retry-After', '60');
        $this->signIn(2);
        $this->postJson('/locations/search', ['query' => 'Jaffna'])->assertTooManyRequests();
        Http::assertSentCount(1);
    }

    public function test_provider_failure_is_not_exposed_or_cached_as_no_results(): void
    {
        $this->signIn();
        Http::fake(['geocoder.test/*' => Http::response(['error' => 'Private provider detail'], 500)]);
        $this->postJson('/locations/search', ['query' => 'Colombo'])->assertStatus(503)->assertDontSee('Private provider detail');
        Cache::store('array')->forget('geocoding:next-request');
        $this->postJson('/locations/search', ['query' => 'Colombo'])->assertStatus(503);
        Http::assertSentCount(2);
    }
}
