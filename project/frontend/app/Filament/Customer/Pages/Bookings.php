<?php

namespace App\Filament\Customer\Pages;

use App\Filament\Shared\GatewayPage;
use Livewire\Attributes\Url;

class Bookings extends GatewayPage
{
    protected static ?string $slug = 'bookings';

    protected static ?string $title = 'Your bookings';

    protected static ?string $navigationLabel = 'Bookings';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-calendar-days';

    protected static ?int $navigationSort = 3;

    protected string $view = 'filament.shared.bookings';

    protected ?string $subheading = 'From the first request to the finishing touches.';

    #[Url]
    public string $status = '';

    protected function getViewData(): array
    {
        return ['bookings' => $this->gateway()->bookings(auth()->user(), ['status' => $this->status])['data'], 'area' => 'customer', 'recordPath' => 'bookings'];
    }
}
