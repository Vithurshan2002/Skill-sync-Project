<?php

namespace App\Filament\Shared;

use Filament\Facades\Filament;
use Filament\Pages\Page;

class NotificationsPage extends Page
{
    protected static ?string $slug = 'notifications';

    protected static ?string $title = 'Notifications';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-bell';

    protected static ?int $navigationSort = 91;

    protected ?string $subheading = 'Booking updates and activity, all in one place.';

    protected string $view = 'filament.shared.notifications-page';

    public static function canAccess(): bool
    {
        return auth()->check() && auth()->user()->role === Filament::getCurrentPanel()?->getId();
    }
}
