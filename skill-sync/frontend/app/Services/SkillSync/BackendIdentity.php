<?php

namespace App\Services\SkillSync;

use App\Models\User;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Str;
use Symfony\Component\HttpKernel\Exception\HttpException;

class BackendIdentity
{
    public function sync(array $identity, ?User $current = null): User
    {
        if (! is_string($identity['id'] ?? null) || ! is_string($identity['email'] ?? null)
            || ! is_string($identity['name'] ?? null) || ! is_string($identity['town'] ?? null)
            || ! in_array($identity['role'] ?? null, ['customer', 'worker', 'admin'], true)
            || (($identity['role'] ?? null) === 'worker' && ! is_string($identity['workerId'] ?? null))) {
            throw new HttpException(503, 'The service returned an invalid account.');
        }
        if ($current && $current->backend_id !== $identity['id']) {
            app(BackendClient::class)->unauthenticated();
        }
        $user = $current ?? User::firstOrNew(['backend_id' => $identity['id']]);
        $user->fill([
            'name' => $identity['name'], 'email' => $identity['email'], 'role' => $identity['role'],
            'town' => $identity['town'], 'worker_id' => $identity['workerId'] ?? null,
        ]);
        if (! $user->exists) {
            $user->password = Str::random(64);
        }
        if ($user->isDirty()) {
            $user->save();
        }

        return $user;
    }

    public function signIn(array $result): User
    {
        if (! is_string($result['accessToken'] ?? null) || ! is_array($result['user'] ?? null)) {
            throw new HttpException(503, 'The service returned an invalid login response.');
        }
        $user = $this->sync($result['user']);
        Auth::login($user);
        session()->regenerate();
        session(['backend_token' => Crypt::encryptString($result['accessToken'])]);

        return $user;
    }
}
