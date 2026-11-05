<?php

use App\Http\Middleware\BackendSession;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->redirectGuestsTo(fn () => route('login'));
        $middleware->redirectUsersTo(fn (Request $request) => '/'.$request->user()->role.'/dashboard');
        $middleware->web(append: [BackendSession::class]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->render(function (ValidationException $exception, Request $request) {
            if ($request->expectsJson() && ! $request->is('livewire/*')) {
                return response()->json(['error' => ['code' => 'validation_failed', 'message' => 'Please check the supplied values.', 'fields' => $exception->errors()]], 422);
            }
        });
        $exceptions->render(function (HttpExceptionInterface $exception, Request $request) {
            if ($request->expectsJson() && ! $request->is('livewire/*')) {
                return response()->json(['error' => ['code' => match ($exception->getStatusCode()) {
                    401 => 'unauthenticated', 403 => 'forbidden', 404 => 'not_found', 503 => 'service_unavailable', default => 'request_failed'
                }, 'message' => $exception->getStatusCode() >= 500 ? 'The service is temporarily unavailable. Please try again.' : ($exception->getMessage() ?: 'This action could not be completed.')]], $exception->getStatusCode());
            }
        });
        $exceptions->shouldRenderJsonWhen(
            fn (Request $request) => $request->is('api/*') || $request->expectsJson(),
        );
    })->create();
