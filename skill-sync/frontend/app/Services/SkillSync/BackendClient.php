<?php

namespace App\Services\SkillSync;

use Illuminate\Auth\AuthenticationException;
use Illuminate\Contracts\Encryption\DecryptException;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\Http;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpException;

class BackendClient
{
    public function token(): string
    {
        try {
            $encrypted = session('backend_token');
            if (is_string($encrypted) && $encrypted !== '') {
                return Crypt::decryptString($encrypted);
            }
        } catch (DecryptException) {
            // Invalid sessions must authenticate again.
        }
        $this->unauthenticated();
    }

    public function unauthenticated(): never
    {
        Auth::logout();
        session()->invalidate();
        session()->regenerateToken();
        throw new AuthenticationException('Please sign in again.', ['web']);
    }

    public function send(string $method, string $path, array $input = [], bool $authenticated = true): array
    {
        $client = Http::baseUrl(rtrim(config('skillsync.fastapi_base_url'), '/'))
            ->acceptJson()->asJson()->connectTimeout(config('skillsync.connect_timeout'))
            ->timeout(config('skillsync.timeout'));
        if ($authenticated) {
            $client = $client->withToken($this->token());
        }
        try {
            $response = $client->send($method, '/api/v1'.$path, $method === 'GET'
                ? ['query' => $input] : ['json' => $input ?: (object) []]);
        } catch (ConnectionException) {
            throw new HttpException(503, 'The service is temporarily unavailable. Please try again.');
        }
        if ($response->status() === 401) {
            if ($authenticated) {
                $this->unauthenticated();
            }
            throw ValidationException::withMessages(['email' => 'Email or password is incorrect.']);
        }
        if (in_array($response->status(), [409, 422], true)) {
            $fields = $response->json('error.fields');
            throw ValidationException::withMessages(is_array($fields) && $fields !== []
                ? $fields : [str_starts_with($path, '/auth/') ? 'email' : 'operation' => $response->json('error.message') ?: 'This record has changed. Refresh and try again.']);
        }
        if (! $response->successful()) {
            throw new HttpException(in_array($response->status(), [403, 404], true) ? $response->status() : 503,
                $response->status() >= 500 ? 'The service is temporarily unavailable. Please try again.' : 'This record is unavailable or access is denied.');
        }
        $result = $response->json();
        if (! is_array($result) || ! isset($result['data']) || ! is_array($result['data'])) {
            throw new HttpException(503, 'The service returned an unexpected response. Please try again.');
        }

        return $result;
    }

    /** Existing workspace tables consume all records; follow API pagination without truncating. */
    public function all(string $path, array $filters = []): array
    {
        $items = [];
        $page = 1;
        do {
            $result = $this->send('GET', $path, [...$filters, 'page' => $page, 'perPage' => 100]);
            $lastPage = $result['meta']['lastPage'] ?? null;
            if (! is_int($lastPage) || $lastPage < 1 || ($result['meta']['page'] ?? null) !== $page) {
                throw new HttpException(503, 'The service returned invalid pagination.');
            }
            array_push($items, ...$result['data']);
            $page++;
        } while ($page <= $lastPage);

        return ['data' => $items];
    }
}
