<?php

namespace App\Filament\Worker\Pages;

use App\Filament\Customer\Pages\Bookings;

class Jobs extends Bookings
{
    protected static string $role = 'worker';

    protected static ?string $slug = 'jobs';

    protected static ?string $title = 'Your jobs';

    protected static ?string $navigationLabel = 'Jobs';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-briefcase';

    protected static ?int $navigationSort = 2;

    protected function getViewData(): array
    {
        return ['bookings' => $this->gateway()->bookings(auth()->user(), ['status' => $this->status])['data'], 'area' => 'worker', 'recordPath' => 'jobs'];
    }
}
