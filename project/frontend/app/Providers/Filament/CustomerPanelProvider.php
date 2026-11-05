<?php

namespace App\Providers\Filament;

use App\Filament\Customer\Pages;
use Filament\Panel;

class CustomerPanelProvider extends SkillSyncPanelProvider
{
    public function panel(Panel $panel): Panel
    {
        return $this->shared($panel, 'customer')->default()->pages([
            Pages\Dashboard::class, Pages\NewRequest::class, Pages\RequestDetails::class,
            Pages\Recommendations::class, Pages\Bookings::class, Pages\BookingDetails::class,
            Pages\Profile::class,
        ]);
    }
}
