<?php

namespace App\Filament\Worker\Pages;

use App\Filament\Shared\GatewayPage;
use App\Filament\Shared\WorkspaceStats;

class Dashboard extends GatewayPage
{
    protected static string $role = 'worker';

    protected static ?string $slug = 'dashboard';

    protected static ?string $title = 'Good work starts here.';

    protected static ?string $navigationLabel = 'Overview';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-squares-2x2';

    protected static ?int $navigationSort = 1;

    protected string $view = 'filament.worker.dashboard';

    protected ?string $subheading = 'Your next opportunity and your day ahead, all in one place.';

    protected function getViewData(): array
    {
        return ['bookings' => $this->gateway()->bookings(auth()->user())['data'], 'worker' => $this->gateway()->profile(auth()->user())['data']];
    }

    protected function getHeaderWidgets(): array
    {
        return [WorkspaceStats::class];
    }
}
