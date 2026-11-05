<?php

namespace App\Providers;

use App\Http\Controllers\AuthController;
use App\Http\Middleware\BackendSession;
use Filament\Auth\Http\Controllers\LogoutController;
use Illuminate\Support\ServiceProvider;
use Livewire\Livewire;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        $this->app->bind(LogoutController::class, AuthController::class);
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        Livewire::addPersistentMiddleware([BackendSession::class]);
    }
}
