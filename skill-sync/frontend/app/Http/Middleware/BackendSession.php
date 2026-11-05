<?php

namespace App\Http\Middleware;

use App\Services\SkillSync\BackendClient;
use App\Services\SkillSync\BackendIdentity;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class BackendSession
{
    public function handle(Request $request, Closure $next): Response
    {
        if ($request->user() && ! $request->is('login', 'register', 'logout', '*/logout') && ! $request->attributes->get('backend_verified')) {
            $identity = app(BackendClient::class)->send('GET', '/me')['data'];
            app(BackendIdentity::class)->sync($identity, $request->user());
            $request->attributes->set('backend_verified', true);
        }

        return $next($request);
    }
}
