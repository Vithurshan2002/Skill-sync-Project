<?php

use App\Filament\Shared\NotificationsPage;
use App\Filament\Shared\SettingsPage;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\LocationSearchController;
use App\Http\Controllers\PublicController;
use App\Livewire\PublicPages\WorkerDirectory;
use Illuminate\Support\Facades\Route;

Route::get('/', [PublicController::class, 'home'])->name('home');
Route::get('/about', [PublicController::class, 'about'])->name('about');
Route::get('/services', [PublicController::class, 'services'])->name('services');
Route::get('/workers', WorkerDirectory::class)->name('workers');
Route::get('/workers/{workerId}', [PublicController::class, 'worker'])->name('workers.show');
Route::get('/login', [AuthController::class, 'loginPage'])->name('login')->middleware('guest');
Route::post('/login', [AuthController::class, 'login'])->middleware(['guest', 'throttle:10,1']);
Route::get('/register', [AuthController::class, 'registerPage'])->name('register')->middleware('guest');
Route::post('/register', [AuthController::class, 'register'])->middleware(['guest', 'throttle:10,1']);
Route::post('/logout', [AuthController::class, 'logout'])->name('logout');
Route::middleware('auth')->group(function (): void {
    Route::post('/locations/search', LocationSearchController::class)->middleware('throttle:10,1')->name('locations.search');
    Route::get('/notifications', fn () => redirect(NotificationsPage::getUrl(panel: auth()->user()->role)))->name('notifications');
    Route::get('/settings', fn () => redirect(SettingsPage::getUrl(panel: auth()->user()->role)))->name('settings');
});
Route::fallback(fn () => response()->view('public.not-found', [], 404));
