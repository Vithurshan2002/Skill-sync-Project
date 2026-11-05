<?php

namespace App\Filament\Customer\Pages;

use App\Filament\Shared\GatewayPage;
use App\Filament\Shared\WorkspaceStats;
use Filament\Actions\Action;

class Dashboard extends GatewayPage
{
    protected static ?string $slug = 'dashboard';

    protected static ?string $title = 'Your home, in good hands.';

    protected static ?string $navigationLabel = 'Overview';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-squares-2x2';

    protected static ?int $navigationSort = 1;

    protected string $view = 'filament.customer.dashboard';

    protected ?string $subheading = 'A little less to do. A little more peace of mind.';

    protected function getHeaderActions(): array
    {
        return [Action::make('request')->label('New service request')->icon('heroicon-o-plus')->url('/customer/requests/new')];
    }

    protected function getHeaderWidgets(): array
    {
        return [WorkspaceStats::class];
    }

    protected function getViewData(): array
    {
        $requests = $this->gateway()->requests(auth()->user())['data'];
        $bookings = $this->gateway()->bookings(auth()->user())['data'];
        $notifications = $this->gateway()->notifications(auth()->user())['data'];

        return compact('requests', 'bookings', 'notifications');
    }
}
